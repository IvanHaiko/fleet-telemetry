"""Snapshot, readiness checks and the one-screen status of a recording run.

A snapshot combines what the host sees (container states, the Flink REST API
on its loopback port, Grafana's unauthenticated `/api/health`) with a
read-only probe inside the archive network namespace
(runtime/continuous/recording_status.py). Readiness compares two snapshots
taken a declared window apart, because advancing traffic and completing
checkpoints are changes, not states. A value that could not be measured is
`None`, shown as `unknown`, and never passes a check.
"""

from __future__ import annotations

import json
import time
from typing import cast
from urllib.error import URLError
from urllib.request import urlopen

from runtime.recording.evidence import probe
from runtime.recording.profile import PROJECT, Document, Profile

GRAFANA_HEALTH = "http://127.0.0.1:13003/api/health"
CHECKPOINT_AGE_LIMIT_S = 30.0  # three 10 s checkpoint intervals
STATUS_AGE_LIMIT_S = 10.0
# Every other signal has a threshold and a state in runtime/recording/health.py.
NOT_INSTRUMENTED = ("Kafka broker metrics beyond health, offsets and partitions",)


def flink_view(run: Profile) -> Document:
    try:
        overview = run.rest("/overview")
        jobs = run.jobs()
        out: Document = {
            "version": overview.get("flink-version"),
            "taskmanagers": overview.get("taskmanagers"),
            "slots_total": overview.get("slots-total"),
            "slots_free": overview.get("slots-available"),
            "jobs": [{"jid": j["jid"], "state": j["state"]} for j in jobs],
            "job": None,
        }
        running = [j for j in jobs if j.get("state") == "RUNNING"]
        if len(running) == 1:
            jid = str(running[0]["jid"])
            detail = run.rest(f"/jobs/{jid}")
            points = run.rest(f"/jobs/{jid}/checkpoints")
            counts = cast(Document, points.get("counts") or {})
            latest = cast(Document, points.get("latest") or {})
            done = cast(Document | None, latest.get("completed"))
            now = cast(int, detail.get("now", 0))
            out["job"] = {
                "jid": jid,
                "all_running": all(
                    v.get("status") == "RUNNING"
                    for v in cast(list[Document], detail.get("vertices", []))
                ),
                "completed": counts.get("completed"),
                "failed": counts.get("failed"),
                "restored": counts.get("restored"),
                "latest_id": None if done is None else done.get("id"),
                "latest_age_s": None
                if done is None or not now
                else round((now - cast(int, done["latest_ack_timestamp"])) / 1e3, 1),
            }
        return out
    except (URLError, OSError, ValueError, KeyError):
        return {"error": "unreachable"}


def grafana_view() -> Document:
    try:
        with urlopen(GRAFANA_HEALTH, timeout=5) as response:
            return cast(Document, json.loads(response.read(65536)))
    except (URLError, OSError, ValueError):
        return {"error": "unreachable"}


def snapshot(run: Profile) -> Document:
    rows = run.docker(
        *("ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}"),
        *("--format", "{{.Names}}\t{{.State}}\t{{.Status}}"),
    )
    containers = {}
    for line in rows.splitlines():
        name, state, detail = line.split("\t", 2)
        # Observers inherit the image's compose labels; keep service containers.
        if not (name.startswith(PROJECT + "-") and name.endswith("-1")):
            continue
        service = name.removeprefix(PROJECT + "-").removesuffix("-1")
        health = "healthy" if "(healthy)" in detail else None
        containers[service] = {"state": state, "health": health}
    return {
        "host_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "containers": containers,
        "flink": flink_view(run),
        "grafana": grafana_view(),
        "inside": probe(run, "snapshot", network=True),
    }


def field(document: object, *path: str) -> object:
    for key in path:
        if not isinstance(document, dict):
            return None
        document = document.get(key)
    return document


def number_at(document: object, *path: str) -> float | None:
    value = field(document, *path)
    return value if isinstance(value, (int, float)) and value is not True else None


