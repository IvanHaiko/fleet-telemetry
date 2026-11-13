"""Validate local job, source registration and delivery context before conversion."""

import re
from dataclasses import fields
from hashlib import sha256
from pathlib import Path
from typing import Literal

from telemetry.conversion_contract import (
    JOB_VERSION,
    ConversionError,
    ConversionJob,
    integer_value,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.local_io import read_bounded, validate_local_path
from telemetry.models import (
    MAX_NATIVE_INTEGER,
    ClockAnchor,
    DeliveryMetadata,
    SourceManifest,
    ULogSourceManifest,
)
from telemetry.validation import (
    identifier,
    integer,
    utc,
    validate_manifest,
    validate_ulog_manifest,
)
from ulog_integrity import (
    F09_MAX_INPUT_BYTES,
    F09_SOURCE_ID,
    MAX_INPUT_BYTES,
    ULogExpectation,
)


def _anchor(value: object) -> ClockAnchor:
    data = object_value(value)
    require_keys(data, {"native_anchor_us", "utc_anchor"}, {"anchor_uncertainty_us"})
    uncertainty = data.get("anchor_uncertainty_us")
    result = ClockAnchor(
        integer_value(data["native_anchor_us"]),
        string_value(data["utc_anchor"]),
        None if uncertainty is None else integer_value(uncertainty),
    )
    integer(
        result.native_anchor_us,
        "native_anchor_us",
        "invalid_time_anchor",
        0,
        MAX_NATIVE_INTEGER,
    )
    utc(result.utc_anchor, "utc_anchor", "invalid_time_anchor")
    if result.anchor_uncertainty_us is not None:
        integer(
            result.anchor_uncertainty_us,
            "anchor_uncertainty_us",
            "invalid_time_anchor",
            0,
            MAX_NATIVE_INTEGER,
        )
    return result


def _manifest(value: object, mode: str) -> SourceManifest | ULogSourceManifest:
    data = object_value(value)
    model = SourceManifest if mode == "synthetic" else ULogSourceManifest
    allowed = {item.name for item in fields(model)}
    if set(data) - allowed:
        raise ConversionError("invalid_manifest_keys")
    common = {
        name: string_value(data.get(name))
        for name in (
            "source_manifest_id",
            "source_log_id",
            "vehicle_id",
            "source_stream",
            "retrieved_at",
            "license_evidence",
            "privacy_review",
        )
    }
    for name in ("source_manifest_id", "vehicle_id", "source_stream"):
        if len(common[name]) > 256:
            raise ConversionError("identifier_too_long")
    anchor = _anchor(data.get("clock_anchor"))
    lower = integer_value(data.get("native_timestamp_min_us"))
    upper = integer_value(data.get("native_timestamp_max_us"))
    if mode == "synthetic":
        result: SourceManifest | ULogSourceManifest = SourceManifest(
            source_manifest_id=common["source_manifest_id"],
            source_log_id=common["source_log_id"],
            vehicle_id=common["vehicle_id"],
            source_stream=common["source_stream"],
            native_timestamp_min_us=lower,
            native_timestamp_max_us=upper,
            clock_anchor=anchor,
            retrieved_at=common["retrieved_at"],
            license_evidence=common["license_evidence"],
            privacy_review=common["privacy_review"],
            fixture_specification=string_value(data.get("fixture_specification")),
            parser_version=string_value(
                data.get("parser_version", "literal-records-v1")
            ),
            vehicle_mapping_version=string_value(
                data.get("vehicle_mapping_version", "synthetic-vehicles-v1")
            ),
            native_format_version=string_value(
                data.get("native_format_version", "synthetic-battery-native-v1")
            ),
            normalization_version=string_value(
                data.get("normalization_version", "battery-v1")
            ),
            source_type=string_value(data.get("source_type", "synthetic")),
            privacy_classification=string_value(
                data.get("privacy_classification", "synthetic")
            ),
        )
        assert isinstance(result, SourceManifest)
        validate_manifest(result)
        if result.parser_version != "literal-records-v1":
            raise ConversionError("unsupported_fixture_generator")
        return result
    from telemetry.models import (
        ULOG_FIRMWARE,
        ULOG_NATIVE_FORMAT,
        ULOG_NORMALIZATION_VERSION,
        ULOG_PRODUCER_PROFILE,
        ULOG_SEMANTIC_PROJECTION,
    )

    sample_field = data.get("sample_timestamp_field")
    result = ULogSourceManifest(
        source_manifest_id=common["source_manifest_id"],
        source_log_id=common["source_log_id"],
        vehicle_id=common["vehicle_id"],
        source_stream=common["source_stream"],
        native_timestamp_min_us=lower,
        native_timestamp_max_us=upper,
        clock_anchor=anchor,
        retrieved_at=common["retrieved_at"],
        license_evidence=common["license_evidence"],
        privacy_review=common["privacy_review"],
        source_reference=string_value(data.get("source_reference")),
        parser_version=string_value(data.get("parser_version")),
        vehicle_mapping_version=string_value(data.get("vehicle_mapping_version")),
        producer_evidence=string_value(data.get("producer_evidence")),
        field_definition_reference=string_value(data.get("field_definition_reference")),
        firmware_commit=string_value(data.get("firmware_commit", ULOG_FIRMWARE)),
        producer_profile=string_value(
            data.get("producer_profile", ULOG_PRODUCER_PROFILE)
        ),
        native_format_version=string_value(
            data.get("native_format_version", ULOG_NATIVE_FORMAT)
        ),
        normalization_version=string_value(
            data.get("normalization_version", ULOG_NORMALIZATION_VERSION)
        ),
        semantic_projection_version=string_value(
            data.get("semantic_projection_version", ULOG_SEMANTIC_PROJECTION)
        ),
        source_type=string_value(data.get("source_type", "ulog")),
        privacy_classification=string_value(
            data.get("privacy_classification", "restricted")
        ),
        timestamp_kind=string_value(data.get("timestamp_kind", "publication")),
        sample_timestamp_field=None
        if sample_field is None
        else string_value(sample_field),
    )
    validate_ulog_manifest(result)
    return result


def load_job(path: Path) -> ConversionJob:
    """Read a strict bounded job; all evidence remains caller assertions."""
    data = read_bounded(path, 65536)
    spec = json_object(data)
    require_keys(spec, {"job_version", "mode", "input", "manifest", "delivery"})
    if spec["job_version"] != JOB_VERSION or spec["mode"] not in ("synthetic", "ulog"):
        raise ConversionError("unsupported_job")
    source = object_value(spec["input"])
    require_keys(source, {"path", "source_log_id", "size_bytes"})
    size = integer_value(source["size_bytes"])
    checksum = string_value(source["source_log_id"])
    limit = F09_MAX_INPUT_BYTES if checksum == F09_SOURCE_ID else MAX_INPUT_BYTES
    if not 0 < size <= limit:
        raise ConversionError("invalid_input_size")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", checksum) is None:
        raise ConversionError("invalid_input_checksum")
    source_path = path.resolve().parent / string_value(source["path"])
    validate_local_path(source_path)
    input_path = source_path.resolve(strict=True)
    mode: Literal["synthetic", "ulog"] = (
        "synthetic" if spec["mode"] == "synthetic" else "ulog"
    )
    manifest = _manifest(spec["manifest"], mode)
    if manifest.source_log_id != checksum:
        raise ConversionError("manifest_checksum_mismatch")
    metadata = object_value(spec["delivery"])
    require_keys(metadata, {"dataset_run_id", "ingest_timestamp", "replay_mode"})
    delivery = DeliveryMetadata(
        *(
            string_value(metadata[name])
            for name in (
                "ingest_timestamp",
                "dataset_run_id",
                "replay_mode",
            )
        )
    )
    if (
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", delivery.dataset_run_id)
        is None
    ):
        raise ConversionError("invalid_run_id")
    identifier(delivery.dataset_run_id, "dataset_run_id", "invalid_delivery")
    utc(delivery.ingest_timestamp, "ingest_timestamp", "invalid_delivery")
    expected_mode = "synthetic" if manifest.source_type == "synthetic" else "historical"
    if delivery.replay_mode != expected_mode:
        raise ConversionError("invalid_delivery_mode")
    return ConversionJob(
        mode,
        input_path,
        ULogExpectation(checksum, size),
        manifest,
        delivery,
        "sha256:" + sha256(data).hexdigest(),
    )
