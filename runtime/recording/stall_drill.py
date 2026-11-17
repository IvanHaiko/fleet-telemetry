"""Stall drill of roadmap step 2: is each stopped stage explained? (ADR-0059)

`run` writes `criterion.json` (the detection interval and the phases, before
any service starts), then `ops start`, and samples the explanation of
runtime/recording/stall.py every `--every` seconds over a `--window`:

replay (`--source f09|f07|f03`, or `--source-file` for an admitted original):

1. `serving-pause`: stop the serving worker for `--pause-s` while input and
   archive advance; expect `serving_behind`;
2. `publisher-pause`: pause the publisher (its explicit paused state) for
   `--pause-s`; expect `replay_paused`;
3. end of file: expect `replay_ended` or `advancing` while later stages
   finish, then `completed`; then `ops verify` reconciles SQL with the
   reference and an archive-only rebuild.

live (`--source live`):

1. `source-silence`: pause the simulator for `--pause-s` while the gateway
   runs; expect `source_silent`; then `ops complete` and `ops verify`.

A phase passes when its expected explanation appears within the declared
detection interval of its start, and after its end the run is `advancing`
again (replay) within the same interval. Every sample is kept in
`why.jsonl`; the verdict is in `drill.json`. Output holds counts, states and
times only.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import deque
from pathlib import Path
from typing import cast

from runtime.recording import ops
from runtime.recording.evidence import write
from runtime.recording.ops_view import snapshot
from runtime.recording.profile import Document, Profile, RunFailure, require
from runtime.recording.stall import explain

EXPECTED = {
    "serving-pause": "serving_behind",
    "publisher-pause": "replay_paused",
    "source-silence": "source_silent",
}


class Sampler:
    """Snapshots every `every` s; each explanation spans at least `window` s."""

    def __init__(self, run: Profile, out: Path, every: float, window: float) -> None:
        self.run, self.every, self.window = run, every, window
        self.path = out / "why.jsonl"
        self.history: deque[tuple[float, Document]] = deque()
        self.phase = "baseline"

    def sample(self) -> Document:
        began = time.monotonic()
        current = snapshot(self.run)
        self.history.append((began, current))
        while len(self.history) > 1 and began - self.history[1][0] >= self.window:
            self.history.popleft()
        then, previous = self.history[0]
        why = explain(previous, current, round(began - then, 1))
        row = {
            "t": round(time.time(), 3),
            "observer_ms": cast(Document, current.get("inside") or {}).get("clock_ms"),
            "phase": self.phase,
            **why,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        time.sleep(max(0.0, self.every - (time.monotonic() - began)))
        return row

    def until(self, wanted: set[str], limit: float) -> Document | None:
        """Sample until an explanation in `wanted` appears; None after `limit`."""
        end = time.monotonic() + limit
        while time.monotonic() < end:
            row = self.sample()
            if row["explanation"] in wanted:
                return row
        return None

    def hold(self, seconds: float) -> list[str]:
        end, seen = time.monotonic() + seconds, []
        while time.monotonic() < end:
            seen.append(str(self.sample()["explanation"]))
        return seen


def acknowledged(run: Profile) -> int:
    status = run.read_state("producer-status.json")[1] or {}
    return cast(int, status.get("acknowledged", 0))


def phase(
    sampler: Sampler,
    name: str,
    begin: list[str],
    end: list[str],
    args: argparse.Namespace,
) -> Document:
    run = sampler.run
    sampler.phase = name
    started = time.time()
    run.docker(*begin)
    run.log("drill_phase_started", name=name)
    first = sampler.until({EXPECTED[name]}, args.detection_s)
    detected = None if first is None else round(cast(float, first["t"]) - started, 1)
    remaining = args.pause_s - (time.time() - started)
    seen = sampler.hold(max(0.0, remaining))
    run.docker(*end)
    resumed = time.time()
    sampler.phase = name + "-resumed"
    back = sampler.until({"advancing", "completed"}, args.detection_s * 2)
    row: Document = {
        "name": name,
        "expected": EXPECTED[name],
        "detected_after_s": detected,
        "explanations_while_held": sorted(set(seen)),
        "held_s": round(resumed - started, 1),
        "advancing_after_resume_s": None
        if back is None
        else round(cast(float, back["t"]) - resumed, 1),
    }
    row["passed"] = detected is not None and back is not None
    run.log("drill_phase_done", **row)
    return row


def criterion(args: argparse.Namespace) -> Document:
    live = args.source == "live"
    return {
        "run_id": args.run_id,
        "declared_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_run": True,
        "source": args.source,
        "source_file": None if args.source_file is None else str(args.source_file),
        "phases": ["source-silence"]
        if live
        else ["serving-pause", "publisher-pause", "end-of-file"],
        "triggers": {"source-silence": f"{args.silence_after_s} s after ready"}
        if live
        else {
            "serving-pause": f"producer acknowledged >= {args.serving_at}",
            "publisher-pause": f"producer acknowledged >= {args.publisher_at}",
        },
        "pause_s": args.pause_s,
        "detection_interval_s": args.detection_s,
        "sample_every_s": args.every,
        "explanation_window_s": args.why_window,
        "expected": EXPECTED,
        "conditions": [
            "each phase's expected explanation appears within the detection "
            "interval of the phase start",
            "the run is advancing again within twice the detection interval of "
            "the phase end (replay: query-visible progress grows)",
            "replay: before completion the publisher's end of file is seen as "
            "replay_ended or advancing, then completed within the drain limit",
            "ops verify passes: SQL equals the reference, zero logical repeats, "
            "and an archive-only rebuild is equal",
            "browser delay stays unknown (not measured)",
        ],
    }


def drill(args: argparse.Namespace) -> Document:
    out, _ = ops.scope(args.run_id)
    require(not out.exists(), "run_scope_exists")
    out.mkdir()
    write(out / "criterion.json", criterion(args))
    ops.start(args)
    run, _ = ops.load(args.run_id)
    sampler = Sampler(run, out, args.every, args.why_window)
    phases: list[Document] = []
    if args.source == "live":
        sampler.hold(args.silence_after_s)
        sitl = run.container("px4-sitl")
        phases.append(
            phase(
                sampler,
                "source-silence",
                ["pause", sitl],
                ["unpause", sitl],
                args,
            )
        )
        args.sample = 0.0
        ops.complete(args)
        sampler.phase = "complete"
        sampler.sample()
        ending: Document = {}
    else:
        publisher = run.container("publisher")
        pause_file = f"/evidence/{args.run_id}/state/pause-publisher"
        # Phases run in the order of their triggers.
        for name, at, begin, end in sorted(
            (
                (
                    "serving-pause",
                    args.serving_at,
                    ["stop", "--timeout", "60", run.container("serving-worker")],
                    ["start", run.container("serving-worker")],
                ),
                (
                    "publisher-pause",
                    args.publisher_at,
                    ["exec", publisher, "touch", pause_file],
                    ["exec", publisher, "rm", "-f", pause_file],
                ),
            ),
            key=lambda item: cast(int, item[1]),
        ):
            while acknowledged(run) < at:
                sampler.sample()
            phases.append(phase(sampler, name, begin, end, args))
        sampler.phase = "end-of-file"
        began = time.time()
        seen: list[str] = []
        deadline = time.monotonic() + args.drain_limit_s
        while time.monotonic() < deadline:
            row = sampler.sample()
            seen.append(str(row["explanation"]))
            if row["explanation"] == "completed":
                break
        ending = {
            "explanations": sorted(set(seen)),
            "completed_after_s": round(time.time() - began, 1)
            if seen and seen[-1] == "completed"
            else None,
            "end_of_file_seen": "replay_ended" in seen
            or (bool(seen) and seen[-1] == "completed"),
        }
        run.log("drill_end_of_file", **ending)
    verified = ops.verify(args)
    passed = (
        all(p["passed"] is True for p in phases)
        and verified.get("status") == "passed"
        and (args.source == "live" or ending.get("completed_after_s") is not None)
    )
    result: Document = {
        "run_id": args.run_id,
        "status": "passed" if passed else "failed_criterion",
        "phases": phases,
        "end_of_file": ending,
        "verify": verified,
        "browser_delay": "unknown",
    }
    write(out / "drill.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--source", choices=(*ops.RECORDING_INPUTS, "live", "ulog"), default="f09"
    )
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--rights", default="")
    parser.add_argument("--reference", default="")
    parser.add_argument("--start-us", type=int)
    parser.add_argument("--end-us", type=int)
    parser.add_argument("--serving-at", type=int, default=1500)
    parser.add_argument("--publisher-at", type=int, default=4000)
    parser.add_argument("--silence-after-s", type=float, default=60.0)
    parser.add_argument("--pause-s", type=float, default=60.0)
    parser.add_argument("--detection-s", type=float, default=30.0)
    parser.add_argument("--drain-limit-s", type=float, default=900.0)
    parser.add_argument("--every", type=float, default=5.0)
    parser.add_argument("--why-window", type=float, default=10.0)
    # ops.start: readiness window and timeout.
    parser.add_argument("--window", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)
    if args.source_file is not None:
        args.source = "ulog"
    try:
        result = drill(args)
    except (RunFailure, OSError, ValueError, KeyError) as error:
        category = str(error) if isinstance(error, RunFailure) else type(error).__name__
        print(
            json.dumps(
                {"run_id": args.run_id, "status": "failed", "category": category}
            )
        )
        return 2
    print(json.dumps({"run_id": args.run_id, "status": result["status"]}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
