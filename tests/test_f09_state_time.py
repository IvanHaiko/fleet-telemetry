"""Temporal safety boundaries of the F09 research association."""

import pytest

from runtime.flight_analytics.state_time import (
    Gap,
    StatePoint,
    bracket_dropouts,
    match_states,
)


def test_past_only_age_boundary_and_dropout_mask_nulls() -> None:
    points = [StatePoint(0, 100, "a"), StatePoint(1, 200, "b")]
    matches = match_states(
        [99, 100, 150, 151, 170, 199, 200, 250, 251], points, [Gap(170, 200)], 50
    )
    assert [m.status for m in matches] == [
        "before_first",
        "matched",
        "matched",
        "stale",
        "recording_gap",
        "recording_gap",
        "matched",
        "matched",
        "stale",
    ]
    assert matches[2].event_id == "a" and matches[2].age_us == 50
    assert matches[6].event_id == "b" and matches[6].age_us == 0
    assert all(
        m.event_id is None and m.age_us is None
        for m in matches
        if m.status != "matched"
    )
    assert (
        match_states([200, 250], points, [Gap(200, None)], 50)[0].status
        == "recording_gap"
    )


def test_ambiguous_clocks_missing_ordinals_and_invalid_limits_refuse() -> None:
    points = [StatePoint(0, 100, "a"), StatePoint(1, 100, "b")]
    with pytest.raises(ValueError, match="ambiguous_state_order"):
        match_states([100], points, [], 50)
    with pytest.raises(ValueError, match="ambiguous_state_order"):
        match_states([100], [StatePoint(1, 100, "a")], [], 50)
    with pytest.raises(ValueError, match="invalid_gps_order"):
        match_states([101, 100], points[:1], [], 50)
    with pytest.raises(ValueError, match="invalid_gps_order"):
        match_states([-1], points[:1], [], 50)
    with pytest.raises(ValueError, match="invalid_state_match_input"):
        match_states([100], points[:1], [], True)


def test_file_neighbor_mask_uses_all_streams_and_exposes_unbounded_edges() -> None:
    records = {
        "gps": [(20, 100), (40, 200)],
        "land": [(22, 90), (42, 220)],
        "status": [(24, 95), (44, 210)],
    }
    assert bracket_dropouts([18, 30, 50], records) == [
        Gap(0, 100),
        Gap(90, 220),
        Gap(200, None),
    ]
    with pytest.raises(ValueError, match="ambiguous_dropout_records"):
        bracket_dropouts([30], {"gps": [(20, 100), (40, 99)]})
    with pytest.raises(ValueError, match="dropout_record_overlap"):
        bracket_dropouts([20], records)
