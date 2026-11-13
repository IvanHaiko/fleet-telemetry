"""Bounded latest-value projection of eligible facts produced by Flink Battery."""

import json
from typing import cast

from telemetry_reader import read_battery_event
from telemetry_reference import epoch_milliseconds


class LiveState:
    """Caller serializes access. Replayed output never moves a vehicle backwards."""

    def __init__(self, run: str, source_logs: dict[str, str]) -> None:
        if not 1 <= len(source_logs) <= 1024:
            raise ValueError("live_vehicle_bound")
        self.run, self.source_logs = run, source_logs
        self.values: dict[str, dict[str, object]] = {}
        self.received_at: dict[str, float] = {}
        self.polled_at: float | None = None
        self.ready = False
        self.error: str | None = None

    def accept(
        self, body: bytes, unix_ms: int, live_monotonic: float | None = None
    ) -> bool:
        if len(body) > 131072:
            raise ValueError("live_fact_bound")
        fact = cast(dict[str, object], json.loads(body))
        if (
            fact.get("format_version") != "continuous-processing-v1"
            or fact.get("run_id") != self.run
        ):
            raise ValueError("live_fact_scope")
        if fact.get("kind") != "event" or fact.get("disposition") != "eligible":
            return False
        event = read_battery_event(json.dumps(fact["event"]).encode())
        vehicle = event["vehicle_id"]
        if self.source_logs.get(vehicle) != event["source_log_id"]:
            raise ValueError("live_vehicle_scope")
        stamp = epoch_milliseconds(event["source_timestamp"])
        previous = self.values.get(vehicle)
        if previous:
            if stamp < cast(int, previous["measurement_ms"]):
                return False
            if stamp == previous["measurement_ms"]:
                if (
                    previous["event_id"] != event["event_id"]
                    or previous["semantic_sha256"] != fact["semantic_sha256"]
                ):
                    raise ValueError("live_competing_measurement")
                return False
        self.values[vehicle] = {
            "vehicle_id": vehicle,
            "event_id": event["event_id"],
            "measurement_ms": stamp,
            "source_timestamp": event["source_timestamp"],
            "ingest_timestamp": event["ingest_timestamp"],
            "payload": event["payload"],
            "semantic_sha256": fact["semantic_sha256"],
            "source": fact["source"],
            "live_received_unix_ms": unix_ms,
        }
        if live_monotonic is None:
            self.received_at.pop(vehicle, None)
        else:
            self.received_at[vehicle] = live_monotonic
        return True

    def snapshot(self, now: float) -> dict[str, object]:
        healthy = (
            self.ready
            and self.error is None
            and self.polled_at is not None
            and 0 <= now - self.polled_at <= 1
        )
        return {
            "format_version": "flink-live-state-v1",
            "run_id": self.run,
            "collection_ok": healthy,
            "error": self.error,
            "vehicles": [self._vehicle(v, now, healthy) for v in self.source_logs],
        }

    def _vehicle(self, vehicle: str, now: float, healthy: bool) -> dict[str, object]:
        row = self.values.get(vehicle)
        if row is None:
            return {"vehicle_id": vehicle, "payload": None}
        received = self.received_at.get(vehicle)
        age = now - received if received is not None else None
        if not healthy or age is None or age < 0:
            return {**row, "live_age_seconds": None, "admission_to_live_ms": None}
        delay = cast(int, row["live_received_unix_ms"]) - epoch_milliseconds(
            cast(str, row["ingest_timestamp"])
        )
        return {
            **row,
            "live_age_seconds": age,
            "admission_to_live_ms": delay if delay >= 0 else None,
        }
