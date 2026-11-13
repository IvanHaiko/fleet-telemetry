"""Native-boot live position contract and deterministic unit conversion."""

import hashlib
import math

from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)

INPUT_VERSION = "px4-live-position-input-v1"
FACT_VERSION = "px4-live-position-fact-v1"
NATIVE_FIELDS = {"time_boot_ms", "lat", "lon", "alt", "relative_alt", "vx", "vy", "vz"}


def integer_field(data: dict[str, object], field: str, lower: int, upper: int) -> int:
    value = data.get(field)
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError("mavlink_field_range")
    return value


def native_position(data: dict[str, object]) -> dict[str, int]:
    return {
        "time_boot_ms": integer_field(data, "time_boot_ms", 0, 2**32 - 1),
        "lat": integer_field(data, "lat", -900_000_000, 900_000_000),
        "lon": integer_field(data, "lon", -1_800_000_000, 1_800_000_000),
        **{
            name: integer_field(data, name, -(2**31), 2**31 - 1)
            for name in ("alt", "relative_alt")
        },
        **{
            name: integer_field(data, name, -32768, 32767)
            for name in ("vx", "vy", "vz")
        },
    }


def position_values(native: dict[str, int]) -> dict[str, float]:
    return {
        "latitude_deg": native["lat"] / 10_000_000,
        "longitude_deg": native["lon"] / 10_000_000,
        "altitude_msl_m": native["alt"] / 1000,
        "relative_altitude_m": native["relative_alt"] / 1000,
        "ground_speed_m_s": math.hypot(native["vx"], native["vy"]) / 100,
        "down_speed_m_s": native["vz"] / 100,
    }


def position_identity(session: str, system: int, component: int, boot_ms: int) -> str:
    if (
        not 1 <= len(session) <= 128
        or not all(c.isascii() and (c.isalnum() or c in "-_.") for c in session)
        or type(system) is not int
        or not 1 <= system <= 255
        or type(component) is not int
        or not 1 <= component <= 255
        or type(boot_ms) is not int
        or not 0 <= boot_ms < 2**32
    ):
        raise ValueError("position_identity_scope")
    return (
        "sha256:"
        + hashlib.sha256(
            f"px4-mavlink-position-v1:{session}:{system}:{component}:GLOBAL_POSITION_INT:{boot_ms}".encode()
        ).hexdigest()
    )


def make_input(
    data: dict[str, object], session: str, system: int, component: int
) -> dict[str, object]:
    native = native_position(data)
    return {
        "format_version": INPUT_VERSION,
        "event_id": position_identity(
            session, system, component, native["time_boot_ms"]
        ),
        "source_kind": "px4-sitl",
        "source_boot_session": session,
        "system_id": system,
        "component_id": component,
        "source_time_kind": "boot_timestamp_clock_unverified",
        "native": native,
    }


def read_input(body: bytes) -> dict[str, object]:
    if not 0 < len(body) <= 8192:
        raise ValueError("position_input_limit")
    row = json_object(body)
    require_keys(
        row,
        {
            "format_version",
            "event_id",
            "source_kind",
            "source_boot_session",
            "system_id",
            "component_id",
            "source_time_kind",
            "native",
        },
    )
    native = object_value(row["native"])
    require_keys(native, NATIVE_FIELDS)
    expected = make_input(
        native,
        string_value(row["source_boot_session"]),
        integer_value(row["system_id"]),
        integer_value(row["component_id"]),
    )
    if row != expected:
        raise ValueError("position_input_identity_or_profile")
    return expected


def make_fact(
    body: bytes,
    key: bytes,
    topic: str,
    partition: int,
    offset: int,
    *,
    offset_limit: int = 32,
) -> dict[str, object]:
    event = read_input(body)
    if (
        key != string_value(event["event_id"]).encode()
        or partition != 0
        or type(offset_limit) is not int
        or not 1 <= offset_limit <= 4096
        or type(offset) is not int
        or not 0 <= offset < offset_limit
    ):
        raise ValueError("position_source_coordinate")
    native = native_position(object_value(event["native"]))
    return {
        "format_version": FACT_VERSION,
        "input_topic": topic,
        "input_partition": partition,
        "input_offset": offset,
        "input_key_sha256": hashlib.sha256(key).hexdigest(),
        "input_value_sha256": hashlib.sha256(body).hexdigest(),
        "event": event,
        "payload": position_values(native),
    }


def unique_events(events: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    if not 0 < len(events) <= 32:
        raise ValueError("position_event_bound")
    result: dict[str, dict[str, object]] = {}
    for candidate in events:
        event = read_input(json_line(candidate))
        identity = string_value(event["event_id"])
        if identity in result and result[identity] != event:
            raise ValueError("competing_position_content")
        result[identity] = event
    return result
