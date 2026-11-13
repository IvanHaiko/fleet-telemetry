# ruff: noqa: E402
"""One authored Kafka/Flink idle-resume scenario with exact SQL reconciliation.

The parent starts/stops fresh services. This command changes no existing profile,
archive or M4 seal, and never bootstraps schemas or credentials implicitly.
"""

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from m3_transport import Transport
from m3_transport_types import Record
from m5_late_sql import insert, reports

from runtime.clickhouse.transport import HttpConfig
from scripts.slice_run import exact6
from telemetry.archive_documents import canonical, digest
from telemetry.conversion_contract import SEMANTIC_FIELDS
from telemetry.serving_projection import _decimal, _semantic_json
from telemetry_convert import convert_job, verify_job
from telemetry_reference import (
    EndOfInput,
    Observation,
    ReferenceScope,
    TraceStep,
    Watermark,
    calculate_windows,
    epoch_milliseconds,
)

type Row = dict[str, object]
DOCKER = shutil.which("docker.exe") or shutil.which("docker") or "docker"
PYTHON = (
    "/home/ivan/.local/share/fleet-telemetry/pyflink/"
    "m3-compatibility-002/venv/bin/python"
)
METRICS = ("voltage_v", "current_a", "remaining_fraction")


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def obj(value: object) -> Row:
    require(isinstance(value, dict), "expected_object")
    return cast(Row, value)


def save(folder: Path, name: str, value: object) -> None:
    with (folder / name).open("xb") as stream:
        stream.write(canonical(value))


def command(args: list[str], *, input_text: str | None = None) -> str:
    result = subprocess.run(
        [DOCKER, *args], input=input_text, capture_output=True, text=True, timeout=30
    )
    require(result.returncode == 0, "docker_command_failed")
    return result.stdout


def control(project: str, name: str, location: str) -> Row | None:
    return cast(
        Row | None,
        json.loads(
            command(
                [
                    "exec",
                    project + "-jobmanager-1",
                    PYTHON,
                    "-c",
                    "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
                    "print(p.read_text() if p.exists() else 'null')",
                    location + "/" + name,
                ]
            )
        ),
    )


def await_control(project: str, name: str, deadline: float, location: str) -> Row:
    while time.monotonic() < deadline:
        value = control(project, name, location)
        if value is not None:
            return value
        time.sleep(0.1)
    raise TimeoutError("control_deadline")


