"""Bounded live heartbeat state, independent of measurement/event-time state."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

Status = Literal["unknown", "connected", "lost"]


@dataclass
class Link:
    sequence: int = -1
    gateway_received_unix_ms: int = -1
    received_monotonic: float | None = None
    status: Status = "unknown"


class LinkWatch:
    """Caller serializes access and supplies receiver clocks for every operation."""

    def __init__(
        self,
        vehicles: list[str],
        epoch: str,
        now: float,
        timeout: float = 3.0,
        max_age: float = 1.0,
        monitor_grace: float = 0.5,
    ) -> None:
        if (
            not 1 <= len(vehicles) <= 1024
            or len(set(vehicles)) != len(vehicles)
            or any(
                not isinstance(v, str)
                or not 1 <= len(v) <= 128
                or not all(c.isascii() and (c.isalnum() or c in "-_.") for c in v)
                for v in vehicles
            )
            or not epoch
            or not all(isfinite(v) for v in (now, timeout, max_age, monitor_grace))
            or not 1 <= timeout <= 30
            or not 0 < max_age <= timeout / 2
            or not 0.1 <= monitor_grace <= 1
        ):
            raise ValueError("link_watch_configuration")
        self.links = {v: Link() for v in vehicles}
        self.epoch = epoch
        self.timeout = timeout
        self.max_age = max_age
        self.monitor_grace = monitor_grace
        self.last_tick = now

    def heartbeat(self, row: dict[str, object], now: float, unix_ms: int) -> None:
        """Retries, replay, old epochs and unknown vehicles never refresh a deadline."""
        if (
            set(row)
            != {
                "format_version",
                "receiver_epoch",
                "vehicle_id",
                "sequence",
                "gateway_received_unix_ms",
            }
            or row.get("format_version") != "live-heartbeat-v1"
        ):
            raise ValueError("link_watch_format")
        if row["receiver_epoch"] != self.epoch:
            raise ValueError("link_watch_epoch")
        vehicle = row["vehicle_id"]
        if not isinstance(vehicle, str) or vehicle not in self.links:
            raise ValueError("link_watch_vehicle")
        sequence, stamp = row["sequence"], row["gateway_received_unix_ms"]
        if (
            type(sequence) is not int
            or type(stamp) is not int
            or not 0 <= sequence < 2**63
            or not 0 <= stamp < 2**63
        ):
            raise ValueError("link_watch_fields")
        age = (unix_ms - stamp) / 1000
        if not -0.1 <= age <= self.max_age:
            raise ValueError("link_watch_stale_or_future")
        link = self.links[vehicle]
        if sequence <= link.sequence or stamp <= link.gateway_received_unix_ms:
            raise ValueError("link_watch_replayed")
        link.sequence = sequence
        link.gateway_received_unix_ms = stamp
        link.received_monotonic = now - max(0.0, age)

    def healthy(self, now: float) -> bool:
        return 0 <= now - self.last_tick <= self.monitor_grace

    def status(self, link: Link, now: float) -> Status:
        if not self.healthy(now) or link.received_monotonic is None:
            return "unknown"
        return "lost" if now - link.received_monotonic >= self.timeout else "connected"

    def tick(self, now: float) -> list[dict[str, object]]:
        """A paused monitor loses knowledge; a fresh heartbeat must re-establish it."""
        if not self.healthy(now):
            for link in self.links.values():
                link.received_monotonic = None
        self.last_tick = now
        transitions: list[dict[str, object]] = []
        for vehicle, link in self.links.items():
            status = self.status(link, now)
            if status != link.status:
                transitions.append(
                    {
                        "event": "live_link_transition",
                        "vehicle_id": vehicle,
                        "previous": link.status,
                        "status": status,
                        "gateway_received_unix_ms": (
                            None if link.sequence < 0 else link.gateway_received_unix_ms
                        ),
                    }
                )
                link.status = status
        return transitions

    def snapshot(self, now: float) -> dict[str, object]:
        return {
            "format_version": "live-link-state-v1",
            "receiver_epoch": self.epoch,
            "monitor_ok": self.healthy(now),
            "timeout_seconds": self.timeout,
            "vehicles": [
                {
                    "vehicle_id": vehicle,
                    "status": self.status(link, now),
                    "age_seconds": (
                        None
                        if link.received_monotonic is None
                        else max(0.0, now - link.received_monotonic)
                    ),
                    "last_gateway_received_unix_ms": (
                        None if link.sequence < 0 else link.gateway_received_unix_ms
                    ),
                }
                for vehicle, link in self.links.items()
            ],
        }

    def metrics(self, now: float) -> bytes:
        counts = {s: 0 for s in ("unknown", "connected", "lost")}
        for link in self.links.values():
            counts[self.status(link, now)] += 1
        values = {"monitor_ok": int(self.healthy(now)), **counts}
        return "".join(
            f"# TYPE telemetry_link_{name} gauge\ntelemetry_link_{name} {value}\n"
            for name, value in values.items()
        ).encode()
