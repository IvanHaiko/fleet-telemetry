"""Observable contract checks with authored, nonprivate recording payloads."""

import json
from copy import deepcopy
from types import MappingProxyType
from typing import cast

import pytest
from recording_stream_support import battery, gps, state

from telemetry.recording_stream import (
    EVENT_PROFILE,
    STREAMS,
    Document,
    event_bytes,
    event_order,
    make_event,
    read_event,
    validate_event,
)
from telemetry_reader import read_battery_event
from ulog_integrity import F09_SOURCE_ID


def test_round_trip_preserves_original_payloads_and_tie_order() -> None:
    payloads = [battery(), state(STREAMS[1]), state(STREAMS[2]), gps()]
    events = []
    for rank, (stream, payload) in enumerate(zip(STREAMS, payloads, strict=True)):
        original = deepcopy(payload)
        event = make_event(stream, MappingProxyType(payload), "delivery-2")
        assert event == {
            "profile": EVENT_PROFILE,
            "source_id": F09_SOURCE_ID,
            "run_id": "delivery-2",
            "stream": stream,
            "source_ordinal": 0,
            "native_timestamp_us": 100,
            "measurement_id": payload["event_id"],
            "payload": payload,
        }
        wire = event_bytes(event)
        assert (
            wire
            == json.dumps(
                event, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        )
        assert not wire.endswith(b"\n")
        assert read_event(wire) == validate_event(event) == event
        assert event_order(event) == (100, rank, 0)
        assert payload == original
        cast(Document, event["payload"])["event_id"] = "changed-output-only"
        assert payload == original
        events.append(make_event(stream, payload, "delivery-2"))
    assert sorted(reversed(events), key=event_order) == events
    assert event_order(make_event(STREAMS[0], battery(2, 99), "r")) < (
        event_order(make_event(STREAMS[3], gps(0, 100), "r"))
    )


def test_delivery_runs_do_not_change_identity_or_battery_clock() -> None:
    payload = battery(7, 1000)
    first = make_event(STREAMS[0], payload, "outer-one")
    second = make_event(STREAMS[0], payload, "outer-two")
    assert first["measurement_id"] == second["measurement_id"] == payload["event_id"]
    assert first["payload"] == second["payload"] == payload
    assert read_battery_event(json.dumps(payload).encode()) == payload
    detached = cast(Document, validate_event(first)["payload"])
    cast(Document, detached["delivery"])["dataset_run_id"] = "modified-copy"
    assert cast(Document, payload["delivery"])["dataset_run_id"] == (
        "original-battery-delivery"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile", "future"),
        ("source_id", "other"),
        ("stream", "vehicle_status:1"),
        ("run_id", "unsafe/path"),
        ("run_id", ""),
        ("run_id", "r" * 129),
        ("source_ordinal", True),
        ("native_timestamp_us", 101),
        ("measurement_id", "different"),
        ("unknown", None),
    ],
)
def test_envelope_refuses_mismatched_scope_and_metadata(
    field: str,
    value: object,
) -> None:
    event = make_event(STREAMS[3], gps(), "r")
    event[field] = value
    with pytest.raises(ValueError):
        validate_event(event)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_id", "bad"),
        ("vehicle_id", "other"),
        ("source_ordinal", -1),
        ("native_timestamp_us", 2**64),
        ("native_sample_us", True),
        ("gps_time_relative_us", 2**31),
        ("fix_type", 256),
        ("fix_type", 2),
        ("latitude_deg", None),
        ("longitude_deg", 181),
        ("altitude_msl_m", True),
        ("ground_speed_m_s", -1),
        ("ground_speed_m_s", float("inf")),
        ("gps_utc", "1970-01-01T00:00:00.000000Z"),
        ("gps_utc", "2026-02-30T00:00:00.000000Z"),
        ("unknown", 0),
    ],
)
def test_gps_refuses_invalid_identity_types_bounds_and_nullable_meanings(
    field: str,
    value: object,
) -> None:
    payload = gps()
    payload[field] = value
    with pytest.raises(ValueError):
        make_event(STREAMS[3], payload, "r")


