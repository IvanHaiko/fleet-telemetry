"""A live session of several vehicles in one ordered lane (ADR-0060).

Each vehicle gets its own receipt-ordered `LiveRuntime` (ADR-0054); the lane
keeps the input offset contiguous for the whole session.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

from telemetry.conversion_contract import (
    integer_value,
    json_line,
    object_value,
    require_keys,
    string_value,
)
from telemetry.live_event import event_bytes, read_event
from telemetry.live_runtime import (
    MAX_HEAD_BYTES,
    MAX_RECEIPT_AGE_MS,
    SESSION_PROFILE,
    Document,
    LiveRuntime,
    session_config,
)
from telemetry.recording_output import MAX_EVENTS, _identifier

FLEET_PROFILE = "mavlink-fleet-session-v1"
MAX_VEHICLES = 8
MAX_FLEET_HEAD_BYTES = MAX_VEHICLES * MAX_HEAD_BYTES + 4096
_FLEET_STATE_PROFILE = "mavlink-fleet-runtime-state-v1"


def fleet_config(value: Mapping[str, object]) -> Document:
    """A session whose vehicles join as their first event arrives (ADR-0060)."""
    require_keys(value, {"profile", "run_id", "max_receipt_age_ms", "max_vehicles"})
    if value["profile"] != FLEET_PROFILE:
        raise ValueError("fleet_session_profile")
    age = integer_value(value["max_receipt_age_ms"])
    vehicles = integer_value(value["max_vehicles"])
    if not 0 <= age <= MAX_RECEIPT_AGE_MS or not 1 <= vehicles <= MAX_VEHICLES:
        raise ValueError("fleet_session_bounds")
    return {
        "profile": FLEET_PROFILE,
        "run_id": _identifier(value["run_id"]),
        "max_receipt_age_ms": age,
        "max_vehicles": vehicles,
    }


class FleetRuntime:
    """One ordered lane holding one receipt-ordered runtime per vehicle.

    The lane keeps the input offset contiguous for the whole session; each
    vehicle's runtime sees only its own events, so a position is associated
    only with the same vehicle's battery and state, and one vehicle's order
    or refusal never depends on another's. Signatures share one keyed store:
    positions are keyed by measurement and untimed events by gateway receipt,
    both unique across vehicles.
    """

    def __init__(
        self, session: Mapping[str, object], *, max_events: int = MAX_EVENTS
    ) -> None:
        self.session = fleet_config(session)
        self.session_sha256 = hashlib.sha256(json_line(self.session)).hexdigest()
        if type(max_events) is not int or not 1 <= max_events <= MAX_EVENTS:
            raise ValueError("fleet_runtime_limit")
        self.max_events = max_events
        self._signatures: dict[str, str] = {}
        self._lookup: Callable[[str], str | None] = self._signatures.get
        self._insert: Callable[[str, str], None] = self._signatures.__setitem__
        self._managed = False
        self._vehicles: dict[str, LiveRuntime] = {}
        self._deliveries = 0

    @property
    def deliveries(self) -> int:
        return self._deliveries

    @property
    def signature_count(self) -> int:
        return sum(item.signature_count for item in self._vehicles.values())

    @property
    def vehicles(self) -> tuple[str, ...]:
        return tuple(self._vehicles)

    def _vehicle_session(self, source: Mapping[str, object]) -> Document:
        return {
            "profile": SESSION_PROFILE,
            "run_id": self.session["run_id"],
            "source": source,
            "max_receipt_age_ms": self.session["max_receipt_age_ms"],
        }

    def _runtime(
        self, source: Mapping[str, object], head: Document | None = None
    ) -> LiveRuntime:
        vehicle = string_value(source["vehicle"])
        runtime = self._vehicles.get(vehicle)
        if runtime is None:
            if len(self._vehicles) >= integer_value(self.session["max_vehicles"]):
                raise ValueError("fleet_runtime_vehicles")
            runtime = LiveRuntime(
                self._vehicle_session(source), max_events=self.max_events
            )
            runtime.attach_managed_signatures(self._lookup, self._insert, head)
            self._vehicles[vehicle] = runtime
        elif head is not None:
            raise ValueError("fleet_runtime_state_vehicles")
        return runtime

    def accept(self, event: Mapping[str, object]) -> Document | None:
        """Consume one delivery in lane order; the vehicle's runtime decides."""
        if self._deliveries >= self.max_events:
            raise ValueError("fleet_runtime_event_limit")
        row = read_event(event_bytes(event))
        if row["run_id"] != self.session["run_id"]:
            raise ValueError("fleet_runtime_scope")
        # A vehicle keeps the scope of its first event; LiveRuntime refuses
        # a later event of the same vehicle with a different declaration.
        fact = self._runtime(object_value(row["source"])).accept(row)
        self._deliveries += 1
        return fact

    def checkpoint_head(self) -> Document:
        return {
            "profile": _FLEET_STATE_PROFILE,
            "session_sha256": self.session_sha256,
            "deliveries": self._deliveries,
            "vehicles": [
                {"source": item.session["source"], "head": item.checkpoint_head()}
                for item in self._vehicles.values()
            ],
        }

    def attach_managed_signatures(
        self,
        lookup: Callable[[str], str | None],
        insert: Callable[[str, str], None],
        head: Document | None,
    ) -> None:
        if self._managed or self._deliveries:
            raise ValueError("fleet_runtime_managed")
        self._lookup, self._insert, self._managed = lookup, insert, True
        if head is None:
            return
        require_keys(head, {"profile", "session_sha256", "deliveries", "vehicles"})
        if (
            head["profile"] != _FLEET_STATE_PROFILE
            or head["session_sha256"] != self.session_sha256
        ):
            raise ValueError("fleet_runtime_state_binding")
        listed = head["vehicles"]
        if not isinstance(listed, list) or len(listed) > integer_value(
            self.session["max_vehicles"]
        ):
            raise ValueError("fleet_runtime_state_vehicles")
        total = 0
        for item in listed:
            entry = object_value(item)
            require_keys(entry, {"source", "head"})
            runtime = self._runtime(
                object_value(entry["source"]), object_value(entry["head"])
            )
            total += runtime.deliveries
        deliveries = integer_value(head["deliveries"])
        if len(self._vehicles) != len(listed) or deliveries != total:
            raise ValueError("fleet_runtime_state_counts")
        self._deliveries = deliveries


def make_runtime(
    session: Mapping[str, object], *, max_events: int = MAX_EVENTS
) -> LiveRuntime | FleetRuntime:
    """The runtime a session declares: one SITL source, or a fleet."""
    if session.get("profile") == FLEET_PROFILE:
        return FleetRuntime(session, max_events=max_events)
    return LiveRuntime(session, max_events=max_events)


def runtime_session(value: Mapping[str, object]) -> Document:
    """Validate either session kind."""
    if value.get("profile") == FLEET_PROFILE:
        return fleet_config(value)
    return session_config(value)
