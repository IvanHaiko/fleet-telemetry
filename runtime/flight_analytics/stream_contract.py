"""Reuse protected F09 preparation as a bounded, deterministic offline stream.

Source payloads keep their original ordinals. Exact duplicate input rows collapse
before ordering checks; conflicting identities and non-increasing per-stream
ordinals/times refuse. GPS/state coverage is contiguous from ordinal zero;
battery holes retain their separate rejection-gap meaning. This verifies retained
artifacts, not independent source admission or physical clock synchronization.
"""

import hashlib
import re
from pathlib import Path
from typing import cast

from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.local_io import read_bounded, run_path
from telemetry.recording_stream import (
    STREAMS,
    event_bytes,
    event_order,
    make_event,
    validate_event,
)
from ulog_integrity import F09_SOURCE_ID

type Document = dict[str, object]
CONTEXT_PROFILE = "f09-recording-context-v1"
BUNDLE_PROFILE = "f09-recording-stream-bundle-v1"
MAX_EVENTS = 50_000
MAX_BYTES = 64 * 1024 * 1024
SOURCE_BYTES = 122_463_132
_RUN = re.compile(r"[A-Za-z0-9._-]{1,128}", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}", re.ASCII)
LIMITATIONS = [
    "exact F09 research source; protected preparation reused, not source admission",
    "common native boot clock assumed; no physical synchronization proof",
    "GPS receiver UTC is display time; battery UTC anchor remains synthetic",
    "battery rejection intervals are open; state masks are file-neighbor [start,end)",
    "source loss count unknown; retained original includes unprocessed topics",
    "offline interval only; no Kafka, Flink, archive or SQL runtime integration",
]
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
_MANIFEST_KEYS = {
    "profile",
    "source_id",
    "run_id",
    "start_us",
    "end_us",
    "events",
    "stream_counts",
    "predecessor_count",
    "files",
    "input_artifacts",
    "limitations",
}


def _integer(value: object, low: int, high: int) -> int:
    number = integer_value(value)
    if not low <= number <= high:
        raise ValueError("stream_integer_range")
    return number


def _scope(run_id: object, start_us: object, end_us: object) -> tuple[str, int, int]:
    if not isinstance(run_id, str) or _RUN.fullmatch(run_id) is None:
        raise ValueError("stream_run_id")
    start = _integer(start_us, 0, 2**64 - 1)
    end = _integer(end_us, 1, 2**64 - 1)
    if start >= end:
        raise ValueError("stream_interval")
    return run_id, start, end


def _documents(value: object, limit: int) -> list[Document]:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError("stream_list_limit")
    return [object_value(item) for item in cast(list[object], value)]


def _gaps(value: object, limit: int) -> list[Document]:
    result: list[Document] = []
    for gap in _documents(value, limit):
        require_keys(gap, {"start_us", "end_us"})
        start = _integer(gap["start_us"], 0, 2**64 - 1)
        end = gap["end_us"]
        if end is not None:
            end = _integer(end, start + 1, 2**64 - 1)
        result.append({"start_us": start, "end_us": end})
    return result


def _ordered_unique(
    events: list[Document], *, complete: bool = False
) -> list[Document]:
    """Collapse exact repeats before requiring unambiguous original source order."""
    seen: dict[str, bytes] = {}
    previous: dict[str, tuple[int, int]] = {}
    result = []
    for candidate in events:
        event = validate_event(candidate)
        identity = string_value(event["measurement_id"])
        body = event_bytes(event)
        if identity in seen:
            if seen[identity] != body:
                raise ValueError("stream_identity_conflict")
            continue
        stream = string_value(event["stream"])
        ordinal = integer_value(event["source_ordinal"])
        stamp = integer_value(event["native_timestamp_us"])
        prior = previous.get(stream)
        if prior is not None and (ordinal <= prior[0] or stamp <= prior[1]):
            raise ValueError("stream_source_order")
        if complete and stream != STREAMS[0]:
            expected = 0 if prior is None else prior[0] + 1
            if ordinal != expected:
                raise ValueError("stream_source_coverage")
        seen[identity] = body
        previous[stream] = ordinal, stamp
        result.append(event)
    return result


