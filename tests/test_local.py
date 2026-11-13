"""The local demo must reconcile this run, preserve clocks and retain unknowns."""

import copy
from pathlib import Path

import pytest

from scripts.local import verify_projection
from telemetry.conversion_contract import json_object
from telemetry_convert import convert_job


@pytest.fixture
def projection(tmp_path: Path) -> tuple[list[bytes], list[dict[str, object]]]:
    result = convert_job(
        Path(__file__).parent / "fixtures/synthetic-conversion-job.json",
        tmp_path / "demo-synthetic-001",
    )
    inputs = (result.output_directory / "events.jsonl").read_bytes().splitlines()
    rows: list[dict[str, object]] = []
    for index, (raw, power) in enumerate(
        zip(inputs, (66.36, -20.0, None), strict=True)
    ):
        event = json_object(raw)
        payload = event["payload"]
        assert isinstance(payload, dict)
        rows.append(
            {
                "profile": "local-battery-projection-v1",
                "dataset_run_id": "demo-synthetic-001",
                "event_id": event["event_id"],
                "vehicle_id": event["vehicle_id"],
                "source_timestamp": event["source_timestamp"],
                "voltage_v": payload["voltage_v"],
                "current_a": payload["current_a"],
                "remaining_fraction": payload["remaining_fraction"],
                "power_w": power,
                "raw_event": raw.decode(),
                "source_partition": index,
                "source_offset": 0,
            }
        )
    return inputs, rows


def test_current_run_reconciliation_allows_repeats_but_not_old_results(
    projection: tuple[list[bytes], list[dict[str, object]]],
) -> None:
    inputs, rows = projection
    assert verify_projection(inputs, rows + rows, "demo-synthetic-001") == 3
    with pytest.raises(ValueError, match="received 0"):
        verify_projection(inputs, rows, "another-delivery")
    with pytest.raises(ValueError, match="received 2"):
        verify_projection(inputs, rows[:2], "demo-synthetic-001")


def test_changed_clock_power_unknown_and_transport_coordinates_refuse(
    projection: tuple[list[bytes], list[dict[str, object]]],
) -> None:
    inputs, rows = projection
    for index, field, value in (
        (0, "source_timestamp", "2026-11-11T00:00:00Z"),
        (0, "power_w", 0.0),
        (2, "power_w", 0.0),
        (2, "voltage_v", False),
        (0, "source_partition", 12),
    ):
        changed = copy.deepcopy(rows)
        changed[index][field] = value
        with pytest.raises(ValueError):
            verify_projection(inputs, changed, "demo-synthetic-001")
