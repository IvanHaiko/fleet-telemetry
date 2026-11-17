"""Receipt-ordered association of a live PX4 SITL session (ADR-0054).

The runtime processes the input topic in order. Each new position takes the
latest battery summary and state that precede it in that order. They carry no
measurement time, so the association is by receipt order, never by
measurement time, and it is a function of event content in topic order: a
replay from the archive yields the same facts. Checkpoints are trusted
application state, not authenticated source evidence.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.live_event import (
    MAV_STATE_UNINIT,
    REPLAY_KIND,
    REPLAY_MAPPING_V2,
    content_signature,
    epoch_value,
    event_bytes,
    event_key,
    observation_id,
    read_event,
    source_scope,
)
from telemetry.mavlink_position import native_position, position_values
from telemetry.recording_output import MAX_EVENTS, _digest, _identifier, _source

type Document = dict[str, object]

SESSION_PROFILE = "px4-live-session-v1"
FACT_PROFILE = "px4-live-fact-v1"
OUTPUT_PROFILE = "px4-live-output-v1"
TIME_KIND = "boot_timestamp_clock_unverified"
MAX_RECEIPT_AGE_MS = 60_000
MAX_EPOCHS = 64
MAX_OUTPUT_BYTES = 16_384
MAX_HEAD_BYTES = 16_384
_STATE_PROFILE = "px4-live-runtime-state-v1"
_STATUSES = ("receipt_ordered", "stale", "unknown_after_restart", "none")


def session_config(value: Mapping[str, object]) -> Document:
    require_keys(value, {"profile", "run_id", "source", "max_receipt_age_ms"})
    if value["profile"] != SESSION_PROFILE:
        raise ValueError("live_session_profile")
    age = integer_value(value["max_receipt_age_ms"])
    if not 0 <= age <= MAX_RECEIPT_AGE_MS:
        raise ValueError("live_session_age")
    return {
        "profile": SESSION_PROFILE,
        "run_id": _identifier(value["run_id"]),
        "source": source_scope(object_value(value["source"])),
        "max_receipt_age_ms": age,
    }


def battery_values(native: Mapping[str, object]) -> Document:
    """SYS_STATUS sentinels become nulls; a summary, not a per-battery reading."""
    voltage = integer_value(native["voltage_battery"])
    current = integer_value(native["current_battery"])
    remaining = integer_value(native["battery_remaining"])
    return {
        "voltage_v": None if voltage == 65535 else voltage / 1000,
        "current_a": None if current == -1 else current / 100,
        "remaining_fraction": None if remaining == -1 else remaining / 100,
    }


def state_values(native: Mapping[str, object]) -> Document:
    """Raw PX4 mode codes; flight phases are not inferred from them."""
    base = integer_value(native["base_mode"])
    return {
        "armed": bool(base & 128),
        "base_mode_code": base,
        "custom_mode_code": integer_value(native["custom_mode"]),
        "system_status_code": integer_value(native["system_status"]),
    }


def _available(source: Mapping[str, object]) -> Mapping[str, object] | None:
    """A replay's declared availability; None for a source that sends all."""
    if source.get("kind") != REPLAY_KIND:
        return None
    return object_value(source["available"])


def shown_position(source: Mapping[str, object], native: dict[str, int]) -> Document:
    """Position values; fields the replay could not derive stay null."""
    values: Document = dict(position_values(native))
    available = _available(source)
    if available is not None:
        if not available["relative_alt"]:
            values["relative_altitude_m"] = None
        first = source.get("velocity_from_boot_ms")
        if not available["velocity"] or (
            first is not None and native["time_boot_ms"] < integer_value(first)
        ):
            values["ground_speed_m_s"] = values["down_speed_m_s"] = None
    return values


def shown_values(
    source: Mapping[str, object], stream: str, native: Mapping[str, object]
) -> Document:
    """Battery or state values; the player's own heartbeat fields stay null.

    A replay's HEARTBEAT exists to show the virtual vehicle is reachable. Its
    system status is the player's, and its armed flag and mode code are
    recorded values only where the declaration says the file supplied them.
    """
    values = battery_values(native) if stream == "battery" else state_values(native)
    available = _available(source)
    if available is None:
        return values
    if stream == "battery":
        return values if available["battery"] else dict.fromkeys(values)
    values["system_status_code"] = None
    if not available["armed"] or (
        source.get("mapping_version") == REPLAY_MAPPING_V2
        and native["system_status"] == MAV_STATE_UNINIT
    ):
        values["armed"] = values["base_mode_code"] = None
    if not available["mode"]:
        values["custom_mode_code"] = None
    return values


def _capture(event: Mapping[str, object]) -> tuple[str, int]:
    capture = object_value(event["capture"])
    return string_value(capture["epoch"]), integer_value(capture["sequence"])


