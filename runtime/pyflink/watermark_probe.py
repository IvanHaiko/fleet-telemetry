"""Actual periodic watermarks and state boundaries in a finite paced Flink job."""

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import cast

from pyflink.common import Duration, Types, WatermarkStrategy
from pyflink.datastream.functions import (
    KeyedProcessFunction,
    RuntimeContext,
    SourceFunction,
)
from pyflink.datastream.time_domain import TimeDomain
from pyflink.java_gateway import get_gateway

from battery_gate import (
    ADMITTED,
    INVALID,
    Admitted,
    BatteryScope,
    BatteryTimestamp,
    bounded_input,
)
from battery_operator import BatteryOperator
from paced_source import PacedGate, PacedSource, Scheduled, decode_frame, receipt
from probe_support import collect_output, execution_environment


class ObservedBattery(BatteryOperator):
    """Test-only processing-time polling records the operator's actual watermark."""

    def __init__(self, scope: BatteryScope, control: Path, identity_limit: int) -> None:
        super().__init__(scope, identity_limit)
        self.control = control

    def open(self, runtime_context: RuntimeContext) -> None:
        super().open(runtime_context)
        self.last_index = -1
        self.polling = False

    def publish(self, ctx: KeyedProcessFunction.Context) -> None:
        watermark = cast(int, ctx.timer_service().current_watermark())  # type: ignore[no-untyped-call]
        receipt(
            self.control / "state.json",
            {
                "observation_index": self.last_index,
                "watermark_ms": watermark,
                **self.state_counts(),
            },
        )

    def process_element(
        self, value: Admitted, ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        yield from super().process_element(value, ctx)
        self.last_index = value[0]
        self.publish(ctx)
        if not self.polling:
            ctx.timer_service().register_processing_time_timer(
                cast(int, ctx.timer_service().current_processing_time()) + 100  # type: ignore[no-untyped-call]
            )
            self.polling = True

    def on_timer(
        self, timestamp: int, ctx: KeyedProcessFunction.OnTimerContext
    ) -> Iterator[str]:
        if ctx.time_domain() == TimeDomain.EVENT_TIME:
            yield from super().on_timer(timestamp, ctx)
        else:
            self.publish(ctx)
            ctx.timer_service().register_processing_time_timer(
                cast(int, ctx.timer_service().current_processing_time()) + 100  # type: ignore[no-untyped-call]
            )


def run(
    scope: BatteryScope,
    samples: Sequence[Scheduled],
    scratch: Path,
    *,
    identity_limit: int = 1023,
) -> list[object]:
    scope.validate()
    bounded_input([sample.wire for sample in samples])
    if len(samples) > 128:
        raise ValueError("paced_trace_limit")
    scratch.mkdir(parents=True, exist_ok=False)
    control = scratch / "control"
    control.mkdir()
    env = execution_environment(scratch / "job")
    env.get_config().set_auto_watermark_interval(100)
    for name in (
        "watermark_probe.py",
        "paced_source.py",
        "battery_gate.py",
        "battery_operator.py",
        "worker_probe.py",
    ):
        env.add_python_file(str(Path(__file__).with_name(name).resolve()))
    with PacedSource(samples, control) as source:
        # Existing bundled legacy source; no custom JVM code or added JAR.
        j_functions = get_gateway().jvm.org.apache.flink.streaming.api.functions
        source_class = j_functions.source.legacy.SocketTextStreamFunction
        j_source = source_class("127.0.0.1", source.port, "\n", 0)
        framed = env.add_source(SourceFunction(j_source), type_info=Types.STRING())
        decoded = framed.map(
            decode_frame,
            output_type=Types.TUPLE(
                [
                    Types.LONG(),
                    Types.PRIMITIVE_ARRAY(Types.BYTE()),
                ]
            ),
        )
        gated = decoded.process(PacedGate(scope, control), output_type=ADMITTED).uid(
            "battery-paced-admission-v1"
        )
        timed = gated.assign_timestamps_and_watermarks(
            WatermarkStrategy.for_bounded_out_of_orderness(
                Duration.of_seconds(2)
            ).with_timestamp_assigner(BatteryTimestamp())
        )
        processed = (
            timed.key_by(
                lambda value: (scope.dataset_run_id, value[1]),
                key_type=Types.TUPLE([Types.STRING(), Types.STRING()]),
            )
            .process(
                ObservedBattery(scope, control, identity_limit),
                output_type=Types.STRING(),
            )
            .uid("battery-paced-state-v1")
        )
        output = processed.union(gated.get_side_output(INVALID))
        return collect_output(output, 3 * len(samples), "m3-paced-watermarks")
