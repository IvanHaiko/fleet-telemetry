"""Finite synthetic position-file adapter and experimental v1 reader."""

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import cast

from telemetry.conversion_contract import json_object
from telemetry.position_live import PositionView

MAX_SOURCE_BYTES = 1_048_576
MAX_RECORDS = 1000
HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
TIME = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z\Z")


def _timestamp(anchor: str, boot_ms: int) -> str:
    if not isinstance(anchor, str) or TIME.fullmatch(anchor) is None:
        raise ValueError("position_anchor")
    try:
        value = datetime.fromisoformat(anchor.replace("Z", "+00:00")) + timedelta(
            milliseconds=boot_ms
        )
    except (ValueError, OverflowError):
        raise ValueError("position_anchor") from None
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _version(anchor: str) -> str:
    return "sim-position-file-v1-" + hashlib.sha256(anchor.encode()).hexdigest()


def _identity(
    source_id: str, vehicle: str, stream: str, index: int, version: str
) -> str:
    parts = [
        "event-id-v1",
        "synthetic",
        source_id,
        vehicle,
        stream,
        index,
        "telemetry.position",
        version,
    ]
    return (
        "sha256:"
        + hashlib.sha256(json.dumps(parts, separators=(",", ":")).encode()).hexdigest()
    )


def adapt(
    source: bytes, *, run_id: str, anchor: str, vehicles: dict[int, str]
) -> list[dict[str, object]]:
    """Adapt a bounded JSONL source; the whole batch is rejected on any error."""
    if type(source) is not bytes or not 0 < len(source) <= MAX_SOURCE_BYTES:
        raise ValueError("position_source_size")
    if not isinstance(run_id, str) or NAME.fullmatch(run_id) is None:
        raise ValueError("position_run")
    if (
        not vehicles
        or len(vehicles) > 10
        or any(
            type(k) is not int
            or not 1 <= k <= 255
            or not isinstance(v, str)
            or NAME.fullmatch(v) is None
            for k, v in vehicles.items()
        )
        or len(set(vehicles.values())) != len(vehicles)
    ):
        raise ValueError("position_vehicles")
    lines = source.splitlines()
    if not lines or len(lines) > MAX_RECORDS:
        raise ValueError("position_record_limit")
    _timestamp(anchor, 0)
    version = _version(anchor)
    source_id = "sha256:" + hashlib.sha256(source).hexdigest()
    indices: dict[int, int] = {}
    events = []
    for line in lines:
        row = json_object(line)
        system = row.get("system_id")
        if type(system) is not int or system not in vehicles:
            raise ValueError("position_vehicle")
        # Validate one measurement without the latest-view ordering policy.
        view = PositionView({system})
        view.accept(row, None)
        position = view.positions[system]
        stream = f"simulated-position:{system}"
        index = indices.get(system, 0)
        indices[system] = index + 1
        event: dict[str, object] = {
            "event_id": _identity(source_id, vehicles[system], stream, index, version),
            "vehicle_id": vehicles[system],
            "event_type": "telemetry.position",
            "schema_version": "1.0.0",
            "source_timestamp": _timestamp(anchor, position.boot_ms),
            "source_log_id": source_id,
            "source_type": "synthetic",
            "source_stream": stream,
            "source_record_index": index,
            "normalization_version": version,
            "source_time": {
                "clock_basis": "boot_relative",
                "native_timestamp_ms": position.boot_ms,
                "timestamp_kind": "publication",
                "anchor_kind": "synthetic_fixed",
                "utc_anchor": anchor,
            },
            "quality_flags": ["synthetic_time_anchor"],
            "payload": {
                "latitude_deg": position.latitude_deg,
                "longitude_deg": position.longitude_deg,
                "altitude_msl_m": position.altitude_msl_m,
                "relative_altitude_m": position.relative_altitude_m,
                "fix_type": row["fix_type"],
            },
            "delivery": {"dataset_run_id": run_id, "replay_mode": "synthetic"},
        }
        events.append(read_position(event))
    return events


