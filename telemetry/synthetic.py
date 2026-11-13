"""Pure synthetic battery value mapping under ADR-0005."""

import json
import math
from collections.abc import Mapping
from datetime import timedelta
from hashlib import sha256

from telemetry.models import (
    MAX_NATIVE_INTEGER,
    NORMALIZATION_VERSION,
    BatteryEnvelope,
    BatteryPayload,
    ClockAnchor,
    DeliveryMetadata,
    Rejection,
    SourceManifest,
)
from telemetry.validation import (
    InvalidInput,
    identifier,
    integer,
    utc,
    validate_manifest,
)


def _scaled(value: int, divisor: int, field: str) -> float:
    try:
        result = value / divisor
    except OverflowError as error:
        raise InvalidInput("invalid_unit_value", field) from error
    if not math.isfinite(result):
        raise InvalidInput("invalid_unit_value", field)
    return result


def normalize_battery(
    native_record: Mapping[str, object],
    manifest: SourceManifest,
    clock_anchor: ClockAnchor | None,
    delivery: DeliveryMetadata,
) -> BatteryEnvelope | Rejection:
    """Normalize one record without I/O, clock reads, mutation, or ordinal allocation.

    Native fields are untrusted values. Manifest, anchor and delivery use typed
    structures; their contract values are validated before admission. The caller
    registers exact fixture bytes and supplies the anchor recorded in that manifest.
    """
    raw_index = native_record.get("source_record_index")
    index = (
        raw_index
        if isinstance(raw_index, int)
        and not isinstance(raw_index, bool)
        and 0 <= raw_index <= MAX_NATIVE_INTEGER
        else None
    )
    try:
        validate_manifest(manifest)
        identifier(delivery.dataset_run_id, "dataset_run_id", "invalid_delivery")
        utc(delivery.ingest_timestamp, "ingest_timestamp", "invalid_delivery")
        if delivery.replay_mode != "synthetic":
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
        for field in ("source_record_index", "timestamp_us", "voltage_mv"):
            if field not in native_record:
                raise InvalidInput("missing_required_field", field)
        ordinal = integer(
            raw_index, "source_record_index", "invalid_record", 0, MAX_NATIVE_INTEGER
        )
        timestamp = integer(
            native_record["timestamp_us"],
            "timestamp_us",
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
            raise InvalidInput("invalid_timestamp", "timestamp_us") from error
        voltage = integer(
            native_record["voltage_mv"], "voltage_mv", "invalid_unit_value", 0
        )
        current_value = native_record.get("current_ma")
        current = (
            None
            if current_value is None
            else _scaled(
                integer(current_value, "current_ma", "invalid_unit_value"),
                1000,
                "current_ma",
            )
        )
        remaining_value = native_record.get("remaining_pct")
        remaining = None
        if remaining_value is not None:
            percentage = integer(
                remaining_value, "remaining_pct", "invalid_unit_value", -1, 100
            )
            if percentage != -1:
                remaining = percentage / 100
        payload: BatteryPayload = {
            "voltage_v": _scaled(voltage, 1000, "voltage_mv"),
            "current_a": current,
            "remaining_fraction": remaining,
        }
    except InvalidInput as error:
        return Rejection(
            error.reason,
            error.field,
            manifest.source_manifest_id,
            manifest.source_stream,
            index,
        )

    identity = [
        "event-id-v1",
        "synthetic",
        manifest.source_log_id,
        manifest.vehicle_id,
        manifest.source_stream,
        ordinal,
        "telemetry.battery",
        NORMALIZATION_VERSION,
    ]
    identity_bytes = json.dumps(identity, separators=(",", ":")).encode("utf-8")
    flags = ["synthetic_time_anchor"]
    if current is None or remaining is None:
        flags.append("source_value_missing")
    return {
        "event_id": "sha256:" + sha256(identity_bytes).hexdigest(),
        "vehicle_id": manifest.vehicle_id,
        "event_type": "telemetry.battery",
        "schema_version": "1.0.0",
        "source_timestamp": source_timestamp,
        "ingest_timestamp": delivery.ingest_timestamp,
        "source_log_id": manifest.source_log_id,
        "source_type": "synthetic",
        "source_stream": manifest.source_stream,
        "source_record_index": ordinal,
        "normalization_version": NORMALIZATION_VERSION,
        "source_time": {
            "clock_basis": "boot_relative",
            "native_timestamp_us": timestamp,
            "timestamp_kind": "measurement",
            "mapping": {
                "native_anchor_us": anchor_native,
                "utc_anchor": clock_anchor.utc_anchor,
                "anchor_kind": "synthetic_fixed",
                "anchor_uncertainty_us": clock_anchor.anchor_uncertainty_us,
            },
        },
        "provenance": {
            "source_manifest_id": manifest.source_manifest_id,
            "privacy_classification": "synthetic",
        },
        "quality_flags": sorted(flags),
        "payload": payload,
        "delivery": {
            "dataset_run_id": delivery.dataset_run_id,
            "replay_mode": "synthetic",
        },
    }
