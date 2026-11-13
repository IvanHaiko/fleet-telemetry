"""Bounded local conversion with explicit reconciliation and fresh run outputs."""

import argparse
import importlib.metadata
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from telemetry import artifacts as run_artifacts
from telemetry import local_io
from telemetry.conversion_contract import (
    SEMANTIC_FIELDS,
    ConversionError,
    ConversionJob,
    ConversionResult,
    json_line,
)
from telemetry.jobs import load_job
from telemetry.validation import InvalidInput
from ulog_integrity import InputIntegrityError


def convert_job(job_path: Path, output_directory: Path) -> ConversionResult:
    """Validate all source outcomes, then publish a fresh bounded run."""
    job = load_job(job_path)
    target = local_io.destination(output_directory, job.delivery.dataset_run_id)
    artifacts, manifest = run_artifacts.prepare_run(job)
    stage = Path(tempfile.mkdtemp(prefix=".telemetry-stage-", dir=target.parent))
    try:
        for name, content in artifacts.items():
            with (stage / name).open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        with (stage / "run-manifest.json").open("xb") as handle:
            handle.write(json_line(manifest))
            handle.flush()
            os.fsync(handle.fileno())
        local_io.publish_run(stage, target)
    except BaseException:
        # The checked absolute stage was created here and remains under this parent.
        if (
            stage.is_dir()
            and not stage.is_symlink()
            and not stage.is_junction()
            and stage.resolve().parent == target.parent
            and stage.name.startswith(".telemetry-stage-")
        ):
            shutil.rmtree(stage)
        raise
    return ConversionResult(target, manifest)


def verify_job(job_path: Path, output_directory: Path) -> ConversionResult:
    """Read-only, byte-exact replay verification under the current pinned runtime.

    Regenerate expected bytes from the external job and registered source rather
    than trusting mutually consistent hashes supplied by a modified run.
    """
    job = load_job(job_path)
    target = local_io.run_path(output_directory, job.delivery.dataset_run_id)
    if not target.is_dir():
        raise ConversionError("invalid_verification_directory")
    names = {"events.jsonl", "rejections.jsonl", "run-manifest.json"}
    seen: set[str] = set()
    for index, item in enumerate(target.iterdir()):
        if index >= 3 or item.name not in names:
            raise ConversionError("invalid_run_contents")
        if item.is_symlink() or item.is_junction():
            raise ConversionError("output_symlink_unsupported")
        seen.add(item.name)
    if seen != names:
        raise ConversionError("invalid_run_contents")
    artifacts, manifest = run_artifacts.prepare_run(job)
    artifacts["run-manifest.json"] = json_line(manifest)
    for name, expected in artifacts.items():
        try:
            actual = local_io.read_bounded(target / name, len(expected))
        except ConversionError as error:
            if error.reason == "input_too_large":
                raise ConversionError("run_artifact_mismatch") from None
            raise
        if actual != expected:
            raise ConversionError("run_artifact_mismatch")
    return ConversionResult(target, manifest)


class _Arguments(argparse.Namespace):
    job: Path
    output: Path | None
    verify: Path | None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a bounded local telemetry source."
    )
    parser.add_argument("--job", required=True, type=Path)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument("--verify", type=Path)
    args = parser.parse_args(argv, namespace=_Arguments())
    try:
        if args.verify is not None:
            result = verify_job(args.job, args.verify)
            status = "verified"
        else:
            assert args.output is not None
            result = convert_job(args.job, args.output)
            status = str(result.run_manifest["status"])
    except (
        ConversionError,
        InputIntegrityError,
        InvalidInput,
        OSError,
        importlib.metadata.PackageNotFoundError,
    ) as error:
        reason = (
            error.reason
            if isinstance(error, (ConversionError, InputIntegrityError))
            else "validation_or_io_failure"
        )
        print(json.dumps({"status": "failed", "reason": reason}), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": status,
                "counts": result.run_manifest["counts"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    "SEMANTIC_FIELDS",
    "ConversionError",
    "ConversionJob",
    "ConversionResult",
    "load_job",
    "convert_job",
    "verify_job",
    "main",
]
