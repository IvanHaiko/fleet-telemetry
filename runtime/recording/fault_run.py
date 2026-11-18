"""Run one F09 recording replay with a declared fault schedule, then reconcile.

Host-side orchestration for the single-machine profile (ADR-0052, ADR-0053),
using only the standard library and the Docker CLI. One invocation:

1. prepares a fresh bundle, reference and private scope for the interval;
2. writes `criterion.json` with the fault schedule and every limit before any
   service starts;
3. starts the profile, initializes, submits the Flink job and starts the
   observer container and the resource sampler;
4. starts the workers and executes the schedule (fault_actions.py);
5. waits for serving completion, reconciles SQL with the reference, rebuilds the
   facts from the archive into a separate database and reconciles that;
6. evaluates the observer samples (fault_analysis.py), writes `result.json` and
   stops the profile without removing any volume, topic, checkpoint, archive
   object or table.

Output holds counts, digests, times and Flink/Docker states only; no
coordinates, credentials or event identifiers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

from runtime.recording.fault_actions import (
    DEFAULT_RECOVERY_S,
    KINDS,
    Fault,
    Watcher,
    archive_pause,
    fault_checks,
    flink_evidence,
    job_resubmit,
    taskmanager_kill,
)
from runtime.recording.fault_analysis import evaluate
from runtime.recording.prepare import prepare
from runtime.recording.profile import (
    ROOT,
    Document,
    Profile,
    RunFailure,
    require,
)

PREPARED = ROOT / ".local-discovery/gold-grafana-20261104/connected-recording-v1"
ORIGINAL = (
    ROOT / ".local-discovery/real-ulog-20261027-001/log_67_2025-8-21-14-24-48.ulg"
)
_REVIEW = ROOT / ".local-discovery/second-log-review-20261117"
_PX4 = ROOT / ".local-discovery/fleet-source-inventory-20261103/px4-originals"
# Local, ignored locations of each registered recording's verified inspection
# and exact original (telemetry/recordings.py, ADR-0057). Source modes are the
# registration keys; "live" is the separate SITL profile.
RECORDING_INPUTS = {
    "f09": (PREPARED, ORIGINAL),
    "f07": (
        _REVIEW / "f07/inspection",
        _PX4 / "ac5a5608-5fc8-4422-9f2d-3ae25ab7c2c3.ulg",
    ),
    "f03": (
        _REVIEW / "f03/inspection",
        _PX4 / "3908856f-e963-44f2-95a8-5c158a2f3629.ulg",
    ),
}


def recording_inputs(source: str) -> tuple[Path, Path]:
    require(source in RECORDING_INPUTS, "recording_source")
    return RECORDING_INPUTS[source]


def plan_inputs(plan: Document) -> tuple[Path, Path]:
    """A run's prepared inspection and original: its own for an admitted file."""
    if plan.get("source") == "ulog":
        return ROOT / str(plan["prepared"]), Path(str(plan["original"]))
    return recording_inputs(str(plan["source"]))


