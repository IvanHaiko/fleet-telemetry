"""File-boundary evidence: reconciliation, replay and failure before publication."""

import json
from collections.abc import Mapping
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from typing import cast

from ulog_binary import synthetic_log

FIXTURES = Path(__file__).parent / "fixtures"
DEFINITION = (
    "battery_status:uint64_t timestamp;float voltage_v;float current_a;"
    "float remaining;bool connected;uint8_t source;"
)
ULOG_AVAILABLE = find_spec("pyulog") is not None and find_spec("numpy") is not None


def obj(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def values(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def read_json(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_bytes())
    return obj(value)


def read_lines(path: Path) -> list[dict[str, object]]:
    return [obj(json.loads(line)) for line in path.read_bytes().splitlines()]


def write_job(
    directory: Path,
    *,
    mode: str = "synthetic",
    run_id: str = "run-001",
    payload: bytes | None = None,
) -> Path:
    data = (
        payload
        if payload is not None
        else (
            (FIXTURES / "synthetic-battery-v1.json").read_bytes()
            if mode == "synthetic"
            else synthetic_log()
        )
    )
    source = directory / ("input.json" if mode == "synthetic" else "input.ulg")
    source.write_bytes(data)
    receipt = "sha256:" + sha256(data).hexdigest()
    manifest: dict[str, object] = {
        "source_manifest_id": "authored-file-v1",
        "source_log_id": receipt,
        "vehicle_id": "demo-vehicle-001",
        "source_stream": "battery_status:0",
        "native_timestamp_min_us": 0,
        "native_timestamp_max_us": 2000000,
        "clock_anchor": {
            "native_anchor_us": 0,
            "utc_anchor": "2026-01-01T12:00:00.000000Z",
        },
        "retrieved_at": "2026-10-19T00:00:00.000000Z",
        "license_evidence": "Project-authored values and bytes.",
        "privacy_review": "Synthetic values without device identifiers or locations.",
        "parser_version": "literal-records-v1"
        if mode == "synthetic"
        else "pyulog-1.2.2",
        "source_type": "synthetic",
        "privacy_classification": "synthetic",
    }
    if mode == "synthetic":
        manifest["fixture_specification"] = "input.json"
    else:
        manifest.update(
            {
                "source_reference": "input.ulg",
                "vehicle_mapping_version": "authored-vehicles-v1",
                "producer_evidence": (
                    "Authored binary case; no real producer attribution."
                ),
                "field_definition_reference": "sha256:"
                + sha256(DEFINITION.encode()).hexdigest(),
            }
        )
    spec = {
        "job_version": "bounded-conversion-v1",
        "mode": mode,
        "input": {
            "path": source.name,
            "source_log_id": receipt,
            "size_bytes": len(data),
        },
        "manifest": manifest,
        "delivery": {
            "dataset_run_id": run_id,
            "ingest_timestamp": "2026-10-19T00:00:00.000000Z",
            "replay_mode": "synthetic",
        },
    }
    job = directory / f"{run_id}.job.json"
    job.write_text(json.dumps(spec), encoding="utf-8")
    return job


def rewrite_job(path: Path, spec: Mapping[str, object]) -> None:
    path.write_text(json.dumps(spec), encoding="utf-8")


def assert_no_output(root: Path, run_id: str = "run-001") -> None:
    assert not (root / run_id).exists()
    assert not list(root.glob(".telemetry-stage-*"))
