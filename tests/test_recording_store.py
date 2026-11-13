"""Shared recording scope and missing-source projection invariants."""

import hashlib
from pathlib import Path

import pytest

pytest.importorskip(
    "pyulog", reason="Install the pinned ulog extra for recording tests."
)

from runtime.flight_analytics.f01 import PROFILE, VEHICLE, project_state
from runtime.flight_analytics.recording_store import project
from telemetry.conversion_contract import json_line
from ulog_integrity import F01_SOURCE_ID


def prepared(directory: Path, *, unknown_value: bool = False) -> None:
    directory.mkdir()
    rows = []
    for ordinal in range(77):
        state = project_state(
            "vehicle_status",
            ordinal,
            {
                "timestamp": 100 + ordinal,
                "arming_state": 1,
                "nav_state": 255,
                "failsafe": 0,
            },
        )
        land = project_state(
            "vehicle_land_detected",
            0,
            {
                "timestamp": 100,
                "landed": 1,
                "ground_contact": 0,
                "maybe_landed": 0,
            },
        )
        rows.append(
            {
                "observation": {
                    "event_id": state["event_id"],
                    "source_stream": "vehicle_status:0",
                    "source_ordinal": ordinal,
                    "native_timestamp_us": 100 + ordinal,
                },
                "gps": None,
                "battery": {
                    "status": "missing_stream",
                    "event_id": None,
                    "age_us": None,
                    "values": {"voltage_v": 12} if unknown_value else None,
                },
                "states": {
                    "vehicle_status": {
                        "status": "matched",
                        "event_id": state["event_id"],
                        "age_us": 0,
                        "values": {"arming_state": 1, "nav_state": 255, "failsafe": 0},
                    },
                    "vehicle_land_detected": {
                        "status": "matched",
                        "event_id": land["event_id"],
                        "age_us": ordinal,
                        "values": {"landed": 1, "ground_contact": 0, "maybe_landed": 0},
                    },
                },
            }
        )
    body = b"".join(json_line(row) for row in rows)
    (directory / "inspection.jsonl").write_bytes(body)
    (directory / "recording.json").write_bytes(
        json_line(
            {
                "profile": PROFILE,
                "source_id": F01_SOURCE_ID,
                "vehicle_id": VEHICLE,
                "inspection_records": len(rows),
                "max_age_us": 1_000_000,
                "inspection_sha256": hashlib.sha256(body).hexdigest(),
                "capabilities": {
                    "gps": "empty_stream",
                    "battery": "missing_stream",
                    "state": "recorded",
                },
            }
        )
    )


def test_shared_scope_is_replay_stable_and_missing_streams_stay_null(
    tmp_path: Path,
) -> None:
    prepared(tmp_path / "first")
    prepared(tmp_path / "replay")
    registry, rows = project(tmp_path / "first")
    assert project(tmp_path / "replay") == (registry, rows)
    assert registry["source_id"] == F01_SOURCE_ID
    assert len(rows) == registry["records"] == 77
    for row in rows:
        assert row["observation_stream"] == "vehicle_status:0"
        assert row["gps_status"] == "empty_stream"
        assert row["battery_status"] == "missing_stream"
        assert all(
            row[key] is None
            for key in (
                "latitude_deg",
                "longitude_deg",
                "voltage_v",
                "current_a",
                "battery_age_us",
                "battery_event_id",
                "receiver_utc",
            )
        )
        assert row["nav_state"] == 255
        assert row["landed"] == 1


def test_unknown_values_and_changed_artifacts_refuse_before_sql(tmp_path: Path) -> None:
    prepared(tmp_path / "unknown", unknown_value=True)
    with pytest.raises(ValueError, match="inspection_unknown_value"):
        project(tmp_path / "unknown")
    prepared(tmp_path / "changed")
    path = tmp_path / "changed/inspection.jsonl"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="inspection_digest_mismatch"):
        project(tmp_path / "changed")
