"""Run-health quality checks: one definition, each rule catches its violation.

The SQL runs in the pinned ClickHouse image with `clickhouse local` (no
network, no server) over tiny authored tables: one valid row plus one row per
check that breaks exactly that rule. No coordinate here comes from a flight.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from runtime.continuous.recording_health import F09_CHECKS, LIVE_CHECKS, health_sql

ROOT = Path(__file__).resolve().parents[1]
DASHBOARDS = ROOT / "runtime/flight_analytics/dashboards"
IMAGE = re.search(
    r"image: (clickhouse/clickhouse-server:\S+)",
    (ROOT / "compose/recording.yml").read_text(encoding="utf-8"),
)

F09_COLUMNS = (
    "event_id String, input_offset UInt64, native_timestamp_us UInt64, "
    "latitude_deg Nullable(Float64), longitude_deg Nullable(Float64), "
    "voltage_v Nullable(Float64), current_a Nullable(Float64), "
    "remaining_fraction Nullable(Float64), battery_status String, "
    "battery_age_us Nullable(UInt64), land_status String, "
    "land_age_us Nullable(UInt64), landed Nullable(UInt8), "
    "ground_contact Nullable(UInt8), maybe_landed Nullable(UInt8), "
    "vehicle_status_status String, vehicle_status_age_us Nullable(UInt64), "
    "arming_state Nullable(UInt8), nav_state Nullable(UInt8), failsafe Nullable(UInt8)"
)
F09_VALID = {
    "latitude_deg": 10.0,
    "longitude_deg": 20.0,
    "voltage_v": 12.0,
    "current_a": 1.0,
    "remaining_fraction": 0.5,
    "battery_status": "matched",
    "battery_age_us": 100,
    "land_status": "matched",
    "land_age_us": 100,
    "landed": 0,
    "ground_contact": 1,
    "maybe_landed": 0,
    "vehicle_status_status": "matched",
    "vehicle_status_age_us": 100,
    "arming_state": 2,
    "nav_state": 3,
    "failsafe": 0,
}
_NO_BATTERY = {"voltage_v": None, "current_a": None, "remaining_fraction": None}
F09_BREAKS = {
    "identity_conflicts": {"event_id": "e0", "current_a": 2.0},
    "time_order": {"native_timestamp_us": 1},
    "latitude_range": {"latitude_deg": 95.0},
    "longitude_range": {"longitude_deg": 190.0},
    "null_island": {"latitude_deg": 0.0, "longitude_deg": 0.0},
    "position_pair": {"latitude_deg": None},
    "voltage_positive": {"voltage_v": 0.0},
    "current_nonnegative": {"current_a": -2.0},
    "remaining_fraction_range": {"remaining_fraction": 1.5},
    "battery_values_iff_matched": {"battery_status": "stale", "battery_age_us": None},
    "state_values_iff_matched": {"land_status": "recording_gap", "land_age_us": None},
    "association_age": {"battery_age_us": 2_000_000},
    "status_domain": {
        "battery_status": "invented",
        "battery_age_us": None,
        **_NO_BATTERY,
    },
}
LIVE_COLUMNS = (
    "event_id String, input_offset UInt64, native_time_boot_ms UInt64, "
    "latitude_deg Float64, longitude_deg Float64, voltage_v Nullable(Float64), "
    "current_a Nullable(Float64), remaining_fraction Nullable(Float64), "
    "battery_status String, battery_receipt_age_ms Nullable(UInt64), "
    "state_status String, state_receipt_age_ms Nullable(UInt64), "
    "armed Nullable(UInt8), base_mode_code Nullable(UInt8), "
    "custom_mode_code Nullable(UInt32), system_status_code Nullable(UInt8)"
)
LIVE_VALID = {
    "latitude_deg": 10.0,
    "longitude_deg": 20.0,
    "voltage_v": 12.0,
    "current_a": 1.0,
    "remaining_fraction": 0.5,
    "battery_status": "receipt_ordered",
    "battery_receipt_age_ms": 100,
    "state_status": "receipt_ordered",
    "state_receipt_age_ms": 100,
    "armed": 0,
    "base_mode_code": 1,
    "custom_mode_code": 0,
    "system_status_code": 3,
}
LIVE_BREAKS = {
    "identity_conflicts": {"event_id": "e0", "current_a": 2.0},
    "time_order": {"native_time_boot_ms": 1},
    "latitude_range": {"latitude_deg": -95.0},
    "longitude_range": {"longitude_deg": -190.0},
    "null_island": {"latitude_deg": 0.0, "longitude_deg": 0.0},
    "voltage_nonnegative": {"voltage_v": -1.0},
    "remaining_fraction_range": {"remaining_fraction": -0.5},
    "battery_values_iff_receipt_ordered": {
        "battery_status": "stale",
        "battery_receipt_age_ms": 5000,
    },
    "state_values_iff_receipt_ordered": {
        "state_status": "none",
        "state_receipt_age_ms": None,
    },
    "receipt_age": {"battery_receipt_age_ms": 4000},
    "status_domain": {
        "state_status": "invented",
        "state_receipt_age_ms": None,
        "armed": None,
        "base_mode_code": None,
        "custom_mode_code": None,
        "system_status_code": None,
    },
}


def _rows(
    valid: dict[str, object], breaks: dict[str, dict[str, object]], time: str
) -> list[dict[str, object]]:
    rows = []
    for index, change in enumerate([{}, *breaks.values()]):
        row = {
            "event_id": f"e{index}",
            "input_offset": index,
            time: 1000 * (index + 1),
            **valid,
            **change,
        }
        rows.append(row)
    return rows


def _run(
    columns: str, rows: list[dict[str, object]], source: str
) -> list[dict[str, object]]:
    if IMAGE is None or shutil.which("docker") is None:
        pytest.skip("docker and the pinned ClickHouse image are required")
    image = IMAGE[1]
    if subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True
    ).returncode:
        pytest.skip("pinned ClickHouse image not present locally")
    body = "\n".join(json.dumps(row) for row in rows)
    assert "'" not in body
    insert = f"INSERT INTO fixture.points SELECT * FROM format(JSONEachRow, '{body}'); "
    sql = (
        "CREATE DATABASE fixture; "
        f"CREATE TABLE fixture.points ({columns}) ENGINE=Memory; "
        + (insert if rows else "")
        + health_sql(source, "fixture")
        + " FORMAT JSONEachRow"
    )
    result = subprocess.run(
        [
            *("docker", "run", "--rm", "--network", "none"),
            *("--entrypoint", "clickhouse", image, "local", "--multiquery"),
            *("--query", sql),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


@pytest.mark.parametrize(
    ("source", "columns", "valid", "breaks", "time", "checks"),
    [
        ("f09", F09_COLUMNS, F09_VALID, F09_BREAKS, "native_timestamp_us", F09_CHECKS),
        (
            "live",
            LIVE_COLUMNS,
            LIVE_VALID,
            LIVE_BREAKS,
            "native_time_boot_ms",
            LIVE_CHECKS,
        ),
    ],
)
def test_each_check_counts_exactly_its_planted_violation(
    source: str,
    columns: str,
    valid: dict[str, object],
    breaks: dict[str, dict[str, object]],
    time: str,
    checks: tuple[tuple[str, str], ...],
) -> None:
    assert set(breaks) == {name for name, _ in checks}
    result = _run(columns, _rows(valid, breaks, time), source)
    assert {
        row["check_name"]: (row["violations"], row["state"]) for row in result
    } == dict.fromkeys(breaks, (1, "fail"))
    clean = _run(columns, _rows(valid, {}, time), source)
    assert {row["state"] for row in clean} == {"ok"}
    empty = _run(columns, [], source)
    # Zero facts measure nothing: unknown, never a pass.
    assert {row["state"] for row in empty} == {"unknown"}


@pytest.mark.parametrize(
    ("template", "source"),
    [("recording-stream.json", "f09"), ("live-sitl.json", "live")],
)
def test_run_health_panel_runs_the_same_checks_as_status(
    template: str, source: str
) -> None:
    dashboard = json.loads((DASHBOARDS / template).read_text(encoding="utf-8"))
    panels = [p for p in dashboard["panels"] if p["title"] == "Run health"]
    assert len(panels) == 1
    assert [t["rawSql"] for t in panels[0]["targets"]] == [
        health_sql(source, "${database}")
    ]


def _signals(snap: dict[str, object], health: dict[str, object]) -> dict[str, str]:
    from runtime.recording.health_signals import evaluate

    return {str(r["signal"]): str(r["state"]) for r in evaluate(snap, health)}


def test_unobserved_signals_stay_unknown_never_zero() -> None:
    states = _signals({}, {"source": "f09"})
    assert set(states.values()) == {"unknown"}, states


def _running(
    archived: int, end: int, age_ms: int, memory: float, free: int
) -> dict[str, dict[str, object]]:
    clock = 10_000_000
    snap: dict[str, object] = {
        "inside": {
            "clock_ms": clock,
            "kafka": {"input_end": end},
            "progress": {
                "archive-status": {
                    "input_next": archived,
                    "written_ms": clock - age_ms,
                },
                "serving-status": {"input_archived": archived, "written_ms": clock},
            },
            "markers": {"serving-complete": False},
        }
    }
    health: dict[str, object] = {
        "source": "f09",
        "resources": {
            "containers": [
                {
                    "service": "taskmanager",
                    "memory_pct": memory,
                    "memory_limit": 1 << 30,
                    "cpu_budget_pct": 10.0,
                }
            ],
            "engine_memory": 2 << 30,
            "disk": {
                "size": 1 << 40,
                "available": free,
                "docker_available": free,
                "host_available": free,
            },
        },
    }
    return {"snap": snap, "health": health}


@pytest.mark.parametrize(
    ("archived", "age_ms", "memory", "free_runs", "expected"),
    [
        (9000, 1000, 79.9, 2.0, ("ok", "ok", "ok")),
        (8999, 1000, 80.0, 1.99, ("warn", "warn", "warn")),
        (9000, 10_001, 94.9, 1.0, ("warn", "warn", "warn")),
        (9000, 60_001, 95.0, 0.99, ("fail", "fail", "fail")),
    ],
)
def test_thresholds_give_the_declared_state(
    archived: int,
    age_ms: int,
    memory: float,
    free_runs: float,
    expected: tuple[str, str, str],
) -> None:
    from runtime.recording.health import FULL_RUN_BYTES

    case = _running(archived, 10_000, age_ms, memory, int(free_runs * FULL_RUN_BYTES))
    states = _signals(case["snap"], case["health"])
    assert (states["archive_coverage"], states["memory"], states["disk_free"]) == (
        expected
    )


def test_a_completed_run_needs_complete_coverage() -> None:
    case = _running(9999, 10_000, 0, 1.0, 1 << 40)
    inside = case["snap"]["inside"]
    assert isinstance(inside, dict)
    inside["markers"] = {"serving-complete": True}
    assert _signals(case["snap"], case["health"])["archive_coverage"] == "fail"


@pytest.mark.parametrize(
    ("final", "acked", "expected"),
    [
        (None, 1275, "ok"),
        (None, 1278, "fail"),
        (None, None, "unknown"),
        (1277, 1277, "ok"),
    ],
)
def test_live_input_end_while_running_and_at_completion(
    final: int | None, acked: int | None, expected: str
) -> None:
    # The gateway's count is per epoch and written after the acknowledgement,
    # so a running broker end may exceed it; the final count must be equal.
    snap: dict[str, object] = {
        "inside": {
            "kafka": {"input_end": 1277},
            "progress": {"gateway-status": {"published": acked}},
            "gateway_final_published": final,
            "markers": {"serving-complete": final is not None},
        }
    }
    states = _signals(snap, {"source": "live"})
    assert states["kafka_input_end"] == expected


@pytest.mark.parametrize(("signalled", "passed"), [(True, True), (False, False)])
def test_a_container_stopped_by_completion_may_report_zero_memory(
    tmp_path: Path, signalled: bool, passed: bool
) -> None:
    from runtime.recording.mvp_run import VOLUMES, _resources

    events = [{"event": "ready", "host_ms": 0}]
    events += [{"event": "completing", "host_ms": 25_000}] * signalled
    events += [{"event": "serving_complete", "host_ms": 40_000}]
    rows = [
        {
            "host_ms": t,
            "volumes": dict.fromkeys((*VOLUMES, "state"), "1MB"),
            "containers": [
                {
                    "service": "live-gateway",
                    "memory_bytes": 0 if t >= 30_000 else 1 << 20,
                    "memory_limit": 1 << 28,
                    "memory_pct": 0.0,
                }
            ],
        }
        for t in range(0, 45_000, 15_000)
    ]
    for name, lines in (("events.jsonl", events), ("resources.jsonl", rows)):
        (tmp_path / name).write_text("".join(json.dumps(x) + "\n" for x in lines))
    ok, _ = _resources(tmp_path, {"sample_gap_limit_s": 30.0})
    assert ok is passed
