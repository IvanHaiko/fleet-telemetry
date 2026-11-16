"""Receipt-ordered live association, repeats and checkpoint restore (ADR-0054)."""

from typing import cast

import pytest

from telemetry.conversion_contract import json_line, json_object
from telemetry.live_event import event_bytes, make_event, read_event
from telemetry.live_runtime import (
    SESSION_PROFILE,
    Document,
    LiveRuntime,
    make_output,
    read_output,
)

SOURCE: Document = {
    "kind": "px4-sitl",
    "vehicle": "sitl-1",
    "boot_session": "boot-a",
    "system": 1,
    "component": 1,
}
SESSION: Document = {
    "profile": SESSION_PROFILE,
    "run_id": "live-test",
    "source": SOURCE,
    "max_receipt_age_ms": 3000,
}
EPOCH_A, EPOCH_B = "a" * 32, "b" * 32


def position(boot: int, sequence: int, received: int, epoch: str = EPOCH_A) -> Document:
    data: Document = {
        "time_boot_ms": boot,
        "lat": 473977418,
        "lon": 85455939,
        "alt": 488000,
        "relative_alt": 1000,
        "vx": 30,
        "vy": -40,
        "vz": 0,
    }
    return make_event(
        "live-test", SOURCE, "GLOBAL_POSITION_INT", data, epoch, sequence, received
    )


def battery(sequence: int, received: int, epoch: str = EPOCH_A) -> Document:
    data: Document = {
        "voltage_battery": 16200,
        "current_battery": -1,
        "battery_remaining": 80,
    }
    return make_event(
        "live-test", SOURCE, "SYS_STATUS", data, epoch, sequence, received
    )


def state(sequence: int, received: int, epoch: str = EPOCH_A) -> Document:
    data: Document = {
        "autopilot": 12,
        "base_mode": 81,
        "custom_mode": 0,
        "system_status": 3,
    }
    return make_event("live-test", SOURCE, "HEARTBEAT", data, epoch, sequence, received)


def link(fact: Document | None, name: str) -> Document:
    assert fact is not None
    return cast(Document, fact[name])


def test_untimed_streams_associate_by_receipt_order_only() -> None:
    runtime = LiveRuntime(SESSION)
    assert (
        link(runtime.accept(position(1000, 0, 10_000)), "battery")["status"] == "none"
    )
    for untimed in (battery(1, 10_100), state(2, 10_200)):
        assert untimed["measurement_id"] is None
        assert untimed["native_time_boot_ms"] is None
        assert runtime.accept(untimed) is None
    fresh = runtime.accept(position(1200, 3, 10_500))
    assert link(fresh, "battery")["status"] == "receipt_ordered"
    assert link(fresh, "battery")["receipt_age_ms"] == 400
    assert cast(Document, link(fresh, "battery")["values"])["current_a"] is None
    assert cast(Document, link(fresh, "state")["values"])["armed"] is False
    stale = link(runtime.accept(position(5000, 4, 13_101)), "battery")
    assert (stale["status"], stale["values"]) == ("stale", None)
    # A gateway restart starts a new epoch: earlier receipts become unknown
    # until new battery and state packets pass.
    restarted = runtime.accept(position(6000, 0, 14_000, EPOCH_B))
    assert link(restarted, "battery")["status"] == "unknown_after_restart"
    assert link(restarted, "state")["values"] is None
    runtime.accept(battery(1, 14_100, EPOCH_B))
    after = runtime.accept(position(6200, 2, 14_300, EPOCH_B))
    assert link(after, "battery")["status"] == "receipt_ordered"
    assert link(after, "state")["status"] == "unknown_after_restart"
    assert after is not None
    output = make_output(
        after,
        {"cluster_id": "c", "topic_id": "m/w+A", "topic": "t"},
        7,
        runtime.session_sha256,
    )
    assert read_output(json_line(output)[:-1]) == output


def test_repeats_conflicts_and_order() -> None:
    runtime = LiveRuntime(SESSION)
    first = position(1000, 0, 10_000)
    assert runtime.accept(first) is not None
    assert runtime.accept(first) is None  # Kafka redelivery of the same bytes
    # The same measurement under another receipt is a repeat, not a conflict.
    assert runtime.accept(position(1000, 5, 10_900)) is None
    assert runtime.deliveries == 3 and runtime.signature_count == 1
    competing = position(1000, 6, 11_000)
    competing["native"] = {**cast(Document, competing["native"]), "lat": 473977419}
    with pytest.raises(ValueError, match="live_runtime_identity_conflict"):
        runtime.accept(competing)
    with pytest.raises(ValueError, match="live_runtime_position_order"):
        runtime.accept(position(900, 7, 11_100))
    with pytest.raises(ValueError, match="live_runtime_capture_order"):
        runtime.accept(battery(0, 11_200))
    with pytest.raises(ValueError, match="live_event_canonical"):
        read_event(event_bytes(first).replace(b'"run_id"', b' "run_id"'))
    heartbeat: Document = {
        "autopilot": 3,
        "base_mode": 0,
        "custom_mode": 0,
        "system_status": 0,
    }
    with pytest.raises(ValueError, match="live_event_not_px4"):
        make_event("live-test", SOURCE, "HEARTBEAT", heartbeat, EPOCH_A, 9, 1)


def test_restore_from_checkpoint_head_yields_the_same_facts() -> None:
    events = [
        battery(0, 10_000),
        state(1, 10_050),
        position(1000, 2, 10_100),
        position(1200, 3, 10_300),
        battery(0, 11_000, EPOCH_B),
        position(1400, 1, 11_100, EPOCH_B),
        position(1400, 2, 11_150, EPOCH_B),
    ]
    reference = LiveRuntime(SESSION)
    expected = [reference.accept(e) for e in events]
    first = LiveRuntime(SESSION)
    signatures: dict[str, str] = {}
    first.attach_managed_signatures(signatures.get, signatures.__setitem__, None)
    for e in events[:4]:
        first.accept(e)
    # Flink keeps the head as JSON and the signatures in keyed map state.
    head = json_object(json_line(first.checkpoint_head()))
    restored = LiveRuntime(SESSION)
    restored.attach_managed_signatures(signatures.get, signatures.__setitem__, head)
    assert [restored.accept(e) for e in events[4:]] == expected[4:]


def test_capture_reads_sequence_and_ids_from_the_frame_header() -> None:
    # pymavlink reports system 0 and sequence 0 for message IDs outside its
    # dialect; rehearsal live-s4-reh-20261116-04 counted those as lost packets.
    from runtime.continuous.live_gateway import header

    unknown_v2 = bytes.fromhex("fd0100007701019b01001200")  # message ID 411
    assert header(unknown_v2) == (0x77, 1, 1)
    assert header(bytes.fromhex("fe09420101000000")) == (0x42, 1, 1)
    assert header(b"\x00" * 12) is None
