"""Independent contract expectations for the first synthetic normalization slice."""

import copy
import json
from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from fleet_telemetry import (
    BatteryEnvelope,
    ClockAnchor,
    DeliveryMetadata,
    ReasonCode,
    Rejection,
    SourceManifest,
    normalize_battery,
)
from telemetry_reader import read_battery_event

FIXTURES = Path(__file__).parent / "fixtures"
ANCHOR = ClockAnchor(0, "2026-01-01T12:00:00.000000Z")
DELIVERY = DeliveryMetadata("2026-01-02T09:00:00.000000Z", "demo-run-001")
SOURCE_CHECKSUM = (
    "sha256:a023177a0240f8202effe5ec8fa0f301aea8a09e73c25635311d1af370780ffc"
)
MANIFEST = SourceManifest(
    source_manifest_id="synthetic-battery-manifest-v1",
    source_log_id=SOURCE_CHECKSUM,
    vehicle_id="demo-vehicle-001",
    source_stream="battery_status:0",
    native_timestamp_min_us=0,
    native_timestamp_max_us=2000000,
    clock_anchor=ANCHOR,
    fixture_specification="tests/fixtures/synthetic-battery-v1.json",
    retrieved_at="2026-10-19T00:00:00.000000Z",
    license_evidence="Original synthetic values for this project; no third-party data.",
    privacy_review="Synthetic values and pseudonym; no real vehicles or coordinates.",
)
SEMANTIC_FIELDS = (
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
    "quality_flags",
)


def object_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(dict[str, object], value)