def test_nullable_gps_values_keep_native_time_without_inferred_utc() -> None:
    payload = gps(9, 2**64 - 1)
    payload.update(
        {
            "fix_type": 0,
            "native_sample_us": 0,
            "gps_time_relative_us": -(2**31),
            "latitude_deg": None,
            "longitude_deg": None,
            "altitude_msl_m": None,
            "ground_speed_m_s": None,
        }
    )
    assert make_event(STREAMS[3], payload, "r")["payload"] == payload
    payload["gps_utc"] = "2026-01-01T00:00:00.000001Z"
    assert make_event(STREAMS[3], payload, "r")["payload"] == payload


@pytest.mark.parametrize(
    ("stream", "field", "value"),
    [
        (STREAMS[1], "landed", True),
        (STREAMS[1], "ground_contact", None),
        (STREAMS[1], "maybe_landed", 2),
        (STREAMS[1], "arming_state", 1),
        (STREAMS[2], "arming_state", 0),
        (STREAMS[2], "nav_state", 256),
        (STREAMS[2], "failsafe", 1.0),
        (STREAMS[2], "stream", "vehicle_land_detected"),
        (STREAMS[2], "source_ordinal", 10_000),
        (STREAMS[2], "event_id", "bad"),
    ],
)
def test_state_requires_stream_specific_values_and_identity(
    stream: str,
    field: str,
    value: object,
) -> None:
    payload = state(stream)
    payload[field] = value
    with pytest.raises(ValueError):
        make_event(stream, payload, "r")


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        (None, "normalization_version", "ulog-battery-v1"),
        (None, "vehicle_id", "other"),
        (None, "source_record_index", True),
        (None, "unknown", 0),
        ("source_time", "timestamp_kind", "measurement"),
        ("source_time", "native_timestamp_us", True),
        ("mapping", "anchor_kind", "gps"),
        ("mapping", "unknown", 0),
        ("payload", "voltage_v", True),
        ("payload", "remaining_fraction", 2),
        ("payload", "unknown", 0),
        ("provenance", "unknown", 0),
        ("delivery", "unknown", 0),
    ],
)
def test_battery_reuses_canonical_validation_without_projecting_unknown_keys(
    section: str | None,
    field: str,
    value: object,
) -> None:
    payload = battery()
    target = payload
    if section == "mapping":
        target = cast(Document, cast(Document, payload["source_time"])["mapping"])
    elif section is not None:
        target = cast(Document, payload[section])
    target[field] = value
    with pytest.raises(ValueError):
        make_event(STREAMS[0], payload, "r")


def test_required_nullable_fields_cannot_be_omitted() -> None:
    payloads = [battery(), state(STREAMS[1]), state(STREAMS[2]), gps()]
    fields = ["remaining_fraction", "nav_state", "landed", "gps_utc"]
    for stream, payload, field in zip(STREAMS, payloads, fields, strict=True):
        target = cast(Document, payload["payload"]) if stream == STREAMS[0] else payload
        assert target.pop(field) is None
        with pytest.raises(ValueError):
            make_event(stream, payload, "r")


def test_wire_refuses_duplicates_nonfinite_values_and_excess_bytes() -> None:
    wire = event_bytes(make_event(STREAMS[3], gps(), "r"))
    invalid = [
        b'{"profile":"x",' + wire[1:],
        wire.replace(b'"fix_type":3', b'"fix_type":3,"fix_type":3'),
        wire.replace(b'"altitude_msl_m":10.0', b'"altitude_msl_m":NaN'),
        wire.replace(b'"altitude_msl_m":10.0', b'"altitude_msl_m":1e999'),
        wire + b" " * (65_537 - len(wire)),
        wire.replace(b'"run_id":"r"', b'"run_id":"\xff"'),
        b"[]",
    ]
    for data in invalid:
        with pytest.raises(ValueError):
            read_event(data)
    padded = wire + b" " * (65_536 - len(wire))
    assert read_event(padded) == read_event(wire)
    payload = battery()
    cast(Document, payload["provenance"])["source_manifest_id"] = "x" * 65_536
    with pytest.raises(ValueError, match="size_limit"):
        make_event(STREAMS[0], payload, "r")
