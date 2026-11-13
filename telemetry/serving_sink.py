"""Bounded synchronous event publication with exact independent readback."""

import json
from dataclasses import asdict, dataclass
from typing import Protocol, cast

from telemetry.archive_interfaces import ReadStore
from telemetry.serving_projection import (
    PROJECTION_VERSION,
    ServingScope,
    project_archive,
)

SCHEMA_VERSION = "serving-events-v1"
MAX_BODY_BYTES = 8388608
COLUMNS = (
    "projection_version",
    "dataset_run_id",
    "pipeline_version",
    "event_id",
    "vehicle_id",
    "source_timestamp",
    "voltage_v",
    "current_a",
    "remaining_fraction",
    "quality_flags",
    "semantic_json",
    "source_dataset_run_id",
    "source_job_sha256",
    "archive_descriptor_sha256",
)


class SinkError(ValueError):
    """Safe fixed diagnostic category and field."""

    def __init__(self, category: str, field: str) -> None:
        super().__init__(category)
        self.category = category
        self.field = field


class EventWriter(Protocol):
    def write(self, body: bytes) -> None: ...


class EventReader(Protocol):
    def check_schema(self) -> None: ...
    def read(self, scope: ServingScope) -> bytes: ...


@dataclass(frozen=True)
class WriteReceipt:
    schema_version: str
    scope: ServingScope
    archive_descriptor_sha256: str
    event_count: int
    acknowledged_batches: int


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError("nonfinite")


def _json_object(line: str) -> dict[str, object]:
    value: object = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
    if not isinstance(value, dict):
        raise ValueError("object")
    return cast(dict[str, object], value)


def _read_rows(body: bytes) -> dict[str, dict[str, object]]:
    if type(body) is not bytes:
        raise SinkError("invalid_response", "rows")
    if len(body) > MAX_BODY_BYTES:
        raise SinkError("limit_exceeded", "rows")
    try:
        text = body.decode("utf-8")
        lines = text.split("\n")
        if lines[-1] == "":
            lines.pop()
        if len(lines) > 64:
            raise SinkError("limit_exceeded", "rows")
        result: dict[str, dict[str, object]] = {}
        for line in lines:
            row = _json_object(line)
            if set(row) != set(COLUMNS):
                raise ValueError("fields")
            for key, value in row.items():
                if key == "quality_flags":
                    if type(value) is not list or any(
                        type(flag) is not str for flag in cast(list[object], value)
                    ):
                        raise ValueError("flags")
                elif key in ("current_a", "remaining_fraction") and value is None:
                    continue
                elif type(value) is not str:
                    raise ValueError("string")
            event_id = cast(str, row["event_id"])
            if event_id in result and result[event_id] != row:
                raise SinkError("sink_conflict", "rows")
            result[event_id] = row
        return result
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, SinkError):
            raise
        raise SinkError("invalid_response", "rows") from None


def publish_archive(
    descriptor: bytes,
    expected_sha256: str,
    store: ReadStore,
    scope: ServingScope,
    writer: EventWriter,
    reader: EventReader,
    *,
    batch_size: int = 16,
) -> WriteReceipt:
    """Project afresh, admit schema, write once per batch, then reconcile."""
    if type(batch_size) is not int or not 1 <= batch_size <= 64:
        raise SinkError("invalid_batch_size", "batch_size")
    batch = project_archive(descriptor, expected_sha256, store, scope)
    expected: dict[str, dict[str, object]] = {}
    encoded: list[bytes] = []
    for row in sorted(batch.rows, key=lambda item: item.event_id):
        value: dict[str, object] = asdict(row)
        value["quality_flags"] = list(row.quality_flags)
        value["projection_version"] = PROJECTION_VERSION
        expected[row.event_id] = value
        encoded.append(
            (
                json.dumps(
                    value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                )
                + "\n"
            ).encode("utf-8")
        )
    if sum(map(len, encoded)) > MAX_BODY_BYTES:
        raise SinkError("limit_exceeded", "body")
    bodies = [
        b"".join(encoded[i : i + batch_size])
        for i in range(0, len(encoded), batch_size)
    ]
    acknowledged = 0
    phase = "read"
    try:
        reader.check_schema()
        phase = "write"
        for body in bodies:
            writer.write(body)
            acknowledged += 1
        phase = "read"
        actual = _read_rows(reader.read(scope))
    except PermissionError:
        raise SinkError("permission_denied", "sink") from None
    except OSError:
        category = "write_ambiguous" if phase == "write" else "sink_unavailable"
        raise SinkError(category, phase) from None
    if actual != expected:
        raise SinkError("reconciliation_failed", "rows")
    return WriteReceipt(
        SCHEMA_VERSION,
        scope,
        batch.archive_descriptor_sha256,
        len(expected),
        acknowledged,
    )
