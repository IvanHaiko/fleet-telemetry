"""Bounded PX4 SITL observations with explicit source time and receipt freshness."""

import math
from dataclasses import dataclass

from telemetry.link_watch import LinkWatch
from telemetry.mavlink_position import (
    integer_field as _integer,
)
from telemetry.mavlink_position import (
    native_position,
    position_identity,
    position_values,
)


@dataclass
class Observation:
    values: dict[str, int | float | None]
    received: float | None
    boot_ms: int | None = None
    event_id: str | None = None
    qualification: str = "received"
    source_time_raw_us: str | None = None


class MavlinkView:
    """One configured simulation source. Caller serializes all state access."""

    def __init__(
        self,
        vehicle: str,
        boot_session: str,
        system: int,
        component: int,
        epoch: str,
        now: float,
    ) -> None:
        if (
            not 1 <= len(boot_session) <= 128
            or not all(
                c.isascii() and (c.isalnum() or c in "-_.") for c in boot_session
            )
            or type(system) is not int
            or not 1 <= system <= 255
            or type(component) is not int
            or not 1 <= component <= 255
        ):
            raise ValueError("mavlink_source_scope")
        self.vehicle, self.boot_session = vehicle, boot_session
        self.system, self.component = system, component
        self.watch = LinkWatch([vehicle], epoch, now)
        self.observations: dict[str, Observation] = {}
        self.last_position: tuple[int, ...] | None = None
        self.last_poll: float | None = None
        self.failure: str | None = None
        self.sequence = 0
        self.accepted = self.rejected = self.ignored = 0

    def poll(self, now: float) -> None:
        if not math.isfinite(now):
            raise ValueError("mavlink_clock")
        if self.last_poll is not None and not 0 <= now - self.last_poll <= 0.5:
            for observation in self.observations.values():
                observation.received = None
            self.watch.links[self.vehicle].received_monotonic = None
        self.last_poll = now

    def accept(
        self,
        kind: str,
        data: dict[str, object],
        system: int,
        component: int,
        now: float,
        unix_ms: int,
    ) -> bool:
        """Observe received packets; unsigned heartbeat replay is not detectable."""
        if (system, component) != (self.system, self.component) or self.failure:
            self.rejected += 1
            return False
        if kind not in {
            "HEARTBEAT",
            "GPS_RAW_INT",
            "GLOBAL_POSITION_INT",
            "SYS_STATUS",
        }:
            self.ignored += 1
            return False
        try:
            accepted = self._accept(kind, data, now, unix_ms)
        except ValueError:
            self.rejected += 1
            raise
        if accepted:
            self.accepted += 1
        else:
            self.rejected += 1
        return accepted

    def _accept(
        self, kind: str, data: dict[str, object], now: float, unix_ms: int
    ) -> bool:
        if not math.isfinite(now):
            raise ValueError("mavlink_clock")
        if kind == "HEARTBEAT":
            if _integer(data, "autopilot", 0, 255) != 12:
                raise ValueError("mavlink_not_px4")
            mode = _integer(data, "base_mode", 0, 255)
            custom = _integer(data, "custom_mode", 0, 2**32 - 1)
            status = _integer(data, "system_status", 0, 255)
            self.watch.heartbeat(
                {
                    "format_version": "live-heartbeat-v1",
                    "receiver_epoch": self.watch.epoch,
                    "vehicle_id": self.vehicle,
                    "sequence": self.sequence,
                    "gateway_received_unix_ms": unix_ms,
                },
                now,
                unix_ms,
            )
            self.sequence += 1
            self.observations["state"] = Observation(
                {
                    "armed_flag": int(bool(mode & 128)),
                    "base_mode_code": mode,
                    "custom_mode_code": custom,
                    "system_status_code": status,
                },
                now,
            )
        elif kind == "GPS_RAW_INT":
            fix_code = _integer(data, "fix_type", 0, 8)
            raw_time = (
                str(_integer(data, "time_usec", 0, 2**64 - 1))
                if "time_usec" in data
                else None
            )
            self.observations["gps_fix"] = Observation(
                {"fix_type": fix_code}, now, source_time_raw_us=raw_time
            )
        elif kind == "SYS_STATUS":
            voltage = _integer(data, "voltage_battery", 0, 65535)
            current = _integer(data, "current_battery", -32768, 32767)
            remaining = _integer(data, "battery_remaining", -1, 100)
            self.observations["battery"] = Observation(
                {
                    "voltage_v": None if voltage == 65535 else voltage / 1000,
                    "current_a": None if current == -1 else current / 100,
                    "remaining_fraction": None if remaining == -1 else remaining / 100,
                },
                now,
            )
        else:
            native = native_position(data)
            boot = native["time_boot_ms"]
            content = tuple(
                native[name]
                for name in (
                    "time_boot_ms",
                    "lat",
                    "lon",
                    "alt",
                    "relative_alt",
                    "vx",
                    "vy",
                    "vz",
                )
            )
            if self.last_position is not None:
                if boot < self.last_position[0]:
                    self.failure = "source_clock_reset_requires_new_boot_session"
                    return False
                if boot == self.last_position[0]:
                    if content != self.last_position:
                        self.failure = "competing_position_at_source_time"
                    return False
            self.last_position = content
            fix = self.observations.get("gps_fix")
            qualified = (
                fix is not None
                and fix.received is not None
                and 0 <= now - fix.received <= 3
                and fix.values["fix_type"] is not None
                and fix.values["fix_type"] >= 3
            )
            values: dict[str, int | float | None] = dict(position_values(native))
            identity = position_identity(
                self.boot_session, self.system, self.component, boot
            )
            self.observations["position"] = Observation(
                values if qualified else dict.fromkeys(values),
                now,
                boot,
                identity,
                "fix_qualified" if qualified else "unqualified_fix",
            )
        return True

    def snapshot(self, now: float) -> dict[str, object]:
        healthy = (
            self.failure is None
            and self.last_poll is not None
            and 0 <= now - self.last_poll <= 0.5
            and self.watch.healthy(now)
        )
        groups: dict[str, object] = {}
        for name in ("position", "battery", "state", "gps_fix"):
            observation = self.observations.get(name)
            age = (
                None
                if observation is None or observation.received is None
                else now - observation.received
            )
            status = (
                "unknown"
                if not healthy or age is None or age < 0
                else "stale"
                if age >= 3
                else "fresh"
            )
            if name == "position" and observation is not None:
                fix = self.observations.get("gps_fix")
                valid_fix = (
                    fix is not None
                    and fix.received is not None
                    and 0 <= now - fix.received < 3
                    and fix.values["fix_type"] is not None
                    and fix.values["fix_type"] >= 3
                )
                if status == "fresh" and (
                    not valid_fix or observation.qualification == "unqualified_fix"
                ):
                    status = "unqualified_fix"
            groups[name] = {
                "status": status,
                "receipt_age_seconds": age,
                "source_boot_ms": None if observation is None else observation.boot_ms,
                "event_id": None if observation is None else observation.event_id,
                "values": None
                if observation is None or status == "unknown"
                else observation.values,
                "source_time_raw_us": (
                    None if observation is None else observation.source_time_raw_us
                ),
                "time_kind": "source_boot_timestamp"
                if name == "position"
                else "raw_timestamp_clock_unverified"
                if name == "gps_fix"
                else "measurement_time_not_provided",
            }
        link = self.watch.snapshot(now)
        return {
            "format_version": "px4-mavlink-live-view-v1",
            "source_kind": "px4-sitl",
            "source_boot_session": self.boot_session,
            "receiver_epoch": self.watch.epoch,
            "vehicle_id": self.vehicle,
            "gateway_ok": healthy,
            "cause": self.failure,
            "connection": self.watch.status(self.watch.links[self.vehicle], now)
            if healthy
            else "unknown",
            "heartbeat": link,
            "groups": groups,
            "counts": {
                "accepted": self.accepted,
                "rejected": self.rejected,
                "ignored": self.ignored,
            },
            "security": "unsigned local MAVLink; no general replay protection",
        }
