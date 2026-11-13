"""Fresh read-only whole-graph verification rooted in independently trusted bytes."""

from dataclasses import dataclass
from typing import cast

from runtime.s3.immutable import StoreError
from telemetry.archive_codec import (
    Coverage,
    _fail,
    decode_observations,
    reconcile_coverage,
)
from telemetry.archive_documents import (
    BODY_BUDGET,
    check_body,
    digest,
    document,
    interval,
    ref,
    store_failure,
)
from telemetry.archive_interfaces import ReadStore
from telemetry.archive_lineage import measurements, registrations


@dataclass(frozen=True)
class VerifiedArchive:
    """Owned validated descriptor, exact observations, lineage and measurements."""

    descriptor: dict[str, object]
    coverage: Coverage
    blobs: dict[str, bytes]
    measurements: tuple[dict[str, object], ...]


class GraphReader:
    """Per-invocation reference consistency and bounded full-read accounting."""

    def __init__(self, store: ReadStore) -> None:
        self.store = store
        self.references: dict[str, dict[str, object]] = {}
        self.total = 0

    def read(self, value: object, role: str) -> bytes:
        """Check a role-specific reference and independently verify returned bytes."""
        reference = ref(value, role)
        key = cast(str, reference["key"])
        prior = self.references.get(key)
        if prior is not None and prior != reference:
            _fail("invalid_format", "reference")
        if prior is None:
            self.total += cast(int, reference["byte_length"])
            if len(self.references) >= 64 or self.total > BODY_BUDGET:
                _fail("limit_exceeded", "objects")
            self.references[key] = reference
        try:
            body = self.store.read(
                key, cast(str, reference["sha256"]), cast(int, reference["byte_length"])
            )
        except StoreError as error:
            store_failure(error, "object")
        except (KeyError, FileNotFoundError):
            _fail("object_missing", "object")
        except PermissionError:
            _fail("permission_denied", "object")
        except TimeoutError:
            _fail("deadline_exceeded", "object")
        except OSError:
            _fail("source_unavailable", "object")
        return check_body(body, reference)


def verify_catalog(
    descriptor: bytes, expected_sha256: str, store: ReadStore
) -> VerifiedArchive:
    """Verify every graph edge and original value without source filesystem I/O."""
    if type(descriptor) is not bytes or digest(descriptor) != expected_sha256:
        _fail("untrusted_catalog", "descriptor")
    root = document(descriptor, "descriptor")
    reader = GraphReader(store)
    catalog = document(reader.read(root["catalog"], "catalog"), "catalog")
    for key in ("archive_run_id", "source", "start_offset", "next_offset"):
        if catalog[key] != root[key]:
            _fail("lineage_mismatch", "catalog")
    entries = cast(list[dict[str, object]], catalog["lineage"])
    blobs: dict[str, bytes] = {}
    for entry in entries:
        obj = cast(dict[str, object], entry["object"])
        blobs[cast(str, obj["key"])] = reader.read(obj, "source")
    jobs = registrations(entries, blobs)
    batches: list[bytes] = []
    line_count = 0
    for entry in cast(list[dict[str, object]], catalog["batches"]):
        manifest = document(reader.read(entry["manifest"], "manifest"), "manifest")
        for key in ("archive_run_id", "source", "lineage"):
            if manifest[key] != catalog[key]:
                _fail("lineage_mismatch", "manifest")
        receipt = document(reader.read(entry["receipt"], "receipt"), "receipt")
        if (
            receipt["manifest"] != entry["manifest"]
            or receipt["archive_run_id"] != catalog["archive_run_id"]
        ):
            _fail("lineage_mismatch", "receipt")
        body = reader.read(manifest["observations"], "batch")
        line_count += body.count(b"\n")
        if line_count > 64:
            _fail("limit_exceeded", "observations")
        rows = decode_observations(body)
        start, end = interval(manifest)
        if len(rows) != manifest["record_count"] or end - start != len(rows):
            _fail("coverage_gap", "manifest")
        reconcile_coverage(
            [body], cast(dict[str, object], manifest["source"]), start, end
        )
        batches.append(body)
    start, end = interval(root)
    coverage = reconcile_coverage(
        batches, cast(dict[str, object], root["source"]), start, end
    )
    return VerifiedArchive(
        root, coverage, blobs, measurements(coverage.observations, jobs)
    )
