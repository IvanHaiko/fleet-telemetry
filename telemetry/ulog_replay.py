"""A recorded ULog flight as the MAVLink stream of a virtual PX4 (ADR-0060).

Pure planning, no network: the file becomes a deterministic, time-ordered
list of MAVLink message fields that a player sends at the recording's pace.

- Structure is checked by the offline inventory's policy (complete file,
  within the ADR-0058 admitted limits); only the fields of the signature table
  below are decoded.
- A capability is used when its topic has instance 0 with samples and exactly
  one known field signature. Field names and types identify the units.
- What cannot be derived is declared unavailable and sent as a MAVLink
  sentinel or zero; the downstream runtime shows it as null, never as a value.
- Enumerations whose meaning changed between firmware versions are not
  interpreted: `arming_state` codes 1 and 2 (disarmed, armed in every
  reviewed firmware) give the armed flag only when the replayed interval
  holds no other code, and the navigation mode is not sent.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from telemetry.recordings import ADMITTED_MAX_INPUT_BYTES, ADMITTED_MAX_RECORDS
from telemetry.ulog_inventory import inventory
from telemetry.ulog_samples import Samples, Topic, Value, decode
from ulog_integrity import _MAGIC, InputIntegrityError

PLAN_VERSION = "ulog-replay-plan-v1"
POSITION_PERIOD_US = 200_000
SLOW_PERIOD_US = 1_000_000
PX4_AUTOPILOT = 12
MAV_TYPE_GENERIC = 0
MAV_STATE_ACTIVE = 4
MAV_MODE_FLAG_SAFETY_ARMED = 128
ARMING_DISARMED, ARMING_ARMED = 1, 2
_INT32 = 2**31


@dataclass(frozen=True)
class PositionSignature:
    """Field names and types that fix a position's units."""

    topic: str
    fields: tuple[tuple[str, str], tuple[str, str], tuple[str, str]]

    @property
    def scaled(self) -> bool:
        """int32 1e-7 degrees and millimetres; otherwise degrees and metres."""
        return self.fields[0][1] == "int32_t"


_SCALED = (("lat", "int32_t"), ("lon", "int32_t"), ("alt", "int32_t"))
_DEGREES = (
    ("latitude_deg", "double"),
    ("longitude_deg", "double"),
    ("altitude_msl_m", "double"),
)
# In order of preference: the estimate a physical PX4 sends in
# GLOBAL_POSITION_INT first, then the receiver's own fix.
_POSITION = (
    PositionSignature(
        "vehicle_global_position",
        (("lat", "double"), ("lon", "double"), ("alt", "float")),
    ),
    PositionSignature("vehicle_gps_position", _DEGREES),
    PositionSignature("sensor_gps", _DEGREES),
    PositionSignature("vehicle_gps_position", _SCALED),
    PositionSignature("sensor_gps", _SCALED),
)
_HOME = (("alt", "float"),)
_VELOCITY = (("vx", "float"), ("vy", "float"), ("vz", "float"))
_BATTERY = (("voltage_v", "float"), ("current_a", "float"), ("remaining", "float"))
_STATUS = (("arming_state", "uint8_t"),)


class ReplayRefused(ValueError):
    """The file cannot be replayed; the reason is a fixed category."""


@dataclass(frozen=True)
class Packet:
    """One MAVLink message to send at a native time of the recording."""

    native_us: int
    message: str
    fields: dict[str, int]


@dataclass(frozen=True)
class ReplayPlan:
    source_id: str
    firmware: str | None
    position_topic: str | None
    available: dict[str, bool]
    packets: tuple[Packet, ...]
    first_us: int
    last_us: int

    @property
    def digest(self) -> str:
        return self.source_id.removeprefix("sha256:")

    @property
    def vehicle(self) -> str:
        return f"ulog-{self.digest[:16]}"

    def declaration(self, system: int, component: int = 1) -> dict[str, object]:
        """The source scope the gateway admits (telemetry.live_event)."""
        return {
            "kind": "ulog-replay",
            "vehicle": self.vehicle,
            "label": "ULog " + self.digest[:8],
            "source_id": self.source_id,
            "firmware": self.firmware,
            "position_topic": self.position_topic,
            "system": system,
            "component": component,
            "available": dict(self.available),
        }

    def summary(self) -> dict[str, object]:
        """Counts and capabilities only, never values or coordinates."""
        counts: dict[str, int] = {}
        for packet in self.packets:
            counts[packet.message] = counts.get(packet.message, 0) + 1
        return {
            "format_version": PLAN_VERSION,
            "source_id": self.source_id,
            "vehicle": self.vehicle,
            "firmware": self.firmware,
            "position_topic": self.position_topic,
            "available": self.available,
            "packets": counts,
            "duration_s": round((self.last_us - self.first_us) / 1e6, 3),
        }


