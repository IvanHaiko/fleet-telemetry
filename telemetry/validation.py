"""Native context validation shared by the two source mappers."""

import re
from datetime import datetime

from telemetry.models import (
    MAX_NATIVE_INTEGER,
    NATIVE_FORMAT,
    NORMALIZATION_VERSION,
    ULOG_FIRMWARE,
    ULOG_NATIVE_FORMAT,
    ULOG_NORMALIZATION_VERSION,
    ULOG_PRODUCER_PROFILE,
    ULOG_SEMANTIC_PROJECTION,
    ReasonCode,
    SourceManifest,
    ULogSourceManifest,
)


class InvalidInput(ValueError):
    """Invalid native context, with fixed reason and field names only."""

    def __init__(self, reason: ReasonCode, field: str) -> None:
        super().__init__(reason, field)
        self.reason = reason
        self.field = field


def integer(
    value: object,
    field: str,
    reason: ReasonCode,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInput(reason, field)
    if minimum is not None and value < minimum:
        raise InvalidInput(reason, field)
    if maximum is not None and value > maximum:
        raise InvalidInput(reason, field)
    return value


def identifier(value: object, field: str, reason: ReasonCode) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[\x20-\x7e]+", value) is None:
        raise InvalidInput(reason, field)


def utc(value: object, field: str, reason: ReasonCode) -> datetime:
    if (
        not isinstance(value, str)
        or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
            value,
        )
        is None
    ):
        raise InvalidInput(reason, field)
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise InvalidInput(reason, field) from error


def validate_manifest(manifest: SourceManifest) -> None:
    for field in (
        "source_manifest_id",
        "vehicle_id",
        "source_stream",
        "parser_version",
        "vehicle_mapping_version",
    ):
        identifier(getattr(manifest, field), field, "invalid_manifest")
    for field in ("fixture_specification", "license_evidence", "privacy_review"):
        value: object = getattr(manifest, field)
        if not isinstance(value, str) or not value.strip():
            raise InvalidInput("invalid_manifest", field)
    if (
        not isinstance(manifest.source_log_id, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", manifest.source_log_id) is None
    ):
        raise InvalidInput("invalid_manifest", "source_log_id")
    if (
        manifest.native_format_version != NATIVE_FORMAT
        or manifest.normalization_version != NORMALIZATION_VERSION
        or manifest.source_type != "synthetic"
    ):
        raise InvalidInput("unsupported_schema", "manifest_version")
    if manifest.privacy_classification != "synthetic":
        raise InvalidInput("invalid_manifest", "privacy_classification")
    lower = integer(
        manifest.native_timestamp_min_us,
        "native_timestamp_min_us",
        "invalid_manifest",
        0,
        MAX_NATIVE_INTEGER,
    )
    integer(
        manifest.native_timestamp_max_us,
        "native_timestamp_max_us",
        "invalid_manifest",
        lower,
        MAX_NATIVE_INTEGER,
    )
    utc(manifest.retrieved_at, "retrieved_at", "invalid_manifest")


def validate_ulog_manifest(manifest: ULogSourceManifest) -> None:
    for field in (
        "source_manifest_id",
        "vehicle_id",
        "source_stream",
        "parser_version",
        "vehicle_mapping_version",
    ):
        identifier(getattr(manifest, field), field, "invalid_manifest")
    for field in (
        "source_reference",
        "license_evidence",
        "privacy_review",
        "producer_evidence",
        "field_definition_reference",
    ):
        value: object = getattr(manifest, field)
        if not isinstance(value, str) or not value.strip():
            raise InvalidInput("invalid_manifest", field)
    if (
        not isinstance(manifest.source_log_id, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", manifest.source_log_id) is None
    ):
        raise InvalidInput("invalid_manifest", "source_log_id")
    from telemetry.models import (
        F09_FIRMWARE,
        F09_NATIVE_FORMAT,
        F09_NORMALIZATION_VERSION,
        F09_PRODUCER_PROFILE,
    )
    from ulog_integrity import F09_SOURCE_ID

    f09 = manifest.source_log_id == F09_SOURCE_ID
    versions = {
        "firmware_commit": F09_FIRMWARE if f09 else ULOG_FIRMWARE,
        "producer_profile": F09_PRODUCER_PROFILE if f09 else ULOG_PRODUCER_PROFILE,
        "native_format_version": F09_NATIVE_FORMAT if f09 else ULOG_NATIVE_FORMAT,
        "normalization_version": F09_NORMALIZATION_VERSION
        if f09
        else ULOG_NORMALIZATION_VERSION,
        "semantic_projection_version": ULOG_SEMANTIC_PROJECTION,
        "timestamp_kind": "publication",
    }
    for field, expected in versions.items():
        if getattr(manifest, field) != expected:
            raise InvalidInput("unsupported_schema", field)
    if f09 and (
        manifest.source_type != "ulog" or manifest.source_stream != "battery_status:0"
    ):
        raise InvalidInput("unsupported_schema", "source_stream")
    if manifest.sample_timestamp_field is not None:
        raise InvalidInput("unsupported_schema", "sample_timestamp_field")
    if manifest.source_type not in ("synthetic", "ulog"):
        raise InvalidInput("unsupported_schema", "source_type")
    expected_privacy = (
        "synthetic" if manifest.source_type == "synthetic" else "restricted"
    )
    if manifest.privacy_classification != expected_privacy:
        raise InvalidInput("invalid_manifest", "privacy_classification")
    stream = re.fullmatch(r"battery_status:(0|[1-9][0-9]{0,2})", manifest.source_stream)
    if stream is None or int(stream[1]) > 255:
        raise InvalidInput("unsupported_schema", "source_stream")
    lower = integer(
        manifest.native_timestamp_min_us,
        "native_timestamp_min_us",
        "invalid_manifest",
        0,
        MAX_NATIVE_INTEGER,
    )
    integer(
        manifest.native_timestamp_max_us,
        "native_timestamp_max_us",
        "invalid_manifest",
        lower,
        MAX_NATIVE_INTEGER,
    )
    utc(manifest.retrieved_at, "retrieved_at", "invalid_manifest")
