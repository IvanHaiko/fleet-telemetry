"""Bounded workloads and independent trace/window reference verification."""

from __future__ import annotations

import importlib
import json
from typing import cast

from m3_runtime import Runtime, array, integer, obj, require, text
from m3_transport_types import Fixtures, Record


def fixtures() -> Fixtures:
    return cast(Fixtures, importlib.import_module("tests.test_reference"))


def scope_fields() -> dict[str, object]:
    selected = fixtures().scope()
    return {
        key: text(getattr(selected, key))
        for key in (
            "dataset_run_id",
            "pipeline_version",
            "source_log_id",
            "timestamp_min",
            "timestamp_max",
        )
    }


def schedule(lane: str) -> list[Record]:
    fixture = fixtures()

    def event(index: int, seconds: int, voltage: int) -> bytes:
        timestamp = f"1970-01-01T00:00:{seconds:02d}.000000Z"
        if seconds == 86401:
            timestamp = "1970-01-02T00:00:00.000001Z"
        return json.dumps(
            fixture.event(index, timestamp, voltage=float(voltage)),
            separators=(",", ":"),
            allow_nan=False,
        ).encode()

    pairs: list[tuple[int, bytes]]
    if lane == "idle":
        a0, b0, a12 = event(0, 0, 1), event(1, 0, 2), event(2, 12, 3)
        b9 = event(3, 9, 4)
        a42, b42 = event(8, 42, 9), event(9, 42, 10)
        pairs = [(0, a0), (1, b0), (0, a12)] + [(0, a12)] * 40
        pairs += [
            (1, b9),
            (1, b9),
            (1, event(10, 86401, 1)),
            (1, event(4, 22, 5)),
            (0, event(5, 22, 6)),
            (1, event(6, 32, 7)),
            (0, event(7, 21, 8)),
            (0, a42),
            (1, b42),
            (0, a42),
            (1, b42),
        ]
    elif lane in {"tm", "cold"}:
        unique = [event(i, 0 if i < 5 else 10, i + 1) for i in range(8)]
        pairs = [(0, unique[i]) for i in (0, 1, 2, 3, 1, 4, 5, 6, 7)]
    else:
        require(lane == "pressure", "unknown_lane")
        pairs = [(0, event(i, 0, i + 1)) for i in range(4)]
    offsets = [0, 0]
    result: list[Record] = []
    for index, (partition, value) in enumerate(pairs):
        result.append(Record(partition, offsets[partition], index, value))
        offsets[partition] += 1
    require(
        len(result) < 128 and sum(len(r.key) + len(r.value) for r in result) <= 1048576,
        "workload_bound",
    )
    return result


def normalized_windows(
    records: list[Record], rows: list[object]
) -> tuple[list[object], list[object]]:
    from dataclasses import asdict

    from m3_runtime import obj

    from telemetry_reference import (
        EndOfInput,
        Observation,
        ReferenceScope,
        TraceStep,
        Watermark,
        calculate_windows,
    )

    dispositions = sorted(
        [obj(r) for r in rows if obj(r).get("kind") == "disposition"],
        key=lambda r: integer(r["observation_index"]),
    )
    require(
        [r["observation_index"] for r in dispositions] == list(range(len(records))),
        "reference_dispositions_missing",
    )
    trace: list[TraceStep] = []
    watermark = -(2**63)
    for record, row in zip(records, dispositions, strict=True):
        if row["disposition"] != "invalid":
            current = integer(row["watermark_ms"])
            require(current >= watermark, "reference_watermark_decreased")
            if current > watermark:
                trace.append(Watermark(current))
                watermark = current
        trace.append(Observation(record.value))
    trace.append(EndOfInput())
    expected: list[object] = []
    for window in calculate_windows(
        cast(ReferenceScope, fixtures().scope()), trace
    ).windows:
        value = asdict(window)
        value["measures"] = {
            name: [measure.count, str(measure.total) if measure.count else None]
            for name, measure in zip(
                ("voltage_v", "current_a", "remaining_fraction"),
                (window.voltage, window.current, window.remaining),
                strict=True,
            )
        }
        for key in ("voltage", "current", "remaining"):
            del value[key]
        expected.append(value)
    actual: list[object] = []
    for row in sorted(
        [obj(r) for r in rows if obj(r).get("kind") == "window"],
        key=lambda r: (text(r["vehicle_id"]), integer(r["start_ms"])),
    ):
        value = {
            k: row[k]
            for k in (
                "dataset_run_id",
                "pipeline_version",
                "vehicle_id",
                "start_ms",
                "end_ms",
                "unique_events",
            )
        }
        value["measures"] = {
            k: [array(v)[0], array(v)[1] if array(v)[0] else None]
            for k, v in obj(row["measures"]).items()
        }
        actual.append(value)
    require(expected == actual, "normalized_reference_windows_differ")
    return expected, actual


