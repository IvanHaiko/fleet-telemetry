"""Independent value-policy fixtures and boundaries for the pure ULog slice."""

import copy
import json
import math
from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from fleet_telemetry import (
    ClockAnchor,
    DeliveryMetadata,
    Rejection,
    ULogBatteryEnvelope,
    ULogSourceManifest,
    normalize_ulog_battery,
)
from telemetry.models import (
    F09_FIRMWARE,
    F09_NATIVE_FORMAT,
    F09_NORMALIZATION_VERSION,
    F09_PRODUCER_PROFILE,
)
from telemetry_reader import EnvelopeError, read_battery_event
from ulog_integrity import F09_SOURCE_ID

FIXTURES = Path(__file__).parent / "fixtures"
CHECKSUM = "sha256:ec8b91945ad7e6e12cb592a7a999de21f1abc4a4469638da76f69aaebbfc065f"
ANCHOR = ClockAnchor(0, "2026-01-01T00:00:00.000000Z")
DELIVERY = DeliveryMetadata("2026-10-19T00:00:00.000000Z", "ulog-policy-run-001")
MANIFEST = ULogSourceManifest(
    source_manifest_id="ulog-policy-fixture-manifest-v1",
    source_log_id=CHECKSUM,
    vehicle_id="demo-ulog-policy-001",
    source_stream="battery_status:0",
    native_timestamp_min_us=0,
    native_timestamp_max_us=2000000,
    clock_anchor=ANCHOR,
    source_reference="tests/fixtures/ulog-battery-policy-v1.json",
    retrieved_at="2026-10-19T00:00:00.000000Z",
    license_evidence="Project-authored synthetic cases; no flight-log derivative.",
    privacy_review="Synthetic values; no device identifiers or coordinates.",
    parser_version="literal-records-v1",
    vehicle_mapping_version="synthetic-vehicles-v1",
    producer_evidence=(
        "Authored cases for the reviewed library policy; "
        "no real producer attribution claimed."
    ),
    field_definition_reference=(
        "PX4 commit 8583f1da30b63154d6ba0bc187d86135dfe33cf9 msg/battery_status.msg"
    ),
    source_type="synthetic",
    privacy_classification="synthetic",
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


def fixture_cases() -> list[dict[str, object]]:
    return [
        object_dict(item)
        for item in object_list(read_fixture("ulog-battery-policy-v1.json")["cases"])
    ]


def baseline() -> dict[str, object]:
    return object_dict(fixture_cases()[0]["record"])


def admitted(
    record: Mapping[str, object],
    ordinal: int = 0,
    manifest: ULogSourceManifest = MANIFEST,
    anchor: ClockAnchor = ANCHOR,
    delivery: DeliveryMetadata = DELIVERY,
) -> ULogBatteryEnvelope:
    result = normalize_ulog_battery(record, ordinal, manifest, anchor, delivery)
    assert not isinstance(result, Rejection), result
    return result


def test_f09_profile_has_separate_lineage_and_refuses_other_sources() -> None:
    manifest = replace(
        MANIFEST,
        source_log_id=F09_SOURCE_ID,
        firmware_commit=F09_FIRMWARE,
        native_format_version=F09_NATIVE_FORMAT,
        normalization_version=F09_NORMALIZATION_VERSION,
        producer_profile=F09_PRODUCER_PROFILE,
        source_type="ulog",
        privacy_classification="restricted",
    )
    delivery = DeliveryMetadata("2026-10-19T00:00:00.000000Z", "research", "historical")
    result = normalize_ulog_battery(baseline(), 4, manifest, ANCHOR, delivery)
    assert not isinstance(result, Rejection)
    assert result["normalization_version"] == F09_NORMALIZATION_VERSION
    assert read_battery_event(json.dumps(result).encode()) == result
    result["source_log_id"] = CHECKSUM
    with pytest.raises(EnvelopeError, match="profile_mismatch"):
        read_battery_event(json.dumps(result).encode())
    rejected = normalize_ulog_battery(
        baseline(), 4, replace(manifest, source_log_id=CHECKSUM), ANCHOR, delivery
    )
    assert isinstance(rejected, Rejection)
    assert rejected.reason_code == "unsupported_schema"


@pytest.mark.parametrize("case", fixture_cases(), ids=lambda item: str(item["case_id"]))
def test_all_authored_outcomes_match_the_independent_expectations(
    case: dict[str, object],
) -> None:
    expected = read_fixture("expected-ulog-battery-policy-v1.json")
    expected_outcomes = {
        item["case_id"]: item
        for value in object_list(expected["accepted"])
        + object_list(expected["rejected"])
        for item in [object_dict(value)]
    }
    golden = expected_outcomes[case["case_id"]]
    ordinal = case["source_record_index"]
    assert isinstance(ordinal, int)
    result = normalize_ulog_battery(
        object_dict(case["record"]),
        ordinal,
        MANIFEST,
        ANCHOR,
        DELIVERY,
    )
    if "reason_code" in golden:
        assert isinstance(result, Rejection)
        assert (result.reason_code, result.field, result.source_record_index) == (
            golden["reason_code"],
            golden["field"],
            golden["source_record_index"],
        )
        assert result.source_manifest_id == MANIFEST.source_manifest_id
        assert result.source_stream == "battery_status:0"
        return
    assert not isinstance(result, Rejection), result
    identities = read_fixture("expected-ulog-battery-identities-v1.json")
    assert read_battery_event(json.dumps(result).encode()) == result
    identity = next(
        object_dict(value)["event_id"]
        for value in object_list(identities["accepted"])
        if object_dict(value)["case_id"] == case["case_id"]
    )
    assert result == {
        "event_id": identity,
        "vehicle_id": "demo-ulog-policy-001",
        "event_type": "telemetry.battery",
        "schema_version": "1.0.0",
        "source_timestamp": golden["source_timestamp"],
        "ingest_timestamp": DELIVERY.ingest_timestamp,
        "source_log_id": CHECKSUM,
        "source_type": "synthetic",
        "source_stream": "battery_status:0",
        "source_record_index": golden["source_record_index"],
        "normalization_version": "ulog-battery-v1",
        "source_time": {
            "clock_basis": "boot_relative",
            "native_timestamp_us": 1000000,
            "timestamp_kind": golden["timestamp_kind"],
            "mapping": {
                "native_anchor_us": 0,
                "utc_anchor": "2026-01-01T00:00:00.000000Z",
                "anchor_kind": "synthetic_fixed",
                "anchor_uncertainty_us": None,
            },
        },
        "provenance": {
            "source_manifest_id": "ulog-policy-fixture-manifest-v1",
            "privacy_classification": "synthetic",
        },
        "quality_flags": golden["quality_flags"],
        "payload": golden["payload"],
        "delivery": {
            "dataset_run_id": DELIVERY.dataset_run_id,
            "replay_mode": "synthetic",
        },
    }
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_registration_and_two_delivery_runs_reconcile_identity_and_content() -> None:
    assert (
        "sha256:"
        + sha256((FIXTURES / "ulog-battery-policy-v1.json").read_bytes()).hexdigest()
        == CHECKSUM
    )
    identities = read_fixture("expected-ulog-battery-identities-v1.json")
    assert identities["source_log_id"] == CHECKSUM
    runs: list[list[ULogBatteryEnvelope]] = []
    for delivery in (
        DELIVERY,
        DeliveryMetadata("2026-10-20T23:59:59.999999Z", "ulog-policy-run-002"),
    ):
        outcomes = [
            normalize_ulog_battery(
                object_dict(case["record"]),
                cast(int, case["source_record_index"]),
                MANIFEST,
                ANCHOR,
                delivery,
            )
            for case in fixture_cases()
        ]
        events = [item for item in outcomes if not isinstance(item, Rejection)]
        assert (len(outcomes), len(events)) == (22, 9)
        assert [item["source_record_index"] for item in events] == [
            0,
            1,
            2,
            5,
            6,
            11,
            12,
            13,
            21,
        ]
        assert [item["event_id"] for item in events] == [
            object_dict(value)["event_id"]
            for value in object_list(identities["accepted"])
        ]
        assert len({item["event_id"] for item in events}) == 9
        assert all(
            item["ingest_timestamp"] == delivery.ingest_timestamp for item in events
        )
        runs.append(events)
    for first, second in zip(*runs, strict=True):
        assert first["delivery"] != second["delivery"]
        assert {
            k: v for k, v in first.items() if k not in ("delivery", "ingest_timestamp")
        } == {
            k: v for k, v in second.items() if k not in ("delivery", "ingest_timestamp")
        }


@pytest.mark.parametrize("field", ["voltage_v", "current_a", "remaining"])
@pytest.mark.parametrize(
    "value",
    [None, True, False, "1", float("nan"), float("inf"), -float("inf"), 10**400],
)
def test_numeric_fields_reject_unknown_types_and_nonfinite_values(
    field: str,
    value: object,
) -> None:
    result = normalize_ulog_battery(
        dict(baseline(), **{field: value}), 3, MANIFEST, ANCHOR, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field, result.source_record_index) == (
        "invalid_unit_value",
        field,
        3,
    )


@pytest.mark.parametrize("value", [-1, 2000001, 1.0, True, "1", float("nan")])
def test_timestamp_never_falls_back_to_admission_time(value: object) -> None:
    result = normalize_ulog_battery(
        dict(baseline(), timestamp=value), 4, MANIFEST, ANCHOR, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field) == ("invalid_timestamp", "timestamp")


@pytest.mark.parametrize("value", [-1, 9007199254740992, True, 1.0, "1", None])
def test_external_invalid_ordinals_are_not_allocated_or_echoed(value: object) -> None:
    result = normalize_ulog_battery(
        baseline(), cast(int, value), MANIFEST, ANCHOR, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field, result.source_record_index) == (
        "invalid_record",
        "source_record_index",
        None,
    )


@pytest.mark.parametrize("value", [1, -1, True, 0.0, "0"])
def test_native_source_must_be_the_supported_integer_enum(value: object) -> None:
    result = normalize_ulog_battery(
        dict(baseline(), source=value), 0, MANIFEST, ANCHOR, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field) == ("unsupported_schema", "source")


@pytest.mark.parametrize(
    ("manifest", "reason"),
    [
        (replace(MANIFEST, firmware_commit="other"), "unsupported_schema"),
        (replace(MANIFEST, producer_profile="other"), "unsupported_schema"),
        (replace(MANIFEST, producer_evidence=""), "invalid_manifest"),
        (replace(MANIFEST, field_definition_reference=""), "invalid_manifest"),
        (replace(MANIFEST, source_reference=""), "invalid_manifest"),
        (replace(MANIFEST, parser_version=""), "invalid_manifest"),
        (replace(MANIFEST, vehicle_mapping_version=""), "invalid_manifest"),
        (replace(MANIFEST, source_log_id="sha256:bad"), "invalid_manifest"),
        (replace(MANIFEST, license_evidence=""), "invalid_manifest"),
        (replace(MANIFEST, privacy_review=""), "invalid_manifest"),
        (replace(MANIFEST, retrieved_at="yesterday"), "invalid_manifest"),
        (replace(MANIFEST, native_timestamp_min_us=-1), "invalid_manifest"),
        (replace(MANIFEST, native_timestamp_max_us=-1), "invalid_manifest"),
        (replace(MANIFEST, normalization_version="battery-v1"), "unsupported_schema"),
        (replace(MANIFEST, native_format_version="other"), "unsupported_schema"),
        (
            replace(MANIFEST, semantic_projection_version="battery-semantic-v1"),
            "unsupported_schema",
        ),
        (replace(MANIFEST, timestamp_kind="measurement"), "unsupported_schema"),
        (
            replace(MANIFEST, sample_timestamp_field="timestamp_sample"),
            "unsupported_schema",
        ),
        (replace(MANIFEST, source_type="mavlink"), "unsupported_schema"),
        (replace(MANIFEST, privacy_classification="restricted"), "invalid_manifest"),
        (replace(MANIFEST, source_stream="battery_status:256"), "unsupported_schema"),
        (replace(MANIFEST, source_stream="battery_status:01"), "unsupported_schema"),
        (replace(MANIFEST, source_stream="other:0"), "unsupported_schema"),
    ],
)
def test_manifest_scope_gate(manifest: ULogSourceManifest, reason: str) -> None:
    result = normalize_ulog_battery(baseline(), 0, manifest, ANCHOR, DELIVERY)
    assert isinstance(result, Rejection)
    assert result.reason_code == reason


def test_missing_changed_and_invalid_anchors_cannot_read_a_host_clock() -> None:
    for anchor, reason in (
        (None, "missing_time_anchor"),
        (replace(ANCHOR, native_anchor_us=1), "invalid_time_anchor"),
        (
            replace(ANCHOR, utc_anchor="2026-01-01T00:00:60.000000Z"),
            "invalid_time_anchor",
        ),
        (replace(ANCHOR, anchor_uncertainty_us=-1), "invalid_time_anchor"),
    ):
        result = normalize_ulog_battery(baseline(), 0, MANIFEST, anchor, DELIVERY)
        assert isinstance(result, Rejection)
        assert result.reason_code == reason


@pytest.mark.parametrize(
    ("anchor", "timestamp", "expected"),
    [
        (
            ClockAnchor(1000001, "2026-01-01T00:00:00.000000Z", 7),
            1000000,
            "2025-12-31T23:59:59.999999Z",
        ),
        (ANCHOR, 0, "2026-01-01T00:00:00.000000Z"),
        (ANCHOR, 2000000, "2026-01-01T00:00:02.000000Z"),
    ],
)
def test_integer_microsecond_mapping_and_inclusive_session_bounds(
    anchor: ClockAnchor,
    timestamp: int,
    expected: str,
) -> None:
    event = admitted(
        dict(baseline(), timestamp=timestamp),
        manifest=replace(MANIFEST, clock_anchor=anchor),
        anchor=anchor,
    )
    assert event["source_timestamp"] == expected
    assert (
        event["source_time"]["mapping"]["anchor_uncertainty_us"]
        == anchor.anchor_uncertainty_us
    )


def test_utc_overflow_is_rejected() -> None:
    anchor = ClockAnchor(0, "9999-12-31T23:59:59.999999Z")
    result = normalize_ulog_battery(
        baseline(), 0, replace(MANIFEST, clock_anchor=anchor), anchor, DELIVERY
    )
    assert isinstance(result, Rejection) and result.reason_code == "invalid_timestamp"


@pytest.mark.parametrize("sample_time", [999999, None])
def test_sample_time_cannot_be_ignored_by_the_publication_only_profile(
    sample_time: object,
) -> None:
    result = normalize_ulog_battery(
        dict(baseline(), timestamp_sample=sample_time), 0, MANIFEST, ANCHOR, DELIVERY
    )
    assert isinstance(result, Rejection)
    assert (result.reason_code, result.field) == (
        "unsupported_schema",
        "timestamp_sample",
    )


def test_ulog_origin_delivery_and_privacy_are_separate_from_fixture_origin() -> None:
    # This tests caller metadata, not real parsing, rights or producer attribution.
    manifest = replace(
        MANIFEST,
        source_type="ulog",
        privacy_classification="restricted",
        source_log_id="sha256:68d1020f688109f027dba08d2950247cc0ae34aaefdcf37e4a7d60838f3e1aa3",
    )
    delivery = replace(DELIVERY, replay_mode="historical")
    event = admitted(baseline(), manifest=manifest, delivery=delivery)
    assert read_battery_event(json.dumps(event).encode()) == event
    canonical_charging = json.loads(json.dumps(event))
    canonical_charging["payload"]["current_a"] = -2.5
    assert (
        read_battery_event(json.dumps(canonical_charging).encode())["payload"][
            "current_a"
        ]
        == -2.5
    )
    assert event["source_type"] == "ulog"
    assert event["provenance"]["privacy_classification"] == "restricted"
    assert event["delivery"]["replay_mode"] == "historical"
    assert event["event_id"] != admitted(baseline())["event_id"]
    result = normalize_ulog_battery(baseline(), 0, manifest, ANCHOR, DELIVERY)
    assert isinstance(result, Rejection) and result.reason_code == "invalid_delivery"


@pytest.mark.parametrize(
    "delivery",
    [
        replace(DELIVERY, dataset_run_id=""),
        replace(DELIVERY, ingest_timestamp="2026-01-01T00:00:00Z"),
        replace(DELIVERY, replay_mode="historical"),
    ],
)
def test_invalid_delivery_is_rejected_before_record_admission(
    delivery: DeliveryMetadata,
) -> None:
    result = normalize_ulog_battery(baseline(), 0, MANIFEST, ANCHOR, delivery)
    assert isinstance(result, Rejection) and result.reason_code == "invalid_delivery"


def test_stream_instance_and_external_ordinal_control_identity() -> None:
    event = admitted(baseline())
    second_instance = admitted(
        baseline(), manifest=replace(MANIFEST, source_stream="battery_status:1")
    )
    assert second_instance["source_stream"] == "battery_status:1"
    assert second_instance["event_id"] != event["event_id"]
    assert admitted(baseline(), ordinal=1)["event_id"] != event["event_id"]
    assert admitted(dict(baseline(), source_record_index=999)) == event
    assert (
        admitted(dict(baseline(), optional_diagnostic={"note": "synthetic"})) == event
    )


def test_zero_is_preserved_and_inputs_and_results_do_not_share_mutable_content() -> (
    None
):
    record = baseline()
    before = copy.deepcopy((record, MANIFEST, ANCHOR, DELIVERY))
    event = admitted(record)
    assert (record, MANIFEST, ANCHOR, DELIVERY) == before
    event["payload"]["voltage_v"] = 999.0
    event["quality_flags"].append("mutated")
    assert admitted(record)["payload"]["voltage_v"] == 12.5
    assert admitted(record)["quality_flags"] == ["synthetic_time_anchor"]
    for value in (0.0, -0.0):
        current = admitted(dict(record, current_a=value))["payload"]["current_a"]
        assert current == 0.0
        assert math.copysign(1.0, current) == 1.0
