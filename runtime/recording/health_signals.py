"""Turn one run's observations into monitoring signals (pure; ADR-0056).

Input: the status snapshot (runtime/recording/ops_view.py) and the health
observations (runtime/recording/health.py). Output: one row per signal with
its source, its declared threshold, the observed value and a state of `ok`,
`warn`, `fail` or `unknown`. Anything not observed is `unknown`; a count is
never assumed to be zero. Thresholds are declared here and in ADR-0056, from
contracts, compose limits and documented behaviour, not from the stored data.
"""

from __future__ import annotations

from typing import cast

from runtime.recording.health import (
    CHECKPOINT_AGE_FAIL_S,
    CPU_WARN,
    DECLARED_REPEATS,
    EXPECTED_CHECKPOINT_FAILURES,
    FULL_RUN_BYTES,
    LAG_WARN,
    MEMORY_FAIL,
    MEMORY_WARN,
    REPEAT_RATIO_WARN,
    STATUS_AGE_FAIL_S,
    STATUS_AGE_WARN_S,
    operator_counters,
)
from runtime.recording.ops_view import _get, _number, age_s

type Document = dict[str, object]
UNKNOWN = "unknown"


def _signal(
    name: str, source: str, threshold: str, value: object, state: str
) -> Document:
    shown = UNKNOWN if value is None else value
    return {
        "signal": name,
        "source": source,
        "threshold": threshold,
        "value": shown,
        "state": state,
    }


def _lag(value: float | None, age: float | None, complete: bool) -> str:
    if complete:
        return "ok" if value == 0 else "fail"
    if value is None or age is None:
        return UNKNOWN
    if age > STATUS_AGE_FAIL_S:
        return "fail"
    return "warn" if value > LAG_WARN or age > STATUS_AGE_WARN_S else "ok"


def _admission(source: str, a: Document) -> Document:
    name, origin = "source_admission", "source counts"
    if not a:
        return _signal(name, origin, "counts reconcile", None, UNKNOWN)
    if source == "live":
        threshold = "no refusal; lost packets and sequence gaps 0 (warn)"
        value = (
            f"captured {a.get('captured')}, published {a.get('published')}, "
            f"rejected bad_data {a.get('bad_data')} foreign "
            f"{a.get('foreign_packets')}, lost {a.get('lost_packets')}, gaps "
            f"{a.get('sequence_gaps')} (current gateway epoch)"
        )
        if a.get("refusal") is not None:
            return _signal(name, "gateway status", threshold, value, "fail")
        loss = (a.get("lost_packets"), a.get("sequence_gaps"))
        if any(not isinstance(v, int) for v in loss):
            return _signal(name, "gateway status", threshold, value, UNKNOWN)
        state = "warn" if any(cast(int, v) > 0 for v in loss) else "ok"
        return _signal(name, "gateway status", threshold, value, state)
    streams = cast(dict[str, int], a["stream_counts"])
    reasons = cast(dict[str, int], a["rejection_reasons"])
    source_n = cast(int, a["battery_source_records"])
    admitted, rejected = (
        cast(int, a[k]) for k in ("battery_admitted", "battery_rejected")
    )
    reconciled = (
        source_n == admitted + rejected
        and sum(reasons.values()) == rejected
        and sum(streams.values()) == a["bundle_events"]
    )
    value = (
        f"battery {source_n} records = {admitted} admitted + {rejected} rejected "
        f"({', '.join(f'{k} {v}' for k, v in reasons.items())}) for the whole "
        f"recording; this interval: {a['bundle_events']} events "
        f"({', '.join(f'{k.split(":")[0]} {v}' for k, v in streams.items())}); "
        f"association context: {a['battery_rejection_gaps']} battery rejection "
        f"gaps, {a['state_gaps']} state gaps (whole recording)"
    )
    return _signal(
        name,
        "prepared manifests and bundle",
        "source = admitted + rejected; every rejection has a reason",
        value,
        "ok" if reconciled else "fail",
    )


