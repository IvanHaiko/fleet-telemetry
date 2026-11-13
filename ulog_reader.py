"""Pinned upstream decoding after whole-input framing and provenance checks.

This boundary accepts caller attestations about producer provenance; it cannot
infer the physical producer from a source enum or firmware metadata alone.
"""

from collections.abc import Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO, StringIO
from threading import Lock
from types import MappingProxyType
from typing import Protocol, cast

from fleet_telemetry import ULOG_FIRMWARE, ULogSourceManifest
from ulog_integrity import (
    F09_SOURCE_ID,
    InputIntegrityError,
    ULogExpectation,
    ULogInspection,
    inspect_ulog,
)

PARSER_VERSION = "pyulog-1.2.2"
_PARSER_LOCK = Lock()
_FIELDS = {
    "timestamp": ("uint64_t", "uint64"),
    "voltage_v": ("float", "float32"),
    "current_a": ("float", "float32"),
    "remaining": ("float", "float32"),
    "connected": ("bool", "int8"),
    "source": ("uint8_t", "uint8"),
}


@dataclass(frozen=True)
class DecodedRecord:
    source_record_index: int
    native_record: Mapping[str, object]


@dataclass(frozen=True)
class DecodedULog:
    records: tuple[DecodedRecord, ...]
    inspection: ULogInspection


class _Scalar(Protocol):
    def item(self) -> object: ...


class _Array(Protocol):
    @property
    def dtype(self) -> object: ...

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> _Scalar: ...


