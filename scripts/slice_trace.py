"""Compare the bounded Flink trace with the independent M4 reference."""

from fractions import Fraction
from typing import cast

from scripts.slice_queries import Row, require
from scripts.slice_run import exact6
from telemetry.serving_projection import ServingScope
from telemetry_reference import ReferenceResult


def processing_rows(
    trace: list[Row], reference_result: ReferenceResult, scope: ServingScope, sha: str
) -> tuple[list[Row], list[Row]]:
    dispositions = [row for row in trace if row["kind"] == "disposition"]
    require(
        [
            (row["observation_index"], row["disposition"], row["event_id"])
            for row in dispositions
        ]
        == [
            (d.observation_index, d.kind, d.event_id)
            for d in reference_result.dispositions
        ],
        "flink_dispositions_mismatch",
    )
    raw_windows = [row for row in trace if row["kind"] == "window"]
    require(len(raw_windows) == len(reference_result.windows) == 1, "window_count")
    expected_window = reference_result.windows[0]
    actual_window = raw_windows[0]
    for field in (
        "dataset_run_id",
        "pipeline_version",
        "vehicle_id",
        "start_ms",
        "end_ms",
        "unique_events",
    ):
        require(
            actual_window[field] == getattr(expected_window, field),
            "window_mismatch",
        )
    windows: list[Row] = []
    for metric, summary in zip(
        ("voltage_v", "current_a", "remaining_fraction"),
        (
            expected_window.voltage,
            expected_window.current,
            expected_window.remaining,
        ),
        strict=True,
    ):
        measures = actual_window["measures"]
        require(isinstance(measures, dict), "object_required")
        measure = cast(list[object], cast(Row, measures)[metric])
        require(
            measure[0] == summary.count
            and Fraction(cast(str, measure[1])) == (summary.total or Fraction(0)),
            "window_sum_mismatch",
        )
        # The tiny fixture is exactly representable; refuse rounding elsewhere.
        total = Fraction(cast(str, measure[1]))
        value_sum = exact6(total)
        windows.append(
            {
                "dataset_run_id": scope.dataset_run_id,
                "pipeline_version": scope.pipeline_version,
                "vehicle_id": actual_window["vehicle_id"],
                "start_ms": actual_window["start_ms"],
                "end_ms": actual_window["end_ms"],
                "metric": metric,
                "unique_events": actual_window["unique_events"],
                "valid_count": measure[0],
                "value_sum": value_sum,
                "archive_descriptor_sha256": sha,
            }
        )
    facts = [
        {
            "dataset_run_id": scope.dataset_run_id,
            "pipeline_version": scope.pipeline_version,
            **{
                key: row[key]
                for key in (
                    "observation_index",
                    "event_id",
                    "disposition",
                    "reason",
                    "watermark_ms",
                )
            },
            "archive_descriptor_sha256": sha,
        }
        for row in dispositions
    ]
    return facts, windows
