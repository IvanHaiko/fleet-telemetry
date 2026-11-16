"""Final evidence run of roadmap step 6: one run without faults (ADR-0056).

Three commands, each against a run ID that `ops` has never used:

- `declare`: write the criterion draft `.local-discovery/<run>-criterion-draft.json`
  and start nothing. The maintainer approves or changes it;
- `run`: require the approved draft, write `criterion.json`, then `ops start`,
  sample resources every `--sample` seconds, save the health signals at the
  mid-run trigger (`health-midrun.json`) and after completion
  (`health-final.json`), run `ops verify`, and leave the profile running for
  the signed-in dashboard check;
- `evaluate`: after the dashboard check wrote `dashboard-check.json` and
  `ops stop` collected the run, judge every condition and write `result.json`.

A failed condition is reported, never retried; output holds counts, states,
sizes and times only.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from runtime.recording import ops
from runtime.recording.evidence import write
from runtime.recording.fault_analysis import evaluate as visibility
from runtime.recording.health import FULL_RUN_BYTES, sample, size_bytes
from runtime.recording.ops_view import snapshot
from runtime.recording.profile import PROJECT, Document, Profile, RunFailure, require

ALLOWED = {"kafka_broker_metrics": {"unknown"}, "cpu": {"ok", "warn"}}
ALLOWED["memory"] = {"ok", "warn"}
VOLUMES = ("archive-data", "evidence", "grafana-data", "kafka-data", "serving-data")
CONDITIONS = [
    "ops start reaches readiness within the start timeout (every readiness check "
    "of the runbook passes over the readiness window)",
    "mid-run health (at the trigger) and final health (after serving-complete): "
    "every signal is ok, except kafka_broker_metrics, which is unknown, and cpu "
    "and memory, which are ok or warn",
    "ops verify passes with every check true",
    "resource samples: from ops start returning to serving-complete, no gap "
    "between consecutive samples exceeds the gap limit; every sample lists "
    "memory bytes and limit for every running service container and the size "
    "of every profile volume; no container reaches 95 % of its memory limit",
    "SQL visibility (observer, 2 s samples): every expected fact is observed and "
    "no fact's acknowledgement-to-visibility interval exceeds the visibility limit",
    "disk: the profile volumes grow by at most the run budget between the first "
    "and the last sample, and the run directory on the host stays within it",
    "dashboard, signed in, with the profile still running after completion: "
    "datasource Save & test reports working; every panel query sent at once in 5 "
    "rounds returns no error; every panel renders without an error mark or "
    "'No data'; Run health lists every check as ok; F09: the map panel draws one "
    "point per native second of the flight plus the last position; live: "
    "Connection showed observed during the session",
    "ops stop collects a completed manifest with health.json and an inventory; "
    "every profile volume still exists",
]


def criterion(args: argparse.Namespace) -> Document:
    document: Document = {
        "run_id": args.run_id,
        "source": args.source,
        "scenario": "one run without faults: ops start, mid-run and final health, "
        "ops complete, ops verify, signed-in dashboard check, ops stop",
        "trigger": f"producer acknowledged >= {args.trigger}"
        if args.source == "f09"
        else f"{args.trigger} s after ops start returned",
        "readiness_window_s": args.window,
        "start_timeout_s": args.timeout,
        "sample_s": args.sample,
        "sample_gap_limit_s": 30.0,
        "visibility_limit_s": 15.0,
        "run_disk_budget_bytes": FULL_RUN_BYTES,
        "conditions": CONDITIONS,
        "not_judged": "capture-to-browser latency (computed as SQL visibility + "
        "one sample + the 5 s refresh + the slowest concurrent panel query, not "
        "measured); Kafka broker metrics; any fault",
    }
    if args.source == "f09":
        document["interval_us"] = [args.start_us, args.end_us]
    else:
        document["session_s"] = args.session_s
    return document


def draft_path(run_id: str) -> Path:
    return ops.scope(run_id)[0].with_name(run_id + "-criterion-draft.json")


def declare(args: argparse.Namespace) -> Document:
    require(not ops.scope(args.run_id)[0].exists(), "run_scope_exists")
    write(draft_path(args.run_id), criterion(args) | {"declared_utc": None})
    return {"run_id": args.run_id, "status": "declared"}


class Sampler(threading.Thread):
    """Resource samples on a fixed cadence for the whole run (ADR-0056)."""

    def __init__(self, run: Profile, every: float) -> None:
        super().__init__(daemon=True)
        self.run_profile, self.every = run, every
        self.stopped = threading.Event()

    def run(self) -> None:
        while not self.stopped.is_set():
            began = time.monotonic()
            sample(self.run_profile)
            self.stopped.wait(max(0.0, self.every - (time.monotonic() - began)))


def _wait(until: float, reached: Callable[[], bool]) -> None:
    while not reached():
        require(time.monotonic() < until, "trigger_timeout")
        time.sleep(5)


def run(args: argparse.Namespace) -> Document:
    draft = json.loads(draft_path(args.run_id).read_text())
    draft.pop("declared_utc", None)
    require(draft == criterion(args), "criterion_differs_from_approved_draft")
    out = ops.scope(args.run_id)[0]
    out.mkdir()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write(out / "criterion.json", criterion(args) | {"declared_utc": stamp})
    # Until start returns, its readiness loop samples; then this thread does.
    ops.start(args)
    profile, plan = ops.load(args.run_id)
    returned = time.monotonic()
    sampler = Sampler(profile, args.sample)
    sampler.start()
    try:

        def triggered() -> bool:
            if args.source == "live":
                return bool(time.monotonic() - returned >= args.trigger)
            _, status = profile.read_state("producer-status.json")
            acknowledged = cast(int, (status or {}).get("acknowledged", 0))
            return bool(acknowledged >= args.trigger)

        deadline = returned + args.timeout_complete
        _wait(deadline, triggered)
        midrun = ops.health_of(profile, plan, snapshot(profile))
        write(out / "health-midrun.json", midrun)
        if args.source == "live":
            _wait(deadline, lambda: time.monotonic() - returned >= args.session_s)
        ops.complete(
            argparse.Namespace(
                run_id=args.run_id, timeout=args.timeout_complete, sample=0.0
            )
        )
    finally:
        sampler.stopped.set()
        sampler.join(timeout=120)
    final = ops.health_of(profile, plan, snapshot(profile))
    write(out / "health-final.json", final)
    verified = ops.verify(args)
    return {
        "run_id": args.run_id,
        "status": "awaiting_dashboard_check",
        "verify": verified["status"],
    }


def _states_pass(path: Path) -> bool:
    signals = cast(list[Document], json.loads(path.read_text())["signals"])
    return all(r["state"] in ALLOWED.get(str(r["signal"]), {"ok"}) for r in signals)


def _resources(out: Path, criterion_doc: Document) -> tuple[bool, Document]:
    events = [json.loads(x) for x in (out / "events.jsonl").read_text().splitlines()]
    ready = next(e["host_ms"] for e in events if e["event"] == "ready")
    done = next(e["host_ms"] for e in events if e["event"] == "serving_complete")
    rows = [json.loads(x) for x in (out / "resources.jsonl").read_text().splitlines()]
    window = [r for r in rows if ready - 30_000 <= r["host_ms"] <= done + 30_000]
    times = [r["host_ms"] for r in window]
    gaps = [(b - a) / 1000 for a, b in zip(times, times[1:], strict=False)]
    complete = bool(window) and all(
        set(r.get("volumes") or {}) >= {*VOLUMES, "state"}
        and r.get("containers")
        and all(
            c.get("memory_bytes") and c.get("memory_limit") for c in r["containers"]
        )
        for r in window
    )
    peaks: dict[str, Document] = {}
    for r in window:
        for c in r.get("containers") or []:
            peak = peaks.setdefault(
                c["service"],
                {
                    "bytes": 0,
                    "pct": 0.0,
                    "limit": c.get("memory_limit"),
                    "cpu_pct": 0.0,
                },
            )
            peak["bytes"] = max(cast(int, peak["bytes"]), c.get("memory_bytes") or 0)
            peak["pct"] = max(cast(float, peak["pct"]), c.get("memory_pct") or 0.0)
            cpu = c.get("cpu_budget_pct") or 0.0
            peak["cpu_pct"] = max(cast(float, peak["cpu_pct"]), cpu)
    total = [
        sum(size_bytes(str(v)) or 0 for v in r["volumes"].values())
        for r in window
        if r.get("volumes")
    ]
    growth = total[-1] - total[0] if total else None
    limit = cast(float, criterion_doc["sample_gap_limit_s"])
    passed = (
        bool(gaps)
        and max(gaps) <= limit
        and complete
        and all(cast(float, p["pct"]) < 95.0 for p in peaks.values())
    )
    return passed, {
        "samples": len(window),
        "max_gap_s": max(gaps, default=None),
        "fields_complete": complete,
        "peaks": peaks,
        "volume_growth_bytes": growth,
    }


def evaluate(args: argparse.Namespace) -> Document:
    out = ops.scope(args.run_id)[0]
    doc = json.loads((out / "criterion.json").read_text())
    events = [json.loads(x) for x in (out / "events.jsonl").read_text().splitlines()]
    plan = json.loads((out / "ops.json").read_text())
    verify = json.loads(sorted(out.glob("verify-*.json"))[-1].read_text())
    resources_ok, resources = _resources(out, doc)
    expected = cast(int, plan.get("expected") or 0)
    samples = [
        json.loads(x)
        for x in (out / "observe.jsonl").read_text().splitlines()
        if x.strip()
    ]
    if not expected:
        expected = len({o for s in samples for o in (s.get("new") or [])})
    seen = visibility(samples, [], expected, doc["visibility_limit_s"], 3600.0)
    run_bytes = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    dashboard = json.loads((out / "dashboard-check.json").read_text())
    stops = sorted((out / "evidence").glob("*-stop"))
    manifest = json.loads((stops[-1] / "manifest.json").read_text()) if stops else {}
    listing = Profile(args.run_id, out, out).docker("volume", "ls", "-q").split()
    budget = cast(int, doc["run_disk_budget_bytes"])
    checks = {
        "ready": any(e["event"] == "ready" for e in events),
        "health": _states_pass(out / "health-midrun.json")
        and _states_pass(out / "health-final.json"),
        "verify": verify["status"] == "passed",
        "resources": resources_ok,
        "visibility": bool(seen["pass_visibility"]),
        "disk": resources["volume_growth_bytes"] is not None
        and cast(int, resources["volume_growth_bytes"]) <= budget
        and run_bytes <= budget,
        "dashboard": all(
            v is True for v in cast(Document, dashboard["checks"]).values()
        ),
        "stop": manifest.get("completion") == "completed"
        and bool(stops)
        and (stops[-1] / "health.json").exists()
        and all(f"{PROJECT}_{v}" in listing for v in (*VOLUMES, "state")),
    }
    vis = cast(Document, seen["visibility_outside_windows_s"])
    query_ms = cast(float, dashboard.get("max_concurrent_query_ms") or 0) / 1000
    result: Document = {
        "run_id": args.run_id,
        "status": "passed" if all(checks.values()) else "failed_criterion",
        "checks": checks,
        "resources": resources,
        "visibility_s": vis,
        "run_directory_bytes": run_bytes,
        "browser_latency_bound_s": None
        if vis.get("max") is None
        else round(cast(float, vis["max"]) + 2.0 + 5.0 + query_ms, 1),
        "dashboard": dashboard,
    }
    write(out / "result.json", result)
    return {"run_id": args.run_id, "status": result["status"], "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("declare", "run", "evaluate"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source", choices=("f09", "live"), default="f09")
    parser.add_argument("--start-us", type=int, default=0)
    parser.add_argument("--end-us", type=int, default=2_436_000_000)
    parser.add_argument("--trigger", type=int, default=20_000)
    parser.add_argument("--session-s", type=float, default=300.0)
    parser.add_argument("--window", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--timeout-complete", type=float, default=3600.0)
    parser.add_argument("--sample", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        commands = {"declare": declare, "run": run, "evaluate": evaluate}
        result = commands[args.command](args)
    except (RunFailure, OSError, ValueError, KeyError, StopIteration) as error:
        category = str(error) if isinstance(error, RunFailure) else type(error).__name__
        print(
            json.dumps(
                {"command": args.command, "status": "failed", "category": category}
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") != "failed_criterion" else 1


if __name__ == "__main__":
    raise SystemExit(main())
