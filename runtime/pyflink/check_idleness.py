"""Verify two-input idle/resume behavior against literal and reference expectations."""

import argparse
import json
from pathlib import Path
from typing import cast

from tests.test_reference import event, scope

from battery_gate import BatteryScope
from check_battery import verify, wire
from check_probe import require
from idleness_probe import run


def inputs() -> dict[str, bytes]:
    values = {
        "a0": event(0, voltage=1.0),
        "b0": event(1, voltage=2.0),
        "a12": event(2, "1970-01-01T00:00:12.000000Z", voltage=3.0),
        "b9": event(3, "1970-01-01T00:00:09.000000Z", voltage=4.0),
        "b22": event(4, "1970-01-01T00:00:22.000000Z", voltage=5.0),
        "a22": event(5, "1970-01-01T00:00:22.000000Z", voltage=6.0),
        "b32": event(6, "1970-01-01T00:00:32.000000Z", voltage=7.0),
        "a21": event(7, "1970-01-01T00:00:21.000000Z", voltage=8.0),
        "a42": event(8, "1970-01-01T00:00:42.000000Z", voltage=9.0),
        "b42": event(9, "1970-01-01T00:00:42.000000Z", voltage=10.0),
        "invalid": event(99, "1970-01-02T00:00:00.000001Z"),
    }
    return {name: wire(value) for name, value in values.items()}


def check(
    wires: list[bytes], rows: list[object], phases: list[dict[str, object]]
) -> dict[str, object]:
    result = verify(wires, rows, terminal_only=False)
    records = cast(list[dict[str, object]], rows)
    dispositions = {
        cast(int, row["observation_index"]): row
        for row in records
        if row["kind"] == "disposition"
    }
    expected_phases = (
        ("active_minimum_held", -2001),
        ("idle_excluded", 9999),
        ("resumed_old_event", 9999),
        ("resumed_input_holds_minimum", 9999),
        ("all_silent_no_eof", 19999),
        ("resume_after_both_silent", 29999),
        ("second_resumed_old_event", 29999),
        ("both_active_advanced", 39999),
    )
    require(
        [(row["phase"], row["watermark_ms"]) for row in phases]
        == list(expected_phases),
        "idleness_phase_trace_differs",
    )
    for phase in (phases[2], phases[6]):
        row = dispositions[cast(int, phase["observation_index"])]
        require(
            row["disposition"] == "late"
            and row["watermark_ms"] == phase["watermark_ms"],
            "resumed_old_event_not_late",
        )
    repeated = dispositions[cast(int, phases[2]["observation_index"]) + 1]
    require(repeated["disposition"] == "duplicate", "resumed_repeat_not_duplicate")
    require(
        sum(row["disposition"] == "invalid" for row in dispositions.values()) == 1,
        "invalid_future_not_isolated",
    )
    windows = [row for row in records if row["kind"] == "window"]
    require(
        sorted((row["start_ms"], row["watermark_ms"]) for row in windows)
        == [
            (0, 9999),
            (10000, 19999),
            (20000, 29999),
            (30000, 39999),
            (40000, 2**63 - 1),
        ],
        "idle_window_close_watermarks_differ",
    )
    require(
        sorted(
            (
                row["start_ms"],
                row["unique_events"],
                cast(dict[str, list[object]], row["measures"])["voltage_v"],
            )
            for row in windows
        )
        == [
            (0, 2, [2, "3"]),
            (10000, 1, [1, "3"]),
            (20000, 2, [2, "11"]),
            (30000, 1, [1, "7"]),
            (40000, 2, [2, "19"]),
        ],
        "literal_idle_windows_differ",
    )
    return {"status": "idleness_reference_match", "phases": phases, **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", required=True, type=Path)
    args = parser.parse_args()
    reference = scope()
    selected = BatteryScope(
        reference.dataset_run_id,
        reference.pipeline_version,
        reference.source_log_id,
        reference.timestamp_min,
        reference.timestamp_max,
    )
    wires, rows, phases = run(selected, inputs(), args.scratch)
    print(json.dumps(check(wires, rows, phases)), flush=True)


if __name__ == "__main__":
    main()
