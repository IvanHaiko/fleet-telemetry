"""Independent authored cases for docs/reference/m3-window-reference.md."""

import copy
import hashlib
import json
from fractions import Fraction
from typing import cast

import pytest

from telemetry_reference import (
    DEDUP_MS,
    MAX_TRACE_BYTES,
    MAX_TRACE_STEPS,
    POLICY_VERSION,
    WINDOW_MS,
    BatteryWindow,
    EndOfInput,
    Observation,
    ReferenceError,
    ReferenceResult,
    ReferenceScope,
    TraceStep,
    Watermark,
    calculate_windows,
    epoch_milliseconds,
)

SOURCE = "sha256:" + "a" * 64


def scope(**changes: str) -> ReferenceScope:
    values = dict(
        dataset_run_id="test-run",
        pipeline_version="test-pipeline",
        source_log_id=SOURCE,
        timestamp_min="1969-12-31T23:00:00.000000Z",
        timestamp_max="1970-01-02T00:00:00.000000Z",
    )
    values.update(changes)
    return ReferenceScope(**values)


def event(
    index: int = 0,
    timestamp: str = "1970-01-01T00:00:00.000000Z",
    vehicle: str = "vehicle-a",
    voltage: float = 1.1,
    current: float | None = None,
    remaining: float | None = None,
) -> dict[str, object]:
    # Independent standard datetime arithmetic implements the documented fixture clock.
    from datetime import datetime

    delta = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ") - datetime(
        1969, 12, 31, 23
    )
    native_us = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
    identity = [
        "event-id-v1",
        "synthetic",
        SOURCE,
        vehicle,
        "battery_status:0",
        index,
        "telemetry.battery",
        "battery-v1",
    ]
    digest = hashlib.sha256(
        json.dumps(identity, separators=(",", ":")).encode()
    ).hexdigest()
    flags = ["synthetic_time_anchor"]
    if current is None or remaining is None:
        flags.append("source_value_missing")
    return dict(
        event_id="sha256:" + digest,
        vehicle_id=vehicle,
        event_type="telemetry.battery",
        schema_version="1.0.0",
        source_timestamp=timestamp,
        ingest_timestamp="1970-01-02T00:00:00.000000Z",
        source_log_id=SOURCE,
        source_type="synthetic",
        source_stream="battery_status:0",
        source_record_index=index,
        normalization_version="battery-v1",
        source_time=dict(
            clock_basis="boot_relative",
            native_timestamp_us=native_us,
            timestamp_kind="measurement",
            mapping=dict(
                native_anchor_us=0,
                utc_anchor="1969-12-31T23:00:00.000000Z",
                anchor_kind="synthetic_fixed",
                anchor_uncertainty_us=None,
            ),
        ),
        provenance=dict(
            source_manifest_id="authored-test-manifest",
            privacy_classification="synthetic",
        ),
        quality_flags=flags,
        payload=dict(
            voltage_v=voltage, current_a=current, remaining_fraction=remaining
        ),
        delivery=dict(dataset_run_id="test-run", replay_mode="synthetic"),
    )


def obs(value: dict[str, object]) -> Observation:
    return Observation(json.dumps(value, separators=(",", ":")).encode())


def run(*steps: TraceStep) -> ReferenceResult:
    return calculate_windows(scope(), [*steps, EndOfInput()])


def kinds(result: ReferenceResult) -> list[tuple[int, str, str]]:
    return [(d.observation_index, d.kind, d.reason) for d in result.dispositions]


def summary(
    window: BatteryWindow,
) -> tuple[int, int, Fraction | None, int, Fraction | None, int, Fraction | None]:
    return (
        window.unique_events,
        window.voltage.count,
        window.voltage.total,
        window.current.count,
        window.current.total,
        window.remaining.count,
        window.remaining.total,
    )


def test_policy_and_explicit_empty_completion() -> None:
    assert (POLICY_VERSION, WINDOW_MS, DEDUP_MS, MAX_TRACE_STEPS, MAX_TRACE_BYTES) == (
        "battery-window-reference-v1",
        10000,
        600000,
        1024,
        1048576,
    )
    result = run()
    assert cast(object, result.windows) == result.dispositions == ()
    assert result.conflict_free is True
    assert (result.peak_active_identities, result.reconciled_identities) == (0, 0)


