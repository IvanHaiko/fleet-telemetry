"""Bounded job/run types, strict JSON shapes and deterministic serialization."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from telemetry.models import (
    BatteryEnvelope,
    DeliveryMetadata,
    SourceManifest,
    ULogBatteryEnvelope,
    ULogSourceManifest,
)
from ulog_integrity import ULogExpectation

JOB_VERSION = "bounded-conversion-v1"
RUN_VERSION = "bounded-run-v1"
PIPELINE_VERSION = "bounded-converter-v2"
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
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


type Event = BatteryEnvelope | ULogBatteryEnvelope


class ConversionError(ValueError):
    """Safe input/run error: messages contain fixed codes, never source values."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ConversionJob:
    mode: Literal["synthetic", "ulog"]
    input_path: Path
    expectation: ULogExpectation
    manifest: SourceManifest | ULogSourceManifest
    delivery: DeliveryMetadata
    config_sha256: str


@dataclass(frozen=True)
class ConversionResult:
    output_directory: Path
    run_manifest: Mapping[str, object]


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ConversionError("duplicate_json_key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ConversionError("nonfinite_json_constant")


def object_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ConversionError("invalid_object")
    return cast(dict[str, object], value)


def json_object(data: bytes) -> dict[str, object]:
    try:
        value: object = json.loads(
            data, object_pairs_hook=_pairs, parse_constant=_constant
        )
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, ConversionError):
            raise
        raise ConversionError("invalid_json") from error
    return object_value(value)


def require_keys(
    value: Mapping[str, object], required: set[str], optional: set[str] | None = None
) -> None:
    if not required <= value.keys() or value.keys() - required - (optional or set()):
        raise ConversionError("invalid_keys")


def string_value(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ConversionError("invalid_string")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ConversionError("invalid_string") from error
    return value


def integer_value(value: object) -> int:
    if type(value) is not int:
        raise ConversionError("invalid_integer")
    return value


def json_line(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")
