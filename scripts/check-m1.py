"""Run the locked M1 checks on Windows or Linux with an installed Python 3.13."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "fleet_telemetry.py",
    "telemetry",
    "ulog_integrity.py",
    "ulog_reader.py",
    "telemetry_convert.py",
    "telemetry_reader.py",
    "telemetry_receipts.py",
    "telemetry_publication.py",
    "telemetry_metrics.py",
    "telemetry_reference.py",
    "tests",
    "scripts/check-m1.py",
    "scripts/check-observability.py",
    "scripts/check-flink-scrape.py",
    "scripts/benchmark-transport.py",
]


def check_module_sizes() -> None:
    """Keep owned Python modules below the agreed 500-line boundary."""
    paths = list(ROOT.glob("*.py"))
    for directory in ("telemetry", "scripts", "tests", "runtime"):
        paths.extend((ROOT / directory).rglob("*.py"))
    oversized = [
        str(path.relative_to(ROOT))
        for path in sorted(paths)
        if len(path.read_text(encoding="utf-8").splitlines()) >= 500
    ]
    if oversized:
        raise ValueError(
            "Python modules must have fewer than 500 lines: " + ", ".join(oversized)
        )


def run(arguments: list[str], environment: dict[str, str]) -> None:
    """Stop the lane when a command fails; preserve its output and exact exit."""
    print("+ " + subprocess.list2cmdline(arguments), flush=True)
    subprocess.run(arguments, cwd=ROOT, env=environment, check=True)


def main() -> int:
    """Install one locked profile, check it and retain a fresh CLI smoke run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("synthetic", "ulog"), default="synthetic")
    parser.add_argument("--cache-directory", default=".uv-cache")
    parser.add_argument("--offline", action="store_true")
    options = parser.parse_args()
    if sys.version_info[:2] != (3, 13) or sys.platform not in {"win32", "linux"}:
        parser.error("M1 checks require Python 3.13 on Windows or Linux.")
    environment = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(ROOT / ".venv"))
    try:
        check_module_sizes()
        version = subprocess.run(
            ["uv", "--version"],
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not re.match(r"^uv 0\.11\.19(?: |$)", version):
            raise ValueError("M1 checks require uv 0.11.19.")
        common = [
            "--cache-dir",
            options.cache_directory,
            "--python",
            sys.executable,
            "--no-python-downloads",
        ]
        if options.offline:
            common.append("--offline")
        run(["uv", "lock", "--check", *common], environment)
        extra = ["--extra", "ulog"] if options.profile == "ulog" else []
        run(["uv", "sync", "--frozen", *common, *extra], environment)
        executable = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
        python = str(ROOT / ".venv" / executable)
        if options.profile == "ulog":
            dependency_check = (
                "from importlib.metadata import version; "
                'expected = {"pyulog": "1.2.2", "numpy": "2.3.5"}; '
                "actual = {name: version(name) for name in expected}; "
                'sys.exit(0 if actual == expected else "ULog dependency mismatch")'
            )
        else:
            dependency_check = (
                "from importlib.util import find_spec; "
                'present = [n for n in ("pyulog", "numpy") if find_spec(n)]; '
                'sys.exit("Unexpected optional packages: " + str(present) if present '
                "else 0)"
            )
        run([python, "-c", "import sys; " + dependency_check], environment)
        # Ruff covers every tracked Python file; it honours .gitignore, so local
        # evidence trees stay out. Strict mypy stays on the typed core list.
        run([python, "-m", "ruff", "check", "."], environment)
        run([python, "-m", "ruff", "format", "--check", "."], environment)
        run([python, "-m", "mypy", *SOURCES], environment)

        # Pytest can clear basetemp. Use a fresh owned subtree inside the project.
        evidence = (ROOT / ".local-discovery").resolve()
        if not evidence.is_relative_to(ROOT):
            raise ValueError("Check evidence directory must stay inside the workspace.")
        evidence.mkdir(exist_ok=True)
        run_parent = Path(tempfile.mkdtemp(prefix="m1-check-", dir=evidence))
        run(
            [
                python,
                "-m",
                "pytest",
                "-q",
                "--tb=short",
                "--basetemp=" + str(run_parent / "pytest"),
            ],
            environment,
        )
        output = str(run_parent / "demo-synthetic-001")
        fixture = "tests/fixtures/synthetic-conversion-job.json"
        run(
            [
                python,
                "-S",
                "telemetry_convert.py",
                "--job",
                fixture,
                "--output",
                output,
            ],
            environment,
        )
        run(
            [
                python,
                "-S",
                "telemetry_convert.py",
                "--job",
                fixture,
                "--verify",
                output,
            ],
            environment,
        )
        run(
            [python, "-S", "telemetry_reader.py", str(Path(output) / "events.jsonl")],
            environment,
        )
        print(f"M1 {options.profile} checks passed. Retained smoke output: {output}")
    except subprocess.CalledProcessError as error:
        print(
            f"M1 check failed (exit {error.returncode}): {error.cmd}", file=sys.stderr
        )
        return error.returncode if 0 < error.returncode < 256 else 1
    except (OSError, ValueError) as error:
        print(f"M1 setup failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
