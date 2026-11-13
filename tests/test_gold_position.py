"""Synthetic position adapter and Gold behavior."""

import copy
import hashlib
import json
from typing import cast

import pytest

from runtime.continuous.gold import overview
from telemetry.conversion_contract import SEMANTIC_FIELDS
from telemetry.position_file import adapt, read_position
from telemetry.serving_projection import _semantic_json


def source() -> bytes:
    row = {
        "format_version": "simulated-position-v1",
        "source": "px4-sitl",
        "system_id": 1,
        "boot_ms": 1200,
        "latitude_e7": 523000000,
        "longitude_e7": 134000000,
        "altitude_msl_mm": 74000,
        "relative_altitude_mm": 5000,
        "fix_type": 3,
    }
    return (json.dumps(row) + "\n").encode()


def fact(event: dict[str, object], offset: int = 0) -> dict[str, object]:
    semantic = {field: event[field] for field in SEMANTIC_FIELDS}
    encoded = _semantic_json(semantic)
    packet = {
        "format_version": "continuous-processing-v1",
        "run_id": "test-run",
        "kind": "event",
        "event": event,
        "disposition": "eligible",
        "semantic_json": encoded,
        "semantic_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
    }
    return {
        "output_partition": 0,
        "output_offset": offset,
        "kind": "event",
        "fact_json": json.dumps(packet),
    }


def test_file_identity_time_units_and_gold_replay() -> None:
    data = source()
    event = adapt(
        data,
        run_id="test-run",
        anchor="2026-01-01T00:00:00.000000Z",
        vehicles={1: "vehicle-1"},
    )[0]
    assert event["source_log_id"] == "sha256:" + hashlib.sha256(data).hexdigest()
    assert event["source_timestamp"] == "2026-01-01T00:00:01.200000Z"
    assert event["payload"] == {
        "latitude_deg": 52.3,
        "longitude_deg": 13.4,
        "altitude_msl_m": 74.0,
        "relative_altitude_m": 5.0,
        "fix_type": 3,
    }
    replay = adapt(
        data,
        run_id="replay",
        anchor="2026-01-01T00:00:00.000000Z",
        vehicles={1: "vehicle-1"},
    )[0]
    assert event["event_id"] == replay["event_id"]
    shifted = adapt(
        data,
        run_id="test-run",
        anchor="2026-01-02T00:00:00.000000Z",
        vehicles={1: "vehicle-1"},
    )[0]
    assert event["event_id"] != shifted["event_id"]
    report = overview("test-run", [fact(event), fact(event), fact(event, 1)])
    assert report["unique_measurements"] == 1
    group = cast(list[dict[str, object]], report["groups"])[0]
    assert (
        group["event_type"] == "telemetry.position"
        and group["timestamp_kind"] == "publication"
    )


def test_invalid_position_time_identity_and_conflicting_measurement_refuse() -> None:
    event = adapt(
        source(),
        run_id="test-run",
        anchor="2026-01-01T00:00:00.000000Z",
        vehicles={1: "vehicle-1"},
    )[0]
    for field, value in (
        ("event_id", "sha256:" + "0" * 64),
        ("source_timestamp", "2026-01-01T00:00:00.000000Z"),
    ):
        invalid = copy.deepcopy(event)
        invalid[field] = value
        with pytest.raises(ValueError):
            read_position(invalid)
    changed = copy.deepcopy(event)
    cast(dict[str, object], changed["payload"])["latitude_deg"] = 52.4
    with pytest.raises(ValueError, match="gold_identity_conflict"):
        overview("test-run", [fact(event), fact(changed, 1)])
    invalid_row = json.loads(source())
    invalid_row["fix_type"] = 1
    with pytest.raises(ValueError):
        adapt(
            json.dumps(invalid_row).encode(),
            run_id="test-run",
            anchor="2026-01-01T00:00:00.000000Z",
            vehicles={1: "vehicle-1"},
        )
