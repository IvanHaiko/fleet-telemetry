"""Position view rejects bad or stale updates and preserves source time."""

from typing import cast

import pytest

from telemetry.position_live import PositionView


def event(system: int = 1, boot_ms: int = 1000) -> dict[str, object]:
    return {
        "format_version": "simulated-position-v1",
        "source": "px4-sitl",
        "system_id": system,
        "boot_ms": boot_ms,
        "latitude_e7": 473_977_430,
        "longitude_e7": 85_455_950,
        "altitude_msl_mm": 489_000,
        "relative_altitude_mm": 2_500,
        "fix_type": 3,
    }


def test_position_freshness_order_and_invalid_fix() -> None:
    view = PositionView({1, 2})
    assert view.accept(event(), 100.0)
    assert not view.accept(event(), 101.0)
    assert not view.accept(event(boot_ms=999), 101.0)
    fresh = view.snapshot(102.0)["vehicles"]
    assert fresh == [
        {
            "system_id": 1,
            "status": "fresh",
            "age_seconds": 2.0,
            "boot_ms": 1000,
            "latitude_deg": 47.397743,
            "longitude_deg": 8.545595,
            "altitude_msl_m": 489.0,
            "relative_altitude_m": 2.5,
        },
        {"system_id": 2, "status": "unknown"},
    ]
    stale = cast(list[dict[str, object]], view.snapshot(104.0)["vehicles"])
    assert stale[0]["status"] == "stale"
    with pytest.raises(ValueError, match="position_invalid_fix"):
        view.accept({**event(boot_ms=1001), "fix_type": 2}, 104.0)
    with pytest.raises(ValueError, match="position_competing_measurement"):
        view.accept({**event(), "latitude_e7": 1}, 104.0)


def test_position_scope_and_limits() -> None:
    view = PositionView(set(range(1, 11)))
    assert all(view.accept(event(i), float(i)) for i in range(1, 11))
    with pytest.raises(ValueError, match="position_vehicle_scope"):
        PositionView(set(range(1, 12)))
    with pytest.raises(ValueError, match="position_identity"):
        view.accept(event(11), 20.0)
    with pytest.raises(ValueError, match="position_type"):
        view.accept({**event(), "latitude_e7": True}, 20.0)


def test_reconstructed_position_does_not_become_fresh() -> None:
    view = PositionView({1})
    assert view.accept(event(), None)
    assert view.snapshot(10.0)["vehicles"] == [{"system_id": 1, "status": "unknown"}]
    assert not view.accept(event(), 11.0)
    assert view.snapshot(11.0)["vehicles"] == [{"system_id": 1, "status": "unknown"}]
    assert view.accept(event(boot_ms=1001), 12.0)
    fresh = cast(list[dict[str, object]], view.snapshot(12.5)["vehicles"])
    assert fresh[0]["status"] == "fresh"
