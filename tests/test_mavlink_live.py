"""Live observations preserve units, native identity and independent freshness."""

import pytest

from telemetry.conversion_contract import object_value
from telemetry.mavlink_live import MavlinkView


def view(epoch: str = "receiver-a") -> MavlinkView:
    result = MavlinkView("sitl-001", "declared-boot-a", 1, 1, epoch, 0.0)
    result.poll(0.0)
    return result


def position(boot: int = 1000) -> dict[str, object]:
    return {
        "time_boot_ms": boot,
        "lat": 473_982_000,
        "lon": 85_463_000,
        "alt": 490_125,
        "relative_alt": 2500,
        "vx": 300,
        "vy": 400,
        "vz": -100,
    }


def heartbeat() -> dict[str, object]:
    return {"autopilot": 12, "base_mode": 128, "custom_mode": 65536, "system_status": 4}


def test_units_sentinels_and_source_filter_do_not_invent_measurement_time() -> None:
    state = view()
    assert not state.accept("HEARTBEAT", heartbeat(), 2, 1, 0.0, 1000)
    assert state.watch.status(state.watch.links[state.vehicle], 0.0) == "unknown"
    state.accept(
        "GPS_RAW_INT", {"fix_type": 3, "time_usec": 2**64 - 1}, 1, 1, 0.0, 1000
    )
    assert state.observations["gps_fix"].source_time_raw_us == str(2**64 - 1)
    state.accept("GLOBAL_POSITION_INT", position(), 1, 1, 0.0, 1000)
    values = state.observations["position"].values
    assert values == {
        "latitude_deg": 47.3982,
        "longitude_deg": 8.5463,
        "altitude_msl_m": 490.125,
        "relative_altitude_m": 2.5,
        "ground_speed_m_s": 5.0,
        "down_speed_m_s": -1.0,
    }
    state.accept(
        "SYS_STATUS",
        {"voltage_battery": 12050, "current_battery": 425, "battery_remaining": 50},
        1,
        1,
        0.0,
        1000,
    )
    assert state.observations["battery"].values == {
        "voltage_v": 12.05,
        "current_a": 4.25,
        "remaining_fraction": 0.5,
    }
    state.accept(
        "SYS_STATUS",
        {"voltage_battery": 65535, "current_battery": -1, "battery_remaining": -1},
        1,
        1,
        0.0,
        1000,
    )
    assert all(value is None for value in state.observations["battery"].values.values())
    assert state.observations["battery"].event_id is None
    assert state.observations["battery"].boot_ms is None
    with pytest.raises(ValueError, match="mavlink_field_range"):
        state.accept(
            "SYS_STATUS",
            {"voltage_battery": 12, "current_battery": 1, "battery_remaining": 101},
            1,
            1,
            0.0,
            1000,
        )


def test_position_duplicates_conflicts_reset_and_receiver_restart_identity() -> None:
    state = view()
    state.accept("GPS_RAW_INT", {"fix_type": 3}, 1, 1, 0.0, 1000)
    state.accept("GLOBAL_POSITION_INT", position(), 1, 1, 0.0, 1000)
    assert not state.accept("GLOBAL_POSITION_INT", position(), 1, 1, 1.0, 2000)
    assert state.observations["position"].received == 0.0
    restored = view("receiver-b")
    restored.accept("GPS_RAW_INT", {"fix_type": 3}, 1, 1, 0.0, 1000)
    restored.accept("GLOBAL_POSITION_INT", position(), 1, 1, 0.0, 1000)
    assert (
        restored.observations["position"].event_id
        == state.observations["position"].event_id
    )
    assert not state.accept(
        "GLOBAL_POSITION_INT", {**position(), "alt": 1}, 1, 1, 1.0, 2000
    )
    assert state.snapshot(0.0)["gateway_ok"] is False
    assert not restored.accept("GLOBAL_POSITION_INT", position(999), 1, 1, 0.1, 1100)
    assert restored.failure == "source_clock_reset_requires_new_boot_session"


def test_heartbeat_and_measurements_expire_independently_and_pause_is_unknown() -> None:
    state = view()
    state.accept("HEARTBEAT", heartbeat(), 1, 1, 0.0, 1000)
    state.accept("GPS_RAW_INT", {"fix_type": 3}, 1, 1, 0.0, 1000)
    state.accept("GLOBAL_POSITION_INT", position(), 1, 1, 0.0, 1000)
    for tenth in range(1, 32):
        now = tenth / 10
        state.poll(now)
        state.watch.tick(now)
    assert state.snapshot(3.1)["connection"] == "lost"
    state.accept("HEARTBEAT", heartbeat(), 1, 1, 3.1, 4100)
    snapshot = state.snapshot(3.1)
    assert snapshot["connection"] == "connected"
    assert (
        object_value(object_value(snapshot["groups"])["position"])["status"] == "stale"
    )
    state.poll(4.0)
    assert state.snapshot(4.0)["connection"] == "unknown"
    assert (
        object_value(object_value(state.snapshot(4.0)["groups"])["position"])["values"]
        is None
    )
    assert not state.accept("GLOBAL_POSITION_INT", position(), 1, 1, 4.0, 5000)
    assert state.observations["position"].received is None
