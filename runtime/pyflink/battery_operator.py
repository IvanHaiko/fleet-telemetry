"""Managed state and event-time timers for a finite synthetic battery experiment."""

import json
from collections.abc import Iterator
from fractions import Fraction
from typing import cast

from pyflink.common import Types
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import MapState, MapStateDescriptor
from pyflink.metrics import Counter

from battery_gate import MAX_OBSERVATIONS, Admitted, BatteryScope, semantics

WINDOW_MS = 10_000
DEDUP_MS = 600_000
MEASURES = ("voltage_v", "current_a", "remaining_fraction")


class BatteryOperator(KeyedProcessFunction):
    """Keyed by run/vehicle; all windows are provisional until finite reconciliation."""

    def __init__(
        self, scope: BatteryScope, identity_limit: int = MAX_OBSERVATIONS
    ) -> None:
        if (
            type(identity_limit) is not int
            or not 1 <= identity_limit <= MAX_OBSERVATIONS
        ):
            raise ValueError("invalid_battery_identity_limit")
        self.scope = scope
        self.identity_limit = identity_limit

    def open(self, runtime_context: RuntimeContext) -> None:
        """Declare serializers and distinct active, history and aggregate state."""
        self.active: MapState[str, int] = runtime_context.get_map_state(
            MapStateDescriptor("active-identities-v1", Types.STRING(), Types.LONG())
        )
        self.history: MapState[str, str] = runtime_context.get_map_state(
            MapStateDescriptor("bounded-history-v1", Types.STRING(), Types.STRING())
        )
        self.windows: MapState[int, str] = runtime_context.get_map_state(
            MapStateDescriptor("battery-windows-v1", Types.LONG(), Types.STRING())
        )
        self.counters: dict[str, Counter] = {
            name: runtime_context.get_metrics_group().counter(name)
            for name in (
                "eligible",
                "duplicate",
                "late",
                "conflict",
                "state_limit",
                "expired",
            )
        }

    def state_counts(self) -> dict[str, int]:
        """Observe actual managed entries, not a TTL-derived memory estimate."""
        return {
            "active": len(list(self.active.keys())),
            "history": len(list(self.history.keys())),
            "windows": len(list(self.windows.keys())),
        }

    def process_element(
        self, value: Admitted, ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        """Conflict precedes duplicate; duplicate precedes closed-window routing."""
        index, vehicle, event_ms, event_id, wire = value
        event = cast(dict[str, object], json.loads(wire))
        signature = semantics(event)
        watermark = cast(int, ctx.timer_service().current_watermark())  # type: ignore[no-untyped-call]
        previous = self.history.get(event_id)
        start = event_ms // WINDOW_MS * WINDOW_MS
        kind, reason = "eligible", "window_open"
        if previous is not None and json.loads(previous) != json.loads(signature):
            kind, reason = "conflict", "identity_conflict"
        else:
            if (
                previous is None
                and len(list(self.history.keys())) >= self.identity_limit
            ):
                self.counters["state_limit"].inc()
                raise ValueError("battery_history_limit")
            self.history.put(event_id, signature)
            if self.active.contains(event_id):
                kind, reason = "duplicate", "identity_repeat"
            else:
                expiry = event_ms + DEDUP_MS
                if expiry > watermark:
                    self.active.put(event_id, expiry)
                    ctx.timer_service().register_event_time_timer(expiry)
                if watermark >= start + WINDOW_MS - 1:
                    kind, reason = "late", "window_closed"
                else:
                    self.add_window(
                        start, cast(dict[str, float | None], event["payload"])
                    )
                    ctx.timer_service().register_event_time_timer(start + WINDOW_MS - 1)
        self.counters[kind].inc()
        yield json.dumps(
            {
                "kind": "disposition",
                "observation_index": index,
                "disposition": kind,
                "reason": reason,
                "event_id": event_id,
                "watermark_ms": watermark,
                "assigned_ms": ctx.timestamp(),
                "vehicle_id": vehicle,
                "window_start_ms": start,
                "window_end_ms": start + WINDOW_MS,
                "state": self.state_counts(),
            }
        )

    def add_window(self, start: int, payload: dict[str, float | None]) -> None:
        """Accumulate exact decimal fractions without importing the reference."""
        stored = self.windows.get(start)
        row = (
            cast(dict[str, object], json.loads(stored))
            if stored
            else {
                "unique_events": 0,
                "measures": {name: [0, "0"] for name in MEASURES},
            }
        )
        row["unique_events"] = cast(int, row["unique_events"]) + 1
        measures = cast(dict[str, list[int | str]], row["measures"])
        for name in MEASURES:
            number = payload[name]
            if number is not None:
                count, total = measures[name]
                measures[name] = [
                    int(count) + 1,
                    str(Fraction(total) + Fraction(str(number))),
                ]
        self.windows.put(start, json.dumps(row))

    def on_timer(
        self, timestamp: int, ctx: KeyedProcessFunction.OnTimerContext
    ) -> Iterator[str]:
        """Actual Flink event-time callbacks flush windows and release active IDs."""
        watermark = cast(int, ctx.timer_service().current_watermark())  # type: ignore[no-untyped-call]
        start = timestamp - WINDOW_MS + 1
        stored = self.windows.get(start)
        if stored is not None:
            row = cast(dict[str, object], json.loads(stored))
            yield json.dumps(
                {
                    "kind": "window",
                    "dataset_run_id": self.scope.dataset_run_id,
                    "pipeline_version": self.scope.pipeline_version,
                    "vehicle_id": cast(tuple[str, str], ctx.get_current_key())[1],  # type: ignore[no-untyped-call]
                    "start_ms": start,
                    "end_ms": start + WINDOW_MS,
                    **row,
                    "watermark_ms": watermark,
                }
            )
            self.windows.remove(start)
        expired = [key for key, expiry in self.active.items() if expiry <= timestamp]
        for key in expired:
            self.active.remove(key)
        if expired:
            self.counters["expired"].inc(len(expired))
            yield json.dumps(
                {
                    "kind": "expiry",
                    "timer_ms": timestamp,
                    "watermark_ms": watermark,
                    "vehicle_id": cast(tuple[str, str], ctx.get_current_key())[1],  # type: ignore[no-untyped-call]
                    "expired": len(expired),
                    "event_ids": sorted(expired),
                    "active_remaining": len(list(self.active.keys())),
                }
            )