def prove_graph(runtime: object, job: str, control: str) -> None:
    from m3_runtime import Runtime, obj

    runtime = cast(Runtime, runtime)
    plan = obj(runtime.rest("/jobs/" + job + "/plan"))
    runtime.log("actual_plan", plan)
    nodes = [obj(n) for n in array(obj(plan["plan"])["nodes"])]
    sources = [n for n in nodes if not n.get("inputs")]
    require(
        sources and all(n["parallelism"] == 2 for n in sources),
        "source_graph_parallelism",
    )
    vertices = [obj(v) for v in array(obj(runtime.rest("/jobs/" + job))["vertices"])]
    require(
        all(v["parallelism"] in {1, 2} for v in vertices), "unexpected_lane_parallelism"
    )
    for marker, parallelism in [
        ("PartitionAdmission", 2),
        ("Extract-Timestamp", 2),
        ("Watermark-Generator", 2),
        ("Remove-Timestamp", 2),
        ("ObservedBattery", 1),
    ]:
        matches = [v for v in vertices if marker.lower() in text(v["name"]).lower()]
        require(
            matches and all(v["parallelism"] == parallelism for v in matches),
            "named_graph_parallelism_unproven",
        )
    # Locate the job-retained get_execution_plan JSON without assuming its filename.
    raw = runtime.execute(
        "jobmanager",
        """import pathlib,json,sys
roots=[pathlib.Path(sys.argv[1]),pathlib.Path('/state/tmp/idle001')]; rows=[]
files=[p for root in roots for p in root.rglob('*.json')]; assert len(files)<=512
for p in files:
 if p.stat().st_size>1048576: continue
 value=json.loads(p.read_text())
 if isinstance(value,dict) and 'nodes' in value:
  rows.append({'path':str(p),'plan':value})
print(json.dumps(rows))""",
        control,
    )
    plans = array(json.loads(raw))
    runtime.log("retained_execution_plans", plans)
    candidates = [obj(obj(p)["plan"]) for p in plans]
    require(candidates, "retained_execution_plan_missing")
    planned = [obj(n) for p in candidates for n in array(p["nodes"])]
    lane = []
    for marker, parallelism in (
        ("PartitionAdmission", 2),
        ("Extract-Timestamp", 2),
        ("Watermark-Generator", 2),
        ("Remove-Timestamp", 2),
    ):
        matches = [n for n in planned if n.get("type") == marker]
        require(len(matches) == 1, "planned_bridge_node")
        node = matches[0]
        require(node.get("parallelism") == parallelism, "planned_bridge_parallelism")
        lane.append(node)
    # The pinned StreamGraph plan uses predecessors/id, independently read back
    # from the submitted graph; REST above proves the deployed parallelism.
    for upstream, downstream in zip(lane[:-1], lane[1:], strict=True):
        edges = [obj(e) for e in array(downstream.get("predecessors", []))]
        require(
            len(edges) == 1
            and edges[0].get("id") == upstream["id"]
            and edges[0].get("ship_strategy") == "FORWARD",
            "planned_bridge_forward",
        )


def check_reference(
    runtime: Runtime, records: list[Record], rows: list[object], *, terminal: bool
) -> dict[str, object]:
    # The existing verifier imports PyFlink modules; run it in the pinned Linux
    # profile while leaving the Windows transport/controller dependency intact.
    clean: list[object] = []
    for row in rows:
        copied = dict(obj(row))
        copied.pop("run_tag", None)
        copied.pop("attempt", None)
        clean.append(copied)
    manifest = runtime.manifest(
        "reference-" + runtime.phase,
        {
            "wires_hex": [r.value.hex() for r in records],
            "rows": clean,
            "terminal_only": terminal,
        },
    )
    raw = runtime.execute(
        "jobmanager",
        "import pathlib,json,sys; from check_battery import verify; "
        "p=pathlib.Path(sys.argv[1]); assert p.stat().st_size<=1048576; "
        "data=json.loads(p.read_text()); "
        "assert len(data['wires_hex'])<=128 and len(data['rows'])<=512; "
        "result=verify([bytes.fromhex(w) for w in data['wires_hex']], "
        "data['rows'],terminal_only=data['terminal_only']); "
        "print(json.dumps(result))",
        manifest,
    )
    return obj(json.loads(raw))


def observed(
    runtime: Runtime, path: str, index: int | None = None
) -> dict[str, object]:
    def probe() -> object:
        row = runtime.control(path)
        if row is None:
            return None
        if index is not None and obj(row).get("observation_index") != index:
            return None
        return row

    return obj(runtime.wait(probe, "observation"))
