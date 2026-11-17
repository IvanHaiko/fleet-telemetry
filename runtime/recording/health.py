"""Monitoring signals of one recording run, each with a threshold and a state.

No monitoring service is added (ADR-0056): every signal is computed from what
the profile already writes or answers: the source's own counts, the Flink
REST API, the Kafka command-line tools inside the broker container, the run's
progress files, the SQL quality checks (runtime/continuous/recording_health.py)
and the Docker CLI. `measure` gathers those observations; `evaluate` is pure
and turns them into signals with a state of `ok`, `warn`, `fail` or `unknown`.
A value that was not observed stays `unknown`; zero is never substituted.

Signal names, labels and values carry counts, sizes and states only, never an
event, vehicle or measurement identifier and never a coordinate.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from typing import cast
from urllib.error import URLError

from runtime.recording.evidence import probe
from runtime.recording.profile import (
    PROJECT,
    ROOT,
    WORKER_IMAGE,
    Document,
    Profile,
    RunFailure,
)

LAG_WARN = 1000  # deliveries: about one minute of the F09 replay at 1x
STATUS_AGE_WARN_S, STATUS_AGE_FAIL_S = 10.0, 60.0
CHECKPOINT_AGE_FAIL_S = 30.0  # three 10 s checkpoint intervals (ADR-0055)
EXPECTED_CHECKPOINT_FAILURES = 1  # the trigger at submission (ADR-0052)
REPEAT_RATIO_WARN = 2.0
MEMORY_WARN, MEMORY_FAIL = 80.0, 95.0  # percent of the container's limit
CPU_WARN = 95.0  # percent of the container's CPU budget
# One complete F09 run measured 287 MB on the Docker disk and 118 MB in its
# run directory (ADR-0056); the budget adds room for the verification rebuild
# database and container logs.
FULL_RUN_BYTES = 512 << 20
DECLARED_REPEATS = 2  # recording_initialize appends two deliberate repeats
OPERATOR_COUNTERS = {
    "f09": ("accepted", "duplicate", "late", "gps", "rejected"),
    "live": ("accepted", "duplicate", "position", "rejected"),
}


def operator_counters(source: str) -> tuple[str, ...]:
    """Every registered recording uses the recording lane's counters."""
    return OPERATOR_COUNTERS["live" if source == "live" else "f09"]


def _run(*args: str, timeout: float = 60) -> str | None:
    try:
        done = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _number(text: str) -> float | None:
    try:
        return float(text.strip().rstrip("%"))
    except ValueError:
        return None


_UNITS = {
    "b": 1,
    "kib": 1 << 10,
    "mib": 1 << 20,
    "gib": 1 << 30,
    "tib": 1 << 40,
    "kb": 10**3,
    "mb": 10**6,
    "gb": 10**9,
    "tb": 10**12,
}


def size_bytes(text: str) -> int | None:
    """`512.3MiB` or `1.2GB` as bytes; None when it cannot be read."""
    match = re.fullmatch(r"([0-9.]+)\s*([A-Za-z]+)", text.strip())
    unit = None if match is None else _UNITS.get(match[2].lower())
    return None if match is None or unit is None else int(float(match[1]) * unit)


def resources() -> Document:
    """Memory and CPU of the profile's service containers, limits and disk."""
    names = (_run("ps", "--format", "{{.Names}}") or "").split()
    services = [n for n in names if n.startswith(PROJECT + "-") and n.endswith("-1")]
    out: Document = {"containers": None, "engine_memory": None, "disk": None}
    if services:
        stats = _run("stats", "--no-stream", "--format", "{{json .}}", *services)
        inspect = _run("inspect", *services)
        if stats is not None and inspect is not None:
            limits = {
                str(c["Name"]).lstrip("/"): cast(Document, c["HostConfig"])
                for c in json.loads(inspect)
            }
            rows = []
            for line in stats.splitlines():
                row = json.loads(line)
                name = str(row["Name"])
                host = limits.get(name, {})
                cpus = cast(int, host.get("NanoCpus") or 0) / 1e9
                cpu = _number(str(row.get("CPUPerc", "")))
                rows.append(
                    {
                        "service": name.removeprefix(PROJECT + "-").removesuffix("-1"),
                        "memory_pct": _number(str(row.get("MemPerc", ""))),
                        "memory_bytes": size_bytes(
                            str(row.get("MemUsage", "")).split("/")[0]
                        ),
                        "memory_limit": host.get("Memory") or None,
                        "cpu_budget_pct": None
                        if cpu is None or not cpus
                        else round(cpu / cpus, 1),
                    }
                )
            out["containers"] = rows
    else:
        out["containers"] = []
    total = _run("info", "--format", "{{.MemTotal}}")
    out["engine_memory"] = int(total) if total and total.strip().isdigit() else None
    df = _run(
        *("run", "--rm", "--network", "none", "--entrypoint", "df"),
        *("-v", f"{PROJECT}_evidence:/v:ro", WORKER_IMAGE, "-B1", "/v"),
    )
    # Docker's virtual disk grows on the host disk; either may run out first.
    host_disk = shutil.disk_usage(ROOT)
    if df:
        cells = df.splitlines()[-1].split()
        out["disk"] = {
            "size": int(cells[1]),
            "available": min(int(cells[3]), host_disk.free),
            "docker_available": int(cells[3]),
            "host_available": host_disk.free,
        }
    return out


