"""Exercise a fresh local ClickHouse database; never start or stop services.

This is a finite compatibility probe, not an admitted production sink.
Credentials come from M4_SERVING_PASSWORD and stay outside the report.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import os
import re
import threading
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "runtime/clickhouse"
PIPELINE = "serving-spike-v1"
type Row = dict[str, object]
type Results = dict[str, list[Row]]


def object_row(value: object) -> Row:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("invalid_object")
    return cast(Row, value)


def number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("invalid_number")
    return float(value)


def text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid_text")
    return value


class Client:
    def __init__(self, port: int, database: str, user: str, password: str) -> None:
        self.port = port
        self.database = database
        self.auth = base64.b64encode(f"{user}:{password}".encode()).decode()

    def execute(self, sql: str, run: str = "main") -> bytes:
        params = urlencode(
            {
                "database": self.database,
                "param_run": run,
                "param_pipeline": PIPELINE,
                "wait_end_of_query": "1",
                "buffer_size": "1048576",
                "max_execution_time": "10",
                "max_memory_usage": "268435456",
                "max_threads": "1",
                "output_format_json_quote_64bit_integers": "0",
            }
        )
        request = Request(
            f"http://127.0.0.1:{self.port}/?{params}",
            data=sql.encode(),
            headers={"Authorization": f"Basic {self.auth}"},
        )
        with urlopen(request, timeout=15) as response:
            data = response.read(1_048_577)
            if not isinstance(data, bytes):
                raise ValueError("invalid_response_type")
            if len(data) > 1_048_576:
                raise ValueError("response_limit")
            return data

    def rows(self, sql: str, run: str = "main") -> list[Row]:
        return [
            object_row(json.loads(line)) for line in self.execute(sql, run).splitlines()
        ]

    def insert(self, table: str, rows: list[Row]) -> None:
        if table not in {"events", "windows"}:
            raise ValueError("unknown_table")
        self.execute(
            f"INSERT INTO {table} SETTINGS async_insert=0, insert_deduplicate=0 "
            "FORMAT JSONEachRow\n" + "\n".join(json.dumps(row) for row in rows)
        )

    def guard(self, run: str) -> None:
        """Run separately so empty result sets cannot bypass conflict evaluation."""
        self.execute(
            "SELECT throwIf(count() > 0, 'serving_identity_conflict') FROM conflicts "
            "WHERE dataset_run_id={run:String} AND pipeline_version={pipeline:String}",
            run,
        )


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def lost_ack(client: Client, table: str, rows: list[Row]) -> None:
    """Forward a real insert, consume upstream success, drop downstream response."""
    completed: list[bool] = []

    class DropResponse(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            try:
                self.rfile.read(int(self.headers["Content-Length"]))
                client.insert(table, rows)
                completed.append(True)
            finally:
                self.close_connection = True

        def log_message(self, format: str, *args: object) -> None:
            pass

    with HTTPServer(("127.0.0.1", 0), DropResponse) as server:
        server.timeout = 20
        worker = threading.Thread(target=server.handle_request, daemon=True)
        worker.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=20
        )
        try:
            connection.request("POST", "/", body=b"insert")
            try:
                connection.getresponse()
            except http.client.RemoteDisconnected:
                pass
            else:
                raise ValueError("ack_was_not_lost")
        finally:
            connection.close()
            worker.join(25)
        require(not worker.is_alive() and completed == [True], "upstream_insert_failed")


def fixture() -> tuple[list[Row], list[Row]]:
    """Use the existing golden identities/values, not a second source generator."""
    golden = object_row(
        json.loads((ROOT / "tests/fixtures/expected-battery-v1.json").read_bytes())
    )
    accepted = golden["accepted"]
    if not isinstance(accepted, list):
        raise ValueError("invalid_golden")
    events: list[Row] = []
    for value in accepted:
        event = object_row(value)
        events.append(
            {
                "dataset_run_id": "main",
                "pipeline_version": PIPELINE,
                "event_id": event["event_id"],
                "vehicle_id": "demo-vehicle-001",
                "source_timestamp": text(event["source_timestamp"]).replace("T", " ")[
                    :-1
                ],
                **object_row(event["payload"]),
                "disposition": "eligible",
                "quality_flags": event["quality_flags"],
                "semantic_json": json.dumps(
                    event, sort_keys=True, separators=(",", ":")
                ),
            }
        )
    # Exact independent golden reference, not an aggregate of query results.
    windows: list[Row] = [
        {
            "dataset_run_id": "main",
            "pipeline_version": PIPELINE,
            "vehicle_id": "demo-vehicle-001",
            "metric_definition": metric,
            "start_ms": 1767268800000,
            "end_ms": 1767268810000,
            "revision": 1,
            "unique_events": 3,
            "valid_count": count,
            "value_sum": value,
        }
        for metric, count, value in (
            ("voltage_v", 3, "31.8"),
            ("current_a", 2, "2.95"),
            ("remaining_fraction", 1, "0.72"),
        )
    ]
    return events, windows


def results(client: Client, run: str = "main") -> Results:
    client.guard(run)
    return {
        name: client.rows((SQL / f"{name}.sql").read_text(), run)
        for name in ("trends", "coverage", "quality")
    }


def refused(client: Client, sql: str, marker: bytes, run: str = "main") -> None:
    try:
        client.guard(run)
        client.execute(sql, run)
    except HTTPError as error:
        require(marker in error.read(65536), "wrong_refusal")
    else:
        raise ValueError("expected_refusal")


def verify(client: Client, events: list[Row]) -> Results:
    observed = results(client)
    coverage = observed["coverage"]
    require(
        coverage
        == [
            {
                "vehicle_id": "demo-vehicle-001",
                "measurements": 3,
                "voltage_valid": 3,
                "voltage_missing": 0,
                "current_valid": 2,
                "current_missing": 1,
                "remaining_valid": 1,
                "remaining_missing": 2,
            }
        ],
        "coverage_mismatch",
    )
    expected = {
        "voltage_v": (3, "31.8", 10.6),
        "current_a": (2, "2.95", 1.475),
        "remaining_fraction": (1, "0.72", 0.72),
    }
    require(len(observed["trends"]) == 3, "window_set_mismatch")
    for row in observed["trends"]:
        count, total, mean = expected[text(row["metric_definition"])]
        require(
            row["unique_events"] == 3
            and row["valid_count"] == count
            and Decimal(str(row["value_sum"])) == Decimal(total)
            and abs(number(row["mean"]) - mean) < 1e-12
            and row["start_ms"] == 1767268800000
            and row["end_ms"] == 1767268810000,
            "trend_mismatch",
        )
    require(
        observed["quality"]
        == [
            {
                "disposition": "eligible",
                "quality_flag": "source_value_missing",
                "measurements": 2,
            },
            {
                "disposition": "eligible",
                "quality_flag": "synthetic_time_anchor",
                "measurements": 3,
            },
        ],
        "quality_mismatch",
    )
    rows = client.rows(
        "SELECT event_id, semantic_json FROM unique_events "
        "WHERE dataset_run_id='main' AND pipeline_version='serving-spike-v1' "
        "ORDER BY event_id FORMAT JSONEachRow"
    )
    require(
        rows
        == sorted(
            [
                {"event_id": row["event_id"], "semantic_json": row["semantic_json"]}
                for row in events
            ],
            key=lambda row: text(row["event_id"]),
        ),
        "identity_or_content_mismatch",
    )
    return observed


def run_probe(client: Client, report: Row) -> None:
    events, windows = fixture()
    # Server-side merges are explicitly stopped and physical copies are inspected.
    for table in ("events", "windows"):
        client.execute(f"SYSTEM STOP MERGES {table}")
    lost_ack(client, "events", events)
    lost_ack(client, "windows", windows)
    for row in reversed(events):
        client.insert("events", [row])
    client.insert("windows", windows[:1])
    client.insert("windows", windows[1:])
    report["before_merge"] = verify(client, events)
    physical_rows = client.rows(
        "SELECT 'events' AS table_name, count() AS rows FROM events UNION ALL "
        "SELECT 'windows', count() FROM windows FORMAT JSONEachRow"
    )
    report["physical_rows"] = physical_rows
    require(
        len(physical_rows) == 2 and all(row["rows"] == 6 for row in physical_rows),
        "copies_not_present",
    )
    # Older revision arrives last; it must never win by physical arrival order.
    client.insert("windows", [{**windows[0], "revision": 0, "value_sum": "999"}])
    require(verify(client, events) == report["before_merge"], "revision_order_mismatch")
    for table in ("events", "windows"):
        client.execute(f"SYSTEM START MERGES {table}")
        client.execute(f"OPTIMIZE TABLE {table} FINAL")
    report["after_merge"] = verify(client, events)
    # Separate namespaces exercise late facts and isolation without changing main.
    client.insert(
        "events", [{**events[0], "dataset_run_id": "late", "disposition": "late"}]
    )
    require(
        results(client, "late")["quality"]
        == [
            {
                "disposition": "late",
                "quality_flag": "synthetic_time_anchor",
                "measurements": 1,
            }
        ],
        "late_mismatch",
    )
    client.insert("events", [{**events[0], "pipeline_version": "another-pipeline"}])
    require(verify(client, events) == report["before_merge"], "namespace_mixed")
    # Equal identity with changed payload, and equal revision with changed aggregate.
    for run, table, original, change in (
        ("event-conflict", "events", events[0], {"voltage_v": 99}),
        ("window-conflict", "windows", windows[0], {"value_sum": "999"}),
    ):
        client.insert(
            table,
            [
                {**original, "dataset_run_id": run},
                {**original, "dataset_run_id": run, **change},
            ],
        )
        for phase in ("before", "after"):
            for name in ("trends", "coverage", "quality"):
                refused(
                    client,
                    (SQL / f"{name}.sql").read_text(),
                    b"serving_identity_conflict",
                    run,
                )
            if phase == "before":
                client.execute(f"OPTIMIZE TABLE {table} FINAL")
    report["checks"] = [
        "lost_event_ack",
        "lost_window_ack",
        "changed_batch_retry",
        "physical_duplicates_before_merge",
        "exact_identity_and_content",
        "three_queries",
        "older_revision_arrives_last",
        "post_merge",
        "late_fact",
        "run_and_pipeline_isolation",
        "conflicts_before_after_merge",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, default=18123)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--readback", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"m4_serving_[a-z0-9_]{1,48}", args.database):
        parser.error("Use a fresh bounded m4_serving_ experiment identifier.")
    if args.report.exists():
        parser.error("Report must be fresh.")
    client = Client(
        args.port, "default", "bootstrap", os.environ["M4_SERVING_PASSWORD"]
    )
    report: Row = {"complete": False, "database": args.database}
    try:
        report["version"] = client.execute("SELECT version()").decode().strip()
        require(report["version"] == "26.8.34.13", "version_mismatch")
        if not args.readback:
            client.execute(f"CREATE DATABASE {args.database}")
        client.database = args.database
        if args.readback:
            report["readback"] = verify(client, fixture()[0])
        else:
            for statement in (SQL / "schema.sql").read_text().split(";"):
                if statement.strip():
                    client.execute(statement)
            run_probe(client, report)
        report["sha256"] = {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in [Path(__file__), *sorted(SQL.glob("*.sql")), SQL / "limits.xml"]
        }
        report["complete"] = True
    except Exception as error:
        report["failure_type"] = type(error).__name__
        # Do not serialize request headers, credentials or arbitrary server payloads.
        if isinstance(error, ValueError):
            report["reason"] = str(error)
        raise
    finally:
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
