"""Run the Python 3.13 toolchain and bounded offline archive checks."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = [
    "runtime/s3/immutable.py",
    "runtime/s3/boto_transport.py",
    "runtime/s3/prepare_image.py",
    "runtime/s3/archive_store.py",
    *sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "runtime/archive_runtime").glob("*.py")
    ),
    "scripts/archive.py",
    *sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "telemetry").glob("archive_*.py")
    ),
    *sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "runtime/kafka_archive").glob("*.py")
    ),
    "telemetry/serving_projection.py",
    "telemetry/serving_sink.py",
    "runtime/clickhouse/transport.py",
    "scripts/slice_queries.py",
    "scripts/slice_run.py",
    "scripts/replay-slice.py",
    "scripts/check-m4.py",
]


def main() -> int:
    """Check pure/fake boundaries without installing SDKs or starting services."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13):
        parser.error("The documented M4 profile requires Python 3.13.")
    if args.report is not None and (args.report.exists() or args.report.is_symlink()):
        parser.error("The report must name a fresh output file.")
    fixtures = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "runtime/m4_acceptance").glob("*.py")
    )
    sources = PRODUCTION + fixtures
    hashes: dict[str, str] = {}
    for name in sources:
        data = (ROOT / name).read_bytes()
        if len(data.decode("utf-8").splitlines()) >= 500:
            parser.error("An M4 Python module exceeds the agreed size limit.")
        hashes[name] = hashlib.sha256(data).hexdigest()
    linux_only = [
        name
        for name in PRODUCTION
        if name.startswith("runtime/archive_runtime/")
        or name in {"scripts/archive.py", "scripts/replay-slice.py"}
    ]
    commands = [
        [sys.executable, "-m", "ruff", "check", "--no-cache", *sources],
        [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", *sources],
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--explicit-package-bases",
            *[name for name in PRODUCTION if name not in linux_only],
        ],
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--explicit-package-bases",
            "--platform",
            "linux",
            *linux_only,
        ],
        [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            str(ROOT / "runtime/m4_acceptance"),
            "-v",
        ],
    ]
    results = _run_checks(commands)
    complete = len(results) == len(commands) and all(
        row.get("exit_code") == 0 and row.get("timed_out") is False for row in results
    )
    report = {"complete": complete, "sha256": hashes, "checks": results}
    if args.report is not None:
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    return 0 if complete else 1


def _run_checks(commands: list[list[str]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for command in commands:
        print("+ " + subprocess.list2cmdline(command), flush=True)
        try:
            if "unittest" in command:
                outcome = _run_suite(command)
            else:
                outcome = subprocess.run(
                    command, cwd=ROOT, capture_output=True, text=True, timeout=120
                )
        except subprocess.TimeoutExpired:
            results.append({"args": command, "timed_out": True})
            break
        except OSError:
            results.append({"args": command, "launch_failed": True})
            break
        print(outcome.stdout, end="", flush=True)
        print(outcome.stderr, end="", file=sys.stderr, flush=True)
        results.append(
            {
                "args": command,
                "exit_code": outcome.returncode,
                "stdout": outcome.stdout,
                "stderr": outcome.stderr,
                "timed_out": False,
            }
        )
        if outcome.returncode != 0:
            break
    return results


def _run_suite(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Keep reconstruction scratch outside the checkout and preserve fixtures."""
    with tempfile.TemporaryDirectory(prefix="fleet-archive-checks-") as temporary:
        working = Path(temporary)
        (working / "scratch").mkdir()
        fixtures = working / "tests/fixtures"
        fixtures.mkdir(parents=True)
        for name in (
            "synthetic-battery-v1.json",
            "synthetic-conversion-job.json",
            "expected-battery-v1.json",
        ):
            shutil.copyfile(ROOT / "tests/fixtures" / name, fixtures / name)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            command, cwd=working, env=env, capture_output=True, text=True, timeout=120
        )


if __name__ == "__main__":
    raise SystemExit(main())
