"""Reconcile protected source artifacts before interval preparation."""

import hashlib
import re
from collections import Counter
from pathlib import Path

from runtime.flight_analytics.stream_contract import (
    _RUN,
    MAX_BYTES,
    MAX_EVENTS,
    SOURCE_BYTES,
    Document,
    _check_reference,
    _integer,
    _limitations,
    _read,
    _reference,
    _rows,
    _safe_path,
    _same,
)
from telemetry.conversion_contract import (
    SEMANTIC_FIELDS,
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.models import ULogBatteryEnvelope
from telemetry.recording_stream import (
    STREAMS,
    make_event,
)
from telemetry_reader import read_battery_event
from ulog_integrity import F09_SOURCE_ID


def _verify_prepared(
    prepared: Path, source: Path
) -> tuple[
    list[Document], list[Document], list[Document], int, list[Document], Document
]:
    """Read bounded snapshots and reconcile every retained inspection section."""
    # Imports stay local: pure timeline/readback do not require the ULog parser.
    from runtime.flight_analytics.gps import (
        FIRMWARE,
        GPS_DEFINITION,
    )
    from runtime.flight_analytics.recording import PROFILE, combine
    from runtime.flight_analytics.state import (
        COUNTS,
        DEFINITIONS,
        FIELDS,
        read_prepared,
    )
    from runtime.flight_analytics.state_time import source_gaps

    inventory: Document = {}
    source_body = _read(source, SOURCE_BYTES)
    if len(source_body) != SOURCE_BYTES or (
        "sha256:" + hashlib.sha256(source_body).hexdigest() != F09_SOURCE_ID
    ):
        raise ValueError("stream_original_bytes")
    inventory["source.ulog"] = _reference(source_body)
    del source_body
    total = 0

    def artifact(relative: str, limit: int = MAX_BYTES) -> bytes:
        nonlocal total
        body = _read(prepared / relative, limit)
        total += len(body)
        if total > MAX_BYTES:
            raise ValueError("stream_prepared_byte_limit")
        inventory["prepared/" + relative] = _reference(body)
        return body

    report = json_object(artifact("recording.json", 32_000))
    gps_manifest = json_object(artifact("gps/manifest.json", 8192))
    gps_body = artifact("gps/gps.jsonl", 32_000_000)
    state_manifest = json_object(artifact("state/manifest.json", 8192))
    state_body = artifact("state/state.jsonl", 8_000_000)
    gps = _rows(gps_body, 25_000)
    states = _rows(state_body, 10_000)
    # Existing helper validates the complete state projection and pinned metadata.
    if not _same(read_prepared(_safe_path(prepared / "state")), states):
        raise ValueError("stream_state_changed")
    expected_gps: Document = {
        "profile": "f09-gps-research-v1",
        "source_id": F09_SOURCE_ID,
        "firmware": FIRMWARE,
        "gps_definition_sha256": GPS_DEFINITION,
        "stream": STREAMS[3],
        "records": 21_054,
        "valid_positions": sum(row.get("latitude_deg") is not None for row in gps),
        "valid_ground_speed": sum(
            row.get("ground_speed_m_s") is not None for row in gps
        ),
        "gps_utc_nonzero": sum(row.get("gps_utc") is not None for row in gps),
        "source_time_semantics": (
            "boot-relative; GPS UTC is not a proven sample-time mapping"
        ),
        "privacy": "restricted",
        "scope": "exact F09 source; parser/framing agreement only",
        "rows_sha256": hashlib.sha256(gps_body).hexdigest(),
    }
    if len(gps) != 21_054:
        raise ValueError("stream_gps_count")
    root = _safe_path(prepared / "battery")
    deliveries = list(root.iterdir())
    if len(deliveries) != 1:
        raise ValueError("stream_battery_delivery_count")
    delivery = deliveries[0].name
    if _RUN.fullmatch(delivery) is None or delivery in (".", ".."):
        raise ValueError("stream_battery_delivery")
    if not _safe_path(deliveries[0]).is_dir():
        raise ValueError("stream_battery_delivery")
    prefix = "battery/" + delivery + "/"
    run = json_object(artifact(prefix + "run-manifest.json", 32_000))
    battery_body = artifact(prefix + "events.jsonl", 32_000_000)
    rejections_body = artifact(prefix + "rejections.jsonl", 1_000_000)
    battery = _rows(battery_body, MAX_EVENTS)
    rejections = _rows(rejections_body, MAX_EVENTS)
    if not 0 < len(battery) <= MAX_EVENTS or len(rejections) > MAX_EVENTS:
        raise ValueError("stream_battery_count")
    artifacts = object_value(run["artifacts"])
    require_keys(artifacts, {"events.jsonl", "rejections.jsonl"})
    _check_reference(artifacts["events.jsonl"], battery_body, prefixed=True)
    _check_reference(artifacts["rejections.jsonl"], rejections_body, prefixed=True)
    expected_run: Document = {
        "run_manifest_version": "bounded-run-v1",
        "pipeline_version": "bounded-converter-f09-research-v1",
        "dataset_run_id": delivery,
        "source_log_id": F09_SOURCE_ID,
        "source_bytes": SOURCE_BYTES,
        "source_type": "ulog",
        "source_stream": STREAMS[0],
        "normalization_version": "ulog-battery-f09-research-v1",
        "schema_version": "1.0.0",
        "semantic_projection_version": "ulog-battery-semantic-v1",
        "semantic_digest_version": "bounded-semantic-digest-v1",
        "time_label": "synthetic-time",
        "status": "completed_with_rejections" if rejections else "completed",
    }
    for key, value in expected_run.items():
        if not _same(run.get(key), value):
            raise ValueError("stream_battery_profile")
    parser = object_value(run["parser"])
    require_keys(parser, {"name", "version", "numpy", "python"})
    if (parser["name"], parser["version"], parser["numpy"]) != (
        "pyulog",
        "1.2.2",
        "2.3.5",
    ):
        raise ValueError("stream_battery_parser")
    string_value(parser["python"])
    if re.fullmatch(r"sha256:[0-9a-f]{64}", string_value(run["job_sha256"])) is None:
        raise ValueError("stream_battery_job_hash")
    manifest_id = string_value(run["source_manifest_id"])
    accepted_ordinals = []
    for row in battery:
        # Frozen A validates complete F09 payload semantics and identity.
        make_event(STREAMS[0], row, delivery)
        if (
            object_value(row["delivery"])["dataset_run_id"] != delivery
            or object_value(row["provenance"])["source_manifest_id"] != manifest_id
        ):
            raise ValueError("stream_battery_delivery_scope")
        accepted_ordinals.append(integer_value(row["source_record_index"]))
    rejected_ordinals = []
    reasons: Counter[str] = Counter()
    for rejection in rejections:
        require_keys(
            rejection,
            {
                "reason_code",
                "field",
                "source_manifest_id",
                "source_stream",
                "source_record_index",
            },
        )
        if rejection["source_manifest_id"] != manifest_id or (
            rejection["source_stream"] != STREAMS[0]
        ):
            raise ValueError("stream_rejection_scope")
        reasons[string_value(rejection["reason_code"])] += 1
        string_value(rejection["field"])
        rejected_ordinals.append(_integer(rejection["source_record_index"], 0, 11729))
    source_count = len(battery) + len(rejections)
    if (
        source_count != 11_730
        or rejected_ordinals != sorted(set(rejected_ordinals))
        or sorted(accepted_ordinals + rejected_ordinals) != list(range(source_count))
    ):
        raise ValueError("stream_battery_coverage")
    expected_counts = {
        "source_records": source_count,
        "admitted_records": len(battery),
        "rejected_records": len(rejections),
        "unique_events": len(battery),
        "duplicate_events": 0,
    }
    semantic = b"".join(
        json_line(
            {
                "event_id": row["event_id"],
                "measurement": {name: row[name] for name in SEMANTIC_FIELDS},
            }
        )
        for row in battery
    )
    semantic_hash = "sha256:" + hashlib.sha256(semantic).hexdigest()
    if (
        not _same(run["counts"], expected_counts)
        or not _same(run["rejection_reasons"], dict(reasons))
        or run["semantic_sha256"] != semantic_hash
    ):
        raise ValueError("stream_battery_reconciliation")
    gaps, evidence = source_gaps(_safe_path(source), gps, states)
    dropout = evidence["dropout_count"]
    duration = evidence["dropout_duration_ms"]
    expected_gps.update(dropout_markers=dropout, dropout_duration_ms=duration)
    if not _same(gps_manifest, expected_gps):
        raise ValueError("stream_gps_manifest")
    expected_state: Document = {
        "profile": "f09-state-research-v1",
        "source_id": F09_SOURCE_ID,
        "firmware": FIRMWARE,
        "definition_sha256": DEFINITIONS,
        "records": COUNTS,
        "rows_sha256": hashlib.sha256(state_body).hexdigest(),
        "dropout_markers": dropout,
        "dropout_duration_ms": duration,
        "privacy": "restricted",
        "clock": "microseconds since system start",
    }
    if not _same(state_manifest, expected_state) or not _same(
        run["source_observations"],
        {"dropout_count": dropout, "dropout_duration_ms": duration},
    ):
        raise ValueError("stream_state_or_source_manifest")
    age = _integer(report["max_age_us"], 0, 60_000_000)
    typed_battery: list[ULogBatteryEnvelope] = []
    for row in battery:
        event = read_battery_event(json_line(row))
        if event["source_type"] != "ulog":
            raise ValueError("stream_battery_profile")
        typed_battery.append(event)
    expected_rows = combine(gps, states, typed_battery, source_count, gaps, age)
    inspection = artifact("inspection.jsonl")
    rows = _rows(inspection, 25_000)
    if not _same(rows, expected_rows):
        raise ValueError("stream_inspection_values")
    statuses: dict[str, Counter[str]] = {
        name: Counter() for name in ("battery", *FIELDS)
    }
    for row in expected_rows:
        statuses["battery"][string_value(object_value(row["battery"])["status"])] += 1
        selected = object_value(row["states"])
        for stream in FIELDS:
            status = string_value(object_value(selected[stream])["status"])
            statuses[stream][status] += 1
    expected_report: Document = {
        "profile": PROFILE,
        "status": "completed_with_quality_limits",
        "privacy": "restricted",
        "source_id": F09_SOURCE_ID,
        "vehicle_id": "f09-research-vehicle",
        "inspection_records": len(rows),
        "inspection_sha256": hashlib.sha256(inspection).hexdigest(),
        "max_age_us": age,
        "association_status_counts": {name: dict(c) for name, c in statuses.items()},
        "gps": gps_manifest,
        "state": state_manifest,
        "battery_counts": expected_counts,
        "battery_semantic_sha256": semantic_hash,
        "battery_rejection_reasons": dict(reasons),
        "original_evidence": evidence,
    }
    require_keys(report, set(expected_report) | {"limitations"})
    for key, value in expected_report.items():
        if not _same(report[key], value):
            raise ValueError("stream_recording_report")
    _limitations(report["limitations"])
    return (
        gps,
        battery,
        states,
        source_count,
        [{"start_us": gap.start_us, "end_us": gap.end_us} for gap in gaps],
        inventory,
    )
