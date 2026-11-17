"""Recorded flights as virtual vehicles (ADR-0060) on authored ULog bytes."""

import struct
from pathlib import Path

from ulog_binary import FIRMWARE_COMMIT, header, info, packet

from telemetry.conversion_contract import object_value
from telemetry.fleet_runtime import (
    FLEET_PROFILE,
    FleetRuntime,
)
from telemetry.live_event import make_event
from telemetry.ulog_replay import plan

GPS = "vehicle_gps_position:uint64_t timestamp;int32_t lat;int32_t lon;int32_t alt;"
STATUS = "vehicle_status:uint64_t timestamp;uint8_t arming_state;uint8_t[7] _padding0;"
BATTERY = (
    "battery_status:uint64_t timestamp;float voltage_v;float current_a;float remaining;"
    "uint8_t[4] _padding0;"
)
EPOCH = "0" * 32


def _log(*frames: bytes) -> bytes:
    prefix = header() + packet("B", bytes(40))
    prefix += info("char[40]", "ver_sw", FIRMWARE_COMMIT.encode("ascii"))
    return prefix + b"".join(frames)


def _topic(text: str, msg_id: int) -> bytes:
    name = text.partition(":")[0]
    return packet("F", text.encode("ascii")) + packet(
        "A", struct.pack("<BH", 0, msg_id) + name.encode("ascii")
    )


def _gps(stamp: int, lat: int) -> bytes:
    return packet("D", struct.pack("<HQiii", 1, stamp, lat, 85_000_000, 500_000))


def _status(stamp: int, code: int) -> bytes:
    return packet("D", struct.pack("<HQB7x", 2, stamp, code))


def _battery(stamp: int) -> bytes:
    return packet("D", struct.pack("<HQfff4x", 3, stamp, 15.2, 3.5, 0.75))


def _write(tmp_path: Path, data: bytes) -> Path:
    path = tmp_path / "flight.ulg"
    path.write_bytes(data)
    return path


def _fleet() -> FleetRuntime:
    return FleetRuntime(
        {
            "profile": FLEET_PROFILE,
            "run_id": "fleet-test",
            "max_receipt_age_ms": 3000,
            "max_vehicles": 8,
        }
    )


def test_int32_gps_without_battery_plays_with_battery_unknown(tmp_path: Path) -> None:
    data = _log(
        _topic(GPS, 1),
        _topic(STATUS, 2),
        *(_gps(1_000_000 + i * 100_000, 473_000_000 + i) for i in range(30)),
        _status(1_000_000, 1),
        _status(2_000_000, 2),
    )
    replay = plan(_write(tmp_path, data))

    # Units come from the field signature: int32 1e-7 degrees and mm.
    assert replay.position_topic == "vehicle_gps_position"
    assert replay.available == {
        "relative_alt": False,
        "velocity": False,
        "battery": False,
        "armed": True,
        "mode": False,
    }
    positions = [p for p in replay.packets if p.message == "GLOBAL_POSITION_INT"]
    # One position per 200 ms of native time, first sample of each period.
    assert [p.fields["time_boot_ms"] for p in positions] == [
        1000 + 200 * i for i in range(15)
    ]
    assert positions[0].fields["lat"] == 473_000_000
    assert positions[0].fields["alt"] == 500_000
    battery = [p for p in replay.packets if p.message == "SYS_STATUS"]
    assert battery and all(
        p.fields
        == {"voltage_battery": 65535, "current_battery": -1, "battery_remaining": -1}
        for p in battery
    )
    heartbeats = [
        p.fields["base_mode"] for p in replay.packets if p.message == "HEARTBEAT"
    ]
    assert heartbeats[0] == 0 and heartbeats[-1] == 128


def test_unknown_arming_code_makes_armed_unavailable(tmp_path: Path) -> None:
    # Code 3 means different things in different firmware (ADR-0057).
    data = _log(
        _topic(GPS, 1),
        _topic(STATUS, 2),
        _gps(1_000_000, 473_000_000),
        _status(1_000_000, 3),
    )
    replay = plan(_write(tmp_path, data))

    assert replay.available["armed"] is False
    assert all(
        p.fields["base_mode"] == 0 for p in replay.packets if p.message == "HEARTBEAT"
    )
    fleet = _fleet()
    scope = replay.declaration(2)
    facts = []
    for sequence, item in enumerate(replay.packets):
        event = make_event(
            "fleet-test",
            scope,
            item.message,
            item.fields,
            EPOCH,
            sequence,
            10_000 + sequence,
        )
        facts.append(fleet.accept(event))
    fact = next(f for f in facts if f is not None)
    state = object_value(fact["state"])["values"]
    # The player's heartbeat is availability, not a recorded state.
    assert state == {
        "armed": None,
        "base_mode_code": None,
        "custom_mode_code": None,
        "system_status_code": None,
    }


def test_identity_ignores_system_and_vehicles_stay_apart(tmp_path: Path) -> None:
    flight = _log(
        _topic(GPS, 1),
        _topic(STATUS, 2),
        _topic(BATTERY, 3),
        _status(1_000_000, 1),
        _battery(1_000_000),
        *(_gps(1_000_000 + i * 200_000, 473_000_000 + i) for i in range(5)),
    )
    other = _log(_topic(GPS, 1), _gps(1_000_000, 10), _gps(1_200_000, 20))
    first = plan(_write(tmp_path, flight))
    (tmp_path / "other").mkdir()
    second = plan(_write(tmp_path / "other", other))

    def ids(system: int) -> list[object]:
        scope = first.declaration(system)
        return [
            make_event("r", scope, p.message, p.fields, EPOCH, n, n)["measurement_id"]
            for n, p in enumerate(first.packets)
            if p.message == "GLOBAL_POSITION_INT"
        ]

    # Replaying the same file under another system ID keeps its identities.
    assert ids(2) == ids(7) and None not in ids(2)

    fleet = _fleet()
    sequence = 0
    facts: list[dict[str, object]] = []
    # Interleave the two vehicles; only the first file has a battery.
    for system, replay in ((2, first), (3, second)):
        scope = replay.declaration(system)
        for item in replay.packets:
            event = make_event(
                "fleet-test", scope, item.message, item.fields, EPOCH, sequence, 5_000
            )
            sequence += 1
            fact = fleet.accept(event)
            if fact is not None:
                facts.append(fact)
    by_vehicle = {
        str(f["source"]["vehicle"]): f["battery"]["values"]  # type: ignore[index]
        for f in facts
    }
    assert by_vehicle[first.vehicle] == {
        "voltage_v": 15.2,
        "current_a": 3.5,
        "remaining_fraction": 0.75,
    }
    # The second vehicle never inherits the first one's battery.
    assert by_vehicle[second.vehicle] == {
        "voltage_v": None,
        "current_a": None,
        "remaining_fraction": None,
    }
    assert fleet.vehicles == (first.vehicle, second.vehicle)
