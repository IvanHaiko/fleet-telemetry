"""Bounded native-time F09 association with file-neighbor uncertainty masks."""

import hashlib
import struct
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from runtime.flight_analytics.state import (
    DEFINITIONS,
    FIRMWARE,
    SOURCE_BYTES,
    validate_rows,
)
from telemetry.conversion_contract import integer_value
from ulog_integrity import F09_SOURCE_ID, ULogExpectation, inspect_ulog

VERSION = "f09-gps-state-association-v1"
GPS_STREAM = "vehicle_gps_position"
GPS_DEFINITION = "e01e4b9dfff5a5b7332eca486e78460ddacf9bb36363a8cb450c176eda18675e"


@dataclass(frozen=True)
class StatePoint:
    ordinal: int
    timestamp_us: int
    event_id: str


@dataclass(frozen=True)
class Gap:
    start_us: int
    end_us: int | None


@dataclass(frozen=True)
class StateMatch:
    status: Literal["matched", "before_first", "stale", "recording_gap"]
    event_id: str | None = None
    age_us: int | None = None


def bracket_dropouts(
    markers: list[int], records: dict[str, list[tuple[int, int]]]
) -> list[Gap]:
    """Mask [earliest previous, latest next) across the three selected streams.

    File neighbors bound a reproducible research mask, not physical lost time.
    A missing previous neighbor uses zero; any missing next neighbor is open-ended.
    """
    if (
        not records
        or len(markers) > 1000
        or any(type(offset) is not int or offset < 16 for offset in markers)
    ):
        raise ValueError("invalid_dropout_bracket")
    offsets: dict[str, list[int]] = {}
    for name, selected in records.items():
        if not selected or len(selected) > 25_000:
            raise ValueError("invalid_dropout_records")
        previous_offset = previous_time = -1
        for offset, timestamp in selected:
            if (
                type(offset) is not int
                or type(timestamp) is not int
                or offset <= previous_offset
                or not 0 <= timestamp < 2**64
                or timestamp <= previous_time
            ):
                raise ValueError("ambiguous_dropout_records")
            previous_offset, previous_time = offset, timestamp
        offsets[name] = [offset for offset, _ in selected]
    gaps = []
    for marker in markers:
        starts = []
        ends = []
        unbounded = False
        for name, selected in records.items():
            index = bisect_left(offsets[name], marker)
            if index < len(selected) and selected[index][0] == marker:
                raise ValueError("dropout_record_overlap")
            starts.append(selected[index - 1][1] if index else 0)
            if index < len(selected):
                ends.append(selected[index][1])
            else:
                unbounded = True
        start = min(starts)
        end = None if unbounded else max(ends)
        if end is not None and end <= start:
            raise ValueError("ambiguous_dropout_bracket")
        gaps.append(Gap(start, end))
    return gaps


def match_states(
    gps_times: list[int], points: list[StatePoint], gaps: list[Gap], max_age_us: int
) -> list[StateMatch]:
    """Choose only a past observation; unknown results carry no ID or age."""
    if (
        type(max_age_us) is not int
        or not 0 <= max_age_us <= 60_000_000
        or not 0 < len(points) <= 10_000
        or not 0 < len(gps_times) <= 25_000
        or len(gaps) > 1000
    ):
        raise ValueError("invalid_state_match_input")
    previous = -1
    for timestamp in gps_times:
        if (
            type(timestamp) is not int
            or not 0 <= timestamp < 2**64
            or timestamp < previous
        ):
            raise ValueError("invalid_gps_order")
        previous = timestamp
    for index, point in enumerate(points):
        if (
            type(point.ordinal) is not int
            or point.ordinal != index
            or type(point.timestamp_us) is not int
            or not 0 <= point.timestamp_us < 2**64
            or not isinstance(point.event_id, str)
            or not point.event_id
            or (index and point.timestamp_us <= points[index - 1].timestamp_us)
        ):
            raise ValueError("ambiguous_state_order")
    if len({p.event_id for p in points}) != len(points):
        raise ValueError("state_identity_conflict")
    for gap in gaps:
        if (
            type(gap.start_us) is not int
            or not 0 <= gap.start_us < 2**64
            or (
                gap.end_us is not None
                and (
                    type(gap.end_us) is not int or not gap.start_us < gap.end_us < 2**64
                )
            )
        ):
            raise ValueError("invalid_recording_gap")
    times = [point.timestamp_us for point in points]
    result = []
    for timestamp in gps_times:
        index = bisect_right(times, timestamp) - 1
        if index < 0:
            result.append(StateMatch("before_first"))
        elif any(
            g.start_us <= timestamp and (g.end_us is None or timestamp < g.end_us)
            for g in gaps
        ):
            result.append(StateMatch("recording_gap"))
        elif timestamp - times[index] > max_age_us:
            result.append(StateMatch("stale"))
        else:
            result.append(
                StateMatch("matched", points[index].event_id, timestamp - times[index])
            )
    return result


