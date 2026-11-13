"""Run the complete bounded local synthetic M2 verification matrix."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kafka_evidence import BrokerQuarantined, require_mutable_profile  # noqa: E402

from telemetry_metrics import read_metrics  # noqa: E402

COMPOSE = [
    "docker",
    "compose",
    "-p",
    "fleet-kafka-440-probe",
    "-f",
    str(ROOT / "compose" / "kafka.yml"),
]
CONTAINER = "fleet-kafka-440-probe-kafka-1"
VOLUME = "fleet-kafka-440-probe_kafka-data"


def require(condition: bool, reason: str) -> None:
    """Fail explicitly, including under optimized Python."""
    if not condition:
        raise ValueError(reason)


def obj(value: object) -> dict[str, object]:
    """Validate decoded JSON before inspecting ownership or state."""
    require(isinstance(value, dict), "expected_object")
    value = cast(dict[object, object], value)
    require(all(isinstance(k, str) for k in value), "expected_string_keys")
    return cast(dict[str, object], value)


def verify_metrics(
    output: Path, commands: list[dict[str, object]]
) -> dict[str, object]:
    """Check runtime snapshots against the actual failure/commit windows."""

    def captures(path: Path) -> list[dict[str, object]]:
        return [
            obj(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
        ]

    def selected(stderr: object, operation: str, event: str) -> list[dict[str, object]]:
        require(isinstance(stderr, str), "missing_stderr")
        return [
            obj(r["values"])
            for r in read_metrics(cast(str, stderr))
            if r["operation"] == operation and r["event"] == event
        ]

    producer = captures(output / "producer/commands.jsonl")
    for index, operation in enumerate(("producer_initial", "producer_retry")):
        final = selected(producer[index]["stderr"], operation, "completed")
        require(
            len(final) == 1
            and all(
                final[0].get(k) == v
                for k, v in {
                    "attempted_records": 3,
                    "enqueued_records": 3,
                    "acknowledged_records": 3,
                    "callback_errors": 0,
                    "pending_records": 0,
                }.items()
            ),
            "producer_metrics_differs",
        )
        callbacks = selected(producer[index]["stderr"], operation, "callback")
        require(
            [v.get("acknowledged_records") for v in callbacks] == [1, 2, 3],
            "callback_metrics_differs",
        )
    all_metrics = [
        r for row in commands for r in read_metrics(cast(str, row["stderr"]))
    ]
    for operation, queued, unqueued in (
        ("producer_unavailable", 3, 0),
        ("producer_queue_pressure", 1, 2),
    ):
        failed = [
            obj(r["values"])
            for r in all_metrics
            if r["operation"] == operation and r["event"] == "failed"
        ]
        require(
            len(failed) == 1
            and all(
                failed[0].get(k) == v
                for k, v in {
                    "attempted_records": 3,
                    "enqueued_records": queued,
                    "unqueued_records": unqueued,
                    "acknowledged_records": 0,
                    "callback_errors": queued,
                    "pending_records": 0,
                }.items()
            ),
            "failure_metrics_differs",
        )
    recovery = captures(output / "recovery/commands.jsonl")
    completed_replays: list[object] = []
    crash_windows: list[int] = []
    for row in recovery:
        persisted = selected(row["stderr"], "consumer", "receipt_persisted")
        commits = selected(row["stderr"], "consumer", "commit_confirmed")
        if row["exit_code"] in (86, 87):
            require(
                len(persisted) == 1 and persisted[0].get("captured_lag_records") == 3,
                "precommit_metric_differs",
            )
            acknowledged_end = any(v.get("committed_next_offset") == 3 for v in commits)
            require(
                acknowledged_end == (row["exit_code"] == 87),
                "commit_metric_window_differs",
            )
            crash_windows.append(cast(int, row["exit_code"]))
        if row["exit_code"] == 0:
            completed = selected(row["stderr"], "consumer", "completed")
            require(
                len(completed) == 1
                and completed[0].get("committed_next_offset") == 3
                and completed[0].get("captured_lag_records") == 0
                and cast(float, completed[0].get("duration_seconds", 0)) > 0,
                "completed_consumer_metrics_differs",
            )
            completed_replays.append(completed[0]["replayed_observations"])
    require(
        crash_windows == [86, 87] and completed_replays == [0, 3, 0],
        "recovery_metrics_coverage_differs",
    )
    return {
        "status": "runtime_metrics_verified",
        "producer_attempts": 2,
        "failure_profiles": 2,
        "consumer_crash_windows": crash_windows,
        "consumer_completed_replays": completed_replays,
    }


def check(
    job: Path,
    run: Path,
    prefix: str,
    output: Path,
    docker_context: str = "desktop-linux",
) -> dict[str, object]:
    """Refuse the historical Desktop broker before any runtime operation."""
    require_mutable_profile("fleet-kafka-440-probe", docker_context)
    require(bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", prefix)), "invalid_prefix")
    require(not output.exists() and output.parent.is_dir(), "fresh_output_required")
    commands: list[dict[str, object]] = []
    env = dict(os.environ)
    env["UV_CACHE_DIR"] = str(ROOT / ".uv-cache")
    env["TEMP"] = env["TMP"] = str(ROOT / ".local-discovery/kafka-install-temp")
    env["UV_LINK_MODE"] = "copy"
    require(Path(env["TEMP"]).is_dir(), "existing_workspace_temp_required")

    def command(args: list[str], timeout: int = 120) -> str:
        result = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        row = {
            "command": args,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        commands.append(row)
        if output.is_dir():
            with (output / "commands.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(row) + "\n")
        print(
            json.dumps(
                {
                    "step": Path(args[0]).name,
                    "exit_code": result.returncode,
                    "command": args,
                }
            ),
            flush=True,
        )
        require(result.returncode == 0, "suite_command_failed")
        return result.stdout.strip()

    def container() -> dict[str, object]:
        raw: object = json.loads(command(["docker", "inspect", CONTAINER]))
        require(isinstance(raw, list) and len(raw) == 1, "unexpected_container")
        info = obj(cast(list[object], raw)[0])
        labels = obj(obj(info["Config"])["Labels"])
        require(
            labels.get("com.docker.compose.project") == "fleet-kafka-440-probe"
            and labels.get("com.docker.compose.service") == "kafka",
            "wrong_owner",
        )
        mounts = info["Mounts"]
        require(isinstance(mounts, list), "missing_mounts")
        matching = [
            obj(m)
            for m in cast(list[object], mounts)
            if obj(m).get("Destination") == "/var/lib/kafka/data"
        ]
        require(
            len(matching) == 1
            and matching[0].get("Name") == VOLUME
            and matching[0].get("Type") == "volume",
            "wrong_volume",
        )
        return {
            "id": info["Id"],
            "image": info["Image"],
            "state": obj(info["State"]),
            "volume": VOLUME,
        }

    require(
        docker_context in {"desktop-linux", "default"} and not env.get("DOCKER_HOST"),
        "local_context_required",
    )
    require(command(["docker", "context", "show"]) == docker_context, "wrong_context")
    if docker_context == "default":
        require(
            os.name == "posix"
            and command(
                [
                    "docker",
                    "context",
                    "inspect",
                    "default",
                    "--format",
                    "{{.Endpoints.docker.Host}}",
                ]
            )
            == "unix:///var/run/docker.sock",
            "local_linux_engine_required",
        )
    initial = container()
    require(obj(initial["state"])["Status"] == "exited", "broker_must_start_stopped")
    output.mkdir()
    with (output / "commands.jsonl").open("x", encoding="utf-8") as log:
        for row in commands:
            log.write(json.dumps(row) + "\n")
    report: dict[str, object] = {
        "status": "incomplete",
        "initial_container": initial,
        "commands": commands,
        "prefix": prefix,
    }
    verified = False

    def integration(script: str, arguments: list[str], optimized: bool = False) -> None:
        command(
            [
                sys.executable,
                *(["-O"] if optimized else []),
                str(ROOT / "scripts" / script),
                "--job",
                str(job),
                "--run",
                str(run),
                *arguments,
            ],
            timeout=180,
        )

    try:
        for profile in ("synthetic", "ulog"):
            command(
                [
                    sys.executable,
                    str(ROOT / "scripts/check-m1.py"),
                    "--profile",
                    profile,
                    "--offline",
                ],
                timeout=180,
            )
        files = [
            str(p.relative_to(ROOT)) for p in sorted((ROOT / "scripts").glob("*.py"))
        ]
        for task in (["ruff", "check"], ["ruff", "format", "--check"], ["mypy"]):
            command([sys.executable, "-m", *task, *files])
        command(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(output / "pytest-kafka"),
                str(ROOT / "tests/test_kafka_creation.py"),
                str(ROOT / "tests/test_kafka_restart_readiness.py"),
                str(ROOT / "tests/test_kafka_topic_policy.py"),
            ]
        )
        command(["docker", "version", "--format", "{{json .}}"])
        command(["docker", "compose", "version"])
        command([*COMPOSE, "start", "kafka"])
        require(
            command(
                [*COMPOSE, "exec", "-T", "kafka", "cat", "config/probe.properties"]
            ).splitlines()
            == (ROOT / "runtime/kafka/kafka-probe.properties").read_text().splitlines(),
            "runtime_config_differs",
        )
        report["resource_snapshot"] = command(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", CONTAINER]
        )
        integration(
            "check-kafka-producer.py",
            ["--prefix", prefix + "-producer", "--output", str(output / "producer")],
        )
        integration(
            "check-kafka-recovery.py",
            ["--prefix", prefix + "-recovery", "--output", str(output / "recovery")],
            optimized=True,
        )
        integration(
            "check-kafka-retention.py",
            [
                "--experiment",
                "retention-" + prefix,
                "--output",
                str(output / "retention"),
            ],
        )
        command([*COMPOSE, "stop", "kafka"])
        for mode in ("graceful", "sigkill"):
            integration(
                "check-kafka-restart.py",
                [
                    "--experiment",
                    prefix + "-" + mode,
                    "--output",
                    str(output / mode),
                    "--mode",
                    mode,
                ],
            )
        report["runtime_metrics"] = verify_metrics(output, commands)
        producer = obj(json.loads((output / "producer/summary.json").read_bytes()))
        audit_args = [
            sys.executable,
            "-S",
            str(ROOT / "telemetry_publication.py"),
            "--job",
            str(job),
            "--run",
            str(run),
            "--commands",
            str(output / "producer/commands.jsonl"),
            "--retry-receipt",
            str(output / "producer/retry-receipt.json"),
            "--observations",
            str(output / "producer/observations.json"),
            "--prefix",
            prefix + "-producer",
            "--cluster-id",
            str(producer["cluster_id"]),
            "--topic-id",
            str(producer["topic_id"]),
        ]
        manifest = command(audit_args)
        publication_path = output / "publication.json"
        with publication_path.open("xb") as artifact:
            artifact.write((manifest + "\n").encode())
        command([*audit_args, "--verify-manifest", str(publication_path)])
        report["publication_manifest"] = "publication.json"
        verified = True
    finally:
        try:
            command([*COMPOSE, "stop", "kafka"])
            final = container()
            require(obj(final["state"])["Status"] == "exited", "broker_not_stopped")
            require(
                all(initial[k] == final[k] for k in ("id", "image", "volume")),
                "runtime_identity_changed",
            )
            require(
                command(
                    ["docker", "volume", "inspect", VOLUME, "--format", "{{.Name}}"]
                )
                == VOLUME,
                "volume_missing",
            )
            report["final_container"] = final
            report["status"] = (
                "local_synthetic_matrix_verified" if verified else "incomplete"
            )
            report["volume_preserved"] = True
        finally:
            with (output / "summary.json").open("x", encoding="utf-8") as summary:
                summary.write(json.dumps(report, indent=2) + "\n")
    return {
        "status": report["status"],
        "broker": "stopped",
        "volume": "preserved",
        "evidence": str(output / "summary.json"),
    }


def main() -> int:
    """Run the local matrix without publication or external source adoption."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--docker-context",
        choices=("desktop-linux", "default"),
        default="desktop-linux",
    )
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                check(args.job, args.run, args.prefix, args.output, args.docker_context)
            )
        )
    except BrokerQuarantined as error:
        print(json.dumps({"status": "failed", "reason": str(error)}), file=sys.stderr)
        return 2
    except (ValueError, OSError, subprocess.TimeoutExpired):
        print(
            json.dumps({"status": "failed", "reason": "m2_suite_failed"}),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
