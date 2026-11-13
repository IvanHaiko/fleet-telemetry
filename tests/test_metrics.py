"""Observable metric population, cardinality and finite-value boundaries."""

import json

import pytest

from telemetry_metrics import MetricsError, emit_metrics, metrics_record, read_metrics


def test_stderr_snapshots_roundtrip_without_polluting_result_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_metrics(
        "producer_retry",
        "completed",
        attempted_records=3,
        acknowledged_records=3,
        pending_records=0,
        duration_seconds=0.5,
    )
    output = capsys.readouterr()
    assert output.out == ""
    records = read_metrics("native diagnostic\n" + output.err)
    assert len(records) == 1
    assert records[0]["values"] == {
        "attempted_records": 3,
        "acknowledged_records": 3,
        "pending_records": 0,
        "duration_seconds": 0.5,
    }
    assert set(records[0]) == {"metrics_version", "operation", "event", "values"}


@pytest.mark.parametrize(
    "values",
    [
        {"event_id": "sensitive"},
        {"attempted_records": True},
        {"pending_records": -1},
        {"duration_seconds": float("nan")},
        {"duration_seconds": float("inf")},
        {"duration_seconds": 10**400},
    ],
)
def test_ids_and_invalid_units_cannot_be_emitted(values: dict[str, object]) -> None:
    with pytest.raises(MetricsError) as caught:
        metrics_record("consumer", "completed", values)
    assert "sensitive" not in str(caught.value)


def test_unknown_metric_versions_and_shape_are_visible_failures() -> None:
    record = metrics_record(
        "consumer", "commit_confirmed", {"committed_next_offset": 3}
    )
    record["metrics_version"] = "future"
    with pytest.raises(MetricsError, match="invalid_metric_shape"):
        read_metrics(json.dumps(record))
    with pytest.raises(MetricsError, match="invalid_metric_json"):
        read_metrics('{"metrics_version":')
    with pytest.raises(MetricsError, match="invalid_metric_dimensions"):
        metrics_record("vehicle-001", "completed", {"observed_records": 1})