def age_s(snap: Document, progress: str) -> float | None:
    written = number_at(snap, "inside", "progress", progress, "written_ms")
    clock = number_at(snap, "inside", "clock_ms")
    return None if written is None or clock is None else (clock - written) / 1e3


def increased(prev: Document, cur: Document, *path: str) -> bool | None:
    before, after = number_at(prev, *path), number_at(cur, *path)
    return None if before is None or after is None else after > before


def _both(*values: bool | None) -> bool | None:
    return None if any(v is None for v in values) else all(values)


def _running(snap: Document, service: str) -> bool:
    return field(snap, "containers", service, "state") == "running"


def evaluate(
    prev: Document, cur: Document, source: str, after_end: int | None = None
) -> dict[str, bool | None]:
    """One entry per readiness condition; `None` means it could not be measured."""
    live = source == "live"
    prefix = "live-" if live else ""
    sender = (
        ("live-gateway", "gateway-status") if live else ("publisher", "producer-status")
    )
    job, before = (
        field(cur, "flink", "job"),
        field(prev, "flink", "job"),
    )

    def fresh(service: str, progress: str) -> bool | None:
        age = age_s(cur, progress)
        return _both(
            _running(cur, service), None if age is None else age <= STATUS_AGE_LIMIT_S
        )

    identity = field(cur, "inside", "kafka", "identity_ok")
    checkpoints: bool | None = None
    if isinstance(job, dict) and isinstance(before, dict):
        age = number_at(job, "latest_age_s")
        checkpoints = (
            job.get("jid") == before.get("jid")
            and increased(prev, cur, "flink", "job", "completed") is True
            and age is not None
            and age <= CHECKPOINT_AGE_LIMIT_S
        )
    slots = number_at(cur, "flink", "slots_total")
    checks: dict[str, bool | None] = {
        "broker_healthy": _both(
            field(cur, "containers", "kafka", "health") == "healthy",
            None if identity is None else identity is True,
        ),
        "flink_slots_registered": None if slots is None else slots >= 1,
        "job_running": None
        if "error" in cast(Document, cur.get("flink") or {})
        else isinstance(job, dict) and job.get("all_running") is True,
        "checkpoints_completing": checkpoints,
        "archive_worker": fresh(prefix + "archive-worker", "archive-status"),
        "serving_worker": fresh(prefix + "serving-worker", "serving-status"),
        "source_worker": fresh(*sender),
        "clickhouse": None
        if field(cur, "inside", "status") != "ok"
        else field(cur, "inside", "sql", "error") is None,
        "seaweedfs": field(cur, "inside", "s3_answers") is True
        if field(cur, "inside", "status") == "ok"
        else None,
        "grafana_health": None
        if "error" in cast(Document, cur.get("grafana") or {})
        else field(cur, "grafana", "database") == "ok",
        "input_advancing": increased(prev, cur, "inside", "kafka", "input_end"),
        "archive_advancing": increased(
            prev, cur, "inside", "progress", "archive-status", "input_next"
        ),
        "sql_advancing": increased(prev, cur, "inside", "sql", "distinct_inputs"),
    }
    if live:
        refusal = field(cur, "inside", "progress", "gateway-status", "refusal")
        checks["source_not_refused"] = refusal is None
    if after_end is not None:
        highest = number_at(cur, "inside", "sql", "max_input_offset")
        checks["fact_after_resume_visible"] = (
            None if highest is None else highest >= after_end
        )
    return checks


def _show(value: object, unit: str = "") -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.1f}{unit}"
    return f"{value}{unit}"


