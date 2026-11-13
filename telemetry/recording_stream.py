"""Strict offline events for the registered F09 research recording only.

GPS/state keep boot-relative time. Battery retains its original synthetic UTC
anchor and publication-time meaning; the outer run is delivery metadata only.
Validation checks protocol consistency, not authenticity of measurement values.
"""

import json
import math
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from telemetry.conversion_contract import json_object
from telemetry.models import F09_NORMALIZATION_VERSION
from telemetry_reader import read_battery_event
from ulog_integrity import F09_SOURCE_ID

type Document = dict[str, object]

EVENT_PROFILE = "f09-recording-event-v1"
STREAMS = (
    "battery_status:0",
    "vehicle_land_detected:0",
    "vehicle_status:0",
    "vehicle_gps_position:0",
)
_MAX_BYTES = 65_536
_VEHICLE = "f09-research-vehicle"
_ENVELOPE = {
    "profile",
    "source_id",
    "run_id",
    "stream",
    "source_ordinal",
    "native_timestamp_us",
    "measurement_id",
    "payload",
}
_GPS = {
    "event_id",
    "vehicle_id",
    "source_ordinal",
    "native_timestamp_us",
    "native_sample_us",
    "gps_utc",
    "gps_time_relative_us",
    "latitude_deg",
    "longitude_deg",
    "altitude_msl_m",
    "ground_speed_m_s",
    "fix_type",
}
_STATE_VALUES = {
    "vehicle_land_detected:0": {"landed", "ground_contact", "maybe_landed"},
    "vehicle_status:0": {"arming_state", "nav_state", "failsafe"},
}
_VALUES = _STATE_VALUES["vehicle_land_detected:0"] | _STATE_VALUES["vehicle_status:0"]
_BATTERY = {
    "event_id",
    "vehicle_id",
    "event_type",
    "schema_version",
    "source_timestamp",
    "ingest_timestamp",
    "source_log_id",
    "source_type",
    "source_stream",
    "source_record_index",
    "normalization_version",
    "source_time",
    "provenance",
    "quality_flags",
    "payload",
    "delivery",
}


def _mapping(value: object, keys: set[str]) -> Document:
    if not isinstance(value, Mapping):
        raise ValueError("event_object")
    mapping = cast(Mapping[object, object], value)
    if any(type(key) is not str for key in mapping) or set(mapping) != keys:
        raise ValueError("event_keys")
    return {key: mapping[key] for key in keys}


def _integer(value: object, lower: int = 0, upper: int = 2**64) -> int:
    if type(value) is not int or not lower <= value < upper:
        raise ValueError("event_integer")
    return value


def _number(value: object) -> int | float:
    if type(value) not in (int, float):
        raise ValueError("event_number")
    number = cast(int | float, value)
    try:
        finite = math.isfinite(number)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("event_number")
    return number


