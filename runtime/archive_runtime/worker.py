"""Single bounded role entry point; all credentials arrive via startup pipes."""

import base64
import binascii
import os
import resource
import socket
import sys
from collections.abc import Mapping
from contextlib import ExitStack
from pathlib import Path
from typing import cast

from runtime.archive_runtime.config import strict_json
from runtime.archive_runtime.processes import CATEGORIES, FIELDS, FRAME, STARTUP, encode
from runtime.s3.archive_store import ArchiveStore, make_archive_store
from runtime.s3.immutable import StoreError
from telemetry.archive_codec import ArchiveError, _fail
from telemetry.archive_documents import (
    BLOB,
    check_body,
    checksum,
    digest,
    document,
    interval,
    lineage,
    mapping,
)
from telemetry.archive_graph import VerifiedArchive, verify_catalog
from telemetry.archive_interfaces import SourceState
from telemetry.archive_rebuild import rebuild_archive, sync_directory, write_file
from telemetry.archive_worker import JOB_FIELDS
from telemetry.local_io import read_bounded


def binary(value: object, maximum: int = BLOB) -> bytes:
    if type(value) is not str or len(value) > (maximum + 2) // 3 * 4:
        _fail("limit_exceeded", "protocol")
    try:
        body = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        _fail("invalid_format", "protocol")
    if len(body) > maximum:
        _fail("limit_exceeded", "protocol")
    return body


def packet(body: bytes, sha: str, op: str) -> dict[str, object]:
    return {
        "op": op,
        "descriptor_b64": base64.b64encode(body).decode("ascii"),
        "sha256": sha,
    }


def send(frame: Mapping[str, object]) -> None:
    sys.stdout.buffer.write(encode(frame))
    sys.stdout.buffer.flush()


def reply(frame: dict[str, object]) -> dict[str, object]:
    send(frame)
    return strict_json(sys.stdin.buffer.readline(FRAME + 1), FRAME)


class Hooks:
    def __init__(self, failpoint: object) -> None:
        self.failpoint = failpoint

    def verify_fresh(self, descriptor: bytes, expected_sha256: str) -> None:
        if reply(packet(descriptor, expected_sha256, "verify")) != {"ok": True}:
            _fail("untrusted_catalog", "hooks")

    def retain(self, descriptor: bytes, expected_sha256: str) -> None:
        if reply(packet(descriptor, expected_sha256, "retain")) != {"ok": True}:
            _fail("untrusted_catalog", "hooks")
        if self.failpoint == "after_retain":
            os._exit(77)

    def read_retained(self) -> bytes:
        return binary(reply({"op": "read_retained"}).get("descriptor_b64"), 65536)


def store(request: dict[str, object], descriptor: dict[str, object]) -> ArchiveStore:
    storage = mapping(
        request["storage"], {"endpoint", "region", "bucket", "access_key", "secret_key"}
    )
    if storage["bucket"] != descriptor["bucket"]:
        _fail("lineage_mismatch", "storage")
    return make_archive_store(
        cast(str, storage["endpoint"]),
        cast(str, storage["region"]),
        cast(str, storage["bucket"]),
        cast(str, descriptor["prefix"]),
        cast(str, storage["access_key"]),
        cast(str, storage["secret_key"]),
    )


class ExportStore:
    """Record only full reads whose key, length and hash were independently checked."""

    def __init__(self, source: ArchiveStore, target: Path | None) -> None:
        self.source, self.target = source, target
        self.seen: dict[str, bytes] = {}

    def read(self, key: str, sha256: str, byte_length: int) -> bytes:
        body = self.source.read(key, sha256, byte_length)
        check_body(body, {"sha256": sha256, "byte_length": byte_length})
        self.source._key(key)
        prior = self.seen.get(key)
        if prior is not None and prior != body:
            _fail("observation_conflict", "storage")
        if prior is None:
            if (
                len(self.seen) >= 64
                or sum(map(len, self.seen.values())) + len(body) > 96 * 1024 * 1024
            ):
                _fail("limit_exceeded", "storage")
            self.seen[key] = body
        return body

    def export(self) -> None:
        if self.target is None:
            return
        # Called only after the entire graph passes; partial exports are retained.
        for key, body in self.seen.items():
            path = self.target / key
            path.parent.mkdir(parents=True, exist_ok=True)
            write_file(path, body)
        for path in sorted(
            (p for p in self.target.rglob("*") if p.is_dir()), reverse=True
        ):
            sync_directory(path)
        sync_directory(self.target)


class StageStore:
    def read(self, key: str, sha256: str, byte_length: int) -> bytes:
        if (
            not key
            or key.startswith("/")
            or any(part in ("", ".", "..") for part in key.split("/"))
        ):
            _fail("invalid_format", "storage")
        path = Path("/stage") / key
        if any(item.is_symlink() for item in (path, *path.parents)):
            _fail("invalid_format", "storage")
        return check_body(
            read_bounded(path, BLOB), {"sha256": sha256, "byte_length": byte_length}
        )


