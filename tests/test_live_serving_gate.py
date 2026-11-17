"""Live serving admits a Flink fact only as recomputed from the archive (ADR-0054)."""

import base64
from pathlib import Path
from typing import cast

import pytest

from runtime.continuous.live_archive_gate import SESSION_KEY, ArchivedFacts
from runtime.s3.archive_store import ArchiveStore
from telemetry.archive_documents import digest
from telemetry.continuous_archive import SegmentedArchive
from telemetry.conversion_contract import json_line
from telemetry.live_event import event_bytes, event_key, make_event
from telemetry.live_runtime import Document, LiveRuntime, make_output, session_config

SOURCE: Document = {"cluster_id": "c", "topic_id": "m/w+A", "topic": "t"}
SCOPE: Document = {
    "kind": "px4-sitl",
    "vehicle": "sitl-1",
    "boot_session": "boot-a",
    "system": 1,
    "component": 1,
}
SESSION: Document = {
    "profile": "px4-live-session-v1",
    "run_id": "live-test",
    "source": SCOPE,
    "max_receipt_age_ms": 3000,
}


def event(message: str, data: Document, sequence: int, received: int) -> Document:
    return make_event("live-test", SCOPE, message, data, "a" * 32, sequence, received)


def battery(sequence: int, received: int) -> Document:
    data: Document = {
        "voltage_battery": 16200,
        "current_battery": -1,
        "battery_remaining": 80,
    }
    return event("SYS_STATUS", data, sequence, received)


def position(boot: int, sequence: int, received: int) -> Document:
    native = ("lat", "lon", "alt", "relative_alt", "vx", "vy", "vz")
    data: Document = {"time_boot_ms": boot, **dict.fromkeys(native, 0)}
    return event("GLOBAL_POSITION_INT", data, sequence, received)


class Store:
    """Exact immutable objects, read back by digest like the archive store."""

    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def create(self, key: str, body: bytes) -> str:
        if self.values.setdefault(key, body) != body:
            raise ValueError("immutable_conflict")
        return key

    def read(self, key: str, sha256: str, byte_length: int) -> bytes:
        body = self.values[key]
        assert len(body) == byte_length and digest(body) == sha256
        return body

    def lookup(self, key: str) -> bytes | None:
        return self.values.get(key)


def row(offset: int, event: Document) -> Document:
    return {
        **SOURCE,
        "partition": 0,
        "offset": offset,
        "format_version": "kafka-observation-v1",
        "timestamp_ms": None,
        "timestamp_type": "not_available",
        "key_b64": base64.b64encode(event_key(event).encode()).decode(),
        "value_b64": base64.b64encode(event_bytes(event)).decode(),
        "headers": [],
        "measurement": None,
    }


def test_outputs_wait_for_the_archive_and_must_equal_its_recomputation(
    tmp_path: Path,
) -> None:
    plan: Document = {
        "format_version": "continuous-archive-plan-v1",
        "partitions": 1,
        "source": SOURCE,
    }
    config: Document = {
        "session": SESSION,
        "archive_plan": plan,
        "max_deliveries": 100,
        "sources": {"input": SOURCE},
    }
    store = Store()
    store.create(SESSION_KEY, json_line(session_config(SESSION)))
    writer = SegmentedArchive(
        store, store, tmp_path / "cursor.json", plan, initialize=True
    )
    events = [battery(0, 10_000), position(1000, 1, 10_100), position(1200, 2, 10_300)]
    runtime = LiveRuntime(SESSION)
    outputs = {
        offset: make_output(fact, SOURCE, offset, runtime.session_sha256)
        for offset, event in enumerate(events)
        if (fact := runtime.accept(event)) is not None
    }
    writer.publish(0, [row(i, e) for i, e in enumerate(events[:2])])
    gate = ArchivedFacts(config, cast(ArchiveStore, store), tmp_path)
    gate.advance()
    assert gate.admit(outputs[1])
    assert not gate.admit(outputs[2])  # its input is not archived yet
    writer.publish(0, [row(2, events[2])])
    gate.advance()
    assert gate.admit(outputs[2])
    assert gate.identities == {
        cast(Document, outputs[o]["fact"])["measurement_id"] for o in (1, 2)
    }
    # A fact that differs from the archive recomputation never reaches SQL.
    fact = cast(Document, outputs[2]["fact"])
    changed = {
        **fact,
        "battery": {**cast(Document, fact["battery"]), "status": "stale"},
    }
    with pytest.raises(ValueError, match="live_output_content"):
        gate.admit({**outputs[2], "fact": changed})