class LiveRuntime:
    """One ordered lane with bounded receipt state and keyed signatures."""

    def __init__(
        self, session: Mapping[str, object], *, max_events: int = MAX_EVENTS
    ) -> None:
        self.session = session_config(session)
        self.session_sha256 = hashlib.sha256(json_line(self.session)).hexdigest()
        if type(max_events) is not int or not 1 <= max_events <= MAX_EVENTS:
            raise ValueError("live_runtime_limit")
        self.max_events = max_events
        self._signatures: dict[str, str] = {}
        self._lookup: Callable[[str], str | None] = self._signatures.get
        self._insert: Callable[[str, str], None] = self._signatures.__setitem__
        self._managed = False
        self._current: dict[str, Document] = {}
        self._last_boot_ms: int | None = None
        self._last_capture: tuple[str, int] | None = None
        self._epochs: list[str] = []
        self._deliveries = 0
        self._positions = 0
        self._signature_count = 0

    @property
    def deliveries(self) -> int:
        return self._deliveries

    @property
    def signature_count(self) -> int:
        return self._signature_count

    def accept(self, event: Mapping[str, object]) -> Document | None:
        """Consume one delivery; a repeat changes neither state nor order."""
        if self._deliveries >= self.max_events:
            raise ValueError("live_runtime_event_limit")
        row = read_event(event_bytes(event))
        if (
            row["run_id"] != self.session["run_id"]
            or row["source"] != self.session["source"]
        ):
            raise ValueError("live_runtime_scope")
        key, signature = event_key(row), content_signature(row)
        previous = self._lookup(key)
        if previous is not None:
            if previous != signature:
                raise ValueError("live_runtime_identity_conflict")
            self._deliveries += 1
            return None
        epoch, sequence = _capture(row)
        if self._last_capture is not None:
            if epoch == self._last_capture[0]:
                if sequence <= self._last_capture[1]:
                    raise ValueError("live_runtime_capture_order")
            elif epoch in self._epochs or len(self._epochs) >= MAX_EPOCHS:
                raise ValueError("live_runtime_epoch")
        boot = row["native_time_boot_ms"]
        if boot is not None and self._last_boot_ms is not None:
            if integer_value(boot) <= self._last_boot_ms:
                raise ValueError("live_runtime_position_order")
        self._insert(key, signature)
        self._signature_count += 1
        if epoch not in self._epochs:
            self._epochs.append(epoch)
        self._last_capture = (epoch, sequence)
        self._deliveries += 1
        stream = string_value(row["stream"])
        if stream != "position":
            self._current[stream] = row
            return None
        self._last_boot_ms = integer_value(boot)
        self._positions += 1
        return self._fact(row)

    def _association(self, stream: str, position: Document) -> Document:
        prior = self._current.get(stream)
        if prior is None:
            return {
                "status": "none",
                "observation_id": None,
                "receipt_age_ms": None,
                "values": None,
            }
        epoch, sequence = _capture(prior)
        identity = observation_id(epoch, sequence)
        if epoch != _capture(position)[0]:
            return {
                "status": "unknown_after_restart",
                "observation_id": identity,
                "receipt_age_ms": None,
                "values": None,
            }
        age = integer_value(position["received_unix_ms"]) - integer_value(
            prior["received_unix_ms"]
        )
        if age < 0:
            raise ValueError("live_runtime_receipt_order")
        fresh = age <= integer_value(self.session["max_receipt_age_ms"])
        values = shown_values(
            object_value(prior["source"]), stream, object_value(prior["native"])
        )
        return {
            "status": "receipt_ordered" if fresh else "stale",
            "observation_id": identity,
            "receipt_age_ms": age,
            "values": values if fresh else None,
        }

    def _fact(self, row: Document) -> Document:
        native = native_position(object_value(row["native"]))
        return {
            "profile": FACT_PROFILE,
            "run_id": self.session["run_id"],
            "source": self.session["source"],
            "measurement_id": row["measurement_id"],
            "native_time_boot_ms": row["native_time_boot_ms"],
            "time_kind": TIME_KIND,
            "capture": row["capture"],
            "received_unix_ms": row["received_unix_ms"],
            "input_event_sha256": hashlib.sha256(event_bytes(row)).hexdigest(),
            "position": shown_position(object_value(row["source"]), native),
            "battery": self._association("battery", row),
            "state": self._association("state", row),
        }

    def checkpoint_head(self) -> Document:
        """Bounded head: two latest untimed events, order and counters."""
        return {
            "profile": _STATE_PROFILE,
            "session_sha256": self.session_sha256,
            "current": self._current,
            "last_boot_ms": self._last_boot_ms,
            "last_capture": None
            if self._last_capture is None
            else list(self._last_capture),
            "epochs": self._epochs,
            "deliveries": self._deliveries,
            "positions": self._positions,
            "signature_count": self._signature_count,
        }

    def attach_managed_signatures(
        self,
        lookup: Callable[[str], str | None],
        insert: Callable[[str, str], None],
        head: Document | None,
    ) -> None:
        """Bind a fresh runtime to keyed state without scanning it."""
        if self._managed or self._deliveries:
            raise ValueError("live_runtime_managed")
        self._lookup, self._insert, self._managed = lookup, insert, True
        if head is not None:
            self._restore_head(head)

    def _restore_head(self, row: Document) -> None:
        require_keys(row, set(self.checkpoint_head()))
        if (
            row["profile"] != _STATE_PROFILE
            or row["session_sha256"] != self.session_sha256
        ):
            raise ValueError("live_runtime_state_binding")
        deliveries = integer_value(row["deliveries"])
        count = integer_value(row["signature_count"])
        positions = integer_value(row["positions"])
        if not 0 <= positions <= count <= deliveries <= self.max_events:
            raise ValueError("live_runtime_state_counts")
        listed = row["epochs"]
        if not isinstance(listed, list):
            raise ValueError("live_runtime_state_epochs")
        epochs = [epoch_value(e) for e in listed]
        if len(set(epochs)) != len(epochs) or len(epochs) > MAX_EPOCHS:
            raise ValueError("live_runtime_state_epochs")
        last = row["last_capture"]
        capture: tuple[str, int] | None = None
        if last is not None:
            if not isinstance(last, list) or len(last) != 2 or last[0] != epochs[-1]:
                raise ValueError("live_runtime_state_capture")
            capture = (epoch_value(last[0]), integer_value(last[1]))
        elif count:
            raise ValueError("live_runtime_state_capture")
        boot = row["last_boot_ms"]
        if (boot is None) != (positions == 0):
            raise ValueError("live_runtime_state_position")
        current: dict[str, Document] = {}
        for stream, value in object_value(row["current"]).items():
            event = read_event(event_bytes(object_value(value)))
            if (
                stream not in ("battery", "state")
                or event["stream"] != stream
                or event["run_id"] != self.session["run_id"]
                or event["source"] != self.session["source"]
                or _capture(event)[0] not in epochs
            ):
                raise ValueError("live_runtime_state_current")
            current[stream] = event
        self._current = current
        self._last_boot_ms = None if boot is None else integer_value(boot)
        self._last_capture = capture
        self._epochs = epochs
        self._deliveries = deliveries
        self._positions = positions
        self._signature_count = count