RECOVERY_DEFINITION = (
    "fault start to the first sample after the resume action at which every "
    "fact acknowledged before the fault is SQL-visible, at least one fact "
    "acknowledged after the resume action is SQL-visible (when one exists) and no "
    "pending fact is older than the visibility limit; for archive-pause the "
    "limit applies to the catch-up from the resume action, because the pause "
    "length is declared"
)
CORRECTNESS = [
    "SQL fact_json SHA-256 set equals the reference set exactly",
    "zero logical repeats: distinct identities = DISTINCT view rows = reference "
    "lines and 0 conflicting identities; physical repeats are allowed",
    "taskmanager-kill and job-resubmit: the restored checkpoint is the latest "
    "completed one before the fault; no operator refusal (offset == "
    "runtime.deliveries) appears in any job's exception history; repeated "
    "output facts start at the first GPS fact of the restored source position",
    "serving-ack-cursor: the worker exits with the fault code after SQL "
    "confirmed the batch; after restart every member has more than one "
    "physical row and exactly one content",
    "archive-pause: serving holds below the archived prefix while the producer "
    "is ahead of it",
    "archive rebuild: a separate database rebuilt from archive objects only "
    "has the same fact hash set as the reference and the original database",
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout


def python(*args: str) -> Document:
    result = subprocess.run(
        [sys.executable, "-m", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    require(result.returncode == 0 and lines, "prepare_" + args[0].rsplit(".")[-1])
    return cast(Document, json.loads(lines[-1]))


def prepare_inputs(
    args: argparse.Namespace,
    out: Path,
    private: Path,
    inputs: tuple[Path, Path] | None = None,
) -> Document:
    """Fresh bundle, reference and private scope for exactly this interval."""
    prepared_inputs, original = inputs or recording_inputs(
        getattr(args, "source", "f09")
    )
    python(
        "runtime.flight_analytics.stream_prepare",
        *("--prepared", str(prepared_inputs), "--source", str(original)),
        *("--output", str(out / "bundle"), "--run-id", args.run_id),
        *("--start-us", str(args.start_us), "--end-us", str(args.end_us)),
    )
    python(
        "runtime.flight_analytics.stream_reference",
        *("--bundle", str(out / "bundle"), "--output", str(out / "reference")),
        *("--max-age-us", "1000000"),
    )
    reference = out / "reference/facts.jsonl"
    prepared = prepare(out / "bundle", reference, original, private)
    return {
        # recording_initialize appends two declared repeats to the events.
        "deliveries": cast(int, prepared["events"]) + 2,
        "expected": len(reference.read_bytes().splitlines()),
    }


def declare(
    args: argparse.Namespace, out: Path, faults: list[Fault], scope: Document
) -> None:
    """Write the criterion before any service starts; it is never rewritten."""
    patch = git("diff", "HEAD")
    (out / "working.patch").write_text(patch, encoding="utf-8", newline="\n")
    criterion: Document = {
        "run_id": args.run_id,
        "declared_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_run": True,
        "code_revision": git("rev-parse", "HEAD").strip(),
        "working_patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "interval_us": [args.start_us, args.end_us],
        **scope,
        "pace": "native time, 1x",
        "faults": [
            {
                "name": f.name,
                "kind": f.kind,
                "trigger": f.trigger,
                "pause_s": f.seconds or None,
                "recovery_limit_s": args.recovery[f.kind],
            }
            for f in faults
        ],
        "observer": "one container in the archive namespace, one clock, "
        f"samples every {args.interval} s",
        "recovery": RECOVERY_DEFINITION,
        "visibility_limit_s": args.visibility_limit,
        "visibility_scope": "facts whose acknowledgement-to-visibility interval "
        "lies outside every fault window",
        "terminal_drain_limit_s": args.drain_limit,
        "coverage": "a sample gap above 10 s leaves the run unestablished, not passed",
        "correctness": CORRECTNESS,
    }
    with (out / "criterion.json").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(criterion, indent=2) + "\n")


def launch(
    run: Profile, args: argparse.Namespace, expected: int
) -> subprocess.Popen[bytes]:
    """Submit the job, start the observer and sampler, then the workers."""
    job = run.submit()
    run.wait(lambda: run.job_running(job), 180, "job_not_running")
    run.log("job_running", job=job)
    run.start_observer(expected, args.interval)
    sampler = subprocess.Popen(
        [sys.executable, "-m", "runtime.recording.sample_resources"]
        + ["--output", str(run.out / "resources.jsonl"), "--interval", "10"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run.docker(*run.compose, *"up -d --no-deps archive-worker serving-worker".split())
    # Serving loads the bundle and the archived reference before its first
    # status; on the complete flight that takes about 30 s. Publishing earlier
    # would count that start-up as visibility age of the first facts.
    run.wait(
        lambda: run.read_state("serving-status.json")[1] is not None,
        300,
        "serving_not_ready",
    )
    run.log("serving_ready")
    run.docker(*run.compose, *"up -d --no-deps publisher".split())
    run.log("workers_started")
    return sampler


def schedule(run: Profile, faults: list[Fault], watch: Watcher, seconds: float) -> None:
    """Execute the triggered faults in order, then wait for serving completion."""

    def acknowledged() -> int:
        return cast(
            int,
            (run.read_state("producer-status.json")[1] or {}).get("acknowledged", 0),
        )

    for fault in faults:
        if fault.kind == "serving-ack-cursor":
            continue  # fires inside the worker; the watcher handles it
        while acknowledged() < fault.at:
            watch()
            time.sleep(0.3)
        if fault.kind == "taskmanager-kill":
            row = taskmanager_kill(run, fault)
        elif fault.kind == "job-resubmit":
            row = job_resubmit(run, fault)
        else:
            row = archive_pause(run, fault, watch)
        row["recovery_limit_s"] = watch.recovery[fault.kind]
        watch.executed.append(row)
    deadline = time.monotonic() + seconds + 1800
    while run.read_state("serving-complete.json")[1] is None:
        require(time.monotonic() < deadline, "serving_not_complete")
        watch()
        time.sleep(1)
    require(watch.serving is None or watch.serving_handled, "serving_fault_not_fired")
    run.log("serving_complete")


def collect(run: Profile, executed: list[Document]) -> tuple[Document, ...]:
    """Flink evidence, reconciliation, the isolated rebuild and its reconciliation."""
    run.docker("wait", run.observer, timeout=180)
    flink = flink_evidence(run)
    positions = [
        str(row["committed_offset_at_restore"])
        for row in executed
        if isinstance(row.get("committed_offset_at_restore"), int)
    ]
    reconcile = run.worker(
        "recording_reconcile",
        *(["--restore-positions", ",".join(positions)] if positions else []),
    )
    rebuilt = run.worker("recording_rebuild", "--rebuild", "001", timeout=1800)
    rebuild_check = run.worker(
        "recording_reconcile", "--database", str(rebuilt.get("database"))
    )
    for name, document in (
        ("flink", flink),
        ("reconcile", reconcile),
        ("rebuild", rebuilt),
        ("rebuild-reconcile", rebuild_check),
    ):
        (run.out / f"{name}.json").write_text(json.dumps(document, indent=1))
    return flink, reconcile, rebuild_check


def assess(
    run: Profile,
    args: argparse.Namespace,
    faults: list[Fault],
    executed: list[Document],
    expected: int,
) -> Document:
    flink, reconcile, rebuild_check = collect(run, executed)
    samples = [
        json.loads(line)
        for line in (run.out / "observe.jsonl").read_text().splitlines()
        if line.strip()
    ]
    order = {f.name: i for i, f in enumerate(faults)}
    executed.sort(key=lambda row: order[cast(str, row["name"])])
    timing = evaluate(
        samples, executed, expected, args.visibility_limit, args.drain_limit
    )
    checks = fault_checks(executed, flink, reconcile, timing)
    correctness: Document = {
        "fact_hash_sets_equal": reconcile.get("fact_hash_sets_equal"),
        "zero_logical_repeats": reconcile.get("zero_logical_repeats"),
        "rebuild_fact_hash_sets_equal": rebuild_check.get("fact_hash_sets_equal"),
        "rebuild_zero_logical_repeats": rebuild_check.get("zero_logical_repeats"),
        "rebuild_matches_original_hash_set": rebuild_check.get("fact_hash_set_sha256")
        == reconcile.get("fact_hash_set_sha256"),
    }
    passed = (
        len(executed) == len(faults)
        and all(v is True for v in checks.values())
        and all(v is True for v in correctness.values())
        and all(
            timing[k] is True
            for k in ("pass_visibility", "pass_drain", "pass_recovery")
        )
    )
    return {
        "run_id": args.run_id,
        "status": "passed" if passed else "failed_criterion",
        "faults_declared": [f.name for f in faults],
        "faults_executed": executed,
        "timing": timing,
        "fault_checks": checks,
        "correctness": correctness,
        "physical_rows": reconcile.get("physical_rows"),
        "output_topic_records": reconcile.get("output_topic_records"),
    }


def execute(args: argparse.Namespace) -> int:
    faults = sorted((Fault.parse(t) for t in args.fault), key=lambda f: f.at)
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{2,39}", args.run_id), "run_id")
    require(len({f.kind for f in faults}) == len(faults), "one_fault_per_kind")
    out = (ROOT / ".local-discovery" / args.run_id).resolve()
    private = ROOT / ".local-discovery" / f"recording-private-{args.run_id}"
    require(not out.exists() and not private.exists(), "run_scope_exists")
    out.mkdir()
    run = Profile(args.run_id, out, private)
    scope = prepare_inputs(args, out, private)
    for fault in faults:
        kind = "expected" if fault.kind == "serving-ack-cursor" else "deliveries"
        require(0 < fault.at < cast(int, scope[kind]), "fault_outside_run")
    declare(args, out, faults, scope)
    run.log("criterion_declared", faults=[f.name for f in faults])

    sampler: subprocess.Popen[bytes] | None = None
    result: Document = {"run_id": args.run_id, "status": "failed"}
    owns_cleanup = False
    try:
        containers = cast(dict[str, str], run.status()["containers"])
        busy = [n for n, s in containers.items() if s == "running" and "worker" in n]
        require(
            not busy and containers.get(run.container("publisher")) != "running",
            "workers_busy",
        )
        owns_cleanup = True
        run.start()
        serving = next((f for f in faults if f.kind == "serving-ack-cursor"), None)
        fault_option = (
            []
            if serving is None
            else ["--serving-fault-after-outputs", str(serving.at)]
        )
        summary = run.worker("recording_initialize", *fault_option)
        require(summary.get("deliveries") == scope["deliveries"], "delivery_count")
        (out / "initialize.json").write_text(json.dumps(summary, indent=1))
        sampler = launch(run, args, cast(int, scope["expected"]))
        watch = Watcher(run, serving, args.recovery)
        schedule(run, faults, watch, (args.end_us - args.start_us) / 1e6)
        result = assess(run, args, faults, watch.executed, cast(int, scope["expected"]))
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
        if sampler is not None:
            sampler.terminate()
        if owns_cleanup and not args.keep_running:
            run.stop()
        with (out / "result.json").open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"run_id": args.run_id, "status": result["status"]}))
    return 0 if result["status"] == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start-us", type=int, required=True)
    parser.add_argument("--end-us", type=int, required=True)
    parser.add_argument(
        "--fault",
        action="append",
        default=[],
        help="kind@at[:seconds]; kinds: " + ", ".join(KINDS),
    )
    parser.add_argument(
        "--recovery-limit",
        action="append",
        default=[],
        help="kind=seconds, replacing that kind's default recovery limit",
    )
    parser.add_argument("--visibility-limit", type=float, default=15.0)
    parser.add_argument("--drain-limit", type=float, default=30.0)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="leave the profile running after the run for inspection",
    )
    args = parser.parse_args(argv)
    try:
        limits = dict(item.split("=", 1) for item in args.recovery_limit)
        require(set(limits) <= set(KINDS), "recovery_limit_kind")
        args.recovery = {
            **DEFAULT_RECOVERY_S,
            **{k: float(v) for k, v in limits.items()},
        }
        return execute(args)
    except (RunFailure, ValueError) as error:
        category = str(error) if isinstance(error, RunFailure) else "arguments"
        print(json.dumps({"status": "failed", "category": category}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
