"""Finite injectable coordination only; no Kafka client or storage runtime."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast

from telemetry.archive_codec import (
    _fail,
    _integer,
    _source,
    encode_observations,
    reconcile_coverage,
)
from telemetry.archive_documents import (
    bucket_name,
    canonical,
    check_body,
    checksum,
    digest,
    document,
    interval,
    lineage,
    mapping,
    reference,
    run_id,
    timestamp,
)
from telemetry.archive_graph import GraphReader, VerifiedArchive, verify_catalog
from telemetry.archive_interfaces import (
    ArchiveHooks,
    ArchiveSource,
    CommitAmbiguous,
    PublishStore,
    SourceState,
)
from telemetry.archive_lineage import registrations
from telemetry.archive_publish import ProposedStore, inventory, lookup, publish

__all__ = ["CommitAmbiguous", "SourceState", "archive_interval"]
JOB_FIELDS = {
    "archive_run_id",
    "bucket",
    "source",
    "start_offset",
    "next_offset",
    "lineage",
    "writer_version",
    "verified_at",
    "batch_size",
}


def source_state(source: ArchiveSource, job: dict[str, object]) -> SourceState:
    """Require fresh identity, supported profile, retention and finite progress."""
    try:
        state = source.snapshot()
    except PermissionError:
        _fail("permission_denied", "source")
    except TimeoutError:
        _fail("deadline_exceeded", "source")
    except OSError:
        _fail("source_unavailable", "source")
    if not isinstance(state, SourceState):
        _fail("invalid_format", "source")
    if _source(state.source) != job["source"]:
        _fail("lineage_mismatch", "source")
    if any(
        value is not True
        for value in (state.assigned, state.delete_only, state.non_transactional)
    ):
        _fail("unsupported_profile", "source")
    low = _integer(state.low, 0, 2**63)
    high = _integer(state.high, 0, 2**63)
    start, end = interval(job)
    if not low <= start < end <= high:
        _fail("source_unavailable", "retention")
    if type(state.committed) is not int or state.committed not in (start, end):
        _fail("progress_mismatch", "committed")
    return state


def root_bytes(job: dict[str, object], catalog: bytes) -> bytes:
    """Create and schema-check the trusted descriptor candidate."""
    body = canonical(
        {
            "format_version": "archive-recovery-descriptor-v1",
            **{
                key: job[key]
                for key in (
                    "archive_run_id",
                    "bucket",
                    "source",
                    "start_offset",
                    "next_offset",
                )
            },
            "prefix": f"archive-v1/{job['archive_run_id']}/",
            "catalog": reference(catalog, "catalog"),
        }
    )
    document(body, "descriptor")
    return body


def compare_archive(
    result: VerifiedArchive,
    job: dict[str, object],
    blobs: Mapping[str, bytes],
    observations: tuple[dict[str, object], ...],
    store: PublishStore,
) -> None:
    """A prior seal is reusable only against this original job and fresh source."""
    for key in ("archive_run_id", "bucket", "source", "start_offset", "next_offset"):
        if result.descriptor[key] != job[key]:
            _fail("lineage_mismatch", "catalog")
    catalog = document(
        GraphReader(store).read(result.descriptor["catalog"], "catalog"), "catalog"
    )
    if catalog["lineage"] != job["lineage"] or result.blobs != blobs:
        _fail("lineage_mismatch", "lineage")
    if result.coverage.observations != observations:
        _fail("observation_conflict", "source")


def archive_interval(
    job: Mapping[str, object],
    blobs: Mapping[str, bytes],
    source: ArchiveSource,
    store: PublishStore,
    hooks: ArchiveHooks,
) -> bytes:
    """Publish an entire finite interval then return only after fresh observed U.

    Hooks and storage/source ports are trusted obligations, not proofs of process
    isolation, external durable retention, disk allocation or command deadlines.
    No deletion, partial commit, reset or automatic commit retry is performed.
    """
    spec = mapping(job, JOB_FIELDS)
    run_id(spec["archive_run_id"])
    bucket_name(spec["bucket"])
    spec["source"] = _source(spec["source"])
    start, end = interval(spec)
    size = _integer(spec["batch_size"], 1, 16)
    checksum(spec["writer_version"])
    lower_bound = datetime.fromisoformat(timestamp(spec["verified_at"]))
    if lower_bound > datetime.now(UTC):
        _fail("invalid_format", "verified_at")
    entries = lineage(spec["lineage"])
    spec["lineage"] = entries
    owned: dict[str, bytes] = {}
    for entry in entries:
        obj = cast(dict[str, object], entry["object"])
        key = cast(str, obj["key"])
        if key not in blobs:
            _fail("object_missing", "blob")
        body = check_body(blobs[key], obj)
        owned[key] = body
    if set(blobs) != set(owned):
        _fail("lineage_mismatch", "blobs")
    registrations(entries, owned)
    initial = source_state(source, spec)
    try:
        supplied = source.observations(start, end)
    except PermissionError:
        _fail("permission_denied", "source")
    except TimeoutError:
        _fail("deadline_exceeded", "source")
    except OSError:
        _fail("source_unavailable", "source")
    if len(supplied) > 32:
        _fail("limit_exceeded", "observations")
    if len(supplied) != end - start:
        _fail("coverage_gap", "source")
    # Encode the supplied observations, never regenerate transport values.
    raw = [
        encode_observations(supplied[i : i + 16]) for i in range(0, len(supplied), 16)
    ]
    coverage = reconcile_coverage(
        raw, cast(dict[str, object], spec["source"]), start, end
    )
    rows = coverage.observations
    inventory(store, {})
    existing = lookup(store, "catalog.json")
    if existing is not None:
        descriptor = root_bytes(spec, existing)
        result = verify_catalog(descriptor, digest(descriptor), store)
        compare_archive(result, spec, owned, rows, store)
    else:
        if initial.committed == end:
            _fail("progress_mismatch", "missing_catalog")
        base = {key: spec[key] for key in ("archive_run_id", "source", "lineage")}
        batches: list[dict[str, object]] = []
        proposed = dict(owned)
        publication: list[tuple[dict[str, object], bytes, str]] = []
        for entry in entries:
            obj = cast(dict[str, object], entry["object"])
            publication.append((obj, owned[cast(str, obj["key"])], "source"))

        def add(body: bytes, role: str) -> dict[str, object]:
            obj = reference(body, role)
            proposed[cast(str, obj["key"])] = body
            publication.append((obj, body, role))
            return obj

        for index in range(0, len(rows), size):
            group = rows[index : index + size]
            body = encode_observations(group)
            batch = add(body, "batch")
            manifest = add(
                canonical(
                    {
                        "format_version": "archive-batch-manifest-v1",
                        **base,
                        "start_offset": group[0]["offset"],
                        "next_offset": cast(int, group[-1]["offset"]) + 1,
                        "record_count": len(group),
                        "observations": batch,
                    }
                ),
                "manifest",
            )
            receipt = add(
                canonical(
                    {
                        "format_version": "archive-readback-v1",
                        "archive_run_id": spec["archive_run_id"],
                        "writer_version": spec["writer_version"],
                        "manifest": manifest,
                        "verified_at": spec["verified_at"],
                        "readback_method": "full_get_sha256",
                    }
                ),
                "receipt",
            )
            batches.append({"manifest": manifest, "receipt": receipt})
        batches.sort(
            key=lambda entry: cast(
                str, cast(dict[str, object], entry["manifest"])["key"]
            )
        )

        def catalog_bytes() -> bytes:
            return canonical(
                {
                    "format_version": "archive-catalog-v1",
                    **base,
                    "start_offset": start,
                    "next_offset": end,
                    "batches": batches,
                }
            )

        catalog = catalog_bytes()
        descriptor = root_bytes(spec, catalog)
        proposed["catalog.json"] = catalog
        # Full graph validation occurs before any publication, including invalid links.
        verify_catalog(descriptor, digest(descriptor), ProposedStore(proposed, store))
        inventory(store, proposed)
        source_state(source, spec)
        for obj, body, role in publication:
            if role == "receipt":
                # Planned bytes validate structure only; never emit them as evidence.
                receipt_data = document(body, "receipt")
                reader = GraphReader(store)
                manifest_data = document(
                    reader.read(receipt_data["manifest"], "manifest"), "manifest"
                )
                reader.read(manifest_data["observations"], "batch")
                completed = datetime.now(UTC)
                if completed < lower_bound:
                    _fail("invalid_format", "verified_at")
                receipt_data["verified_at"] = completed.strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                body = canonical(receipt_data)
                actual = reference(body, "receipt")
                del proposed[cast(str, obj["key"])]
                proposed[cast(str, actual["key"])] = body
                for entry in batches:
                    if entry["receipt"] == obj:
                        entry["receipt"] = actual
                obj = actual
                catalog = catalog_bytes()
                descriptor = root_bytes(spec, catalog)
                proposed["catalog.json"] = catalog
            # Include every orphan and remaining graph object on each admission.
            inventory(store, proposed)
            publish(store, obj, body, role)
        # Recheck actual stored graph before publishing the immutable seal.
        verify_catalog(
            descriptor,
            digest(descriptor),
            ProposedStore({"catalog.json": catalog}, store),
        )
        inventory(store, {"catalog.json": catalog})
        publish(store, reference(catalog, "catalog"), catalog, "catalog")
    verify_catalog(descriptor, digest(descriptor), store)
    trusted_hash = digest(descriptor)
    try:
        hooks.verify_fresh(descriptor, trusted_hash)
        hooks.retain(descriptor, trusted_hash)
        retained = hooks.read_retained()
    except PermissionError:
        _fail("permission_denied", "hooks")
    except TimeoutError:
        _fail("deadline_exceeded", "hooks")
    except OSError:
        _fail("source_unavailable", "hooks")
    if (
        type(retained) is not bytes
        or retained != descriptor
        or digest(retained) != trusted_hash
    ):
        _fail("untrusted_catalog", "retained")
    before = source_state(source, spec)
    if before.committed == end:
        return descriptor
    try:
        source.commit(end)
    except CommitAmbiguous:
        pass
    except PermissionError:
        _fail("permission_denied", "commit")
    except TimeoutError:
        _fail("deadline_exceeded", "commit")
    except OSError:
        _fail("source_unavailable", "commit")
    after = source_state(source, spec)
    if after.committed != end:
        _fail("progress_mismatch", "commit")
    return descriptor
