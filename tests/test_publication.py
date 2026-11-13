"""Producer evidence risks beyond the existing consumer and normalization suite."""

import json
import subprocess
import sys
from collections.abc import Iterator, Sequence
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from telemetry_convert import convert_job
from telemetry_publication import (
    MAX_EVIDENCE_BYTES,
    ProducerContext,
    PublicationAuditError,
    audit_producer_publication,
    verify_publication_manifest,
)

ROOT = Path(__file__).parents[1]
JOB = ROOT / "tests/fixtures/synthetic-conversion-job.json"
SAMPLE = ROOT / "tests/fixtures/producer-audit-evidence-v1.json"
CONTEXT = ProducerContext("audit-producer", "synthetic-cluster", "synthetic-topic-id")


def obj(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def array(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def wire(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def log_bytes(rows: Sequence[object]) -> bytes:
    return b"".join(json.dumps(row).encode() + b"\n" for row in rows)


@pytest.fixture
def inputs(tmp_path: Path) -> Iterator[tuple[Path, Path, Path, Path]]:
    run = tmp_path / "demo-synthetic-001"
    convert_job(JOB, run)
    bundle = obj(json.loads(SAMPLE.read_bytes()))
    commands, retry, observed = [
        tmp_path / name
        for name in ("commands.jsonl", "retry-receipt.json", "observations.json")
    ]
    commands.write_bytes(log_bytes(array(bundle["commands"])))
    retry.write_bytes(wire(bundle["retry_receipt"]))
    observed.write_bytes(wire(bundle["observations"]))
    yield run, commands, retry, observed


def audit(inputs: tuple[Path, Path, Path, Path]) -> dict[str, object]:
    return audit_producer_publication(JOB, *inputs, CONTEXT)


def test_source_coverage_and_ack_populations_bind_manifest(
    tmp_path: Path, inputs: tuple[Path, Path, Path, Path]
) -> None:
    run, commands, retry, observed = inputs
    paths = [commands, retry, observed, *run.iterdir(), JOB, SAMPLE]
    before = {p: p.read_bytes() for p in paths}
    report = audit(inputs)
    assert report["accounting"] == {
        "source_records": 4,
        "source_rejections": 1,
        "publication_attempts_recorded": 2,
        "first_attempt_acknowledged": 3,
        "retry_attempt_acknowledged": 3,
        "acknowledgements_recorded": 6,
        "observations_recorded": 6,
        "unique_source_events": 3,
        "repeated_observations": 3,
        "first_attempt_pending_recorded": 0,
        "retry_attempt_pending_recorded": 0,
    }
    assert report["evidence_sha256"] == {
        "commands": sha256(commands.read_bytes()).hexdigest(),
        "retry_receipt": sha256(retry.read_bytes()).hexdigest(),
        "observations": sha256(observed.read_bytes()).hexdigest(),
    }
    assert (
        report["first_attempt_evidence_kind"]
        == "captured_stdout_without_durable_receipt"
    )
    assert report["scope"] == "recorded_evidence_only"
    assert "unrecorded_attempts" in array(report["unavailable"])
    manifest = tmp_path / "publication.json"
    manifest.write_bytes(wire(report))
    assert (
        verify_publication_manifest(manifest, audit(inputs))
        == sha256(wire(report)).hexdigest()
    )
    changed = obj(json.loads(manifest.read_bytes()))
    obj(changed["accounting"])["unique_source_events"] = 6
    manifest.write_bytes(wire(changed))
    with pytest.raises(PublicationAuditError, match="publication_manifest_differs"):
        verify_publication_manifest(manifest, audit(inputs))
    assert before == {p: p.read_bytes() for p in paths}


@pytest.mark.parametrize(
    "mutation",
    [
        "exit",
        "flags",
        "prefix",
        "ack_boolean",
        "duplicate_key",
        "nonfinite",
        "overflow",
        "surrogate",
        "retry_offset",
        "missing",
        "extra",
        "same_count_conflict",
        "key_hash",
        "size",
    ],
)
def test_evidence_failures_cannot_hide_in_counts_or_summary(
    inputs: tuple[Path, Path, Path, Path], mutation: str
) -> None:
    run, commands, retry, observed = inputs
    captures = [obj(json.loads(line)) for line in commands.read_bytes().splitlines()]
    first = obj(json.loads(cast(str, captures[0]["stdout"])))
    if mutation == "exit":
        captures[0]["exit_code"] = 0
    elif mutation == "flags":
        args = array(captures[1]["command"])
        args[-2] = "--prefix"
    elif mutation == "prefix":
        args = array(captures[0]["command"])
        args[args.index("--prefix") + 1] = "other-prefix"
    elif mutation == "ack_boolean":
        obj(array(first["acknowledged"])[0])["offset"] = False
        captures[0]["stdout"] = json.dumps(first)
    elif mutation in {"nonfinite", "overflow"}:
        value = "NaN" if mutation == "nonfinite" else "1e999"
        captures[0]["stdout"] = '{"future":' + value + "," + json.dumps(first)[1:]
    elif mutation == "surrogate":
        captures[0]["stderr"] = "\ud800"
    commands.write_bytes(log_bytes(captures))
    if mutation == "duplicate_key":
        commands.write_bytes(
            commands.read_bytes().replace(
                b'"exit_code": 88', b'"exit_code": 88, "exit_code": 88', 1
            )
        )
    if mutation == "retry_offset":
        document = obj(json.loads(retry.read_bytes()))
        obj(array(document["acknowledged"])[0])["offset"] = 0
        retry.write_bytes(wire(document))
    if mutation in {"missing", "extra", "same_count_conflict", "key_hash"}:
        rows = array(json.loads(observed.read_bytes()))
        if mutation == "missing":
            rows.pop()
        elif mutation == "extra":
            rows.append(rows[0])
        elif mutation == "same_count_conflict":
            obj(rows[0])["event_id"] = obj(rows[1])["event_id"]
        else:
            obj(rows[0])["key_sha256"] = "0" * 64
        observed.write_bytes(wire(rows))
    if mutation == "size":
        observed.write_bytes(b" " * (MAX_EVIDENCE_BYTES + 1))
    # A fabricated success summary must be irrelevant to independent input checks.
    (run.parent / "summary.json").write_bytes(
        b'{"status":"producer_failure_boundaries_verified"}'
    )
    before = {p: p.read_bytes() for p in (commands, retry, observed)}
    with pytest.raises(PublicationAuditError) as error:
        audit(inputs)
    assert "future" not in str(error.value)
    assert before == {p: p.read_bytes() for p in before}


def test_explicit_context_and_attempt_pair_are_required(
    inputs: tuple[Path, Path, Path, Path],
) -> None:
    run, commands, retry, observed = inputs
    for context in (
        ProducerContext("other-prefix", CONTEXT.cluster_id, CONTEXT.topic_id),
        ProducerContext(CONTEXT.prefix, "other-cluster", CONTEXT.topic_id),
        ProducerContext(CONTEXT.prefix, CONTEXT.cluster_id, "other-topic"),
    ):
        with pytest.raises(PublicationAuditError):
            audit_producer_publication(JOB, run, commands, retry, observed, context)
    captures = commands.read_bytes().splitlines(keepends=True)
    for selected in (captures[:1], captures * 2, list(reversed(captures))):
        commands.write_bytes(b"".join(selected))
        with pytest.raises(PublicationAuditError):
            audit(inputs)


def test_cli_roundtrip_exact_lf_and_safe_refusal_without_site_packages(
    tmp_path: Path, inputs: tuple[Path, Path, Path, Path]
) -> None:
    run, commands, retry, observed = inputs
    args = [
        sys.executable,
        "-S",
        "-O",
        str(ROOT / "telemetry_publication.py"),
        "--job",
        str(JOB),
        "--run",
        str(run),
        "--commands",
        str(commands),
        "--retry-receipt",
        str(retry),
        "--observations",
        str(observed),
        "--prefix",
        CONTEXT.prefix,
        "--cluster-id",
        CONTEXT.cluster_id,
        "--topic-id",
        CONTEXT.topic_id,
    ]
    emitted = subprocess.run(args, capture_output=True, check=False)
    assert emitted.returncode == 0 and emitted.stderr == b""
    assert emitted.stdout == wire(audit(inputs)) and b"\r" not in emitted.stdout
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(emitted.stdout)
    check = subprocess.run(
        args + ["--verify-manifest", str(manifest)], capture_output=True, check=False
    )
    assert check.returncode == 0
    assert obj(json.loads(check.stdout))["status"] == "offline_manifest_consistent"
    # Coordinated manifest hash edits cannot hide invalid observations.
    observed.write_bytes(b'[{"sensitive-raw-example":"never-report-this-value"}]')
    document = obj(json.loads(manifest.read_bytes()))
    obj(document["evidence_sha256"])["observations"] = sha256(
        observed.read_bytes()
    ).hexdigest()
    manifest.write_bytes(wire(document))
    before = manifest.read_bytes()
    check = subprocess.run(
        args + ["--verify-manifest", str(manifest)], capture_output=True, check=False
    )
    assert check.returncode == 2 and check.stdout == b""
    assert json.loads(check.stderr) == {
        "status": "failed",
        "reason": "observation_evidence_differs",
    }
    assert manifest.read_bytes() == before
