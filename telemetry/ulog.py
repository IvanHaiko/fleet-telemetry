"""Pure bounded ULog battery value mapping under ADR-0007."""

import json
import math
from collections.abc import Mapping
from datetime import timedelta
from hashlib import sha256
from typing import Literal

from telemetry.models import (
    MAX_NATIVE_INTEGER,
    ClockAnchor,
    DeliveryMetadata,
    Rejection,
    ULogBatteryEnvelope,
    ULogSourceManifest,
)
from telemetry.validation import (
    InvalidInput,
    identifier,
    integer,
    utc,
    validate_ulog_manifest,
)


def _native_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInput("invalid_unit_value", field)
    try:
        number = float(value)
    except OverflowError as error:
        raise InvalidInput("invalid_unit_value", field) from error
    if not math.isfinite(number):
        raise InvalidInput("invalid_unit_value", field)
    return number


def normalize_ulog_battery(
    native_record: Mapping[str, object],
    source_record_index: int,
    manifest: ULogSourceManifest,
    clock_anchor: ClockAnchor | None,
    delivery: DeliveryMetadata,
) -> ULogBatteryEnvelope | Rejection:
    """Map one validated native-shaped record under the bounded ADR-0007 policy.

    The caller verifies source bytes, embedded types and producer attribution.
    Ordinals belong to that boundary, not native fields. This function performs
    no I/O, clock reads, parser conversion, filtering or ordinal allocation.
    """
    index = (
        source_record_index
        if isinstance(source_record_index, int)
        and not isinstance(source_record_index, bool)
        and 0 <= source_record_index <= MAX_NATIVE_INTEGER
        else None
    )
    try:
        validate_ulog_manifest(manifest)
        identifier(delivery.dataset_run_id, "dataset_run_id", "invalid_delivery")
        utc(delivery.ingest_timestamp, "ingest_timestamp", "invalid_delivery")
        mode = "synthetic" if manifest.source_type == "synthetic" else "historical"
        if delivery.replay_mode != mode:
            raise InvalidInput("invalid_delivery", "replay_mode")
        if clock_anchor is None:
            raise InvalidInput("missing_time_anchor", "clock_anchor")
        anchor_native = integer(
            clock_anchor.native_anchor_us,
            "native_anchor_us",
            "invalid_time_anchor",
            0,
            MAX_NATIVE_INTEGER,
        )
        anchor_utc = utc(clock_anchor.utc_anchor, "utc_anchor", "invalid_time_anchor")
        if clock_anchor.anchor_uncertainty_us is not None:
            integer(
                clock_anchor.anchor_uncertainty_us,
                "anchor_uncertainty_us",
                "invalid_time_anchor",
                0,
                MAX_NATIVE_INTEGER,
            )
        if clock_anchor != manifest.clock_anchor:
            raise InvalidInput("invalid_time_anchor", "clock_anchor")
        ordinal = integer(
            source_record_index,
            "source_record_index",
            "invalid_record",
            0,
            MAX_NATIVE_INTEGER,
        )
        if "timestamp_sample" in native_record:
            raise InvalidInput("unsupported_schema", "timestamp_sample")
        for field in (
            "timestamp",
            "voltage_v",
            "current_a",
            "remaining",
            "connected",
            "source",
        ):
            if field not in native_record:
                raise InvalidInput("missing_required_field", field)
        timestamp = integer(
            native_record["timestamp"],
            "timestamp",
            "invalid_timestamp",
            manifest.native_timestamp_min_us,
            manifest.native_timestamp_max_us,
        )
        try:
            source_timestamp = (
                (anchor_utc + timedelta(microseconds=timestamp - anchor_native))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            )
        except OverflowError as error:
            raise InvalidInput("invalid_timestamp", "timestamp") from error
        voltage = _native_number(native_record["voltage_v"], "voltage_v")
        if voltage <= 0:
            raise InvalidInput("invalid_unit_value", "voltage_v")
        native_current = _native_number(native_record["current_a"], "current_a")
        if native_current < 0 and native_current != -1:
            raise InvalidInput("invalid_unit_value", "current_a")
        current = None if native_current == -1 else native_current + 0.0
        native_remaining = _native_number(native_record["remaining"], "remaining")
        if native_remaining != -1 and not 0 <= native_remaining <= 1:
            raise InvalidInput("invalid_unit_value", "remaining")
        remaining = None if native_remaining == -1 else native_remaining + 0.0
        connected = native_record["connected"]
        if not isinstance(connected, bool):
            raise InvalidInput("invalid_record", "connected")
        integer(native_record["source"], "source", "unsupported_schema", 0, 0)
    except InvalidInput as error:
        return Rejection(
            error.reason,
            error.field,
            manifest.source_manifest_id,
            manifest.source_stream,
            index,
        )

    source_type: Literal["synthetic", "ulog"] = (
        "synthetic" if manifest.source_type == "synthetic" else "ulog"
    )
    privacy: Literal["synthetic", "restricted"] = (
        "synthetic" if source_type == "synthetic" else "restricted"
    )
    replay_mode: Literal["synthetic", "historical"] = (
        "synthetic" if source_type == "synthetic" else "historical"
    )
    identity = [
        "event-id-v1",
        source_type,
        manifest.source_log_id,
        manifest.vehicle_id,
        manifest.source_stream,
        ordinal,
        "telemetry.battery",
        manifest.normalization_version,
    ]
    flags = ["synthetic_time_anchor"]
    if current is None or remaining is None:
        flags.append("source_value_missing")
    if not connected:
        flags.append("source_battery_disconnected")
    return {
        "event_id": "sha256:"
        + sha256(
            json.dumps(identity, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "vehicle_id": manifest.vehicle_id,
        "event_type": "telemetry.battery",
        "schema_version": "1.0.0",
        "source_timestamp": source_timestamp,
        "ingest_timestamp": delivery.ingest_timestamp,
        "source_log_id": manifest.source_log_id,
        "source_type": source_type,
        "source_stream": manifest.source_stream,
        "source_record_index": ordinal,
        "normalization_version": manifest.normalization_version,  # type: ignore[typeddict-item]
        "source_time": {
            "clock_basis": "boot_relative",
            "native_timestamp_us": timestamp,
            "timestamp_kind": "publication",
            "mapping": {
                "native_anchor_us": anchor_native,
                "utc_anchor": clock_anchor.utc_anchor,
                "anchor_kind": "synthetic_fixed",
                "anchor_uncertainty_us": clock_anchor.anchor_uncertainty_us,
            },
        },
        "provenance": {
            "source_manifest_id": manifest.source_manifest_id,
            "privacy_classification": privacy,
        },
        "quality_flags": sorted(flags),
        "payload": {
            "voltage_v": voltage,
            "current_a": current,
            "remaining_fraction": remaining,
        },
        "delivery": {
            "dataset_run_id": delivery.dataset_run_id,
            "replay_mode": replay_mode,
        },
    }
