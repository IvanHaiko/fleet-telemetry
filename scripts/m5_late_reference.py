"""Reconcile M5 idle/resume dispositions and windows before SQL publication."""

import json
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
from typing import cast

from m3_transport_types import Record

from scripts.slice_run import exact6
from telemetry.archive_documents import canonical
from telemetry.conversion_contract import SEMANTIC_FIELDS
from telemetry.serving_projection import metric_decimal, semantic_json
from telemetry_reference import (
    EndOfInput,
    Observation,
    ReferenceScope,
    TraceStep,
    Watermark,
    calculate_windows,
)

type Row = dict[str, object]
METRICS = ("voltage_v", "current_a", "remaining_fraction")


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def obj(value: object) -> Row:
    require(isinstance(value, dict), "expected_object")
    return cast(Row, value)


def save(folder: Path, name: str, value: object) -> None:
    with (folder / name).open("xb") as stream:
        stream.write(canonical(value))


def reconcile_trace(
    folder: Path,
    run_id: str,
    scope: ReferenceScope,
    anchor: int,
    canonical_events: list[Row],
    records: list[Record],
    trace: list[Row],
) -> tuple[list[Row], list[Row], Row]:
    dispositions = [row for row in trace if row["kind"] == "disposition"]
    require(
        [row["observation_index"] for row in dispositions] == list(range(51)),
        "trace_order",
    )
    reference_trace: list[TraceStep] = []
    watermark = -(2**63)
    for record, row in zip(records, dispositions, strict=True):
        current = cast(int, row["watermark_ms"])
        require(current >= watermark, "watermark_regression")
        if current > watermark:
            reference_trace.append(Watermark(current))
            watermark = current
        reference_trace.append(Observation(record.value))
    reference_trace.append(EndOfInput())
    reference = calculate_windows(scope, reference_trace)
    save(
        folder, "reference.json", json.loads(json.dumps(asdict(reference), default=str))
    )
    require(
        [(row["event_id"], row["disposition"], row["reason"]) for row in dispositions]
        == [(row.event_id, row.kind, row.reason) for row in reference.dispositions],
        "reference_dispositions",
    )
    require(
        Counter(row.kind for row in reference.dispositions)
        == {"eligible": 5, "duplicate": 43, "late": 3},
        "disposition_counts",
    )
    require(
        dispositions[43]["disposition"] == "late"
        and dispositions[43]["watermark_ms"] == anchor + 9999
        and dispositions[44]["disposition"] == "duplicate",
        "late_resume_boundary",
    )
    require(
        all(dispositions[i]["disposition"] == "late" for i in (49, 50)),
        "expired_duplicate_misclassified",
    )
    expired = {
        event_id
        for row in trace
        if row["kind"] == "expiry"
        for event_id in cast(list[str], row["event_ids"])
    }
    require(
        {event["event_id"] for event in canonical_events[:5]} <= expired,
        "active_identity_expiry_missing",
    )
    actual_windows = [row for row in trace if row["kind"] == "window"]
    require(len(actual_windows) == len(reference.windows) == 4, "window_count")
    windows: list[Row] = []
    for expected in reference.windows:
        actual = next(
            row for row in actual_windows if row["start_ms"] == expected.start_ms
        )
        require(
            all(
                actual[key] == getattr(expected, key)
                for key in (
                    "dataset_run_id",
                    "pipeline_version",
                    "vehicle_id",
                    "start_ms",
                    "end_ms",
                    "unique_events",
                )
            ),
            "window_identity",
        )
        for metric, summary in zip(
            METRICS,
            (expected.voltage, expected.current, expected.remaining),
            strict=True,
        ):
            measure = cast(list[object], obj(actual["measures"])[metric])
            require(
                measure[0] == summary.count
                and Fraction(cast(str, measure[1])) == (summary.total or Fraction(0)),
                "window_reference",
            )
            windows.append(
                {
                    "dataset_run_id": run_id,
                    "pipeline_version": "online-idle-v1",
                    "vehicle_id": expected.vehicle_id,
                    "metric_definition": metric,
                    "start_ms": expected.start_ms,
                    "end_ms": expected.end_ms,
                    "revision": 1,
                    "unique_events": expected.unique_events,
                    "valid_count": summary.count,
                    "value_sum": exact6(summary.total or Fraction(0)),
                }
            )
    require(
        [str(window.voltage.total) for window in reference.windows]
        == ["3", "3", "5", "6"],
        "late_inflated_window",
    )
    first = {
        cast(str, row["event_id"]): row["disposition"]
        for row in reversed(dispositions)
        if row["disposition"] != "duplicate"
    }
    events: list[Row] = []
    for event in canonical_events:
        payload = obj(event["payload"])
        semantic = {key: event[key] for key in SEMANTIC_FIELDS}
        semantic["quality_flags"] = sorted(cast(list[str], event["quality_flags"]))
        events.append(
            {
                "dataset_run_id": run_id,
                "pipeline_version": "online-idle-v1",
                "event_id": event["event_id"],
                "vehicle_id": event["vehicle_id"],
                "source_timestamp": event["source_timestamp"],
                **{name: metric_decimal(payload[name], name) for name in METRICS},
                "disposition": first[cast(str, event["event_id"])],
                "quality_flags": semantic["quality_flags"],
                "semantic_json": semantic_json(semantic),
            }
        )
    return (
        events,
        windows,
        {
            "dispositions": dict(Counter(row.kind for row in reference.dispositions)),
            "late_event_id": dispositions[43]["event_id"],
            "late_duplicate_disposition": dispositions[44]["disposition"],
        },
    )
