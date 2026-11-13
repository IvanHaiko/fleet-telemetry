"""Offline receipt risks: context substitution, replay accounting and safe refusal."""

import copy
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from telemetry_convert import convert_job
from telemetry_receipts import (
    MAX_RECEIPT_BYTES,
    Phase,
    ReceiptAuditError,
    ReceiptContext,
    audit_consumer_receipt,
)

ROOT = Path(__file__).parents[1]
JOB = ROOT / "tests/fixtures/synthetic-conversion-job.json"
SAMPLE = ROOT / "tests/fixtures/consumer-audit-receipt-v1.json"
CONTEXT = ReceiptContext("audit-fixture", "synthetic-cluster", "synthetic-topic-id")


@pytest.fixture
def run(tmp_path: Path) -> Path:
    output = tmp_path / "demo-synthetic-001"
    convert_job(JOB, output)
    return output


def sample() -> dict[str, object]:
    decoded: object = json.loads(SAMPLE.read_bytes())
    assert isinstance(decoded, dict)
    return cast(dict[str, object], decoded)


def wire(value: dict[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


@pytest.mark.parametrize("phase", ["observed", "committed"])
@pytest.mark.parametrize("resume", [None, 0, 3])
def test_recorded_populations_and_unknown_progress(
    tmp_path: Path, run: Path, phase: Phase, resume: int | None
) -> None:
    original = tmp_path / "original.json"
    original.write_bytes(SAMPLE.read_bytes())
    document = sample()
    if resume is not None:
        document.update(
            status="recovery_observed_before_commit",
            prior_receipt_sha256=sha256(original.read_bytes()).hexdigest(),
            resume_from_offset=resume,
            observed_this_attempt=document["observed"] if resume == 0 else [],
            replayed_observations=3 if resume == 0 else 0,
            unique_events=3,
        )
    if phase == "committed":
        document.update(
            status="admission_and_clean_consumer_reopen_verified"
            if resume is None
            else "consumer_receipt_recovery_verified",
            committed_next_offset=3,
        )
    receipt = tmp_path / "selected.json"
    receipt.write_bytes(wire(document))
    inputs = [JOB, SAMPLE, receipt, original, *run.iterdir()]
    before = {p: p.read_bytes() for p in inputs}
    report = audit_consumer_receipt(
        JOB,
        run,
        receipt,
        CONTEXT,
        phase=phase,
        prior_receipt=original if resume is not None else None,
        resume_from=resume,
    )
    expected_observations = 0 if resume == 3 else 3
    assert report["counts"] == {
        "source_records": 4,
        "source_rejections": 1,
        "original_acknowledged_records": 3,
        "covered_unique_events": 3,
        "observed_records_this_attempt": expected_observations,
        "replayed_observations_this_attempt": 3 if resume == 0 else 0,
        "pending_records_recorded": 0,
    }
    assert report["progress"] == {
        "captured_start_offset": 0,
        "captured_end_offset": 3,
        "recorded_resume_offset": resume,
        "recorded_committed_next_offset": 3 if phase == "committed" else None,
        "captured_commit_gap_records": 0 if phase == "committed" else None,
    }
    assert report["receipt_sha256"] == sha256(receipt.read_bytes()).hexdigest()
    assert report["scope"] == "recorded_evidence_only"
    assert "live_lag_records" in cast(list[str], report["unavailable"])
    serialized = json.dumps(report)
    assert all(
        identifier not in serialized
        for identifier in (
            CONTEXT.experiment_id,
            CONTEXT.cluster_id,
            CONTEXT.topic_id,
            "demo-vehicle-001",
            "m2.audit-fixture.telemetry.canonical.v1",
        )
    )
    assert before == {p: p.read_bytes() for p in inputs}


@pytest.mark.parametrize(
    "mutation", ["format", "extra", "duplicate", "truncated", "boolean", "hash", "size"]
)
def test_exact_checkpoint_refusal_preserves_input(
    tmp_path: Path, run: Path, mutation: str
) -> None:
    document = sample()
    data = wire(document)
    if mutation == "format":
        data = json.dumps(document).encode()
    elif mutation == "extra":
        document["sensitive-raw-example"] = "never-report-this-value"
        data = wire(document)
    elif mutation == "duplicate":
        data = data.replace(b'"pending": 0,', b'"pending": 0, "pending": 0,')
    elif mutation == "truncated":
        data = data[: len(data) // 2]
    elif mutation == "boolean":
        document["start_offset"] = False
        data = wire(document)
    elif mutation == "hash":
        document["events_file_sha256"] = "0" * 64
        data = wire(document)
    elif mutation == "size":
        data = b" " * (MAX_RECEIPT_BYTES + 1)
    receipt = tmp_path / "invalid.json"
    receipt.write_bytes(data)
    with pytest.raises(ReceiptAuditError) as error:
        audit_consumer_receipt(JOB, run, receipt, CONTEXT, phase="observed")
    assert str(error.value) in {
        "receipt_context_or_bytes_differ",
        "receipt_bound_exceeded",
    }
    assert receipt.read_bytes() == data


def test_context_prior_and_phase_cannot_be_selected_by_receipt(
    tmp_path: Path, run: Path
) -> None:
    receipt = tmp_path / "original.json"
    receipt.write_bytes(SAMPLE.read_bytes())
    for context in (
        ReceiptContext("other-experiment", CONTEXT.cluster_id, CONTEXT.topic_id),
        ReceiptContext(CONTEXT.experiment_id, "other-cluster", CONTEXT.topic_id),
        ReceiptContext(CONTEXT.experiment_id, CONTEXT.cluster_id, "other-topic-id"),
    ):
        with pytest.raises(ReceiptAuditError, match="receipt_context_or_bytes_differ"):
            audit_consumer_receipt(JOB, run, receipt, context, phase="observed")
    for prior, resume in ((None, 0), (receipt, None), (receipt, True), (receipt, 1)):
        with pytest.raises(ReceiptAuditError, match="invalid_recovery_context"):
            audit_consumer_receipt(
                JOB, run, receipt, CONTEXT, prior_receipt=prior, resume_from=resume
            )
    with pytest.raises(ReceiptAuditError, match="receipt_context_or_bytes_differ"):
        audit_consumer_receipt(JOB, run, receipt, CONTEXT)
    altered = copy.deepcopy(sample())
    altered["pending"] = 1
    prior = tmp_path / "bad-prior.json"
    prior.write_bytes(wire(altered))
    with pytest.raises(ReceiptAuditError, match="receipt_context_or_bytes_differ"):
        audit_consumer_receipt(
            JOB,
            run,
            receipt,
            CONTEXT,
            phase="observed",
            prior_receipt=prior,
            resume_from=0,
        )


def test_cli_uses_standard_library_under_optimization_and_fails_safely(
    tmp_path: Path, run: Path
) -> None:
    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(SAMPLE.read_bytes())
    args = [
        sys.executable,
        "-S",
        "-O",
        str(ROOT / "telemetry_receipts.py"),
        "--job",
        str(JOB),
        "--run",
        str(run),
        "--receipt",
        str(receipt),
        "--experiment",
        CONTEXT.experiment_id,
        "--cluster-id",
        CONTEXT.cluster_id,
        "--topic-id",
        CONTEXT.topic_id,
        "--phase",
        "observed",
    ]
    success = subprocess.run(args, capture_output=True, text=True, check=False)
    assert success.returncode == 0 and success.stderr == ""
    assert json.loads(success.stdout)["status"] == "offline_receipt_consistent"
    bad = sample()
    bad["sensitive-raw-example"] = "never-report-this-value"
    receipt.write_bytes(wire(bad))
    failure = subprocess.run(args, capture_output=True, text=True, check=False)
    assert failure.returncode == 2 and failure.stdout == ""
    assert json.loads(failure.stderr) == {
        "status": "failed",
        "reason": "receipt_context_or_bytes_differ",
    }
    before = (run / "events.jsonl").read_bytes()
    (run / "events.jsonl").write_bytes(before + b"\n")
    failure = subprocess.run(args, capture_output=True, text=True, check=False)
    assert failure.returncode == 2 and failure.stdout == ""
    assert json.loads(failure.stderr) == {
        "status": "failed",
        "reason": "source_or_io_failure",
    }
    assert receipt.read_bytes() == wire(bad)
    assert (run / "events.jsonl").read_bytes() == before + b"\n"
