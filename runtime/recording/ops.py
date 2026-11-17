"""Operate one run of the single-machine recording profile: replay or live SITL.

A replay source is a registered recording key (f09, f07, f03; ADR-0057) or,
with `--source-file`, any original a mapping profile admits (ADR-0058); a file
it refuses stays inspectable with `python -m telemetry.ulog_inventory`.

Commands (run from the repository root on the host):

- `start`: prepare a fresh scope, start the profile and its workers and source,
  then return only when every readiness check passes over the declared window;
- `status`: one screen of components, progress, ages, lags and the readiness
  checks; anything not measured is `unknown`;
- `collect`: save the run's operational evidence (runtime/recording/evidence.py);
- `stop`: collect, then cancel the run's job and stop the containers. Volumes,
  topics, checkpoints, archive objects and tables are never removed;
- `resume`: restart the profile after a stop or a host shutdown: resubmit the
  job from the newest retained checkpoint, continue the workers from their
  cursors and the source (F09 publisher from its ledger, a new gateway epoch),
  then require readiness and a fact that was not acknowledged before it;
- `complete`: end a live session, or wait for an F09 replay to finish;
- `verify`: reconcile SQL with the reference or the archive-only recomputation,
  and for F09 rebuild from the archive into a separate database;
- `view`: serve a stored run's dashboard (storage, SQL and Grafana only) and
  make its datasource able to read the run.

The run's settings stay in `.local-discovery/<run>/ops.json`; every step is
logged to `events.jsonl` there. Output holds counts, states and times only.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import cast

from runtime.recording.admission import prepare_admitted
from runtime.recording.evidence import collect, probe, write
from runtime.recording.fault_run import RECORDING_INPUTS, git, prepare_inputs
from runtime.recording.health import measure as measure_health
from runtime.recording.health import sample
from runtime.recording.health_signals import evaluate as signals
from runtime.recording.health_signals import render as render_signals
from runtime.recording.live_prepare import prepare_live
from runtime.recording.live_run import launch as launch_live
from runtime.recording.ops_verify import verify_run
from runtime.recording.ops_view import evaluate, render, snapshot
from runtime.recording.profile import (
    PROJECT,
    ROOT,
    Document,
    Profile,
    RunFailure,
    require,
)
from runtime.recording.stall import explain
from runtime.recording.stall import render as render_why
from runtime.recording.stored_view import view
from telemetry.admission import AdmissionRefused


def scope(run_id: str) -> tuple[Path, Path]:
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{2,39}", run_id), "run_id")
    out = (ROOT / ".local-discovery" / run_id).resolve()
    return out, ROOT / ".local-discovery" / f"recording-private-{run_id}"


def load(run_id: str, suffix: str = "") -> tuple[Profile, Document]:
    out, private = scope(run_id)
    require((out / "ops.json").exists(), "not_an_ops_run")
    plan = cast(Document, json.loads((out / "ops.json").read_text()))
    profiles = tuple(cast(list[str], plan["profiles"]))
    return Profile(
        run_id, out, private, profiles=profiles, observer_suffix=suffix
    ), plan


def ready(
    run: Profile, source: str, window: float, timeout: float, after: int | None = None
) -> Document:
    """Poll pairs of snapshots `window` apart until every check passes."""
    end = time.monotonic() + timeout
    previous = snapshot(run)
    while True:
        time.sleep(window)
        sample(run)
        current = snapshot(run)
        checks = evaluate(previous, current, source, after)
        if all(v is True for v in checks.values()):
            run.log("ready", window_s=window, checks=sorted(checks))
            return current
        if time.monotonic() > end:
            print(render(current, checks, window))
            failed = sorted(k for k, v in checks.items() if v is not True)
            run.log("not_ready", failed=failed)
            raise RunFailure("not_ready")
        previous = current


def serving_status(run: Profile, after_ms: int) -> bool:
    _, status = run.read_state("serving-status.json")
    return status is not None and cast(int, status.get("written_ms", 0)) > after_ms


def start(args: argparse.Namespace) -> Document:
    out, private = scope(args.run_id)
    # A drill may have declared its criterion in the otherwise fresh directory.
    present = {p.name for p in out.iterdir()} if out.exists() else set()
    require(present <= {"criterion.json"} and not private.exists(), "run_scope_exists")
    live = args.source == "live"
    admitted = args.source == "ulog"
    require(admitted == (args.source_file is not None), "source_file")
    if not live and not admitted:
        require(args.start_us is not None and args.end_us is not None, "interval")
    out.mkdir(exist_ok=True)
    run = Profile(
        args.run_id, out, private, profiles=("run", "live") if live else ("run",)
    )
    declared: Document = {
        "run_id": args.run_id,
        "source": args.source,
        "profiles": list(run.profiles),
        "declared_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "code_revision": git("rev-parse", "HEAD").strip(),
        "readiness_window_s": args.window,
    }
    if live:
        prepare_live(args.run_id, private)
    else:
        inputs = None
        if admitted:
            decision = prepare_admitted(
                args.source_file,
                out / "admission",
                rights=args.rights,
                reference=args.reference,
            )
            inputs = (out / "admission/inspection", args.source_file.resolve())
            declared |= {
                "label": decision["label"],
                "mapping_profile": decision["mapping_profile"],
                "source_id": decision["source_id"],
                "prepared": inputs[0].relative_to(ROOT).as_posix(),
                "original": str(inputs[1]),
            }
            # The whole file unless an interval was given.
            if args.start_us is None:
                args.start_us = 0
            if args.end_us is None:
                args.end_us = decision["native_end_us"]
        declared |= {"interval_us": [args.start_us, args.end_us]}
        declared |= prepare_inputs(args, out, private, inputs)
    write(out / "ops.json", declared)
    run.log("ops_declared", source=args.source)
    busy = [
        name
        for name, state in cast(dict[str, str], run.status()["containers"]).items()
        if state == "running" and ("worker" in name or "publisher" in name)
    ]
    require(not busy, "workers_busy")
    run.start()
    run.docker(*run.compose, "up", "-d", "grafana")
    if live:
        write(out / "initialize.json", run.worker("live_initialize"))
        args.interval = 1.0
        launch_live(run, args)
    else:
        summary = run.worker("recording_initialize")
        require(summary.get("deliveries") == declared["deliveries"], "delivery_count")
        write(out / "initialize.json", summary)
        job = run.submit()
        run.wait(lambda: run.job_running(job), 180, "job_not_running")
        run.log("job_running", job=job)
        run.start_observer(cast(int, declared["expected"]), 2.0)
        run.docker(
            *run.compose, *"up -d --no-deps archive-worker serving-worker".split()
        )
        # Serving loads the bundle and reference first (ADR-0053); wait for it.
        run.wait(lambda: serving_status(run, 0), 300, "serving_not_ready")
        run.docker(*run.compose, *"up -d --no-deps publisher".split())
    address = live_address(run) if live else None
    write(out / "ops-started.json", {"live_source_address": address})
    ready(run, args.source, args.window, args.timeout)
    return {"run_id": args.run_id, "status": "ready"}


def live_address(run: Profile) -> str:
    networks = cast(
        dict[str, Document],
        cast(Document, run.inspect(run.container("archive"))["NetworkSettings"])[
            "Networks"
        ],
    )
    return str(networks[f"{PROJECT}_live-source"]["IPAddress"])


def restore_job(run: Profile) -> Document:
    """Resubmit from the newest retained checkpoint if no job of the run runs."""
    running = [j for j in run.jobs() if j.get("state") == "RUNNING"]
    if running:
        return {"job": running[0]["jid"], "resubmitted": False}
    listing = probe(run, "checkpoints", "--run-id", run.run_id, network=False)
    points = cast(list[Document], listing.get("checkpoints") or [])
    require(points, "no_retained_checkpoint")
    path = str(points[0]["path"])
    committed = run.processing_offset()
    job = run.submit(restore=path)

    def restored() -> Document | None:
        return run.checkpoint(job, "restored") if run.job_running(job) else None

    point = cast(Document, run.wait(restored, 240, "restore_timeout"))
    row: Document = {
        "job": job,
        "resubmitted": True,
        "checkpoint": path,
        "retained_checkpoints": len(points),
        "restored_id": point.get("id"),
        "restored_path_matches": str(point.get("external_path")).removeprefix("file:")
        == path,
        "committed_offset_at_restore": committed,
    }
    run.log("job_restored", **row)
    return row


def resume(args: argparse.Namespace) -> Document:
    count = len(list(scope(args.run_id)[0].glob("observe*.jsonl")))
    run, plan = load(args.run_id, suffix=f"-r{count}")
    live = plan["source"] == "live"
    begin = time.time_ns() // 1_000_000
    run.log("resume_started")
    run.docker("rm", "-f", run.observer, check=False)
    run.start()
    run.docker(*run.compose, "up", "-d", "grafana")
    job = restore_job(run)
    run.start_observer(0 if live else cast(int, plan["expected"]), 1.0 if live else 2.0)
    # Profile clock and host clock differ; compare status times on one clock.
    clock = run.clock()
    if live:
        _, before = run.read_state("gateway-status.json")
        run.docker(
            *run.compose,
            *"up -d --no-deps live-archive-worker live-serving-worker".split(),
        )
        run.wait(lambda: serving_status(run, clock), 300, "serving_not_ready")
        run.docker(*run.compose, *"up -d --no-deps live-gateway".split())

        def new_epoch() -> bool:
            _, status = run.read_state("gateway-status.json")
            return (
                status is not None
                and status.get("status") == "running"
                and status.get("epoch") != (before or {}).get("epoch")
            )

        run.wait(new_epoch, 120, "gateway_not_ready")
        started = json.loads((run.out / "ops-started.json").read_text())
        require(run.state("px4-sitl")["Status"] == "running", "live_source_not_running")
        require(live_address(run) == started["live_source_address"], "live_address")
    else:
        run.docker(
            *run.compose, *"up -d --no-deps archive-worker serving-worker".split()
        )
        run.wait(lambda: serving_status(run, clock), 300, "serving_not_ready")
        run.docker(*run.compose, *"up -d --no-deps publisher".split())
    baseline = snapshot(run)
    after = cast(Document, baseline.get("inside") or {}).get("kafka")
    end = cast(Document, after or {}).get("input_end")
    require(isinstance(end, int), "input_end_unknown")
    run.log("resume_baseline", input_end=end)
    ready(run, str(plan["source"]), args.window, args.timeout, after=cast(int, end))
    return {
        "run_id": args.run_id,
        "status": "ready",
        "job": job,
        "resume_to_ready_s": round((time.time_ns() // 1_000_000 - begin) / 1e3, 1),
    }


def marker(run: Profile, name: str) -> bool:
    inside = probe(run, "snapshot", network=True)
    return cast(Document, inside.get("markers") or {}).get(name) is True


def complete(args: argparse.Namespace) -> Document:
    run, plan = load(args.run_id)
    # From here the source and the workers exit; an exiting container samples 0 B.
    run.log("completing")
    if plan["source"] == "live":
        run.docker("kill", "--signal", "USR1", run.container("live-gateway"))
        run.wait(lambda: marker(run, "gateway-complete"), 120, "gateway_not_completed")
        run.docker("stop", run.container("px4-sitl"), timeout=60)
    end = time.monotonic() + args.timeout
    while True:
        began = time.monotonic()
        if args.sample > 0:  # 0: the caller samples (runtime/recording/mvp_run.py)
            sample(run)  # memory, CPU and disk while the run finishes (ADR-0056)
        if marker(run, "serving-complete"):
            break
        require(began < end, "not_completed")
        period = max(5.0, args.sample)
        time.sleep(max(0.0, period - (time.monotonic() - began)))
    run.log("serving_complete")
    return {"run_id": args.run_id, "status": "completed"}


def verify(args: argparse.Namespace) -> Document:
    return verify_run(*load(args.run_id))


def health_of(
    run: Profile,
    plan: Document,
    current: Document,
    previous: Document | None = None,
    window: float = 0.0,
) -> Document:
    """Observations, signals (ADR-0056) and, given two snapshots, why a value
    stopped updating (ADR-0059); kept whole in the evidence."""
    observed = measure_health(run, plan, current)
    health: Document = {"observed": observed, "signals": signals(current, observed)}
    if previous is not None:
        health["why"] = explain(previous, current, window)
    return health


WHY_WINDOW_S = 10.0


def two_snapshots(
    run: Profile, window: float = WHY_WINDOW_S
) -> tuple[Document, Document]:
    first = snapshot(run)
    time.sleep(window)
    return first, snapshot(run)


def signal_table(health: Document) -> str:
    return render_signals(cast(list[Document], health["signals"]))


def stop_run(run: Profile, plan: Document | None = None) -> Document:
    """Collect evidence, then stop without removing any data."""
    if plan is None:
        plan = cast(Document, json.loads((run.out / "ops.json").read_text()))
    previous, current = two_snapshots(run)
    collected = collect(
        run, "stop", current, health_of(run, plan, current, previous, WHY_WINDOW_S)
    )
    observers = run.docker(
        *("ps", "-q", "--filter", f"name=f09-observer-{run.run_id}")
    ).split()
    for container in observers:
        run.docker("stop", container, check=False)
    run.stop()
    return collected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            *("start", "status", "collect", "stop", "resume", "complete", "verify"),
            "view",
        ),
    )
    parser.add_argument("--run-id", required=True)
    # A registered recording key replays that recording; "live" is SITL;
    # "ulog" replays --source-file when a mapping profile admits it.
    parser.add_argument(
        "--source", choices=(*RECORDING_INPUTS, "live", "ulog"), default="f09"
    )
    parser.add_argument("--source-file", type=Path, help="an original .ulg file")
    parser.add_argument("--rights", default="", help="licence or permission evidence")
    parser.add_argument("--reference", default="", help="where the file came from")
    parser.add_argument("--start-us", type=int)
    parser.add_argument("--end-us", type=int)
    parser.add_argument("--window", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--label", default="manual")
    parser.add_argument("--sample", type=float, default=15.0)
    args = parser.parse_args(argv)
    if args.source_file is not None:
        args.source = "ulog"
    try:
        if args.command == "start":
            result = start(args)
        elif args.command == "status":
            run, plan = load(args.run_id)
            first = snapshot(run)
            if args.window > 0:
                time.sleep(args.window)
                current = snapshot(run)
                source = str(cast(Document, current["inside"]).get("source"))
                print(render(current, evaluate(first, current, source), args.window))
                health = health_of(run, plan, current, first, args.window)
                print(render_why(cast(Document, health["why"])))
            else:
                current = first
                print(render(first, None, 0))
                health = health_of(run, plan, current)
            print(signal_table(health))
            return 0
        elif args.command == "collect":
            run, plan = load(args.run_id)
            previous, current = two_snapshots(run)
            label = re.sub(r"[^a-z0-9-]", "", args.label)
            result = collect(
                run,
                label,
                current,
                health_of(run, plan, current, previous, WHY_WINDOW_S),
            )
        elif args.command == "stop":
            result = stop_run(*load(args.run_id))
        elif args.command == "resume":
            result = resume(args)
        elif args.command == "complete":
            result = complete(args)
        elif args.command == "view":
            result = view(*load(args.run_id))
        else:
            result = verify(args)
    except AdmissionRefused as refused:
        # The file stays inspectable; each reason names an unavailable part.
        print(
            json.dumps(
                {
                    "command": args.command,
                    "status": "refused",
                    **{"reasons": refused.reasons},
                }
            )
        )
        return 2
    except (RunFailure, OSError, ValueError, KeyError) as error:
        category = str(error) if isinstance(error, RunFailure) else type(error).__name__
        print(
            json.dumps(
                {"command": args.command, "status": "failed", "category": category}
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