def _fact(value: Mapping[str, object]) -> Document:
    row = json_object(json_line(value))
    require_keys(
        row,
        {
            "profile",
            "run_id",
            "source",
            "measurement_id",
            "native_time_boot_ms",
            "time_kind",
            "capture",
            "received_unix_ms",
            "input_event_sha256",
            "position",
            "battery",
            "state",
        },
    )
    if row["profile"] != FACT_PROFILE or row["time_kind"] != TIME_KIND:
        raise ValueError("live_fact_profile")
    _identifier(row["run_id"])
    _digest(row["input_event_sha256"])
    for name in ("battery", "state"):
        association = object_value(row[name])
        require_keys(
            association, {"status", "observation_id", "receipt_age_ms", "values"}
        )
        status = association["status"]
        if status not in _STATUSES:
            raise ValueError("live_fact_status")
        if (association["values"] is None) != (status != "receipt_ordered"):
            raise ValueError("live_fact_values")
    return row


def make_output(
    fact: Mapping[str, object], source: Document, offset: int, session_sha256: str
) -> Document:
    """Wrap a fact with its input coordinate without changing its identity."""
    if type(offset) is not int or not 0 <= offset < MAX_EVENTS:
        raise ValueError("live_output_offset")
    output: Document = {
        "profile": OUTPUT_PROFILE,
        "input_source": _source({**source, "partition": source.get("partition", 0)}),
        "input_offset": offset,
        "session_sha256": _digest(session_sha256),
        "fact": _fact(fact),
    }
    if len(json_line(output)) > MAX_OUTPUT_BYTES:
        raise ValueError("live_output_size")
    return output


def read_output(raw: bytes) -> Document:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_OUTPUT_BYTES:
        raise ValueError("live_output_size")
    row = json_object(raw)
    require_keys(
        row, {"profile", "input_source", "input_offset", "session_sha256", "fact"}
    )
    if row["profile"] != OUTPUT_PROFILE:
        raise ValueError("live_output_profile")
    return make_output(
        object_value(row["fact"]),
        object_value(row["input_source"]),
        integer_value(row["input_offset"]),
        string_value(row["session_sha256"]),
    )
