"""Stop the whole recording profile mid-run, restore it with the runbook commands.

The drill for roadmap step 5 (ADR-0055). One invocation:

1. writes `criterion.json` before any service starts. With `--declare-only` it
   writes a draft for review instead and stops; `--approved-draft` then
   requires the run's criterion to equal that draft, apart from its time;
2. starts the run with `ops start` and waits for the declared trigger;
3. stops every service of the profile at once, as a host shutdown would: no
   job cancellation and no evidence collection first. For a live session the
   PX4 SITL container keeps running; it stands for the external vehicle,
   which does not stop with the recording host;
4. collects evidence during the outage (`ops collect`), which must report a
   partial run with its actual interval;
5. after the declared outage, restores with `ops resume`, completes with
   `ops complete`, reconciles with `ops verify` and stops with `ops stop`;
6. evaluates the declared conditions and writes `result.json`.

Output holds counts, states, digests and times only; no coordinates.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import cast

from runtime.recording import ops
from runtime.recording.evidence import collect, write
from runtime.recording.profile import ROOT, Document, Profile, RunFailure, require

CONDITIONS = [
    "ops start reaches readiness: broker healthy, Flink slots registered, the "
    "run's job RUNNING with checkpoints completing, archive, serving and source "
    "workers current, ClickHouse, SeaweedFS and Grafana /api/health answering, "
    "and input offsets, the archived prefix and SQL facts all advancing over "
    "the readiness window",
    "the outage collection reports completion 'partial' with the acknowledged "
    "deliveries recorded in the volume, at least the count read just before "
    "the stop",
    "ops resume resubmits the job from the newest retained checkpoint (by "
    "_metadata time) and Flink reports that checkpoint as restored; it belongs "
    "to the job that ran before the stop and its ID is at least the latest "
    "completed ID the Flink REST API reported just before the stop (one may "
    "complete while the services stop)",
    "ops resume reaches the same readiness and, in addition, SQL shows a fact "
    "whose input offset is at or beyond the input end offset of the first "
    "snapshot after the workers restarted; the time from the start of ops "
    "resume to that readiness, on the host clock, is within the resume limit",
    "the workers continue from their cursors: the input topic ends at exactly "
    "the declared deliveries (F09) or the published count (live)",
    "ops verify passes: F09 SQL fact hash set equals the reference, zero "
    "logical repeats, archive-only rebuild equals the reference and the "
    "original, re-emission starts at the restored source position; live: "
    "capture covered without sequence gaps inside an epoch, SQL equals the "
    "archive-only recomputation, zero logical repeats, untimed streams "
    "without time, association statuses match receipt order",
    "live only: the gateway opened a new epoch after the resume",
    "ops stop collects a completed manifest and an inventory, and removes no "
    "volume, topic, checkpoint, archive object or table",
]


def criterion(args: argparse.Namespace) -> Document:
    document: Document = {
        "run_id": args.run_id,
        "source": args.source,
        "scenario": "whole-profile stop mid-run as at host shutdown "
        "(docker compose stop of every service, no job cancellation), "
        f"{args.outage_s:g} s outage, then the runbook resume",
        "trigger": f"producer acknowledged >= {args.stop_at}"
        if args.source == "f09"
        else f"{args.stop_at} s after ops start returned",
        "outage_s": args.outage_s,
        "readiness_window_s": args.window,
        "resume_limit_s": args.resume_limit,
        "conditions": CONDITIONS,
        "not_judged": "visibility and drain timing (ADR-0053 and ADR-0054 own "
        "them); the outage itself; power loss and SIGKILL of every process",
    }
    if args.source == "f09":
        document["interval_us"] = [args.start_us, args.end_us]
    else:
        document["complete_after_resume_s"] = args.end_at - args.stop_at - args.outage_s
        document["source_note"] = (
            "the PX4 SITL container keeps running through the outage as the "
            "external vehicle; packets sent while the gateway is down are lost "
            "and appear as the gap between gateway epochs"
        )
    return document


def declare(args: argparse.Namespace, out: Path) -> None:
    document = criterion(args)
    if args.approved_draft is not None:
        draft = json.loads(Path(args.approved_draft).read_text())
        draft.pop("declared_utc", None)
        require(draft == document, "criterion_differs_from_approved_draft")
    document["declared_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    document["declared_before_run"] = True
    out.mkdir()
    write(out / "criterion.json", document)


def host_stop(run: Profile, source: str) -> Document:
    """Stop every service at once without cancelling the job."""
    latest: Document | None = None
    jobs = [j for j in run.jobs() if j.get("state") == "RUNNING"]
    if len(jobs) == 1:
        latest = run.checkpoint(str(jobs[0]["jid"]), "completed")
    _, sent = run.read_state(
        "gateway-status.json" if source == "live" else "producer-status.json"
    )
    clock = run.clock()
    services = run.docker(*run.compose, "config", "--services").split()
    kept = {"px4-sitl"} if source == "live" else set()
    stopped = [s for s in services if s not in kept]
    observers = run.docker(
        "ps", "-q", "--filter", f"name=f09-observer-{run.run_id}"
    ).split()
    run.docker("stop", *observers, check=False)
    run.docker(*run.compose, "stop", *stopped, timeout=600)
    row: Document = {
        "stop_clock_ms": clock,
        "sent_at_stop": (sent or {}).get(
            "published" if source == "live" else "acknowledged"
        ),
        "latest_completed_before_stop": None
        if latest is None
        else {"id": latest.get("id"), "path": latest.get("external_path")},
        "kept_running": sorted(kept),
    }
    run.log("host_stop", **row)
    return row


def same_job_not_older(before: str, restored: str) -> bool:
    """`<checkpoints>/<job>/chk-<n>`: same job directory and n at least as large."""
    pattern = re.compile(r"(?:file:)?(.+)/chk-([0-9]+)")
    first, second = pattern.fullmatch(before), pattern.fullmatch(restored)
    return (
        first is not None
        and second is not None
        and first[1] == second[1]
        and int(second[2]) >= int(first[2])
    )


def evaluate(
    args: argparse.Namespace,
    stop: Document,
    outage: Document,
    resumed: Document,
    verified: Document,
    final: Document,
) -> Document:
    job = cast(Document, resumed.get("job") or {})
    before = cast(Document | None, stop.get("latest_completed_before_stop"))
    restored = str(job.get("checkpoint", ""))
    expected_end = None
    if args.source == "f09":
        plan = json.loads(
            (ROOT / ".local-discovery" / args.run_id / "ops.json").read_text()
        )
        expected_end = plan["deliveries"]
    actual = cast(Document, final.get("actual") or {})
    at_outage = cast(Document, outage.get("actual") or {}).get(
        "acknowledged_deliveries"
    )
    checks: Document = {
        "start_ready": True,  # ops start raised otherwise
        # The source keeps sending until SIGTERM reaches it, so the volume holds
        # at least what was read just before the stop.
        "outage_reported_partial": outage.get("completion") == "partial"
        and isinstance(at_outage, int)
        and isinstance(stop.get("sent_at_stop"), int)
        and at_outage >= cast(int, stop["sent_at_stop"]),
        "restored_latest_checkpoint": job.get("resubmitted") is True
        and job.get("restored_path_matches") is True
        and before is not None
        and same_job_not_older(str(before.get("path", "")), restored),
        "resume_ready_with_new_fact": resumed.get("status") == "ready"
        and cast(float, resumed.get("resume_to_ready_s", 1e9)) <= args.resume_limit,
        "input_ends_at_declared": actual.get("input_end_offset") == expected_end
        if args.source == "f09"
        else actual.get("input_end_offset") is not None,
        "verify_passed": verified.get("status") == "passed",
        "stop_manifest_completed": final.get("completion") == "completed",
    }
    if args.source == "live":
        checks["new_gateway_epoch"] = cast(int, verified.get("capture_epochs", 0)) >= 2
    return checks


def execute(args: argparse.Namespace) -> int:
    out, _ = ops.scope(args.run_id)
    if args.declare_only:
        draft = out.with_name(args.run_id + "-criterion-draft.json")
        write(draft, criterion(args) | {"declared_utc": None})
        print(json.dumps({"draft": draft.relative_to(ROOT).as_posix()}))
        return 0
    require(not out.exists(), "run_scope_exists")
    declare(args, out)
    result: Document = {"run_id": args.run_id, "status": "failed"}
    run: Profile | None = None
    try:
        ops.start(args)
        run, _ = ops.load(args.run_id)
        if args.source == "f09":
            while True:
                _, status = run.read_state("producer-status.json")
                if cast(int, (status or {}).get("acknowledged", 0)) >= args.stop_at:
                    break
                time.sleep(0.5)
        else:
            time.sleep(args.stop_at)
        stop = host_stop(run, args.source)
        outage = collect(run, "outage", {"inside": None, "note": "profile down"})
        outage_manifest = json.loads(
            (ROOT / cast(str, outage["directory"]) / "manifest.json").read_text()
        )
        time.sleep(args.outage_s)
        resumed = ops.resume(args)
        if args.source == "live":
            time.sleep(max(0.0, args.end_at - args.stop_at - args.outage_s))
        if args.source == "f09":
            args.timeout = (args.end_us - args.start_us) / 1e6 + 1800
        ops.complete(args)
        verified = ops.verify(args)
        run, _ = ops.load(args.run_id)
        final = ops.stop_run(run)
        run = None
        final_manifest = json.loads(
            (ROOT / cast(str, final["directory"]) / "manifest.json").read_text()
        )
        checks = evaluate(
            args, stop, outage_manifest, resumed, verified, final_manifest
        )
        result = {
            "run_id": args.run_id,
            "status": "passed"
            if all(v is True for v in checks.values())
            else "failed_criterion",
            "checks": checks,
            "host_stop": stop,
            "resume": resumed,
            "verify": verified,
            "outage_collection": outage,
            "stop_collection": final,
        }
    except (RunFailure, OSError, ValueError, KeyError) as error:
        result["error"] = (
            str(error) if isinstance(error, RunFailure) else type(error).__name__
        )
    finally:
        if run is not None and not args.keep_running:
            ops.stop_run(run)
        with (out / "result.json").open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"run_id": args.run_id, "status": result["status"]}))
    return 0 if result["status"] == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source", choices=("f09", "live"), required=True)
    parser.add_argument("--start-us", type=int)
    parser.add_argument("--end-us", type=int)
    parser.add_argument(
        "--stop-at",
        type=int,
        required=True,
        help="F09: acknowledged deliveries; live: seconds after ops start returned",
    )
    parser.add_argument("--outage-s", type=float, default=30.0)
    parser.add_argument("--end-at", type=float, default=300.0)
    parser.add_argument("--window", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--resume-limit", type=float, default=300.0)
    parser.add_argument("--declare-only", action="store_true")
    parser.add_argument("--approved-draft")
    parser.add_argument("--keep-running", action="store_true")
    args = parser.parse_args(argv)
    try:
        return execute(args)
    except (RunFailure, ValueError) as error:
        category = str(error) if isinstance(error, RunFailure) else "arguments"
        print(json.dumps({"status": "failed", "category": category}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
