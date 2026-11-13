"""Bounded ordered recording association and strict transport output.

Checkpoints are trusted application state, not authenticated source evidence.
The reference's gap/association policy remains the authority for this profile.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from telemetry.conversion_contract import (
    integer_value,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.recording_output import (
    _STATE_FIELDS,
    MAX_EVENTS,
    MAX_OUTPUT_BYTES,
    MAX_SNAPSHOT_BYTES,
    OUTPUT_PROFILE,
    Document,
    _bounded_json,
    _digest,
    _identifier,
    _integer,
    _measurement_id,
    make_output,
    read_output,
)
from telemetry.recording_processing import (
    FACT_PROFILE,
    MAX_AGE_US,
    _association,
    _context,
)
from telemetry.recording_stream import (
    STREAMS,
    event_bytes,
    event_order,
    validate_battery_gaps,
    validate_event,
)
from ulog_integrity import F09_SOURCE_ID

__all__ = [
    "_STATE_FIELDS",
    "MAX_EVENTS",
    "MAX_OUTPUT_BYTES",
    "MAX_SNAPSHOT_BYTES",
    "OUTPUT_PROFILE",
    "Document",
    "_bounded_json",
    "_digest",
    "_identifier",
    "_integer",
    "_measurement_id",
    "make_output",
    "read_output",
]

_SNAPSHOT_PROFILE = "f09-recording-runtime-state-v1"


class RecordingRuntime:
    """One ordered lane, with bounded identity retention and no history replay.

    Each GPS consumes only the latest three observations. Battery coverage keeps
    ordinal/time pairs for finish(), never historical payloads or emitted facts.
    A refused input does not partially advance processing state.
    """

    def __init__(
        self,
        context: Mapping[str, object],
        *,
        max_age_us: int = 1_000_000,
        max_events: int = MAX_EVENTS,
    ) -> None:
        self.max_age_us = _integer(max_age_us, 0, MAX_AGE_US)
        self.max_events = _integer(max_events, 1, MAX_EVENTS)
        raw = _bounded_json(dict(context), MAX_SNAPSHOT_BYTES)
        self._policy = json_object(raw)
        self._context_hash = hashlib.sha256(raw).hexdigest()
        self._selected = _context(self._policy)
        # Observation coverage is checked only at finish, when all selected
        # battery observations are available.
        self._signatures: dict[str, str] = {}
        self._current: dict[str, Document] = {}
        self._positions: dict[str, list[int]] = {}
        self._battery: list[Document] = []
        self._order: tuple[int, int, int] | None = None
        self._deliveries = 0
        self._gps_count = 0
        for event in self._selected.predecessors:
            stream = string_value(event["stream"])
            self._check_new(event)
            self._retain(event, hashlib.sha256(event_bytes(event)).hexdigest())
            self._current[stream] = event

    def _check_new(self, event: Document) -> None:
        stream = string_value(event["stream"])
        ordinal = integer_value(event["source_ordinal"])
        stamp = integer_value(event["native_timestamp_us"])
        if stream == STREAMS[0] and ordinal >= self._selected.battery_source_count:
            raise ValueError("processing_battery_count")
        if len(self._signatures) >= self.max_events:
            raise ValueError("processing_identity_limit")
        previous = self._positions.get(stream)
        if previous is not None and (
            ordinal <= previous[0]
            or stamp < previous[1]
            or (stream != STREAMS[-1] and stamp == previous[1])
        ):
            raise ValueError("processing_stream_order")

    def _retain(self, event: Document, signature: str) -> None:
        stream = string_value(event["stream"])
        ordinal = integer_value(event["source_ordinal"])
        stamp = integer_value(event["native_timestamp_us"])
        self._signatures[string_value(event["measurement_id"])] = signature
        self._positions[stream] = [ordinal, stamp]
        if stream == STREAMS[0]:
            self._battery.append(
                {
                    "stream": stream,
                    "source_ordinal": ordinal,
                    "native_timestamp_us": stamp,
                }
            )

    def accept(self, event: Document) -> Document | None:
        """Consume one delivery; exact repeats do not renew state or ordering."""
        if self._deliveries >= self.max_events:
            raise ValueError("processing_event_limit")
        row = validate_event(event)
        stamp = integer_value(row["native_timestamp_us"])
        if (
            row["run_id"] != self._selected.run_id
            or not self._selected.start_us <= stamp < self._selected.end_us
        ):
            raise ValueError("processing_event_scope")
        identity = string_value(row["measurement_id"])
        signature = hashlib.sha256(event_bytes(row)).hexdigest()
        previous = self._signatures.get(identity)
        if previous is not None:
            if previous != signature:
                raise ValueError("processing_identity_conflict")
            self._deliveries += 1
            return None
        self._check_new(row)
        order = event_order(row)
        if self._order is not None and order < self._order:
            raise ValueError("processing_event_order")
        stream = string_value(row["stream"])
        self._retain(row, signature)
        self._order = order
        self._deliveries += 1
        if stream != STREAMS[-1]:
            self._current[stream] = row
            return None
        self._gps_count += 1
        return {
            "profile": FACT_PROFILE,
            "source_id": F09_SOURCE_ID,
            "run_id": self._selected.run_id,
            "measurement_id": identity,
            "native_timestamp_us": stamp,
            "input_event_sha256": signature,
            "inspection": {
                "gps": row["payload"],
                "battery": _association(
                    self._current.get(STREAMS[0]),
                    stamp,
                    self._selected.battery_masks,
                    "rejection_gap",
                    self.max_age_us,
                ),
                "states": {
                    name: _association(
                        self._current.get(f"{name}:0"),
                        stamp,
                        self._selected.state_masks,
                        "recording_gap",
                        self.max_age_us,
                    )
                    for name in _STATE_FIELDS
                },
            },
        }

    def finish(self) -> None:
        """Check all available mask/ordinal evidence without claiming completeness."""
        if not self._gps_count:
            raise ValueError("processing_empty_gps_interval")
        validate_battery_gaps(self._battery, self._policy)

    def snapshot(self) -> Document:
        """Return detached JSON-native state, including late-duplicate signatures."""
        return json_object(
            _bounded_json(
                {
                    "profile": _SNAPSHOT_PROFILE,
                    "context_sha256": self._context_hash,
                    "max_age_us": self.max_age_us,
                    "max_events": self.max_events,
                    "signatures": self._signatures,
                    "current": self._current,
                    "positions": self._positions,
                    "battery": self._battery,
                    "order": list(self._order) if self._order is not None else None,
                    "deliveries": self._deliveries,
                    "gps_count": self._gps_count,
                },
                MAX_SNAPSHOT_BYTES,
            )
        )

    @classmethod
    def restore(
        cls,
        context: Mapping[str, object],
        snapshot: Document,
        *,
        max_age_us: int = 1_000_000,
        max_events: int = MAX_EVENTS,
    ) -> RecordingRuntime:
        """Validate bounded trusted state; checkpoint authenticity is out of scope."""
        result = cls(context, max_age_us=max_age_us, max_events=max_events)
        row = json_object(_bounded_json(snapshot, MAX_SNAPSHOT_BYTES))
        require_keys(row, set(result.snapshot()))
        if (
            row["profile"] != _SNAPSHOT_PROFILE
            or row["context_sha256"] != result._context_hash
            or type(row["max_age_us"]) is not int
            or row["max_age_us"] != max_age_us
            or type(row["max_events"]) is not int
            or row["max_events"] != max_events
        ):
            raise ValueError("recording_snapshot_policy")
        signatures = object_value(row["signatures"])
        if not len(result._signatures) <= len(signatures) <= max_events:
            raise ValueError("recording_snapshot_signatures")
        parsed_signatures = {
            _measurement_id(k): _digest(v) for k, v in signatures.items()
        }
        if any(parsed_signatures.get(k) != v for k, v in result._signatures.items()):
            raise ValueError("recording_snapshot_predecessors")
        deliveries = _integer(row["deliveries"], 0, max_events)
        gps_count = _integer(row["gps_count"], 0, deliveries)
        unique = len(signatures) - len(result._signatures)
        if not gps_count <= unique <= deliveries:
            raise ValueError("recording_snapshot_counts")
        positions = object_value(row["positions"])
        if positions.keys() - set(STREAMS):
            raise ValueError("recording_snapshot_stream")
        parsed_positions: dict[str, list[int]] = {}
        for stream, value in positions.items():
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("recording_snapshot_position")
            ordinal = _integer(value[0], 0, (1 << 64) - 1)
            stamp = _integer(
                value[1],
                result._selected.start_us if stream == STREAMS[-1] else 0,
                result._selected.end_us - 1,
            )
            if (
                stream == STREAMS[0]
                and ordinal >= result._selected.battery_source_count
            ):
                raise ValueError("processing_battery_count")
            parsed_positions[stream] = [ordinal, stamp]
        current = object_value(row["current"])
        if set(current) != set(positions) - {STREAMS[-1]}:
            raise ValueError("recording_snapshot_current")
        parsed_current: dict[str, Document] = {}
        for stream, value in current.items():
            event = validate_event(object_value(value))
            if (
                event["stream"] != stream
                or event["run_id"] != result._selected.run_id
                or parsed_positions[stream]
                != [event["source_ordinal"], event["native_timestamp_us"]]
                or parsed_signatures.get(string_value(event["measurement_id"]))
                != hashlib.sha256(event_bytes(event)).hexdigest()
            ):
                raise ValueError("recording_snapshot_current")
            if integer_value(event["native_timestamp_us"]) < result._selected.start_us:
                if event not in result._selected.predecessors:
                    raise ValueError("recording_snapshot_predecessors")
            parsed_current[stream] = event
        raw_battery = row["battery"]
        if not isinstance(raw_battery, list) or len(raw_battery) > len(signatures):
            raise ValueError("recording_snapshot_battery")
        battery: list[Document] = []
        prior_ordinal = prior_stamp = -1
        for value in raw_battery:
            point = object_value(value)
            require_keys(point, {"stream", "source_ordinal", "native_timestamp_us"})
            ordinal = _integer(
                point["source_ordinal"], 0, result._selected.battery_source_count - 1
            )
            stamp = _integer(
                point["native_timestamp_us"], 0, result._selected.end_us - 1
            )
            if (
                point["stream"] != STREAMS[0]
                or ordinal <= prior_ordinal
                or stamp <= prior_stamp
                or (stamp < result._selected.start_us and point not in result._battery)
            ):
                raise ValueError("recording_snapshot_battery")
            battery.append(point)
            prior_ordinal, prior_stamp = ordinal, stamp
        last_battery_position = [prior_ordinal, prior_stamp]
        if (
            (battery and parsed_positions.get(STREAMS[0]) != last_battery_position)
            or bool(battery) != (STREAMS[0] in parsed_positions)
            or battery[: len(result._battery)] != result._battery
        ):
            raise ValueError("recording_snapshot_battery")
        order = row["order"]
        parsed_order: tuple[int, int, int] | None = None
        if order is not None:
            if not isinstance(order, list) or len(order) != 3:
                raise ValueError("recording_snapshot_order")
            parsed_order = (
                _integer(
                    order[0], result._selected.start_us, result._selected.end_us - 1
                ),
                _integer(order[1], 0, len(STREAMS) - 1),
                _integer(order[2], 0, (1 << 64) - 1),
            )
        selected_orders = [
            (stamp, STREAMS.index(stream), ordinal)
            for stream, (ordinal, stamp) in parsed_positions.items()
            if stamp >= result._selected.start_us
        ]
        if (
            bool(deliveries) != bool(selected_orders)
            or parsed_order != max(selected_orders, default=None)
            or bool(gps_count) != (STREAMS[-1] in positions)
        ):
            raise ValueError("recording_snapshot_order")
        for stream, position in result._positions.items():
            current_position = parsed_positions.get(stream)
            if current_position is None or current_position < position:
                raise ValueError("recording_snapshot_predecessors")
        result._signatures = parsed_signatures
        result._positions = parsed_positions
        result._current = parsed_current
        result._battery = battery
        result._order = parsed_order
        result._deliveries = deliveries
        result._gps_count = gps_count
        return result