@pytest.mark.parametrize(
    "timestamp, expected",
    [
        ("1970-01-01T00:00:00.000000Z", 0),
        ("1970-01-01T00:00:00.000999Z", 0),
        ("1970-01-01T00:00:00.001000Z", 1),
        ("1969-12-31T23:59:59.999999Z", -1),
        ("1969-12-31T23:59:59.998999Z", -2),
        ("0001-01-01T00:00:00.000000Z", -62135596800000),
        ("9999-12-31T23:59:59.999999Z", 253402300799999),
    ],
)
def test_exact_epoch_floor(timestamp: str, expected: int) -> None:
    assert epoch_milliseconds(timestamp) == expected


def test_window_boundaries_vehicle_sorting_and_equal_timestamps() -> None:
    records = [
        event(0, "1970-01-01T00:00:10.000000Z", "vehicle-b"),
        event(1, "1969-12-31T23:59:59.999999Z"),
        event(2, "1970-01-01T00:00:09.999999Z"),
        event(3),
        event(4),
    ]
    before = copy.deepcopy(records)
    result = run(*(obs(e) for e in records))
    assert [
        (w.vehicle_id, w.start_ms, w.end_ms, w.unique_events) for w in result.windows
    ] == [
        ("vehicle-a", -10000, 0, 1),
        ("vehicle-a", 0, 10000, 3),
        ("vehicle-b", 10000, 20000, 1),
    ]
    assert all(
        w.dataset_run_id == "test-run" and w.pipeline_version == "test-pipeline"
        for w in result.windows
    )
    assert records == before
    assert result.reconciled_identities == result.peak_active_identities == 5


def test_exact_decimal_sums_null_and_zero_counts() -> None:
    result = run(
        obs(event(0, voltage=0.1, current=-0.2, remaining=0)),
        obs(event(1, voltage=0.2, current=0, remaining=1)),
        obs(event(2)),
    )
    assert summary(result.windows[0]) == (
        3,
        3,
        Fraction(7, 5),
        2,
        Fraction(-1, 5),
        2,
        Fraction(1),
    )
    nulls = run(obs(event()))
    assert summary(nulls.windows[0]) == (1, 1, Fraction(11, 10), 0, None, 0, None)


def test_duplicate_metadata_flags_and_missing_optional_normalization() -> None:
    first = event()
    repeated = copy.deepcopy(first)
    repeated["ingest_timestamp"] = "1970-01-03T00:00:00.000000Z"
    cast(dict[str, object], repeated["provenance"])["source_manifest_id"] = (
        "other-authored-manifest"
    )
    cast(dict[str, object], repeated["delivery"])["extra"] = "ignored"
    cast(list[str], repeated["quality_flags"]).reverse()
    del cast(dict[str, object], repeated["payload"])["current_a"]
    del cast(dict[str, object], repeated["payload"])["remaining_fraction"]
    result = run(obs(first), obs(repeated))
    assert kinds(result) == [
        (0, "eligible", "window_open"),
        (1, "duplicate", "identity_repeat"),
    ]
    assert result.dispositions[1].event_id == first["event_id"]
    assert summary(result.windows[0])[0] == 1
    assert result.conflict_free and result.reconciled_identities == 1


def test_close_boundary_active_duplicate_and_late_first_identity() -> None:
    result = run(
        Watermark(9998),
        obs(event()),
        Watermark(9999),
        obs(event()),
        obs(event(1)),
        obs(event(1)),
    )
    assert kinds(result) == [
        (0, "eligible", "window_open"),
        (1, "duplicate", "identity_repeat"),
        (2, "late", "window_closed"),
        (3, "duplicate", "identity_repeat"),
    ]
    assert result.windows[0].unique_events == 1
    assert result.peak_active_identities == result.reconciled_identities == 2


def test_expiry_equality_no_refresh_and_late_after_expiry() -> None:
    result = run(
        obs(event()),
        Watermark(599999),
        obs(event()),
        Watermark(600000),
        obs(event()),
        obs(event()),
    )
    assert kinds(result) == [
        (0, "eligible", "window_open"),
        (1, "duplicate", "identity_repeat"),
        (2, "late", "window_closed"),
        (3, "late", "window_closed"),
    ]
    assert result.peak_active_identities == result.reconciled_identities == 1
    assert result.windows[0].unique_events == 1


