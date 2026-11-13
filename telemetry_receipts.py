"""Inspect bounded consumer receipts offline without importing a Kafka client."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast

from telemetry_convert import load_job, verify_job
from telemetry_reader import MAX_EVENT_FILE_BYTES, read_battery_event

MAX_RECEIPT_BYTES = 64 * 1024
AUDIT_VERSION = "bounded-consumer-audit-v1"
type Phase = Literal["observed", "committed"]


class ReceiptAuditError(ValueError):
    """A fixed reason code without supplied identifiers or payloads."""


@dataclass(frozen=True)
class ReceiptContext:
    """Operator-supplied experiment and previously captured broker identities."""

    experiment_id: str
    cluster_id: str
    topic_id: str

    def validate(self) -> None:
        """Bound context independently of any receipt's claimed identity."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", self.experiment_id):
            raise ReceiptAuditError("invalid_experiment_context")
        if any(
            not re.fullmatch(r"[!-~]{1,128}", value)
            for value in (self.cluster_id, self.topic_id)
        ):
            raise ReceiptAuditError("invalid_broker_context")


def _object(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(k, str) for k in value):
        raise ReceiptAuditError("invalid_verified_manifest")
    return cast(Mapping[str, object], value)


def _count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ReceiptAuditError("invalid_verified_manifest")
    return value


