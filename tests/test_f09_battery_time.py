"""Publication-time matching boundaries for the restricted F09 profile."""

import pytest

from runtime.flight_analytics.battery_time import BatteryPoint, match_publications


def test_publication_match_respects_age_and_rejected_ordinals() -> None:
    points = [
        BatteryPoint(0, 100, "a"),
        BatteryPoint(2, 200, "b"),
        BatteryPoint(3, 300, "c"),
    ]
    matches = match_publications(
        [99, 100, 101, 199, 200, 250, 251, 300, 301], points, 5, 50
    )
    assert [m.status for m in matches] == [
        "before_first",
        "matched",
        "rejection_gap",
        "rejection_gap",
        "matched",
        "matched",
        "stale",
        "matched",
        "rejection_gap",
    ]
    assert matches[5].event_id == "b" and matches[5].age_us == 50
    assert matches[2].event_id is None


def test_nonmonotonic_battery_clock_is_refused() -> None:
    with pytest.raises(ValueError, match="ambiguous_battery_order"):
        match_publications(
            [100], [BatteryPoint(0, 100, "a"), BatteryPoint(1, 100, "b")], 2, 50
        )