def run(folder: Path, project: str, private: Path) -> None:
    require(
        sys.platform == "linux" and re.fullmatch(r"fleet-m3-final-[0-9]{3}", project),
        "unsupported_profile",
    )
    tag = folder.name.rsplit("-", 1)[-1]
    require(re.fullmatch(r"[0-9]{3}", tag), "invalid_case_tag")
    run_id = project + "-" + tag
    location = "/state/m5-" + tag
    folder.mkdir(exist_ok=False)
    config = obj(json.loads(private.read_bytes()))
    writer = HttpConfig(**cast(dict[str, str | int], config["writer"]))  # type: ignore[arg-type]
    reader = HttpConfig(**cast(dict[str, str | int], config["reader"]))  # type: ignore[arg-type]
    fixture = ROOT / "tests/fixtures/m5-idle-conversion-job.json"
    conversion = convert_job(fixture, folder / "demo-m5-idle-001")
    verify_job(fixture, conversion.output_directory)
    values = (conversion.output_directory / "events.jsonl").read_bytes().splitlines()
    require(
        len(values) == 6
        and conversion.run_manifest["counts"]
        == {
            "source_records": 6,
            "admitted_records": 6,
            "rejected_records": 0,
            "unique_events": 6,
            "duplicate_events": 0,
        },
        "fixture_changed",
    )
    canonical_events = [obj(json.loads(value)) for value in values]
    planned = [(0, 0), (1, 1), (0, 3)] + [(0, 3)] * 40
    planned += [(1, 2), (1, 2), (1, 4), (0, 4), (1, 5), (0, 5), (1, 2), (0, 0)]
    offsets = [0, 0]
    records: list[Record] = []
    for index, (partition, event_number) in enumerate(planned):
        records.append(
            Record(
                partition,
                offsets[partition],
                index,
                values[event_number],
                str(canonical_events[event_number]["vehicle_id"]).encode(),
            )
        )
        offsets[partition] += 1
    require(offsets == [45, 6], "schedule_changed")
    scope = ReferenceScope(
        "demo-m5-idle-001",
        "online-idle-v1",
        cast(str, canonical_events[0]["source_log_id"]),
        "2026-01-01T12:00:00.000000Z",
        "2026-01-01T12:10:22.000000Z",
    )
    anchor = epoch_milliseconds(scope.timestamp_min)
    topic = f"m2.m3-final-m5-{run_id}.telemetry.canonical.v1"
    log_index = 0

    def log(kind: str, value: object) -> None:
        nonlocal log_index
        save(folder, f"kafka-{log_index:03d}-{kind}.json", value)
        log_index += 1

    kafka = Transport(log)
    identity = kafka.create(topic, 2)
    metadata = command(
        [
            "exec",
            project + "-kafka-1",
            "/opt/kafka/bin/kafka-topics.sh",
            "--bootstrap-server",
            "kafka:9092",
            "--describe",
            "--topic",
            topic,
        ]
    )
    match = re.search(r"TopicId:\s*(\S+)", metadata)
    require(match is not None, "broker_identity_missing")
    assert match is not None
    require(
        base64.urlsafe_b64decode(match[1] + "==")
        == base64.b64decode(cast(str, identity["topic_id"]) + "=="),
        "topic_uuid_mismatch",
    )
    save(folder, "source-identity.json", {**identity, "broker_metadata": metadata})
    manifest = {
        "profile": "m3-partition-input-v1",
        "topic": topic,
        "bootstrap": "kafka:9092",
        "group": topic + "-group",
        "ends": offsets,
        "scope": asdict(scope),
        "records": [row.proof(index=True) for row in records],
    }
    save(folder, "manifest.json", manifest)
    command(
        [
            "exec",
            "-i",
            project + "-jobmanager-1",
            "sh",
            "-c",
            "cat > /state/m5-input-" + tag + ".json",
        ],
        input_text=json.dumps(manifest),
    )
    argv = [
        DOCKER,
        "exec",
        project + "-jobmanager-1",
        "/opt/m3/entrypoint.sh",
        "submit",
        "-py",
        "/workspace/runtime/pyflink/partition_job.py",
        "--manifest",
        "/state/m5-input-" + tag + ".json",
        "--control",
        location,
        "--scratch",
        "/state/tmp/m5-" + tag,
    ]
    with (
        (folder / "flink.stdout").open("xb") as out,
        (folder / "flink.stderr").open("xb") as err,
    ):
        child = subprocess.Popen(argv, stdout=out, stderr=err)
        try:
            deadline = time.monotonic() + 240
            ready = await_control(project, "ready.json", deadline, location)

            def send(index: int) -> None:
                require(child.poll() in (None, 0), "flink_client_failed")
                record = records[index]
                kafka.send(topic, record)
                audit = await_control(
                    project,
                    f"source-{record.partition}-{record.offset}.json",
                    deadline,
                    location,
                )
                require(
                    all(
                        audit[key] == value
                        for key, value in record.proof(index=True).items()
                    ),
                    "flink_source_bytes",
                )
                require(
                    await_control(project, f"gate-{index}.json", deadline, location)[
                        "admitted"
                    ]
                    is True,
                    "admission_failed",
                )
                while time.monotonic() < deadline:
                    state = control(project, "state.json", location)
                    if state and state["observation_index"] == index:
                        return
                    time.sleep(0.05)
                raise TimeoutError("observation_deadline")

            send(0)
            send(1)
            last_b = time.monotonic()
            send(2)
            active = await_control(project, "state.json", deadline, location)
            require(
                cast(int, active["watermark_ms"]) <= anchor - 2001,
                "active_minimum_advanced",
            )
            heartbeat = time.monotonic()
            transition: Row | None = None
            for index in range(3, 43):
                while time.monotonic() < heartbeat + (index - 2) * 0.8:
                    time.sleep(0.05)
                send(index)
                state = await_control(project, "state.json", deadline, location)
                require(
                    cast(int, state["watermark_ms"]) <= anchor + 9999,
                    "watermark_overshoot",
                )
                if state["watermark_ms"] == anchor + 9999 and transition is None:
                    silence = time.monotonic() - last_b
                    require(silence >= 29, "premature_idle")
                    transition = {
                        "silence_seconds": silence,
                        "watermark_ms": state["watermark_ms"],
                    }
            require(transition is not None, "idle_not_observed")
            send(43)
            send(44)
            send(45)
            send(46)
            send(47)
            send(48)
            while time.monotonic() < deadline:
                state = await_control(project, "state.json", deadline, location)
                if state["watermark_ms"] == anchor + 619999:
                    break
                time.sleep(0.1)
            require(state["watermark_ms"] == anchor + 619999, "horizon_not_advanced")
            send(49)
            send(50)
            finished = await_control(project, "finished.json", deadline, location)
            require(
                finished["status"] == "FINISHED"
                and finished["job_id"] == ready["job_id"],
                "job_not_finished",
            )
            require(child.wait(timeout=30) == 0, "client_exit")
            save(
                folder,
                "runtime.json",
                {
                    "argv": argv,
                    "ready": ready,
                    "finished": finished,
                    "idle_transition": transition,
                },
            )
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
    raw = command(["exec", project + "-jobmanager-1", "cat", location + "/trace.jsonl"])
    trace = [obj(json.loads(line)) for line in raw.splitlines()]
    save(folder, "trace.json", trace)
    dispositions = [row for row in trace if row["kind"] == "disposition"]
    require(
        [row["observation_index"] for row in dispositions] == list(range(51)),
        "trace_order",
    )
    reference_trace: list[TraceStep] = []
    watermark = -(2**63)
    for record, row in zip(records, dispositions, strict=True):
        current = cast(int, row["watermark_ms"])
        require(current >= watermark, "watermark_regression")
        if current > watermark:
            reference_trace.append(Watermark(current))
            watermark = current
        reference_trace.append(Observation(record.value))
    reference_trace.append(EndOfInput())
    reference = calculate_windows(scope, reference_trace)
    save(
        folder, "reference.json", json.loads(json.dumps(asdict(reference), default=str))
    )
    require(
        [(row["event_id"], row["disposition"], row["reason"]) for row in dispositions]
        == [(row.event_id, row.kind, row.reason) for row in reference.dispositions],
        "reference_dispositions",
    )
    require(
        Counter(row.kind for row in reference.dispositions)
        == {"eligible": 5, "duplicate": 43, "late": 3},
        "disposition_counts",
    )
    require(
        dispositions[43]["disposition"] == "late"
        and dispositions[43]["watermark_ms"] == anchor + 9999
        and dispositions[44]["disposition"] == "duplicate",
        "late_resume_boundary",
    )
    require(
        all(dispositions[i]["disposition"] == "late" for i in (49, 50)),
        "expired_duplicate_misclassified",
    )
    expired = {
        event_id
        for row in trace
        if row["kind"] == "expiry"
        for event_id in cast(list[str], row["event_ids"])
    }
    require(
        {event["event_id"] for event in canonical_events[:5]} <= expired,
        "active_identity_expiry_missing",
    )
    actual_windows = [row for row in trace if row["kind"] == "window"]
    require(len(actual_windows) == len(reference.windows) == 4, "window_count")
    windows: list[Row] = []
    for expected in reference.windows:
        actual = next(
            row for row in actual_windows if row["start_ms"] == expected.start_ms
        )
        require(
            all(
                actual[key] == getattr(expected, key)
                for key in (
                    "dataset_run_id",
                    "pipeline_version",
                    "vehicle_id",
                    "start_ms",
                    "end_ms",
                    "unique_events",
                )
            ),
            "window_identity",
        )
        for metric, summary in zip(
            METRICS,
            (expected.voltage, expected.current, expected.remaining),
            strict=True,
        ):
            measure = cast(list[object], obj(actual["measures"])[metric])
            require(
                measure[0] == summary.count
                and Fraction(cast(str, measure[1])) == (summary.total or Fraction(0)),
                "window_reference",
            )
            windows.append(
                {
                    "dataset_run_id": run_id,
                    "pipeline_version": "online-idle-v1",
                    "vehicle_id": expected.vehicle_id,
                    "metric_definition": metric,
                    "start_ms": expected.start_ms,
                    "end_ms": expected.end_ms,
                    "revision": 1,
                    "unique_events": expected.unique_events,
                    "valid_count": summary.count,
                    "value_sum": exact6(summary.total or Fraction(0)),
                }
            )
    require(
        [str(window.voltage.total) for window in reference.windows]
        == ["3", "3", "5", "6"],
        "late_inflated_window",
    )
    first = {
        cast(str, row["event_id"]): row["disposition"]
        for row in reversed(dispositions)
        if row["disposition"] != "duplicate"
    }
    events: list[Row] = []
    for event in canonical_events:
        payload = obj(event["payload"])
        semantic = {key: event[key] for key in SEMANTIC_FIELDS}
        semantic["quality_flags"] = sorted(cast(list[str], event["quality_flags"]))
        events.append(
            {
                "dataset_run_id": run_id,
                "pipeline_version": "online-idle-v1",
                "event_id": event["event_id"],
                "vehicle_id": event["vehicle_id"],
                "source_timestamp": event["source_timestamp"],
                **{name: _decimal(payload[name], name) for name in METRICS},
                "disposition": first[cast(str, event["event_id"])],
                "quality_flags": semantic["quality_flags"],
                "semantic_json": _semantic_json(semantic),
            }
        )
    kafka.readback(topic, records, offsets)
    for table, values_to_write in (("events", events), ("windows", windows)):
        insert(writer, table, run_id, values_to_write, 2)
    before = reports(reader, run_id, events, windows)
    for table, values_to_write in (("events", events), ("windows", windows)):
        insert(writer, table, run_id, values_to_write, 1)
    require(reports(reader, run_id, events, windows) == before, "retry_changed_reports")
    save(folder, "reports.json", before)
    save(
        folder,
        "complete.json",
        {
            "online_late_observed": True,
            "beyond_horizon_repeats_late": True,
            "scope": run_id,
            "dispositions": dict(Counter(row.kind for row in reference.dispositions)),
            "late_event_id": dispositions[43]["event_id"],
            "late_duplicate_disposition": dispositions[44]["disposition"],
            "source_counts": conversion.run_manifest["counts"],
            "reports_unchanged_on_retry": True,
            "sql_windows_exclude_late": True,
            "trace_sha256": digest(raw.encode()),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--private-config", type=Path, required=True)
    args = parser.parse_args()
    run(args.evidence.resolve(), args.project, args.private_config.resolve())
