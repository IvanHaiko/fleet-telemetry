"""Authored intermediate-watermark scenarios compared with the independent oracle."""

import argparse
import copy
import json
from pathlib import Path
from typing import cast

from tests.test_reference import event, scope

from battery_gate import BatteryScope
from check_battery import MIN_WATERMARK, verify, wire
from check_probe import require
from paced_source import Scheduled
from watermark_probe import run


def scenarios() -> dict[str, list[Scheduled]]:
    first = event(0, voltage=1.0)
    open_window = event(2, "1970-01-01T00:00:09.000000Z", voltage=2.0)
    late = event(4, "1970-01-01T00:00:09.000001Z")
    invalid = event(99, "1970-01-02T00:00:00.000001Z")
    changed = copy.deepcopy(first)
    cast(dict[str, object], changed["payload"])["voltage_v"] = 9.9
    inputs = [
        (first, -2001),
        (event(1, "1970-01-01T00:00:11.999000Z"), 9998),
        (open_window, 9998),
        (event(3, "1970-01-01T00:00:12.000000Z"), 9999),
        (open_window, 9999),
        (late, 9999),
        (late, 9999),
        (invalid, 9999),
        (event(5, "1970-01-01T00:00:09.001000Z"), 9999),
        (event(6, "1970-01-01T00:00:09.002000Z"), 9999),
        (event(7, "1970-01-01T00:10:02.000000Z"), 599999),
        (first, 599999),
        (event(8, "1970-01-01T00:10:02.001000Z"), 600000),
        (first, 600000),
        (event(9, "1970-01-01T00:10:11.003000Z"), 609002),
        (late, 609002),
        (event(10, vehicle="vehicle-b"), 609002),
        (invalid, 609002),
    ]
    conflicting = [
        (first, -2001),
        (event(1, vehicle="vehicle-b"), -2001),
        (event(2, "1970-01-01T00:10:02.001000Z"), 600000),
        (changed, 600000),
    ]
    return {
        "clean": [Scheduled(wire(value), watermark) for value, watermark in inputs],
        "conflict": [
            Scheduled(wire(value), watermark) for value, watermark in conflicting
        ],
        "pressure": [Scheduled(wire(event(i)), -2001) for i in range(4)],
    }


def check_schedule(
    name: str, samples: list[Scheduled], rows: list[object]
) -> dict[str, object]:
    result = verify([sample.wire for sample in samples], rows, terminal_only=False)
    dispositions = sorted(
        [
            cast(dict[str, object], row)
            for row in rows
            if cast(dict[str, object], row)["kind"] == "disposition"
        ],
        key=lambda row: cast(int, row["observation_index"]),
    )
    for index, row in enumerate(dispositions):
        if row["disposition"] != "invalid":
            previous = (
                MIN_WATERMARK if index == 0 else samples[index - 1].watermark_after
            )
            require(row["watermark_ms"] == previous, "scheduled_watermark_not_observed")
            require(
                row["window_end_ms"] == cast(int, row["window_start_ms"]) + 10000,
                "late_window_evidence_missing",
            )
    expected = {
        "clean": [
            "eligible",
            "eligible",
            "eligible",
            "eligible",
            "duplicate",
            "late",
            "duplicate",
            "invalid",
            "late",
            "late",
            "eligible",
            "duplicate",
            "eligible",
            "late",
            "eligible",
            "late",
            "late",
            "invalid",
        ],
        "conflict": ["eligible", "eligible", "eligible", "conflict"],
    }
    require(
        [row["disposition"] for row in dispositions] == expected[name],
        "authored_boundary_expectations_differ",
    )
    if name == "clean":
        state5 = cast(dict[str, int], dispositions[5]["state"])
        state9 = cast(dict[str, int], dispositions[9]["state"])
        require(
            state9["active"] > state5["active"]
            and dispositions[5]["watermark_ms"] == dispositions[9]["watermark_ms"],
            "stalled_watermark_growth_not_observed",
        )
        # Literal IDs come from the reused public fixture, not operator state.
        first_id = event(0)["event_id"]
        expiry_rows = [
            cast(dict[str, object], row)
            for row in rows
            if cast(dict[str, object], row)["kind"] == "expiry"
        ]
        require(
            any(
                row["timer_ms"] == 600000
                and row["watermark_ms"] == 600000
                and first_id in cast(list[str], row["event_ids"])
                for row in expiry_rows
            ),
            "exact_expiry_not_observed",
        )
        window_rows = [
            cast(dict[str, object], row)
            for row in rows
            if cast(dict[str, object], row)["kind"] == "window"
        ]
        require(
            any(
                row["start_ms"] == 0 and row["watermark_ms"] == 9999
                for row in window_rows
            ),
            "exact_window_close_not_observed",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument(
        "--scenario", required=True, choices=("clean", "conflict", "pressure")
    )
    args = parser.parse_args()
    reference = scope()
    selected = BatteryScope(
        reference.dataset_run_id,
        reference.pipeline_version,
        reference.source_log_id,
        reference.timestamp_min,
        reference.timestamp_max,
    )
    samples = scenarios()[args.scenario]
    rows = run(
        selected,
        samples,
        args.scratch,
        identity_limit=3 if args.scenario == "pressure" else 1023,
    )
    require(args.scenario != "pressure", "state_pressure_did_not_stop_job")
    result = check_schedule(args.scenario, samples, rows)
    print(
        json.dumps(
            {"status": "watermark_reference_match", "scenario": args.scenario, **result}
        )
    )


if __name__ == "__main__":
    main()