def read_position(event: dict[str, object]) -> dict[str, object]:
    """Validate the exact first synthetic position contract and deterministic ID."""
    fields = {
        "event_id",
        "vehicle_id",
        "event_type",
        "schema_version",
        "source_timestamp",
        "source_log_id",
        "source_type",
        "source_stream",
        "source_record_index",
        "normalization_version",
        "source_time",
        "quality_flags",
        "payload",
        "delivery",
    }
    if (
        set(event) != fields
        or event["event_type"] != "telemetry.position"
        or event["schema_version"] != "1.0.0"
        or event["source_type"] != "synthetic"
    ):
        raise ValueError("position_contract")
    vehicle, source_id, stream, index = (
        event[k]
        for k in ("vehicle_id", "source_log_id", "source_stream", "source_record_index")
    )
    if (
        not isinstance(vehicle, str)
        or NAME.fullmatch(vehicle) is None
        or not isinstance(source_id, str)
        or HASH.fullmatch(source_id) is None
        or not isinstance(stream, str)
        or re.fullmatch(
            r"simulated-position:(?:[1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])",
            stream,
        )
        is None
        or type(index) is not int
        or index < 0
    ):
        raise ValueError("position_identity")
    source_time = event["source_time"]
    if (
        not isinstance(source_time, dict)
        or set(source_time)
        != {
            "clock_basis",
            "native_timestamp_ms",
            "timestamp_kind",
            "anchor_kind",
            "utc_anchor",
        }
        or source_time["clock_basis"] != "boot_relative"
        or source_time["timestamp_kind"] != "publication"
        or source_time["anchor_kind"] != "synthetic_fixed"
        or type(source_time["native_timestamp_ms"]) is not int
        or not 0 <= source_time["native_timestamp_ms"] <= 0xFFFFFFFF
        or not isinstance(source_time["utc_anchor"], str)
        or event["source_timestamp"]
        != _timestamp(source_time["utc_anchor"], source_time["native_timestamp_ms"])
    ):
        raise ValueError("position_time")
    version = _version(source_time["utc_anchor"])
    if event["normalization_version"] != version or event["event_id"] != _identity(
        source_id, vehicle, stream, index, version
    ):
        raise ValueError("position_identity")
    payload = event["payload"]
    if not isinstance(payload, dict) or set(payload) != {
        "latitude_deg",
        "longitude_deg",
        "altitude_msl_m",
        "relative_altitude_m",
        "fix_type",
    }:
        raise ValueError("position_payload")
    # Reuse the simulator boundary's integer/range/fix validation without rounding.
    row: dict[str, object] = {
        "format_version": "simulated-position-v1",
        "source": "px4-sitl",
        "system_id": int(stream.split(":")[1]),
        "boot_ms": source_time["native_timestamp_ms"],
        "fix_type": payload["fix_type"],
    }
    for src, dst, scale in (
        ("latitude_deg", "latitude_e7", 10_000_000),
        ("longitude_deg", "longitude_e7", 10_000_000),
        ("altitude_msl_m", "altitude_msl_mm", 1000),
        ("relative_altitude_m", "relative_altitude_mm", 1000),
    ):
        value = payload[src]
        if type(value) not in (float, int):
            raise ValueError("position_payload")
        scaled = float(cast(float, value)) * scale
        if (
            not (-2147483648 <= scaled <= 2147483647)
            or abs(scaled - round(scaled)) > 1e-6
        ):
            raise ValueError("position_payload")
        row[dst] = round(scaled)
    PositionView({cast(int, row["system_id"])}).accept(row, None)
    delivery = event["delivery"]
    if (
        not isinstance(delivery, dict)
        or set(delivery) != {"dataset_run_id", "replay_mode"}
        or not isinstance(delivery["dataset_run_id"], str)
        or NAME.fullmatch(delivery["dataset_run_id"]) is None
        or delivery["replay_mode"] != "synthetic"
        or event["quality_flags"] != ["synthetic_time_anchor"]
    ):
        raise ValueError("position_delivery")
    return event
