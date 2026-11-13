"""Start one local Kafka/Flink core and reconcile its synthetic battery example."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from telemetry.conversion_contract import json_object, object_value  # noqa: E402
from telemetry_convert import convert_job  # noqa: E402
from telemetry_reader import read_battery_event  # noqa: E402

COMPOSE = [
    "docker",
    "compose",
    "-f",
    str(ROOT / "compose.yaml"),
    "-p",
    "fleet-telemetry-local",
]
JOB = "local-battery-projection-v1"


def command(args: list[str], *, body: bytes | None = None, timeout: int = 120) -> bytes:
    """Run only the selected local project's command; surface failed exits."""
    result = subprocess.run(
        args,
        cwd=ROOT,
        input=body,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-4000:])
    return result.stdout


def local_context() -> None:
    endpoint = (
        command(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"]
        )
        .decode()
        .strip()
    )
    if not (
        endpoint.startswith("npipe:////./pipe/") or endpoint.startswith("unix:///")
    ):
        raise ValueError("Select a local Docker Desktop/default context first.")


def jobs() -> list[dict[str, object]]:
    with urllib.request.urlopen(
        "http://127.0.0.1:8081/jobs/overview", timeout=5
    ) as response:
        document = json_object(response.read(1024 * 1024))
    value = document.get("jobs")
    if not isinstance(value, list):
        raise ValueError("Invalid Flink jobs response")
    return [object_value(row) for row in value]


def ensure_job() -> None:
    selected = [
        row
        for row in jobs()
        if row.get("name") == JOB and row.get("state") == "RUNNING"
    ]
    if len(selected) > 1:
        raise ValueError(
            "Multiple demo jobs are running; cancel extras in the Flink UI."
        )
    if selected:
        return
    print("Submitting the battery SQL job...", flush=True)
    command([*COMPOSE, "--profile", "jobs", "run", "--rm", "submit"], timeout=120)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        selected = [row for row in jobs() if row.get("name") == JOB]
        if any(row.get("state") == "RUNNING" for row in selected):
            return
        if selected and all(row.get("state") == "FAILED" for row in selected):
            raise ValueError("The battery job failed; inspect the Flink UI.")
        time.sleep(1)
    raise ValueError("The battery job did not become RUNNING within 120 seconds.")


def verify_projection(
    inputs: list[bytes], outputs: list[dict[str, object]], run_id: str
) -> int:
    """Check this delivery run's complete content; old results cannot pass it."""
    expected = {read_battery_event(raw)["event_id"]: raw for raw in inputs}
    seen: set[str] = set()
    for row in outputs:
        if row.get("dataset_run_id") != run_id:
            continue
        identity = row.get("event_id")
        if not isinstance(identity, str) or identity not in expected:
            raise ValueError("Unexpected measurement in the current demo run")
        raw = expected[identity]
        event = read_battery_event(raw)
        payload = event["payload"]
        current = payload["current_a"]
        power = None if current is None else payload["voltage_v"] * current
        wanted = {
            "profile": JOB,
            "dataset_run_id": run_id,
            "event_id": identity,
            "vehicle_id": event["vehicle_id"],
            "source_timestamp": event["source_timestamp"],
            **payload,
            "raw_event": raw.decode(),
        }
        if any(row.get(k) != value for k, value in wanted.items()):
            raise ValueError("Flink changed measurement content or source time")
        for field in ("voltage_v", "current_a", "remaining_fraction"):
            value = row.get(field)
            if value is not None and type(value) not in (int, float):
                raise ValueError("A numeric measurement has the wrong JSON type")
        actual = row.get("power_w")
        if power is None:
            if actual is not None:
                raise ValueError("Unknown current must produce unknown power")
        elif type(actual) not in (int, float) or not math.isclose(
            float(str(actual)), power, rel_tol=1e-12
        ):
            raise ValueError("Incorrect battery power")
        partition, offset = row.get("source_partition"), row.get("source_offset")
        if (
            type(partition) is not int
            or not 0 <= partition < 12
            or type(offset) is not int
            or offset < 0
        ):
            raise ValueError("Missing Kafka source coordinates")
        seen.add(identity)
    if seen != set(expected):
        raise ValueError(
            f"Expected {len(expected)} current-run measurements, received {len(seen)}"
        )
    return len(seen)


def demo() -> None:
    ensure_job()
    evidence = ROOT / ".local-discovery"
    evidence.mkdir(exist_ok=True)
    parent = Path(tempfile.mkdtemp(prefix="local-demo-", dir=evidence))
    run_id = "local-demo-" + uuid.uuid4().hex[:12]
    fixture = ROOT / "tests/fixtures/synthetic-conversion-job.json"
    job = json_object(fixture.read_bytes())
    object_value(job["input"])["path"] = str(
        fixture.with_name("synthetic-battery-v1.json")
    )
    object_value(job["delivery"])["dataset_run_id"] = run_id
    path = parent / "job.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    result = convert_job(path, parent / run_id)
    inputs = (result.output_directory / "events.jsonl").read_bytes().splitlines()
    print("Publishing three canonical synthetic measurements...", flush=True)
    command(
        [
            *COMPOSE,
            "exec",
            "-T",
            "kafka",
            "/opt/kafka/bin/kafka-console-producer.sh",
            "--bootstrap-server",
            "kafka:9092",
            "--topic",
            "telemetry.battery.input",
            "--producer-property",
            "acks=all",
        ],
        body=b"\n".join(inputs) + b"\n",
    )
    print("Waiting for Flink output and checking this delivery run...", flush=True)
    read = subprocess.run(
        [
            *COMPOSE,
            "exec",
            "-T",
            "kafka",
            "/opt/kafka/bin/kafka-console-consumer.sh",
            "--bootstrap-server",
            "kafka:9092",
            "--topic",
            "telemetry.battery.output",
            "--from-beginning",
            "--max-messages",
            "4096",
            "--timeout-ms",
            "30000",
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=60,
        check=False,
    )
    (parent / "consumer-stderr.txt").write_bytes(read.stderr)
    (parent / "output.jsonl").write_bytes(read.stdout)
    # The console consumer exits nonzero on its idle timeout. Only complete
    # current-run content reconciliation can establish successful processing.
    if len(read.stdout) > 16 * 1024 * 1024:
        raise ValueError("Demo readback exceeds its 16-MiB limit")
    rows = [json_object(line) for line in read.stdout.splitlines()]
    count = verify_projection(inputs, rows, run_id)
    print(
        json.dumps(
            {
                "status": "verified",
                "measurements": count,
                "run_id": run_id,
                "evidence": str(parent.relative_to(ROOT)),
            }
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "demo", "status", "stop"))
    args = parser.parse_args()
    try:
        local_context()
        if args.action == "start":
            print(
                "Starting one Kafka broker and the Flink session cluster...", flush=True
            )
            subprocess.run(
                [*COMPOSE, "up", "-d", "--build", "--wait", "--wait-timeout", "180"],
                cwd=ROOT,
                check=True,
            )
            print(
                "Ready. Flink: http://127.0.0.1:8081; "
                "next: python scripts/local.py demo"
            )
        elif args.action == "demo":
            demo()
        elif args.action == "status":
            print(command([*COMPOSE, "ps"]).decode())
            print(json.dumps(jobs(), indent=2))
        else:
            print(command([*COMPOSE, "stop"]).decode())
            print("Stopped. Kafka data and checkpoint volumes are retained.")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
