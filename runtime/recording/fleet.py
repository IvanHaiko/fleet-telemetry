"""Operate a fleet session: recorded flights as virtual vehicles (ADR-0060).

Commands (run from the repository root on the host):

- `start`: a fresh live session without a simulator: job, observer, archive
  and serving workers and the gateway; vehicles join later;
- `add --file X.ulg`: plan the file on the host (refused files stop here with
  a reason), then start one replay player for it; returns once the gateway
  publishes the new vehicle;
- `pause`, `resume`, `remove --file X.ulg`: hold, continue or end one player;
- `status`: one line per vehicle from the gateway and player status files;
- `complete`: end every player, close the gateway session and wait until
  serving has every archived fact;
- `verify`: archive-only recomputation equals SQL, no capture loss, and each
  player's ledger equals its vehicle's archived positions.

`ops status`, `ops collect` and `ops stop` work on a fleet run as on a live
one. Output holds counts, states and times only, never values or coordinates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import cast

from runtime.recording.evidence import probe, write
from runtime.recording.fault_run import git
from runtime.recording.live_prepare import UDP_PORT, prepare_live
from runtime.recording.ops import load, scope, stop_run
from runtime.recording.profile import PROJECT, Document, Profile, RunFailure, require
from telemetry.ulog_replay import ReplayRefused, plan

PROFILES = ("run", "live", "fleet")
PLAYERS = "state/players"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def player_name(run: Profile, digest: str) -> str:
    return f"{PROJECT}-replay-{run.run_id}-{digest[:12]}"


def gateway(run: Profile) -> Document:
    return run.read_state("gateway-status.json")[1] or {}


def start(args: argparse.Namespace) -> Document:
    out, private = scope(args.run_id)
    require(not out.exists() and not private.exists(), "run_scope_exists")
    out.mkdir()
    run = Profile(args.run_id, out, private, profiles=PROFILES)
    prepare_live(args.run_id, private, fleet=True)
    write(
        out / "ops.json",
        {
            "run_id": args.run_id,
            # `ops` treats the session as live; the gateway admits players.
            "source": "live",
            "fleet": True,
            "profiles": list(PROFILES),
            "declared_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "code_revision": git("rev-parse", "HEAD").strip(),
            "readiness_window_s": args.window,
        },
    )
    busy = [
        name
        for name, state in cast(dict[str, str], run.status()["containers"]).items()
        if state == "running" and ("worker" in name or "replay" in name)
    ]
    require(not busy, "workers_busy")
    run.start()
    run.docker(*run.compose, "up", "-d", "grafana")
    write(out / "initialize.json", run.worker("live_initialize"))
    job = run.submit()
    run.wait(lambda: run.job_running(job), 180, "job_not_running")
    run.log("job_running", job=job)
    run.start_observer(0, 1.0)
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
    run.wait(lambda: gateway(run).get("status") == "running", 120, "gateway_not_ready")
    write(out / "ops-started.json", {"live_source_address": None})
    run.log("fleet_ready")
    return {"run_id": args.run_id, "status": "ready", "vehicles": 0}


def add(args: argparse.Namespace) -> Document:
    run, _ = load(args.run_id)
    source = cast(Path, args.file).resolve()
    require(source.is_file(), "file_missing")
    try:
        replay = plan(source, start_us=args.start_us, end_us=args.end_us)
    except ReplayRefused as refused:
        run.log("vehicle_refused", reason=str(refused))
        return {"status": "refused", "reason": str(refused)}
    summary = replay.summary()
    digest = replay.digest
    name = player_name(run, digest)
    interval = [
        *(["--start-us", str(args.start_us)] if args.start_us is not None else []),
        *(["--end-us", str(args.end_us)] if args.end_us is not None else []),
    ]
    run.docker(
        *run.compose,
        *("run", "-d", "--no-deps", "--name", name),
        *("-v", f"{source.parent}:/input:ro"),
        "replay-player",
        "runtime.continuous.replay_player",
        *("--source", f"/input/{source.name}"),
        *("--players", f"/evidence/{run.run_id}/{PLAYERS}"),
        *("--port", str(UDP_PORT)),
        *interval,
    )
    vehicle = replay.vehicle

    def published() -> bool:
        row = cast(Document, gateway(run).get("vehicles", {})).get(vehicle)
        return isinstance(row, dict) and cast(int, row.get("published", 0)) > 0

    run.wait(published, 120, "vehicle_not_published")
    record = {"vehicle": vehicle, "container": name, "plan": summary}
    write(run.out / f"vehicle-{digest[:12]}.json", record)
    run.log("vehicle_added", vehicle=vehicle, packets=summary["packets"])
    return {"status": "added", **record}


def control(args: argparse.Namespace, action: str) -> Document:
    run, _ = load(args.run_id)
    digest = _digest(cast(Path, args.file).resolve())
    vehicle = f"ulog-{digest[:16]}"
    folder = f"/evidence/{run.run_id}/{PLAYERS}"
    script = (
        "import pathlib,sys\n"
        "p=pathlib.Path(sys.argv[1])\n"
        "p.unlink(missing_ok=True) if sys.argv[2]=='clear' else p.touch()\n"
    )
    target, verb = {
        "pause": (f"{folder}/{vehicle}.pause", "touch"),
        "resume": (f"{folder}/{vehicle}.pause", "clear"),
        "remove": (f"{folder}/{vehicle}.stop", "touch"),
    }[action]
    run.docker("exec", player_name(run, digest), "python", "-c", script, target, verb)
    run.log("vehicle_" + action, vehicle=vehicle)
    return {"status": action, "vehicle": vehicle, "at_ms": time.time_ns() // 1_000_000}


def players(run: Profile) -> dict[str, Document]:
    found: dict[str, Document] = {}
    for vehicle in cast(Document, gateway(run).get("vehicles", {})):
        _, row = run.read_state(f"players/{vehicle}.status.json")
        if row is not None:
            found[vehicle] = row
    return found


def status(args: argparse.Namespace) -> Document:
    run, _ = load(args.run_id)
    state = gateway(run)
    clock, _ = run.read_state("gateway-status.json")
    states = players(run)
    rows = []
    for vehicle, value in cast(dict[str, Document], state.get("vehicles", {})).items():
        heartbeat = value.get("last_heartbeat_ms")
        player = states.get(vehicle, {})
        rows.append(
            {
                "vehicle": vehicle,
                "label": value.get("label"),
                "system": value.get("system"),
                "published": value.get("published"),
                "heartbeat_age_ms": None
                if heartbeat is None
                else clock - cast(int, heartbeat),
                "player": player.get("status"),
                "sent": player.get("sent"),
                "total": player.get("total"),
                "lost_packets": value.get("lost_packets"),
                "refusal": value.get("refusal"),
            }
        )
    return {"gateway": state.get("status"), "vehicles": rows}


def complete(args: argparse.Namespace) -> Document:
    run, _ = load(args.run_id)
    run.log("completing")
    for vehicle, row in players(run).items():
        if row.get("status") in ("running", "paused"):
            container = f"{PROJECT}-replay-{run.run_id}-{vehicle[5:17]}"
            run.docker(
                *("exec", container, "python", "-c"),
                "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()",
                f"/evidence/{run.run_id}/{PLAYERS}/{vehicle}.stop",
            )
    run.wait(
        lambda: all(
            r.get("status") in ("ended", "stopped", "failed")
            for r in players(run).values()
        ),
        60,
        "players_not_finished",
    )
    run.docker("kill", "--signal", "USR1", run.container("live-gateway"))

    def marker(name: str) -> bool:
        inside = probe(run, "snapshot", network=True)
        return cast(Document, inside.get("markers") or {}).get(name) is True

    run.wait(lambda: marker("gateway-complete"), 120, "gateway_not_completed")
    run.wait(lambda: marker("serving-complete"), args.timeout, "not_completed")
    run.log("serving_complete")
    return {"run_id": args.run_id, "status": "completed"}


def verify(args: argparse.Namespace) -> Document:
    run, _ = load(args.run_id)
    reconcile = run.worker("live_reconcile", timeout=900)
    capture = cast(Document, reconcile["capture"])
    fleet = cast(dict[str, Document], reconcile.get("players") or {})
    checks: Document = {
        "capture_covered": capture["covered"],
        "no_capture_loss": capture["lost_packets"] == 0,
        "fact_hash_sets_equal": reconcile["fact_hash_sets_equal"],
        "zero_logical_repeats": reconcile["zero_logical_repeats"],
        "untimed_without_time": reconcile["untimed_without_time"],
        "statuses_match_receipt_order": cast(Document, reconcile["restart"])[
            "statuses_match_receipt_order"
        ],
        "players_present": bool(fleet),
        "player_ledgers_equal_archive": bool(fleet)
        and all(row["equal"] is True for row in fleet.values()),
    }
    result: Document = {
        "run_id": args.run_id,
        "status": "passed" if all(v is True for v in checks.values()) else "failed",
        "checks": checks,
        "players": fleet,
        "reconcile": reconcile,
    }
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    write(run.out / f"verify-{stamp}.json", result)
    run.log("verified", status=result["status"])
    return {k: result[k] for k in ("run_id", "status", "checks", "players")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "start",
            "add",
            "pause",
            "resume",
            "remove",
            "status",
            "complete",
            "verify",
            "stop",
        ),
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--start-us", type=int)
    parser.add_argument("--end-us", type=int)
    parser.add_argument("--window", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args(argv)
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{2,39}", args.run_id), "run_id")
    try:
        if args.command in ("add", "pause", "resume", "remove"):
            require(args.file is not None, "file_required")
        if args.command == "start":
            result = start(args)
        elif args.command == "add":
            result = add(args)
        elif args.command in ("pause", "resume", "remove"):
            result = control(args, args.command)
        elif args.command == "status":
            result = status(args)
        elif args.command == "complete":
            result = complete(args)
        elif args.command == "verify":
            result = verify(args)
        else:
            run, plan_document = load(args.run_id)
            result = stop_run(run, plan_document)
    except (RunFailure, OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "category": str(error)[:80]}))
        return 2
    print(json.dumps(result, indent=1, default=str))
    return 2 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
