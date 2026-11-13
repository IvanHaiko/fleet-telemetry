"""Read-only original job admission and current-reader measurement linkage."""

import base64
import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import cast

from telemetry.archive_codec import _fail, _integer
from telemetry.archive_documents import (
    BLOB,
    checksum,
    digest,
    mapping,
    safe_json,
    text,
    timestamp,
)
from telemetry.conversion_contract import SEMANTIC_FIELDS, ConversionError
from telemetry.jobs import _manifest
from telemetry.models import SourceManifest
from telemetry.validation import InvalidInput
from telemetry_reader import EnvelopeError, read_battery_event


@dataclass(frozen=True)
class Registration:
    """Validated archived registration; no embedded path is ever resolved."""

    job_hash: str
    manifest: SourceManifest
    delivery: dict[str, object]
    source_length: int


def metadata_path(value: object) -> str:
    """Reject unsafe path syntax without accessing the filesystem."""
    path = text(value)
    posix, windows = PurePosixPath(path), PureWindowsPath(path)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or "\\" in path
        or any(part in ("", ".", "..") for part in path.split("/"))
        or any(ord(char) < 32 for char in path)
        or ":" in path
    ):
        _fail("invalid_format", "path")
    return path


def registration(body: bytes) -> Registration:
    """Validate exact original bounded-conversion-v1 job bytes, purely."""
    spec = mapping(
        safe_json(body, BLOB), {"job_version", "mode", "input", "manifest", "delivery"}
    )
    if spec["job_version"] != "bounded-conversion-v1" or spec["mode"] != "synthetic":
        _fail("unsupported_profile", "job")
    source = mapping(spec["input"], {"path", "source_log_id", "size_bytes"})
    metadata_path(source["path"])
    checksum(source["source_log_id"])
    length = _integer(source["size_bytes"], 1, BLOB)
    try:
        manifest = _manifest(spec["manifest"], "synthetic")
    except (ConversionError, InvalidInput):
        _fail("lineage_mismatch", "registration")
    if not isinstance(manifest, SourceManifest):
        _fail("unsupported_profile", "registration")
    metadata_path(manifest.fixture_specification)
    if manifest.source_log_id != source["source_log_id"]:
        _fail("lineage_mismatch", "source")
    delivery = mapping(
        spec["delivery"], {"dataset_run_id", "ingest_timestamp", "replay_mode"}
    )
    if (
        re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", text(delivery["dataset_run_id"])
        )
        is None
    ):
        _fail("lineage_mismatch", "delivery")
    timestamp(delivery["ingest_timestamp"])
    if delivery["replay_mode"] != "synthetic":
        _fail("unsupported_profile", "delivery")
    return Registration(digest(body), manifest, delivery, length)


def registrations(
    entries: list[dict[str, object]], blobs: dict[str, bytes]
) -> tuple[Registration, ...]:
    """Reconcile every source/job pair, including unused registrations."""
    sources = [entry for entry in entries if entry["role"] == "original_source"]
    jobs = [entry for entry in entries if entry["role"] == "source_manifest"]
    if not 1 <= len(jobs) <= 2 or len(sources) != len(jobs):
        _fail("lineage_mismatch", "pairs")
    used: set[int] = set()
    admitted = []
    metadata = {
        "source_log_id",
        "schema_version",
        "normalization_version",
        "source_dataset_run_id",
        "privacy_classification",
        "semantic_projection",
    }
    for entry in jobs:
        obj = cast(dict[str, object], entry["object"])
        job = registration(blobs[cast(str, obj["key"])])
        manifest = job.manifest
        expected = {
            "source_log_id": manifest.source_log_id,
            "schema_version": "1.0.0",
            "normalization_version": manifest.normalization_version,
            "source_dataset_run_id": job.delivery["dataset_run_id"],
            "privacy_classification": manifest.privacy_classification,
            "semantic_projection": "battery-semantic-v1",
        }
        if any(entry[key] != expected[key] for key in metadata):
            _fail("lineage_mismatch", "registration")
        matches = [
            i
            for i, source in enumerate(sources)
            if all(source[key] == entry[key] for key in metadata)
        ]
        if len(matches) != 1 or matches[0] in used:
            _fail("lineage_mismatch", "pairs")
        used.add(matches[0])
        original = cast(dict[str, object], sources[matches[0]]["object"])
        source_bytes = blobs[cast(str, original["key"])]
        if (
            digest(source_bytes) != manifest.source_log_id
            or len(source_bytes) != job.source_length
        ):
            _fail("lineage_mismatch", "source")
        admitted.append(job)
    return tuple(admitted)


def matches(event: dict[str, object], job: Registration) -> bool:
    """Match all registration, native-clock and original delivery context."""
    manifest = job.manifest
    time = cast(dict[str, object], event["source_time"])
    native = cast(int, time["native_timestamp_us"])
    expected = {
        "source_log_id": manifest.source_log_id,
        "source_type": "synthetic",
        "source_stream": manifest.source_stream,
        "vehicle_id": manifest.vehicle_id,
        "normalization_version": manifest.normalization_version,
        "schema_version": "1.0.0",
        "ingest_timestamp": job.delivery["ingest_timestamp"],
    }
    return (
        all(event[key] == value for key, value in expected.items())
        and event["provenance"]
        == {
            "source_manifest_id": manifest.source_manifest_id,
            "privacy_classification": manifest.privacy_classification,
        }
        and event["delivery"]
        == {
            "dataset_run_id": job.delivery["dataset_run_id"],
            "replay_mode": job.delivery["replay_mode"],
        }
        and time["mapping"]
        == {**asdict(manifest.clock_anchor), "anchor_kind": "synthetic_fixed"}
        and manifest.native_timestamp_min_us
        <= native
        <= manifest.native_timestamp_max_us
    )


def measurements(
    rows: tuple[dict[str, object], ...], jobs: tuple[Registration, ...]
) -> tuple[dict[str, object], ...]:
    """Admit original values and reject hidden links or conflicting semantics."""
    unique: dict[str, dict[str, object]] = {}
    for row in rows:
        value = row["value_b64"]
        event: dict[str, object] | None = None
        if value is not None:
            body = base64.b64decode(cast(str, value), validate=True)
            try:
                event = dict(read_battery_event(body))
            except EnvelopeError:
                pass
        admitted = [] if event is None else [job for job in jobs if matches(event, job)]
        link = row["measurement"]
        if link is None:
            if admitted:
                _fail("lineage_mismatch", "hidden_link")
            continue
        supplied = cast(dict[str, object], link)
        if event is None or not any(
            job.job_hash == supplied["source_manifest_sha256"] for job in admitted
        ):
            _fail("lineage_mismatch", "measurement")
        if supplied["event_id"] != event["event_id"]:
            _fail("lineage_mismatch", "event_id")
        identity = cast(str, event["event_id"])
        prior = unique.get(identity)
        if prior is not None and any(
            prior[key] != event[key] for key in SEMANTIC_FIELDS
        ):
            _fail("observation_conflict", "measurement")
        if prior is None:
            unique[identity] = event
    return tuple(unique.values())
