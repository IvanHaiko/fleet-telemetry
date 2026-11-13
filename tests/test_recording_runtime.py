"""Implementation-authored synthetic invariants for the bounded recording lane."""

import hashlib
from copy import deepcopy
from typing import cast

import pytest
from recording_stream_support import battery, gps, state

from telemetry.conversion_contract import json_line, json_object, object_value
from telemetry.recording_processing import process_events
from telemetry.recording_runtime import (
    MAX_EVENTS,
    MAX_OUTPUT_BYTES,
    MAX_SNAPSHOT_BYTES,
    Document,
    RecordingRuntime,
    make_output,
    read_output,
)
from telemetry.recording_stream import STREAMS, event_order, make_event
from ulog_integrity import F09_SOURCE_ID

RUN = "authored-runtime"
SOURCE: Document = {
    "cluster_id": "authored-cluster",
    "topic_id": "authored-topic-uuid",
    "topic": "authored-recording-input",
    "partition": 0,
}


def policy() -> Document:
    return {
        "profile": "f09-recording-context-v1",
        "source_id": F09_SOURCE_ID,
        "run_id": RUN,
        "start_us": 150,
        "end_us": 1000,
        "battery_source_count": 5,
        "predecessors": [
            make_event(STREAMS[0], battery(0, 100), RUN),
            make_event(STREAMS[1], state(STREAMS[1], 0, 100), RUN),
        ],
        "battery_gaps": [{"start_us": 200, "end_us": 300}],
        "state_gaps": [{"start_us": 150, "end_us": 200}],
    }


def events() -> list[Document]:
    return sorted(
        [
            make_event(STREAMS[-1], gps(i, stamp), RUN)
            for i, stamp in enumerate((150, 151, 200, 250, 300, 351))
        ]
        + [
            make_event(STREAMS[0], battery(ordinal, stamp), RUN)
            for ordinal, stamp in ((1, 200), (3, 300))
        ]
        + [
            make_event(name, state(name, ordinal, stamp), RUN)
            for name, ordinal, stamp in ((STREAMS[1], 1, 200), (STREAMS[2], 0, 200))
        ],
        key=event_order,
    )


def collect(runtime: RecordingRuntime, deliveries: list[Document]) -> list[Document]:
    facts: list[Document] = []
    for event in deliveries:
        fact = runtime.accept(event)
        if fact is not None:
            facts.append(fact)
    return facts


def association(fact: Document, name: str) -> Document:
    inspection = object_value(fact["inspection"])
    if name == "battery":
        return object_value(inspection[name])
    return object_value(object_value(inspection["states"])[name])


def test_incremental_matches_reference_including_gaps_age_and_late_duplicates() -> None:
    selected = events()
    # A late GPS and battery repeat after newer state must neither emit nor renew.
    deliveries = selected + [selected[0], selected[2]]
    context = policy()
    original = deepcopy((deliveries, context))
    runtime = RecordingRuntime(context, max_age_us=50)
    facts = collect(runtime, deliveries)
    runtime.finish()
    assert facts == process_events(deliveries, context, max_age_us=50)
    assert (deliveries, context) == original
    assert [association(fact, "battery")["status"] for fact in facts] == [
        "matched",
        "stale",
        "matched",
        "rejection_gap",
        "matched",
        "stale",
    ]
    assert association(facts[0], "vehicle_land_detected")["status"] == "recording_gap"
    assert association(facts[0], "vehicle_status")["status"] == "before_first"
    for fact in facts:
        for name in ("battery", "vehicle_land_detected", "vehicle_status"):
            match = association(fact, name)
            if match["status"] != "matched":
                assert match["event_id"] is match["age_us"] is match["values"] is None


def test_restore_at_each_boundary_preserves_facts_and_duplicate_memory() -> None:
    selected = events()
    deliveries = selected + [selected[0], selected[2]]
    expected = process_events(deliveries, policy(), max_age_us=50)
    for split in range(len(deliveries) + 1):
        runtime = RecordingRuntime(policy(), max_age_us=50)
        facts = collect(runtime, deliveries[:split])
        snapshot = runtime.snapshot()
        assert len(json_line(snapshot)) <= MAX_SNAPSHOT_BYTES
        restored = RecordingRuntime.restore(
            policy(),
            json_object(json_line(snapshot)),
            max_age_us=50,
        )
        facts.extend(collect(restored, deliveries[split:]))
        restored.finish()
        assert facts == expected
        assert restored.snapshot()["deliveries"] == len(deliveries)


