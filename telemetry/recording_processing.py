"""Bounded ordered F09 replay; native-time associations are research assumptions."""

import hashlib
import re
from bisect import bisect_right
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass

from runtime.flight_analytics.state import FIELDS, VALUES
from telemetry.conversion_contract import (
    integer_value,
    object_value,
    require_keys,
    string_value,
)
from telemetry.recording_stream import (
    event_bytes,
    event_order,
    validate_battery_gaps,
    validate_event,
)
from ulog_integrity import F09_SOURCE_ID

FACT_PROFILE = "f09-recording-fact-v1"
MAX_EVENTS = 50_000
MAX_AGE_US = 60_000_000
_BATTERY = "battery_status:0"
_GPS = "vehicle_gps_position:0"
_CONTEXT_KEYS = {
    "profile",
    "source_id",
    "run_id",
    "start_us",
    "end_us",
    "battery_source_count",
    "predecessors",
    "battery_gaps",
    "state_gaps",
}

type Document = dict[str, object]
type _Masks = tuple[list[int], list[int]]


@dataclass(frozen=True)
class _Context:
    run_id: str
    start_us: int
    end_us: int
    battery_source_count: int
    predecessors: list[Document]
    battery_masks: _Masks
    state_masks: _Masks


def _masks(value: object, limit: int, *, open_start: bool) -> _Masks:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError("processing_gap_limit")
    intervals: list[tuple[int, int]] = []
    for item in value:
        gap = object_value(item)
        require_keys(gap, {"start_us", "end_us"})
        start = integer_value(gap["start_us"])
        end = (1 << 64) if gap["end_us"] is None else integer_value(gap["end_us"])
        if not 0 <= start < end <= 1 << 64 or (
            gap["end_us"] is not None and end == 1 << 64
        ):
            raise ValueError("processing_gap_bounds")
        # Integer native microseconds let the same lookup represent (start,end)
        # for battery holes and [start,end) for file-neighbor state masks.
        first = start + int(open_start)
        if first < end:
            intervals.append((first, end))
    starts: list[int] = []
    ends: list[int] = []
    for start, end in sorted(intervals):
        if ends and start <= ends[-1]:
            ends[-1] = max(ends[-1], end)
        else:
            starts.append(start)
            ends.append(end)
    return starts, ends


def _masked(timestamp: int, masks: _Masks) -> bool:
    starts, ends = masks
    index = bisect_right(starts, timestamp) - 1
    return index >= 0 and timestamp < ends[index]


def _context(value: Mapping[str, object]) -> _Context:
    require_keys(value, _CONTEXT_KEYS)
    if (
        value["profile"] != "f09-recording-context-v1"
        or value["source_id"] != F09_SOURCE_ID
    ):
        raise ValueError("processing_context_profile")
    run_id = string_value(value["run_id"])
    if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", run_id) is None:
        raise ValueError("processing_run_id")
    start = integer_value(value["start_us"])
    end = integer_value(value["end_us"])
    count = integer_value(value["battery_source_count"])
    if not 0 <= start < end < 1 << 64 or not 0 <= count <= 100_000:
        raise ValueError("processing_context_bounds")
    raw = value["predecessors"]
    if not isinstance(raw, list) or len(raw) > 3:
        raise ValueError("processing_predecessor_limit")
    predecessors: list[Document] = []
    streams: set[str] = set()
    for item in raw:
        event = deepcopy(validate_event(object_value(item)))
        stream = string_value(event["stream"])
        if (
            stream == _GPS
            or stream in streams
            or event["run_id"] != run_id
            or event["source_id"] != F09_SOURCE_ID
            or integer_value(event["native_timestamp_us"]) >= start
        ):
            raise ValueError("processing_predecessor_scope")
        streams.add(stream)
        predecessors.append(event)
    return _Context(
        run_id,
        start,
        end,
        count,
        predecessors,
        _masks(value["battery_gaps"], 100_000, open_start=True),
        _masks(value["state_gaps"], 1000, open_start=False),
    )