def _dispositions(source: str, flink: Document, complete: bool) -> Document:
    counters = cast(Document | None, flink.get("counters"))
    threshold = "rejected 0 (absent counts only with 0 job restarts)" + (
        f"; duplicates {DECLARED_REPEATS} at completion" if source != "live" else ""
    )
    if not counters:
        return _signal(
            "processing_dispositions",
            "Flink operator counters",
            threshold,
            None,
            UNKNOWN,
        )
    # PyFlink registers a counter at its first increment: absent is not zero.
    missing = [n for n in operator_counters(source) if n not in counters]
    value = ", ".join(f"{k} {v}" for k, v in counters.items()) + " (since job start)"
    if missing:
        value += "; not reported: " + ", ".join(missing)
    rejected, restarts = counters.get("rejected"), flink.get("restarts")
    state = "ok"
    if rejected:
        state = "fail"
    elif rejected is None and restarts != 0:
        # A rejection fails the job; only zero restarts shows none occurred.
        state = UNKNOWN
    elif (
        source != "live" and complete and counters.get("duplicate") != DECLARED_REPEATS
    ):
        state = "warn"  # restored jobs re-count only after their checkpoint
    return _signal(
        "processing_dispositions", "Flink operator counters", threshold, value, state
    )


def _input_end(
    source: str, inside: Document, health: Document, end: float | None, complete: bool
) -> Document:
    name, origin = "kafka_input_end", "broker end offset"
    threshold = (
        "equals the declared deliveries (F09) or the gateway's final count (live) "
        "at completion; running: F09 end <= declared, live end >= the count the "
        "current gateway epoch acknowledged"
    )
    declared = _get(health, "declared", "deliveries")
    if source == "live":
        declared = _get(inside, "gateway_final_published")
        acked = _get(inside, "progress", "gateway-status", "published")
        if not isinstance(declared, int):
            # The final count exists only after completion. While running, the
            # gateway reports what it acknowledged in its current epoch, written
            # every 0.5 s after the acknowledgement: the broker holds at least that.
            return _signal(
                name,
                origin,
                threshold,
                None
                if end is None
                else f"{int(end)}; current gateway epoch acknowledged "
                f"{UNKNOWN if acked is None else acked}",
                UNKNOWN
                if end is None or not isinstance(acked, int)
                else ("ok" if end >= acked else "fail"),
            )
    return _signal(
        name,
        origin,
        threshold,
        None if end is None else f"{int(end)} of {declared or UNKNOWN}",
        UNKNOWN
        if end is None or not isinstance(declared, int)
        else (
            "ok" if end == declared or (not complete and end <= declared) else "fail"
        ),
    )


