"""Data-quality checks and storage footprint of one recording run.

One definition of every check serves two readers: the operations status
(through `recording_status.py health`, in the storage network namespace) and
the dashboard's *Run health* panel, whose SQL in the dashboard templates must
equal `health_sql` (a test holds them together). Each check counts violations
of a rule declared in docs/data-contracts.md or by the processing contract
(ADR-0049, ADR-0052, ADR-0054); no bound is derived from the data. A check
over zero facts is `unknown`, never a pass.

The SQL is one aggregate scan of the run's `points` view, so it stays within
the Grafana identity's read budget (50,000 rows) and needs no subquery,
window function or join. Time order compares neighbours of the
input-offset-sorted array instead of a window. Coordinate checks return
violation counts only, never values.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.s3.archive_store import Listing
from runtime.s3.boto_transport import make_client
from telemetry.conversion_contract import (
    integer_value,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded

type Document = dict[str, object]

# The Grafana panels' own read-only budgets (tests/test_recording_dashboard.py).
SETTINGS = (
    "readonly=1,max_execution_time=10,max_threads=1,max_memory_usage=268435456,"
    "max_rows_to_read=50000,max_bytes_to_read=64000000,read_overflow_mode='throw',"
    "max_result_rows=4096,max_result_bytes=4194304,result_overflow_mode='throw'"
)
F09_AGE_US = 1_000_000  # recording job max_age_us (ADR-0052)
LIVE_AGE_MS = 3000  # live session max_receipt_age_ms (ADR-0054)


def _order(column: str) -> str:
    """Violations of non-decreasing native time along input offsets."""
    ordered = (
        f"arrayMap(x -> x.2, arraySort(groupArray(tuple(input_offset, {column}))))"
    )
    pairs = f"arrayPopBack({ordered}), arrayPopFront({ordered})"
    return f"arrayCount((a, b) -> b < a, {pairs})"


def _any(names: tuple[str, ...]) -> str:
    return "(" + " OR ".join(f"isNotNull({n})" for n in names) + ")"


def _present_iff(
    status: str, matched: str, required: tuple[str, ...], values: tuple[str, ...]
) -> str:
    """Required values exist when matched; every value is NULL otherwise."""
    missing = "(" + " OR ".join(f"isNull({n})" for n in required) + ")"
    return f"if({status} = '{matched}', {missing}, {_any(values)})"


def _age_f09(group: str) -> str:
    age = f"{group}_age_us"
    return (
        f"if({group}_status = 'matched', isNull({age}) OR {age} > {F09_AGE_US}, "
        f"isNotNull({age}))"
    )


def _age_live(group: str) -> str:
    status, age, limit = f"{group}_status", f"{group}_receipt_age_ms", LIVE_AGE_MS
    return (
        f"multiIf({status} = 'receipt_ordered', isNull({age}) OR {age} > {limit}, "
        f"{status} = 'stale', isNull({age}) OR {age} <= {limit}, isNotNull({age}))"
    )


_COMMON = (
    # Equal identity with different content is a conflict (data-contracts.md).
    ("identity_conflicts", "toInt64(count()) - toInt64(uniqExact(event_id))"),
    ("latitude_range", "countIf(latitude_deg < -90 OR latitude_deg > 90)"),
    ("longitude_range", "countIf(longitude_deg < -180 OR longitude_deg > 180)"),
    # Unknown position is NULL, never (0, 0) by convention (data-contracts.md).
    ("null_island", "countIf(latitude_deg = 0 AND longitude_deg = 0)"),
    (
        "remaining_fraction_range",
        "countIf(remaining_fraction < 0 OR remaining_fraction > 1)",
    ),
)
_LAND = ("landed", "ground_contact", "maybe_landed")
_COMMANDER = ("arming_state", "nav_state", "failsafe")
_BATTERY = ("voltage_v", "current_a", "remaining_fraction")
F09_CHECKS = (
    *_COMMON,
    ("time_order", _order("native_timestamp_us")),
    ("position_pair", "countIf(isNull(latitude_deg) != isNull(longitude_deg))"),
    # ULog battery policy: positive volts, nonnegative amperes (data-contracts.md).
    ("voltage_positive", "countIf(voltage_v <= 0)"),
    ("current_nonnegative", "countIf(current_a < 0)"),
    (
        "battery_values_iff_matched",
        "countIf("
        + _present_iff("battery_status", "matched", ("voltage_v",), _BATTERY)
        + ")",
    ),
    (
        "state_values_iff_matched",
        f"countIf({_present_iff('land_status', 'matched', _LAND, _LAND)} OR "
        + _present_iff("vehicle_status_status", "matched", _COMMANDER, _COMMANDER)
        + ")",
    ),
    (
        "association_age",
        f"countIf({_age_f09('battery')} OR {_age_f09('land')} OR "
        f"{_age_f09('vehicle_status')})",
    ),
    (
        "status_domain",
        "countIf(battery_status NOT IN "
        "('matched','before_first','stale','rejection_gap') OR land_status NOT IN "
        "('matched','before_first','stale','recording_gap') OR vehicle_status_status "
        "NOT IN ('matched','before_first','stale','recording_gap'))",
    ),
)
_STATE = ("armed", "base_mode_code", "custom_mode_code", "system_status_code")
LIVE_CHECKS = (
    *_COMMON,
    ("time_order", _order("native_time_boot_ms")),
    # Canonical battery: finite, nonnegative volts (data-contracts.md).
    ("voltage_nonnegative", "countIf(voltage_v < 0)"),
    (
        "battery_values_iff_receipt_ordered",
        "countIf(battery_status != 'receipt_ordered' AND " + _any(_BATTERY) + ")",
    ),
    (
        "state_values_iff_receipt_ordered",
        "countIf(state_status != 'receipt_ordered' AND " + _any(_STATE) + ")",
    ),
    ("receipt_age", f"countIf({_age_live('battery')} OR {_age_live('state')})"),
    (
        "status_domain",
        "countIf(battery_status NOT IN "
        "('receipt_ordered','stale','unknown_after_restart','none') OR state_status "
        "NOT IN ('receipt_ordered','stale','unknown_after_restart','none'))",
    ),
)


def health_sql(source: str, database: str) -> str:
    """One row per check: name, violations, state over the `points` view."""
    checks = LIVE_CHECKS if source == "live" else F09_CHECKS
    rows = ",".join(f"tuple('{name}',toInt64({sql}))" for name, sql in checks)
    return (
        f"SELECT tupleElement(arrayJoin([{rows}]) AS r,1) AS check_name,"
        "tupleElement(r,2) AS violations,"
        "multiIf(uniqExact(event_id) = 0,'unknown',tupleElement(r,2) = 0,'ok','fail')"
        f" AS state FROM {database}.points LIMIT 32 SETTINGS {SETTINGS}"
    )


def _rows(config: HttpConfig, sql: str) -> list[Document]:
    body = _request(config, sql + " FORMAT JSONEachRow", b"")
    return [json_object(line) for line in body.splitlines() if line.strip()]


def _bytes(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def _archive_bytes(keys: Document, bucket: str, prefix: str) -> int:
    client = cast(
        Listing,
        make_client(
            endpoint="http://127.0.0.1:8333",
            region="us-east-1",
            access_key=string_value(keys["access_key"]),
            secret_key=string_value(keys["secret_key"]),
        ),
    )
    total, token = 0, None
    for _ in range(1000):  # at most 1,000,000 objects
        args: dict[str, object] = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            args["ContinuationToken"] = token
        page = object_value(client.list_objects_v2(**args))
        for item in cast(list[object], page.get("Contents") or []):
            total += integer_value(object_value(item)["Size"])
        if not page.get("IsTruncated"):
            return total
        token = string_value(page["NextContinuationToken"])
    raise ValueError("archive_listing_bound")


def measure(private: Path, evidence: Path, state: Path) -> Document:
    """Quality checks and the run's footprint; a failed part is an error, not 0."""
    live = (private / "live-run.json").exists()
    plan = json_object(
        read_bounded(private / ("live-run.json" if live else "run.json"), 65536)
    )
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    run_id, database = string_value(plan["run_id"]), string_value(plan["database"])
    config = HttpConfig(
        8123, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
    )
    out: Document = {"status": "ok", "source": "live" if live else "f09"}
    try:
        out["quality"] = _rows(config, health_sql(str(out["source"]), database))
    except Exception as failure:  # recorded, never hidden
        out["quality_error"] = type(failure).__name__
    footprint: Document = {
        "evidence_bytes": _bytes(evidence / run_id),
        "state_bytes": _bytes(state / f"{run_id}-checkpoints"),
    }
    try:
        parts = _rows(
            config,
            "SELECT sum(bytes_on_disk) AS bytes FROM system.parts "
            f"WHERE database = '{database}' AND active",
        )
        footprint["sql_bytes"] = parts[0]["bytes"]
    except Exception as failure:
        footprint["sql_error"] = type(failure).__name__
    try:
        keys = object_value(object_value(secrets["s3"])["reader"])
        footprint["archive_bytes"] = _archive_bytes(
            keys, string_value(plan["bucket"]), f"archive-v1/{run_id}/"
        )
    except Exception as failure:
        footprint["archive_error"] = type(failure).__name__
    out["footprint"] = footprint
    return out