def _encode(value: Mapping[str, object]) -> bytes:
    try:
        body = json.dumps(
            dict(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ValueError("event_json") from None
    if len(body) > _MAX_BYTES:
        raise ValueError("event_size_limit")
    return body


def _gps(payload: object) -> Document:
    row = _mapping(payload, _GPS)
    ordinal = _integer(row["source_ordinal"])
    _integer(row["native_timestamp_us"])
    _integer(row["native_sample_us"])
    _integer(row["gps_time_relative_us"], -(2**31), 2**31)
    fix = _integer(row["fix_type"], 0, 256)
    identity = sha256(
        f"f09-gps-research-v1:{F09_SOURCE_ID}:vehicle_gps_position:0:{ordinal}".encode()
    ).hexdigest()
    if row["vehicle_id"] != _VEHICLE or row["event_id"] != identity:
        raise ValueError("gps_identity")
    latitude, longitude = row["latitude_deg"], row["longitude_deg"]
    if (latitude is None) != (longitude is None):
        raise ValueError("gps_position")
    if latitude is not None:
        if (
            fix not in (3, 4, 5, 6)
            or not -90 <= _number(latitude) <= 90
            or not -180 <= _number(longitude) <= 180
        ):
            raise ValueError("gps_position")
    altitude = row["altitude_msl_m"]
    if altitude is not None:
        if latitude is None:
            raise ValueError("gps_altitude")
        _number(altitude)
    speed = row["ground_speed_m_s"]
    if speed is not None and _number(speed) < 0:
        raise ValueError("gps_speed")
    utc = row["gps_utc"]
    if utc is not None:
        if (
            not isinstance(utc, str)
            or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
                utc,
            )
            is None
        ):
            raise ValueError("gps_utc")
        try:
            instant = datetime.fromisoformat(utc)
        except ValueError:
            raise ValueError("gps_utc") from None
        if instant <= datetime(1970, 1, 1, tzinfo=UTC):
            raise ValueError("gps_utc")
    return row


def _state(stream: str, payload: object) -> Document:
    row = _mapping(
        payload,
        {"event_id", "stream", "source_ordinal", "native_timestamp_us"} | _VALUES,
    )
    ordinal = _integer(row["source_ordinal"], 0, 10_000)
    _integer(row["native_timestamp_us"])
    name = stream.removesuffix(":0")
    identity = sha256(
        f"f09-state-research-v1:{F09_SOURCE_ID}:{name}:0:{ordinal}".encode()
    ).hexdigest()
    if row["stream"] != name or row["event_id"] != identity:
        raise ValueError("state_identity")
    for field in _VALUES:
        value = row[field]
        if field not in _STATE_VALUES[stream]:
            if value is not None:
                raise ValueError("state_null")
        elif field == "nav_state":
            _integer(value, 0, 256)
        elif field == "arming_state":
            _integer(value, 1, 3)
        else:
            _integer(value, 0, 2)
    return row


def _battery(payload: object) -> Document:
    row = _mapping(payload, _BATTERY)
    source_time = _mapping(
        row["source_time"],
        {"clock_basis", "native_timestamp_us", "timestamp_kind", "mapping"},
    )
    _mapping(
        source_time["mapping"],
        {"native_anchor_us", "utc_anchor", "anchor_kind", "anchor_uncertainty_us"},
    )
    _mapping(row["provenance"], {"source_manifest_id", "privacy_classification"})
    _mapping(row["delivery"], {"dataset_run_id", "replay_mode"})
    _mapping(row["payload"], {"voltage_v", "current_a", "remaining_fraction"})
    if (
        row["source_log_id"] != F09_SOURCE_ID
        or row["vehicle_id"] != _VEHICLE
        or row["normalization_version"] != F09_NORMALIZATION_VERSION
        or row["source_type"] != "ulog"
        or row["source_stream"] != STREAMS[0]
    ):
        raise ValueError("battery_profile")
    # The existing independent reader owns canonical identity, scalar, value,
    # anchor, provenance and publication-clock validation. Exact shapes above
    # prevent its optional-field projection from silently discarding anything.
    return dict(read_battery_event(_encode(row)))


def _payload(stream: str, payload: object) -> Document:
    if stream == STREAMS[0]:
        return _battery(payload)
    if stream in _STATE_VALUES:
        return _state(stream, payload)
    return _gps(payload)


def _coordinates(stream: str, payload: Document) -> tuple[int, int, str]:
    if stream == STREAMS[0]:
        time = cast(Document, payload["source_time"])
        ordinal = cast(int, payload["source_record_index"])
        native = cast(int, time["native_timestamp_us"])
    else:
        ordinal = cast(int, payload["source_ordinal"])
        native = cast(int, payload["native_timestamp_us"])
    return ordinal, native, cast(str, payload["event_id"])


def make_event(stream: str, payload: Mapping[str, object], run_id: str) -> Document:
    """Wrap a validated original payload without rebasing its identity or time."""
    if not isinstance(stream, str) or stream not in STREAMS:
        raise ValueError("event_stream")
    row = _payload(stream, payload)
    ordinal, native, identity = _coordinates(stream, row)
    return validate_event(
        {
            "profile": EVENT_PROFILE,
            "source_id": F09_SOURCE_ID,
            "run_id": run_id,
            "stream": stream,
            "source_ordinal": ordinal,
            "native_timestamp_us": native,
            "measurement_id": identity,
            "payload": row,
        }
    )


def validate_event(event: Mapping[str, object]) -> Document:
    """Return an independent strict JSON document; reject inconsistent envelopes."""
    row = _mapping(event, _ENVELOPE)
    if row["profile"] != EVENT_PROFILE or row["source_id"] != F09_SOURCE_ID:
        raise ValueError("event_profile")
    run = row["run_id"]
    if not isinstance(run, str) or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", run) is None:
        raise ValueError("event_run_id")
    stream = row["stream"]
    if not isinstance(stream, str) or stream not in STREAMS:
        raise ValueError("event_stream")
    payload = _payload(stream, row["payload"])
    ordinal, native, identity = _coordinates(stream, payload)
    if (
        _integer(row["source_ordinal"]) != ordinal
        or _integer(row["native_timestamp_us"]) != native
        or row["measurement_id"] != identity
    ):
        raise ValueError("event_payload_mismatch")
    row["payload"] = payload
    # A wire round trip also detaches all nested battery data from the caller.
    return json_object(_encode(row))


def read_event(data: bytes) -> Document:
    """Read one bounded UTF-8 JSON object, refusing duplicate keys at any depth."""
    if type(data) is not bytes:
        raise ValueError("event_input_type")
    if len(data) > _MAX_BYTES:
        raise ValueError("event_size_limit")
    try:
        row = json_object(data.decode("utf-8").encode("utf-8"))
    except UnicodeError:
        raise ValueError("event_utf8") from None
    return validate_event(row)


def event_bytes(event: Mapping[str, object]) -> bytes:
    """Encode a validated event as compact sorted finite JSON without a newline."""
    return _encode(validate_event(event))


def event_order(event: Mapping[str, object]) -> tuple[int, int, int]:
    """Order by original native time, fixed stream precedence and source ordinal."""
    row = validate_event(event)
    return (
        cast(int, row["native_timestamp_us"]),
        STREAMS.index(cast(str, row["stream"])),
        cast(int, row["source_ordinal"]),
    )


def validate_battery_gaps(
    events: list[Document], context: Mapping[str, object]
) -> None:
    """Reconcile masks with already validated, unique, source-ordered events.

    Only available interval/predecessor observations can be checked. References
    outside that selection are protected preparation evidence, not authenticated
    source completeness. This is shared by bundle admission and direct replay.
    """
    points = [event for event in events if event["stream"] == STREAMS[0]]
    count = _integer(context["battery_source_count"], 0, 100_001)
    raw = context["battery_gaps"]
    if not isinstance(raw, list) or len(raw) > min(count, 50_000):
        raise ValueError("stream_battery_gap_limit")
    gaps: list[Document] = []
    for item in cast(list[object], raw):
        gap = _mapping(item, {"start_us", "end_us"})
        start = _integer(gap["start_us"])
        parsed_end = (
            None if gap["end_us"] is None else _integer(gap["end_us"], start + 1)
        )
        gaps.append({"start_us": start, "end_us": parsed_end})
    starts: dict[int, Document] = {}
    previous_end = -1
    for gap in gaps:
        start = _integer(gap["start_us"])
        if start < previous_end or start in starts:
            raise ValueError("stream_battery_gap_order")
        starts[start] = gap
        end = gap["end_us"]
        previous_end = 2**64 if end is None else _integer(end)
    gap_index = 0
    point_times = {_integer(point["native_timestamp_us"]) for point in points}
    start_us = _integer(context["start_us"])
    end_us = _integer(context["end_us"])
    for gap in gaps:
        start = _integer(gap["start_us"])
        end = gap["end_us"]
        if start < start_us and (end is None or start_us < _integer(end)):
            if start not in point_times:
                raise ValueError("stream_battery_gap_predecessor")
        for boundary in (gap["start_us"], gap["end_us"]):
            if boundary is not None:
                stamp = _integer(boundary)
                if start_us <= stamp < end_us and stamp not in point_times:
                    raise ValueError("stream_battery_gap_observation")
    for index, point in enumerate(points):
        stamp = _integer(point["native_timestamp_us"])
        while gap_index < len(gaps):
            end = gaps[gap_index]["end_us"]
            if end is None or stamp < _integer(end):
                break
            gap_index += 1
        if gap_index < len(gaps):
            gap = gaps[gap_index]
            if _integer(gap["start_us"]) < stamp:
                raise ValueError("stream_battery_gap_observation")
        following = points[index + 1] if index + 1 < len(points) else None
        ordinal = _integer(point["source_ordinal"])
        if following is not None:
            needed = _integer(following["source_ordinal"]) > ordinal + 1
            expected = {"start_us": stamp, "end_us": following["native_timestamp_us"]}
            if (needed and starts.get(stamp) != expected) or (
                not needed and stamp in starts
            ):
                raise ValueError("stream_battery_gap_coverage")
        elif ordinal == count - 1 and stamp in starts:
            raise ValueError("stream_battery_gap_coverage")