def _association(
    event: Document | None,
    timestamp: int,
    masks: _Masks,
    gap_status: str,
    max_age_us: int,
) -> Document:
    unknown: Document = {
        "status": "before_first",
        "event_id": None,
        "age_us": None,
        "values": None,
    }
    if event is None:
        return unknown
    age = timestamp - integer_value(event["native_timestamp_us"])
    if _masked(timestamp, masks):
        unknown["status"] = gap_status
        return unknown
    if age > max_age_us:
        unknown["status"] = "stale"
        return unknown
    payload = object_value(event["payload"])
    stream = string_value(event["stream"])
    values = (
        object_value(payload["payload"])
        if stream == _BATTERY
        else {name: payload[name] for name in VALUES if name in FIELDS[stream[:-2]]}
    )
    return {
        "status": "matched",
        "event_id": event["measurement_id"],
        "age_us": age,
        "values": deepcopy(values),
    }


def process_events(
    events: Iterable[Document],
    context: Mapping[str, object],
    *,
    max_age_us: int = 1_000_000,
    max_events: int = MAX_EVENTS,
) -> list[Document]:
    """Replay selected ordered deliveries without refreshing state on duplicates.

    Both deliveries and identity signatures (including at most three context
    predecessors) are capped by max_events. Signatures hash every envelope field;
    only the preceding event of each associated stream is retained as state.
    This file reference is not an out-of-order streaming admission policy.
    """
    if type(max_age_us) is not int or not 0 <= max_age_us <= MAX_AGE_US:
        raise ValueError("processing_age_limit")
    if type(max_events) is not int or not 1 <= max_events <= MAX_EVENTS:
        raise ValueError("processing_event_limit")
    policy = {key: deepcopy(value) for key, value in context.items()}
    selected = _context(policy)
    battery_points = [
        event for event in selected.predecessors if event["stream"] == _BATTERY
    ]
    signatures: dict[str, bytes] = {}
    current: dict[str, Document] = {}
    positions: dict[str, tuple[int, int]] = {}

    def admit(event: Document) -> bytes | None:
        stream = string_value(event["stream"])
        ordinal = integer_value(event["source_ordinal"])
        timestamp = integer_value(event["native_timestamp_us"])
        if stream == _BATTERY and ordinal >= selected.battery_source_count:
            raise ValueError("processing_battery_count")
        identity = string_value(event["measurement_id"])
        signature = hashlib.sha256(event_bytes(event)).digest()
        previous = signatures.get(identity)
        if previous is not None:
            if previous != signature:
                raise ValueError("processing_identity_conflict")
            return None
        if len(signatures) >= max_events:
            raise ValueError("processing_identity_limit")
        position = positions.get(stream)
        if position is not None and (
            ordinal <= position[0]
            or timestamp < position[1]
            or (stream != _GPS and timestamp == position[1])
        ):
            raise ValueError("processing_stream_order")
        signatures[identity] = signature
        positions[stream] = ordinal, timestamp
        return signature

    for event in selected.predecessors:
        admit(event)
        current[string_value(event["stream"])] = event

    result: list[Document] = []
    previous_order: tuple[int, int, int] | None = None
    for index, raw in enumerate(events):
        if index >= max_events:
            raise ValueError("processing_event_limit")
        event = deepcopy(validate_event(raw))
        timestamp = integer_value(event["native_timestamp_us"])
        if (
            event["source_id"] != F09_SOURCE_ID
            or event["run_id"] != selected.run_id
            or not selected.start_us <= timestamp < selected.end_us
        ):
            raise ValueError("processing_event_scope")
        signature = admit(event)
        if signature is None:
            continue
        order = event_order(event)
        if previous_order is not None and order < previous_order:
            raise ValueError("processing_event_order")
        previous_order = order
        stream = string_value(event["stream"])
        if stream == _BATTERY:
            battery_points.append(event)
        if stream != _GPS:
            current[stream] = event
            continue
        result.append(
            {
                "profile": FACT_PROFILE,
                "source_id": F09_SOURCE_ID,
                "run_id": selected.run_id,
                "measurement_id": event["measurement_id"],
                "native_timestamp_us": timestamp,
                "input_event_sha256": signature.hex(),
                "inspection": {
                    "gps": event["payload"],
                    "battery": _association(
                        current.get(_BATTERY),
                        timestamp,
                        selected.battery_masks,
                        "rejection_gap",
                        max_age_us,
                    ),
                    "states": {
                        name: _association(
                            current.get(f"{name}:0"),
                            timestamp,
                            selected.state_masks,
                            "recording_gap",
                            max_age_us,
                        )
                        for name in FIELDS
                    },
                },
            }
        )
    if not result:
        raise ValueError("processing_empty_gps_interval")
    validate_battery_gaps(battery_points, policy)
    return result