def source_gaps(
    source: Path, gps_rows: list[dict[str, object]], state_rows: list[dict[str, object]]
) -> tuple[list[Gap], dict[str, object]]:
    """Recheck original framing and independently decode all selected native times."""
    validate_rows(state_rows)
    if source.stat().st_size != SOURCE_BYTES or len(gps_rows) != 21_054:
        raise ValueError("association_source_size")
    data = source.read_bytes()
    inspection = inspect_ulog(data, ULogExpectation(F09_SOURCE_ID, SOURCE_BYTES))
    if inspection.firmware_commit != FIRMWARE:
        raise ValueError("association_firmware")
    definitions = {**DEFINITIONS, GPS_STREAM: GPS_DEFINITION}
    embedded = dict(inspection.definitions)
    records: dict[str, list[tuple[int, int]]] = {}
    for name, expected in definitions.items():
        definition = embedded.get(name)
        if (
            definition is None
            or hashlib.sha256(definition.encode()).hexdigest() != expected
        ):
            raise ValueError("association_definition")
        streams = [s for s in inspection.streams if s.name == name and s.multi_id == 0]
        selected = (
            gps_rows
            if name == GPS_STREAM
            else [row for row in state_rows if row["stream"] == name]
        )
        if len(streams) != 1 or len(streams[0].record_offsets) != len(selected):
            raise ValueError("association_source_count")
        records[name] = []
        for ordinal, (offset, row) in enumerate(
            zip(streams[0].record_offsets, selected, strict=True)
        ):
            # The three pinned definitions put uint64 timestamp first in D payloads.
            timestamp = struct.unpack_from("<Q", data, offset + 5)[0]
            if (
                integer_value(row.get("source_ordinal")) != ordinal
                or integer_value(row.get("native_timestamp_us")) != timestamp
            ):
                raise ValueError("association_original_time_mismatch")
            if name == GPS_STREAM:
                expected_id = hashlib.sha256(
                    f"f09-gps-research-v1:{F09_SOURCE_ID}:{name}:0:{ordinal}".encode()
                ).hexdigest()
                if row.get("event_id") != expected_id:
                    raise ValueError("association_gps_identity")
            records[name].append((offset, timestamp))
    markers: list[int] = []
    durations: list[int] = []
    offset = 16
    while offset < len(data):
        size, kind = struct.unpack_from("<HB", data, offset)
        if kind == ord("O"):
            markers.append(offset)
            durations.append(struct.unpack_from("<H", data, offset + 3)[0])
        offset += 3 + size
    if (
        len(markers) != inspection.dropout_count
        or sum(durations) != inspection.dropout_duration_ms
    ):
        raise ValueError("association_dropout_count")
    gaps = bracket_dropouts(markers, records)
    return gaps, {
        "source_id": F09_SOURCE_ID,
        "firmware": FIRMWARE,
        "definition_sha256": definitions,
        "original_native_timestamps_match": True,
        "dropout_count": len(markers),
        "dropout_duration_ms": sum(durations),
        "dropout_masks": [
            {
                "frame_offset": offset,
                "duration_ms": duration,
                "start_us": gap.start_us,
                "end_us": gap.end_us,
            }
            for offset, duration, gap in zip(markers, durations, gaps, strict=True)
        ],
        "mask_semantics": "file-neighbor [start,end), not physical dropout times",
    }
