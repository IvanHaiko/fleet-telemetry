"""Compare retained source bytes and progress across a graceful or SIGKILL restart."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    TopicCollection,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient
from confluent_kafka.admin._topic import TopicDescription

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.kafka_evidence import (  # noqa: E402
    BrokerQuarantined,
    require_mutable_profile,
)
from telemetry_convert import ConversionError, load_job, verify_job  # noqa: E402
from telemetry_reader import EnvelopeError, read_battery_event  # noqa: E402

CONTAINER = "fleet-kafka-440-probe-kafka-1"
VOLUME = "fleet-kafka-440-probe_kafka-data"
COMPOSE = [
    "docker",
    "compose",
    "-p",
    "fleet-kafka-440-probe",
    "-f",
    str(ROOT / "compose" / "kafka.yml"),
]


class CheckError(ValueError):
    """Safe verification reason without event payloads."""


def require(condition: bool, reason: str) -> None:
    """Keep evidence checks active even in an optimized Python interpreter."""
    if not condition:
        raise CheckError(reason)


def obj(value: object) -> dict[str, object]:
    """Validate a JSON object boundary before inspecting fields."""
    require(isinstance(value, dict), "expected_object")
    result = cast(dict[object, object], value)
    require(all(isinstance(k, str) for k in result), "expected_string_keys")
    return cast(dict[str, object], result)


def text(value: object) -> str:
    """Require a nonempty runtime identity string."""
    if not isinstance(value, str) or not value:
        raise CheckError("expected_identity_string")
    return value


def committed_offset(consumer: Consumer, topic: str) -> int:
    """Bound coordinator recovery without retrying missing or changed progress."""
    deadline = time.monotonic() + 15
    while True:
        remaining = deadline - time.monotonic()
        require(remaining > 0, "coordinator_recovery_deadline")
        try:
            progress = consumer.committed(
                [TopicPartition(topic, 0)], timeout=min(10, remaining)
            )
            break
        except KafkaException as error:
            if (
                not error.args
                or not isinstance(error.args[0], KafkaError)
                or error.args[0].code()
                not in (
                    KafkaError.NOT_COORDINATOR,
                    KafkaError.COORDINATOR_NOT_AVAILABLE,
                    KafkaError.COORDINATOR_LOAD_IN_PROGRESS,
                )
            ):
                raise
            remaining = deadline - time.monotonic()
            require(remaining > 0, "coordinator_recovery_deadline")
            time.sleep(min(0.1, remaining))
    require(
        len(progress) == 1
        and progress[0].error is None
        and progress[0].topic == topic
        and progress[0].partition == 0,
        "committed_progress_lookup_failed",
    )
    return progress[0].offset


def retained_snapshot(
    experiment: str, values: tuple[bytes, ...], keys: tuple[bytes, ...]
) -> dict[str, object]:
    """Read all captured records without committing or republishing anything."""
    topic = f"m2.{experiment}.telemetry.canonical.v1"
    admin = AdminClient({"bootstrap.servers": "127.0.0.1:19092", "log_level": 0})
    metadata = admin.list_topics(timeout=15)
    cluster: object = metadata.cluster_id
    require(len(metadata.brokers) == 1, "unexpected_broker_count")
    require(
        all(
            b.host == "127.0.0.1" and b.port == 19092 for b in metadata.brokers.values()
        ),
        "unexpected_listener",
    )
    description: object = admin.describe_topics(
        TopicCollection([topic]), request_timeout=10
    )[topic].result(timeout=12)
    require(isinstance(description, TopicDescription), "unexpected_topic_metadata")
    description = cast(TopicDescription, description)
    require(
        description.name == topic
        and len(description.partitions) == 1
        and description.partitions[0].id == 0,
        "unexpected_partition_layout",
    )
    consumer = Consumer(
        {
            "bootstrap.servers": "127.0.0.1:19092",
            "group.id": f"m2-{experiment}",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "auto.offset.reset": "error",
            "group.protocol": "classic",
            "socket.timeout.ms": 10000,
            "log_level": 0,
        }
    )

    rows: list[dict[str, object]] = []
    try:
        require(committed_offset(consumer, topic) == 3, "committed_progress_changed")
        require(
            consumer.get_watermark_offsets(TopicPartition(topic, 0), timeout=10)
            == (0, 3),
            "retained_interval_changed",
        )
        # This is read-only inspection of retained bytes, not a group reset.
        consumer.assign([TopicPartition(topic, 0, 0)])
        deadline = time.monotonic() + 15
        while len(rows) < 3:
            require(time.monotonic() < deadline, "read_deadline_exceeded")
            message = consumer.poll(1)
            if message is None:
                continue
            require(message.error() is None, "consumer_record_error")
            index = len(rows)
            require(
                (message.topic(), message.partition(), message.offset())
                == (topic, 0, index),
                "record_position_changed",
            )
            value, key = message.value(), message.key()
            require(
                value == values[index] and key == keys[index], "retained_bytes_differ"
            )
            if value is None or key is None:
                raise CheckError("missing_record_bytes")
            event = read_battery_event(value)
            rows.append(
                {
                    "offset": index,
                    "partition": 0,
                    "event_id": event["event_id"],
                    "key_sha256": hashlib.sha256(key).hexdigest(),
                    "value_sha256": hashlib.sha256(value).hexdigest(),
                }
            )
        require(
            committed_offset(consumer, topic) == 3,
            "inspection_advanced_or_reset_progress",
        )
        require(
            consumer.get_watermark_offsets(TopicPartition(topic, 0), timeout=10)
            == (0, 3),
            "interval_changed_during_inspection",
        )
    finally:
        consumer.close()
    return {
        "cluster_id": text(cluster),
        "topic": topic,
        "topic_id": str(description.topic_id),
        "committed_next_offset": 3,
        "low_offset": 0,
        "high_offset": 3,
        "records": rows,
    }


def check(
    job: Path, run: Path, experiment: str, output: Path, mode: str = "graceful"
) -> dict[str, object]:
    """Refuse the historical local profile before source or runtime access."""
    require_mutable_profile("fleet-kafka-440-probe", "desktop-linux")
    require(
        bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", experiment)),
        "invalid_experiment_id",
    )
    require(mode in ("graceful", "sigkill"), "invalid_restart_mode")
    require(load_job(job).mode == "synthetic", "synthetic_job_required")
    verify_job(job, run)
    with (run / "events.jsonl").open("rb") as source:
        raw = source.read(64 * 1024 * 1024 + 1)
    require(len(raw) <= 64 * 1024 * 1024, "event_file_bound_exceeded")
    values = tuple(raw.splitlines())
    require(len(values) == 3, "three_event_fixture_required")
    events = [read_battery_event(value) for value in values]
    require(
        all(e["source_type"] == "synthetic" for e in events), "synthetic_input_required"
    )
    keys = tuple(e["vehicle_id"].encode() for e in events)
    require(
        not output.exists() and output.parent.is_dir(), "new_output_directory_required"
    )
    commands: list[dict[str, object]] = []

    def command(arguments: list[str]) -> str:
        result = subprocess.run(
            arguments, cwd=ROOT, text=True, capture_output=True, timeout=45, check=False
        )
        row: dict[str, object] = {
            "command": arguments,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        commands.append(row)
        if output.is_dir():
            with (output / "commands.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(row) + "\n")
        require(result.returncode == 0, "external_command_failed")
        return result.stdout.strip()

    def container() -> dict[str, object]:
        decoded: object = json.loads(command(["docker", "inspect", CONTAINER]))
        require(
            isinstance(decoded, list) and len(decoded) == 1,
            "unexpected_container_result",
        )
        info = obj(cast(list[object], decoded)[0])
        config = obj(info["Config"])
        labels = obj(config["Labels"])
        require(
            labels.get("com.docker.compose.project") == "fleet-kafka-440-probe"
            and labels.get("com.docker.compose.service") == "kafka",
            "unexpected_container_owner",
        )
        mounts = info["Mounts"]
        require(isinstance(mounts, list), "missing_container_mounts")
        data = [
            obj(v)
            for v in cast(list[object], mounts)
            if obj(v).get("Destination") == "/var/lib/kafka/data"
        ]
        require(
            len(data) == 1
            and data[0].get("Type") == "volume"
            and data[0].get("Name") == VOLUME,
            "unexpected_data_volume",
        )
        state = obj(info["State"])
        require(
            isinstance(state["ExitCode"], int)
            and not isinstance(state["ExitCode"], bool)
            and isinstance(state["OOMKilled"], bool),
            "unexpected_exit_state",
        )
        return {
            "id": text(info["Id"]),
            "image": text(info["Image"]),
            "state": text(state["Status"]),
            "started_at": text(state["StartedAt"]),
            "volume": VOLUME,
            "exit_code": state["ExitCode"],
            "oom_killed": state["OOMKilled"],
        }

    require(
        command(["docker", "context", "show"]) == "desktop-linux",
        "unexpected_docker_context",
    )
    initial = container()
    require(initial["state"] == "exited", "experiment_broker_must_start_stopped")
    output.mkdir()
    report: dict[str, object] = {
        "status": "incomplete",
        "experiment_id": experiment,
        "restart_mode": (
            "sigkill-compose-kill-start"
            if mode == "sigkill"
            else "graceful-compose-restart"
        ),
        "initial_container": initial,
        "source_events_sha256": hashlib.sha256(raw).hexdigest(),
        "commands": commands,
    }
    verified, stopped = False, False
    try:
        command([*COMPOSE, "start", "kafka"])
        ready = AdminClient({"bootstrap.servers": "127.0.0.1:19092", "log_level": 0})
        require(len(ready.list_topics(timeout=15).brokers) == 1, "broker_not_ready")
        require(
            command(
                [*COMPOSE, "exec", "-T", "kafka", "bin/kafka-topics.sh", "--version"]
            )
            == "4.4.0",
            "unexpected_broker_version",
        )
        command(
            [
                sys.executable,
                str(ROOT / "scripts/kafka-probe.py"),
                "--job",
                str(job),
                "--run",
                str(run),
                "--experiment",
                experiment,
                "--receipt",
                str(output / "admission.json"),
            ]
        )
        before = retained_snapshot(experiment, values, keys)
        before_container = container()
        report.update({"before": before, "before_container": before_container})
        with (output / "before.json").open("x", encoding="utf-8") as checkpoint:
            checkpoint.write(json.dumps(before, indent=2) + "\n")
        if mode == "sigkill":
            require(
                command([*COMPOSE, "exec", "-T", "kafka", "cat", "/proc/1/comm"])
                == "java",
                "broker_jvm_not_pid_one",
            )
            report["pid1_comm"] = "java"
            command([*COMPOSE, "kill", "--signal", "SIGKILL", "kafka"])
            crashed = container()
            report["crashed_container"] = crashed
            with (output / "crashed.json").open("x", encoding="utf-8") as checkpoint:
                checkpoint.write(json.dumps(crashed, indent=2) + "\n")
            require(
                crashed["state"] == "exited"
                and crashed["exit_code"] == 137
                and crashed["oom_killed"] is False,
                "sigkill_exit_not_confirmed",
            )
            require(
                all(
                    crashed[k] == before_container[k] for k in ("id", "image", "volume")
                )
                and crashed["started_at"] == before_container["started_at"],
                "crash_changed_container_identity",
            )
            command([*COMPOSE, "start", "kafka"])
        else:
            command([*COMPOSE, "restart", "--timeout", "30", "kafka"])
        after = retained_snapshot(experiment, values, keys)
        after_container = container()
        report.update({"after": after, "after_container": after_container})
        with (output / "after.json").open("x", encoding="utf-8") as checkpoint:
            checkpoint.write(json.dumps(after, indent=2) + "\n")
        require(before == after, "restart_changed_records_identity_or_offsets")
        require(
            before_container["state"] == after_container["state"] == "running",
            "broker_not_running_at_comparison",
        )
        require(
            all(
                initial[k] == before_container[k] == after_container[k]
                for k in ("id", "image", "volume")
            ),
            "container_image_or_volume_changed",
        )
        require(
            before_container["started_at"] != after_container["started_at"],
            "broker_process_not_restarted",
        )
        verified = True
    finally:
        try:
            command([*COMPOSE, "stop", "kafka"])
            final = container()
            require(final["state"] == "exited", "broker_not_stopped")
            require(
                command(
                    ["docker", "volume", "inspect", VOLUME, "--format", "{{.Name}}"]
                )
                == VOLUME,
                "data_volume_missing",
            )
            report["final_container"] = final
            stopped = True
        finally:
            success = (
                "retained_records_sigkill_verified"
                if mode == "sigkill"
                else "retained_records_restart_verified"
            )
            report["status"] = success if verified and stopped else "incomplete"
            report["volume_preserved"] = stopped
            with (output / "summary.json").open("x", encoding="utf-8") as summary:
                summary.write(json.dumps(report, indent=2) + "\n")
    return {
        "status": report["status"],
        "records": 3,
        "committed_next_offset": 3,
        "broker": "stopped",
        "volume": "preserved",
        "evidence": str(output / "summary.json"),
    }


def main() -> int:
    """Run one real broker restart, preserving prior artifacts and the volume."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("graceful", "sigkill"), default="graceful")
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                check(args.job, args.run, args.experiment, args.output, args.mode)
            )
        )
    except (BrokerQuarantined, CheckError, ConversionError, EnvelopeError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}), file=sys.stderr)
        return 2
    except (OSError, KafkaException, subprocess.TimeoutExpired):
        print(
            json.dumps({"status": "failed", "reason": "runtime_or_inspection_failure"}),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
