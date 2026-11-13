"""Exact processing-fact readback and three bounded SQL reports for the slice."""

from collections import Counter
from fractions import Fraction
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.archive_documents import canonical
from telemetry.serving_projection import ServingScope

type Row = dict[str, object]


def require(condition: object, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def rows(body: bytes) -> list[Row]:
    import json

    return [cast(Row, json.loads(line)) for line in body.splitlines()]


def insert(config: HttpConfig, table: str, values: list[Row], size: int) -> None:
    require(table in {"slice_dispositions_v1", "slice_windows_v1"}, "table_scope")
    for start in range(0, len(values), size):
        _request(
            config,
            f"INSERT INTO {config.database}.{table} "
            "SETTINGS async_insert=0, insert_deduplicate=0 FORMAT JSONEachRow",
            b"".join(canonical(row) for row in values[start : start + size]),
            write=True,
        )


def query(config: HttpConfig, sql: str, scope: ServingScope) -> list[Row]:
    return rows(
        _request(
            config,
            sql + " SETTINGS max_execution_time=10, "
            "max_threads=1, max_memory_usage=268435456, "
            "max_rows_to_read=4096, read_overflow_mode='throw' "
            "FORMAT JSONEachRow",
            b"",
            parameters={
                "param_run": scope.dataset_run_id,
                "param_pipeline": scope.pipeline_version,
            },
        )
    )


def reconcile(
    config: HttpConfig, scope: ServingScope, dispositions: list[Row], windows: list[Row]
) -> dict[str, object]:
    """Compare full facts before issuing queries; refuse conflicts or omissions."""
    where = " WHERE dataset_run_id={run:String} AND pipeline_version={pipeline:String}"
    for table, expected in (
        ("slice_dispositions_v1", dispositions),
        ("slice_windows_v1", windows),
    ):
        columns = list(expected[0])
        select = [
            f"toDecimalString({c},6) AS {c}" if c == "value_sum" else c for c in columns
        ]
        actual = query(
            config,
            f"SELECT DISTINCT {','.join(select)} "
            f"FROM {config.database}.{table}" + where + " LIMIT 65",
            scope,
        )
        require(
            sorted(map(canonical, actual)) == sorted(map(canonical, expected)),
            "processing_fact_reconciliation_failed",
        )
    # DISTINCT removes only complete identical rows; the exact comparison above
    # has already refused competing content at any expected logical key.
    unique = f"(SELECT DISTINCT * FROM {config.database}.slice_windows_v1{where})"
    trends = query(
        config,
        "SELECT vehicle_id,start_ms,end_ms,metric,valid_count,"
        "toDecimalString(w.value_sum,6) AS value_sum,"
        "toString(w.value_sum / nullIf(valid_count,0)) AS mean "
        f"FROM {unique} AS w ORDER BY vehicle_id,start_ms,metric",
        scope,
    )
    coverage = query(
        config,
        "SELECT vehicle_id,metric,sum(valid_count) AS valid,"
        "sum(unique_events-valid_count) AS missing "
        f"FROM {unique} GROUP BY vehicle_id,metric ORDER BY vehicle_id,metric",
        scope,
    )
    quality = query(
        config,
        "SELECT disposition,count() AS observations FROM "
        f"(SELECT DISTINCT * FROM {config.database}.slice_dispositions_v1"
        + where
        + ") GROUP BY disposition ORDER BY disposition",
        scope,
    )
    flags = query(
        config,
        "SELECT flag,count() AS measurements FROM "
        f"(SELECT DISTINCT * FROM {config.database}.serving_events_v1"
        + where
        + ") ARRAY JOIN quality_flags AS flag GROUP BY flag ORDER BY flag",
        scope,
    )
    expected_quality = dict(Counter(str(row["disposition"]) for row in dispositions))
    keys = ("vehicle_id", "start_ms", "end_ms", "metric")
    require(
        len(trends) == len(windows)
        and {tuple(row[key] for key in keys) for row in trends}
        == {tuple(row[key] for key in keys) for row in windows},
        "trend_query_mismatch",
    )
    for trend_row in trends:
        expected_trend = next(
            w
            for w in windows
            if all(
                w[key] == trend_row[key]
                for key in ("vehicle_id", "start_ms", "end_ms", "metric")
            )
        )
        require(
            trend_row["valid_count"] == expected_trend["valid_count"]
            and trend_row["value_sum"] == expected_trend["value_sum"],
            "trend_query_mismatch",
        )
        count = cast(int, expected_trend["valid_count"])
        require(
            (trend_row["mean"] is None and count == 0)
            or (
                count > 0
                and Fraction(cast(str, trend_row["mean"]))
                == Fraction(cast(str, expected_trend["value_sum"])) / count
            ),
            "trend_mean_mismatch",
        )
    require(
        {str(row["disposition"]): row["observations"] for row in quality}
        == expected_quality,
        "quality_query_mismatch",
    )
    require(
        len(coverage) == len({(w["vehicle_id"], w["metric"]) for w in windows})
        and {(row["vehicle_id"], row["metric"]) for row in coverage}
        == {(w["vehicle_id"], w["metric"]) for w in windows},
        "coverage_query_mismatch",
    )
    for row in coverage:
        selected = [
            w
            for w in windows
            if w["vehicle_id"] == row["vehicle_id"] and w["metric"] == row["metric"]
        ]
        require(
            row["valid"] == sum(cast(int, w["valid_count"]) for w in selected)
            and row["missing"]
            == sum(
                cast(int, w["unique_events"]) - cast(int, w["valid_count"])
                for w in selected
            ),
            "coverage_query_mismatch",
        )
    return {
        "trends": trends,
        "coverage": coverage,
        "quality": {
            "dispositions": quality,
            "flags": flags,
            "late_observations": expected_quality.get("late", 0),
        },
    }
