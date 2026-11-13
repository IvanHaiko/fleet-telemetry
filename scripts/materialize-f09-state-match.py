"""Associate exact F09 native state times with GPS in a fresh local SQL scope."""

import argparse
import hashlib
import json
import os
import runpy
from collections import Counter
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.flight_analytics.state import FIELDS, read_prepared
from runtime.flight_analytics.state_time import (
    VERSION,
    Gap,
    StatePoint,
    match_states,
    source_gaps,
)
from telemetry.conversion_contract import integer_value, json_object, string_value

DATABASE = "f09_state_association_v1"
TABLE = f"{DATABASE}.gps_state_match_v1"
BOUNDS = (
    " SETTINGS max_execution_time=10, max_threads=1, "
    "max_memory_usage=268435456, max_rows_to_read=100000, "
    "max_bytes_to_read=32000000, read_overflow_mode='throw'"
)


def build_rows(
    gps: list[dict[str, object]],
    states: list[dict[str, object]],
    gaps: list[Gap],
    max_age_us: int,
) -> list[dict[str, object]]:
    """Create one association per GPS ordinal and selected state stream."""
    times = [integer_value(row["native_timestamp_us"]) for row in gps]
    result = []
    for stream in FIELDS:
        points = [
            StatePoint(
                integer_value(row["source_ordinal"]),
                integer_value(row["native_timestamp_us"]),
                string_value(row["event_id"]),
            )
            for row in states
            if row["stream"] == stream
        ]
        matches = match_states(times, points, gaps, max_age_us)
        for ordinal, (row, match) in enumerate(zip(gps, matches, strict=True)):
            result.append(
                {
                    "association_version": VERSION,
                    "gps_ordinal": ordinal,
                    "gps_event_id": row["event_id"],
                    "state_stream": stream,
                    "status": match.status,
                    "state_event_id": match.event_id,
                    "age_us": match.age_us,
                    "max_age_us": max_age_us,
                }
            )
    return sorted(
        result,
        key=lambda r: (
            integer_value(r["gps_ordinal"]),
            string_value(r["state_stream"]),
        ),
    )


def reconcile(config: HttpConfig, rows: list[dict[str, object]]) -> None:
    """Compare every association field, including unknown NULLs and extra copies."""
    count = _request(
        config, f"SELECT count() FROM {TABLE}" + BOUNDS + " FORMAT TabSeparated", b""
    )
    if count.strip() != str(len(rows)).encode():
        raise ValueError("state_match_sql_count")
    for start in range(0, len(rows) // 2, 500):
        body = _request(
            config,
            f"SELECT * FROM {TABLE} "
            "WHERE gps_ordinal >= {lo:UInt32} AND gps_ordinal < {hi:UInt32} "
            "ORDER BY gps_ordinal, state_stream" + BOUNDS + " FORMAT JSONEachRow",
            b"",
            parameters={"param_lo": str(start), "param_hi": str(start + 500)},
        )
        actual = [json_object(line) for line in body.splitlines()]
        if actual != rows[2 * start : 2 * (start + 500)]:
            raise ValueError("state_match_sql_rows")


def load(admin: HttpConfig, reader: HttpConfig, rows: list[dict[str, object]]) -> None:
    """Write only a fresh fixed database; never retry ambiguous mutations."""
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
        f"CREATE TABLE {TABLE} (association_version String, "
        "gps_ordinal UInt32, gps_event_id String, state_stream String, "
        "status LowCardinality(String), state_event_id Nullable(String), "
        "age_us Nullable(UInt64), max_age_us UInt64) "
        "ENGINE = MergeTree ORDER BY (gps_ordinal, state_stream)",
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
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--gps", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--max-age-us", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=28132)
    args = parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise ValueError("output_unavailable")
    coverage = runpy.run_path(str(Path(__file__).with_name("report-f09-coverage.py")))
    coverage["gps_summary"](args.gps)
    manifest = json_object((args.gps / "manifest.json").read_bytes())
    gps_bytes = coverage["_checked_file"](
        args.gps / "gps.jsonl", "sha256:" + str(manifest["rows_sha256"]), 32_000_000
    )
    gps_rows = [json_object(line) for line in gps_bytes.splitlines()]
    states = read_prepared(args.state)
    gaps, evidence = source_gaps(args.source, gps_rows, states)
    rows = build_rows(gps_rows, states, gaps, args.max_age_us)
    reader = HttpConfig(
        args.port,
        "default",
        "flight_reader",
        os.environ["FLIGHT_CH_READER_PASSWORD"],
        timeout_seconds=15,
    )
    # Source tables must still agree with the retained inputs before any writes.
    coverage["reconcile_gps_rows"](reader, args.gps)
    state_sql = runpy.run_path(str(Path(__file__).with_name("f09-state-gold.py")))
    state_sql["reconcile"](reader, states)
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
    body = b"".join(
        (json.dumps(row, separators=(",", ":")) + "\n").encode() for row in rows
    )
    evidence.update(
        {
            "association_version": VERSION,
            "max_age_us": args.max_age_us,
            "gps_rows_sha256": hashlib.sha256(gps_bytes).hexdigest(),
            "state_rows_sha256": hashlib.sha256(
                (args.state / "state.jsonl").read_bytes()
            ).hexdigest(),
            "association_rows_sha256": hashlib.sha256(body).hexdigest(),
            "sql_all_fields_match": True,
            "privacy": "restricted",
            "gps_records": len(gps_rows),
            "association_rows": len(rows),
            "status_counts": {
                stream: dict(
                    sorted(
                        Counter(
                            string_value(r["status"])
                            for r in rows
                            if r["state_stream"] == stream
                        ).items()
                    )
                )
                for stream in FIELDS
            },
            "limitations": [
                "common boot clock assumed; no physical simultaneity or validated UTC",
                "dropout masks use file neighbors, not physical loss intervals",
                "exploratory age bound; no flight phases or source completeness",
                "SQL input and output reads have no sealed concurrent snapshot",
            ],
        }
    )
    args.output.mkdir()
    with (args.output / "associations.jsonl").open("xb") as target:
        target.write(body)
    with (args.output / "report.json").open("x", encoding="utf-8") as target:
        json.dump(evidence, target, sort_keys=True, indent=2, allow_nan=False)
        target.write("\n")
    print(
        json.dumps(
            {
                "status": "verified",
                "gps_records": len(gps_rows),
                "association_rows": len(rows),
                "status_counts": evidence["status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
