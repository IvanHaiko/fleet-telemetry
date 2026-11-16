"""PX4 SITL live input events: position, battery summary and mode state.

A position is a timed measurement with the ADR-0045 identity: the declared
boot session, system and component IDs and the native boot milliseconds, with
an unverified clock basis. A battery summary (SYS_STATUS) or state (HEARTBEAT)
has no measurement time and no measurement identity; its key identifies one
receipt by gateway epoch and capture sequence. Receipt time is delivery
metadata and never becomes measurement time or identity.
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
    """The one configured source; IDs are filters, not proof of the producer."""
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
    identity = (
        None
        if boot is None
        else position_identity(
            string_value(scope["boot_session"]),
            integer_value(scope["system"]),
            integer_value(scope["component"]),
            integer_value(boot),
        )
    )
    event: Document = {
        "profile": EVENT_PROFILE,
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
