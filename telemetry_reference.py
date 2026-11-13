"""Finite synthetic window calculations independent of a streaming runtime."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from typing import Literal, cast

from fleet_telemetry import BatteryEnvelope
from telemetry_reader import EnvelopeError, read_battery_event

POLICY_VERSION = "battery-window-reference-v1"
WINDOW_MS = 10_000
DEDUP_MS = 600_000
MAX_TRACE_STEPS = 1024
MAX_TRACE_BYTES = 1_048_576
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z")
_SEMANTIC_FIELDS = (
    "vehicle_id",
    "event_type",
    "source_timestamp",
    "source_log_id",
    "source_type",
    "source_stream",
    "source_record_index",
    "normalization_version",
    "source_time",
    "payload",
)


class ReferenceError(ValueError):
    """Fixed safe failure reason; never echoes supplied values."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ReferenceScope:
    dataset_run_id: str
    pipeline_version: str
    source_log_id: str
    timestamp_min: str
    timestamp_max: str


@dataclass(frozen=True)
class Observation:
    wire: bytes


@dataclass(frozen=True)
class Watermark:
    timestamp_ms: int


@dataclass(frozen=True)
class EndOfInput:
    pass


type TraceStep = Observation | Watermark | EndOfInput


@dataclass(frozen=True)
class MeasureSummary:
    count: int
    total: Fraction | None


@dataclass(frozen=True)
class BatteryWindow:
    dataset_run_id: str
    pipeline_version: str
    vehicle_id: str
    start_ms: int
    end_ms: int
    unique_events: int
    voltage: MeasureSummary
    current: MeasureSummary
    remaining: MeasureSummary


@dataclass(frozen=True)
class Disposition:
    observation_index: int
    kind: Literal["eligible", "duplicate", "late", "invalid", "conflict"]
    reason: str
    event_id: str | None


@dataclass(frozen=True)
class ReferenceResult:
    windows: tuple[BatteryWindow, ...]
    dispositions: tuple[Disposition, ...]
    conflict_free: bool
    peak_active_identities: int
    reconciled_identities: int


def _epoch_microseconds(timestamp: str) -> int:
    if not isinstance(timestamp, str) or _UTC.fullmatch(timestamp) is None:
        raise ReferenceError("invalid_timestamp")
    try:
        delta = datetime.fromisoformat(timestamp) - _EPOCH
    except ValueError:
        raise ReferenceError("invalid_timestamp") from None
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def epoch_milliseconds(timestamp: str) -> int:
    """Floor canonical UTC to epoch milliseconds, including pre-epoch values."""
    return _epoch_microseconds(timestamp) // 1000


