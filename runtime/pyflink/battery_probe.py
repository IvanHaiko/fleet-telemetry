"""Finite real Python-worker battery processing with provisional collected output."""

from collections.abc import Sequence
from pathlib import Path

from pyflink.common import Duration, Types, WatermarkStrategy

from battery_gate import (
    ADMITTED,
    INVALID,
    BatteryGate,
    BatteryScope,
    BatteryTimestamp,
    bounded_input,
)
from battery_operator import BatteryOperator
from probe_support import collect_output, execution_environment


def run(scope: BatteryScope, wires: Sequence[bytes], scratch: Path) -> list[object]:
    """Finite source EOF drives terminal timers; no broker or checkpoint is used."""
    scope.validate()
    samples = bounded_input(wires)
    env = execution_environment(scratch)
    # Deliberately no periodic watermark: deterministic terminal-only first slice.
    env.get_config().set_auto_watermark_interval(0)
    for name in ("battery_gate.py", "battery_operator.py", "worker_probe.py"):
        env.add_python_file(str(Path(__file__).with_name(name).resolve()))
    gated = (
        env.from_collection(
            samples,
            type_info=Types.TUPLE([Types.LONG(), Types.PRIMITIVE_ARRAY(Types.BYTE())]),
        )
        .process(BatteryGate(scope), output_type=ADMITTED)
        .uid("battery-admission-v1")
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
        .process(BatteryOperator(scope), output_type=Types.STRING())
        .uid("battery-state-v1")
    )
    return collect_output(
        processed.union(gated.get_side_output(INVALID)),
        3 * len(samples),
        "m3-bounded-battery-operator",
    )