def counts(result: VerifiedArchive, sha: str) -> dict[str, object]:
    return {
        "op": "done",
        "descriptor_sha256": sha,
        "observation_count": len(result.coverage.observations),
        "measurement_count": len(result.measurements),
        "next_offset": result.descriptor["next_offset"],
    }


def publish(request: dict[str, object]) -> dict[str, object]:
    from runtime.kafka_archive.source import open_source
    from telemetry.archive_lineage import registrations
    from telemetry.archive_worker import archive_interval

    job = mapping(request["job"], JOB_FIELDS)
    raw = request["blobs"]
    if not isinstance(raw, dict):
        _fail("invalid_format", "blobs")
    blobs = {key: binary(value) for key, value in cast(dict[str, object], raw).items()}
    jobs = registrations(lineage(job["lineage"]), blobs)
    start, end = interval(job)
    with ExitStack() as clients:
        source = open_source(
            "127.0.0.1:19092",
            cast(str, request["group"]),
            cast(dict[str, object], job["source"]),
            start,
            end,
            jobs,
            non_transactional=True,
            timeout_seconds=cast(float, request["timeout_seconds"]),
        )
        clients.callback(source.close)
        storage = store(
            request,
            {
                "bucket": job["bucket"],
                "prefix": f"archive-v1/{job['archive_run_id']}/",
            },
        )
        clients.callback(storage.close)
        failpoint = request.get("failpoint")

        class Publication:
            def create(self, key: str, body: bytes) -> str:
                result = storage.create(key, body)
                if (failpoint == "after_batch" and key.startswith("batches/")) or (
                    failpoint == "after_receipt" and key.startswith("receipts/")
                ):
                    os._exit(77)
                return result

            def read(self, key: str, sha256: str, byte_length: int) -> bytes:
                return storage.read(key, sha256, byte_length)

            def lookup(self, key: str) -> bytes | None:
                return storage.lookup(key)

            def inventory(self) -> tuple[tuple[str, int], ...]:
                return storage.inventory()

        class Progress:
            def snapshot(self) -> SourceState:
                return source.snapshot()

            def observations(
                self, start: int, next_offset: int
            ) -> tuple[dict[str, object], ...]:
                return source.observations(start, next_offset)

            def commit(self, next_offset: int) -> None:
                source.commit(next_offset)
                if failpoint == "after_commit":
                    os._exit(77)

        descriptor = archive_interval(
            job, blobs, Progress(), Publication(), Hooks(failpoint)
        )
        verified = verify_catalog(descriptor, digest(descriptor), storage)
        return counts(verified, digest(descriptor))


def execute(request: dict[str, object]) -> dict[str, object]:
    role = request.get("role")
    if role == "probe":
        paths = cast(list[str], request["hidden"])
        if any(Path(path).exists() for path in paths):
            _fail("unsupported_profile", "worker")
        if request.get("offline") is True:
            with socket.socket() as connection:
                connection.settimeout(0.2)
                try:
                    connection.connect(("127.0.0.1", 19092))
                except OSError:
                    pass
                else:
                    _fail("unsupported_profile", "worker")
        return {"op": "done", "hidden": True, "offline": request.get("offline") is True}
    if role == "publish":
        return publish(request)
    body = binary(request.get("descriptor_b64"), 65536)
    sha = checksum(request.get("sha256"))
    descriptor = document(body, "descriptor")
    if digest(body) != sha:
        _fail("untrusted_catalog", "catalog")
    if role == "offline":
        result = rebuild_archive(
            body, sha, StageStore(), Path("/output") / cast(str, request["output_name"])
        )
        return counts(result, sha)
    if role != "verify":
        _fail("invalid_format", "protocol")
    storage = store(request, descriptor)
    try:
        export = ExportStore(
            storage, Path("/stage") if request.get("export") is True else None
        )
        result = verify_catalog(body, sha, export)
        export.export()
        return counts(result, sha)
    finally:
        storage.close()


def main() -> int:
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (96 * 1024**2, 96 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        request = strict_json(sys.stdin.buffer.readline(STARTUP + 1), STARTUP)
        send(execute(request))
        return 0
    except (ArchiveError, StoreError) as error:
        category = (
            error.category if error.category in CATEGORIES else "unsupported_profile"
        )
        field = (
            error.field
            if isinstance(error, ArchiveError) and error.field in FIELDS
            else "worker"
        )
        send({"op": "error", "category": category, "field": field})
    except (OSError, ValueError, KeyError, TypeError):
        send({"op": "error", "category": "source_unavailable", "field": "worker"})
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
