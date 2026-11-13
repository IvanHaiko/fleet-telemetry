"""Observable boundaries of the exact-file state research projection."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest

from runtime.flight_analytics.state import (
    COUNTS,
    DEFINITIONS,
    FIRMWARE,
    PROFILE,
    prepare,
    project,
    read_prepared,
    summarize,
    validate_rows,
)
from ulog_integrity import F09_SOURCE_ID

ROOT = Path(__file__).resolve().parents[1]


def _rows() -> list[dict[str, object]]:
    return [
        project(
            stream,
            ordinal,
            {
                "timestamp": ordinal * 100,
                **(
                    {"landed": int(ordinal < 2), "ground_contact": 0, "maybe_landed": 0}
                    if stream == "vehicle_land_detected"
                    else {"arming_state": 1, "nav_state": 255, "failsafe": 0}
                ),
            },
        )
        for stream, count in COUNTS.items()
        for ordinal in range(count)
    ]


def test_state_identity_is_replay_stable_and_stream_specific() -> None:
    row = _rows()[0]
    assert row == project(
        "vehicle_land_detected",
        0,
        {
            "timestamp": 0,
            "landed": 1,
            "ground_contact": 0,
            "maybe_landed": 0,
        },
    )
    assert (
        row["event_id"]
        != project(
            "vehicle_status",
            0,
            {
                "timestamp": 0,
                "arming_state": 1,
                "nav_state": 255,
                "failsafe": 0,
            },
        )["event_id"]
    )
    assert row["arming_state"] is None


def test_state_refuses_invalid_flags_and_nonmonotonic_or_missing_records() -> None:
    with pytest.raises(ValueError, match="state_value"):
        project(
            "vehicle_land_detected",
            0,
            {
                "timestamp": 0,
                "landed": 2,
                "ground_contact": 0,
                "maybe_landed": 0,
            },
        )
    rows = _rows()
    rows[2]["native_timestamp_us"] = 0
    with pytest.raises(ValueError, match="state_order"):
        validate_rows(rows)
    with pytest.raises(ValueError, match="state_source_count"):
        validate_rows(_rows()[:-1])
    rows = _rows()
    rows[0]["event_id"] = "forged"
    with pytest.raises(ValueError, match="state_row_mismatch"):
        validate_rows(rows)


def test_record_counts_do_not_turn_into_duration_or_inferred_flight() -> None:
    result = summarize(_rows())
    streams = result["streams"]
    assert isinstance(streams, dict)
    land = streams["vehicle_land_detected"]
    assert land["record_value_counts"]["landed"] == {"0": 2335, "1": 2}
    assert land["adjacent_value_changes"]["landed"] == 1
    assert land["observed_span_us"] == 233600
    assert land["max_adjacent_gap_us"] == 100
    assert "flight_duration" not in json.dumps(result)


def test_artifact_tamper_and_existing_destination_refuse(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="output_exists"):
        prepare(tmp_path / "missing.ulg", tmp_path)
    body = b"\n".join(json.dumps(row).encode() for row in _rows())
    manifest = {
        "profile": PROFILE,
        "source_id": F09_SOURCE_ID,
        "firmware": FIRMWARE,
        "definition_sha256": DEFINITIONS,
        "records": COUNTS,
        "rows_sha256": hashlib.sha256(body).hexdigest(),
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "state.jsonl").write_bytes(body)
    assert read_prepared(tmp_path) == _rows()
    (tmp_path / "state.jsonl").write_bytes(body + b"\n")
    with pytest.raises(ValueError, match="state_artifact_mismatch"):
        read_prepared(tmp_path)


def test_sql_reconciliation_detects_duplicate_and_changed_typed_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = runpy.run_path(str(ROOT / "scripts/f09-state-gold.py"))
    reconcile = namespace["reconcile"]
    original = _rows()[0]
    stored = {**original, "row_json": json.dumps(original, separators=(",", ":"))}
    monkeypatch.setitem(
        reconcile.__globals__,
        "_request",
        lambda *a: (json.dumps(stored) + "\n" + json.dumps(stored)).encode(),
    )
    with pytest.raises(ValueError, match="state_sql_count_mismatch"):
        reconcile(None, [original])
    stored["landed"] = 0
    monkeypatch.setitem(
        reconcile.__globals__, "_request", lambda *a: json.dumps(stored).encode()
    )
    with pytest.raises(ValueError, match="state_sql_row_mismatch"):
        reconcile(None, [original])