@pytest.mark.parametrize("expire", [False, True])
def test_semantic_conflict_precedes_duplicate_or_late_and_suppresses_all_windows(
    expire: bool,
) -> None:
    original = event()
    changed = copy.deepcopy(original)
    cast(dict[str, object], changed["payload"])["voltage_v"] = 2
    steps: list[TraceStep] = [obs(original), obs(event(1, vehicle="vehicle-b"))]
    if expire:
        steps.append(Watermark(600000))
    result = run(*steps, obs(changed), obs(original))
    assert result.windows == () and result.conflict_free is False
    assert result.dispositions[2].kind == "conflict"
    assert result.dispositions[2].reason == "identity_conflict"
    assert result.dispositions[3].kind == ("late" if expire else "duplicate")
    assert result.reconciled_identities == 2


def test_invalid_future_cannot_change_explicit_watermark_or_identity_state() -> None:
    future = event(0, "1970-01-02T00:00:00.000001Z")
    malformed = Observation(b'{"private":"do-not-echo"}')
    result = run(
        Watermark(9998),
        obs(future),
        malformed,
        obs(event()),
        Watermark(9999),
        obs(event(1)),
    )
    assert kinds(result) == [
        (0, "invalid", "scope_mismatch"),
        (1, "invalid", "envelope_invalid"),
        (2, "eligible", "window_open"),
        (3, "late", "window_closed"),
    ]
    assert result.dispositions[1].event_id is None
    assert "do-not-echo" not in repr(result)
    assert result.reconciled_identities == 2
    assert result.windows[0].unique_events == 1


def test_inclusive_scope_bounds_and_run_source_mismatch() -> None:
    low = event(0, "1969-12-31T23:00:00.000000Z")
    high = event(1, "1970-01-02T00:00:00.000000Z")
    wrong_run = event(2)
    cast(dict[str, object], wrong_run["delivery"])["dataset_run_id"] = "another-run"
    result = run(obs(low), obs(high), obs(wrong_run))
    assert [d.kind for d in result.dispositions] == ["eligible", "eligible", "invalid"]
    assert result.dispositions[-1].reason == "scope_mismatch"
    result = calculate_windows(
        scope(source_log_id="sha256:" + "b" * 64), [obs(event()), EndOfInput()]
    )
    assert kinds(result) == [(0, "invalid", "scope_mismatch")]
    assert result.windows == () and result.reconciled_identities == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"dataset_run_id": ""},
        {"pipeline_version": "\u00e9"},
        {"source_log_id": "sha256:" + "A" * 64},
        {"timestamp_min": "1970-01-01T00:00:00Z"},
        {"timestamp_min": "1970-01-03T00:00:00.000000Z"},
    ],
)
def test_invalid_scope_is_fatal(changes: dict[str, str]) -> None:
    with pytest.raises(ReferenceError) as caught:
        calculate_windows(scope(**changes), [EndOfInput()])
    assert isinstance(caught.value.reason, str) and caught.value.reason


def test_bounded_malformed_traces_and_explicit_completion() -> None:
    bad_traces: list[list[TraceStep]] = [
        [],
        [obs(event())],
        [EndOfInput(), EndOfInput()],
        [cast(Observation, object()), EndOfInput()],
        [Observation(cast(bytes, "not bytes")), EndOfInput()],
        [Watermark(True), EndOfInput()],
        [Watermark(cast(int, 1.0)), EndOfInput()],
        [Watermark(1), Watermark(0), EndOfInput()],
        [Watermark(-(2**63) - 1), EndOfInput()],
        [Watermark(2**63 - 1), EndOfInput()],
        cast(list[TraceStep], [Watermark(0)] * 1024) + [EndOfInput()],
        [Observation(b" " * 1048577), EndOfInput()],
    ]
    for trace in bad_traces:
        with pytest.raises(ReferenceError) as caught:
            calculate_windows(scope(), trace)
        assert isinstance(caught.value.reason, str) and caught.value.reason
    assert run(*([Watermark(0)] * 1023)).windows == ()
    assert run(Watermark(-(2**63)), Watermark(2**63 - 2)).windows == ()
    # Byte-bound equality reaches envelope admission rather than failing the trace.
    result = run(Observation(b" " * 1048576))
    assert kinds(result) == [(0, "invalid", "envelope_invalid")]
