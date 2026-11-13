"""Trusted synthetic admission before timestamp assignment in the bounded probe."""

import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import cast

from pyflink.common import Types
from pyflink.common.watermark_strategy import TimestampAssigner
from pyflink.datastream import OutputTag
from pyflink.datastream.functions import ProcessFunction, RuntimeContext
from pyflink.metrics import Counter
from telemetry_reader import EnvelopeError, read_battery_event

from worker_probe import epoch_milliseconds

MAX_OBSERVATIONS = 1023
MAX_INPUT_BYTES = 1_048_576
INVALID = OutputTag("battery-invalid-v1", Types.STRING())
ADMITTED = Types.TUPLE(
    [Types.LONG(), Types.STRING(), Types.LONG(), Types.STRING(), Types.STRING()]
)
type Admitted = tuple[int, str, int, str, str]
SEMANTIC_FIELDS = (
    "vehicle_id",
    "event_type",
    "source_timestamp",
    "source_log_id",
    "source_type",
    "source_stream",
    "source_record_index",
    "normalization_version",
    "source_time",
    "payload",
)


@dataclass(frozen=True)
class BatteryScope:
    dataset_run_id: str
    pipeline_version: str
    source_log_id: str
    timestamp_min: str
    timestamp_max: str

    def validate(self) -> None:
        """Refuse invalid trusted configuration before a job is submitted."""
        if (
            any(
                re.fullmatch(r"[\x20-\x7e]+", value) is None
                for value in (self.dataset_run_id, self.pipeline_version)
            )
            or re.fullmatch(r"sha256:[0-9a-f]{64}", self.source_log_id) is None
        ):
            raise ValueError("invalid_battery_scope")
        epoch_milliseconds(self.timestamp_min)
        epoch_milliseconds(self.timestamp_max)
        if self.timestamp_min > self.timestamp_max:
            raise ValueError("invalid_battery_scope_bounds")


def bounded_input(wires: Sequence[bytes]) -> list[tuple[int, bytes]]:
    """The finite source, not event-time TTL, bounds this experiment's history."""
    if len(wires) > MAX_OBSERVATIONS or any(type(wire) is not bytes for wire in wires):
        raise ValueError("battery_input_count_or_type")
    if sum(map(len, wires)) > MAX_INPUT_BYTES:
        raise ValueError("battery_input_bytes")
    return list(enumerate(wires))


def semantics(event: dict[str, object]) -> str:
    """Use recognized M1 semantics; delivery/provenance are not measurements."""
    result = {key: event[key] for key in SEMANTIC_FIELDS}
    result["quality_flags"] = sorted(cast(list[str], event["quality_flags"]))
    return json.dumps(result, sort_keys=True, separators=(",", ":"))


class BatteryGate(ProcessFunction):
    def __init__(self, scope: BatteryScope) -> None:
        self.scope = scope

    def open(self, runtime_context: RuntimeContext) -> None:
        self.admitted: Counter = runtime_context.get_metrics_group().counter("admitted")
        self.invalid: Counter = runtime_context.get_metrics_group().counter("invalid")

    def process_element(
        self, value: tuple[int, bytes], ctx: ProcessFunction.Context
    ) -> Iterator[Admitted | tuple[OutputTag, str]]:
        """Reject bad envelopes and out-of-scope time before watermark generation."""
        index, wire = value
        event_id = None
        reason = "envelope_invalid"
        try:
            event = read_battery_event(wire)
        except EnvelopeError:
            pass
        else:
            event_id = event["event_id"]
            if (
                event["source_type"] == "synthetic"
                and event["normalization_version"] == "battery-v1"
                and event["source_log_id"] == self.scope.source_log_id
                and event["delivery"]["dataset_run_id"] == self.scope.dataset_run_id
                and self.scope.timestamp_min
                <= event["source_timestamp"]
                <= self.scope.timestamp_max
            ):
                # The reader supplies normalized nullable payloads and flags.
                self.admitted.inc()
                yield (
                    index,
                    event["vehicle_id"],
                    epoch_milliseconds(event["source_timestamp"]),
                    event_id,
                    json.dumps(event, separators=(",", ":")),
                )
                return
            reason = "scope_mismatch"
        self.invalid.inc()
        yield (
            INVALID,
            json.dumps(
                {
                    "kind": "disposition",
                    "observation_index": index,
                    "disposition": "invalid",
                    "reason": reason,
                    "event_id": event_id,
                }
            ),
        )


class BatteryTimestamp(TimestampAssigner):
    def extract_timestamp(self, value: Admitted, record_timestamp: int) -> int:
        """Assign only a validated measurement time."""
        return value[2]
