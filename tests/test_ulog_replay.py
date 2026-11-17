"""Recorded flights as virtual vehicles (ADR-0060) on authored ULog bytes."""

import struct
from hashlib import sha256
from pathlib import Path

from ulog_binary import FIRMWARE_COMMIT, header, info, packet

from runtime.continuous.live_reconcile import ledger_check
from telemetry.conversion_contract import json_line, object_value
from telemetry.fleet_runtime import (
    FLEET_PROFILE,
    FleetRuntime,
)
from telemetry.live_event import event_bytes, make_event, read_event
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


def test_late_velocity_and_state_keep_unknown_until_observed(tmp_path: Path) -> None:
    velocity = (
        "vehicle_local_position:uint64_t timestamp;float vx;float vy;float vz;"
        "uint8_t[4] _padding0;"
    )
    flight = _log(
        _topic(GPS, 1),
        _topic(STATUS, 2),
        _topic(velocity, 3),
        _gps(1_000_000, 10),
        packet("D", struct.pack("<HQfff4x", 3, 1_000_001, 0.0, 0.0, 0.0)),
        _gps(1_200_000, 11),
        _status(1_500_000, 1),
        _gps(2_000_000, 12),
        _status(3_000_000, 2),
        _gps(3_000_000, 13),
    )
    replay = plan(_write(tmp_path, flight))
    scope = replay.declaration(2)
    fleet = _fleet()
    values = []
    for seq, p in enumerate(replay.packets):
        row = make_event("fleet-test", scope, p.message, p.fields, EPOCH, seq, seq)
        fact = fleet.accept(read_event(event_bytes(row)))
        if fact is not None:
            position = object_value(fact["position"])
            state = object_value(object_value(fact["state"])["values"])
            values.append((position["ground_speed_m_s"], state["armed"]))
    assert values == [(None, None), (0.0, None), (0.0, False), (0.0, True)]

    # A retained v1 capture has no mapping extension and sent ACTIVE heartbeats.
    legacy = dict(scope)
    del legacy["mapping_version"], legacy["velocity_from_boot_ms"]
    previous = _fleet()
    for seq, p in enumerate(replay.packets):
        fields = dict(p.fields)
        if p.message == "HEARTBEAT":
            fields["system_status"] = 4
        row = make_event("fleet-test", legacy, p.message, fields, EPOCH, seq, seq)
        assert read_event(event_bytes(row))["source"] == legacy
        fact = previous.accept(row)
        if fact is not None:
            assert object_value(fact["position"])["ground_speed_m_s"] == 0.0
            assert object_value(object_value(fact["state"])["values"])["armed"] is False
            break
    else:
        raise AssertionError("Expected a legacy position")


def test_each_player_needs_its_own_ledger_including_without_gps(tmp_path: Path) -> None:
    native = {"time_boot_ms": 1000}
    ledger = json_line(
        {"measurement_id": "id", "native_sha256": sha256(json_line(native)).hexdigest()}
    )
    events: list[dict[str, object]] = [
        {"source": {"vehicle": name}, "measurement_id": identity, "native": native}
        for name, identity in (("a", "id"), ("b", "id"), ("no-gps", None))
    ]
    declared = {"a", "b", "no-gps"}
    (tmp_path / "a.ledger.jsonl").write_bytes(ledger)
    (tmp_path / "no-gps.ledger.jsonl").touch()
    rows = ledger_check(tmp_path, events, declared)
    assert object_value(rows["a"])["equal"] is True
    assert object_value(rows["no-gps"])["equal"] is True
    assert object_value(rows["b"])["equal"] is False
    assert object_value(rows["b"])["ledger_present"] is False
    (tmp_path / "b.ledger.jsonl").write_bytes(ledger)
    assert all(
        object_value(r)["equal"]
        for r in ledger_check(tmp_path, events, declared).values()
    )
    (tmp_path / "no-gps.ledger.jsonl").unlink()
    rows = ledger_check(tmp_path, events, {"a", "no-gps", "absent"})
    assert all(
        not object_value(rows[name])["equal"] for name in ("b", "no-gps", "absent")
    )


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
