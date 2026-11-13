"""Closed terminal-reference runs and immutable, archive-bound report admission."""

import base64
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from typing import cast

from runtime.clickhouse.transport import HttpConfig, HttpReader, HttpWriter
from scripts.slice_queries import Row, insert, reconcile, require
from telemetry.archive_documents import canonical, digest, document
from telemetry.archive_graph import verify_catalog
from telemetry.archive_interfaces import PublishStore, ReadStore
from telemetry.serving_projection import ServingScope, project_archive
from telemetry.serving_sink import _json_object, _read_rows, publish_archive
from telemetry_reference import (
    EndOfInput,
    Observation,
    ReferenceScope,
    calculate_windows,
)

VERSION = "sealed-battery-run-v1"
POLICY = "terminal-battery-reference-v1"
MIN_WATERMARK = -(2**63)
MAX_SEAL_BYTES = 1_048_576
METRICS = ("voltage_v", "current_a", "remaining_fraction")


def exact6(value: Fraction) -> str:
    scaled = value * 1_000_000
    require(scaled.denominator == 1, "window_precision_loss")
    require(abs(scaled.numerator) <= 999999999999999999, "window_decimal_overflow")
    whole, fraction = divmod(abs(scaled.numerator), 1_000_000)
    return ("-" if scaled < 0 else "") + f"{whole}.{fraction:06d}"


def expected_run(
    descriptor: bytes,
    expected_sha256: str,
    archive_store: ReadStore,
    scope: ServingScope,
) -> Row:
    """Derive every expected fact from a fresh authenticated archive graph."""
    archive = verify_catalog(descriptor, expected_sha256, archive_store)
    projection = project_archive(descriptor, expected_sha256, archive_store, scope)
    require(archive.descriptor["start_offset"] == 0, "unsupported_reference_interval")
    require(0 < len(archive.coverage.observations) <= 32, "reference_limit")
    require(bool(projection.rows), "empty_reference")
    event_rows: list[Row] = []
    for projected in projection.rows:
        row: Row = asdict(projected)
        row["quality_flags"] = list(projected.quality_flags)
        row["projection_version"] = "serving-battery-exact6-v1"
        event_rows.append(row)
    originals = {row.source_dataset_run_id for row in projection.rows}
    logs = {event["source_log_id"] for event in archive.measurements}
    require(len(originals) == len(logs) == 1, "mixed_reference_scope")
    times = [cast(str, event["source_timestamp"]) for event in archive.measurements]
    source_scope = ReferenceScope(
        next(iter(originals)),
        scope.pipeline_version,
        cast(str, next(iter(logs))),
        min(times),
        max(times),
    )
    wires: list[bytes] = []
    for observation in archive.coverage.observations:
        require(observation["measurement"] is not None, "unsupported_reference_record")
        wires.append(
            base64.b64decode(cast(str, observation["value_b64"]), validate=True)
        )
    result = calculate_windows(
        source_scope, [*[Observation(wire) for wire in wires], EndOfInput()]
    )
    require(result.conflict_free and bool(result.windows), "reference_refused")
    require(
        all(row.kind in {"eligible", "duplicate"} for row in result.dispositions),
        "reference_refused",
    )
    common: Row = {
        "dataset_run_id": scope.dataset_run_id,
        "pipeline_version": scope.pipeline_version,
        "archive_descriptor_sha256": expected_sha256,
    }
    dispositions: list[Row] = [
        {
            **common,
            "observation_index": row.observation_index,
            "event_id": row.event_id,
            "disposition": row.kind,
            "reason": row.reason,
            "watermark_ms": MIN_WATERMARK,
        }
        for row in result.dispositions
    ]
    windows: list[Row] = []
    for window in result.windows:
        for metric, summary in zip(
            METRICS, (window.voltage, window.current, window.remaining), strict=True
        ):
            windows.append(
                {
                    **common,
                    "vehicle_id": window.vehicle_id,
                    "start_ms": window.start_ms,
                    "end_ms": window.end_ms,
                    "metric": metric,
                    "unique_events": window.unique_events,
                    "valid_count": summary.count,
                    "value_sum": exact6(summary.total or Fraction(0)),
                }
            )
    return {
        "format_version": VERSION,
        "policy": POLICY,
        "scope": asdict(scope),
        "archive_descriptor_sha256": expected_sha256,
        "observation_count": len(wires),
        "events": event_rows,
        "dispositions": dispositions,
        "windows": windows,
    }


def fact_rows(seal: Row, name: str) -> list[Row]:
    value = seal[name]
    require(isinstance(value, list), "invalid_run_seal")
    return cast(list[Row], value)


