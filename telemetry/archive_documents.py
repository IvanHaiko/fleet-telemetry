"""Bounded exact archive control schemas and independent byte integrity."""

import json
import re
from datetime import datetime
from hashlib import sha256
from typing import NoReturn, cast

from runtime.s3.immutable import StoreError
from telemetry.archive_codec import (
    ArchiveError,
    _fail,
    _integer,
    _mapping,
    _nesting,
    _pairs,
    _parse_integer,
    _reject_number,
    _source,
    _string,
)

CONTROL = 65536
BLOB = 16 * 1024 * 1024
BODY_BUDGET = 96 * 1024 * 1024
REF_FIELDS = {"key", "sha256", "byte_length", "version_id"}
LINEAGE_FIELDS = {
    "role",
    "object",
    "source_log_id",
    "schema_version",
    "normalization_version",
    "source_dataset_run_id",
    "privacy_classification",
    "semantic_projection",
}
COMMON = {"format_version", "archive_run_id", "source", "start_offset", "next_offset"}
SCHEMAS = {
    "descriptor": COMMON | {"bucket", "prefix", "catalog"},
    "catalog": COMMON | {"lineage", "batches"},
    "manifest": COMMON | {"record_count", "observations", "lineage"},
    "receipt": {
        "format_version",
        "archive_run_id",
        "writer_version",
        "manifest",
        "verified_at",
        "readback_method",
    },
}
VERSIONS = {
    "descriptor": "archive-recovery-descriptor-v1",
    "catalog": "archive-catalog-v1",
    "manifest": "archive-batch-manifest-v1",
    "receipt": "archive-readback-v1",
}


def store_failure(error: StoreError, field: str) -> NoReturn:
    """Expose only documented categories from the accepted immutable adapter."""
    category = error.category
    if category not in (
        "invalid_format",
        "unsupported_profile",
        "limit_exceeded",
        "object_missing",
        "checksum_mismatch",
        "observation_conflict",
        "coverage_gap",
        "lineage_mismatch",
        "untrusted_catalog",
        "permission_denied",
        "deadline_exceeded",
        "source_unavailable",
        "progress_mismatch",
        "conditional_create_unsupported",
    ):
        category = "unsupported_profile"
    _fail(category, field)


def digest(body: bytes) -> str:
    """Hash exact complete stored bytes."""
    return "sha256:" + sha256(body).hexdigest()


def canonical(value: object) -> bytes:
    """Encode canonical JSON including its final LF."""
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def mapping(value: object, fields: set[str]) -> dict[str, object]:
    """Check exact fields and return a fresh shallow object."""
    return dict(_mapping(value, fields))


def text(value: object) -> str:
    """Bound a metadata string without truncation."""
    return _string(value, 512)


def checksum(value: object) -> str:
    """Validate a SHA-256 identifier."""
    result = text(value)
    if re.fullmatch(r"sha256:[0-9a-f]{64}", result) is None:
        _fail()
    return result


def run_id(value: object) -> str:
    """Validate the owned archive namespace component."""
    result = text(value)
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", result) is None:
        _fail()
    return result


def bucket_name(value: object) -> str:
    """Validate an explicit isolated bucket name, never an endpoint or path."""
    result = text(value)
    if (
        re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", result) is None
        or ".." in result
    ):
        _fail()
    return result


def timestamp(value: object) -> str:
    """Check exact UTC spelling and a real calendar date."""
    result = text(value)
    if (
        re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z", result
        )
        is None
    ):
        _fail()
    try:
        datetime.fromisoformat(result)
    except ValueError:
        _fail()
    return result


def interval(data: dict[str, object]) -> tuple[int, int]:
    """Validate the bounded nonempty half-open interval."""
    start = _integer(data["start_offset"], 0, 2**63 - 1)
    end = _integer(data["next_offset"], 0, 2**63)
    if end <= start:
        _fail()
    if end - start > 32:
        _fail("limit_exceeded", "interval")
    return start, end


def safe_json(body: bytes, maximum: int, control: bool = False) -> dict[str, object]:
    """Bound depth before parsing, reject duplicate keys and invalid strings."""
    if type(body) is not bytes or not body:
        _fail()
    if len(body) > maximum:
        _fail("limit_exceeded", "document")
    _nesting(body)
    try:
        parsed: object = json.loads(
            body,
            object_pairs_hook=_pairs,
            parse_float=_reject_number,
            parse_constant=_reject_number,
            parse_int=_parse_integer,
        )
    except ArchiveError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        _fail()
    if not isinstance(parsed, dict):
        _fail()
    pending: list[object] = [parsed]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            obj = cast(dict[str, object], item)
            pending.extend(obj.keys())
            pending.extend(obj.values())
        elif isinstance(item, list):
            pending.extend(cast(list[object], item))
        elif isinstance(item, str):
            text(item)
    result = cast(dict[str, object], parsed)
    if control and canonical(result) != body:
        _fail()
    return result


