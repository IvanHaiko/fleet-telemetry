"""Bounded immutable segments and durable progress for a continuous archive."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, cast

from telemetry.archive_codec import _source, decode_observations, encode_observations
from telemetry.archive_documents import canonical, digest

type Row = dict[str, object]
MAX_SEGMENT = 1_048_576
MAX_RECORDS = 256


class ByteStore(Protocol):
    def create(self, key: str, body: bytes) -> str: ...
    def read(self, key: str, sha256: str, byte_length: int) -> bytes: ...
    def lookup(self, key: str) -> bytes | None: ...


def require(condition: object, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def object_row(value: object) -> Row:
    require(isinstance(value, dict), "archive_document_shape")
    return cast(Row, value)


def segment_body(rows: Sequence[Mapping[str, object]]) -> bytes:
    require(0 < len(rows) <= MAX_RECORDS, "archive_segment_count")
    body = b"".join(
        encode_observations(rows[i : i + 16]) for i in range(0, len(rows), 16)
    )
    require(len(body) <= MAX_SEGMENT, "archive_segment_bytes")
    decoded = segment_rows(body)
    source = _source(
        {
            key: decoded[0][key]
            for key in ("cluster_id", "topic_id", "topic", "partition")
        }
    )
    start = cast(int, decoded[0]["offset"])
    for index, row in enumerate(decoded):
        require(
            all(row[key] == value for key, value in source.items()),
            "archive_mixed_source",
        )
        require(row["offset"] == start + index, "archive_offset_gap")
    return body


def segment_rows(body: bytes) -> tuple[Row, ...]:
    require(
        0 < len(body) <= MAX_SEGMENT and body.endswith(b"\n"), "archive_segment_bytes"
    )
    lines = body.splitlines(keepends=True)
    require(0 < len(lines) <= MAX_RECORDS, "archive_segment_count")
    return tuple(
        row
        for i in range(0, len(lines), 16)
        for row in decode_observations(b"".join(lines[i : i + 16]))
    )


def durable_cursor(path: Path, value: Row) -> None:
    """Replace only current progress; immutable evidence remains in object storage."""
    require(not path.is_symlink(), "archive_cursor_symlink")
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("wb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    if os.name == "posix":
        fd = os.open(path.parent, os.O_RDONLY | int(getattr(os, "O_DIRECTORY", 0)))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class SegmentedArchive:
    """One locked runtime owner; remote readback -> local cursor -> broker commit."""

    def __init__(
        self,
        writer: ByteStore,
        reader: ByteStore,
        path: Path,
        plan: Row,
        *,
        initialize: bool = False,
    ) -> None:
        self.writer, self.reader, self.path, self.plan = writer, reader, path, plan
        plan_body = canonical(plan)
        require(
            plan.get("format_version") == "continuous-archive-plan-v1",
            "archive_plan_version",
        )
        count = plan.get("partitions")
        require(
            type(count) is int and 1 <= count <= 18,
            "archive_partition_bound",
        )
        self.count = cast(int, count)
        self.binding = digest(plan_body)
        if initialize:
            require(
                not path.exists() and reader.lookup("stream-plan.json") is None,
                "archive_scope_exists",
            )
            writer.create("stream-plan.json", plan_body)
            require(
                reader.read("stream-plan.json", self.binding, len(plan_body))
                == plan_body,
                "archive_plan_readback",
            )
            state: Row = {
                "format_version": "continuous-archive-cursor-v1",
                "plan_sha256": self.binding,
                "partitions": {
                    str(i): {"next": 0, "start": 0, "receipt_sha256": None}
                    for i in range(self.count)
                },
            }
            durable_cursor(path, state)
        require(
            path.is_file() and path.stat().st_size <= 65536, "archive_cursor_required"
        )
        self.state = object_row(json.loads(path.read_bytes()))
        require(
            set(self.state) == {"format_version", "plan_sha256", "partitions"}
            and self.state["format_version"] == "continuous-archive-cursor-v1"
            and self.state["plan_sha256"] == self.binding,
            "archive_cursor_binding",
        )
        require(
            reader.read("stream-plan.json", self.binding, len(plan_body)) == plan_body,
            "archive_plan_readback",
        )
        self.positions = object_row(self.state["partitions"])
        require(
            set(self.positions) == {str(i) for i in range(self.count)},
            "archive_cursor_partitions",
        )
        for partition in range(self.count):
            position = object_row(self.positions[str(partition)])
            require(
                set(position) == {"next", "start", "receipt_sha256"}
                and type(position["next"]) is int
                and type(position["start"]) is int
                and 0 <= position["start"] <= position["next"],
                "archive_cursor_shape",
            )
            if position["next"]:
                self.verify_receipt(
                    partition,
                    cast(int, position["start"]),
                    expected=cast(str, position["receipt_sha256"]),
                    end=cast(int, position["next"]),
                )
            else:
                require(position["receipt_sha256"] is None, "archive_cursor_shape")

    def next_offset(self, partition: int) -> int:
        return cast(int, object_row(self.positions[str(partition)])["next"])

    @staticmethod
    def receipt_key(partition: int, start: int) -> str:
        return f"receipts/p{partition:02d}/{start:020d}.json"

    def verify_receipt(
        self,
        partition: int,
        start: int,
        *,
        expected: str | None = None,
        end: int | None = None,
    ) -> tuple[Row, bytes] | None:
        body = self.reader.lookup(self.receipt_key(partition, start))
        if body is None:
            require(expected is None, "archive_receipt_missing")
            return None
        require(
            len(body) <= 65536 and (expected is None or digest(body) == expected),
            "archive_receipt_hash",
        )
        receipt = object_row(json.loads(body))
        require(
            set(receipt)
            == {
                "format_version",
                "plan_sha256",
                "partition",
                "start",
                "next",
                "segment_key",
                "segment_sha256",
                "segment_bytes",
                "previous_sha256",
            },
            "archive_receipt_shape",
        )
        require(
            receipt["format_version"] == "continuous-archive-segment-v1"
            and receipt["plan_sha256"] == self.binding
            and receipt["partition"] == partition
            and receipt["start"] == start
            and type(receipt["next"]) is int
            and start < receipt["next"] <= start + MAX_RECORDS
            and (end is None or receipt["next"] == end),
            "archive_receipt_binding",
        )
        length = receipt["segment_bytes"]
        require(
            type(length) is int and 0 < length <= MAX_SEGMENT,
            "archive_segment_bytes",
        )
        data = self.reader.read(
            cast(str, receipt["segment_key"]),
            cast(str, receipt["segment_sha256"]),
            cast(int, length),
        )
        rows = segment_rows(data)
        require(
            len(rows) == cast(int, receipt["next"]) - start, "archive_receipt_count"
        )
        source = object_row(self.plan["source"])
        for index, row in enumerate(rows):
            require(
                row["partition"] == partition
                and row["offset"] == start + index
                and all(row[key] == value for key, value in source.items()),
                "archive_receipt_source",
            )
        return receipt, data

    def publish(self, partition: int, rows: Sequence[Mapping[str, object]]) -> int:
        require(str(partition) in self.positions and bool(rows), "archive_partition")
        position = object_row(self.positions[str(partition)])
        start = self.next_offset(partition)
        require(rows[0]["offset"] == start, "archive_offset_gap")
        existing = self.verify_receipt(partition, start)
        if existing is not None:
            receipt, prior_data = existing
            take = cast(int, receipt["next"]) - start
            if len(rows) < take:
                return 0
            data = segment_body(rows[:take])
            require(
                data == prior_data
                and receipt["previous_sha256"] == position["receipt_sha256"],
                "archive_retry_conflict",
            )
        else:
            take = len(rows)
            data = segment_body(rows)
            key = f"segments/p{partition:02d}/{start:020d}-{start + take:020d}.jsonl"
            self.writer.create(key, data)
            require(
                self.reader.read(key, digest(data), len(data)) == data,
                "archive_segment_readback",
            )
            receipt = {
                "format_version": "continuous-archive-segment-v1",
                "plan_sha256": self.binding,
                "partition": partition,
                "start": start,
                "next": start + take,
                "segment_key": key,
                "segment_sha256": digest(data),
                "segment_bytes": len(data),
                "previous_sha256": position["receipt_sha256"],
            }
            self.writer.create(self.receipt_key(partition, start), canonical(receipt))
        receipt_body = canonical(receipt)
        self.verify_receipt(
            partition, start, expected=digest(receipt_body), end=start + take
        )
        self.positions[str(partition)] = {
            "next": start + take,
            "start": start,
            "receipt_sha256": digest(receipt_body),
        }
        durable_cursor(self.path, self.state)
        return take
