"""Live MAVLink input events: position, battery summary and mode state.

Two source kinds share the gateway. A PX4 SITL source (`px4-live-event-v1`)
keeps the ADR-0045 position identity: the declared boot session, system and
component IDs and the native boot milliseconds, with an unverified clock
basis. A recorded flight replayed as a virtual vehicle (ADR-0060,
`mavlink-vehicle-event-v1`) derives its position identity from the original
file's checksum and the boot milliseconds only: its system ID is a session
assignment, so a file replayed again under any ID yields the same identities.

A battery summary (SYS_STATUS) or state (HEARTBEAT) has no measurement time
and no measurement identity; its key identifies one receipt by gateway epoch
and capture sequence. Receipt time is delivery metadata and never becomes
measurement time or identity.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.mavlink_position import native_position, position_identity

type Document = dict[str, object]

EVENT_PROFILE = "px4-live-event-v1"
REPLAY_PROFILE = "mavlink-vehicle-event-v1"
REPLAY_KIND = "ulog-replay"
REPLAY_MAPPING_V2 = "ulog-replay-plan-v2"
MAV_STATE_UNINIT = 0
# What a replay player could derive from its file (ADR-0060); a field marked
# false arrives as zero or a MAVLink sentinel and is never shown as a value.
AVAILABLE = ("relative_alt", "velocity", "battery", "armed", "mode")
MESSAGES = {
    "GLOBAL_POSITION_INT": "position",
    "SYS_STATUS": "battery",
    "HEARTBEAT": "state",
}
STREAMS = ("position", "battery", "state")
MAX_EVENT_BYTES = 4096
PX4_AUTOPILOT = 12
_NAME = re.compile(r"[A-Za-z0-9._-]{1,128}")
_EPOCH = re.compile(r"[0-9a-f]{32}")
_SOURCE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_POSITION_TOPICS = ("vehicle_global_position", "vehicle_gps_position", "sensor_gps")
_EVENT_KEYS = {
    "profile",
    "run_id",
    "source",
    "stream",
    "message",
    "measurement_id",
    "native_time_boot_ms",
    "capture",
    "received_unix_ms",
    "native",
}


def _name(value: object) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value) or value in (".", ".."):
        raise ValueError("live_event_name")
    return value


def _bounded(value: object, low: int, high: int) -> int:
    number = integer_value(value)
    if not low <= number <= high:
        raise ValueError("live_event_range")
    return number


def epoch_value(value: object) -> str:
    if not isinstance(value, str) or not _EPOCH.fullmatch(value):
        raise ValueError("live_event_epoch")
    return value


def source_scope(value: Mapping[str, object]) -> Document:
    """One declared source; IDs are filters, not proof of the producer."""
    if value.get("kind") == REPLAY_KIND:
        return replay_scope(value)
    require_keys(value, {"kind", "vehicle", "boot_session", "system", "component"})
    if value["kind"] != "px4-sitl":
        raise ValueError("live_event_source_kind")
    return {
        "kind": "px4-sitl",
        "vehicle": _name(value["vehicle"]),
        "boot_session": _name(value["boot_session"]),
        "system": _bounded(value["system"], 1, 255),
        "component": _bounded(value["component"], 1, 255),
    }


def replay_scope(value: Mapping[str, object]) -> Document:
    """A recorded file as a virtual vehicle, with what the player could map."""
    mapping: Document = {}
    if "mapping_version" in value:
        if value["mapping_version"] != REPLAY_MAPPING_V2:
            raise ValueError("live_event_replay_mapping")
        first = value.get("velocity_from_boot_ms")
        mapping = {
            "mapping_version": REPLAY_MAPPING_V2,
            "velocity_from_boot_ms": None
            if first is None
            else _bounded(first, 0, 2**32 - 1),
        }
    require_keys(
        value,
        {
            "kind",
            "vehicle",
            "label",
            "source_id",
            "firmware",
            "position_topic",
            "system",
            "component",
            "available",
            *mapping,
        },
    )
    source_id = value["source_id"]
    if not isinstance(source_id, str) or _SOURCE_ID.fullmatch(source_id) is None:
        raise ValueError("live_event_source_id")
    digest = source_id.removeprefix("sha256:")
    if value["vehicle"] != f"ulog-{digest[:16]}" or value["label"] != (
        "ULog " + digest[:8]
    ):
        raise ValueError("live_event_replay_names")
    firmware = value["firmware"]
    if firmware is not None and (
        not isinstance(firmware, str) or not re.fullmatch(r"[0-9a-f]{1,64}", firmware)
    ):
        raise ValueError("live_event_firmware")
    topic = value["position_topic"]
    if topic is not None and topic not in _POSITION_TOPICS:
        raise ValueError("live_event_position_topic")
    available = object_value(value["available"])
    require_keys(available, set(AVAILABLE))
    if not all(type(available[name]) is bool for name in AVAILABLE):
        raise ValueError("live_event_available")
    if mapping and available["velocity"] != (
        mapping["velocity_from_boot_ms"] is not None
    ):
        raise ValueError("live_event_velocity_availability")
    return {
        "kind": REPLAY_KIND,
        "vehicle": value["vehicle"],
        "label": value["label"],
        "source_id": source_id,
        "firmware": firmware,
        "position_topic": topic,
        # System 1 stays for a physical or simulated vehicle.
        "system": _bounded(value["system"], 2, 250),
        "component": _bounded(value["component"], 1, 255),
        "available": {name: available[name] for name in AVAILABLE},
        **mapping,
    }


def replay_position_identity(source_id: str, boot_ms: int) -> str:
    """File checksum and native boot milliseconds; never the system ID."""
    if _SOURCE_ID.fullmatch(source_id) is None or not 0 <= boot_ms < 2**32:
        raise ValueError("replay_identity_scope")
    text = f"{REPLAY_PROFILE}:position:{source_id}:{boot_ms}"
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def native_values(message: str, data: Mapping[str, object]) -> Document:
    """Exact native integers of one admitted message; sentinels stay as sent."""
    fields = dict(data)
    if message == "GLOBAL_POSITION_INT":
        return dict(native_position(fields))
    if message == "SYS_STATUS":
        return {
            "voltage_battery": _bounded(fields.get("voltage_battery"), 0, 65535),
            "current_battery": _bounded(fields.get("current_battery"), -32768, 32767),
            "battery_remaining": _bounded(fields.get("battery_remaining"), -1, 100),
        }
    if message == "HEARTBEAT":
        if fields.get("autopilot") != PX4_AUTOPILOT:
            raise ValueError("live_event_not_px4")
        return {
            "autopilot": PX4_AUTOPILOT,
            "base_mode": _bounded(fields.get("base_mode"), 0, 255),
            "custom_mode": _bounded(fields.get("custom_mode"), 0, 2**32 - 1),
            "system_status": _bounded(fields.get("system_status"), 0, 255),
        }
    raise ValueError("live_event_message")


def observation_id(epoch: str, sequence: int) -> str:
    """Identity of one receipt; it never stands for a measurement."""
    text = f"{EVENT_PROFILE}:observation:{epoch_value(epoch)}:{sequence}"
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def make_event(
    run_id: str,
    source: Mapping[str, object],
    message: str,
    data: Mapping[str, object],
    epoch: str,
    sequence: int,
    received_unix_ms: int,
) -> Document:
    scope = source_scope(source)
    if message not in MESSAGES:
        raise ValueError("live_event_message")
    native = native_values(message, data)
    stream = MESSAGES[message]
    boot = native["time_boot_ms"] if stream == "position" else None
    replay = scope["kind"] == REPLAY_KIND
    identity: str | None
    if boot is None:
        identity = None
    elif replay:
        identity = replay_position_identity(
            string_value(scope["source_id"]), integer_value(boot)
        )
    else:
        identity = position_identity(
            string_value(scope["boot_session"]),
            integer_value(scope["system"]),
            integer_value(scope["component"]),
            integer_value(boot),
        )
    event: Document = {
        "profile": REPLAY_PROFILE if replay else EVENT_PROFILE,
        "run_id": _name(run_id),
        "source": scope,
        "stream": stream,
        "message": message,
        "measurement_id": identity,
        "native_time_boot_ms": boot,
        "capture": {
            "epoch": epoch_value(epoch),
            "sequence": _bounded(sequence, 0, 2**63 - 1),
        },
        "received_unix_ms": _bounded(received_unix_ms, 0, 2**63 - 1),
        "native": native,
    }
    event_bytes(event)
    return event


def event_bytes(event: Mapping[str, object]) -> bytes:
    """Compact sorted JSON without a newline, within the event size bound."""
    raw = json_line(event)[:-1]
    if len(raw) > MAX_EVENT_BYTES:
        raise ValueError("live_event_size")
    return raw


def read_event(raw: bytes) -> Document:
    """Decode one event and refuse anything but its exact canonical form."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_EVENT_BYTES:
        raise ValueError("live_event_size")
    row = json_object(raw)
    require_keys(row, _EVENT_KEYS)
    capture = object_value(row["capture"])
    require_keys(capture, {"epoch", "sequence"})
    event = make_event(
        string_value(row["run_id"]),
        object_value(row["source"]),
        string_value(row["message"]),
        object_value(row["native"]),
        string_value(capture["epoch"]),
        integer_value(capture["sequence"]),
        integer_value(row["received_unix_ms"]),
    )
    if event != row or event_bytes(event) != raw:
        raise ValueError("live_event_canonical")
    return event


def event_key(event: Mapping[str, object]) -> str:
    """Kafka key and deduplication identity: measurement, else receipt."""
    identity = event["measurement_id"]
    if identity is not None:
        return string_value(identity)
    capture = object_value(event["capture"])
    return observation_id(
        string_value(capture["epoch"]), integer_value(capture["sequence"])
    )


def content_signature(event: Mapping[str, object]) -> str:
    """Signature of what a repeat must match.

    A position repeats when its measurement content repeats, whatever receipt
    carried it; an untimed event repeats only as the same receipt.
    """
    if event["measurement_id"] is None:
        return hashlib.sha256(event_bytes(event)).hexdigest()
    projection = {
        name: event[name]
        for name in ("source", "measurement_id", "native_time_boot_ms", "native")
    }
    return hashlib.sha256(json_line(projection)).hexdigest()