def _matches(topic: Topic | None, signature: tuple[tuple[str, str], ...]) -> bool:
    return (
        topic is not None
        and bool(topic.samples)
        and all(topic.kinds.get(name) == kind for name, kind in signature)
    )


def _buckets(samples: Samples, period: int) -> Iterator[tuple[int, dict[str, Value]]]:
    """First sample at or after each period boundary of native time."""
    last = None
    for stamp, values in samples:
        bucket = stamp // period
        if bucket != last:
            last = bucket
            yield stamp, values


def _latest(
    samples: Samples, stamp: int, start: int
) -> tuple[int, dict[str, Value] | None]:
    """Index cursor and the newest sample at or before `stamp`."""
    index = start
    while index + 1 < len(samples) and samples[index + 1][0] <= stamp:
        index += 1
    if not samples or samples[index][0] > stamp:
        return index, None
    return index, samples[index][1]


def _scaled(value: Value, scale: float, low: int, high: int) -> int | None:
    number = float(value)
    if not math.isfinite(number):
        return None
    result = round(number * scale)
    return result if low <= result <= high else None


def _position_fields(
    values: dict[str, Value], signature: PositionSignature
) -> tuple[int, int, int] | None:
    (lat, _), (lon, _), (alt, _) = signature.fields
    if signature.scaled:
        a, b, c = int(values[lat]), int(values[lon]), int(values[alt])
        if abs(a) > 900_000_000 or abs(b) > 1_800_000_000:
            return None
        return a, b, c
    la = _scaled(values[lat], 1e7, -900_000_000, 900_000_000)
    lo = _scaled(values[lon], 1e7, -1_800_000_000, 1_800_000_000)
    al = _scaled(values[alt], 1000, -_INT32, _INT32 - 1)
    if la is None or lo is None or al is None:
        return None
    return la, lo, al


def _positions(
    samples: Samples,
    signature: PositionSignature,
    home: Samples | None,
    velocity: Samples | None,
) -> list[Packet]:
    packets: list[Packet] = []
    home_index = velocity_index = 0
    for stamp, values in _buckets(samples, POSITION_PERIOD_US):
        scaled = _position_fields(values, signature)
        if scaled is None:
            continue
        lat, lon, alt = scaled
        relative = 0
        if home is not None:
            home_index, base = _latest(home, stamp, home_index)
            home_mm = (
                None
                if base is None
                else _scaled(base["alt"], 1000, -_INT32, _INT32 - 1)
            )
            relative = 0 if home_mm is None else alt - home_mm
            if not -_INT32 <= relative < _INT32:
                continue
        vx = vy = vz = 0
        if velocity is not None:
            velocity_index, speed = _latest(velocity, stamp, velocity_index)
            if speed is not None:
                parts = [
                    _scaled(speed[name], 100, -32768, 32767)
                    for name in ("vx", "vy", "vz")
                ]
                known = [part for part in parts if part is not None]
                if len(known) != 3:
                    continue  # out of the MAVLink range: the sample is not sent
                vx, vy, vz = known
        boot = stamp // 1000
        if packets and packets[-1].fields["time_boot_ms"] == boot:
            continue  # one position per boot millisecond: keep the first
        packets.append(
            Packet(
                stamp,
                "GLOBAL_POSITION_INT",
                {
                    "time_boot_ms": boot,
                    "lat": lat,
                    "lon": lon,
                    "alt": alt,
                    "relative_alt": relative,
                    "vx": vx,
                    "vy": vy,
                    "vz": vz,
                    "hdg": 65535,
                },
            )
        )
    return packets


def _battery(cell: dict[str, Value] | None) -> dict[str, int]:
    """SYS_STATUS battery fields; MAVLink sentinels where a value is unknown."""
    if cell is None:
        return {
            "voltage_battery": 65535,
            "current_battery": -1,
            "battery_remaining": -1,
        }
    voltage = _scaled(cell["voltage_v"], 1000, 0, 65534)
    current = _scaled(cell["current_a"], 100, 0, 32767)
    remaining = _scaled(cell["remaining"], 100, 0, 100)
    return {
        "voltage_battery": 65535 if voltage is None else voltage,
        "current_battery": -1 if current is None else current,
        "battery_remaining": -1 if remaining is None else remaining,
    }


