"""Verify producer loss of local progress, retry reconciliation and bounded failure."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from confluent_kafka import (
    KafkaException,
)
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kafka_evidence import obj, require, save  # noqa: E402
from kafka_producer_transport import (  # noqa: E402
    ENDPOINT,
    fixture,
    identity,
    publish,
    read_records,
    unavailable,
)
from kafka_reconciliation import negative_reconciliation, reconcile  # noqa: E402
from kafka_topic_policy import (  # noqa: E402
    admit_fixture,
    topic_config,
    verify_topic_config,
)

from telemetry_convert import (  # noqa: E402
    ConversionError,
)
from telemetry_reader import EnvelopeError, read_battery_event  # noqa: E402


def attempt(
    job: Path,
    run: Path,
    topic: str,
    output: Path,
    retry: bool,
    expected_cluster: str | None,
    expected_topic: str | None,
) -> dict[str, object]:
    """Crash after ACK before a receipt, or explicitly retry the captured source."""
    require(
        not output.exists() and output.parent.is_dir(), "fresh_attempt_receipt_required"
    )
    values = fixture(job, run)
    admin = AdminClient({"bootstrap.servers": ENDPOINT, "log_level": 0})
    keys = tuple(read_battery_event(value)["vehicle_id"].encode() for value in values)
    admit_fixture(admin, values, keys)
    if not retry:
        require(topic not in admin.list_topics(timeout=15).topics, "topic_exists")
        admin.create_topics(
            [
                NewTopic(
                    topic,
                    num_partitions=1,
                    replication_factor=1,
                    config=topic_config(),
                )
            ],
            request_timeout=10,
        )[topic].result(timeout=12)
    ids = identity(admin, topic, wait_for_creation=not retry)
    verify_topic_config(admin, topic)
    if retry:
        require(ids == (expected_cluster, expected_topic), "retry_identity_differs")
        first = read_records(topic, 3)
        require(
            [r.value for r in first] == list(values)
            and all(
                r.key == read_battery_event(r.value)["vehicle_id"].encode()
                for r in first
            ),
            "retry_source_coverage_differs",
        )
    report = {
        "status": "acknowledged_before_local_receipt",
        "cluster_id": ids[0],
        "topic_id": ids[1],
        "topic": topic,
        **publish(topic, values, 3 if retry else 0),
    }
    if not retry:
        print(json.dumps(report), flush=True)
        os._exit(88)
    require(identity(admin, topic) == ids, "topic_changed_during_attempt")
    report["status"] = "retry_attempt_receipt_verified"
    save(output, report)
    return report


def check(job: Path, run: Path, prefix: str, output: Path) -> dict[str, object]:
    """Run both child processes and independently reconcile all six observations."""
    require(bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", prefix)), "invalid_prefix")
    values = fixture(job, run)
    require(not output.exists() and output.parent.is_dir(), "fresh_output_required")
    output.mkdir()
    topic = f"m2.{prefix}.producer.canonical.v1"
    commands: list[dict[str, object]] = []
    report: dict[str, object] = {
        "status": "incomplete",
        "topic": topic,
        "commands": commands,
    }

    def child(retry: bool, ids: tuple[str, str] | None = None) -> dict[str, object]:
        destination = output / ("retry-receipt.json" if retry else "lost-progress.json")
        args = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--job",
            str(job),
            "--run",
            str(run),
            "--prefix",
            prefix,
            "--output",
            str(destination),
            "--attempt",
            "retry" if retry else "initial",
        ]
        if ids is not None:
            args += ["--expected-cluster", ids[0], "--expected-topic", ids[1]]
        result = subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, timeout=45, check=False
        )
        commands.append(
            {
                "command": args,
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )
        with (output / "commands.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(commands[-1]) + "\n")
        require(result.returncode == (0 if retry else 88), "unexpected_child_exit")
        require(
            not destination.exists() if not retry else destination.is_file(),
            "attempt_receipt_state",
        )
        return obj(json.loads(result.stdout))

    try:
        first = child(False)
        require(
            first["status"] == "acknowledged_before_local_receipt", "wrong_failpoint"
        )
        admin = AdminClient({"bootstrap.servers": ENDPOINT, "log_level": 0})
        ids = identity(admin, topic)
        require(
            (first["cluster_id"], first["topic_id"]) == ids, "first_identity_differs"
        )
        initial_rows = read_records(topic, 3)
        require([r.value for r in initial_rows] == list(values), "first_source_differs")
        second = child(True, ids)
        rows = read_records(topic, 6)
        require(identity(admin, topic) == ids, "final_identity_differs")
        result = reconcile(values, rows)
        require(
            result
            == {
                "observations": 6,
                "unique_expected": 3,
                "duplicate_observations": 3,
                "missing_identities": 0,
                "extra_identities": 0,
                "conflicting_identities": 0,
                "byte_mismatches": 0,
                "key_mismatches": 0,
            },
            "retry_reconciliation_failed",
        )
        raw_rows = [
            {
                "offset": r.offset,
                "partition": 0,
                "event_id": read_battery_event(r.value)["event_id"],
                "key_sha256": hashlib.sha256(r.key).hexdigest(),
                "value_sha256": hashlib.sha256(r.value).hexdigest(),
            }
            for r in rows
        ]
        save(output / "observations.json", raw_rows)
        report.update(
            {
                "first_attempt": first,
                "retry_attempt": second,
                "cluster_id": ids[0],
                "topic_id": ids[1],
                "retained_interval": [0, 6],
                "reconciliation": result,
                "negative_reconciliation": negative_reconciliation(job, values, rows),
                "unavailable": unavailable(values, 1000),
                "queue_pressure": unavailable(values, 1),
                "source_events_sha256": hashlib.sha256(
                    (run / "events.jsonl").read_bytes()
                ).hexdigest(),
                "status": "producer_failure_boundaries_verified",
            }
        )
    finally:
        save(output / "summary.json", report)
    return {
        "status": report["status"],
        "observations": 6,
        "unique_expected": 3,
        "duplicate_observations": 3,
        "evidence": str(output / "summary.json"),
    }


def main() -> int:
    """Expect the isolated broker to be running; a suite owns its lifecycle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attempt", choices=("initial", "retry"))
    parser.add_argument("--expected-cluster")
    parser.add_argument("--expected-topic")
    args = parser.parse_args()
    try:
        require(
            bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", args.prefix)),
            "invalid_prefix",
        )
        if args.attempt:
            result = attempt(
                args.job,
                args.run,
                f"m2.{args.prefix}.producer.canonical.v1",
                args.output,
                args.attempt == "retry",
                args.expected_cluster,
                args.expected_topic,
            )
        else:
            result = check(args.job, args.run, args.prefix, args.output)
        print(json.dumps(result))
    except (
        ValueError,
        ConversionError,
        EnvelopeError,
        KafkaException,
        OSError,
        BufferError,
        TimeoutError,
        subprocess.TimeoutExpired,
    ):
        print(
            json.dumps({"status": "failed", "reason": "producer_check_failed"}),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