def test_caller_mutation_cannot_change_policy_events_or_saved_state() -> None:
    context = policy()
    original = deepcopy(context)
    runtime = RecordingRuntime(context, max_age_us=50)
    context["battery_gaps"] = []
    object_value(cast(list[object], context["predecessors"])[0])["payload"] = {}
    deliveries = events()
    facts: list[Document] = []
    for event in deliveries:
        fact = runtime.accept(event)
        event["payload"] = {}
        if fact is not None:
            facts.append(fact)
    runtime.finish()
    assert facts == process_events(events(), original, max_age_us=50)
    snapshot = runtime.snapshot()
    object_value(snapshot["current"]).clear()
    assert object_value(runtime.snapshot()["current"])
    saved = runtime.snapshot()
    restored = RecordingRuntime.restore(original, saved, max_age_us=50)
    object_value(saved["current"]).clear()
    assert restored.snapshot() == runtime.snapshot()


def test_refused_conflict_and_order_do_not_partially_advance_state() -> None:
    runtime = RecordingRuntime(policy())
    initial = make_event(STREAMS[-1], gps(1, 200), RUN)
    runtime.accept(initial)
    saved = runtime.snapshot()
    conflict = deepcopy(initial)
    object_value(conflict["payload"])["ground_speed_m_s"] = 2.0
    bad_order = make_event(STREAMS[0], battery(1, 200), RUN)
    bad_stream_order = make_event(STREAMS[-1], gps(0, 250), RUN)
    bad_scope = make_event(STREAMS[-1], gps(2, 1000), RUN)
    for event, reason in (
        (conflict, "identity_conflict"),
        (bad_order, "event_order"),
        (bad_stream_order, "stream_order"),
        (bad_scope, "event_scope"),
    ):
        with pytest.raises(ValueError, match=reason):
            runtime.accept(event)
        assert runtime.snapshot() == saved
    assert runtime.accept(initial) is None
    assert runtime.snapshot()["deliveries"] == 2


def test_hard_delivery_and_signature_caps_include_predecessors_and_duplicates() -> None:
    with pytest.raises(ValueError):
        RecordingRuntime(policy(), max_events=MAX_EVENTS + 1)
    with pytest.raises(ValueError):
        RecordingRuntime(policy(), max_events=True)
    with pytest.raises(ValueError):
        RecordingRuntime(policy(), max_age_us=True)
    # Two predecessors occupy signatures before any selected observation.
    runtime = RecordingRuntime(policy(), max_events=2)
    with pytest.raises(ValueError, match="identity_limit"):
        runtime.accept(events()[0])
    context = policy()
    context["predecessors"] = []
    runtime = RecordingRuntime(context, max_events=2)
    runtime.accept(events()[0])
    assert runtime.accept(events()[0]) is None
    with pytest.raises(ValueError, match="event_limit"):
        runtime.accept(events()[0])
    assert runtime.snapshot()["deliveries"] == 2


