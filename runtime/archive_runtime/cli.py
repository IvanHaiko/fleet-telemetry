"""Safe JSON command interface for the bounded Linux archive supervisor."""

import argparse
import json
import time
from pathlib import Path
from typing import NoReturn

from runtime.archive_runtime.config import directory, duration, load_config, regular
from runtime.archive_runtime.processes import _alarm
from runtime.archive_runtime.supervisor import Supervisor, load_job
from runtime.s3.immutable import StoreError
from telemetry.archive_codec import ArchiveError, _fail
from telemetry.archive_documents import CONTROL, checksum, digest, document
from telemetry.conversion_contract import ConversionError
from telemetry.local_io import read_bounded


class Arguments(argparse.Namespace):
    mode: str
    config: Path
    scratch_parent: Path
    timeout_seconds: float
    job: Path
    blob: list[str]
    group: str
    root_parent: Path
    non_transactional_fixture: bool
    test_failpoint: str | None
    descriptor: Path
    expected_sha256: str
    output: Path


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _fail("invalid_format", "config")


def main() -> int:
    started = time.monotonic()
    parser = Parser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("publish", "rebuild"):
        command = modes.add_parser(mode)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--scratch-parent", type=Path, required=True)
        command.add_argument("--timeout-seconds", type=float, default=120)
        if mode == "publish":
            command.add_argument("--job", type=Path, required=True)
            command.add_argument("--blob", action="append", required=True)
            command.add_argument("--group", required=True)
            command.add_argument("--root-parent", type=Path, required=True)
            command.add_argument(
                "--non-transactional-fixture", action="store_true", required=True
            )
            command.add_argument(
                "--test-failpoint",
                choices=(
                    "after_batch",
                    "after_receipt",
                    "after_retain",
                    "after_commit",
                ),
            )
        else:
            command.add_argument("--descriptor", type=Path, required=True)
            command.add_argument("--expected-sha256", required=True)
            command.add_argument("--output", type=Path, required=True)
    try:
        args = Arguments()
        parser.parse_args(namespace=args)
        timeout = duration(args.timeout_seconds)
        expires = started + timeout
        with _alarm(expires):
            config = load_config(args.config, publish=args.mode == "publish")
            scratch = directory(args.scratch_parent)
            if args.mode == "publish":
                root = directory(args.root_parent)
                job, blobs = load_job(args.job, args.blob, config)
                supervisor = Supervisor(
                    config, scratch, duration(expires - time.monotonic())
                )
                result = supervisor.publish(
                    job, blobs, args.group, root, args.test_failpoint
                )
            else:
                descriptor_path = regular(args.descriptor)
                body = read_bounded(descriptor_path, CONTROL)
                sha = checksum(args.expected_sha256)
                document(body, "descriptor")
                if digest(body) != sha:
                    raise ArchiveError("untrusted_catalog", "catalog")
                supervisor = Supervisor(
                    config, scratch, duration(expires - time.monotonic())
                )
                result = supervisor.rebuild(
                    body, sha, args.output, protected_root=descriptor_path.parent
                )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ArchiveError, StoreError) as error:
        print(
            json.dumps(
                {
                    "error": error.category,
                    "field": error.field
                    if isinstance(error, ArchiveError)
                    else "storage",
                }
            )
        )
    except (OSError, ConversionError, ValueError):
        print(json.dumps({"error": "invalid_format", "field": "config"}))
    return 1
