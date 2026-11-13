"""Compare real bounded operator output with the independent M3 reference."""

import argparse
import copy
import json
from pathlib import Path
from typing import cast

from telemetry_reference import (
    EndOfInput,
    Observation,
    ReferenceScope,
    TraceStep,
    Watermark,
    calculate_windows,
    epoch_milliseconds,
)
from tests.test_reference import event, scope

from battery_gate import BatteryScope
from battery_probe import run
from check_probe import require

MIN_WATERMARK = -(2**63)
MAX_WATERMARK = 2**63 - 1


def wire(value: dict[str, object]) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


def scenarios() -> dict[str, list[bytes]]:
    """Reuse authored source/identity fixtures; keep calculation logic independent."""
    first = event(timestamp="1969-12-31T23:59:59.999999Z", current=0.1)
    repeated = copy.deepcopy(first)
    repeated["ingest_timestamp"] = "1970-01-03T00:00:00.000000Z"
    cast(dict[str, object], repeated["payload"]).pop("remaining_fraction")
    second = event(1, "1970-01-01T00:00:09.999999Z", voltage=2.0, remaining=0.3)
    numeric_copy = copy.deepcopy(second)
    cast(dict[str, object], numeric_copy["payload"])["voltage_v"] = 2
    same_ms = event(
        6, "1970-01-01T00:00:09.999001Z", voltage=0.1, current=0.0, remaining=0.0
    )
    exact_edge = event(7, "1970-01-01T00:00:10.000000Z", voltage=0.2)
    third = event(2, "1970-01-01T00:00:10.000001Z", current=-0.2)
    other = event(3, "1970-01-01T00:00:09.999999Z", vehicle="vehicle-b")
    future = event(4, "1970-01-02T00:00:00.000001Z")
    wrong_run = event(5)
    wrong_run["delivery"] = {"dataset_run_id": "other-run", "replay_mode": "synthetic"}
    conflict = copy.deepcopy(second)
    conflict["payload"] = {
        "voltage_v": 9.9,
        "current_a": None,
        "remaining_fraction": 0.3,
    }
    return {
        "clean": [
            wire(v)
            for v in (
                first,
                repeated,
                second,
                numeric_copy,
                same_ms,
                exact_edge,
                third,
                other,
                future,
                wrong_run,
            )
        ]
        + [b"private-invalid-payload"],
        # Include another vehicle to check whole-run invalidation, not per-key release.
        "conflict": [wire(v) for v in (other, second, conflict, second)],
        "empty": [],
    }


