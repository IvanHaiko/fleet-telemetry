"""Parent-operated bounded M3 acceptance harness for a fresh isolated runtime."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Protocol, cast

from m3_recovery import pressure, recovery
from m3_reference import (
    check_reference,
    normalized_windows,
    observed,
    prove_graph,
    schedule,
    scope_fields,
)
from m3_resources import storage
from m3_runtime import Runtime, array, integer, obj, require, text
from m3_transport import Transport
from m3_transport_types import Record


class Arguments(Protocol):
    source: Path
    evidence: Path
    project: str


class Validator(Protocol):
    def validate_m3(self, report: object) -> dict[str, object]: ...


def phase(
    runtime: Runtime, control: str, name: str, watermark: int, *, hold: float = 0
) -> dict[str, object]:
    start = time.monotonic()

    def probe() -> object:
        row = obj(runtime.control(control + "/state.json"))
        actual = integer(row["watermark_ms"])
        require(actual <= watermark, "watermark_overshoot")
        return row if actual == watermark else None

    result = obj(runtime.wait(probe, name))
    since = time.monotonic()
    while time.monotonic() - since < hold:
        row = obj(runtime.control(control + "/state.json"))
        require(row["watermark_ms"] == watermark, "watermark_hold_failed")
        if name == "all_silent_no_eof":
            require(row.get("windows") == 1, "silent_window_state_changed")
            require(
                runtime.control(control + "/finished.json") is None, "premature_eof"
            )
        time.sleep(0.1)
    runtime.log(
        "phase_observation",
        {
            "name": name,
            "first_seen": since,
            "wait_started": start,
            "held_seconds": time.monotonic() - since,
            "actual": result,
        },
    )
    return {"name": name, "watermark_ms": integer(result["watermark_ms"])}


def send_idle(
    runtime: Runtime, kafka: Transport, topic: str, control: str, record: Record
) -> None:
    kafka.send(topic, record)
    audit = obj(
        runtime.wait(
            lambda: runtime.control(
                f"{control}/source-{record.partition}-{record.offset}.json"
            ),
            "source_audit",
        )
    )
    for key, value in record.proof(index=True).items():
        require(audit.get(key) == value, "source_manifest_mismatch")
    require(
        type(audit.get("source_subtask")) is int
        and type(audit.get("worker_pid")) is int,
        "source_mapping_missing",
    )
    gate = obj(
        runtime.wait(
            lambda: runtime.control(f"{control}/gate-{record.index}.json"),
            "admission_audit",
        )
    )
    require(gate.get("admitted") is (record.index != 45), "admission_result")
    if record.index != 45:
        observed(runtime, control + "/state.json", record.index)


def idle(
    runtime: Runtime, kafka: Transport, topic: str
) -> tuple[dict[str, object], dict[str, object]]:
    runtime.begin_lane("idleness")
    records = schedule("idle")
    before = kafka.create(topic, 2)
    control = "/state/idle001"
    manifest = runtime.manifest(
        "idle",
        {
            "profile": "m3-partition-input-v1",
            "topic": topic,
            "bootstrap": "kafka:9092",
            "group": topic + "-group",
            "ends": [46, 8],
            "scope": scope_fields(),
            "records": [r.proof(index=True) for r in records],
        },
    )
    runtime.submit(
        "idle",
        "partition_job.py",
        [
            "--manifest",
            manifest,
            "--control",
            control,
            "--scratch",
            "/state/tmp/idle001",
        ],
    )
    job = runtime.finished(control)
    phases: list[dict[str, object]] = []

    def send(i: int) -> None:
        send_idle(runtime, kafka, topic, control, records[i])

    send(0)
    send(1)
    last_b = time.monotonic()
    send(2)
    phases.append(phase(runtime, control, "active_minimum_held", -2001, hold=2.1))
    transition: dict[str, object] | None = None
    heartbeat_start = time.monotonic()

    def check_transition() -> None:
        nonlocal transition
        state = obj(runtime.control(control + "/state.json"))
        watermark = integer(state["watermark_ms"])
        require(watermark in {-2001, 9999}, "idle_transition_overshoot")
        if watermark == 9999 and transition is None:
            silence = time.monotonic() - last_b
            require(silence >= 29, "early_idle_exclusion")
            transition = {"name": "idle_excluded", "watermark_ms": watermark}
            runtime.log(
                "idle_transition", {"actual": state, "silence_seconds": silence}
            )

    for i in range(3, 43):
        target = heartbeat_start + (i - 2) * 0.8
        while time.monotonic() < target:
            check_transition()
            time.sleep(0.05)
        send(i)
        check_transition()
    require(transition is not None, "idle_exclusion_not_observed")
    phases.append(cast(dict[str, object], transition))
    send(43)
    phases.append(phase(runtime, control, "resumed_old_event", 9999))
    send(44)
    send(45)
    send(46)
    phases.append(phase(runtime, control, "resumed_input_holds_minimum", 9999))
    send(47)
    phases.append(phase(runtime, control, "all_silent_no_eof", 19999, hold=32))
    send(48)
    phases.append(phase(runtime, control, "resume_after_both_silent", 29999))
    send(49)
    phases.append(phase(runtime, control, "second_resumed_old_event", 29999))
    send(50)
    phase(runtime, control, "a42_holds", 29999)
    send(51)
    phases.append(phase(runtime, control, "both_active_advanced", 39999))
    for i in (52, 53):
        send(i)
    runtime.await_finished(control, job)
    mappings: dict[int, set[int]] = {0: set(), 1: set()}
    for record in records:
        audit = obj(
            runtime.control(f"{control}/source-{record.partition}-{record.offset}.json")
        )
        require(
            all(audit.get(k) == v for k, v in record.proof(index=True).items()),
            "source_audit_changed",
        )
        mappings[record.partition].add(integer(audit["source_subtask"]))
    require(
        all(len(s) == 1 for s in mappings.values())
        and mappings[0].isdisjoint(mappings[1]),
        "partition_subtask_mapping",
    )
    prove_graph(runtime, job, control)
    runtime.client_exit("idle")
    rows = runtime.lines(control + "/trace.jsonl")
    reference = check_reference(runtime, records, rows, terminal=False)
    windows = [obj(r) for r in rows if obj(r).get("kind") == "window"]
    windows.sort(key=lambda r: integer(r["start_ms"]))
    summaries = [
        (
            integer(w["start_ms"]),
            integer(w["unique_events"]),
            array(obj(w["measures"])["voltage_v"])[1],
        )
        for w in windows
    ]
    require(
        summaries
        == [
            (0, 2, "3"),
            (10000, 1, "3"),
            (20000, 2, "11"),
            (30000, 1, "7"),
            (40000, 2, "19"),
        ],
        "literal_idle_windows",
    )
    require(
        [w["watermark_ms"] for w in windows] == [9999, 19999, 29999, 39999, 2**63 - 1],
        "window_close_watermarks",
    )
    dispositions = [obj(r) for r in rows if obj(r).get("kind") == "disposition"]
    ids = sorted(
        {
            text(r["event_id"])
            for r in dispositions
            if r.get("event_id") and r.get("disposition") != "invalid"
        }
    )
    expected_ids = sorted(
        {text(obj(json.loads(r.value))["event_id"]) for r in records if r.index != 45}
    )
    actual = kafka.readback(topic, records, [46, 8])
    after = kafka.identity(topic, 2)
    require(before == after, "idle_identity_changed")
    runtime.log("idle_reference", reference)
    expected_windows, actual_windows = normalized_windows(records, rows)
    idleness: dict[str, object] = {
        "timeout_ms": 30000,
        "source_parallelism": 2,
        "lane_parallelism": 2,
        "phases": phases,
        "expected_ids": expected_ids,
        "actual_ids": ids,
        "expected_windows": expected_windows,
        "actual_windows": actual_windows,
        "invalid_future_count": sum(
            r.get("disposition") == "invalid" for r in dispositions
        ),
        "late_resume_count": sum(r.get("disposition") == "late" for r in dispositions),
        "duplicate_resume_count": sum(
            r.get("disposition") == "duplicate" and r.get("observation_index") == 44
            for r in dispositions
        ),
    }
    return {
        "source_before": before,
        "source_after": after,
        "ends": [46, 8],
        "expected_records": [r.proof() for r in records],
        "actual_records": actual,
    }, idleness


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--project", required=True)
    args = cast(Arguments, parser.parse_args())
    require(
        os.name == "nt" and sys.version_info[:2] == (3, 13),
        "windows_python313_required",
    )
    runtime = Runtime(args.source, args.evidence, args.project)
    old: list[object] | None = None
    try:
        old = runtime.preflight()
        sys.path[:0] = [
            str(runtime.source / "runtime" / "pyflink"),
            str(runtime.source / "scripts"),
            str(runtime.source),
        ]
        for lane in ("idle", "tm", "cold", "pressure"):
            records = schedule(lane)
            runtime.log(
                "planned_workload",
                {
                    "lane": lane,
                    "records": len(records),
                    "raw_bytes": sum(len(r.key) + len(r.value) for r in records),
                },
            )
        runtime.start()
        storage(runtime)
        runtime.sampling()
        kafka = Transport(runtime.log)
        prefix = "m2.m3-final-" + args.project.removeprefix("fleet-m3-final-")

        def topic(lane: str) -> str:
            return prefix + "-" + lane + ".telemetry.canonical.v1"

        source, idleness = idle(runtime, kafka, topic("idle"))
        proofs = [
            recovery(runtime, kafka, topic(lane), kind)
            for lane, kind in [
                ("tm", "taskmanager_sigkill"),
                ("cold", "runtime_restart"),
            ]
        ]
        resources = pressure(runtime, kafka, topic("pressure"))
        report: dict[str, object] = {
            "profile": "m3-local-synthetic-v1",
            "kafka": source,
            "idleness": idleness,
            "recovery": proofs,
            "resources": resources,
        }
        validator = cast(Validator, importlib.import_module("m3_completion_evidence"))
        summary = validator.validate_m3(report)
        (runtime.evidence / "report.json").write_text(
            json.dumps(report, indent=2), encoding="utf8"
        )
        runtime.log("validated_summary", summary)
    except BaseException as error:
        runtime.log("failure", {"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        try:
            runtime.close()
        finally:
            if old is not None:
                after = runtime.inventory()
                runtime.log("historical_after", after)
                require(after == old, "historical_containers_changed")


if __name__ == "__main__":
    main()
