"""Continuous progress, immutable retry boundaries and visible retained corruption."""

from pathlib import Path

import pytest

from telemetry.archive_documents import digest
from telemetry.continuous_archive import SegmentedArchive


class Store:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def create(self, key: str, body: bytes) -> str:
        prior = self.values.setdefault(key, body)
        if prior != body:
            raise ValueError("immutable_conflict")
        return key

    def read(self, key: str, sha256: str, byte_length: int) -> bytes:
        body = self.values[key]
        if len(body) != byte_length or digest(body) != sha256:
            raise ValueError("checksum_mismatch")
        return body

    def lookup(self, key: str) -> bytes | None:
        return self.values.get(key)


SOURCE = {
    "cluster_id": "AQEBAQEBAQEBAQEBAQEBAQ",
    "topic_id": "AgICAgICAgICAgICAgICAg",
    "topic": "continuous-input",
}
PLAN: dict[str, object] = {
    "format_version": "continuous-archive-plan-v1",
    "source": SOURCE,
    "partitions": 2,
}


def rows(start: int, end: int) -> list[dict[str, object]]:
    return [
        {
            **SOURCE,
            "format_version": "kafka-observation-v1",
            "partition": 0,
            "offset": i,
            "timestamp_type": "create_time",
            "timestamp_ms": i,
            "key_b64": "aw==",
            "value_b64": "e30=",
            "headers": [],
            "measurement": None,
        }
        for i in range(start, end)
    ]


def test_resume_after_uncommitted_receipt_accepts_changed_batch_boundaries(
    tmp_path: Path,
) -> None:
    store = Store()
    path = tmp_path / "cursor.json"
    archive = SegmentedArchive(store, store, path, PLAN, initialize=True)
    initial = path.read_bytes()
    assert archive.publish(0, rows(0, 130)) == 130
    path.write_bytes(initial)  # Model a crash before durable local progress.
    resumed = SegmentedArchive(store, store, path, PLAN)
    assert resumed.publish(0, rows(0, 256)) == 130
    assert resumed.publish(0, rows(130, 256)) == 126
    assert resumed.next_offset(0) == 256
    assert SegmentedArchive(store, store, path, PLAN).next_offset(0) == 256
    with pytest.raises(ValueError, match="archive_offset_gap"):
        resumed.publish(0, rows(257, 258))


def test_retained_segment_damage_cannot_certify_restart_progress(
    tmp_path: Path,
) -> None:
    store = Store()
    path = tmp_path / "cursor.json"
    archive = SegmentedArchive(store, store, path, PLAN, initialize=True)
    archive.publish(0, rows(0, 64))
    key = next(key for key in store.values if key.startswith("segments/"))
    store.values[key] = b"damaged\n"
    with pytest.raises(ValueError, match="checksum_mismatch"):
        SegmentedArchive(store, store, path, PLAN)