def _serialized(report: dict[str, object]) -> bytes:
    return (
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def _exact_receipt(path: Path, expected: dict[str, object]) -> bytes:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise ReceiptAuditError("regular_receipt_required")
    with path.open("rb") as source:
        data = source.read(MAX_RECEIPT_BYTES + 1)
    if len(data) > MAX_RECEIPT_BYTES:
        raise ReceiptAuditError("receipt_bound_exceeded")
    if data != _serialized(expected):
        raise ReceiptAuditError("receipt_context_or_bytes_differ")
    return data


def audit_consumer_receipt(
    job: Path,
    run: Path,
    receipt: Path,
    context: ReceiptContext,
    *,
    phase: Phase = "committed",
    prior_receipt: Path | None = None,
    resume_from: int | None = None,
) -> dict[str, object]:
    """Reconstruct one fixed-fixture receipt and report recorded accounting only.

    Recovery needs an independently selected original precommit receipt and an
    explicit captured resume offset. No receipt field selects its own context.
    """
    context.validate()
    if phase not in {"observed", "committed"}:
        raise ReceiptAuditError("invalid_phase")
    recovery = prior_receipt is not None
    if (not recovery and resume_from is not None) or (
        recovery and (type(resume_from) is not int or resume_from not in (0, 3))
    ):
        raise ReceiptAuditError("invalid_recovery_context")
    if load_job(job).mode != "synthetic":
        raise ReceiptAuditError("synthetic_job_required")
    manifest = verify_job(job, run).run_manifest
    with (run / "events.jsonl").open("rb") as source:
        raw = source.read(MAX_EVENT_FILE_BYTES + 1)
    if len(raw) > MAX_EVENT_FILE_BYTES:
        raise ReceiptAuditError("event_file_bound_exceeded")
    artifact = _object(_object(manifest["artifacts"])["events.jsonl"])
    if artifact["sha256"] != "sha256:" + sha256(raw).hexdigest():
        raise ReceiptAuditError("verified_events_changed")
    values = raw.splitlines()
    if len(values) != 3:
        raise ReceiptAuditError("three_event_fixture_required")
    events = [read_battery_event(value) for value in values]
    if any(event["source_type"] != "synthetic" for event in events):
        raise ReceiptAuditError("synthetic_events_required")
    observed = [
        {
            "offset": index,
            "partition": 0,
            "event_id": event["event_id"],
            "value_sha256": sha256(values[index]).hexdigest(),
            "key_sha256": sha256(event["vehicle_id"].encode()).hexdigest(),
        }
        for index, event in enumerate(events)
    ]
    topic = f"m2.{context.experiment_id}.telemetry.canonical.v1"
    expected: dict[str, object] = {
        "receipt_version": "kafka-probe-receipt-v1",
        "status": "observed_before_commit",
        "experiment_id": context.experiment_id,
        "cluster_id": context.cluster_id,
        "topic_id": context.topic_id,
        "topic": topic,
        "client": "2.16.0",
        "librdkafka": "2.16.0",
        "events_file_sha256": sha256(raw).hexdigest(),
        "start_offset": 0,
        "end_offset": 3,
        "start_committed_offset": 0,
        "pending": 0,
        "acknowledged": [
            {
                "input_position": i,
                "acknowledged": True,
                "error_code": None,
                "partition": 0,
                "offset": i,
            }
            for i in range(3)
        ],
        "observed": observed,
        "consumer_config": {
            "bootstrap.servers": "127.0.0.1:19092",
            "group.id": f"m2-{context.experiment_id}",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "auto.offset.reset": "error",
            "group.protocol": "classic",
            "socket.timeout.ms": 10000,
        },
        "retention_scope": "single-local-replica",
    }
    prior_hash: str | None = None
    attempt_observations = 3
    if prior_receipt is not None:
        prior_hash = sha256(_exact_receipt(prior_receipt, expected)).hexdigest()
        attempt_observations = 3 if resume_from == 0 else 0
        expected.update(
            {
                "status": "recovery_observed_before_commit",
                "prior_receipt_sha256": prior_hash,
                "resume_from_offset": resume_from,
                "observed_this_attempt": observed if resume_from == 0 else [],
                "replayed_observations": attempt_observations,
                "unique_events": 3,
            }
        )
    if phase == "committed":
        expected.update(
            {
                "status": "consumer_receipt_recovery_verified"
                if recovery
                else "admission_and_clean_consumer_reopen_verified",
                "committed_next_offset": 3,
            }
        )
    checked = _exact_receipt(receipt, expected)
    counts = _object(manifest["counts"])
    return {
        "audit_version": AUDIT_VERSION,
        "status": "offline_receipt_consistent",
        "scope": "recorded_evidence_only",
        "phase": phase,
        "mode": "recovery" if recovery else "admission",
        "receipt_sha256": sha256(checked).hexdigest(),
        "prior_receipt_sha256": prior_hash,
        "events_file_sha256": sha256(raw).hexdigest(),
        "counts": {
            "source_records": _count(counts["source_records"]),
            "source_rejections": _count(counts["rejected_records"]),
            "original_acknowledged_records": 3,
            "covered_unique_events": 3,
            "observed_records_this_attempt": attempt_observations,
            "replayed_observations_this_attempt": attempt_observations
            if recovery
            else 0,
            "pending_records_recorded": 0,
        },
        "progress": {
            "captured_start_offset": 0,
            "captured_end_offset": 3,
            "recorded_resume_offset": resume_from,
            "recorded_committed_next_offset": 3 if phase == "committed" else None,
            "captured_commit_gap_records": 0 if phase == "committed" else None,
        },
        "unavailable": [
            "live_broker_identity",
            "live_lag_records",
            "publication_attempts",
            "acknowledgement_errors",
            "recovery_duration_seconds",
            "late_events",
            "throughput_records_per_second",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """Emit one safe JSON result; failure produces no partial success output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--cluster-id", required=True)
    parser.add_argument("--topic-id", required=True)
    parser.add_argument(
        "--phase", choices=("observed", "committed"), default="committed"
    )
    parser.add_argument("--prior-receipt", type=Path)
    parser.add_argument("--resume-from", type=int, choices=(0, 3))
    args = parser.parse_args(argv)
    try:
        result = audit_consumer_receipt(
            args.job,
            args.run,
            args.receipt,
            ReceiptContext(args.experiment, args.cluster_id, args.topic_id),
            phase=cast(Phase, args.phase),
            prior_receipt=args.prior_receipt,
            resume_from=args.resume_from,
        )
    except (ValueError, OSError) as error:
        reason = (
            str(error)
            if isinstance(error, ReceiptAuditError)
            else "source_or_io_failure"
        )
        print(json.dumps({"status": "failed", "reason": reason}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