def ref(value: object, role: str) -> dict[str, object]:
    """Validate content addressing and role-specific limits before any fetch."""
    result = mapping(value, REF_FIELDS)
    hashed = checksum(result["sha256"])
    folder, suffix, maximum = {
        "source": ("sources", "bin", BLOB),
        "batch": ("batches", "jsonl", 1024 * 1024),
        "manifest": ("manifests", "json", CONTROL),
        "receipt": ("receipts", "json", CONTROL),
        "catalog": ("", "", CONTROL),
    }[role]
    expected = (
        "catalog.json" if role == "catalog" else f"{folder}/{hashed[7:]}.{suffix}"
    )
    if result["key"] != expected or result["version_id"] is not None:
        _fail()
    _integer(result["byte_length"], 0 if role == "source" else 1, maximum)
    return result


def reference(body: bytes, role: str) -> dict[str, object]:
    """Build a validated reference to newly encoded bytes."""
    folder, suffix = {
        "source": ("sources", "bin"),
        "batch": ("batches", "jsonl"),
        "manifest": ("manifests", "json"),
        "receipt": ("receipts", "json"),
    }.get(role, ("", ""))
    hashed = digest(body)
    key = "catalog.json" if role == "catalog" else f"{folder}/{hashed[7:]}.{suffix}"
    return ref(
        {"key": key, "sha256": hashed, "byte_length": len(body), "version_id": None},
        role,
    )


def check_body(body: bytes, reference: dict[str, object]) -> bytes:
    """Do not trust the storage adapter to check its own response."""
    if (
        type(body) is not bytes
        or len(body) != reference["byte_length"]
        or digest(body) != reference["sha256"]
    ):
        _fail("checksum_mismatch", "object")
    return body


def lineage(value: object) -> list[dict[str, object]]:
    """Validate the complete sorted bounded lineage registration list."""
    if not isinstance(value, list) or not value:
        _fail()
    if len(value) > 4:
        _fail("limit_exceeded", "lineage")
    entries: list[dict[str, object]] = []
    order: list[tuple[str, str]] = []
    for item in value:
        entry = mapping(item, LINEAGE_FIELDS)
        role = text(entry["role"])
        if role not in ("original_source", "source_manifest"):
            _fail("unsupported_profile", "lineage")
        entry["object"] = obj = ref(entry["object"], "source")
        for key in LINEAGE_FIELDS - {"object"}:
            text(entry[key])
        checksum(entry["source_log_id"])
        for key, expected in (
            ("schema_version", "1.0.0"),
            ("normalization_version", "battery-v1"),
            ("privacy_classification", "synthetic"),
            ("semantic_projection", "battery-semantic-v1"),
        ):
            if entry[key] != expected:
                _fail("unsupported_profile", "lineage")
        order.append((role, cast(str, obj["key"])))
        entries.append(entry)
    if order != sorted(set(order)):
        _fail()
    return entries


def document(body: bytes, role: str) -> dict[str, object]:
    """Parse and validate an exact canonical control document."""
    result = mapping(safe_json(body, CONTROL, True), SCHEMAS[role])
    if result["format_version"] != VERSIONS[role]:
        _fail("unsupported_profile", "format_version")
    run = run_id(result["archive_run_id"])
    if role != "receipt":
        result["source"] = _source(result["source"])
        interval(result)
    if role == "descriptor":
        bucket_name(result["bucket"])
        if result["prefix"] != f"archive-v1/{run}/":
            _fail()
        result["catalog"] = ref(result["catalog"], "catalog")
    elif role in ("catalog", "manifest"):
        result["lineage"] = lineage(result["lineage"])
        if role == "manifest":
            _integer(result["record_count"], 1, 16)
            result["observations"] = ref(result["observations"], "batch")
        else:
            batches = result["batches"]
            if not isinstance(batches, list) or not batches:
                _fail()
            if len(batches) > 16:
                _fail("limit_exceeded", "batches")
            entries = []
            keys = []
            for item in batches:
                entry = mapping(item, {"manifest", "receipt"})
                entry = {key: ref(entry[key], key) for key in entry}
                keys.append(
                    cast(str, cast(dict[str, object], entry["manifest"])["key"])
                )
                entries.append(entry)
            if keys != sorted(set(keys)):
                _fail()
            result["batches"] = entries
    else:
        result["manifest"] = ref(result["manifest"], "manifest")
        checksum(result["writer_version"])
        timestamp(result["verified_at"])
        if result["readback_method"] != "full_get_sha256":
            _fail("unsupported_profile", "readback_method")
    return result