def object_list(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def read_fixture(name: str) -> dict[str, object]:
    decoded: object = json.loads((FIXTURES / name).read_bytes())
    return object_dict(decoded)


def records() -> list[dict[str, object]]:
    return [
        object_dict(value)
        for value in object_list(read_fixture("synthetic-battery-v1.json")["records"])
    ]


def admitted(
    record: Mapping[str, object],
    manifest: SourceManifest = MANIFEST,
    anchor: ClockAnchor = ANCHOR,
    delivery: DeliveryMetadata = DELIVERY,
) -> BatteryEnvelope:
    result = normalize_battery(record, manifest, anchor, delivery)
    assert not isinstance(result, Rejection), result
    return result


def semantic_projection(event: BatteryEnvelope) -> dict[str, object]:
    view: Mapping[str, object] = event
    return {key: view[key] for key in SEMANTIC_FIELDS}


def test_published_identity_vector_and_entire_contract_example() -> None:
    contract = (Path(__file__).parents[1] / "docs/data-contracts.md").read_text(
        encoding="utf-8"
    )
    example: object = json.loads(contract.split("```json\n", 1)[1].split("```", 1)[0])
    checksum = "sha256:" + sha256(b"synthetic-battery-fixture-v1").hexdigest()
    assert checksum == (
        "sha256:f71b1ba9fda9c72427902180a4f964eec46949d721a0928c6de84971ff298b80"
    )
    manifest = replace(
        MANIFEST,
        source_log_id=checksum,
        fixture_specification="UTF-8 literal synthetic-battery-fixture-v1; no newline",
    )
    record = dict(records()[0], source_record_index=42)
    event = admitted(record, manifest)
    assert event["event_id"] == (
        "sha256:720eb3715d64d401929ec27b6f11bbdb5cb3a7c53c1d6e619afd492fe8113714"
    )
    assert event == example
    assert read_battery_event(json.dumps(example).encode()) == example


def test_fixture_bytes_and_registration_are_pinned() -> None:
    actual = (
        "sha256:"
        + sha256((FIXTURES / "synthetic-battery-v1.json").read_bytes()).hexdigest()
    )
    expected = read_fixture("expected-battery-v1.json")
    assert actual == MANIFEST.source_log_id == expected["source_log_id"]
    specification = read_fixture("synthetic-battery-v1.json")
    assert specification["seed"] == 0
    assert specification["generator_version"] == MANIFEST.parser_version
    assert specification["native_format_version"] == MANIFEST.native_format_version
    assert [record["source_record_index"] for record in records()] == [0, 1, 2, 3]


def test_two_deliveries_match_independent_golden_content_and_native_ordinals() -> None:
    expected = read_fixture("expected-battery-v1.json")
    for delivery in (
        DELIVERY,
        DeliveryMetadata("2026-10-19T10:00:00.999999Z", "demo-run-002"),
    ):
        outcomes = [
            normalize_battery(record, MANIFEST, ANCHOR, delivery)
            for record in records()
        ]
        events = [event for event in outcomes if not isinstance(event, Rejection)]
        rejected = [event for event in outcomes if isinstance(event, Rejection)]
        assert len(outcomes) == len(events) + len(rejected) == 4
        assert [event["source_record_index"] for event in events] == [0, 2, 3]
        assert [
            {
                "source_record_index": event.source_record_index,
                "reason_code": event.reason_code,
                "field": event.field,
            }
            for event in rejected
        ] == expected["rejected"]
        for event, golden_value in zip(
            events, object_list(expected["accepted"]), strict=True
        ):
            assert read_battery_event(json.dumps(event).encode()) == event
            golden = object_dict(golden_value)
            assert event["event_id"] == golden["event_id"]
            assert event["ingest_timestamp"] == delivery.ingest_timestamp
            assert event["delivery"] == {
                "dataset_run_id": delivery.dataset_run_id,
                "replay_mode": "synthetic",
            }
            assert semantic_projection(event) == {
                "vehicle_id": "demo-vehicle-001",
                "event_type": "telemetry.battery",
                "source_timestamp": golden["source_timestamp"],
                "source_log_id": SOURCE_CHECKSUM,
                "source_type": "synthetic",
                "source_stream": "battery_status:0",
                "source_record_index": golden["source_record_index"],
                "normalization_version": "battery-v1",
                "source_time": {
                    "clock_basis": "boot_relative",
                    "native_timestamp_us": golden["native_timestamp_us"],
                    "timestamp_kind": "measurement",
                    "mapping": {
                        "native_anchor_us": 0,
                        "utc_anchor": "2026-01-01T12:00:00.000000Z",
                        "anchor_kind": "synthetic_fixed",
                        "anchor_uncertainty_us": None,
                    },
                },
                "payload": golden["payload"],
                "quality_flags": golden["quality_flags"],
            }
            assert json.loads(json.dumps(event, allow_nan=False)) == event


@pytest.mark.parametrize(
    ("native", "expected"), [(4200, 4.2), (-1250, -1.25), (-1, -0.001), (0, 0.0)]
)
def test_current_units_sign_and_no_numeric_sentinel(
    native: int, expected: float
) -> None:
    event = admitted(dict(records()[0], current_ma=native))
    assert event["payload"]["current_a"] == expected


@pytest.mark.parametrize("optional", [{}, {"current_ma": None, "remaining_pct": None}])
def test_missing_and_explicit_null_have_the_same_independent_expected_form(
    optional: dict[str, object],
) -> None:
    event = admitted(
        {"source_record_index": 0, "timestamp_us": 1234567, "voltage_mv": 15800}
        | optional
    )
    assert event["payload"] == {
        "voltage_v": 15.8,
        "current_a": None,
        "remaining_fraction": None,
    }
    assert event["quality_flags"] == ["source_value_missing", "synthetic_time_anchor"]


@pytest.mark.parametrize(("native", "expected"), [(-1, None), (0, 0.0), (100, 1.0)])
def test_remaining_sentinel_and_inclusive_endpoints(
    native: int, expected: float | None
) -> None:
    event = admitted(dict(records()[0], remaining_pct=native))
    assert event["payload"]["remaining_fraction"] == expected
    assert ("source_value_missing" in event["quality_flags"]) == (expected is None)


@pytest.mark.parametrize("field", ["voltage_mv", "timestamp_us", "source_record_index"])
def test_missing_required_fields(field: str) -> None:
    record = records()[0]
    del record[field]
    result = normalize_battery(record, MANIFEST, ANCHOR, DELIVERY)
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field) == ("missing_required_field", field)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("voltage_mv", None, "invalid_unit_value"),
        ("voltage_mv", -1, "invalid_unit_value"),
        ("current_ma", "4200", "invalid_unit_value"),
        ("remaining_pct", -2, "invalid_unit_value"),
        ("remaining_pct", 101, "invalid_unit_value"),
        ("timestamp_us", None, "invalid_timestamp"),
        ("timestamp_us", -1, "invalid_timestamp"),
        ("timestamp_us", 2000001, "invalid_timestamp"),
        ("timestamp_us", 9007199254740992, "invalid_timestamp"),
        ("source_record_index", -1, "invalid_record"),
        ("source_record_index", 9007199254740992, "invalid_record"),
        ("voltage_mv", 10**400, "invalid_unit_value"),
        ("current_ma", -(10**400), "invalid_unit_value"),
    ],
)
def test_invalid_values_have_explicit_rejections(
    field: str, value: object, reason: str
) -> None:
    result = normalize_battery(
        dict(records()[0], **{field: value}), MANIFEST, ANCHOR, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field) == (reason, field)


@pytest.mark.parametrize(
    "field",
    [
        "voltage_mv",
        "current_ma",
        "remaining_pct",
        "timestamp_us",
        "source_record_index",
    ],
)
@pytest.mark.parametrize(
    "value", [True, False, 1.0, "1", float("nan"), float("inf"), []]
)
def test_native_integer_fields_reject_coercion_and_nonfinite_values(
    field: str, value: object
) -> None:
    result = normalize_battery(
        dict(records()[0], **{field: value}), MANIFEST, ANCHOR, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert result.field == field


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-01-01T12:00:00Z",
        "2026-01-01T12:00:00.000000+00:00",
        "2026-01-01T12:00:00.00000Z",
        "2026-01-01T12:00:60.000000Z",
        "2026-02-30T12:00:00.000000Z",
        "not-a-time",
    ],
)
def test_invalid_anchor_and_ingestion_timestamps(timestamp: str) -> None:
    anchor = replace(ANCHOR, utc_anchor=timestamp)
    result = normalize_battery(
        records()[0], replace(MANIFEST, clock_anchor=anchor), anchor, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field) == ("invalid_time_anchor", "utc_anchor")
    result = normalize_battery(
        records()[0], MANIFEST, ANCHOR, replace(DELIVERY, ingest_timestamp=timestamp)
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field) == (
        "invalid_delivery",
        "ingest_timestamp",
    )


