"""Parent ownership of trust, credentials, protected retention and one deadline."""

import base64
import re
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from runtime.archive_runtime.config import (
    Config,
    Credentials,
    directory,
    duration,
    regular,
    strict_json,
)
from runtime.archive_runtime.processes import run_worker
from runtime.archive_runtime.retention import RetainedRoot
from runtime.archive_runtime.sandbox import (
    ROOT,
    admit_space,
    closure,
    command,
    hidden_mounts,
    prerequisite,
)
from runtime.archive_runtime.worker import binary, packet
from telemetry.archive_codec import _fail, _integer, _source
from telemetry.archive_documents import (
    BLOB,
    CONTROL,
    bucket_name,
    check_body,
    checksum,
    digest,
    document,
    interval,
    lineage,
    mapping,
    run_id,
    timestamp,
)
from telemetry.archive_lineage import registrations
from telemetry.archive_rebuild import fresh_destination
from telemetry.archive_worker import JOB_FIELDS
from telemetry.local_io import read_bounded


def admission(
    job: dict[str, object], blobs: dict[str, bytes], config: Config
) -> dict[str, object]:
    spec = mapping(job, JOB_FIELDS)
    run_id(spec["archive_run_id"])
    if bucket_name(spec["bucket"]) != config.bucket:
        _fail("lineage_mismatch", "storage")
    source = _source(spec["source"])
    if source["partition"] != 0:
        _fail("unsupported_profile", "assignment")
    spec["source"] = source
    start, end = interval(spec)
    if end > 2**63 - 1 or not start < end:
        _fail("invalid_format", "interval")
    _integer(spec["batch_size"], 1, 16)
    checksum(spec["writer_version"])
    if datetime.fromisoformat(timestamp(spec["verified_at"])) > datetime.now(UTC):
        _fail("invalid_format", "verified_at")
    entries = lineage(spec["lineage"])
    owned: dict[str, bytes] = {}
    for entry in entries:
        ref = cast(dict[str, object], entry["object"])
        key = cast(str, ref["key"])
        if key not in blobs:
            _fail("object_missing", "blob")
        owned[key] = check_body(blobs[key], ref)
    if set(owned) != set(blobs):
        _fail("lineage_mismatch", "blobs")
    registrations(entries, owned)
    spec["lineage"] = entries
    return spec


def storage(config: Config, credentials: Credentials) -> dict[str, object]:
    return {
        "endpoint": config.endpoint,
        "region": config.region,
        "bucket": config.bucket,
        "access_key": credentials.access_key,
        "secret_key": credentials.secret_key,
    }


