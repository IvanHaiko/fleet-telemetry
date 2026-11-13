# ruff: noqa: E402
"""One failed checkpoint, repaired checkpoint, and restored backlog on a fresh job."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
from typing import cast
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from m3_transport import Transport
from m3_transport_types import Record

from scripts.slice_queries import require
from telemetry.archive_documents import canonical, digest
from telemetry_reference import (
    EndOfInput,
    Observation,
    ReferenceScope,
    calculate_windows,
)

DOCKER = shutil.which("docker.exe") or shutil.which("docker") or "docker"
PYTHON = (
    "/home/ivan/.local/share/fleet-telemetry/pyflink/"
    "m3-compatibility-002/venv/bin/python"
)
type Row = dict[str, object]


def command(args: list[str], data: str | None = None) -> str:
    result = subprocess.run(
        [DOCKER, *args], input=data, capture_output=True, text=True, timeout=30
    )
    require(result.returncode == 0, "docker_command_failed")
    return result.stdout


def rest(path: str, body: object | None = None) -> Row:
    request = Request(
        "http://127.0.0.1:18081" + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        wire = response.read(1_048_577)
    require(len(wire) <= 1_048_576, "rest_limit")
    return cast(Row, json.loads(wire))


def wait(probe: Callable[[], object], seconds: int = 90) -> object:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = probe()
        if value:
            return value
        time.sleep(0.2)
    raise TimeoutError("m5_checkpoint_deadline")


def run(project: str, source: Path, evidence: Path) -> None:
    require(re.fullmatch(r"fleet-m3-final-[0-9]{3}", project), "project_scope")
    tag = evidence.name.rsplit("-", 1)[-1]
    require(re.fullmatch(r"[0-9]{3}", tag), "case_tag")
    evidence.mkdir(exist_ok=False)
    values = (source / "demo-m5-idle-001/events.jsonl").read_bytes().splitlines()[:4]
    require(len(values) == 4, "fixture_count")
    events = [cast(Row, json.loads(value)) for value in values]
    scope = ReferenceScope(
        "demo-m5-idle-001",
        "m5-checkpoint-v1",
        cast(str, events[0]["source_log_id"]),
        "2026-01-01T12:00:00.000000Z",
        "2026-01-01T12:10:22.000000Z",
    )
    topic = f"m2.m3-final-m5-checkpoint-{project}-{tag}.telemetry.canonical.v1"
    group = "m5-checkpoint-" + project + "-" + tag
    operations: list[object] = []
    kafka = Transport(
        lambda kind, data: operations.append({"kind": kind, "data": data})
    )
    identity = kafka.create(topic, 1)
    records = [
        Record(0, index, index, value, str(events[index]["vehicle_id"]).encode())
        for index, value in enumerate(values)
    ]
    for record in records[:2]:
        kafka.send(topic, record)
    manifest = {
        "profile": "m3-persistent-input-v1",
        "topic": topic,
        "bootstrap": "kafka:9092",
        "group": group,
        "end": 4,
        "scope": asdict(scope),
    }
    command(
        [
            "exec",
            "-i",
            project + "-jobmanager-1",
            "sh",
            "-c",
            "cat > /state/m5-checkpoint-input-" + tag + ".json",
        ],
        json.dumps(manifest),
    )
    control = "/state/m5-checkpoint-control-" + tag
    checkpoint_root = "/state/m5-checkpoint-storage-" + tag

    def receipt(pattern: str) -> list[Row]:
        raw = command(
            [
                "exec",
                project + "-jobmanager-1",
                PYTHON,
                "-c",
                "import pathlib,json,sys; p=pathlib.Path(sys.argv[1]); "
                "rows=[json.loads(f.read_text()) for f in p.glob(sys.argv[2])]; "
                "print(json.dumps(rows))",
                control,
                pattern,
            ]
        )
        return cast(list[Row], json.loads(raw))

    argv = [
        DOCKER,
        "exec",
        project + "-jobmanager-1",
        "/opt/m3/entrypoint.sh",
        "submit",
        "-py",
        "/workspace/runtime/pyflink/persistent_job.py",
        "--manifest",
        "/state/m5-checkpoint-input-" + tag + ".json",
        "--control",
        control,
        "--checkpoints",
        checkpoint_root,
        "--run-tag",
        "initial",
        "--identity-limit",
        "128",
    ]
    with (
        (evidence / "flink.stdout").open("xb") as out,
        (evidence / "flink.stderr").open("xb") as err,
    ):
        child = subprocess.Popen(argv, stdout=out, stderr=err)
        try:
            ready = cast(list[Row], wait(lambda: receipt("ready-initial.json")))[0]
            job = cast(str, ready["job_id"])
            prefix = cast(
                list[Row], wait(lambda: receipt("observation-initial-*-1.json"))
            )[-1]
            require(len(cast(list[str], prefix["history_ids"])) == 2, "prefix_state")
            # Only this job's new checkpoint directory is changed. No data is deleted.
            permission_script = (
                "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
                "assert p.resolve()==p and p.parent==pathlib.Path('/state') "
                "and p.name.startswith('m5-checkpoint-storage-'); "
                "ds=[x for x in p.rglob('*') if x.is_dir()]+[p]; "
                "assert all(not x.is_symlink() for x in ds); "
                "[x.chmod(int(sys.argv[2],8)) for x in ds]"
            )
            command(
                [
                    "exec",
                    project + "-jobmanager-1",
                    PYTHON,
                    "-c",
                    permission_script,
                    checkpoint_root,
                    "555",
                ]
            )
            try:
                trigger = rest("/jobs/" + job + "/checkpoints", {})
                failed = cast(
                    Row,
                    wait(
                        lambda: cast(
                            Row, rest("/jobs/" + job + "/checkpoints")["latest"]
                        ).get("failed")
                    ),
                )
                require(failed["status"] == "FAILED", "checkpoint_did_not_fail")
                progress_failed = kafka.committed(topic, group)
                require(progress_failed < 0, "failed_checkpoint_committed_progress")
            finally:
                command(
                    [
                        "exec",
                        project + "-jobmanager-1",
                        PYTHON,
                        "-c",
                        permission_script,
                        checkpoint_root,
                        "755",
                    ]
                )
            wait(
                lambda: all(
                    vertex["status"] == "RUNNING"
                    for vertex in cast(list[Row], rest("/jobs/" + job)["vertices"])
                )
            )
            # The selected default policy restarts after the failed checkpoint.
            # Wait for the source/operator prefix, not merely job-level RUNNING.
            wait(
                lambda: any(
                    cast(int, r["attempt"]) > cast(int, prefix["attempt"])
                    and r["history_ids"] == prefix["history_ids"]
                    for r in receipt("observation-initial-*-1.json")
                )
            )
            rest("/jobs/" + job + "/checkpoints", {})
            completed = cast(
                Row,
                wait(
                    lambda: cast(
                        Row, rest("/jobs/" + job + "/checkpoints")["latest"]
                    ).get("completed")
                ),
            )
            require(completed["status"] == "COMPLETED", "checkpoint_not_repaired")
            wait(lambda: kafka.committed(topic, group) == 2)
            # A retained checkpoint exists before the controlled TaskManager loss.
            command(["kill", "--signal", "KILL", project + "-taskmanager-1"])
            killed = json.loads(command(["inspect", project + "-taskmanager-1"]))[0]
            require(
                killed["State"]["ExitCode"] == 137 and not killed["State"]["OOMKilled"],
                "not_injected_sigkill",
            )
            for record in records[2:]:
                kafka.send(topic, record)
            kafka.readback(topic, records, [4])
            backlog = {
                "committed": kafka.committed(topic, group),
                "high": 4,
                "observations_pending": 2,
            }
            require(backlog["committed"] == 2, "progress_changed_while_down")
            command(["start", project + "-taskmanager-1"])

            def restored_prefix() -> object:
                return next(
                    (
                        r
                        for r in receipt("before-initial-*-2.json")
                        if r["first_offset"] == 2
                        and r["history_ids"] == prefix["history_ids"]
                    ),
                    None,
                )

            restored = cast(Row, wait(restored_prefix, 120))
            # Observe restored state before processing the first pending observation.
            restored_checkpoint = cast(
                Row,
                cast(Row, rest("/jobs/" + job + "/checkpoints")["latest"])["restored"],
            )
            require(
                restored_checkpoint["id"] == completed["id"],
                "wrong_restored_checkpoint",
            )
            finished = cast(
                list[Row], wait(lambda: receipt("finished-initial.json"), 120)
            )[0]
            require(
                finished["status"] == "FINISHED" and child.wait(timeout=30) == 0,
                "backlog_not_drained",
            )
            raw = command(
                [
                    "exec",
                    project + "-jobmanager-1",
                    "cat",
                    control + "/trace-initial.jsonl",
                ]
            )
            trace = [cast(Row, json.loads(line)) for line in raw.splitlines()]
            reference = calculate_windows(
                scope, [*[Observation(value) for value in values], EndOfInput()]
            )
            windows = [r for r in trace if r["kind"] == "window"]
            require(len(windows) == len(reference.windows) == 2, "window_count")
            for expected in reference.windows:
                actual = next(r for r in windows if r["start_ms"] == expected.start_ms)
                require(
                    actual["unique_events"] == expected.unique_events, "window_unique"
                )
                for name, summary in zip(
                    ("voltage_v", "current_a", "remaining_fraction"),
                    (expected.voltage, expected.current, expected.remaining),
                    strict=True,
                ):
                    measure = cast(list[object], cast(Row, actual["measures"])[name])
                    require(
                        measure[0] == summary.count
                        and Fraction(cast(str, measure[1]))
                        == (summary.total or Fraction(0)),
                        "recovered_window_mismatch",
                    )
            require(
                [str(w.voltage.total) for w in reference.windows] == ["7", "3"],
                "reference_changed",
            )
            with (evidence / "complete.json").open("xb") as stream:
                stream.write(
                    canonical(
                        {
                            "identity": identity,
                            "argv": argv,
                            "failed_trigger": trigger,
                            "failed": failed,
                            "progress_at_failure": progress_failed,
                            "completed": completed,
                            "backlog_while_taskmanager_down": backlog,
                            "restored_before_processing": restored,
                            "restored_checkpoint": restored_checkpoint,
                            "finished": finished,
                            "reference_window_sums": ["7", "3"],
                            "trace_sha256": digest(raw.encode()),
                            "operations": operations,
                        }
                    )
                )
            (evidence / "trace.jsonl").write_text(raw)
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    run(args.project, args.source_evidence.resolve(), args.evidence.resolve())