def evaluate(snap: Document, health: Document) -> list[Document]:
    source = str(health.get("source"))
    inside = cast(Document, snap.get("inside") or {})
    complete = _get(inside, "markers", "serving-complete") is True
    end = _number(inside, "kafka", "input_end")
    archived = _number(inside, "progress", "archive-status", "input_next")
    served = _number(inside, "progress", "serving-status", "input_archived")
    rows = [_admission(source, cast(Document, health.get("admission") or {}))]
    rows.append(
        _dispositions(source, cast(Document, health.get("flink") or {}), complete)
    )
    physical = _number(inside, "sql", "physical_rows")
    logical = _number(inside, "sql", "distinct_inputs")
    ratio = None if not physical or not logical else round(physical / logical, 3)
    rows.append(
        _signal(
            "sql_repeats",
            "SQL facts",
            f"physical/logical <= {REPEAT_RATIO_WARN} (warn); conflicts in run health",
            None
            if ratio is None
            else f"{int(physical or 0)} rows / {int(logical or 0)} facts = {ratio}",
            UNKNOWN
            if ratio is None
            else ("ok" if ratio <= REPEAT_RATIO_WARN else "warn"),
        )
    )
    rows.append(_input_end(source, inside, health, end, complete))
    archive_age = age_s(snap, "archive-status")
    rows.append(
        _signal(
            "archive_coverage",
            "archive progress vs broker end",
            f"complete: lag 0; running: lag <= {LAG_WARN} and status <= "
            f"{STATUS_AGE_WARN_S:g} s (warn), status > {STATUS_AGE_FAIL_S:g} s (fail)",
            None
            if end is None or archived is None
            else f"{int(archived)}/{int(end)} archived, lag {int(end - archived)}",
            _lag(
                None if end is None or archived is None else end - archived,
                archive_age,
                complete and archived is not None,
            ),
        )
    )
    serving_age = age_s(snap, "serving-status")
    rows.append(
        _signal(
            "serving_coverage",
            "serving progress vs archive",
            "as archive_coverage, against the archived prefix",
            None
            if archived is None or served is None
            else f"{int(served)}/{int(archived)} served, lag {int(archived - served)}",
            _lag(
                None if archived is None or served is None else archived - served,
                serving_age,
                complete,
            ),
        )
    )
    job = cast(Document, _get(snap, "flink", "job") or {})
    failed, latest = job.get("failed"), _number(job, "latest_age_s")
    rows.append(
        _signal(
            "checkpoints",
            "Flink REST",
            f"failed <= {EXPECTED_CHECKPOINT_FAILURES} (submission trigger), else "
            f"warn; latest > {CHECKPOINT_AGE_FAIL_S:g} s fail",
            None
            if not job
            else f"completed {job.get('completed')}, failed "
            f"{failed}, latest age {latest} s",
            UNKNOWN
            if not isinstance(failed, int) or latest is None
            else "fail"
            if latest > CHECKPOINT_AGE_FAIL_S
            else ("ok" if failed <= EXPECTED_CHECKPOINT_FAILURES else "warn"),
        )
    )
    restarts = _get(health, "flink", "restarts")
    rows.append(
        _signal(
            "job_restarts",
            "Flink REST numRestarts",
            "0 ok; > 0 warn (recovered); no running job fail",
            restarts,
            "fail"
            if not job
            and isinstance(snap.get("flink"), dict)
            and "error" not in cast(Document, snap["flink"])
            else UNKNOWN
            if not isinstance(restarts, int)
            else ("ok" if restarts == 0 else "warn"),
        )
    )
    rows += _kafka(snap, health)
    rows += _resources(cast(Document, health.get("resources") or {}))
    rows += _quality(health)
    return rows


def _kafka(snap: Document, health: Document) -> list[Document]:
    unavailable = _get(health, "kafka", "unavailable")
    healthy = _get(snap, "containers", "kafka", "health") == "healthy"
    identity = _get(snap, "inside", "kafka", "identity_ok") is True
    groups = cast(dict[str, int] | None, _get(health, "kafka", "groups"))
    lag = max(groups.values()) if groups else None
    size = _get(health, "kafka", "topic_bytes")
    return [
        _signal(
            "kafka_broker",
            "healthcheck, topic IDs, unavailable partitions",
            "healthy, IDs unchanged, 0 unavailable partitions",
            f"healthy {healthy}, IDs unchanged {identity}, unavailable "
            f"{UNKNOWN if unavailable is None else unavailable}, run topics "
            f"{UNKNOWN if size is None else size} bytes",
            UNKNOWN
            if unavailable is None
            else ("ok" if healthy and identity and unavailable == 0 else "fail"),
        ),
        _signal(
            "kafka_group_lag",
            "kafka-consumer-groups",
            f"max lag <= {LAG_WARN} (warn); committed per checkpoint",
            None
            if groups is None
            else ", ".join(f"{k} {v}" for k, v in groups.items())
            or "no committed run group",
            UNKNOWN if lag is None else ("ok" if lag <= LAG_WARN else "warn"),
        ),
        _signal(
            "kafka_broker_metrics",
            "none (no JMX exporter in the profile)",
            "not measured",
            None,
            UNKNOWN,
        ),
    ]


