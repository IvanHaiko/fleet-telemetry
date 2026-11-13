"""Parent-owned exclusive, durable recovery descriptor retention."""

import os
import tempfile
from pathlib import Path

from runtime.archive_runtime.config import directory, regular
from telemetry.archive_codec import _fail
from telemetry.archive_documents import CONTROL, checksum, digest, document, run_id
from telemetry.archive_rebuild import sync_directory, write_file
from telemetry.conversion_contract import ConversionError
from telemetry.local_io import publish_run, read_bounded


class RetainedRoot:
    def __init__(self, parent: Path, archive_run_id: str) -> None:
        self.parent = directory(parent)
        self.run = run_id(archive_run_id)
        self.target = self.parent / self.run

    def _validate(self, body: bytes, sha: str) -> None:
        checksum(sha)
        if digest(body) != sha:
            _fail("untrusted_catalog", "retained")
        descriptor = document(body, "descriptor")
        if descriptor["archive_run_id"] != self.run:
            _fail("lineage_mismatch", "retained")

    def retain(self, descriptor: bytes, expected_sha256: str) -> None:
        self._validate(descriptor, expected_sha256)
        try:
            directory(self.parent)
            if os.path.lexists(self.target):
                if self.read() != descriptor:
                    _fail("untrusted_catalog", "retained")
                return
            stage = Path(tempfile.mkdtemp(prefix=".archive-root-", dir=self.parent))
            write_file(stage / "descriptor.json", descriptor)
            write_file(
                stage / "descriptor.sha256", (expected_sha256 + "\n").encode("ascii")
            )
            sync_directory(stage)
            sync_directory(self.parent)
            publish_run(stage, self.target)
            sync_directory(self.parent)
        except PermissionError:
            _fail("permission_denied", "retained")
        except (OSError, ConversionError):
            _fail("source_unavailable", "retained")

    def read(self) -> bytes:
        try:
            directory(self.target)
            if {item.name for item in self.target.iterdir()} != {
                "descriptor.json",
                "descriptor.sha256",
            }:
                _fail("untrusted_catalog", "retained")
            body = read_bounded(regular(self.target / "descriptor.json"), CONTROL)
            raw_hash = read_bounded(regular(self.target / "descriptor.sha256"), 72)
            sha = raw_hash.decode("ascii")
            if not sha.endswith("\n"):
                _fail("untrusted_catalog", "retained")
            sha = sha[:-1]
            self._validate(body, sha)
            return body
        except PermissionError:
            _fail("permission_denied", "retained")
        except (OSError, UnicodeError, ConversionError):
            _fail("untrusted_catalog", "retained")
