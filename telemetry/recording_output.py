"""Bounded ordered recording association and strict transport output.

Checkpoints are trusted application state, not authenticated source evidence.
The reference's gap/association policy remains the authority for this profile.
"""

from __future__ import annotations

import hashlib
import math
import re
from copy import deepcopy
from typing import cast

from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.recording_processing import (
    FACT_PROFILE,
    MAX_AGE_US,
)
from telemetry.recording_stream import (
    STREAMS,
    event_bytes,
    make_event,
)
from ulog_integrity import F09_SOURCE_ID

type Document = dict[str, object]

MAX_EVENTS = 4096
MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024
MAX_OUTPUT_BYTES = 65_536
OUTPUT_PROFILE = "f09-recording-output-v1"
_HEX = re.compile(r"[0-9a-f]{64}")
_IDENTIFIER = re.compile(r"[A-Za-z0-9._-]{1,128}")
_STATE_FIELDS = {
    "vehicle_land_detected": ("landed", "ground_contact", "maybe_landed"),
    "vehicle_status": ("arming_state", "nav_state", "failsafe"),
}


def _bounded_json(value: object, limit: int) -> bytes:
    try:
        raw = json_line(value)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("recording_json") from None
    if len(raw) > limit:
        raise ValueError("recording_json_limit")
    return raw


def _digest(value: object) -> str:
    if not isinstance(value, str) or _HEX.fullmatch(value) is None:
        raise ValueError("recording_digest")
    return value


def _measurement_id(value: object) -> str:
    if isinstance(value, str) and value.startswith("sha256:"):
        _digest(value[7:])
        return value
    return _digest(value)


def _identifier(value: object) -> str:
    if (
        not isinstance(value, str)
        or _IDENTIFIER.fullmatch(value) is None
        or value in (".", "..")
    ):
        raise ValueError("recording_identifier")
    return value


def _integer(value: object, low: int, high: int) -> int:
    number = integer_value(value)
    if not low <= number <= high:
        raise ValueError("recording_integer_bounds")
    return number


def _source(value: Document) -> Document:
    require_keys(value, {"cluster_id", "topic_id", "topic", "partition"})
    for field in ("cluster_id", "topic_id", "topic"):
        _identifier(value[field])
    _integer(value["partition"], 0, 0)
    return deepcopy(value)


def _number(value: object) -> float:
    if type(value) not in (int, float):
        raise ValueError("recording_fact_number")
    try:
        number = float(cast(int | float, value))
    except OverflowError:
        raise ValueError("recording_fact_number") from None
    if not math.isfinite(number):
        raise ValueError("recording_fact_number")
    return number


def _validate_association(value: object, name: str, stamp: int) -> None:
    row = object_value(value)
    require_keys(row, {"status", "event_id", "age_us", "values"})
    gap = "rejection_gap" if name == "battery" else "recording_gap"
    if row["status"] in ("before_first", "stale", gap):
        if any(row[field] is not None for field in ("event_id", "age_us", "values")):
            raise ValueError("recording_fact_unknown")
        return
    if row["status"] != "matched":
        raise ValueError("recording_fact_status")
    identity = row["event_id"]
    if name == "battery":
        if not isinstance(identity, str) or not identity.startswith("sha256:"):
            raise ValueError("recording_battery_identity")
        _digest(identity[7:])
    else:
        _digest(identity)
    _integer(row["age_us"], 0, min(stamp, MAX_AGE_US))
    values = object_value(row["values"])
    if name == "battery":
        require_keys(values, {"voltage_v", "current_a", "remaining_fraction"})
        if _number(values["voltage_v"]) < 0:
            raise ValueError("recording_fact_voltage")
        if values["current_a"] is not None:
            _number(values["current_a"])
        if values["remaining_fraction"] is not None:
            if not 0 <= _number(values["remaining_fraction"]) <= 1:
                raise ValueError("recording_fact_remaining")
    else:
        require_keys(values, set(_STATE_FIELDS[name]))
        for field, number in values.items():
            upper = 255 if field == "nav_state" else 2 if field == "arming_state" else 1
            _integer(number, 1 if field == "arming_state" else 0, upper)


def _fact(value: Document) -> Document:
    row = json_object(_bounded_json(value, MAX_OUTPUT_BYTES))
    require_keys(
        row,
        {
            "profile",
            "source_id",
            "run_id",
            "measurement_id",
            "native_timestamp_us",
            "input_event_sha256",
            "inspection",
        },
    )
    if row["profile"] != FACT_PROFILE or row["source_id"] != F09_SOURCE_ID:
        raise ValueError("recording_fact_profile")
    _identifier(row["run_id"])
    inspection = object_value(row["inspection"])
    require_keys(inspection, {"gps", "battery", "states"})
    gps = make_event(
        STREAMS[-1], object_value(inspection["gps"]), string_value(row["run_id"])
    )
    stamp = _integer(row["native_timestamp_us"], 0, (1 << 64) - 1)
    if (
        row["measurement_id"] != gps["measurement_id"]
        or stamp != gps["native_timestamp_us"]
        or _digest(row["input_event_sha256"])
        != hashlib.sha256(event_bytes(gps)).hexdigest()
    ):
        raise ValueError("recording_fact_input")
    _validate_association(inspection["battery"], "battery", stamp)
    states = object_value(inspection["states"])
    require_keys(states, set(_STATE_FIELDS))
    for name, association in states.items():
        _validate_association(association, name, stamp)
    return row


def make_output(
    fact: Document,
    source: Document,
    offset: int,
    context_sha256: str,
) -> Document:
    """Wrap the complete fact with delivery provenance without changing its ID."""
    output: Document = {
        "profile": OUTPUT_PROFILE,
        "input_source": _source({**source, "partition": source.get("partition", 0)}),
        "input_offset": _integer(offset, 0, MAX_EVENTS - 1),
        "context_sha256": _digest(context_sha256),
        "fact": _fact(fact),
    }
    _bounded_json(output, MAX_OUTPUT_BYTES)
    return output


def read_output(raw: bytes) -> Document:
    """Decode bounded UTF-8 JSON with strict keys, hashes and unknown semantics."""
    if type(raw) is not bytes or len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError("recording_output_bytes")
    # json.loads(bytes) also accepts UTF-16/32. Literal NUL is invalid in UTF-8
    # JSON and must not let those encodings bypass the explicit wire contract.
    if b"\x00" in raw:
        raise ValueError("recording_output_utf8")
    try:
        raw.decode("utf-8")
    except UnicodeError:
        raise ValueError("recording_output_utf8") from None
    row = json_object(raw)
    require_keys(
        row, {"profile", "input_source", "input_offset", "context_sha256", "fact"}
    )
    if row["profile"] != OUTPUT_PROFILE:
        raise ValueError("recording_output_profile")
    return make_output(
        object_value(row["fact"]),
        _source(object_value(row["input_source"])),
        integer_value(row["input_offset"]),
        string_value(row["context_sha256"]),
    )