def test_finish_requires_gps_and_reconciles_available_battery_evidence() -> None:
    with pytest.raises(ValueError, match="empty_gps"):
        RecordingRuntime(policy()).finish()
    context = policy()
    context["battery_gaps"] = []
    runtime = RecordingRuntime(context)
    assert collect(runtime, events())  # Facts are provisional until finish succeeds.
    with pytest.raises(ValueError, match="battery_gap_coverage"):
        runtime.finish()
    context = policy()
    context["battery_gaps"] = [{"start_us": 200, "end_us": 351}]
    runtime = RecordingRuntime(context)
    collect(runtime, events())
    with pytest.raises(ValueError, match="battery_gap_observation"):
        runtime.finish()
    restored = RecordingRuntime.restore(context, runtime.snapshot())
    with pytest.raises(ValueError, match="battery_gap_observation"):
        restored.finish()


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile", "unsupported"),
        ("context_sha256", "0" * 64),
        ("max_age_us", True),
        ("max_events", 5000),
        ("deliveries", True),
        ("gps_count", 4097),
        ("positions", {STREAMS[-1]: [False, 200]}),
        ("order", [True, 3, 0]),
        ("signatures", {"bad": "0" * 64}),
        ("current", {}),
        ("battery", []),
    ],
)
def test_restore_refuses_malformed_or_different_policy_state(
    field: str,
    value: object,
) -> None:
    runtime = RecordingRuntime(policy())
    collect(runtime, events())
    snapshot = runtime.snapshot()
    snapshot[field] = value
    with pytest.raises(ValueError):
        RecordingRuntime.restore(policy(), snapshot)


def test_snapshot_bound_context_binding_and_empty_restore() -> None:
    runtime = RecordingRuntime(policy())
    assert (
        RecordingRuntime.restore(policy(), runtime.snapshot()).snapshot()
        == runtime.snapshot()
    )
    changed = policy()
    changed["state_gaps"] = []
    with pytest.raises(ValueError, match="snapshot_policy"):
        RecordingRuntime.restore(changed, runtime.snapshot())
    with pytest.raises(ValueError, match="snapshot_policy"):
        RecordingRuntime.restore(policy(), runtime.snapshot(), max_age_us=10)
    snapshot = runtime.snapshot()
    snapshot["extra"] = "x" * MAX_SNAPSHOT_BYTES
    with pytest.raises(ValueError, match="json_limit"):
        RecordingRuntime.restore(policy(), snapshot)


def output() -> Document:
    runtime = RecordingRuntime(policy(), max_age_us=50)
    fact = runtime.accept(events()[0])
    assert fact is not None
    return make_output(fact, SOURCE, 0, hashlib.sha256(json_line(policy())).hexdigest())


def test_output_preserves_fact_and_transport_identity_without_aliases() -> None:
    document = output()
    raw = json_line(document)
    decoded = read_output(raw)
    assert decoded == document
    assert set(decoded) == {
        "profile",
        "input_source",
        "input_offset",
        "context_sha256",
        "fact",
    }
    assert object_value(decoded["input_source"])["partition"] == 0
    source_config = {key: value for key, value in SOURCE.items() if key != "partition"}
    assert (
        make_output(
            object_value(document["fact"]),
            source_config,
            0,
            cast(str, document["context_sha256"]),
        )
        == document
    )
    object_value(decoded["fact"])["inspection"] = {}
    assert read_output(raw) == document


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile", "unsupported"),
        ("input_offset", True),
        ("input_offset", MAX_EVENTS),
        ("context_sha256", "A" * 64),
        ("input_source", {**SOURCE, "partition": True}),
        ("input_source", {**SOURCE, "partition": 1}),
        ("input_source", {**SOURCE, "topic": "invalid/topic"}),
        (
            "input_source",
            {key: value for key, value in SOURCE.items() if key != "partition"},
        ),
    ],
)
def test_output_refuses_unsupported_and_invalid_provenance(
    field: str,
    value: object,
) -> None:
    document = output()
    document[field] = value
    with pytest.raises(ValueError):
        read_output(json_line(document))


def test_output_refuses_loss_of_unknowns_hash_mismatch_and_nonfinite_values() -> None:
    document = output()
    fact = object_value(document["fact"])
    association(fact, "vehicle_status")["age_us"] = 0
    with pytest.raises(ValueError, match="fact_unknown"):
        read_output(json_line(document))
    document = output()
    object_value(document["fact"])["input_event_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="fact_input"):
        read_output(json_line(document))
    raw = json_line(output())
    for bad in (
        b"\xff",
        b"x" * (MAX_OUTPUT_BYTES + 1),
        b'{"profile":"a","profile":"b"}',
        raw.replace(b'"latitude_deg":0.0', b'"latitude_deg":1e309'),
        raw.decode().encode("utf-16-le"),
    ):
        with pytest.raises(ValueError):
            read_output(bad)
