"""Run one live PX4 SITL session on the recording profile with declared drills.

Host-side orchestration for ADR-0054, with the standard library and the Docker
CLI only. One invocation:

1. prepares a fresh private scope (live_prepare.py);
2. writes `criterion.json` with the drill schedule and every limit before any
   service starts;
3. starts the profile with the live services, initializes, submits the Flink
   job and starts the observer, the archive and serving workers, the gateway
   and the simulator, whose MAVLink stream is pointed at the gateway;
4. pauses the simulator (source silence), restarts the gateway, and completes
   the session at the declared times;
5. waits for serving completion, reconciles capture, archive and SQL, rebuilds
   the facts from the archive and evaluates the observer samples;
6. writes `result.json` and stops the profile without removing any volume.

No arming, takeoff, mission or other flight command is sent. Output holds
counts, digests, times and states only; no coordinates or credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import cast

from runtime.recording.fault_actions import flink_evidence
from runtime.recording.fault_analysis import evaluate
from runtime.recording.live_prepare import prepare_live
from runtime.recording.profile import (
    PROJECT,
    ROOT,
    Document,
    Profile,
    RunFailure,
    require,
)

LIVE_WORKERS = ("live-archive-worker", "live-serving-worker", "live-gateway")
SITL = "px4-sitl"
# Receipt and health limit of live_state (ADR-0054), plus sampling margin.
LIVE_LIMIT_S = 3.0
STREAMS = (("GLOBAL_POSITION_INT", "5"), ("SYS_STATUS", "1"))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True
    ).stdout


def declare(args: argparse.Namespace, out: Path) -> Document:
    """Write the criterion before any service starts; it is never rewritten."""
    patch = git("diff", "HEAD")
    (out / "working.patch").write_text(patch, encoding="utf-8", newline="\n")
    margin = LIVE_LIMIT_S + 2 * args.interval
    criterion: Document = {
        "run_id": args.run_id,
        "declared_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_run": True,
        "code_revision": git("rev-parse", "HEAD").strip(),
        "working_patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "source": "one fresh PX4 SITL, SIH quadrotor; no flight command is sent",
        "mavlink_stream": "minimal mode at 4000 B/s, "
        + ", ".join(f"{name} {rate} Hz" for name, rate in STREAMS)
        + ", HEARTBEAT 1 Hz",
        "schedule_s_after_first_publication": {
            "source_silence": [args.silence_at, args.silence_at + args.silence_s],
            "gateway_down": [args.restart_at, args.restart_at + args.restart_down_s],
            "complete": args.end_at,
        },
        "observer": "one container in the archive namespace, one clock, "
        f"samples every {args.interval} s",
        "visibility_limit_s": args.visibility_limit,
        "visibility_scope": "position facts whose publication-to-visibility "
        "interval lies outside both drill windows",
        "drill_recovery_limit_s": args.recovery_limit,
        "drill_recovery_scope": "catch-up from the resume action to the first "
        "sample at which every fact published before the drill and one published "
        "after the resume are SQL-visible and none pending is older than the "
        "visibility limit; the drill length itself is declared, not judged",
        "terminal_drain_limit_s": args.drain_limit,
        "live_state": {
            "silence": "every sample from pause + "
            f"{margin:g} s to the resume shows connection 'stale' and no position",
            "gateway_down": f"every sample from stop + {margin:g} s to the "
            "restart shows connection 'unknown' and no position",
            "steady": f"at least {args.observed_fraction:.0%} of samples outside "
            "the drill windows (with the same margin) show 'observed'",
        },
        "correctness": [
            "every acknowledged event matches a captured packet marked published",
            "no MAVLink sequence gap inside a gateway epoch (detectable loss)",
            "archived deliveries equal the published count",
            "SQL fact hash set equals the archive-only LiveRuntime rebuild",
            "zero logical repeats: distinct identities = DISTINCT view rows = "
            "rebuilt facts, no conflicting content",
            "no battery or state event carries measurement time",
            "every position's battery and state status equals what input order "
            "implies: none before a first receipt, unknown_after_restart after a "
            "gateway restart until that stream's first new receipt, then fresh or "
            "stale; the restart shows unknown_after_restart at least once",
            "no operator refusal in any job's exception history",
        ],
        "coverage": "a sample gap above 10 s leaves the run unestablished",
    }
    with (out / "criterion.json").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(criterion, indent=2) + "\n")
    return criterion


def launch(run: Profile, args: argparse.Namespace) -> None:
    """Job, observer, workers, gateway, then the simulator and its stream."""
    job = run.submit()
    run.wait(lambda: run.job_running(job), 180, "job_not_running")
    run.log("job_running", job=job)
    run.start_observer(0, args.interval)
    run.docker(
        *run.compose,
        *"up -d --no-deps live-archive-worker live-serving-worker".split(),
    )
    run.wait(
        lambda: run.read_state("serving-status.json")[1] is not None,
        300,
        "serving_not_ready",
    )
    run.docker(*run.compose, *"up -d --no-deps live-gateway".split())
    run.wait(
        lambda: (
            (run.read_state("gateway-status.json")[1] or {}).get("status") == "running"
        ),
        120,
        "gateway_not_ready",
    )
    run.docker(*run.compose, *"up -d --no-deps px4-sitl".split())
    networks = cast(
        dict[str, Document],
        cast(Document, run.inspect(run.container("archive"))["NetworkSettings"])[
            "Networks"
        ],
    )
    address = str(networks[f"{PROJECT}_live-source"]["IPAddress"])
    require(re.fullmatch(r"[0-9.]{7,15}", address), "live_source_address")
    time.sleep(10)  # PX4 starts its modules before it accepts a new stream
    # A declared, modest stream: the minimal set plus position at 5 Hz and the
    # battery summary at 1 Hz; HEARTBEAT is always sent at 1 Hz.
    mavlink = ("exec", run.container(SITL), "/opt/px4/bin/px4-mavlink")
    run.docker(
        *mavlink,
        *("start", "-u", "14620", "-o", "14560", "-t", address, "-m", "minimal"),
        *("-r", "4000"),
        timeout=60,
    )
    for name, rate in STREAMS:
        run.docker(*mavlink, "stream", "-u", "14620", "-s", name, "-r", rate)
    run.wait(
        lambda: (run.read_state("gateway-status.json")[1] or {}).get("published", 0),
        120,
        "no_live_publication",
    )
    run.log("live_publishing")


def watch(run: Profile, allowed: set[str]) -> None:
    for service in (*LIVE_WORKERS, SITL):
        state = run.state(service)
        if service in allowed or state["Status"] == "running":
            continue
        if state["Status"] == "paused" and service == SITL and SITL in allowed:
            continue
        raise RunFailure(f"{service}_{state['Status']}_{state['ExitCode']}")
    require(not any(j.get("state") == "FAILED" for j in run.jobs()), "flink_job_failed")


def schedule(run: Profile, args: argparse.Namespace) -> list[Document]:
    """Source silence, gateway restart and completion at the declared times."""
    began = time.monotonic()
    drills: list[Document] = []

    def until(seconds: float, allowed: set[str]) -> None:
        while time.monotonic() - began < seconds:
            watch(run, allowed)
            time.sleep(1)

    until(args.silence_at, set())
    start = run.clock()
    run.docker("pause", run.container(SITL))
    until(args.silence_at + args.silence_s, {SITL})
    run.docker("unpause", run.container(SITL))
    drills.append(
        {
            "name": "source-silence",
            "kind": "source-silence",
            "start_ms": start,
            "resume_ms": run.clock(),
            "recovery_limit_s": args.recovery_limit,
        }
    )
    run.log("drill_done", name="source-silence")
    until(args.restart_at, set())
    start = run.clock()
    run.docker("stop", run.container("live-gateway"), timeout=120)
    require(run.state("live-gateway")["ExitCode"] == 0, "gateway_unclean_stop")
    until(args.restart_at + args.restart_down_s, {"live-gateway"})
    run.docker("start", run.container("live-gateway"))
    drills.append(
        {
            "name": "gateway-restart",
            "kind": "gateway-restart",
            "start_ms": start,
            "resume_ms": run.clock(),
            "recovery_limit_s": args.recovery_limit,
        }
    )
    run.log("drill_done", name="gateway-restart")
    until(args.end_at, set())
    run.docker("kill", "--signal", "USR1", run.container("live-gateway"))
    run.wait(
        lambda: run.read_state("gateway-complete.json")[1] is not None,
        60,
        "gateway_not_completed",
    )
    run.docker("stop", run.container(SITL), timeout=60)
    run.wait(
        lambda: run.read_state("serving-complete.json")[1] is not None,
        600,
        "serving_not_completed",
    )
    run.log("serving_complete")
    return drills


def live_checks(
    samples: list[Document], drills: list[Document], args: argparse.Namespace
) -> Document:
    """Connection states the live view showed during and outside the drills."""
    margin = int((LIVE_LIMIT_S + 2 * args.interval) * 1000)

    def window(name: str) -> list[Document]:
        drill = next(d for d in drills if d["name"] == name)
        low = cast(int, drill["start_ms"]) + margin
        return [
            s
            for s in samples
            if low <= cast(int, s["t_ms"]) <= cast(int, drill["resume_ms"])
        ]

    def shown(sample: Document) -> Document:
        return cast(Document, sample.get("live") or {})

    silence, down = window("source-silence"), window("gateway-restart")
    observed_from = next(
        (s["t_ms"] for s in samples if shown(s).get("connection") == "observed"), None
    )
    completed = next(
        (s["t_ms"] for s in samples if s.get("producer") == "completed"), None
    )
    steady = [
        s
        for s in samples
        if observed_from is not None
        and cast(int, observed_from) <= cast(int, s["t_ms"])
        and (completed is None or cast(int, s["t_ms"]) < cast(int, completed))
        and not any(
            cast(int, d["start_ms"])
            <= cast(int, s["t_ms"])
            <= cast(int, d["resume_ms"]) + margin
            for d in drills
        )
    ]
    observed = sum(shown(s).get("connection") == "observed" for s in steady)
    fraction = observed / len(steady) if steady else 0.0
    return {
        "silence_samples": len(silence),
        "silence_all_stale": len(silence) >= 3
        and all(
            shown(s).get("connection") == "stale" and not shown(s).get("position_shown")
            for s in silence
        ),
        "gateway_down_samples": len(down),
        "gateway_down_all_unknown": len(down) >= 2
        and all(
            shown(s).get("connection") == "unknown"
            and not shown(s).get("position_shown")
            for s in down
        ),
        "steady_samples": len(steady),
        "steady_observed_fraction": round(fraction, 4),
        "steady_pass": fraction >= args.observed_fraction,
    }


def assess(run: Profile, args: argparse.Namespace, drills: list[Document]) -> Document:
    flink = flink_evidence(run)
    (run.out / "flink.json").write_text(json.dumps(flink, indent=1))
    reconcile = run.worker("live_reconcile", timeout=900)
    (run.out / "reconcile.json").write_text(json.dumps(reconcile, indent=1))
    samples = [
        cast(Document, json.loads(line))
        for line in (run.out / "observe.jsonl").read_text().splitlines()
    ]
    expected = cast(int, reconcile["rebuilt_facts"])
    timing = evaluate(
        samples, drills, expected, args.visibility_limit, args.drain_limit
    )
    live = live_checks(samples, drills, args)
    capture = cast(Document, reconcile["capture"])
    restart = cast(Document, reconcile["restart"])
    correctness: Document = {
        "capture_covered": capture["covered"],
        "no_capture_loss": capture["lost_packets"] == 0,
        "archive_equals_published": reconcile["archived_deliveries"]
        == (run.read_state("gateway-complete.json")[1] or {}).get("published"),
        "fact_hash_sets_equal": reconcile["fact_hash_sets_equal"],
        "zero_logical_repeats": reconcile["zero_logical_repeats"],
        "untimed_without_time": reconcile["untimed_without_time"],
        "restart_unknown_exercised": restart["restart_exercised"],
        "statuses_match_receipt_order": restart["statuses_match_receipt_order"],
        "no_operator_refusal": all(
            j["operator_refusals"] == 0 for j in cast(list[Document], flink["jobs"])
        ),
    }
    passed = (
        all(v is True for v in correctness.values())
        and timing["coverage_established"]
        and timing["pass_visibility"]
        and timing["pass_drain"]
        and timing["pass_recovery"]
        and live["silence_all_stale"]
        and live["gateway_down_all_unknown"]
        and live["steady_pass"]
    )
    return {
        "run_id": args.run_id,
        "status": "passed" if passed else "failed_criterion",
        "drills": drills,
        "timing": timing,
        "live_state": live,
        "correctness": correctness,
        "positions": expected,
        "physical_rows": reconcile["physical_rows"],
        "archived_deliveries": reconcile["archived_deliveries"],
    }


def execute(args: argparse.Namespace) -> int:
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{2,39}", args.run_id), "run_id")
    require(
        0 < args.silence_at
        and args.silence_at + args.silence_s < args.restart_at
        and args.restart_at + args.restart_down_s + 30 < args.end_at <= 1500,
        "schedule_order",
    )
    out = (ROOT / ".local-discovery" / args.run_id).resolve()
    private = ROOT / ".local-discovery" / f"recording-private-{args.run_id}"
    require(not out.exists() and not private.exists(), "run_scope_exists")
    out.mkdir()
    run = Profile(args.run_id, out, private, profiles=("run", "live"))
    prepare_live(args.run_id, private)
    declare(args, out)
    run.log("criterion_declared")
    result: Document = {"run_id": args.run_id, "status": "failed"}
    try:
        containers = cast(dict[str, str], run.status()["containers"])
        busy = [n for n, s in containers.items() if s == "running" and "worker" in n]
        require(not busy, "workers_busy")
        run.start()
        summary = run.worker("live_initialize")
        (out / "initialize.json").write_text(json.dumps(summary, indent=1))
        launch(run, args)
        drills = schedule(run, args)
        result = assess(run, args, drills)
    except (
        RunFailure,
        subprocess.SubprocessError,
        OSError,
        ValueError,
        KeyError,
    ) as error:
        result["error"] = (
            str(error) if isinstance(error, RunFailure) else type(error).__name__
        )
        run.log("run_failed", category=result["error"])
    finally:
        if not args.keep_running:
            run.docker(*run.compose, "stop", *LIVE_WORKERS, SITL, check=False)
            run.stop()
        with (out / "result.json").open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"run_id": args.run_id, "status": result["status"]}))
    return 0 if result["status"] == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--silence-at", type=float, default=180)
    parser.add_argument("--silence-s", type=float, default=30)
    parser.add_argument("--restart-at", type=float, default=360)
    parser.add_argument("--restart-down-s", type=float, default=15)
    parser.add_argument("--end-at", type=float, default=600)
    parser.add_argument("--visibility-limit", type=float, default=5)
    parser.add_argument("--recovery-limit", type=float, default=30)
    parser.add_argument("--drain-limit", type=float, default=30)
    parser.add_argument("--observed-fraction", type=float, default=0.9)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--keep-running", action="store_true")
    args = parser.parse_args(argv)
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
