"""File-boundary evidence: reconciliation, replay and failure before publication."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conversion_support import assert_no_output, obj, read_json, rewrite_job, write_job

import telemetry_convert as converter


def test_synthetic_cli_requires_no_optional_site_packages(tmp_path: Path) -> None:
    job = write_job(tmp_path)
    run = subprocess.run(
        [
            sys.executable,
            "-S",
            "telemetry_convert.py",
            "--job",
            str(job),
            "--output",
            str(tmp_path / "run-001"),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert obj(json.loads(run.stdout))["status"] == "completed_with_rejections"
    verified = subprocess.run(
        [
            sys.executable,
            "-S",
            "telemetry_convert.py",
            "--job",
            str(job),
            "--verify",
            str(tmp_path / "run-001"),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr
    assert obj(json.loads(verified.stdout))["status"] == "verified"
    checked = subprocess.run(
        [
            sys.executable,
            "-S",
            "telemetry_reader.py",
            str(tmp_path / "run-001/events.jsonl"),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr
    assert obj(json.loads(checked.stdout)) == {"status": "validated", "records": 3}


def test_cli_errors_do_not_expose_raw_diagnostics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def failure(*args: object) -> converter.ConversionResult:
        raise PermissionError("private-token-and-coordinates")

    monkeypatch.setattr(converter, "convert_job", failure)
    assert (
        converter.main(["--job", "missing", "--output", str(tmp_path / "run-001")]) == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err) == {
        "status": "failed",
        "reason": "validation_or_io_failure",
    }
    monkeypatch.setattr(converter, "verify_job", failure)
    assert (
        converter.main(["--job", "missing", "--verify", str(tmp_path / "run-001")]) == 2
    )
    assert json.loads(capsys.readouterr().err)["reason"] == "validation_or_io_failure"


def test_nul_in_input_path_has_safe_cli_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    job = write_job(tmp_path)
    spec = read_json(job)
    obj(spec["input"])["path"] = "private\x00input.json"
    rewrite_job(job, spec)
    assert (
        converter.main(["--job", str(job), "--output", str(tmp_path / "run-001")]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "failed", "reason": "invalid_string"}
    assert_no_output(tmp_path)