class _Dataset(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def multi_id(self) -> int: ...

    @property
    def data(self) -> Mapping[str, _Array]: ...


class _Parsed(Protocol):
    @property
    def file_corruption(self) -> bool: ...

    @property
    def data_list(self) -> Sequence[_Dataset]: ...


class _Constructor(Protocol):
    def __call__(self, data: BytesIO, *, disable_str_exceptions: bool) -> _Parsed: ...


class _DiscardDiagnostics(StringIO):
    """Suppress upstream raw diagnostics without retaining source text."""

    def write(self, value: str) -> int:
        return len(value)


def _load_reader() -> _Constructor:
    try:
        if version("pyulog") != "1.2.2" or version("numpy") != "2.3.5":
            raise InputIntegrityError("unsupported_reader_version", None)
        module = import_module("pyulog")
        constructor: object = getattr(module, "ULog", None)
        if not callable(constructor):
            raise InputIntegrityError("unsupported_reader_namespace", None)
        if getattr(constructor, "__module__", None) != "pyulog.core":
            raise InputIntegrityError("unsupported_reader_namespace", None)
        return cast(_Constructor, constructor)
    except (ImportError, PackageNotFoundError):
        raise InputIntegrityError("reader_dependency_unavailable", None) from None
    except InputIntegrityError:
        raise
    except Exception:
        raise InputIntegrityError("reader_initialization_failure", None) from None


def _validate_profile(inspection: ULogInspection, manifest: ULogSourceManifest) -> None:
    if manifest.source_log_id != inspection.source_log_id:
        raise InputIntegrityError("manifest_source_mismatch", None)
    if manifest.parser_version != PARSER_VERSION:
        raise InputIntegrityError("unsupported_reader_version", None)
    if not manifest.producer_evidence.strip():
        raise InputIntegrityError("missing_producer_attestation", None)
    if manifest.source_type not in ("synthetic", "ulog"):
        raise InputIntegrityError("unsupported_source_type", None)
    from telemetry.models import F09_FIRMWARE

    expected_firmware = (
        F09_FIRMWARE if manifest.source_log_id == F09_SOURCE_ID else ULOG_FIRMWARE
    )
    if manifest.firmware_commit != expected_firmware:
        raise InputIntegrityError("unsupported_firmware", None)
    if (
        manifest.source_type == "ulog"
        and inspection.firmware_commit != manifest.firmware_commit
    ):
        raise InputIntegrityError("firmware_metadata_mismatch", None)
    definition = dict(inspection.definitions).get("battery_status")
    if definition is None:
        raise InputIntegrityError("missing_battery_definition", None)
    digest = "sha256:" + sha256(definition.encode("utf-8")).hexdigest()
    if manifest.field_definition_reference != digest:
        raise InputIntegrityError("field_definition_mismatch", None)
    fields: dict[str, str] = {}
    for field in definition.split(":", 1)[1].split(";"):
        if not field:
            continue
        kind, name = field.split()
        if name in fields:
            raise InputIntegrityError("unsupported_battery_schema", None)
        fields[name] = kind
    if "timestamp_sample" in fields or manifest.sample_timestamp_field is not None:
        raise InputIntegrityError("unsupported_sample_timestamp", None)
    if manifest.timestamp_kind != "publication":
        raise InputIntegrityError("unsupported_timestamp_kind", None)
    for name, (kind, _) in _FIELDS.items():
        if fields.get(name) != kind:
            raise InputIntegrityError("unsupported_battery_schema", None)


def _decode_rows(dataset: _Dataset) -> tuple[DecodedRecord, ...]:
    arrays = dataset.data
    for name, (_, dtype) in _FIELDS.items():
        if name not in arrays or str(arrays[name].dtype) != dtype:
            raise InputIntegrityError("reader_scalar_type_mismatch", None)
    count = len(arrays["timestamp"])
    rows: list[DecodedRecord] = []
    previous = -1
    for index in range(count):
        record: dict[str, object] = {}
        for name in _FIELDS:
            value = arrays[name][index].item()
            expected = float if name in ("voltage_v", "current_a", "remaining") else int
            if type(value) is not expected:
                raise InputIntegrityError("reader_scalar_type_mismatch", None)
            if name == "connected":
                if value not in (0, 1):
                    raise InputIntegrityError("invalid_native_bool", None)
                record[name] = value == 1
            else:
                record[name] = value
        timestamp = cast(int, record["timestamp"])
        if timestamp < previous:
            raise InputIntegrityError("decreasing_timestamp", None)
        previous = timestamp
        rows.append(DecodedRecord(index, MappingProxyType(record)))
    return tuple(rows)


def decode_ulog(
    data: bytes, expectation: ULogExpectation, manifest: ULogSourceManifest
) -> DecodedULog:
    """Decode atomically; no records escape a framing or reader failure.

    Definitions are bound to the manifest by SHA-256 of the full UTF-8 F body.
    Ordinals include rows later rejected by the independent value normalizer.
    """
    inspection = inspect_ulog(data, expectation)
    _validate_profile(inspection, manifest)
    constructor = _load_reader()
    try:
        with _PARSER_LOCK, _DiscardDiagnostics() as diagnostics:
            with redirect_stdout(diagnostics), redirect_stderr(diagnostics):
                parsed = constructor(BytesIO(data), disable_str_exceptions=False)
        if parsed.file_corruption:
            raise InputIntegrityError("reader_reported_corruption", None)
        datasets: dict[tuple[str, int], _Dataset] = {}
        for dataset in parsed.data_list:
            key = (dataset.name, dataset.multi_id)
            if key in datasets:
                raise InputIntegrityError("reader_stream_mismatch", None)
            datasets[key] = dataset
        framed = {
            (stream.name, stream.multi_id): stream for stream in inspection.streams
        }
        if set(datasets) != {
            key for key, stream in framed.items() if stream.record_offsets
        }:
            raise InputIntegrityError("reader_stream_mismatch", None)
        for key, dataset in datasets.items():
            expected_count = len(framed[key].record_offsets)
            if not dataset.data or any(
                len(array) != expected_count for array in dataset.data.values()
            ):
                raise InputIntegrityError("reader_count_mismatch", None)
        selected = next(
            (
                dataset
                for (name, multi_id), dataset in datasets.items()
                if f"{name}:{multi_id}" == manifest.source_stream
            ),
            None,
        )
        if selected is None:
            raise InputIntegrityError("missing_selected_stream", None)
        records = _decode_rows(selected)
    except InputIntegrityError:
        raise
    except Exception:
        # Upstream exceptions can contain native data. Keep the public error safe.
        raise InputIntegrityError("reader_failure", None) from None
    return DecodedULog(records, inspection)