class Supervisor:
    def __init__(
        self, config: Config, scratch_parent: Path, timeout_seconds: float
    ) -> None:
        self.expires = time.monotonic() + duration(timeout_seconds)
        self.config = config
        prerequisite()
        self.code = closure(directory(scratch_parent))
        self.left()

    def left(self) -> float:
        value = self.expires - time.monotonic()
        if value <= 0:
            _fail("deadline_exceeded", "worker")
        return value

    def probe(self, *, offline: bool, hidden: list[str]) -> None:
        result = run_worker(
            command(self.config, self.code, offline=offline),
            {"role": "probe", "offline": offline, "hidden": [str(ROOT), *hidden]},
            expires=self.expires,
        )
        if result != {"op": "done", "hidden": True, "offline": offline}:
            _fail("unsupported_profile", "worker")

    def verify(
        self, body: bytes, sha: str, stage: Path | None = None
    ) -> dict[str, object]:
        self.left()
        request = packet(body, sha, "verify")
        request.pop("op")
        request.update(
            {
                "role": "verify",
                "storage": storage(self.config, self.config.reader),
                "export": stage is not None,
            }
        )
        return run_worker(
            command(self.config, self.code, stage=stage),
            request,
            expires=self.expires,
        )

    def publish(
        self,
        job: dict[str, object],
        blobs: dict[str, bytes],
        group: str,
        root_parent: Path,
        failpoint: str | None,
    ) -> dict[str, object]:
        job = admission(job, blobs, self.config)
        retained = RetainedRoot(root_parent, cast(str, job["archive_run_id"]))
        hidden_mounts(self.config, self.code, retained.parent)
        admit_space(retained.parent, CONTROL * 4)
        if re.fullmatch(r"m4-reader-[a-z0-9-]{1,64}", group) is None:
            _fail("unsupported_profile", "source")
        if self.config.writer is None:
            _fail("invalid_format", "credentials")
        if failpoint not in (
            None,
            "after_batch",
            "after_receipt",
            "after_retain",
            "after_commit",
        ):
            _fail("invalid_format", "config")
        self.probe(offline=False, hidden=[str(retained.parent)])
        verified: tuple[bytes, str] | None = None

        def handler(frame: dict[str, object]) -> dict[str, object]:
            nonlocal verified
            self.left()
            if frame["op"] == "read_retained":
                body = retained.read()
                if verified is None or body != verified[0]:
                    _fail("untrusted_catalog", "retained")
                self.left()
                return {"descriptor_b64": base64.b64encode(body).decode("ascii")}
            body = binary(frame["descriptor_b64"], CONTROL)
            sha = checksum(frame["sha256"])
            descriptor = document(body, "descriptor")
            if digest(body) != sha:
                _fail("untrusted_catalog", "catalog")
            if any(
                descriptor[key] != job[key]
                for key in (
                    "archive_run_id",
                    "bucket",
                    "source",
                    "start_offset",
                    "next_offset",
                )
            ):
                _fail("lineage_mismatch", "catalog")
            if frame["op"] == "verify":
                verified = None
                self.verify(body, sha)
                self.left()
                verified = (body, sha)
            elif frame["op"] == "retain":
                if verified != (body, sha):
                    _fail("untrusted_catalog", "retained")
                retained.retain(body, sha)
                self.left()
            else:
                _fail("invalid_format", "protocol")
            return {"ok": True}

        result = run_worker(
            command(self.config, self.code),
            {
                "role": "publish",
                "job": job,
                "blobs": {
                    key: base64.b64encode(body).decode("ascii")
                    for key, body in blobs.items()
                },
                "group": group,
                "storage": storage(self.config, self.config.writer),
                "timeout_seconds": self.left(),
                "failpoint": failpoint,
            },
            handler,
            expires=self.expires,
        )
        body = retained.read()
        if verified is None or body != verified[0]:
            _fail("untrusted_catalog", "retained")
        self.left()
        return self.result(result, digest(body), job)

    def result(
        self, result: dict[str, object], sha: str, descriptor: dict[str, object]
    ) -> dict[str, object]:
        if set(result) != {
            "op",
            "descriptor_sha256",
            "observation_count",
            "measurement_count",
            "next_offset",
        }:
            _fail("invalid_format", "protocol")
        observations = _integer(result["observation_count"], 1, 32)
        measurements = _integer(result["measurement_count"], 0, observations)
        start, end = interval(descriptor)
        if (
            result["descriptor_sha256"] != sha
            or result["next_offset"] != end
            or observations != end - start
        ):
            _fail("lineage_mismatch", "catalog")
        return {
            "descriptor_sha256": sha,
            "observation_count": observations,
            "measurement_count": measurements,
            "next_offset": end,
        }

    def rebuild(
        self, body: bytes, sha: str, output: Path, *, protected_root: Path
    ) -> dict[str, object]:
        checksum(sha)
        descriptor = document(body, "descriptor")
        if digest(body) != sha or descriptor["bucket"] != self.config.bucket:
            _fail("untrusted_catalog", "catalog")
        target = fresh_destination(output)
        protected_root = directory(protected_root)
        hidden_mounts(self.config, self.code, protected_root)
        if protected_root.is_relative_to(target.parent) or target.parent.is_relative_to(
            protected_root
        ):
            _fail("unsupported_profile", "path")
        if ROOT.is_relative_to(target.parent) or self.code.is_relative_to(
            target.parent
        ):
            _fail("unsupported_profile", "path")
        admit_space(target.parent)
        self.probe(offline=True, hidden=[str(target.parent)])
        stage = Path(tempfile.mkdtemp(prefix="export-", dir=self.code.parent))
        fetched = self.verify(body, sha, stage)
        self.result(fetched, sha, descriptor)
        request = packet(body, sha, "offline")
        request.pop("op")
        request.update({"role": "offline", "output_name": target.name})
        result = run_worker(
            command(
                self.config,
                self.code,
                offline=True,
                stage=stage,
                output_parent=target.parent,
            ),
            request,
            expires=self.expires,
        )
        self.left()
        return self.result(result, sha, descriptor)


def load_job(
    path: Path, supplied: list[str], config: Config
) -> tuple[dict[str, object], dict[str, bytes]]:
    job = strict_json(read_bounded(regular(path), CONTROL), CONTROL)
    blobs: dict[str, bytes] = {}
    if not 1 <= len(supplied) <= 4:
        _fail("limit_exceeded", "blobs")
    for entry in supplied:
        key, separator, name = entry.partition("=")
        if not separator or not name or key in blobs:
            _fail("invalid_format", "blobs")
        blobs[key] = read_bounded(regular(Path(name)), BLOB)
    return admission(job, blobs, config), blobs
