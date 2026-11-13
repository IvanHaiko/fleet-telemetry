"""F09 native-time matching with explicit uncertainty at rejected ordinals."""

from bisect import bisect_right
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BatteryPoint:
    ordinal: int
    timestamp_us: int
    event_id: str


@dataclass(frozen=True)
class Match:
    status: Literal["matched", "before_first", "stale", "rejection_gap"]
    event_id: str | None = None
    age_us: int | None = None


def match_publications(
    gps_times: list[int], points: list[BatteryPoint], source_count: int, max_age_us: int
) -> list[Match]:
    """Pair the GPS message timestamp with a preceding battery publication time.

    A rejected ordinal has no retained timestamp. After the preceding accepted
    point, the entire interval until the next accepted point is ambiguous.
    """
    if not points or source_count < 1 or not 0 <= max_age_us <= 60_000_000:
        raise ValueError("invalid_match_input")
    if any(t < 0 for t in gps_times):
        raise ValueError("invalid_gps_time")
    for i, point in enumerate(points):
        if (
            point.ordinal < 0
            or point.ordinal >= source_count
            or point.timestamp_us < 0
            or not point.event_id
        ):
            raise ValueError("invalid_battery_point")
        if i and (
            point.ordinal <= points[i - 1].ordinal
            or point.timestamp_us <= points[i - 1].timestamp_us
        ):
            raise ValueError("ambiguous_battery_order")
    times = [p.timestamp_us for p in points]
    matches = []
    for timestamp in gps_times:
        i = bisect_right(times, timestamp) - 1
        if i < 0:
            matches.append(Match("before_first"))
            continue
        point = points[i]
        age = timestamp - point.timestamp_us
        next_ordinal = points[i + 1].ordinal if i + 1 < len(points) else source_count
        if age > 0 and next_ordinal > point.ordinal + 1:
            matches.append(Match("rejection_gap"))
        elif age > max_age_us:
            matches.append(Match("stale"))
        else:
            matches.append(Match("matched", point.event_id, age))
    return matches
