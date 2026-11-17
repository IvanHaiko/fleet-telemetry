"""Bounded ordered recording association and strict transport output.

Checkpoints are trusted application state, not authenticated source evidence.
The reference's gap/association policy remains the authority for this profile.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

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
    _topic_id,
    make_output,
    read_output,
)
from telemetry.recording_processing import (
    MAX_AGE_US,
    _association,
    _context,
    _masked,
)
from telemetry.recording_stream import (
    STREAMS,
    event_bytes,
    event_order,
    validate_event,
)

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
    "_topic_id",
    "make_output",
    "read_output",
]

_SNAPSHOT_PROFILE = "f09-recording-runtime-state-v2"


class RecordingRuntime:
    """One ordered lane, with bounded identity retention and no history replay.

    Each GPS consumes only the latest three observations. Battery coverage keeps
    a count of observed policy boundaries and the first coverage error.
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
        self._signatures: dict[str, str] = {}
        self._lookup: Callable[[str], str | None] = self._signatures.get
        self._insert: Callable[[str, str], None] = self._signatures.__setitem__
        self._managed = False
        self._signature_count = 0
        self._current: dict[str, Document] = {}
        self._positions: dict[str, list[int]] = {}
        # Compile the fixed policy once. Unique ordered battery stamps can hit
        # each required boundary only once, including boundaries shared by gaps.
        self._gap_ends: dict[int, int | None] = {}
        self._required: set[int] = set()
        self._observed = 0
        self._gap_error: str | None = None
        gaps = self._policy["battery_gaps"]
        assert isinstance(gaps, list)  # validated by _context
        if len(gaps) > min(self._selected.battery_source_count, 50_000):
            self._gap_error = "stream_battery_gap_limit"
        predecessor_stamps = {
            event["native_timestamp_us"]
            for event in self._selected.predecessors
            if event["stream"] == STREAMS[0]
        }
        self._missing_gap_predecessor = False
        previous_end = -1
        for item in gaps:
            gap = object_value(item)
            start = integer_value(gap["start_us"])
            end = None if gap["end_us"] is None else integer_value(gap["end_us"])
            if start < previous_end:
                self._gap_error = self._gap_error or "stream_battery_gap_order"
            self._gap_ends[start] = end
            previous_end = 1 << 64 if end is None else end
            if start < self._selected.start_us < previous_end:
                # Only a context predecessor can supply this pre-interval stamp.
                self._missing_gap_predecessor = start not in predecessor_stamps
                self._required.add(start)
            for boundary in (start, end):
                if (
                    boundary is not None
                    and self._selected.start_us <= boundary < self._selected.end_us
                ):
                    self._required.add(boundary)
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
        if self._signature_count >= self.max_events:
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
        self._insert(string_value(event["measurement_id"]), signature)
        self._signature_count += 1
        if stream == STREAMS[0]:
            self._observed += int(stamp in self._required)
            previous = self._positions.get(stream)
            if previous is not None:
                prev_ordinal, prev_stamp = previous
                skipped = ordinal > prev_ordinal + 1
                if (skipped and self._gap_ends.get(prev_stamp) != stamp) or (
                    not skipped and prev_stamp in self._gap_ends
                ):
                    self._gap_error = self._gap_error or "stream_battery_gap_coverage"
            if _masked(stamp, self._selected.battery_masks):
                self._gap_error = self._gap_error or "stream_battery_gap_observation"
        self._positions[stream] = [ordinal, stamp]

    @property
    def signature_count(self) -> int:
        return self._signature_count

    @property
    def deliveries(self) -> int:
        return self._deliveries

    @property
    def order(self) -> tuple[int, int, int] | None:
        return self._order

    def accept(self, event: Document) -> Document | None:
        """Consume one delivery; exact repeats do not renew state or ordering."""
        if self._deliveries >= self.max_events:
            raise ValueError("processing_event_limit")
        row = validate_event(event)
        stamp = integer_value(row["native_timestamp_us"])
        if (
            row["run_id"] != self._selected.run_id
            or row["source_id"] != self._selected.recording.source_id
            or not self._selected.start_us <= stamp < self._selected.end_us
        ):
            raise ValueError("processing_event_scope")
        identity = string_value(row["measurement_id"])
        signature = hashlib.sha256(event_bytes(row)).hexdigest()
        previous = self._lookup(identity)
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
            "profile": self._selected.recording.name("recording-fact-v1"),
            "source_id": self._selected.recording.source_id,
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
        # Match reference order: policy shape, required boundaries, then
        # point-by-point checks (previous pair coverage before current point).
        if self._gap_error in ("stream_battery_gap_limit", "stream_battery_gap_order"):
            raise ValueError(self._gap_error)
        if self._missing_gap_predecessor:
            raise ValueError("stream_battery_gap_predecessor")
        if self._observed != len(self._required):
            raise ValueError("stream_battery_gap_observation")
        if self._gap_error:
            raise ValueError(self._gap_error)
        last = self._positions.get(STREAMS[0])
        if (
            last
            and last[0] == self._selected.battery_source_count - 1
            and last[1] in self._gap_ends
        ):
            raise ValueError("stream_battery_gap_coverage")

    def checkpoint_head(self) -> Document:
        """For immediate serialization: <=3 latest events, 4 positions and scalars."""
        return {
            "profile": _SNAPSHOT_PROFILE,
            "context_sha256": self._context_hash,
            "max_age_us": self.max_age_us,
            "max_events": self.max_events,
            "current": self._current,
            "positions": self._positions,
            "battery_boundaries_seen": self._observed,
            "battery_error": self._gap_error,
            "order": list(self._order) if self._order is not None else None,
            "deliveries": self._deliveries,
            "gps_count": self._gps_count,
            "signature_count": self._signature_count,
        }

    def snapshot(self) -> Document:
        """Standalone, detached export; never used on the operator's event path."""
        if self._managed:
            raise ValueError("recording_snapshot_managed")
        return json_object(
            _bounded_json(
                {**self.checkpoint_head(), "signatures": self._signatures},
                MAX_SNAPSHOT_BYTES,
            )
        )

    def attach_managed_signatures(
        self,
        lookup: Callable[[str], str | None],
        insert: Callable[[str, str], None],
        head: Document | None,
    ) -> None:
        """Bind a fresh runtime to the current Flink key without scanning MapState."""
        if self._managed or self._deliveries:
            raise ValueError("recording_snapshot_managed")
        for identity, signature in self._signatures.items():
            if head is None:
                insert(identity, signature)
            elif lookup(identity) != signature:
                raise ValueError("recording_snapshot_predecessors")
        self._lookup = lookup
        self._insert = insert
        self._managed = True
        if head is not None:
            self._restore_head(head)

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
        if row.get("profile") != _SNAPSHOT_PROFILE:
            raise ValueError("recording_snapshot_policy")
        signatures = object_value(row.pop("signatures", None))
        if (
            len(signatures) != row.get("signature_count")
            or len(signatures) > max_events
        ):
            raise ValueError("recording_snapshot_signatures")
        parsed = {_measurement_id(k): _digest(v) for k, v in signatures.items()}
        if any(parsed.get(k) != v for k, v in result._signatures.items()):
            raise ValueError("recording_snapshot_predecessors")
        result._signatures.update(parsed)
        result._restore_head(row)
        return result

    def _restore_head(self, row: Document) -> None:
        require_keys(row, set(self.checkpoint_head()))
        if (
            row["profile"] != _SNAPSHOT_PROFILE
            or row["context_sha256"] != self._context_hash
            or type(row["max_age_us"]) is not int
            or row["max_age_us"] != self.max_age_us
            or type(row["max_events"]) is not int
            or row["max_events"] != self.max_events
        ):
            raise ValueError("recording_snapshot_policy")
        seeds = len(self._selected.predecessors)
        count = _integer(row["signature_count"], seeds, self.max_events)
        deliveries = _integer(row["deliveries"], 0, self.max_events)
        gps_count = _integer(row["gps_count"], 0, deliveries)
        unique = count - seeds
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
                self._selected.start_us if stream == STREAMS[-1] else 0,
                self._selected.end_us - 1,
            )
            if stream == STREAMS[0] and ordinal >= self._selected.battery_source_count:
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
                or event["run_id"] != self._selected.run_id
                or parsed_positions[stream]
                != [event["source_ordinal"], event["native_timestamp_us"]]
                or self._lookup(string_value(event["measurement_id"]))
                != hashlib.sha256(event_bytes(event)).hexdigest()
            ):
                raise ValueError("recording_snapshot_current")
            if integer_value(event["native_timestamp_us"]) < self._selected.start_us:
                if event not in self._selected.predecessors:
                    raise ValueError("recording_snapshot_predecessors")
            parsed_current[stream] = event
        observed = _integer(
            row["battery_boundaries_seen"],
            self._observed,
            min(count, len(self._required)),
        )
        error = row["battery_error"]
        if error is not None and (
            not isinstance(error, str)
            or error
            not in (
                "stream_battery_gap_limit",
                "stream_battery_gap_order",
                "stream_battery_gap_observation",
                "stream_battery_gap_coverage",
            )
        ):
            raise ValueError("recording_snapshot_battery")
        if self._gap_error and error != self._gap_error:
            raise ValueError("recording_snapshot_battery")
        order = row["order"]
        parsed_order: tuple[int, int, int] | None = None
        if order is not None:
            if not isinstance(order, list) or len(order) != 3:
                raise ValueError("recording_snapshot_order")
            parsed_order = (
                _integer(order[0], self._selected.start_us, self._selected.end_us - 1),
                _integer(order[1], 0, len(STREAMS) - 1),
                _integer(order[2], 0, (1 << 64) - 1),
            )
        selected_orders = [
            (stamp, STREAMS.index(stream), ordinal)
            for stream, (ordinal, stamp) in parsed_positions.items()
            if stamp >= self._selected.start_us
        ]
        if (
            bool(deliveries) != bool(selected_orders)
            or parsed_order != max(selected_orders, default=None)
            or bool(gps_count) != (STREAMS[-1] in positions)
        ):
            raise ValueError("recording_snapshot_order")
        for stream, position in self._positions.items():
            current_position = parsed_positions.get(stream)
            if current_position is None or current_position < position:
                raise ValueError("recording_snapshot_predecessors")
        self._signature_count = count
        self._positions = parsed_positions
        self._current = parsed_current
        self._observed = observed
        self._gap_error = error
        self._order = parsed_order
        self._deliveries = deliveries
        self._gps_count = gps_count
