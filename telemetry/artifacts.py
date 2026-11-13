"""Prepare and reconcile complete bounded run bytes before filesystem publication."""

import importlib.metadata
import sys
from collections import Counter
from collections.abc import Mapping
from hashlib import sha256

from telemetry.conversion_contract import (
    MAX_OUTPUT_BYTES,
    PIPELINE_VERSION,
    RUN_VERSION,
    SEMANTIC_FIELDS,
    ConversionError,
    ConversionJob,
    Event,
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.local_io import read_bounded
from telemetry.models import (
    MAX_NATIVE_INTEGER,
    Rejection,
    SourceManifest,
)
from telemetry.synthetic import normalize_battery
from telemetry.ulog import normalize_ulog_battery
from telemetry.validation import (
    integer,
)
from ulog_integrity import (
    F09_MAX_INPUT_BYTES,
    F09_SOURCE_ID,
    MAX_INPUT_BYTES,
    MAX_RECORDS,
)


def _synthetic_records(
    data: bytes, manifest: SourceManifest
) -> tuple[tuple[int, Mapping[str, object]], ...]:
    spec = json_object(data)
    require_keys(
        spec,
        {"generator_version", "native_format_version", "seed", "scenario", "records"},
    )
    if (
        spec["generator_version"] != manifest.parser_version
        or spec["native_format_version"] != manifest.native_format_version
    ):
        raise ConversionError("unsupported_fixture")
    integer(
        integer_value(spec["seed"]), "seed", "invalid_record", 0, MAX_NATIVE_INTEGER
    )
    string_value(spec["scenario"])
    records = spec["records"]
    if not isinstance(records, list) or not 0 < len(records) <= MAX_RECORDS:
        raise ConversionError("invalid_record_count")
    result = []
    previous: int | None = None
    for index, value in enumerate(records):
        record = object_value(value)
        if (
            type(record.get("source_record_index")) is not int
            or record["source_record_index"] != index
        ):
            raise ConversionError("invalid_source_positions")
        timestamp = record.get("timestamp_us")
        if (
            type(timestamp) is int
            and manifest.native_timestamp_min_us
            <= timestamp
            <= manifest.native_timestamp_max_us
        ):
            if previous is not None and timestamp < previous:
                raise ConversionError("clock_discontinuity")
            previous = timestamp
        result.append((index, record))
    return tuple(result)


def _projection(event: Mapping[str, object]) -> dict[str, object]:
    return {name: event[name] for name in SEMANTIC_FIELDS}


def _rejection(value: Rejection) -> dict[str, object]:
    return {
        "reason_code": value.reason_code,
        "field": value.field,
        "source_manifest_id": value.source_manifest_id,
        "source_stream": value.source_stream,
        "source_record_index": value.source_record_index,
    }


def _outcomes(
    job: ConversionJob, data: bytes
) -> tuple[list[Event], list[dict[str, object]], dict[str, object]]:
    if (
        len(data) != job.expectation.size_bytes
        or "sha256:" + sha256(data).hexdigest() != job.expectation.source_log_id
    ):
        raise ConversionError("source_bytes_mismatch")
    inspection: dict[str, object] = {}
    if isinstance(job.manifest, SourceManifest):
        records = _synthetic_records(data, job.manifest)
    else:
        from ulog_reader import decode_ulog

        decoded = decode_ulog(data, job.expectation, job.manifest)
        records = tuple(
            (record.source_record_index, record.native_record)
            for record in decoded.records
        )
        inspection = {
            "dropout_count": decoded.inspection.dropout_count,
            "dropout_duration_ms": decoded.inspection.dropout_duration_ms,
        }
    events: list[Event] = []
    rejected = []
    identities: dict[str, bytes] = {}
    serialized_bytes = 0
    for ordinal, record in records:
        if isinstance(job.manifest, SourceManifest):
            result: Event | Rejection = normalize_battery(
                record, job.manifest, job.manifest.clock_anchor, job.delivery
            )
        else:
            result = normalize_ulog_battery(
                record, ordinal, job.manifest, job.manifest.clock_anchor, job.delivery
            )
        if isinstance(result, Rejection):
            if result.reason_code in (
                "invalid_manifest",
                "invalid_delivery",
                "invalid_time_anchor",
                "missing_time_anchor",
                "unsupported_schema",
            ):
                raise ConversionError("context_or_profile_rejected")
            safe_rejection = _rejection(result)
            serialized_bytes += len(json_line(safe_rejection))
            if serialized_bytes > MAX_OUTPUT_BYTES:
                raise ConversionError("output_budget_exceeded")
            rejected.append(safe_rejection)
            continue
        semantic = json_line(_projection(result))
        if result["event_id"] in identities:
            reason = (
                "duplicate_identity"
                if identities[result["event_id"]] == semantic
                else "identity_conflict"
            )
            raise ConversionError(reason)
        identities[result["event_id"]] = semantic
        serialized_bytes += len(json_line(result)) + len(
            json_line(
                {
                    "event_id": result["event_id"],
                    "measurement": _projection(result),
                }
            )
        )
        if serialized_bytes > MAX_OUTPUT_BYTES:
            raise ConversionError("output_budget_exceeded")
        events.append(result)
    if len(records) != len(events) + len(rejected):
        raise ConversionError("outcome_reconciliation_failed")
    return events, rejected, inspection


def prepare_run(job: ConversionJob) -> tuple[dict[str, bytes], dict[str, object]]:
    """Regenerate bounded canonical bytes without writing run artifacts."""
    limit = (
        F09_MAX_INPUT_BYTES
        if job.expectation.source_log_id == F09_SOURCE_ID
        else MAX_INPUT_BYTES
    )
    data = read_bounded(job.input_path, limit)
    events, rejected, inspection = _outcomes(job, data)
    artifacts = {
        "events.jsonl": b"".join(json_line(event) for event in events),
        "rejections.jsonl": b"".join(json_line(item) for item in rejected),
    }
    semantic = b"".join(
        json_line({"event_id": event["event_id"], "measurement": _projection(event)})
        for event in events
    )
    parser: dict[str, object] = {
        "name": "literal-records-v1",
        "python": sys.version.split()[0],
    }
    if job.mode == "ulog":
        parser = {
            "name": "pyulog",
            "version": importlib.metadata.version("pyulog"),
            "numpy": importlib.metadata.version("numpy"),
            "python": sys.version.split()[0],
        }
    manifest: dict[str, object] = {
        "run_manifest_version": RUN_VERSION,
        "pipeline_version": "bounded-converter-f09-research-v1"
        if job.expectation.source_log_id == F09_SOURCE_ID
        else PIPELINE_VERSION,
        "dataset_run_id": job.delivery.dataset_run_id,
        "status": "completed_with_rejections" if rejected else "completed",
        "job_sha256": job.config_sha256,
        "source_log_id": job.manifest.source_log_id,
        "source_bytes": len(data),
        "source_manifest_id": job.manifest.source_manifest_id,
        "source_type": job.manifest.source_type,
        "source_stream": job.manifest.source_stream,
        "normalization_version": job.manifest.normalization_version,
        "schema_version": "1.0.0",
        "semantic_projection_version": "battery-semantic-v1"
        if job.mode == "synthetic"
        else "ulog-battery-semantic-v1",
        "semantic_digest_version": "bounded-semantic-digest-v1",
        "semantic_sha256": "sha256:" + sha256(semantic).hexdigest(),
        "time_label": "synthetic-time",
        "parser": parser,
        "counts": {
            "source_records": len(events) + len(rejected),
            "admitted_records": len(events),
            "rejected_records": len(rejected),
            "unique_events": len(events),
            "duplicate_events": 0,
        },
        "rejection_reasons": dict(
            sorted(Counter(str(item["reason_code"]) for item in rejected).items())
        ),
        "artifacts": {
            name: {
                "sha256": "sha256:" + sha256(content).hexdigest(),
                "bytes": len(content),
            }
            for name, content in artifacts.items()
        },
        "source_observations": inspection,
    }
    return artifacts, manifest
