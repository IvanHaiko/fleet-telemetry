"""Combined inspection must not turn one stream's unknowns into another's facts."""

from pathlib import Path
from typing import cast

import pytest

pytest.importorskip(
    "pyulog", reason="Install the pinned ulog extra for recording tests."
)

from runtime.flight_analytics.recording import combine, connect
from runtime.flight_analytics.state import project
from runtime.flight_analytics.state_time import Gap
from telemetry.conversion_contract import object_value
from telemetry.models import ULogBatteryEnvelope
from ulog_integrity import F09_SOURCE_ID


def battery(ordinal: int, timestamp: int) -> ULogBatteryEnvelope:
    # Only the adapter-checked boundary fields consumed by combine are needed.
    return cast(
        ULogBatteryEnvelope,
        {
            "event_id": f"battery-{ordinal}",
            "source_record_index": ordinal,
            "source_log_id": F09_SOURCE_ID,
            "source_time": {
                "clock_basis": "boot_relative",
                "timestamp_kind": "publication",
                "native_timestamp_us": timestamp,
            },
            "payload": {
                "voltage_v": 12.0,
                "current_a": None,
                "remaining_fraction": 0.5,
            },
        },
    )


def inputs() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    gps: list[dict[str, object]] = [
        {"source_ordinal": i, "native_timestamp_us": t, "event_id": f"gps-{i}"}
        for i, t in enumerate((99, 100, 150, 250, 300, 401))
    ]
    states: list[dict[str, object]] = []
    for ordinal, timestamp in enumerate((100, 300)):
        states.extend(
            (
                project(
                    "vehicle_land_detected",
                    ordinal,
                    {
                        "timestamp": timestamp,
                        "landed": ordinal,
                        "ground_contact": 0,
                        "maybe_landed": 0,
                    },
                ),
                project(
                    "vehicle_status",
                    ordinal,
                    {
                        "timestamp": timestamp,
                        "arming_state": 2,
                        "nav_state": 255,
                        "failsafe": 0,
                    },
                ),
            )
        )
    return gps, states


def test_combination_preserves_separate_unknowns_values_and_identity() -> None:
    gps, states = inputs()
    events = [battery(0, 100), battery(2, 300)]
    rows = combine(gps, states, events, 3, [Gap(250, 300)], 100)
    battery_rows = [object_value(row["battery"]) for row in rows]
    land_rows = [
        object_value(object_value(row["states"])["vehicle_land_detected"])
        for row in rows
    ]
    assert [row["status"] for row in battery_rows] == [
        "before_first",
        "matched",
        "rejection_gap",
        "rejection_gap",
        "matched",
        "stale",
    ]
    assert [row["status"] for row in land_rows] == [
        "before_first",
        "matched",
        "matched",
        "recording_gap",
        "matched",
        "stale",
    ]
    for row in (*battery_rows, *land_rows):
        if row["status"] != "matched":
            assert row["values"] is row["event_id"] is row["age_us"] is None
    assert battery_rows[1]["event_id"] == "battery-0"
    assert object_value(battery_rows[1]["values"])["current_a"] is None
    assert land_rows[2]["age_us"] == 50
    assert land_rows[4]["event_id"] == states[2]["event_id"]
    assert object_value(land_rows[4]["values"])["landed"] == 1
    assert combine(gps, states, events, 3, [Gap(250, 300)], 100) == rows


def test_conflicting_inputs_and_invalid_age_are_refused() -> None:
    gps, states = inputs()
    events = [battery(0, 100), battery(2, 300)]
    with pytest.raises(ValueError, match="inspection_duplicate_identity"):
        combine(gps, states, events * 2, 3, [], 100)
    with pytest.raises(ValueError, match="inspection_gps_ordinals"):
        combine(gps[1:], states, events, 3, [], 100)
    with pytest.raises(ValueError, match="inspection_age_limit"):
        combine(gps, states, events, 3, [], True)


def test_existing_output_and_invalid_age_refuse_without_touching_source(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "retained.txt"
    marker.write_text("retain", encoding="utf-8")
    with pytest.raises(ValueError, match="output_exists"):
        connect(tmp_path / "absent-job.json", tmp_path, 1_000_000)
    with pytest.raises(ValueError, match="inspection_age_limit"):
        connect(tmp_path / "absent-job.json", tmp_path / "unused", -1)
    assert marker.read_text(encoding="utf-8") == "retain"
    assert not (tmp_path / "unused").exists()
    synthetic_job = Path(__file__).parent / "fixtures/synthetic-conversion-job.json"
    with pytest.raises(ValueError, match="unsupported_recording_profile"):
        connect(synthetic_job, tmp_path / "unsupported", 1_000_000)
    assert not (tmp_path / "unsupported").exists()
