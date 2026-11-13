"""Exercise real process exit windows on the existing three-event Kafka probe."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

from confluent_kafka import Consumer, KafkaException, TopicPartition

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "scripts/kafka-probe.py"


def require(condition: bool, reason: str) -> None:
    """Keep acceptance checks enabled with an optimized interpreter."""
    if not condition:
        raise ValueError(reason)


def obj(data: str) -> dict[str, object]:
    """Check JSON command output before reading its fields."""
    value: object = json.loads(data)
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError("unexpected_command_output")
    return cast(dict[str, object], value)


def broker_progress(experiment: str) -> tuple[int, tuple[int, int]]:
    """Inspect broker state independently from the crashed child process."""
    topic = f"m2.{experiment}.telemetry.canonical.v1"
    consumer = Consumer(
        {
            "bootstrap.servers": "127.0.0.1:19092",
            "group.id": f"m2-{experiment}",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "auto.offset.reset": "error",
            "group.protocol": "classic",
            "socket.timeout.ms": 10000,
        }
    )
    try:
        progress = consumer.committed([TopicPartition(topic, 0)], timeout=10)
        if len(progress) != 1 or progress[0].error is not None:
            raise ValueError("broker_progress_lookup_failed")
        return progress[0].offset, consumer.get_watermark_offsets(
            TopicPartition(topic, 0), timeout=10
        )
    finally:
        consumer.close()


def check(job: Path, run: Path, prefix: str, output: Path) -> dict[str, object]:
    """Preserve isolated topics/receipts and report only demonstrated outcomes."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", prefix):
        raise ValueError("invalid_experiment_prefix")
    output.mkdir()
    commands: list[dict[str, object]] = []

    def child(
        experiment: str, receipt: Path, expected: int, extra: tuple[str, ...] = ()
    ) -> dict[str, object]:
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
            str(receipt),
            *extra,
        ]
        result = subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, timeout=60, check=False
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
        if result.returncode != expected:
            raise ValueError("unexpected_child_exit")
        return obj(result.stdout) if expected == 0 else {}

    clean_id = prefix + "-clean"
    clean = child(clean_id, output / "clean.json", 0)
    require(
        clean["status"] == "admission_and_clean_consumer_reopen_verified",
        "recovery_acceptance_failed",
    )
    require(broker_progress(clean_id) == (3, (0, 3)), "recovery_acceptance_failed")
    windows: list[dict[str, object]] = []
    for window, exit_code, committed_before, replayed in (
        ("before-commit", 86, 0, 3),
        ("after-commit", 87, 3, 0),
    ):
        experiment = prefix + "-" + window
        original = output / f"{window}.json"
        child(experiment, original, exit_code, ("--crash-at", window))
        require(
            not original.with_name(original.name + ".committed.json").exists(),
            "recovery_acceptance_failed",
        )
        require(
            broker_progress(experiment) == (committed_before, (0, 3)),
            "recovery_acceptance_failed",
        )
        saved = original.read_bytes()
        if window == "before-commit":
            needle = b'"end_offset": 3'
            require(saved.count(needle) == 1, "recovery_acceptance_failed")
            for name, corrupt in (
                ("truncated", saved[: len(saved) // 2]),
                ("wrong-end", saved.replace(needle, b'"end_offset": 2', 1)),
            ):
                damaged = output / f"{name}.json"
                damaged.write_bytes(corrupt)
                rejected = output / f"{name}-output.json"
                child(experiment, rejected, 2, ("--resume-receipt", str(damaged)))
                require(not rejected.exists(), "recovery_acceptance_failed")
                require(
                    broker_progress(experiment) == (0, (0, 3)),
                    "recovery_acceptance_failed",
                )
                require(damaged.read_bytes() == corrupt, "recovery_acceptance_failed")
                require(
                    obj(str(commands[-1]["stderr"]))
                    == {
                        "status": "failed",
                        "reason": "receipt_context_or_bytes_differ",
                    },
                    "recovery_acceptance_failed",
                )
        recovery = output / f"{window}-recovery.json"
        result = child(experiment, recovery, 0, ("--resume-receipt", str(original)))
        require(
            result["status"] == "consumer_receipt_recovery_verified",
            "recovery_acceptance_failed",
        )
        require(
            result["replayed_observations"] == replayed, "recovery_acceptance_failed"
        )
        require(
            result["unique_events"] == result["committed_next_offset"] == 3,
            "recovery_acceptance_failed",
        )
        require(
            broker_progress(experiment) == (3, (0, 3)), "recovery_acceptance_failed"
        )
        require(original.read_bytes() == saved, "recovery_acceptance_failed")
        final = obj(recovery.with_name(recovery.name + ".committed.json").read_text())
        require(
            final["resume_from_offset"] == committed_before,
            "recovery_acceptance_failed",
        )
        require(
            final["replayed_observations"] == replayed, "recovery_acceptance_failed"
        )
        require(
            len(cast(list[object], final["observed_this_attempt"])) == replayed,
            "recovery_acceptance_failed",
        )
        windows.append(
            {
                "window": window,
                "process_exit": exit_code,
                "committed_after_crash": committed_before,
                "replayed_observations": replayed,
                "unique_events": 3,
                "committed_after_recovery": 3,
                "retained_interval": [0, 3],
                "original_receipt_sha256": hashlib.sha256(saved).hexdigest(),
            }
        )
    report: dict[str, object] = {
        "status": "consumer_interruption_windows_verified",
        "windows": windows,
        "rejected_receipts": 2,
        "clean_admission_regression": "passed",
        "commands": commands,
        "limits": [
            "Single manually assigned partition and exclusive local operator",
            "No host/power-loss, rebalance or concurrent-consumer proof",
            "Retained [0,3) interval required; no retention mutation performed",
        ],
    }
    (output / "summary.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "status": report["status"],
        "windows": windows,
        "rejected_receipts": 2,
        "evidence": str(output / "summary.json"),
    }


def main() -> int:
    """Run only against the explicitly started local M2 broker."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.job, args.run, args.prefix, args.output)))
    except (ValueError, OSError, KafkaException, subprocess.TimeoutExpired):
        print(
            json.dumps({"status": "failed", "reason": "recovery_check_failed"}),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