def _scope_bounds(scope: ReferenceScope) -> tuple[int, int]:
    if not isinstance(scope, ReferenceScope):
        raise ReferenceError("invalid_scope")
    for value in (scope.dataset_run_id, scope.pipeline_version):
        if not isinstance(value, str) or re.fullmatch(r"[\x20-\x7e]+", value) is None:
            raise ReferenceError("invalid_scope")
    if (
        not isinstance(scope.source_log_id, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", scope.source_log_id) is None
    ):
        raise ReferenceError("invalid_scope")
    minimum = _epoch_microseconds(scope.timestamp_min)
    maximum = _epoch_microseconds(scope.timestamp_max)
    if minimum > maximum:
        raise ReferenceError("invalid_scope_bounds")
    return minimum, maximum


def _trace(trace: Sequence[TraceStep]) -> tuple[TraceStep, ...]:
    if not isinstance(trace, Sequence) or not 1 <= len(trace) <= MAX_TRACE_STEPS:
        raise ReferenceError("invalid_trace_size")
    steps = tuple(trace)
    if not isinstance(steps[-1], EndOfInput):
        raise ReferenceError("missing_end_of_input")
    total = 0
    watermark: int | None = None
    for index, step in enumerate(steps):
        if isinstance(step, Observation):
            if type(step.wire) is not bytes:
                raise ReferenceError("invalid_observation_type")
            total += len(step.wire)
            if total > MAX_TRACE_BYTES:
                raise ReferenceError("trace_byte_limit")
        elif isinstance(step, Watermark):
            value = step.timestamp_ms
            if type(value) is not int or not -(2**63) <= value < 2**63 - 1:
                raise ReferenceError("invalid_watermark")
            if watermark is not None and value < watermark:
                raise ReferenceError("decreasing_watermark")
            watermark = value
        elif not isinstance(step, EndOfInput) or index != len(steps) - 1:
            raise ReferenceError("invalid_trace_step")
    return steps


def _semantics(event: BatteryEnvelope) -> dict[str, object]:
    recognized = cast(dict[str, object], event)
    result = {key: recognized[key] for key in _SEMANTIC_FIELDS}
    result["quality_flags"] = sorted(event["quality_flags"])
    return result


def _summary(values: Sequence[float | None]) -> MeasureSummary:
    numbers = [Fraction(str(value)) for value in values if value is not None]
    return MeasureSummary(len(numbers), sum(numbers, Fraction()) if numbers else None)


def calculate_windows(
    scope: ReferenceScope, trace: Sequence[TraceStep]
) -> ReferenceResult:
    """Calculate controlled finite windows; never infers a watermark or source EOF."""
    minimum, maximum = _scope_bounds(scope)
    steps = _trace(trace)
    history: dict[str, dict[str, object]] = {}
    active: dict[str, int] = {}
    eligible: dict[tuple[str, int], list[BatteryEnvelope]] = {}
    dispositions: list[Disposition] = []
    watermark: int | None = None
    peak = 0
    conflict_free = True
    for step in steps:
        if isinstance(step, Watermark):
            watermark = step.timestamp_ms
            active = {
                key: expiry for key, expiry in active.items() if expiry > watermark
            }
            continue
        if isinstance(step, EndOfInput):
            break
        index = len(dispositions)
        try:
            admitted = read_battery_event(step.wire)
        except EnvelopeError:
            dispositions.append(Disposition(index, "invalid", "envelope_invalid", None))
            continue
        event_us = _epoch_microseconds(admitted["source_timestamp"])
        event_id = admitted["event_id"]
        if (
            admitted["normalization_version"] != "battery-v1"
            or admitted["source_type"] != "synthetic"
            or admitted["source_log_id"] != scope.source_log_id
            or admitted["delivery"]["dataset_run_id"] != scope.dataset_run_id
            or not minimum <= event_us <= maximum
        ):
            dispositions.append(
                Disposition(index, "invalid", "scope_mismatch", event_id)
            )
            continue
        event = cast(BatteryEnvelope, admitted)
        semantic = _semantics(event)
        previous = history.get(event_id)
        if previous is not None and previous != semantic:
            conflict_free = False
            dispositions.append(
                Disposition(index, "conflict", "identity_conflict", event_id)
            )
            continue
        history[event_id] = semantic
        if event_id in active:
            dispositions.append(
                Disposition(index, "duplicate", "identity_repeat", event_id)
            )
            continue
        event_ms = event_us // 1000
        expiry = event_ms + DEDUP_MS
        if watermark is None or expiry > watermark:
            active[event_id] = expiry
            peak = max(peak, len(active))
        start = (event_ms // WINDOW_MS) * WINDOW_MS
        if watermark is not None and watermark >= start + WINDOW_MS - 1:
            dispositions.append(Disposition(index, "late", "window_closed", event_id))
        else:
            dispositions.append(Disposition(index, "eligible", "window_open", event_id))
            eligible.setdefault((event["vehicle_id"], start), []).append(event)
    windows = []
    if conflict_free:
        for (vehicle, start), events in sorted(eligible.items()):
            windows.append(
                BatteryWindow(
                    scope.dataset_run_id,
                    scope.pipeline_version,
                    vehicle,
                    start,
                    start + WINDOW_MS,
                    len(events),
                    _summary([event["payload"]["voltage_v"] for event in events]),
                    _summary([event["payload"]["current_a"] for event in events]),
                    _summary(
                        [event["payload"]["remaining_fraction"] for event in events]
                    ),
                )
            )
    return ReferenceResult(
        tuple(windows), tuple(dispositions), conflict_free, peak, len(history)
    )
