"""Malformed source context must not bypass the offline audit CLI error boundary."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conversion_support import obj, read_json, rewrite_job, write_job


@pytest.mark.parametrize(
    ("script", "arguments"),
    [
        (
            "telemetry_receipts.py",
            ["--receipt", "unused", "--experiment", "audit"],
        ),
        (
            "telemetry_publication.py",
            [
                "--commands",
                "unused",
                "--retry-receipt",
                "unused",
                "--observations",
                "unused",
                "--prefix",
                "audit",
            ],
        ),
    ],
)
def test_invalid_source_context_has_safe_json_failure(
    tmp_path: Path, script: str, arguments: list[str]
) -> None:
    job = write_job(tmp_path)
    spec = read_json(job)
    obj(obj(spec["manifest"])["clock_anchor"])["utc_anchor"] = "private-invalid-time"
    rewrite_job(job, spec)
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-O",
            str(Path(__file__).parents[1] / script),
            "--job",
            str(job),
            "--run",
            "unused",
            "--cluster-id",
            "synthetic",
            "--topic-id",
            "synthetic",
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2 and result.stdout == ""
    assert json.loads(result.stderr) == {
        "status": "failed",
        "reason": "source_or_io_failure",
    }