def render(cur: Document, checks: dict[str, bool | None] | None, window: float) -> str:
    """One screen: components, progress, ages, lags and the readiness checks."""
    inside, flink, job = (
        cur.get("inside"),
        cur.get("flink"),
        field(cur, "flink", "job") or {},
    )
    source = field(inside, "source")
    sender = "gateway-status" if source == "live" else "producer-status"
    end = number_at(inside, "kafka", "input_end")
    archived = number_at(inside, "progress", "archive-status", "input_next")
    committed = number_at(inside, "kafka", "processing_committed")

    def lag(a: float | None, b: float | None) -> str:
        return "unknown" if a is None or b is None else str(int(a - b))

    sent = field(inside, "progress", sender) or {}
    sql_error = field(inside, "sql", "error") or (
        "none" if field(inside, "sql") else "unknown"
    )
    count = field(sent, "published" if source == "live" else "acknowledged")
    lines = [
        f"run {_show(field(inside, 'run_id'))} ({_show(source)}), "
        f"host {cur['host_utc']}",
        "Broker      health "
        f"{_show(field(cur, 'containers', 'kafka', 'health'))}; input end "
        f"{_show(end)}; output end {_show(field(inside, 'kafka', 'output_end_total'))}"
        " (incl. transaction markers)",
        f"Flink       {_show(field(flink, 'version'))}; taskmanagers "
        f"{_show(field(flink, 'taskmanagers'))}; slots free/total "
        f"{_show(field(flink, 'slots_free'))}/{_show(field(flink, 'slots_total'))}; "
        f"run jobs {_show(field(flink, 'jobs'))}",
        f"Job         {_show(field(job, 'jid'))} all vertices running "
        f"{_show(field(job, 'all_running'))}; checkpoints completed "
        f"{_show(field(job, 'completed'))}, failed {_show(field(job, 'failed'))}, "
        f"latest #{_show(field(job, 'latest_id'))} age "
        f"{_show(field(job, 'latest_age_s'), ' s')}",
        f"Processing  committed input offset {_show(committed)}; lag behind input "
        f"{lag(end, committed)} deliveries (committed per checkpoint)",
        f"Source      {_show(field(sent, 'status'))}; sent "
        f"{_show(count)}; "
        + (
            f"epoch {_show(field(sent, 'epoch'))}; refusal "
            f"{field(sent, 'refusal') or 'none'}; "
            if source == "live"
            else ""
        )
        + "status age "
        f"{_show(age_s(cur, sender), ' s')}",
        f"Archive     archived prefix {_show(archived)}; lag {lag(end, archived)}; "
        f"status age {_show(age_s(cur, 'archive-status'), ' s')}",
        "Serving     archived seen "
        f"{_show(field(inside, 'progress', 'serving-status', 'input_archived'))}; "
        "logical facts "
        f"{_show(field(inside, 'progress', 'serving-status', 'logical_facts'))}; "
        f"status age {_show(age_s(cur, 'serving-status'), ' s')}",
        f"SQL         ClickHouse {_show(field(inside, 'sql', 'version'))}; rows "
        f"{_show(field(inside, 'sql', 'physical_rows'))}; distinct inputs "
        f"{_show(field(inside, 'sql', 'distinct_inputs'))}; max input offset "
        f"{_show(field(inside, 'sql', 'max_input_offset'))}; error "
        f"{sql_error}",
        f"Storage     SeaweedFS S3 answers {_show(field(inside, 's3_answers'))}",
        f"Grafana     /api/health database {_show(field(cur, 'grafana', 'database'))} "
        f"(version {_show(field(cur, 'grafana', 'version'))}); datasource query is a"
        " manual signed-in check",
    ]
    if source == "live":
        view = field(inside, "sql", "live_state") or {}
        lines.append(
            f"Live state  connection {_show(field(view, 'connection'))}; source "
            f"receipt age {_show(field(view, 'source_receipt_age_ms'), ' ms')}; "
            f"collector age {_show(field(view, 'collector_age_ms'), ' ms')}"
        )
    markers = field(inside, "markers") or {}
    lines.append(
        "Completion  "
        + ", ".join(f"{k} {_show(v)}" for k, v in cast(Document, markers).items())
    )
    if checks is None:
        lines.append("Readiness   unknown (single snapshot; use --window > 0)")
    else:
        failed = [k for k, v in checks.items() if v is not True]
        lines.append(
            f"Readiness   over {window:g} s: "
            + ("ready" if not failed else "NOT READY")
        )
        lines += [
            f"  {k:28} {'ok' if v else _show(v) if v is None else 'FAIL'}"
            for k, v in checks.items()
        ]
    lines.append("Not instrumented (unknown): " + "; ".join(NOT_INSTRUMENTED))
    return "\n".join(lines)
