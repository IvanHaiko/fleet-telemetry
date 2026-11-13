"""Verified synthetic input and exact receipt protocol for the local Kafka probe."""

import hashlib
import json
import os
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from confluent_kafka import libversion

from telemetry.kafka_compat import KafkaCompatibilityError, require_uuid_boundary
from telemetry_convert import load_job, verify_job
from telemetry_reader import BatteryEvent, read_battery_event

ENDPOINT = "127.0.0.1:19092"


RECEIPT_VERSION = "kafka-probe-receipt-v1"


MAX_RECEIPT_BYTES = 64 * 1024


class ProbeError(ValueError):
    """Safe experiment failure without embedding native payloads."""


class RetentionGapError(ProbeError):
    """Describe missing captured coverage without exposing event payloads."""

    def __init__(self, low: int, high: int) -> None:
        super().__init__("retention_gap")
        self.retained_interval = (low, high)
        self.missing_intervals: list[tuple[int, int]] = []
        if low > 0:
            self.missing_intervals.append((0, min(low, 3)))
        if high < 3:
            self.missing_intervals.append((max(high, 0), 3))


@dataclass(frozen=True)
class Fixture:
    """Verified source bytes and the three expected observations."""

    raw: bytes
    values: tuple[bytes, ...]
    events: tuple[BatteryEvent, ...]
    keys: tuple[bytes, ...]


def fixture(job: Path, run: Path) -> Fixture:
    """Preflight the source/run before any broker operation."""
    try:
        require_uuid_boundary()
    except KafkaCompatibilityError:
        raise ProbeError("kafka_uuid_boundary_unavailable") from None
    if load_job(job).mode != "synthetic":
        raise ProbeError("synthetic_job_required")
    verify_job(job, run)
    with (run / "events.jsonl").open("rb") as source:
        raw = source.read(64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024:
        raise ProbeError("event_file_bound_exceeded")
    values = tuple(raw.splitlines())
    if len(values) != 3:
        raise ProbeError("three_event_fixture_required")
    events = tuple(read_battery_event(value) for value in values)
    if any(event["source_type"] != "synthetic" for event in events):
        raise ProbeError("synthetic_events_required")
    return Fixture(raw, values, events, tuple(e["vehicle_id"].encode() for e in events))


def serialized(report: dict[str, object]) -> bytes:
    """Serialize the internal checkpoint format, independent of wire JSON."""
    return (
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def check_receipt(path: Path, expected: dict[str, object]) -> bytes:
    """Compare bounded checkpoint bytes to externally reconstructed coverage."""
    with path.open("rb") as source:
        data = source.read(MAX_RECEIPT_BYTES + 1)
    if len(data) > MAX_RECEIPT_BYTES or data != serialized(expected):
        raise ProbeError("receipt_context_or_bytes_differ")
    return data


def receipt(path: Path, report: dict[str, object]) -> None:
    """Write/fsync/recheck a new receipt before broker commit."""
    data = serialized(report)
    if len(data) > MAX_RECEIPT_BYTES:
        raise ProbeError("receipt_bound_exceeded")
    with path.open("xb") as destination:
        destination.write(data)
        destination.flush()
        os.fsync(destination.fileno())
    check_receipt(path, report)


def consumer_config(experiment: str) -> dict[str, object]:
    """Keep group identity and automatic-offset behavior explicit."""
    return {
        "bootstrap.servers": ENDPOINT,
        "group.id": f"m2-{experiment}",
        "enable.auto.commit": False,
        "enable.auto.offset.store": False,
        "auto.offset.reset": "error",
        "group.protocol": "classic",
        "socket.timeout.ms": 10000,
    }


def acknowledgements() -> list[dict[str, object]]:
    """Expected delivery positions for this fixed, fresh single-partition topic."""
    return [
        {
            "input_position": i,
            "acknowledged": True,
            "error_code": None,
            "partition": 0,
            "offset": i,
        }
        for i in range(3)
    ]


def observation(data: Fixture, index: int) -> dict[str, object]:
    """Bind each native position to the exact key/value bytes and event ID."""
    return {
        "offset": index,
        "partition": 0,
        "event_id": data.events[index]["event_id"],
        "value_sha256": hashlib.sha256(data.values[index]).hexdigest(),
        "key_sha256": hashlib.sha256(data.keys[index]).hexdigest(),
    }


def report_for(
    data: Fixture, experiment: str, topic: str, ids: tuple[str, str]
) -> dict[str, object]:
    """Reconstruct complete receipt coverage without trusting receipt fields."""
    return {
        "receipt_version": RECEIPT_VERSION,
        "status": "observed_before_commit",
        "experiment_id": experiment,
        "cluster_id": ids[0],
        "topic_id": ids[1],
        "topic": topic,
        "client": version("confluent-kafka"),
        "librdkafka": libversion()[0],
        "events_file_sha256": hashlib.sha256(data.raw).hexdigest(),
        "start_offset": 0,
        "end_offset": 3,
        "start_committed_offset": 0,
        "pending": 0,
        "acknowledged": acknowledgements(),
        "observed": [observation(data, index) for index in range(3)],
        "consumer_config": consumer_config(experiment),
        "retention_scope": "single-local-replica",
    }
