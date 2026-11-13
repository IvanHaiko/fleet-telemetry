"""Summarize and reconcile the restricted, prepared F09 research artifacts."""

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.conversion_contract import (
    SEMANTIC_FIELDS,
    integer_value,
    json_line,
    json_object,
    object_value,
)
from telemetry_reader import read_battery_event
from ulog_integrity import F09_SOURCE_ID

DATABASE = "f09_flight_analytics_v1"


def _checked_file(path: Path, expected: object, limit: int) -> bytes:
    if path.stat().st_size > limit:
        raise ValueError("artifact_size_limit")
    data = path.read_bytes()
    if len(data) > limit or "sha256:" + hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("artifact_hash_mismatch")
    return data


def gps_summary(directory: Path) -> dict[str, object]:
    """Summarize a hash-checked GPS delivery, refusing missing or duplicate rows."""
    manifest = json_object((directory / "manifest.json").read_bytes())
    if (
        manifest.get("profile") != "f09-gps-research-v1"
        or manifest.get("source_id") != F09_SOURCE_ID
    ):
        raise ValueError("gps_profile_mismatch")
    data = _checked_file(
        directory / "gps.jsonl",
        "sha256:" + str(manifest.get("rows_sha256")),
        32_000_000,
    )
    rows = [json_object(line) for line in data.splitlines()]
    if not rows or len(rows) != manifest.get("records"):
        raise ValueError("gps_count_mismatch")
    if [r.get("source_ordinal") for r in rows] != list(range(len(rows))):
        raise ValueError("gps_ordinal_mismatch")
    ids = [r.get("event_id") for r in rows]
    if any(not isinstance(v, str) or not v for v in ids) or len(set(ids)) != len(rows):
        raise ValueError("gps_identity_mismatch")
    fixes: Counter[int] = Counter()
    positions = speeds = utc = 0
    for row in rows:
        fix = row.get("fix_type")
        if type(fix) is not int or not 0 <= fix <= 255:
            raise ValueError("gps_fix_invalid")
        fixes[fix] += 1
        positions += int(
            row.get("latitude_deg") is not None and row.get("longitude_deg") is not None
        )
        speeds += int(row.get("ground_speed_m_s") is not None)
        utc += int(row.get("gps_utc") is not None)
    result: dict[str, object] = {
        "records": len(rows),
        "valid_positions": positions,
        "valid_ground_speed": speeds,
        "gps_utc_nonzero": utc,
        "fix_counts": {str(k): v for k, v in sorted(fixes.items())},
    }
    if any(
        result[k] != manifest.get(k)
        for k in ("valid_positions", "valid_ground_speed", "gps_utc_nonzero")
    ):
        raise ValueError("gps_manifest_mismatch")
    return result


def sql_gps_summary(config: HttpConfig) -> dict[str, object]:
    """Read aggregate coverage using the existing SELECT-only account."""
    body = _request(
        config,
        "SELECT fix_type, count() AS records, "
        "countIf(isNotNull(latitude_deg) AND isNotNull(longitude_deg)) AS positions, "
        "countIf(isNotNull(ground_speed_m_s)) AS speeds, "
        f"countIf(isNotNull(gps_utc)) AS utc FROM {DATABASE}.gps_v1 "
        "GROUP BY fix_type ORDER BY fix_type SETTINGS max_execution_time=10, "
        "max_threads=1, max_memory_usage=268435456, max_rows_to_read=100000, "
        "read_overflow_mode='throw' FORMAT JSONEachRow",
        b"",
    )
    rows = [json_object(line) for line in body.splitlines()]
    return {
        "records": sum(integer_value(r["records"]) for r in rows),
        "valid_positions": sum(integer_value(r["positions"]) for r in rows),
        "valid_ground_speed": sum(integer_value(r["speeds"]) for r in rows),
        "gps_utc_nonzero": sum(integer_value(r["utc"]) for r in rows),
        "fix_counts": {
            str(integer_value(r["fix_type"])): integer_value(r["records"]) for r in rows
        },
    }


def reconcile_gps_rows(config: HttpConfig, directory: Path) -> None:
    """Compare every stored typed field and original JSON, in bounded batches."""
    manifest = json_object((directory / "manifest.json").read_bytes())
    data = _checked_file(
        directory / "gps.jsonl",
        "sha256:" + str(manifest.get("rows_sha256")),
        32_000_000,
    )
    lines = data.splitlines()
    for start in range(0, len(lines), 1000):
        body = _request(
            config,
            f"SELECT * FROM {DATABASE}.gps_v1 WHERE source_ordinal >= {{lo:UInt32}} "
            "AND source_ordinal < {hi:UInt32} ORDER BY source_ordinal "
            "SETTINGS max_execution_time=10, max_threads=1, "
            "max_memory_usage=268435456, max_rows_to_read=100000, "
            "read_overflow_mode='throw' FORMAT JSONEachRow",
            b"",
            parameters={"param_lo": str(start), "param_hi": str(start + 1000)},
        )
        actual = [json_object(line) for line in body.splitlines()]
        expected = lines[start : start + 1000]
        if len(actual) != len(expected):
            raise ValueError("gps_sql_row_count_mismatch")
        for row, original in zip(actual, expected, strict=True):
            if row.pop("row_json", None) != original.decode("utf-8"):
                raise ValueError("gps_sql_raw_mismatch")
            stamp = row.get("gps_utc")
            if isinstance(stamp, str):
                row["gps_utc"] = (
                    datetime.fromisoformat(stamp)
                    .replace(tzinfo=UTC)
                    .isoformat(timespec="microseconds")
                    .replace("+00:00", "Z")
                )
            if row != json_object(original):
                raise ValueError("gps_sql_typed_mismatch")


