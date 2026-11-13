"""Authored protocol fixtures, never bytes or measurements from the real F09 log.

GPS/state use the recipes in flight_analytics.gps.prepare/state.project without
importing the optional ULog parser. Battery uses the existing pure normalizer.
"""

from hashlib import sha256

from telemetry.models import (
    F09_FIRMWARE,
    F09_NATIVE_FORMAT,
    F09_NORMALIZATION_VERSION,
    F09_PRODUCER_PROFILE,
    MAX_NATIVE_INTEGER,
    ClockAnchor,
    DeliveryMetadata,
    Rejection,
    ULogSourceManifest,
)
from telemetry.recording_stream import Document
from telemetry.ulog import normalize_ulog_battery
from ulog_integrity import F09_SOURCE_ID


def gps(ordinal: int = 0, stamp: int = 100) -> Document:
    """Build an authored GPS row using the original ordinal identity recipe."""
    identity = sha256(
        f"f09-gps-research-v1:{F09_SOURCE_ID}:vehicle_gps_position:0:{ordinal}".encode()
    ).hexdigest()
    return {
        "event_id": identity,
        "vehicle_id": "f09-research-vehicle",
        "source_ordinal": ordinal,
        "native_timestamp_us": stamp,
        "native_sample_us": stamp,
        "gps_utc": None,
        "gps_time_relative_us": 0,
        "latitude_deg": 0.0,
        "longitude_deg": 0.0,
        "altitude_msl_m": 10.0,
        "ground_speed_m_s": 1.0,
        "fix_type": 3,
    }


def battery(ordinal: int = 0, stamp: int = 100) -> Document:
    """Normalize authored native values in the registered research namespace."""
    anchor = ClockAnchor(0, "2026-01-01T00:00:00.000000Z")
    manifest = ULogSourceManifest(
        source_manifest_id="authored-f09-protocol-fixture",
        source_log_id=F09_SOURCE_ID,
        vehicle_id="f09-research-vehicle",
        source_stream="battery_status:0",
        native_timestamp_min_us=0,
        native_timestamp_max_us=MAX_NATIVE_INTEGER,
        clock_anchor=anchor,
        source_reference="authored fixture; no original recording accessed",
        retrieved_at="2026-01-01T00:00:00.000000Z",
        license_evidence="authored test values",
        privacy_review="authored values; no real coordinates or measurements",
        parser_version="authored-native-record-v1",
        vehicle_mapping_version="authored-f09-protocol-v1",
        producer_evidence="protocol fixture only; physical producer unverified",
        field_definition_reference="authored battery_status fields",
        firmware_commit=F09_FIRMWARE,
        producer_profile=F09_PRODUCER_PROFILE,
        native_format_version=F09_NATIVE_FORMAT,
        normalization_version=F09_NORMALIZATION_VERSION,
    )
    result = normalize_ulog_battery(
        {
            "timestamp": stamp,
            "voltage_v": 12.0,
            "current_a": -1.0,
            "remaining": -1.0,
            "connected": True,
            "source": 0,
        },
        ordinal,
        manifest,
        anchor,
        DeliveryMetadata(
            "2026-01-02T00:00:00.000000Z", "original-battery-delivery", "historical"
        ),
    )
    if isinstance(result, Rejection):
        raise ValueError("invalid_authored_battery")
    return dict(result)


def state(stream: str, ordinal: int = 0, stamp: int = 100) -> Document:
    """Build state.project's shape from a topic name or its instance-zero stream."""
    name = stream.removesuffix(":0")
    if name not in ("vehicle_land_detected", "vehicle_status"):
        raise ValueError("unsupported_authored_state")
    identity = sha256(
        f"f09-state-research-v1:{F09_SOURCE_ID}:{name}:0:{ordinal}".encode()
    ).hexdigest()
    land = name == "vehicle_land_detected"
    return {
        "event_id": identity,
        "stream": name,
        "source_ordinal": ordinal,
        "native_timestamp_us": stamp,
        "landed": 1 if land else None,
        "ground_contact": 1 if land else None,
        "maybe_landed": 0 if land else None,
        "arming_state": None if land else 2,
        "nav_state": None if land else 4,
        "failsafe": None if land else 0,
    }