def verify_events(reader: HttpConfig, scope: ServingScope, seal: Row) -> None:
    native = HttpReader(reader)
    native.check_schema()
    expected = {cast(str, row["event_id"]): row for row in fact_rows(seal, "events")}
    require(_read_rows(native.read(scope)) == expected, "canonical_fact_mismatch")


def reports(reader: HttpConfig, scope: ServingScope, seal: Row) -> Row:
    """Require canonical facts as well as processing facts around every report."""
    verify_events(reader, scope, seal)
    result = reconcile(
        reader, scope, fact_rows(seal, "dispositions"), fact_rows(seal, "windows")
    )
    flags = Counter(
        flag
        for row in fact_rows(seal, "events")
        for flag in cast(list[str], row["quality_flags"])
    )
    quality = cast(Row, result["quality"])
    require(
        quality["flags"]
        == [
            {"flag": flag, "measurements": count}
            for flag, count in sorted(flags.items())
        ],
        "quality_flags_mismatch",
    )
    verify_events(reader, scope, seal)
    return result


def publish_run(
    descriptor: bytes,
    expected_sha256: str,
    archive_store: ReadStore,
    scope: ServingScope,
    writer: HttpConfig,
    reader: HttpConfig,
    seal_store: PublishStore,
    *,
    batch_size: int = 2,
) -> tuple[bytes, Row]:
    """A receipt exists only after exact event and processing readback passes."""
    require(type(batch_size) is int and 1 <= batch_size <= 16, "invalid_batch_size")
    seal = expected_run(descriptor, expected_sha256, archive_store, scope)
    original_runs = {row["source_dataset_run_id"] for row in fact_rows(seal, "events")}
    require(
        scope.dataset_run_id != document(descriptor, "descriptor")["archive_run_id"]
        and scope.dataset_run_id not in original_runs,
        "replay_scope_must_be_isolated",
    )
    publish_archive(
        descriptor,
        expected_sha256,
        archive_store,
        scope,
        HttpWriter(writer),
        HttpReader(reader),
        batch_size=batch_size,
    )
    insert(writer, "slice_dispositions_v1", fact_rows(seal, "dispositions"), batch_size)
    insert(writer, "slice_windows_v1", fact_rows(seal, "windows"), batch_size)
    return seal_existing(
        descriptor, expected_sha256, archive_store, scope, reader, seal_store
    )


def seal_existing(
    descriptor: bytes,
    expected_sha256: str,
    archive_store: ReadStore,
    scope: ServingScope,
    reader: HttpConfig,
    seal_store: PublishStore,
) -> tuple[bytes, Row]:
    """Attest an existing closed scope using SELECT-only database credentials."""
    seal = expected_run(descriptor, expected_sha256, archive_store, scope)
    body = canonical(seal)
    require(len(body) <= MAX_SEAL_BYTES, "seal_limit")
    result = reports(reader, scope, seal)
    key = scope.dataset_run_id + "/" + scope.pipeline_version + "/complete.json"
    seal_store.create(key, body)
    require(seal_store.read(key, digest(body), len(body)) == body, "run_seal_readback")
    return body, result


def admitted_report(
    seal_body: bytes,
    seal_sha256: str,
    descriptor: bytes,
    descriptor_sha256: str,
    archive_store: ReadStore,
    reader: HttpConfig,
) -> Row:
    """Authenticate external trust inputs before issuing any analytical query."""
    require(
        type(seal_body) is bytes and 0 < len(seal_body) <= MAX_SEAL_BYTES,
        "invalid_run_seal",
    )
    require(digest(seal_body) == seal_sha256, "untrusted_run_seal")
    seal = _json_object(seal_body.decode("utf-8"))
    require(
        seal.get("format_version") == VERSION and seal.get("policy") == POLICY,
        "unsupported_run_seal",
    )
    selected = seal.get("scope")
    require(
        isinstance(selected, dict)
        and set(selected) == {"dataset_run_id", "pipeline_version"},
        "invalid_run_seal",
    )
    selected = cast(Row, selected)
    scope = ServingScope(
        cast(str, selected["dataset_run_id"]), cast(str, selected["pipeline_version"])
    )
    expected = expected_run(descriptor, descriptor_sha256, archive_store, scope)
    require(canonical(seal) == canonical(expected), "run_seal_content_mismatch")
    first = reports(reader, scope, seal)
    # Closed-run admission detects ordinary mutations across the query window.
    # A malicious/concurrent administrator remains outside this bounded profile.
    require(reports(reader, scope, seal) == first, "run_changed_during_report")
    return {
        "scope": asdict(scope),
        "seal_sha256": seal_sha256,
        "archive_descriptor_sha256": descriptor_sha256,
        "reports": first,
    }
