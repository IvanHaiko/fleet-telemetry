"""Checks for the F09 coverage report's reconciliation boundaries."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from telemetry.conversion_contract import object_value

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "f09_coverage", ROOT / "scripts/report-f09-coverage.py"
)
assert spec and spec.loader
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def test_gps_reconciles_counts_and_refuses_changed_data(tmp_path: Path) -> None:
    rows = [
        {
            "event_id": "a",
            "source_ordinal": 0,
            "fix_type": 3,
            "latitude_deg": 1,
            "longitude_deg": 2,
            "ground_speed_m_s": None,
            "gps_utc": None,
        },
        {
            "event_id": "b",
            "source_ordinal": 1,
            "fix_type": 4,
            "latitude_deg": None,
            "longitude_deg": None,
            "ground_speed_m_s": 0,
            "gps_utc": "present",
        },
    ]
    data = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    (tmp_path / "gps.jsonl").write_bytes(data)
    write_json(
        tmp_path / "manifest.json",
        {
            "profile": "f09-gps-research-v1",
            "source_id": report.F09_SOURCE_ID,
            "rows_sha256": digest(data)[7:],
            "records": 2,
            "valid_positions": 1,
            "valid_ground_speed": 1,
            "gps_utc_nonzero": 1,
        },
    )
    result = report.gps_summary(tmp_path)
    assert result["fix_counts"] == {"3": 1, "4": 1}
    assert result["valid_ground_speed"] == 1
    (tmp_path / "gps.jsonl").write_bytes(data + b" ")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        report.gps_summary(tmp_path)


def test_battery_rejections_must_cover_original_ordinals_once(tmp_path: Path) -> None:
    events = b""
    rejection = {
        "source_record_index": 0,
        "source_stream": "battery_status:0",
        "reason_code": "invalid_unit_value",
    }
    data = (json.dumps(rejection) + "\n").encode()
    (tmp_path / "events.jsonl").write_bytes(events)
    (tmp_path / "rejections.jsonl").write_bytes(data)
    manifest = {
        "source_log_id": report.F09_SOURCE_ID,
        "normalization_version": "ulog-battery-f09-research-v1",
        "source_stream": "battery_status:0",
        "artifacts": {
            "events.jsonl": {"sha256": digest(events)},
            "rejections.jsonl": {"sha256": digest(data)},
        },
        "counts": {"source_records": 1, "admitted_records": 0, "rejected_records": 1},
        "rejection_reasons": {"invalid_unit_value": 1},
    }
    write_json(tmp_path / "run-manifest.json", manifest)
    assert report.battery_summary(tmp_path)["rejected_records"] == 1
    rejection["source_record_index"] = 1
    changed = (json.dumps(rejection) + "\n").encode()
    (tmp_path / "rejections.jsonl").write_bytes(changed)
    manifest["artifacts"]["rejections.jsonl"]["sha256"] = digest(changed)
    write_json(tmp_path / "run-manifest.json", manifest)
    with pytest.raises(ValueError, match="battery_reconciliation_mismatch"):
        report.battery_summary(tmp_path)
    with pytest.raises(ValueError, match="battery_replay_not_distinct"):
        report.compare_battery_replays(tmp_path, tmp_path)


def test_sql_row_reconciliation_detects_typed_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = {
        "event_id": "a",
        "source_ordinal": 0,
        "ground_speed_m_s": 4.0,
        "gps_utc": None,
    }
    raw = json.dumps(original, separators=(",", ":")).encode()
    (tmp_path / "gps.jsonl").write_bytes(raw + b"\n")
    write_json(tmp_path / "manifest.json", {"rows_sha256": digest(raw + b"\n")[7:]})
    sql_row = {**original, "row_json": raw.decode()}
    monkeypatch.setattr(
        report, "_request", lambda *args, **kwargs: json.dumps(sql_row).encode() + b"\n"
    )
    report.reconcile_gps_rows(None, tmp_path)
    sql_row["ground_speed_m_s"] = 5.0
    with pytest.raises(ValueError, match="gps_sql_typed_mismatch"):
        report.reconcile_gps_rows(None, tmp_path)


def test_battery_semantic_digest_ignores_delivery_but_detects_measurement_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    event: dict[str, object] = {key: None for key in report.SEMANTIC_FIELDS}
    event.update(
        {
            "event_id": "event-1",
            "source_record_index": 0,
            "payload": {"voltage_v": 12.0, "current_a": 1.0, "remaining_fraction": 0.5},
            "delivery": {"dataset_run_id": "first"},
        }
    )
    monkeypatch.setattr(report, "read_battery_event", lambda line: json.loads(line))

    def make_run(name: str) -> Path:
        directory = tmp_path / name
        directory.mkdir()
        data = (json.dumps(event) + "\n").encode()
        (directory / "events.jsonl").write_bytes(data)
        (directory / "rejections.jsonl").write_bytes(b"")
        write_json(
            directory / "run-manifest.json",
            {
                "source_log_id": report.F09_SOURCE_ID,
                "normalization_version": "ulog-battery-f09-research-v1",
                "source_stream": "battery_status:0",
                "artifacts": {
                    "events.jsonl": {"sha256": digest(data)},
                    "rejections.jsonl": {"sha256": digest(b"")},
                },
                "counts": {
                    "source_records": 1,
                    "admitted_records": 1,
                    "rejected_records": 0,
                },
                "rejection_reasons": {},
            },
        )
        return directory

    first = report.battery_summary(make_run("first"))
    event["delivery"] = {"dataset_run_id": "second"}
    second = report.battery_summary(make_run("second"))
    assert first == second
    object_value(event["payload"])["current_a"] = 2.0
    changed = report.battery_summary(make_run("changed"))
    assert first["semantic_sha256"] != changed["semantic_sha256"]