def timeline(
    gps: list[Document],
    battery: list[Document],
    states: list[Document],
    *,
    run_id: str,
    start_us: int,
    end_us: int,
    battery_source_count: int,
    state_gaps: list[Document],
    max_events: int = MAX_EVENTS,
) -> tuple[list[Document], Document]:
    """Select [start,end), retaining prior association state without rebasing IDs.

    Battery masks start strictly after an accepted observation and end strictly
    before the next accepted observation. Rejected leading ordinals supply no
    timestamp: before-first remains unknown, without a fabricated leading mask.
    """
    _scope(run_id, start_us, end_us)
    _integer(max_events, 1, MAX_EVENTS)
    count = _integer(battery_source_count, 0, 100_000)
    gps = _documents(gps, MAX_EVENTS)
    battery = _documents(battery, MAX_EVENTS)
    states = _documents(states, MAX_EVENTS)
    if len(gps) + len(battery) + len(states) > MAX_EVENTS:
        raise ValueError("stream_source_limit")
    gaps = _gaps(state_gaps, 1000)
    inputs = [make_event(STREAMS[3], row, run_id) for row in gps]
    inputs.extend(make_event(STREAMS[0], row, run_id) for row in battery)
    for row in states:
        stream = string_value(row.get("stream")) + ":0"
        if stream not in STREAMS[1:3]:
            raise ValueError("stream_state_stream")
        inputs.append(make_event(stream, row, run_id))
    checked = _ordered_unique(inputs, complete=True)
    accepted = [event for event in checked if event["stream"] == STREAMS[0]]
    if any(integer_value(event["source_ordinal"]) >= count for event in accepted):
        raise ValueError("stream_battery_source_count")
    battery_gaps: list[Document] = []
    for index, event in enumerate(accepted):
        following = accepted[index + 1] if index + 1 < len(accepted) else None
        next_ordinal = (
            count if following is None else integer_value(following["source_ordinal"])
        )
        if next_ordinal > integer_value(event["source_ordinal"]) + 1:
            battery_gaps.append(
                {
                    "start_us": event["native_timestamp_us"],
                    "end_us": (
                        None if following is None else following["native_timestamp_us"]
                    ),
                }
            )
    prior: dict[str, Document] = {}
    selected = []
    for event in checked:
        stamp = integer_value(event["native_timestamp_us"])
        stream = string_value(event["stream"])
        if stamp < start_us and stream != STREAMS[3]:
            prior[stream] = event
        elif start_us <= stamp < end_us:
            selected.append(event)
    if not any(event["stream"] == STREAMS[3] for event in selected):
        raise ValueError("stream_empty_gps_interval")
    if len(selected) > max_events:
        raise ValueError("stream_event_limit")
    selected.sort(key=event_order)
    context: Document = {
        "profile": CONTEXT_PROFILE,
        "source_id": F09_SOURCE_ID,
        "run_id": run_id,
        "start_us": start_us,
        "end_us": end_us,
        "battery_source_count": count,
        "predecessors": sorted(prior.values(), key=event_order),
        "battery_gaps": battery_gaps,
        "state_gaps": gaps,
    }
    return selected, context


def _safe_path(path: Path) -> Path:
    # Reuse the project's ancestor symlink/junction refusal for read paths too.
    absolute = path.absolute()
    return run_path(absolute, absolute.name)


def _read(path: Path, limit: int) -> bytes:
    return read_bounded(_safe_path(path), limit)