def _resources(r: Document) -> list[Document]:
    containers = cast(list[Document] | None, r.get("containers"))
    rows = []
    if containers:
        memory = [
            (c["service"], c["memory_pct"])
            for c in containers
            if isinstance(c.get("memory_pct"), float)
        ]
        cpu = [
            (c["service"], c["cpu_budget_pct"])
            for c in containers
            if isinstance(c.get("cpu_budget_pct"), float)
        ]
        top_m = max(memory, key=lambda x: cast(float, x[1])) if memory else None
        top_c = max(cpu, key=lambda x: cast(float, x[1])) if cpu else None
        peak_m = None if top_m is None else cast(float, top_m[1])
        peak_c = None if top_c is None else cast(float, top_c[1])
        limits = sum(cast(int, c["memory_limit"] or 0) for c in containers)
        engine = r.get("engine_memory")
    else:
        top_m = top_c = peak_m = peak_c = engine = None
        limits = 0
    rows.append(
        _signal(
            "memory",
            "docker stats",
            f"< {MEMORY_WARN:g}% of limit ok, < {MEMORY_FAIL:g}% warn, else fail",
            None if top_m is None else f"peak {top_m[1]}% ({top_m[0]})",
            UNKNOWN
            if peak_m is None
            else "ok"
            if peak_m < MEMORY_WARN
            else "warn"
            if peak_m < MEMORY_FAIL
            else "fail",
        )
    )
    rows.append(
        _signal(
            "cpu",
            "docker stats",
            f"< {CPU_WARN:g}% of CPU budget ok, else warn",
            None if top_c is None else f"peak {top_c[1]}% of budget ({top_c[0]})",
            UNKNOWN if peak_c is None else "ok" if peak_c < CPU_WARN else "warn",
        )
    )
    rows.append(
        _signal(
            "memory_budget",
            "docker inspect, docker info",
            "sum of running limits <= engine memory",
            None
            if not isinstance(engine, int)
            else f"{limits >> 20} MiB of {engine >> 20} MiB",
            UNKNOWN
            if not isinstance(engine, int) or not limits
            else "ok"
            if limits <= engine
            else "fail",
        )
    )
    disk = cast(Document | None, r.get("disk"))
    free = None if not disk else cast(int, disk["available"])
    rows.append(
        _signal(
            "disk_free",
            "df on the Docker disk; free space on the host disk",
            f">= 2 complete runs ({2 * FULL_RUN_BYTES >> 20} MiB) on both ok, "
            ">= 1 warn, else fail",
            None
            if free is None
            else f"{free >> 20} MiB free (Docker "
            f"{cast(int, cast(Document, disk)['docker_available']) >> 20} MiB, host "
            f"{cast(int, cast(Document, disk)['host_available']) >> 20} MiB)",
            UNKNOWN
            if free is None
            else "ok"
            if free >= 2 * FULL_RUN_BYTES
            else "warn"
            if free >= FULL_RUN_BYTES
            else "fail",
        )
    )
    return rows


def _quality(health: Document) -> list[Document]:
    inside = cast(Document, health.get("inside") or {})
    rows = cast(list[Document] | None, inside.get("quality"))
    if not rows:
        return [
            _signal(
                "quality",
                "SQL run health",
                "every check 0 violations",
                inside.get("quality_error"),
                UNKNOWN,
            )
        ]
    return [
        _signal(
            f"quality.{r['check_name']}",
            "SQL run health",
            "0 violations",
            r["violations"],
            str(r["state"]),
        )
        for r in rows
    ]


def render(rows: list[Document]) -> str:
    lines = ["Health      signal / state / value"]
    for row in rows:
        lines.append(f"  {row['signal']:36} {row['state']:7} {row['value']}")
    return "\n".join(lines)