def verify(
    wires: list[bytes], rows: list[object], *, terminal_only: bool = True
) -> dict[str, object]:
    """Require complete dispositions, exact aggregates and observed timer cleanup."""
    require(all(isinstance(row, dict) for row in rows), "invalid_operator_output")
    records = cast(list[dict[str, object]], rows)
    require(
        all(row.get("kind") in {"disposition", "window", "expiry"} for row in records),
        "unknown_operator_output",
    )
    dispositions = sorted(
        [row for row in records if row["kind"] == "disposition"],
        key=lambda row: cast(int, row["observation_index"]),
    )
    require(
        [row["observation_index"] for row in dispositions] == list(range(len(wires))),
        "incomplete_operator_dispositions",
    )
    trace: list[TraceStep] = []
    observed_watermark = MIN_WATERMARK
    registered: dict[str, tuple[int, str]] = {}
    for value, row in zip(wires, dispositions, strict=True):
        if row["disposition"] != "invalid":
            watermark = cast(int, row["watermark_ms"])
            require(watermark >= observed_watermark, "decreasing_observed_watermark")
            if terminal_only:
                require(watermark == MIN_WATERMARK, "unexpected_nonterminal_watermark")
            if watermark > observed_watermark:
                trace.append(Watermark(watermark))
                observed_watermark = watermark
            raw = cast(dict[str, str], json.loads(value))
            expiry = epoch_milliseconds(raw["source_timestamp"]) + 600_000
            if row["disposition"] in {"eligible", "late"} and expiry > watermark:
                registered[raw["event_id"]] = expiry, raw["vehicle_id"]
            require(
                row["assigned_ms"] == epoch_milliseconds(raw["source_timestamp"]),
                "measurement_timestamp_changed",
            )
        else:
            require("assigned_ms" not in row, "invalid_event_was_timestamped")
        trace.append(Observation(value))
    trace.append(EndOfInput())
    expected = calculate_windows(scope(), trace)
    actual_dispositions = [
        (row["observation_index"], row["disposition"], row["reason"], row["event_id"])
        for row in dispositions
    ]
    require(
        actual_dispositions
        == [
            (row.observation_index, row.kind, row.reason, row.event_id)
            for row in expected.dispositions
        ],
        "operator_dispositions_differ",
    )
    conflict_free = not any(row["disposition"] == "conflict" for row in dispositions)
    require(conflict_free == expected.conflict_free, "conflict_status_differs")
    provisional = [row for row in records if row["kind"] == "window"]
    windows = provisional if conflict_free else []
    actual = []
    for row in windows:
        measures = cast(dict[str, list[int | str]], row["measures"])
        require(
            cast(int, row["watermark_ms"]) >= cast(int, row["end_ms"]) - 1,
            "premature_window_timer",
        )
        if terminal_only:
            require(row["watermark_ms"] == MAX_WATERMARK, "nonterminal_window_timer")
        actual.append(
            (
                row["dataset_run_id"],
                row["pipeline_version"],
                row["vehicle_id"],
                row["start_ms"],
                row["end_ms"],
                row["unique_events"],
                *[
                    (measures[k][0], measures[k][1] if measures[k][0] else None)
                    for k in ("voltage_v", "current_a", "remaining_fraction")
                ],
            )
        )
    required = [
        (
            w.dataset_run_id,
            w.pipeline_version,
            w.vehicle_id,
            w.start_ms,
            w.end_ms,
            w.unique_events,
            *[
                (m.count, str(m.total) if m.count else None)
                for m in (w.voltage, w.current, w.remaining)
            ],
        )
        for w in expected.windows
    ]
    require(sorted(actual) == sorted(required), "operator_windows_differ")
    expiries = [row for row in records if row["kind"] == "expiry"]
    expired_ids = [
        event_id for row in expiries for event_id in cast(list[str], row["event_ids"])
    ]
    require(sorted(expired_ids) == sorted(registered), "identity_cleanup_incomplete")
    for row in expiries:
        ids = cast(list[str], row["event_ids"])
        require(len(ids) == row["expired"], "expiry_count_differs")
        require(
            all(registered[key][0] == row["timer_ms"] for key in ids),
            "identity_expiry_boundary_differs",
        )
        require(
            cast(int, row["watermark_ms"]) >= cast(int, row["timer_ms"]),
            "premature_identity_cleanup",
        )
    vehicles = {vehicle for _, vehicle in registered.values()}
    for vehicle in vehicles:
        timers = [row for row in expiries if row["vehicle_id"] == vehicle]
        require(
            bool(timers)
            and (
                not terminal_only
                or all(row["watermark_ms"] == MAX_WATERMARK for row in timers)
            ),
            "terminal_cleanup_not_observed",
        )
        last = max(timers, key=lambda row: cast(int, row["timer_ms"]))
        require(last["active_remaining"] == 0, "active_state_not_empty")
    return {
        "conflict_free": conflict_free,
        "released_windows": len(windows),
        "provisional_windows": len(provisional),
        "observations": len(wires),
        "expired_identities": len(registered),
        "reconciled_identities": expected.reconciled_identities,
        "reference": "battery-window-reference-v1",
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    reference: ReferenceScope = scope()
    selected = BatteryScope(
        reference.dataset_run_id,
        reference.pipeline_version,
        reference.source_log_id,
        reference.timestamp_min,
        reference.timestamp_max,
    )
    results = {}
    for name, wires in scenarios().items():
        rows = run(selected, wires, args.scratch / name)
        results[name] = verify(wires, rows)
        print(json.dumps({"scenario": name, **results[name]}), flush=True)
    print(
        json.dumps(
            {"status": "battery_operator_reference_match", "scenarios": len(results)}
        )
    )


if __name__ == "__main__":
    main()