def plan(
    path: Path, *, start_us: int | None = None, end_us: int | None = None
) -> ReplayPlan:
    """Decide what the file supports and the packets that carry it."""
    report = inventory(path)
    if report["status"] != "complete":
        raise ReplayRefused(f"structure_{report['status']}")
    file_info = report["file"]
    frames = report["frames"]
    if not isinstance(file_info, dict) or not isinstance(frames, int):
        raise ReplayRefused("inventory_shape")
    if int(file_info["bytes"]) > ADMITTED_MAX_INPUT_BYTES:
        raise ReplayRefused("input_size_limit")
    if frames > ADMITTED_MAX_RECORDS:
        raise ReplayRefused("frame_limit")
    data = path.read_bytes()
    source_id = "sha256:" + hashlib.sha256(data).hexdigest()
    if data[:7] != _MAGIC or source_id != file_info["sha256"]:
        raise ReplayRefused("file_changed")
    try:
        topics = decode(data)
    except (InputIntegrityError, struct.error, KeyError) as error:
        raise ReplayRefused("decode_failed") from error
    firmware = report["firmware"]

    def window(samples: Samples) -> Samples:
        return [
            (stamp, values)
            for stamp, values in samples
            if (start_us is None or stamp >= start_us)
            and (end_us is None or stamp < end_us)
        ]

    empty = Topic({}, {})
    home = topics.get("home_position", empty)
    velocity = topics.get("vehicle_local_position", empty)
    battery = topics.get("battery_status", empty)
    status = topics.get("vehicle_status", empty)
    signature = next(
        (s for s in _POSITION if _matches(topics.get(s.topic), s.fields)), None
    )
    positions = window(topics[signature.topic].samples) if signature else []
    # Home altitude shares the AMSL metres of an unscaled position, and must
    # exist before the first replayed position.
    home_ok = (
        _matches(home, _HOME)
        and signature is not None
        and not signature.scaled
        and bool(positions)
        and home.samples[0][0] <= positions[0][0]
    )
    velocity_ok = _matches(velocity, _VELOCITY)
    battery_samples = window(battery.samples) if _matches(battery, _BATTERY) else []
    states = window(status.samples) if _matches(status, _STATUS) else []
    armed_ok = bool(states) and all(
        int(values["arming_state"]) in (ARMING_DISARMED, ARMING_ARMED)
        for _, values in states
    )
    packets = (
        _positions(
            positions,
            signature,
            home.samples if home_ok else None,
            velocity.samples if velocity_ok else None,
        )
        if signature is not None
        else []
    )
    stamps = [p.native_us for p in packets]
    stamps += [stamp for stamp, _ in battery_samples]
    stamps += [stamp for stamp, _ in states]
    if not stamps:
        raise ReplayRefused("no_replayable_samples")
    first, last = min(stamps), max(stamps)

    battery_index = state_index = 0
    for second in range(first // SLOW_PERIOD_US, last // SLOW_PERIOD_US + 1):
        stamp = max(first, second * SLOW_PERIOD_US)
        battery_index, cell = _latest(battery_samples, stamp, battery_index)
        packets.append(Packet(stamp, "SYS_STATUS", _battery(cell)))
        base = 0
        if armed_ok:
            state_index, state = _latest(states, stamp, state_index)
            if state is not None and int(state["arming_state"]) == ARMING_ARMED:
                base = MAV_MODE_FLAG_SAFETY_ARMED
        packets.append(
            Packet(
                stamp,
                "HEARTBEAT",
                {
                    "type": MAV_TYPE_GENERIC,
                    "autopilot": PX4_AUTOPILOT,
                    "base_mode": base,
                    "custom_mode": 0,
                    "system_status": MAV_STATE_ACTIVE,
                },
            )
        )
    order = {"HEARTBEAT": 0, "SYS_STATUS": 1, "GLOBAL_POSITION_INT": 2}
    packets.sort(key=lambda p: (p.native_us, order[p.message]))
    return ReplayPlan(
        source_id=source_id,
        firmware=firmware if isinstance(firmware, str) and firmware else None,
        position_topic=signature.topic if signature and positions else None,
        available={
            "relative_alt": home_ok,
            "velocity": velocity_ok,
            "battery": bool(battery_samples),
            "armed": armed_ok,
            "mode": False,
        },
        packets=tuple(packets),
        first_us=first,
        last_us=last,
    )