def _reference(body: bytes) -> Document:
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def _check_reference(value: object, body: bytes, *, prefixed: bool = False) -> None:
    ref = object_value(value)
    require_keys(ref, {"bytes", "sha256"})
    _integer(ref["bytes"], 0, max(SOURCE_BYTES, MAX_BYTES))
    expected = _reference(body)
    if prefixed:
        expected["sha256"] = "sha256:" + string_value(expected["sha256"])
    if ref != expected:
        raise ValueError("stream_artifact_digest")


def _same(left: object, right: object) -> bool:
    # Canonical JSON comparison distinguishes bool/int and int/float.
    return json_line(left) == json_line(right)


def _rows(body: bytes, limit: int) -> list[Document]:
    lines = body.splitlines()
    if len(lines) > limit:
        raise ValueError("stream_source_limit")
    return [json_object(line) for line in lines]


def _input_names(delivery: str) -> set[str]:
    return {
        "source.ulog",
        "prepared/recording.json",
        "prepared/inspection.jsonl",
        "prepared/gps/manifest.json",
        "prepared/gps/gps.jsonl",
        "prepared/state/manifest.json",
        "prepared/state/state.jsonl",
        *(
            f"prepared/battery/{delivery}/{name}"
            for name in ("run-manifest.json", "events.jsonl", "rejections.jsonl")
        ),
    }


def _limitations(value: object) -> None:
    if not isinstance(value, list) or not 0 < len(value) <= 32:
        raise ValueError("stream_limitations")
    for item in cast(list[object], value):
        if len(string_value(item)) > 512:
            raise ValueError("stream_limitations")


def _validate_context(context: Document) -> list[Document]:
    require_keys(context, _CONTEXT_KEYS)
    run, start, _ = _scope(context["run_id"], context["start_us"], context["end_us"])
    if context["profile"] != CONTEXT_PROFILE or context["source_id"] != F09_SOURCE_ID:
        raise ValueError("stream_context_profile")
    count = _integer(context["battery_source_count"], 0, 100_000)
    _gaps(context["battery_gaps"], min(count, MAX_EVENTS))
    _gaps(context["state_gaps"], 1000)
    predecessors = []
    seen: set[str] = set()
    previous: tuple[int, int, int] | None = None
    for candidate in _documents(context["predecessors"], 3):
        event = validate_event(candidate)
        stream = string_value(event["stream"])
        order = event_order(event)
        if (
            event["run_id"] != run
            or stream not in STREAMS[:3]
            or stream in seen
            or integer_value(event["native_timestamp_us"]) >= start
            or (previous is not None and order <= previous)
        ):
            raise ValueError("stream_predecessor_scope")
        if stream == STREAMS[0] and integer_value(event["source_ordinal"]) >= count:
            raise ValueError("stream_battery_source_count")
        seen.add(stream)
        predecessors.append(event)
        previous = order
    return predecessors


def _validate_inventory(value: object) -> None:
    inventory = object_value(value)
    deliveries: set[str] = set()
    for name in inventory:
        parts = name.split("/")
        if (
            len(parts) == 4
            and parts[:2] == ["prepared", "battery"]
            and _RUN.fullmatch(parts[2]) is not None
            and parts[2] not in (".", "..")
        ):
            deliveries.add(parts[2])
    if len(deliveries) != 1 or set(inventory) != _input_names(next(iter(deliveries))):
        raise ValueError("stream_input_inventory")
    total = 0
    for name, value in inventory.items():
        ref = object_value(value)
        require_keys(ref, {"bytes", "sha256"})
        size = _integer(
            ref["bytes"], 0, SOURCE_BYTES if name == "source.ulog" else MAX_BYTES
        )
        digest = string_value(ref["sha256"])
        if _HASH.fullmatch(digest) is None:
            raise ValueError("stream_input_digest")
        if name == "source.ulog":
            if size != SOURCE_BYTES or "sha256:" + digest != F09_SOURCE_ID:
                raise ValueError("stream_original_reference")
        else:
            total += size
    if total > MAX_BYTES:
        raise ValueError("stream_prepared_byte_limit")
