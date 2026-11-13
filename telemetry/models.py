"""Typed battery contracts and pinned normalization profiles; no I/O."""

from dataclasses import dataclass
from typing import Final, Literal, TypedDict

MAX_NATIVE_INTEGER: Final = 9007199254740991
NATIVE_FORMAT: Final = "synthetic-battery-native-v1"
NORMALIZATION_VERSION: Final = "battery-v1"


type ReasonCode = Literal[
    "missing_required_field",
    "invalid_record",
    "invalid_unit_value",
    "invalid_timestamp",
    "missing_time_anchor",
    "invalid_time_anchor",
    "invalid_manifest",
    "invalid_delivery",
    "unsupported_schema",
]


@dataclass(frozen=True)
class ClockAnchor:
    """Reviewed fixed synthetic UTC anchor for one source session."""

    native_anchor_us: int
    utc_anchor: str
    anchor_uncertainty_us: int | None = None


@dataclass(frozen=True)
class SourceManifest:
    """Registered synthetic source; checksum verification belongs to its caller."""

    source_manifest_id: str
    source_log_id: str
    vehicle_id: str
    source_stream: str
    native_timestamp_min_us: int
    native_timestamp_max_us: int
    clock_anchor: ClockAnchor
    fixture_specification: str
    retrieved_at: str
    license_evidence: str
    privacy_review: str
    parser_version: str = "literal-records-v1"
    vehicle_mapping_version: str = "synthetic-vehicles-v1"
    native_format_version: str = NATIVE_FORMAT
    normalization_version: str = NORMALIZATION_VERSION
    source_type: str = "synthetic"
    privacy_classification: str = "synthetic"


@dataclass(frozen=True)
class DeliveryMetadata:
    """Caller-supplied admission time and isolated delivery run."""

    ingest_timestamp: str
    dataset_run_id: str
    replay_mode: str = "synthetic"


@dataclass(frozen=True)
class Rejection:
    """Local result, not a serialized quarantine envelope or raw payload echo."""

    reason_code: ReasonCode
    field: str
    source_manifest_id: str
    source_stream: str
    source_record_index: int | None


class BatteryPayload(TypedDict):
    voltage_v: float
    current_a: float | None
    remaining_fraction: float | None


class TimeMapping(TypedDict):
    native_anchor_us: int
    utc_anchor: str
    anchor_kind: Literal["synthetic_fixed"]
    anchor_uncertainty_us: int | None


class SourceTime(TypedDict):
    clock_basis: Literal["boot_relative"]
    native_timestamp_us: int
    timestamp_kind: Literal["measurement"]
    mapping: TimeMapping


class Provenance(TypedDict):
    source_manifest_id: str
    privacy_classification: Literal["synthetic"]


class Delivery(TypedDict):
    dataset_run_id: str
    replay_mode: Literal["synthetic"]


class BatteryEnvelope(TypedDict):
    event_id: str
    vehicle_id: str
    event_type: Literal["telemetry.battery"]
    schema_version: Literal["1.0.0"]
    source_timestamp: str
    ingest_timestamp: str
    source_log_id: str
    source_type: Literal["synthetic"]
    source_stream: str
    source_record_index: int
    normalization_version: Literal["battery-v1"]
    source_time: SourceTime
    provenance: Provenance
    quality_flags: list[str]
    payload: BatteryPayload
    delivery: Delivery


ULOG_FIRMWARE: Final = "8583f1da30b63154d6ba0bc187d86135dfe33cf9"
ULOG_NATIVE_FORMAT: Final = "px4-battery-status-8583f1da-v1"
ULOG_PRODUCER_PROFILE: Final = "px4-battery-library-power-module-v1"
ULOG_NORMALIZATION_VERSION: Final = "ulog-battery-v1"
ULOG_SEMANTIC_PROJECTION: Final = "ulog-battery-semantic-v1"
F09_FIRMWARE: Final = "9a2a8d4d3cf3bc74956337d8da8d506073684be0"
F09_NATIVE_FORMAT: Final = "px4-battery-status-9a2a8d4d-v1"
F09_NORMALIZATION_VERSION: Final = "ulog-battery-f09-research-v1"
F09_PRODUCER_PROFILE: Final = "px4-f09-producer-unverified-v1"


@dataclass(frozen=True)
class ULogSourceManifest:
    """Caller-reviewed source and producer scope; no file verification is implied."""

    source_manifest_id: str
    source_log_id: str
    vehicle_id: str
    source_stream: str
    native_timestamp_min_us: int
    native_timestamp_max_us: int
    clock_anchor: ClockAnchor
    source_reference: str
    retrieved_at: str
    license_evidence: str
    privacy_review: str
    parser_version: str
    vehicle_mapping_version: str
    producer_evidence: str
    field_definition_reference: str
    firmware_commit: str = ULOG_FIRMWARE
    producer_profile: str = ULOG_PRODUCER_PROFILE
    native_format_version: str = ULOG_NATIVE_FORMAT
    normalization_version: str = ULOG_NORMALIZATION_VERSION
    semantic_projection_version: str = ULOG_SEMANTIC_PROJECTION
    source_type: str = "ulog"
    privacy_classification: str = "restricted"
    timestamp_kind: str = "publication"
    sample_timestamp_field: str | None = None


class ULogSourceTime(TypedDict):
    clock_basis: Literal["boot_relative"]
    native_timestamp_us: int
    timestamp_kind: Literal["publication"]
    mapping: TimeMapping


class ULogProvenance(TypedDict):
    source_manifest_id: str
    privacy_classification: Literal["synthetic", "restricted"]


class ULogDelivery(TypedDict):
    dataset_run_id: str
    replay_mode: Literal["synthetic", "historical"]


class ULogBatteryEnvelope(TypedDict):
    event_id: str
    vehicle_id: str
    event_type: Literal["telemetry.battery"]
    schema_version: Literal["1.0.0"]
    source_timestamp: str
    ingest_timestamp: str
    source_log_id: str
    source_type: Literal["synthetic", "ulog"]
    source_stream: str
    source_record_index: int
    normalization_version: Literal["ulog-battery-v1", "ulog-battery-f09-research-v1"]
    source_time: ULogSourceTime
    provenance: ULogProvenance
    quality_flags: list[str]
    payload: BatteryPayload
    delivery: ULogDelivery
