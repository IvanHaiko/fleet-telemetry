"""SQL readback for the single M5 online idle/resume scenario."""

from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from scripts.slice_queries import require, rows
from telemetry.archive_documents import canonical

ROOT = Path(__file__).resolve().parents[1]
METRICS = ("voltage_v", "current_a", "remaining_fraction")
type Row = dict[str, object]


def sql(config: HttpConfig, statement: str, run: str, body: bytes = b"") -> list[Row]:
    wire = _request(
        config,
        statement,
        body,
        write=statement.startswith("INSERT"),
        parameters={
            "database": config.database,
            "param_run": run,
            "param_pipeline": "online-idle-v1",
        },
    )
    return rows(wire)


def insert(
    config: HttpConfig, table: str, run: str, rows: list[Row], size: int
) -> None:
    require(table in {"events", "windows"}, "invalid_table")
    for start in range(0, len(rows), size):
        sql(
            config,
            f"INSERT INTO {table} SETTINGS async_insert=0, "
            "insert_deduplicate=0, date_time_input_format='best_effort' "
            "FORMAT JSONEachRow",
            run,
            b"".join(canonical(row) for row in rows[start : start + size]),
        )


def reports(reader: HttpConfig, run: str, events: list[Row], windows: list[Row]) -> Row:
    where = " WHERE dataset_run_id={run:String} AND pipeline_version={pipeline:String}"
    # A separate guard is required even if the requested result is empty.
    sql(
        reader,
        "SELECT throwIf(count()>0,'serving_identity_conflict') FROM conflicts"
        + where
        + " FORMAT JSONEachRow",
        run,
    )
    for table, expected_rows in (("events", events), ("windows", windows)):
        expressions = [
            f"toDecimalString({key},6) AS {key}"
            if key in (*METRICS, "value_sum")
            else "formatDateTime(source_timestamp,'%Y-%m-%dT%H:%i:%S.%fZ','UTC') "
            "AS source_timestamp"
            if key == "source_timestamp"
            else key
            for key in expected_rows[0]
        ]
        stored_rows = sql(
            reader,
            f"SELECT DISTINCT {','.join(expressions)} FROM {table}"
            + where
            + " LIMIT 65 FORMAT JSONEachRow",
            run,
        )
        require(
            sorted(map(canonical, stored_rows))
            == sorted(map(canonical, expected_rows)),
            "full_fact_mismatch",
        )
    result = {
        name: sql(
            reader, (ROOT / "runtime/clickhouse" / (name + ".sql")).read_text(), run
        )
        for name in ("trends", "coverage", "quality")
    }
    trends = result["trends"]
    require(len(trends) == len(windows) == 12, "trend_count")
    for actual in trends:
        expected = next(
            row
            for row in windows
            if all(
                row[key] == actual[key]
                for key in ("vehicle_id", "metric_definition", "start_ms", "end_ms")
            )
        )
        require(
            actual["unique_events"] == expected["unique_events"]
            and actual["valid_count"] == expected["valid_count"]
            and Fraction(str(actual["value_sum"]))
            == Fraction(cast(str, expected["value_sum"])),
            "trend_values",
        )
        count = cast(int, expected["valid_count"])
        require(
            actual["mean"] is None
            if count == 0
            else Fraction(str(actual["mean"]))
            == Fraction(cast(str, expected["value_sum"])) / count,
            "trend_mean",
        )
    require(
        result["coverage"]
        == [
            {
                "vehicle_id": "demo-vehicle-001",
                "measurements": 6,
                "voltage_valid": 6,
                "voltage_missing": 0,
                "current_valid": 3,
                "current_missing": 3,
                "remaining_valid": 2,
                "remaining_missing": 4,
            }
        ],
        "coverage_values",
    )
    expected_quality = Counter(
        (row["disposition"], flag)
        for row in events
        for flag in cast(list[str], row["quality_flags"])
    )
    require(
        result["quality"]
        == [
            {"disposition": kind, "quality_flag": flag, "measurements": count}
            for (kind, flag), count in sorted(expected_quality.items())
        ],
        "quality_values",
    )
    return cast(Row, result)
