"""Materialize F09 battery data and compare GPS and battery native times."""

import argparse
import json
import os
import runpy
from collections import Counter
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.flight_analytics.battery_time import BatteryPoint, match_publications
from telemetry.conversion_contract import integer_value, json_object, object_value
from telemetry_reader import read_battery_event

DATABASE = "f09_battery_research_v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gps", type=Path, required=True)
    parser.add_argument("--battery", type=Path, required=True)
    parser.add_argument("--battery-replay", type=Path, required=True)
    parser.add_argument("--max-age-us", type=int, required=True)
    parser.add_argument("--port", type=int, default=28132)
    args = parser.parse_args()
    coverage = runpy.run_path(str(Path(__file__).with_name("report-f09-coverage.py")))
    gps_summary = coverage["gps_summary"](args.gps)
    battery_summary = coverage["compare_battery_replays"](
        args.battery, args.battery_replay
    )
    gps_manifest = json_object((args.gps / "manifest.json").read_bytes())
    gps_bytes = coverage["_checked_file"](
        args.gps / "gps.jsonl", "sha256:" + str(gps_manifest["rows_sha256"]), 32_000_000
    )
    gps_rows = [json_object(line) for line in gps_bytes.splitlines()]
    manifest = json_object((args.battery / "run-manifest.json").read_bytes())
    artifacts = object_value(manifest["artifacts"])
    event_bytes = coverage["_checked_file"](
        args.battery / "events.jsonl",
        object_value(artifacts["events.jsonl"])["sha256"],
        32_000_000,
    )
    rows = []
    points = []
    for raw in event_bytes.splitlines():
        event = read_battery_event(raw)
        source_time = event["source_time"]
        if (
            source_time["clock_basis"] != "boot_relative"
            or source_time["timestamp_kind"] != "publication"
        ):
            raise ValueError("unsupported_battery_time")
        native = source_time["native_timestamp_us"]
        ordinal = event["source_record_index"]
        payload = event["payload"]
        points.append(BatteryPoint(ordinal, native, event["event_id"]))
        rows.append(
            {
                "event_id": event["event_id"],
                "source_ordinal": ordinal,
                "native_timestamp_us": native,
                "voltage_v": payload["voltage_v"],
                "current_a": payload["current_a"],
                "remaining_fraction": payload["remaining_fraction"],
                "event_json": raw.decode("utf-8"),
            }
        )
    gps_times = [integer_value(row["native_timestamp_us"]) for row in gps_rows]
    matches = match_publications(
        gps_times, points, battery_summary["source_records"], args.max_age_us
    )
    match_rows = [
        {
            "gps_ordinal": index,
            "gps_event_id": gps["event_id"],
            "battery_event_id": match.event_id,
            "age_us": match.age_us,
            "status": match.status,
            "max_age_us": args.max_age_us,
        }
        for index, (gps, match) in enumerate(zip(gps_rows, matches, strict=True))
    ]
    admin = HttpConfig(
        args.port,
        "default",
        "flight_admin",
        os.environ["FLIGHT_CH_ADMIN_PASSWORD"],
        timeout_seconds=15,
    )
    reader_password = os.environ["FLIGHT_CH_READER_PASSWORD"]
    reader = HttpConfig(
        args.port, DATABASE, "flight_reader", reader_password, timeout_seconds=15
    )
    gps_reader = HttpConfig(
        args.port,
        "f09_flight_analytics_v1",
        "flight_reader",
        reader_password,
        timeout_seconds=15,
    )
    if coverage["sql_gps_summary"](gps_reader) != gps_summary:
        raise ValueError("gps_sql_aggregate_mismatch")
    coverage["reconcile_gps_rows"](gps_reader, args.gps)
    exists = _request(
        admin,
        "SELECT count() FROM system.databases WHERE name={name:String} "
        "FORMAT TabSeparated",
        b"",
        parameters={"param_name": DATABASE},
    )
    if exists.strip() != b"0":
        raise ValueError("database_exists")
    _request(admin, f"CREATE DATABASE {DATABASE}", b"", write=True)
    _request(
        admin,
        f"CREATE TABLE {DATABASE}.battery_v1 (event_id String, "
        "source_ordinal UInt32, native_timestamp_us UInt64, voltage_v Float64, "
        "current_a Nullable(Float64), remaining_fraction Nullable(Float64), "
        "event_json String) ENGINE = MergeTree ORDER BY source_ordinal",
        b"",
        write=True,
    )
    _request(
        admin,
        f"CREATE TABLE {DATABASE}.gps_battery_match_v1 (gps_ordinal UInt32, "
        "gps_event_id String, battery_event_id Nullable(String), "
        "age_us Nullable(UInt64), status LowCardinality(String), max_age_us UInt64) "
        "ENGINE = MergeTree ORDER BY gps_ordinal",
        b"",
        write=True,
    )
    for start in range(0, len(rows), 500):
        body = b"".join(
            (json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n").encode()
            for row in rows[start : start + 500]
        )
        _request(
            admin,
            f"INSERT INTO {DATABASE}.battery_v1 FORMAT JSONEachRow",
            body,
            write=True,
        )
    for start in range(0, len(match_rows), 500):
        body = b"".join(
            (json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n").encode()
            for row in match_rows[start : start + 500]
        )
        _request(
            admin,
            f"INSERT INTO {DATABASE}.gps_battery_match_v1 FORMAT JSONEachRow",
            body,
            write=True,
        )
    for start in range(0, battery_summary["source_records"], 500):
        body = _request(
            admin,
            f"SELECT * FROM {DATABASE}.battery_v1 "
            "WHERE source_ordinal >= {lo:UInt32} AND source_ordinal < {hi:UInt32} "
            "ORDER BY source_ordinal FORMAT JSONEachRow",
            b"",
            parameters={"param_lo": str(start), "param_hi": str(start + 500)},
        )
        actual = [json_object(line) for line in body.splitlines()]
        expected = [row for row in rows if start <= row["source_ordinal"] < start + 500]
        if actual != expected:
            raise ValueError("battery_sql_row_mismatch")
    body = _request(
        admin, f"SELECT count() FROM {DATABASE}.battery_v1 FORMAT TabSeparated", b""
    )
    if body.strip() != str(len(rows)).encode():
        raise ValueError("battery_sql_count_mismatch")
    for start in range(0, len(match_rows), 500):
        body = _request(
            admin,
            f"SELECT * FROM {DATABASE}.gps_battery_match_v1 "
            "WHERE gps_ordinal >= {lo:UInt32} AND gps_ordinal < {hi:UInt32} "
            "ORDER BY gps_ordinal FORMAT JSONEachRow",
            b"",
            parameters={"param_lo": str(start), "param_hi": str(start + 500)},
        )
        if [json_object(line) for line in body.splitlines()] != match_rows[
            start : start + 500
        ]:
            raise ValueError("match_sql_row_mismatch")
    body = _request(
        admin,
        f"SELECT count() FROM {DATABASE}.gps_battery_match_v1 FORMAT TabSeparated",
        b"",
    )
    if body.strip() != str(len(match_rows)).encode():
        raise ValueError("match_sql_count_mismatch")
    _request(
        admin,
        f"GRANT SELECT ON {DATABASE}.battery_v1 TO flight_reader",
        b"",
        write=True,
    )
    _request(
        admin,
        f"GRANT SELECT ON {DATABASE}.gps_battery_match_v1 TO flight_reader",
        b"",
        write=True,
    )
    body = _request(
        reader, f"SELECT count() FROM {DATABASE}.battery_v1 FORMAT TabSeparated", b""
    )
    if body.strip() != str(len(rows)).encode():
        raise ValueError("battery_reader_count_mismatch")
    body = _request(
        reader,
        f"SELECT count() FROM {DATABASE}.gps_battery_match_v1 FORMAT TabSeparated",
        b"",
    )
    if body.strip() != str(len(match_rows)).encode():
        raise ValueError("match_reader_count_mismatch")
    print(
        json.dumps(
            {
                "status": "verified",
                "database": DATABASE,
                "gps_rows": len(gps_rows),
                "battery_rows": len(rows),
                "battery_rejections": battery_summary["rejected_records"],
                "max_age_us": args.max_age_us,
                "match_status_counts": dict(
                    sorted(Counter(match.status for match in matches).items())
                ),
                "privacy": "restricted",
                "limitations": [
                    "GPS and battery timestamps have different meanings",
                    "no sealed concurrent SQL snapshot",
                    "source dropouts remain unquantified",
                    "no real UTC or completeness claim",
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
