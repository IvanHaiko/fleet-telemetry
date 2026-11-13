"""Load or read-check the isolated F09 state table and save a restricted report."""

import argparse
import json
import os
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.flight_analytics.state import read_prepared, summarize
from telemetry.conversion_contract import json_object

DATABASE = "f09_state_research_v1"
TABLE = f"{DATABASE}.state_v1"
BOUNDS = (
    " SETTINGS max_execution_time=10, max_threads=1, "
    "max_memory_usage=268435456, max_rows_to_read=10000, "
    "max_bytes_to_read=8000000, read_overflow_mode='throw'"
)


def reconcile(config: HttpConfig, rows: list[dict[str, object]]) -> None:
    """Compare every typed column, identity and original row; reject extra copies."""
    body = _request(
        config,
        f"SELECT * FROM {TABLE} ORDER BY stream, source_ordinal"
        + BOUNDS
        + " FORMAT JSONEachRow",
        b"",
    )
    actual = [json_object(line) for line in body.splitlines()]
    expected = sorted(
        rows, key=lambda row: (str(row["stream"]), int(str(row["source_ordinal"])))
    )
    if len(actual) != len(expected):
        raise ValueError("state_sql_count_mismatch")
    for stored, original in zip(actual, expected, strict=True):
        raw = stored.pop("row_json", None)
        if stored != original or raw != json.dumps(original, separators=(",", ":")):
            raise ValueError("state_sql_row_mismatch")


def load(admin: HttpConfig, reader: HttpConfig, rows: list[dict[str, object]]) -> None:
    """Create a fresh scope; preserve ambiguous or partial writes for inspection."""
    exists = _request(
        admin,
        "SELECT count() FROM system.databases "
        "WHERE name={name:String} FORMAT TabSeparated",
        b"",
        parameters={"param_name": DATABASE},
    )
    if exists.strip() != b"0":
        raise ValueError("database_exists")
    _request(admin, f"CREATE DATABASE {DATABASE}", b"", write=True)
    _request(
        admin,
        f"CREATE TABLE {TABLE} (event_id String, stream String, "
        "source_ordinal UInt32, native_timestamp_us UInt64, "
        "landed Nullable(UInt8), ground_contact Nullable(UInt8), "
        "maybe_landed Nullable(UInt8), arming_state Nullable(UInt8), "
        "nav_state Nullable(UInt8), failsafe Nullable(UInt8), row_json String) "
        "ENGINE = MergeTree ORDER BY (stream, source_ordinal)",
        b"",
        write=True,
    )
    for start in range(0, len(rows), 500):
        body = b"".join(
            (
                json.dumps(
                    {**row, "row_json": json.dumps(row, separators=(",", ":"))},
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            ).encode()
            for row in rows[start : start + 500]
        )
        _request(
            admin,
            f"INSERT INTO {TABLE} SETTINGS async_insert=0 FORMAT JSONEachRow",
            body,
            write=True,
        )
    reconcile(admin, rows)
    _request(admin, f"GRANT SELECT ON {TABLE} TO flight_reader", b"", write=True)
    reconcile(reader, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("load", "report"))
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--port", type=int, default=28132)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("report_exists")
    if not args.report.parent.is_dir():
        raise ValueError("report_parent_missing")
    rows = read_prepared(args.prepared)
    reader = HttpConfig(
        args.port,
        "default",
        "flight_reader",
        os.environ["FLIGHT_CH_READER_PASSWORD"],
        timeout_seconds=15,
    )
    if args.action == "load":
        admin = HttpConfig(
            args.port,
            "default",
            "flight_admin",
            os.environ["FLIGHT_CH_ADMIN_PASSWORD"],
            timeout_seconds=15,
        )
        load(admin, reader, rows)
    else:
        reconcile(reader, rows)
    report = summarize(rows)
    report["sql_typed_and_raw_rows_match"] = True
    with args.report.open("x", encoding="utf-8") as target:
        json.dump(report, target, sort_keys=True, indent=2, allow_nan=False)
        target.write("\n")
    print(
        json.dumps({"status": "verified", "rows": len(rows), "privacy": "restricted"})
    )


if __name__ == "__main__":
    main()