def battery_summary(directory: Path) -> dict[str, object]:
    """Check the bounded replay and account for each admitted/rejected ordinal."""
    manifest = json_object((directory / "run-manifest.json").read_bytes())
    if (
        manifest.get("source_log_id") != F09_SOURCE_ID
        or manifest.get("normalization_version") != "ulog-battery-f09-research-v1"
        or manifest.get("source_stream") != "battery_status:0"
    ):
        raise ValueError("battery_profile_mismatch")
    artifacts = object_value(manifest["artifacts"])
    counts = object_value(manifest["counts"])
    records: set[int] = set()
    ids: set[str] = set()
    available: Counter[str] = Counter()
    ranges: dict[str, list[float]] = {}
    semantics: dict[int, bytes] = {}
    rejections: dict[int, bytes] = {}
    for line in _checked_file(
        directory / "events.jsonl",
        object_value(artifacts["events.jsonl"])["sha256"],
        32_000_000,
    ).splitlines():
        event = read_battery_event(line)
        ordinal = event["source_record_index"]
        event_id = event["event_id"]
        if ordinal in records or event_id in ids:
            raise ValueError("battery_duplicate")
        records.add(ordinal)
        ids.add(event_id)
        raw_event = json_object(line)
        semantics[ordinal] = json_line(
            {
                "event_id": event_id,
                "measurement": {k: raw_event[k] for k in SEMANTIC_FIELDS},
            }
        )
        payload = event["payload"]
        for name, value in (
            ("voltage_v", payload["voltage_v"]),
            ("current_a", payload["current_a"]),
            ("remaining_fraction", payload["remaining_fraction"]),
        ):
            if value is not None:
                available[name] += 1
                if name not in ranges:
                    ranges[name] = [value, value]
                else:
                    ranges[name] = [
                        min(ranges[name][0], value),
                        max(ranges[name][1], value),
                    ]
    reasons: Counter[str] = Counter()
    for line in _checked_file(
        directory / "rejections.jsonl",
        object_value(artifacts["rejections.jsonl"])["sha256"],
        1_000_000,
    ).splitlines():
        row = json_object(line)
        rejected_ordinal = row.get("source_record_index")
        reason = row.get("reason_code")
        if (
            type(rejected_ordinal) is not int
            or rejected_ordinal < 0
            or rejected_ordinal in records
            or not isinstance(reason, str)
            or row.get("source_stream") != "battery_status:0"
        ):
            raise ValueError("battery_rejection_invalid")
        records.add(rejected_ordinal)
        rejections[rejected_ordinal] = json_line(row)
        reasons[reason] += 1
    source_count = counts.get("source_records")
    if (
        type(source_count) is not int
        or source_count < 0
        or source_count > 100_000
        or records != set(range(source_count))
        or len(ids) != counts.get("admitted_records")
        or sum(reasons.values()) != counts.get("rejected_records")
        or dict(reasons) != manifest.get("rejection_reasons")
    ):
        raise ValueError("battery_reconciliation_mismatch")
    return {
        "source_records": source_count,
        "admitted_records": len(ids),
        "rejected_records": sum(reasons.values()),
        "rejection_reasons": dict(sorted(reasons.items())),
        "available_fields": dict(sorted(available.items())),
        "admitted_value_ranges": dict(sorted(ranges.items())),
        "semantic_sha256": hashlib.sha256(
            b"".join(semantics[k] for k in sorted(semantics))
        ).hexdigest(),
        "rejections_sha256": hashlib.sha256(
            b"".join(rejections[k] for k in sorted(rejections))
        ).hexdigest(),
    }


def compare_battery_replays(first: Path, second: Path) -> dict[str, object]:
    """Require distinct run identities and matching measurement outcomes."""
    if first.resolve() == second.resolve():
        raise ValueError("battery_replay_not_distinct")
    first_manifest = json_object((first / "run-manifest.json").read_bytes())
    second_manifest = json_object((second / "run-manifest.json").read_bytes())
    first_id = first_manifest.get("dataset_run_id")
    second_id = second_manifest.get("dataset_run_id")
    if (
        not isinstance(first_id, str)
        or not first_id
        or not isinstance(second_id, str)
        or not second_id
        or first_id == second_id
    ):
        raise ValueError("battery_replay_not_distinct")
    result = battery_summary(first)
    if battery_summary(second) != result:
        raise ValueError("battery_replay_mismatch")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gps", type=Path, required=True)
    parser.add_argument("--battery", type=Path, required=True)
    parser.add_argument("--battery-replay", type=Path, required=True)
    parser.add_argument("--port", type=int, default=28132)
    args = parser.parse_args()
    gps = gps_summary(args.gps)
    battery = compare_battery_replays(args.battery, args.battery_replay)
    config = HttpConfig(
        args.port,
        DATABASE,
        "flight_reader",
        os.environ["FLIGHT_CH_READER_PASSWORD"],
        timeout_seconds=15,
    )
    if sql_gps_summary(config) != gps:
        raise ValueError("gps_sql_aggregate_mismatch")
    reconcile_gps_rows(config, args.gps)
    print(
        json.dumps(
            {
                "profile": "f09-research-coverage-v1",
                "privacy": "restricted",
                "gps": gps,
                "battery": battery,
                "gps_sql_aggregate_matches": True,
                "gps_sql_rows_match": True,
                "battery_replays_match": True,
                "limitations": [
                    "SQL reads do not form a sealed concurrent snapshot",
                    "source dropouts do not quantify missing records",
                    "battery time uses a synthetic anchor",
                    "no GPS/battery time join or flight completeness claim",
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
