"""Sample one recording run's progress on a single clock for later analysis.

Runs in its own container in the storage network namespace with the evidence
volume mounted read-only. Each sample records the producer, archive and serving
status files and the set of SQL-visible GPS input offsets. Offsets are ordinal
positions, not measurement or vehicle identifiers. A failed observation is
recorded as an explicit error, never as an unchanged value. It changes nothing
in the run and stops by itself once every expected fact has been visible for
the settle time, on SIGTERM, or at its lifetime bound.

For a live SITL session (ADR-0054) the gateway status stands in for the
producer, and each sample also records the `live_state` connection and ages
with flags for which current values are shown, never the values themselves.
"""

import argparse
import json
import signal
import time
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.conversion_contract import json_object, string_value
from telemetry.local_io import read_bounded

_MAX_LIFETIME_S = 4 * 3600


def _status(path: Path) -> dict[str, object]:
    try:
        return json_object(read_bounded(path, 65536))
    except (OSError, ValueError):
        return {}


def observe(
    private: Path, evidence: Path, out: Path, expected: int, interval: float
) -> int:
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    live = (private / "live-run.json").exists()
    plan = "live-run.json" if live else "run.json"
    run = json_object(read_bounded(private / plan, 65536))
    database = string_value(run["database"])
    state = evidence / string_value(run["run_id"]) / "state"
    sql = HttpConfig(
        8123, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
    )
    stopped = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    seen: set[int] = set()
    complete_at: int | None = None
    began = time.monotonic()
    count = 0
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        while not stopped and time.monotonic() - began < _MAX_LIFETIME_S:
            tick = time.monotonic()
            now = time.time_ns() // 1_000_000
            producer = _status(
                state / ("gateway-status.json" if live else "producer-status.json")
            )
            archive = _status(state / "archive-status.json")
            serving = _status(state / "serving-status.json")
            error = None
            new: list[int] = []
            try:
                body = _request(
                    sql,
                    f"SELECT DISTINCT input_offset FROM {database}.facts FORMAT TSV",
                    b"",
                )
                new = sorted({int(value) for value in body.split()} - seen)
            except Exception as failure:  # recorded, never hidden
                error = type(failure).__name__
            seen.update(new)
            shown: object = None
            if live:
                try:
                    body = _request(
                        sql,
                        "SELECT connection, collector_age_ms, serving_age_ms, "
                        "source_receipt_age_ms, position_receipt_age_ms, "
                        "battery_status, state_status, "
                        "latitude_deg IS NOT NULL AS position_shown, "
                        "voltage_v IS NOT NULL AS battery_shown, "
                        "armed IS NOT NULL AS state_shown "
                        f"FROM {database}.live_state FORMAT JSONEachRow",
                        b"",
                    )
                    shown = json_object(body.splitlines()[0])
                except Exception as failure:  # recorded, never hidden
                    error = error or type(failure).__name__
            row = {
                "t_ms": now,
                "ack": producer.get("published" if live else "acknowledged"),
                "producer": producer.get("status"),
                "archived": archive.get("input_next"),
                "serving_archived": serving.get("input_archived"),
                "serving_logical": serving.get("logical_facts"),
                "visible": len(seen),
                "new": new,
                "error": error,
                **({"live": shown} if live else {}),
            }
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            count += 1
            done = (
                (state / "serving-complete.json").exists()
                if live
                else producer.get("status") == "completed" and len(seen) >= expected
            )
            if done:
                complete_at = complete_at or now
                if now - complete_at > 20_000:
                    break
            time.sleep(max(0.0, interval - (time.monotonic() - tick)))
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected", type=int, required=True)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args(argv)
    if not 0.5 <= args.interval <= 10 or not 0 <= args.expected <= 100_000:
        print(json.dumps({"status": "failed", "category": "observe_bounds"}))
        return 2
    try:
        samples = observe(
            args.private, args.evidence, args.out, args.expected, args.interval
        )
    except Exception as error:
        print(json.dumps({"status": "failed", "category": type(error).__name__}))
        return 2
    print(json.dumps({"status": "finished", "samples": samples}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