def sample(run: Profile) -> None:
    """Append one resource sample to the run's `resources.jsonl` (ADR-0056)."""
    row: Document = {"host_ms": time.time_ns() // 1_000_000, **resources()}
    listing = _run("system", "df", "-v", "--format", "{{json .Volumes}}")
    row["volumes"] = (
        None
        if listing is None
        else {
            str(v["Name"]).removeprefix(PROJECT + "_"): v["Size"]
            for v in cast(list[Document], json.loads(listing) or [])
            if str(v["Name"]).startswith(PROJECT + "_")
        }
    )
    path = run.out / "resources.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def kafka(run: Profile) -> Document:
    """Consumer-group lag, unavailable partitions and topic bytes of the run."""
    broker = run.container("kafka")
    tools = "/opt/kafka/bin/"
    server = ("--bootstrap-server", "kafka:9092")
    out: Document = {"groups": None, "unavailable": None, "topic_bytes": None}
    groups = _run(
        "exec",
        broker,
        tools + "kafka-consumer-groups.sh",
        *server,
        "--describe",
        "--all-groups",
    )
    if groups is not None:
        lags: dict[str, int] = {}
        for line in groups.splitlines():
            cells = line.split()
            if (
                len(cells) >= 6
                and cells[0].startswith(run.run_id)
                and cells[5].isdigit()
            ):
                lags[cells[0]] = max(lags.get(cells[0], 0), int(cells[5]))
        out["groups"] = {g.removeprefix(run.run_id): lag for g, lag in lags.items()}
    topics = [f"telemetry.{run.run_id}.{w}.v1" for w in ("input", "output")]
    missing = _run(
        "exec",
        broker,
        tools + "kafka-topics.sh",
        *server,
        "--describe",
        "--unavailable-partitions",
    )
    if missing is not None:
        out["unavailable"] = sum(
            1 for line in missing.splitlines() if any(t in line for t in topics)
        )
    sizes = _run(
        "exec",
        broker,
        tools + "kafka-log-dirs.sh",
        *server,
        "--describe",
        "--topic-list",
        ",".join(topics),
    )
    if sizes is not None:
        documents = [line for line in sizes.splitlines() if line.startswith("{")]
        if documents:
            brokers = cast(list[Document], json.loads(documents[-1])["brokers"])
            out["topic_bytes"] = sum(
                cast(int, p["size"])
                for b in brokers
                for d in cast(list[Document], b["logDirs"])
                for p in cast(list[Document], d["partitions"])
            )
    return out


def flink(run: Profile, source: str) -> Document:
    """Job restarts and the association operator's disposition counters."""
    out: Document = {"restarts": None, "counters": None}
    try:
        running = [j for j in run.jobs() if j.get("state") == "RUNNING"]
        if len(running) != 1:
            return out
        jid = running[0]["jid"]
        restarts = cast(
            list[Document], run.rest(f"/jobs/{jid}/metrics?get=numRestarts")
        )
        if restarts:
            out["restarts"] = int(cast(str, restarts[0]["value"]))
        wanted = {
            f"{'live' if source == 'live' else 'recording'}_{name}": name
            for name in operator_counters(source)
        }
        for vertex in cast(list[Document], run.rest(f"/jobs/{jid}")["vertices"]):
            base = f"/jobs/{jid}/vertices/{vertex['id']}/subtasks/metrics"
            ids = [str(m["id"]) for m in cast(list[Document], run.rest(base))]
            found = [i for i in ids if i.rsplit(".", 1)[-1] in wanted]
            if found:
                values = cast(
                    list[Document], run.rest(f"{base}?get={','.join(found)}&agg=sum")
                )
                out["counters"] = {
                    wanted[str(v["id"]).rsplit(".", 1)[-1]]: int(float(str(v["sum"])))
                    for v in values
                }
    except (URLError, OSError, ValueError, KeyError):
        return out
    return out


def admission(run: Profile, source: str, snap: Document) -> Document:
    """The source's own counts: prepared recording manifests or the live gateway."""
    if source == "live":
        status = cast(
            Document,
            cast(
                Document, cast(Document, snap.get("inside") or {}).get("progress") or {}
            ).get("gateway-status")
            or {},
        )
        keys = (
            "captured",
            "published",
            "bad_data",
            "foreign_packets",
            "lost_packets",
            "sequence_gaps",
            "refusal",
        )
        return {k: status.get(k) for k in keys} if status else {}
    from runtime.recording.fault_run import recording_inputs

    bundle = run.out / "bundle"
    try:
        manifest = json.loads((bundle / "manifest.json").read_text())
        context = json.loads((bundle / "context.json").read_text())
        prepared = recording_inputs(source)[0]
        battery = json.loads(
            next((prepared / "battery").glob("*/run-manifest.json")).read_text()
        )
    except (OSError, ValueError, StopIteration, RunFailure):
        return {}
    counts = cast(Document, battery["counts"])
    return {
        "battery_source_records": counts["source_records"],
        "battery_admitted": counts["admitted_records"],
        "battery_rejected": counts["rejected_records"],
        "rejection_reasons": battery["rejection_reasons"],
        "stream_counts": manifest["stream_counts"],
        "bundle_events": manifest["events"],
        "battery_rejection_gaps": len(cast(list[object], context["battery_gaps"])),
        "state_gaps": len(cast(list[object], context["state_gaps"])),
    }


def measure(run: Profile, plan: Document, snap: Document) -> Document:
    source = str(plan["source"])
    return {
        "source": source,
        "declared": {k: plan.get(k) for k in ("deliveries", "expected")},
        "admission": admission(run, source, snap),
        "flink": flink(run, source),
        "kafka": kafka(run),
        "resources": resources(),
        "inside": probe(run, "health", network=True),
    }
