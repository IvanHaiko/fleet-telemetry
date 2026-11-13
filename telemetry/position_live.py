"""Bounded, simulation-only latest-position view for decoded position messages."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast


@dataclass(frozen=True)
class Position:
    system_id: int
    boot_ms: int
    latitude_deg: float
    longitude_deg: float
    altitude_msl_m: float
    relative_altitude_m: float
    observed_monotonic: float | None


class PositionView:
    """Keep only newer source times; a caller must serialize access."""

    def __init__(self, vehicle_ids: set[int], stale_after: float = 3.0) -> None:
        if not 1 <= len(vehicle_ids) <= 10 or any(
            type(value) is not int or not 1 <= value <= 255 for value in vehicle_ids
        ):
            raise ValueError("position_vehicle_scope")
        if not math.isfinite(stale_after) or not 0 < stale_after <= 60:
            raise ValueError("position_stale_after")
        self.vehicle_ids = frozenset(vehicle_ids)
        self.stale_after = stale_after
        self.positions: dict[int, Position] = {}

    def accept(self, row: dict[str, object], observed: float | None) -> bool:
        if set(row) != {
            "format_version",
            "source",
            "system_id",
            "boot_ms",
            "latitude_e7",
            "longitude_e7",
            "altitude_msl_mm",
            "relative_altitude_mm",
            "fix_type",
        }:
            raise ValueError("position_fields")
        if (
            row["format_version"] != "simulated-position-v1"
            or row["source"] != "px4-sitl"
        ):
            raise ValueError("position_source")
        names = (
            "system_id",
            "boot_ms",
            "latitude_e7",
            "longitude_e7",
            "altitude_msl_mm",
            "relative_altitude_mm",
            "fix_type",
        )
        if any(type(row[name]) is not int for name in names) or (
            observed is not None and not math.isfinite(observed)
        ):
            raise ValueError("position_type")
        system_id = cast(int, row["system_id"])
        boot_ms = cast(int, row["boot_ms"])
        lat = cast(int, row["latitude_e7"])
        lon = cast(int, row["longitude_e7"])
        fix = cast(int, row["fix_type"])
        if system_id not in self.vehicle_ids or not 0 <= boot_ms <= 0xFFFFFFFF:
            raise ValueError("position_identity")
        if any(
            not -(2**31) <= cast(int, row[name]) < 2**31
            for name in ("altitude_msl_mm", "relative_altitude_mm")
        ):
            raise ValueError("position_altitude_range")
        if (
            not 3 <= fix <= 8
            or not -900_000_000 <= lat <= 900_000_000
            or not -1_800_000_000 <= lon <= 1_800_000_000
        ):
            raise ValueError("position_invalid_fix")
        position = Position(
            system_id,
            boot_ms,
            lat / 10_000_000,
            lon / 10_000_000,
            cast(int, row["altitude_msl_mm"]) / 1_000,
            cast(int, row["relative_altitude_mm"]) / 1_000,
            observed,
        )
        previous = self.positions.get(system_id)
        if previous and boot_ms < previous.boot_ms:
            return False
        if previous and boot_ms == previous.boot_ms:
            if (
                previous.latitude_deg,
                previous.longitude_deg,
                previous.altitude_msl_m,
                previous.relative_altitude_m,
            ) != (
                position.latitude_deg,
                position.longitude_deg,
                position.altitude_msl_m,
                position.relative_altitude_m,
            ):
                raise ValueError("position_competing_measurement")
            return False
        self.positions[system_id] = position
        return True

    def snapshot(self, now: float) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        for system_id in sorted(self.vehicle_ids):
            position = self.positions.get(system_id)
            age = (
                None
                if position is None or position.observed_monotonic is None
                else now - position.observed_monotonic
            )
            if position is None or age is None or age < 0:
                rows.append({"system_id": system_id, "status": "unknown"})
                continue
            rows.append(
                {
                    "system_id": system_id,
                    "status": "fresh" if age <= self.stale_after else "stale",
                    "age_seconds": age,
                    "boot_ms": position.boot_ms,
                    "latitude_deg": position.latitude_deg,
                    "longitude_deg": position.longitude_deg,
                    "altitude_msl_m": position.altitude_msl_m,
                    "relative_altitude_m": position.relative_altitude_m,
                }
            )
        return {"format_version": "simulated-position-view-v1", "vehicles": rows}
