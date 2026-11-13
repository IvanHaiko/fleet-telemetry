"""Distinct ACK and verified-visibility denominators under a known clock."""

import json
from pathlib import Path

import pytest

from scripts.slice_measurement import SliceMeasurement


def test_finite_batch_timing_does_not_manufacture_streaming_samples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = iter((100.0, 102.0, 110.0, 112.0))
    monkeypatch.setattr(
        "scripts.slice_measurement.time.perf_counter", lambda: next(clock)
    )
    measurement = SliceMeasurement(tmp_path, 32)
    measurement.mark("producer_acked")
    measurement.mark("first_verified_sql_visibility")
    measurement.finish(3, 1024)
    result = json.loads((tmp_path / "measurement.json").read_text())
    assert result["acknowledged_per_second_to_last_ack"] == 16
    assert result["attempted_per_second_to_visibility"] == 3.2
    assert result["unique_visible_per_second"] == 0.3
    assert result["batch_visibility_seconds"] == 10
    assert result["stages_seconds_from_admission"]["retry_verification_complete"] == 12
    assert result["latency_sample_count"] == 1
    assert result["streaming_percentiles"] is None
