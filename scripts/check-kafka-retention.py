"""Expire only a fresh synthetic topic and verify explicit recovery refusal."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

from confluent_kafka import Consumer, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient
from confluent_kafka.admin._config import AlterConfigOpType, ConfigEntry, ConfigResource
from confluent_kafka.admin._resource import ResourceType

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "scripts/kafka-probe.py"
SETTINGS = {
    "retention.ms": "1000",
    "segment.ms": "1000",
    "file.delete.delay.ms": "1000",
}
FIELDS = (
    *SETTINGS,
    "cleanup.policy",
    "retention.bytes",
    "segment.bytes",
    "min.insync.replicas",
)


def require(condition: bool, reason: str) -> None:
    """Keep experiment checks active with Python optimization enabled."""
    if not condition:
        raise ValueError(reason)


def obj(value: object) -> dict[str, object]:
    """Validate a JSON or upstream dictionary boundary."""
    require(isinstance(value, dict), "expected_object")
    result = cast(dict[object, object], value)
    require(all(isinstance(k, str) for k in result), "expected_string_keys")
    return cast(dict[str, object], result)


def settings(admin: AdminClient, topic: str) -> dict[str, str | None]:
    """Read the relevant live topic settings through the pinned admin API."""
    resource = ConfigResource(ResourceType.TOPIC, topic)
    decoded: object = admin.describe_configs([resource], request_timeout=10)[
        resource
    ].result(timeout=12)
    entries = obj(decoded)
    result: dict[str, str | None] = {}
    for name in FIELDS:
        entry = entries[name]
        require(isinstance(entry, ConfigEntry), "unexpected_config_entry")
        result[name] = cast(ConfigEntry, entry).value
    return result


def progress(experiment: str) -> tuple[int, tuple[int, int]]:
    """Read committed progress and watermarks without assigning or committing."""
    topic = f"m2.{experiment}.telemetry.canonical.v1"
    consumer = Consumer(
        {
            "bootstrap.servers": "127.0.0.1:19092",
            "group.id": f"m2-{experiment}",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "auto.offset.reset": "error",
            "socket.timeout.ms": 10000,
            "log_level": 0,
        }
    )
    try:
        stored = consumer.committed([TopicPartition(topic, 0)], timeout=10)
        require(
            len(stored) == 1
            and stored[0].error is None
            and stored[0].topic == topic
            and stored[0].partition == 0,
            "committed_progress_lookup_failed",
        )
        return stored[0].offset, consumer.get_watermark_offsets(
            TopicPartition(topic, 0), timeout=10
        )
    finally:
        consumer.close()


def check(job: Path, run: Path, experiment: str, output: Path) -> dict[str, object]:
    """Apply time retention to this run's new topic, never delete records by API."""
    require(
        bool(re.fullmatch(r"retention-[a-z0-9][a-z0-9-]{0,37}", experiment)),
        "isolated_retention_experiment_required",
    )
    require(not output.exists() and output.parent.is_dir(), "fresh_output_required")
    output.mkdir()
    topic = f"m2.{experiment}.telemetry.canonical.v1"
    checkpoint = output / "before-commit.json"
    commands: list[dict[str, object]] = []
    report: dict[str, object] = {
        "status": "incomplete",
        "experiment_id": experiment,
        "topic": topic,
        "expiration_mode": "topic-time-retention",
        "commands": commands,
    }

    def child(expected: int, resume: bool) -> subprocess.CompletedProcess[str]:
        destination = output / "refused-recovery.json" if resume else checkpoint
        args = [
            sys.executable,
            str(PROBE),
            "--job",
            str(job),
            "--run",
            str(run),
            "--experiment",
            experiment,
            "--receipt",
            str(destination),
        ]
        args.extend(
            ["--resume-receipt", str(checkpoint)]
            if resume
            else ["--crash-at", "before-commit"]
        )
        result = subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, timeout=45, check=False
        )
        row: dict[str, object] = {
            "command": args,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        commands.append(row)
        with (output / "commands.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(row) + "\n")
        require(result.returncode == expected, "unexpected_child_result")
        return result

    try:
        child(86, False)
        original = checkpoint.read_bytes()
        receipt = obj(json.loads(original))
        require(
            receipt["status"] == "observed_before_commit"
            and receipt["receipt_version"] == "kafka-probe-receipt-v1"
            and receipt["start_offset"] == 0
            and receipt["end_offset"] == 3,
            "unexpected_original_receipt",
        )
        report["original_receipt_sha256"] = hashlib.sha256(original).hexdigest()
        require(progress(experiment) == (0, (0, 3)), "unexpected_initial_offsets")
        admin = AdminClient({"bootstrap.servers": "127.0.0.1:19092", "log_level": 0})
        topics_before = set(admin.list_topics(timeout=10).topics)
        others = {
            name: settings(admin, name)
            for name in sorted(topics_before)
            if name != topic and not name.startswith("__")
        }
        report["other_topic_settings_before"] = others
        report["topic_settings_before"] = settings(admin, topic)
        resource = ConfigResource(
            ResourceType.TOPIC,
            topic,
            incremental_configs=[
                ConfigEntry(k, v, incremental_operation=AlterConfigOpType.SET)
                for k, v in SETTINGS.items()
            ],
        )
        # The only mutation target was freshly created by the child above.
        admin.incremental_alter_configs([resource], request_timeout=10)[
            resource
        ].result(timeout=12)
        live_settings = settings(admin, topic)
        require(
            all(live_settings[k] == v for k, v in SETTINGS.items()),
            "retention_settings_not_applied",
        )
        report["topic_settings_expiring"] = live_settings
        observations: list[dict[str, object]] = []
        report["watermark_observations"] = observations
        deadline = time.monotonic() + 45
        started = time.monotonic()
        while True:
            committed, (low, high) = progress(experiment)
            observations.append(
                {
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "committed_next_offset": committed,
                    "low_offset": low,
                    "high_offset": high,
                }
            )
            require(committed == 0 and high == 3, "unexpected_progress_or_new_records")
            if low == 3:
                break
            require(low == 0 and time.monotonic() < deadline, "expiration_not_observed")
            time.sleep(1)
        refused = child(2, True)
        diagnostic = obj(json.loads(refused.stderr))
        require(
            diagnostic
            == {
                "status": "failed",
                "reason": "retention_gap",
                "required_interval": [0, 3],
                "retained_interval": [3, 3],
                "missing_intervals": [[0, 3]],
            }
            and not refused.stdout,
            "missing_explicit_gap_diagnostic",
        )
        report["recovery_refusal"] = diagnostic
        require(progress(experiment) == (0, (3, 3)), "refusal_changed_offsets")
        require(checkpoint.read_bytes() == original, "original_receipt_changed")
        require(
            not (output / "refused-recovery.json").exists()
            and not (output / "refused-recovery.json.committed.json").exists(),
            "refusal_created_success_artifact",
        )
        require(
            set(admin.list_topics(timeout=10).topics) == topics_before,
            "recovery_created_or_removed_topic",
        )
        require(
            all(settings(admin, name) == values for name, values in others.items()),
            "other_topic_settings_changed",
        )
        report.update(
            {
                "status": "retention_gap_refusal_verified",
                "committed_next_offset": 0,
                "low_offset": 3,
                "high_offset": 3,
                "other_topic_settings_unchanged": True,
                "original_receipt_unchanged": True,
                "success_artifacts_created": False,
            }
        )
    finally:
        with (output / "summary.json").open("x", encoding="utf-8") as summary:
            summary.write(json.dumps(report, indent=2) + "\n")
    return {
        "status": report["status"],
        "missing_interval": [0, 3],
        "committed_next_offset": 0,
        "evidence": str(output / "summary.json"),
    }


def main() -> int:
    """Expect an already running isolated broker; the operator owns its stop."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.job, args.run, args.experiment, args.output)))
    except (
        ValueError,
        OSError,
        KafkaException,
        TimeoutError,
        subprocess.TimeoutExpired,
    ):
        print(json.dumps({"status": "failed", "reason": "retention_check_failed"}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
