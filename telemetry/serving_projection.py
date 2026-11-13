"""Finite, read-only projection of freshly verified synthetic battery archives."""

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from telemetry.archive_documents import document
from telemetry.archive_graph import GraphReader, verify_catalog
from telemetry.archive_interfaces import ReadStore
from telemetry.archive_lineage import matches, registrations
from telemetry.conversion_contract import SEMANTIC_FIELDS

PROJECTION_VERSION = "serving-battery-exact6-v1"
_SCOPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", re.ASCII)
_PAYLOAD = ("voltage_v", "current_a", "remaining_fraction")


@dataclass(frozen=True)
class ServingScope:
    """Caller-selected target namespace, independent of original delivery."""

    dataset_run_id: str
    pipeline_version: str


@dataclass(frozen=True)
class ServingRow:
    """Immutable exact-decimal measurement with its original archive lineage."""

    dataset_run_id: str
    pipeline_version: str
    event_id: str
    vehicle_id: str
    source_timestamp: str
    voltage_v: str
    current_a: str | None
    remaining_fraction: str | None
    quality_flags: tuple[str, ...]
    semantic_json: str
    source_dataset_run_id: str
    source_job_sha256: str
    archive_descriptor_sha256: str


@dataclass(frozen=True)
class ServingBatch:
    """All projected rows, returned only after every row passes the profile."""

    scope: ServingScope
    archive_descriptor_sha256: str
    rows: tuple[ServingRow, ...]


class ServingError(ValueError):
    """Fixed diagnostic category and field; projection never echoes input."""

    def __init__(self, category: str, field: str) -> None:
        super().__init__(category)
        self.category = category
        self.field = field


def _decimal(value: object, field: str) -> str | None:
    if value is None:
        return None
    number = Decimal(str(cast(int | float, value)))
    numerator, denominator = number.as_integer_ratio()
    scaled, remainder = divmod(numerator * 1_000_000, denominator)
    if remainder:
        raise ServingError("precision_loss", field)
    if abs(scaled) > 999999999999999999:
        raise ServingError("decimal_overflow", field)
    sign = "-" if scaled < 0 else ""
    whole, fraction = divmod(abs(scaled), 1_000_000)
    return f"{sign}{whole}.{fraction:06d}"


def _semantic_json(value: object) -> str:
    """Encode recognized values with context-independent decimal spelling."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)):
        number = Decimal(str(value))
        if number.is_zero():
            return "0"
        text = format(number, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        return (
            "{"
            + ",".join(
                json.dumps(key, ensure_ascii=False) + ":" + _semantic_json(mapping[key])
                for key in sorted(mapping)
            )
            + "}"
        )
    # The canonical reader supplies only JSON arrays in the remaining case.
    sequence = cast(list[object], value)
    return "[" + ",".join(_semantic_json(item) for item in sequence) + "]"


def project_archive(
    descriptor: bytes,
    expected_sha256: str,
    store: ReadStore,
    scope: ServingScope,
) -> ServingBatch:
    """Freshly verify the whole archive and atomically project its unique events."""
    if type(scope) is not ServingScope or any(
        type(value) is not str or _SCOPE.fullmatch(value) is None
        for value in (scope.dataset_run_id, scope.pipeline_version)
    ):
        raise ServingError("invalid_scope", "scope")
    archive = verify_catalog(descriptor, expected_sha256, store)
    # Authenticate this fresh read against the verified descriptor before using
    # catalog roles; original source bytes remain evidence, never job candidates.
    catalog = document(
        GraphReader(store).read(archive.descriptor["catalog"], "catalog"), "catalog"
    )
    jobs = registrations(
        cast(list[dict[str, object]], catalog["lineage"]), archive.blobs
    )
    rows: list[ServingRow] = []
    for event in sorted(
        archive.measurements, key=lambda item: cast(str, item["event_id"])
    ):
        admitted = [job for job in jobs if matches(event, job)]
        if len(admitted) != 1:
            raise ServingError("lineage_mismatch", "registration")
        job = admitted[0]
        payload = cast(dict[str, object], event["payload"])
        numbers = {field: _decimal(payload[field], field) for field in _PAYLOAD}
        flags = tuple(sorted(cast(list[str], event["quality_flags"])))
        semantic = {field: event[field] for field in SEMANTIC_FIELDS}
        semantic["quality_flags"] = list(flags)
        rows.append(
            ServingRow(
                dataset_run_id=scope.dataset_run_id,
                pipeline_version=scope.pipeline_version,
                event_id=cast(str, event["event_id"]),
                vehicle_id=cast(str, event["vehicle_id"]),
                source_timestamp=cast(str, event["source_timestamp"]),
                voltage_v=cast(str, numbers["voltage_v"]),
                current_a=numbers["current_a"],
                remaining_fraction=numbers["remaining_fraction"],
                quality_flags=flags,
                semantic_json=_semantic_json(semantic),
                source_dataset_run_id=cast(str, job.delivery["dataset_run_id"]),
                source_job_sha256=job.job_hash,
                archive_descriptor_sha256=expected_sha256,
            )
        )
    return ServingBatch(scope, expected_sha256, tuple(rows))
