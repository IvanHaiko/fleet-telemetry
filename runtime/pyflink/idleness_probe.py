"""Observed global watermark from two independently timestamped Flink inputs."""

from pathlib import Path

from pyflink.common import Duration, Types, WatermarkStrategy
from pyflink.datastream.functions import SourceFunction
from pyflink.java_gateway import get_gateway

from battery_gate import ADMITTED, INVALID, BatteryScope, BatteryTimestamp
from idleness_source import IDLE_SECONDS, MAX_INPUTS, IdleInputs
from paced_source import PacedGate, decode_frame
from probe_support import collect_output, execution_environment
from watermark_probe import ObservedBattery


def run(
    scope: BatteryScope, inputs: dict[str, bytes], scratch: Path
) -> tuple[list[bytes], list[object], list[dict[str, object]]]:
    """Use owned loopback sockets, existing SDK generators and unchanged state logic."""
    scope.validate()
    scratch.mkdir(parents=True, exist_ok=False)
    control = scratch / "control"
    control.mkdir()
    env = execution_environment(scratch / "job")
    env.get_config().set_auto_watermark_interval(100)
    for name in (
        "idleness_probe.py",
        "idleness_source.py",
        "watermark_probe.py",
        "paced_source.py",
        "battery_gate.py",
        "battery_operator.py",
        "worker_probe.py",
    ):
        env.add_python_file(str(Path(__file__).with_name(name).resolve()))
    with IdleInputs(inputs, control) as source:
        streams = []
        rejected = []
        for lane, listener in enumerate(source.listeners):
            port = listener.getsockname()[1]
            j_functions = get_gateway().jvm.org.apache.flink.streaming.api.functions
            j_source = j_functions.source.legacy.SocketTextStreamFunction(
                "127.0.0.1", port, "\n", 0
            )
            framed = env.add_source(SourceFunction(j_source), type_info=Types.STRING())
            decoded = framed.map(
                decode_frame,
                output_type=Types.TUPLE(
                    [Types.LONG(), Types.PRIMITIVE_ARRAY(Types.BYTE())]
                ),
            )
            gated = decoded.process(
                PacedGate(scope, control), output_type=ADMITTED
            ).uid(f"battery-idle-admission-{lane}-v1")
            streams.append(
                gated.assign_timestamps_and_watermarks(
                    WatermarkStrategy.for_bounded_out_of_orderness(
                        Duration.of_seconds(2)
                    )
                    .with_idleness(Duration.of_seconds(IDLE_SECONDS))
                    .with_timestamp_assigner(BatteryTimestamp())
                )
            )
            rejected.append(gated.get_side_output(INVALID))
        processed = (
            streams[0]
            .union(streams[1])
            .key_by(
                lambda value: (scope.dataset_run_id, value[1]),
                key_type=Types.TUPLE([Types.STRING(), Types.STRING()]),
            )
            .process(ObservedBattery(scope, control, MAX_INPUTS), Types.STRING())
            .uid("battery-two-input-idleness-v1")
        )
        rows = collect_output(
            processed.union(*rejected), 3 * MAX_INPUTS, "m3-two-input-idleness"
        )
    return source.wires, rows, source.phases
