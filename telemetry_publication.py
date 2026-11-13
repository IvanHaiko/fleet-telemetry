"""Audit captured producer retry evidence and emit a bounded offline manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

from telemetry_convert import load_job, verify_job
from telemetry_reader import MAX_EVENT_FILE_BYTES, read_battery_event

MAX_EVIDENCE_BYTES = 1024 * 1024
MANIFEST_VERSION = "bounded-producer-publication-v1"


class PublicationAuditError(ValueError):
    """A safe fixed reason code without supplied paths or payloads."""


@dataclass(frozen=True)
class ProducerContext:
    """Explicit original experiment prefix and captured broker identities."""

    prefix: str
    cluster_id: str
    topic_id: str

    def validate(self) -> None:
        """Apply the existing producer experiment bounds to independent context."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", self.prefix):
            raise PublicationAuditError("invalid_producer_context")
        if any(
            not re.fullmatch(r"[!-~]{1,128}", value)
            for value in (self.cluster_id, self.topic_id)
        ):
            raise PublicationAuditError("invalid_producer_context")


def _wire(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def _read(path: Path) -> bytes:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise PublicationAuditError("regular_evidence_required")
    with path.open("rb") as source:
        raw = source.read(MAX_EVIDENCE_BYTES + 1)
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise PublicationAuditError("evidence_bound_exceeded")
    return raw


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PublicationAuditError("duplicate_evidence_key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise PublicationAuditError("invalid_evidence_json")


def _json(raw: bytes | str) -> object:
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        value: object = json.loads(
            text, object_pairs_hook=_pairs, parse_constant=_constant
        )
        # Reject nonfinite floats and invalid Unicode even in diagnostic text.
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return value
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, PublicationAuditError):
            raise
        raise PublicationAuditError("invalid_evidence_json") from None


def _object(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(k, str) for k in value):
        raise PublicationAuditError("invalid_evidence_shape")
    return cast(Mapping[str, object], value)


def _attempt(context: ProducerContext, start: int) -> dict[str, object]:
    topic = f"m2.{context.prefix}.producer.canonical.v1"
    return {
        "status": "acknowledged_before_local_receipt"
        if start == 0
        else "retry_attempt_receipt_verified",
        "cluster_id": context.cluster_id,
        "topic_id": context.topic_id,
        "topic": topic,
        "producer_config": {
            "bootstrap.servers": "127.0.0.1:19092",
            "enable.idempotence": True,
            "acks": "all",
            "max.in.flight.requests.per.connection": 5,
            "message.timeout.ms": 5000,
            "queue.buffering.max.messages": 1000,
            "queue.buffering.max.kbytes": 4096,
            "log_level": 0,
        },
        "acknowledged": [
            {
                "input_position": i,
                "acknowledged": True,
                "error_code": None,
                "topic": topic,
                "partition": 0,
                "offset": start + i,
            }
            for i in range(3)
        ],
        "pending": 0,
    }


def _capture(value: object, context: ProducerContext, retry: bool) -> None:
    record = _object(value)
    if set(record) != {"command", "exit_code", "stdout", "stderr"}:
        raise PublicationAuditError("invalid_process_capture")
    if type(record["exit_code"]) is not int or record["exit_code"] != (
        0 if retry else 88
    ):
        raise PublicationAuditError("unexpected_recorded_exit")
    command = record["command"]
    if not isinstance(command, list):
        raise PublicationAuditError("invalid_recorded_command")
    command = cast(list[object], command)
    if len(command) != (16 if retry else 12) or any(
        not isinstance(arg, str) or not arg or len(arg) > 4096 for arg in command
    ):
        raise PublicationAuditError("invalid_recorded_command")
    args = cast(list[str], command)
    if args[1].replace("\\", "/").rsplit("/", 1)[-1] != "check-kafka-producer.py":
        raise PublicationAuditError("invalid_recorded_command")
    flags = dict(zip(args[2::2], args[3::2], strict=True))
    required = {"--job", "--run", "--prefix", "--output", "--attempt"}
    if retry:
        required |= {"--expected-cluster", "--expected-topic"}
    if set(flags) != required or flags["--prefix"] != context.prefix:
        raise PublicationAuditError("invalid_recorded_command")
    if flags["--attempt"] != ("retry" if retry else "initial") or (
        retry
        and (flags["--expected-cluster"], flags["--expected-topic"])
        != (context.cluster_id, context.topic_id)
    ):
        raise PublicationAuditError("recorded_command_context_differs")
    expected_name = "retry-receipt.json" if retry else "lost-progress.json"
    if flags["--output"].replace("\\", "/").rsplit("/", 1)[-1] != expected_name:
        raise PublicationAuditError("invalid_recorded_command")
    if not isinstance(record["stdout"], str) or not isinstance(record["stderr"], str):
        raise PublicationAuditError("invalid_process_capture")
    if _wire(_json(record["stdout"])) != _wire(_attempt(context, 3 if retry else 0)):
        raise PublicationAuditError("attempt_evidence_differs")


def audit_producer_publication(
    job: Path,
    run: Path,
    commands: Path,
    retry_receipt: Path,
    observations: Path,
    context: ProducerContext,
) -> dict[str, object]:
    """Bind original source, both captured attempts and exact retry observations.

    This inspects recorded evidence only. It cannot recreate durable producer
    progress, authenticate historical observations or authorize a retry.
    """
    context.validate()
    if load_job(job).mode != "synthetic":
        raise PublicationAuditError("synthetic_job_required")
    verified = verify_job(job, run).run_manifest
    with (run / "events.jsonl").open("rb") as source:
        raw = source.read(MAX_EVENT_FILE_BYTES + 1)
    if len(raw) > MAX_EVENT_FILE_BYTES:
        raise PublicationAuditError("event_file_bound_exceeded")
    artifact = _object(_object(verified["artifacts"])["events.jsonl"])
    if artifact["sha256"] != "sha256:" + sha256(raw).hexdigest():
        raise PublicationAuditError("verified_events_changed")
    values = raw.splitlines()
    if len(values) != 3:
        raise PublicationAuditError("three_event_fixture_required")
    events = [read_battery_event(value) for value in values]
    if any(event["source_type"] != "synthetic" for event in events):
        raise PublicationAuditError("synthetic_events_required")

    captured = _read(commands)
    lines = captured.splitlines()
    if len(lines) != 2:
        raise PublicationAuditError("two_attempt_captures_required")
    for index, line in enumerate(lines):
        _capture(_json(line), context, retry=index == 1)
    retry = _read(retry_receipt)
    if retry != _wire(_attempt(context, 3)):
        raise PublicationAuditError("retry_receipt_differs")
    expected_observations = [
        {
            "offset": index,
            "partition": 0,
            "event_id": events[index % 3]["event_id"],
            "key_sha256": sha256(events[index % 3]["vehicle_id"].encode()).hexdigest(),
            "value_sha256": sha256(values[index % 3]).hexdigest(),
        }
        for index in range(6)
    ]
    observed = _read(observations)
    if observed != _wire(expected_observations):
        raise PublicationAuditError("observation_evidence_differs")
    counts = _object(verified["counts"])
    return {
        "manifest_version": MANIFEST_VERSION,
        "status": "offline_publication_consistent",
        "scope": "recorded_evidence_only",
        "protocol": "ADR-0015",
        "context": {
            "producer_prefix": context.prefix,
            "cluster_id": context.cluster_id,
            "topic_id": context.topic_id,
            "topic": f"m2.{context.prefix}.producer.canonical.v1",
            "partition": 0,
            "captured_interval": [0, 6],
        },
        "source": {
            "job_sha256": verified["job_sha256"],
            "source_log_id": verified["source_log_id"],
            "dataset_run_id": verified["dataset_run_id"],
            "pipeline_version": verified["pipeline_version"],
            "semantic_sha256": verified["semantic_sha256"],
            "events_file_sha256": sha256(raw).hexdigest(),
        },
        "evidence_sha256": {
            "commands": sha256(captured).hexdigest(),
            "retry_receipt": sha256(retry).hexdigest(),
            "observations": sha256(observed).hexdigest(),
        },
        "accounting": {
            "source_records": counts["source_records"],
            "source_rejections": counts["rejected_records"],
            "publication_attempts_recorded": 2,
            "first_attempt_acknowledged": 3,
            "retry_attempt_acknowledged": 3,
            "acknowledgements_recorded": 6,
            "observations_recorded": 6,
            "unique_source_events": 3,
            "repeated_observations": 3,
            "first_attempt_pending_recorded": 0,
            "retry_attempt_pending_recorded": 0,
        },
        "first_attempt_evidence_kind": "captured_stdout_without_durable_receipt",
        "retry_attempt_evidence_kind": "saved_attempt_receipt",
        "unavailable": [
            "live_broker_identity",
            "current_retention",
            "live_lag_records",
            "acknowledgement_latency_seconds",
            "recovery_duration_seconds",
            "late_events",
            "unrecorded_attempts",
        ],
    }


def verify_publication_manifest(path: Path, expected: dict[str, object]) -> str:
    """Compare saved manifest bytes with independently regenerated evidence."""
    raw = _read(path)
    if raw != _wire(expected):
        raise PublicationAuditError("publication_manifest_differs")
    return sha256(raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    """Emit exact LF manifest bytes or safely verify an existing manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--commands", type=Path, required=True)
    parser.add_argument("--retry-receipt", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--cluster-id", required=True)
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--verify-manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = audit_producer_publication(
            args.job,
            args.run,
            args.commands,
            args.retry_receipt,
            args.observations,
            ProducerContext(args.prefix, args.cluster_id, args.topic_id),
        )
        if args.verify_manifest is not None:
            digest = verify_publication_manifest(args.verify_manifest, manifest)
            print(
                json.dumps(
                    {"status": "offline_manifest_consistent", "manifest_sha256": digest}
                )
            )
        else:
            sys.stdout.buffer.write(_wire(manifest))
    except (ValueError, OSError) as error:
        reason = (
            str(error)
            if isinstance(error, PublicationAuditError)
            else "source_or_io_failure"
        )
        print(json.dumps({"status": "failed", "reason": reason}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
