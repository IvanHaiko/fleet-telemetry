"""Exercise actual Python workers, timestamp assignment and invalid side output."""

import argparse
import json
import platform
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from pyflink.common import Duration, Types, WatermarkStrategy
from pyflink.common.watermark_strategy import TimestampAssigner
from pyflink.datastream import OutputTag
from pyflink.datastream.functions import ProcessFunction

from probe_support import collect_output, execution_environment

INVALID = OutputTag("invalid-time", Types.STRING())
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
UTC_TEXT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z"
)


def epoch_milliseconds(timestamp: str) -> int:
    """Keep integer microseconds until deliberate floor-to-millisecond conversion."""
    if UTC_TEXT.fullmatch(timestamp) is None:
        raise ValueError("invalid_timestamp")
    delta = datetime.fromisoformat(timestamp) - EPOCH
    return ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds) // 1000


class TimeGate(ProcessFunction):
    """Reject malformed time before watermark generation; emit safe dispositions."""

    def process_element(
        self, value: tuple[str, str], ctx: ProcessFunction.Context
    ) -> Iterator[tuple[str, int] | tuple[OutputTag, str]]:
        try:
            milliseconds = epoch_milliseconds(value[1])
        except ValueError:
            yield INVALID, json.dumps({"kind": "invalid", "label": value[0]})
            return
        yield value[0], milliseconds


class EventTimestamp(TimestampAssigner):
    def extract_timestamp(self, value: tuple[str, int], record_timestamp: int) -> int:
        """Assign the separately converted event time, preserving negative epochs."""
        return value[1]


class TimestampAudit(ProcessFunction):
    def process_element(
        self, value: tuple[str, int], ctx: ProcessFunction.Context
    ) -> Iterator[str]:
        """Observe the timestamp at the downstream operator in a Python worker."""
        yield json.dumps(
            {
                "kind": "timestamp",
                "label": value[0],
                "event_ms": value[1],
                "assigned_ms": ctx.timestamp(),
                "worker_python": platform.python_version(),
            }
        )


def run(scratch: Path) -> list[object]:
    """Complete a fixed synthetic trace with finite source EOF."""
    env = execution_environment(scratch)
    env.add_python_file(str(Path(__file__).resolve()))
    samples = [
        ("pre-epoch", "1969-12-31T23:59:59.999999Z"),
        ("epoch", "1970-01-01T00:00:00.000000Z"),
        ("before-edge", "1970-01-01T00:00:09.999999Z"),
        ("edge", "1970-01-01T00:00:10.000000Z"),
        ("after-edge", "1970-01-01T00:00:10.000001Z"),
        ("invalid", "invalid-private-timestamp"),
    ]
    gated = env.from_collection(
        samples, type_info=Types.TUPLE([Types.STRING(), Types.STRING()])
    ).process(TimeGate(), output_type=Types.TUPLE([Types.STRING(), Types.LONG()]))
    timed = gated.assign_timestamps_and_watermarks(
        WatermarkStrategy.for_bounded_out_of_orderness(
            Duration.of_seconds(2)
        ).with_timestamp_assigner(EventTimestamp())
    )
    audited = timed.process(TimestampAudit(), output_type=Types.STRING())
    output = audited.union(gated.get_side_output(INVALID))
    return collect_output(output, 6, "m3-python-worker-probe")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({"status": "worker_probe_completed", "rows": run(args.scratch)}))


if __name__ == "__main__":
    main()
