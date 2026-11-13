"""Small bounded JSONL measurements for the local M2 process protocol."""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping
from typing import cast

METRICS_VERSION = "m2-process-metrics-v1"
OPERATIONS = {
    "producer_initial",
    "producer_retry",
    "producer_unavailable",
    "producer_queue_pressure",
    "probe_producer",
    "consumer",
}
EVENTS = {
    "started",
    "callback",
    "completed",
    "failed",
    "commit_confirmed",
    "receipt_persisted",
}
COUNTS = {
    "attempted_records",
    "enqueued_records",
    "acknowledged_records",
    "callback_errors",
    "unqueued_records",
    "pending_records",
    "observed_records",
    "replayed_observations",
    "committed_next_offset",
    "captured_end_offset",
    "captured_lag_records",
}


class MetricsError(ValueError):
    """Invalid bounded metric shape; never includes supplied values."""


def metrics_record(
    operation: str, event: str, values: Mapping[str, object]
) -> dict[str, object]:
    """Validate fixed dimensions and finite nonnegative measurements, without IDs."""
    if operation not in OPERATIONS or event not in EVENTS or not values:
        raise MetricsError("invalid_metric_dimensions")
    for name, value in values.items():
        if name in COUNTS:
            if type(value) is not int or value < 0:
                raise MetricsError("invalid_metric_count")
        elif name == "duration_seconds":
            if (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or value < 0
            ):
                raise MetricsError("invalid_metric_duration")
            try:
                finite = math.isfinite(value)
            except OverflowError:
                raise MetricsError("invalid_metric_duration") from None
            if not finite:
                raise MetricsError("invalid_metric_duration")
        else:
            raise MetricsError("unknown_metric_name")
    return {
        "metrics_version": METRICS_VERSION,
        "operation": operation,
        "event": event,
        "values": dict(values),
    }


def emit_metrics(operation: str, event: str, **values: int | float) -> None:
    """Flush one structured stderr snapshot before any deliberate process exit."""
    record = metrics_record(operation, event, values)
    print(
        json.dumps(record, sort_keys=True, allow_nan=False), file=sys.stderr, flush=True
    )


def read_metrics(stderr: str) -> tuple[dict[str, object], ...]:
    """Extract validated snapshots while retaining other native stderr elsewhere."""
    records: list[dict[str, object]] = []
    for line in stderr.splitlines():
        try:
            decoded: object = json.loads(line)
        except (ValueError, RecursionError):
            if '"metrics_version"' in line:
                raise MetricsError("invalid_metric_json") from None
            continue
        if not isinstance(decoded, dict) or "metrics_version" not in decoded:
            continue
        record = cast(dict[str, object], decoded)
        if record.get("metrics_version") != METRICS_VERSION or set(record) != {
            "metrics_version",
            "operation",
            "event",
            "values",
        }:
            raise MetricsError("invalid_metric_shape")
        operation, event, values = (
            record["operation"],
            record["event"],
            record["values"],
        )
        if (
            not isinstance(operation, str)
            or not isinstance(event, str)
            or not isinstance(values, dict)
        ):
            raise MetricsError("invalid_metric_shape")
        if not all(isinstance(key, str) for key in values):
            raise MetricsError("invalid_metric_shape")
        records.append(
            metrics_record(operation, event, cast(dict[str, object], values))
        )
    return tuple(records)