def test_missing_and_changed_anchors_are_rejected() -> None:
    missing = normalize_battery(records()[0], MANIFEST, None, DELIVERY)
    changed = normalize_battery(
        records()[0], MANIFEST, replace(ANCHOR, native_anchor_us=1), DELIVERY
    )
    assert (
        isinstance(missing, Rejection) and missing.reason_code == "missing_time_anchor"
    )
    assert (
        isinstance(changed, Rejection) and changed.reason_code == "invalid_time_anchor"
    )


@pytest.mark.parametrize(
    ("native_anchor", "utc_anchor", "native_timestamp", "expected"),
    [
        (100, "2026-01-01T00:00:00.000000Z", 99, "2025-12-31T23:59:59.999999Z"),
        (100, "2026-01-01T00:00:00.000000Z", 101, "2026-01-01T00:00:00.000001Z"),
        (0, "0001-01-01T00:00:00.000000Z", 0, "0001-01-01T00:00:00.000000Z"),
    ],
)
def test_clock_delta_is_integer_microseconds_with_calendar_carry(
    native_anchor: int, utc_anchor: str, native_timestamp: int, expected: str
) -> None:
    anchor = ClockAnchor(native_anchor, utc_anchor, 7)
    event = admitted(
        dict(records()[0], timestamp_us=native_timestamp),
        replace(MANIFEST, clock_anchor=anchor),
        anchor,
    )
    assert event["source_timestamp"] == expected
    assert event["source_time"]["mapping"]["anchor_uncertainty_us"] == 7


@pytest.mark.parametrize(
    ("anchor", "native_timestamp"),
    [
        (ClockAnchor(0, "9999-12-31T23:59:59.999999Z"), 1),
        (ClockAnchor(1, "0001-01-01T00:00:00.000000Z"), 0),
    ],
)
def test_utc_overflow_is_a_rejection(
    anchor: ClockAnchor, native_timestamp: int
) -> None:
    result = normalize_battery(
        dict(records()[0], timestamp_us=native_timestamp),
        replace(MANIFEST, clock_anchor=anchor),
        anchor,
        DELIVERY,
    )
    assert isinstance(result, Rejection) and result.reason_code == "invalid_timestamp"


@pytest.mark.parametrize(
    ("manifest", "reason"),
    [
        (replace(MANIFEST, source_log_id="SHA256:bad"), "invalid_manifest"),
        (replace(MANIFEST, source_log_id=cast(str, None)), "invalid_manifest"),
        (replace(MANIFEST, source_log_id=cast(str, 123)), "invalid_manifest"),
        (replace(MANIFEST, vehicle_id=""), "invalid_manifest"),
        (replace(MANIFEST, source_stream="battéry:0"), "invalid_manifest"),
        (replace(MANIFEST, license_evidence=""), "invalid_manifest"),
        (replace(MANIFEST, retrieved_at="yesterday"), "invalid_manifest"),
        (replace(MANIFEST, native_timestamp_min_us=2000001), "invalid_manifest"),
        (replace(MANIFEST, native_timestamp_max_us=-1), "invalid_manifest"),
        (replace(MANIFEST, normalization_version="battery-v2"), "unsupported_schema"),
        (replace(MANIFEST, source_type="ulog"), "unsupported_schema"),
        (replace(MANIFEST, native_format_version="unknown"), "unsupported_schema"),
        (replace(MANIFEST, privacy_classification="private"), "invalid_manifest"),
    ],
)
def test_manifest_gate(manifest: SourceManifest, reason: ReasonCode) -> None:
    result = normalize_battery(records()[0], manifest, ANCHOR, DELIVERY)
    assert isinstance(result, Rejection) and result.reason_code == reason


def test_unknown_optional_native_field_preserves_the_existing_event() -> None:
    event = admitted(dict(records()[0], future_optional_field={"example": 1}))
    assert event == admitted(records()[0])


def test_inputs_are_not_mutated_and_results_do_not_share_mutable_content() -> None:
    record = records()[0]
    before = copy.deepcopy((record, MANIFEST, ANCHOR, DELIVERY))
    event = admitted(record)
    assert (record, MANIFEST, ANCHOR, DELIVERY) == before
    event["quality_flags"].append("mutated-by-caller")
    event["payload"]["current_a"] = 999.0
    fresh = admitted(record)
    assert fresh["quality_flags"] == ["synthetic_time_anchor"]
    assert fresh["payload"]["current_a"] == 4.2
