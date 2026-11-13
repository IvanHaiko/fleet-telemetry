"""Native live-input identity and duplicate-safe source reconciliation."""

from pathlib import Path

import pytest

from runtime.continuous.position_sql import read_health_snapshot
from telemetry.conversion_contract import json_line
from telemetry.mavlink_position import make_fact, make_input, read_input, unique_events


def native() -> dict[str, object]:
    return {
        "time_boot_ms": 1000,
        "lat": 473982000,
        "lon": 85463000,
        "alt": 490125,
        "relative_alt": 2500,
        "vx": 300,
        "vy": 400,
        "vz": -100,
    }


def test_health_rename_gap_does_not_renew_receipt_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "status.json"
    assert read_health_snapshot(path) is None
    path.write_bytes(b'{"collector_written_ms":100}')
    assert read_health_snapshot(path) == {"collector_written_ms": 100}

    def missing_after_probe(*args: object) -> bytes:
        raise FileNotFoundError

    # The file exists at stat time but disappears before open on the bind mount.
    monkeypatch.setattr(Path, "open", missing_after_probe)
    assert read_health_snapshot(path) is None


def test_wire_profile_keeps_native_time_and_flink_conversion_receipts() -> None:
    event = make_input(native(), "declared-boot", 1, 1)
    body = json_line(event)
    assert read_input(body) == event
    fact = make_fact(body, str(event["event_id"]).encode(), "live.input", 0, 7)
    assert fact["input_offset"] == 7
    assert fact["payload"] == {
        "latitude_deg": 47.3982,
        "longitude_deg": 8.5463,
        "altitude_msl_m": 490.125,
        "relative_altitude_m": 2.5,
        "ground_speed_m_s": 5.0,
        "down_speed_m_s": -1.0,
    }
    assert event["source_time_kind"] == "boot_timestamp_clock_unverified"
    assert "source_timestamp" not in event
    with pytest.raises(ValueError, match="position_source_coordinate"):
        make_fact(body, b"wrong-key", "live.input", 0, 0)
    key = str(event["event_id"]).encode()
    with pytest.raises(ValueError, match="position_source_coordinate"):
        make_fact(body, key, "live.input", 0, 32)
    streamed = make_fact(body, key, "live.input", 0, 32, offset_limit=3600)
    assert streamed["input_offset"] == 32
    assert streamed["event"] == fact["event"]
    assert streamed["payload"] == fact["payload"]
    with pytest.raises(ValueError, match="position_source_coordinate"):
        make_fact(body, key, "live.input", 0, 3600, offset_limit=3600)


def test_repeated_measurements_do_not_hide_competing_native_content() -> None:
    event = make_input(native(), "declared-boot", 1, 1)
    assert len(unique_events([event, event])) == 1
    changed = make_input({**native(), "lat": 1}, "declared-boot", 1, 1)
    assert event["event_id"] == changed["event_id"]
    with pytest.raises(ValueError, match="competing_position_content"):
        unique_events([event, changed])
    assert (
        make_input(native(), "another-source-boot", 1, 1)["event_id"]
        != event["event_id"]
    )
    with pytest.raises(ValueError):
        read_input(json_line({**event, "source_time_kind": "utc"}))
    with pytest.raises(ValueError, match="mavlink_field_range"):
        make_input({**native(), "lat": True}, "declared-boot", 1, 1)
