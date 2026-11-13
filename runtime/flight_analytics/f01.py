"""Exact-file F01 state research adapter, including empty GPS/missing battery."""

import contextlib
import hashlib
import io
import re
import struct
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from pyulog import ULog  # type: ignore[import-untyped]

from runtime.flight_analytics.state import DEFINITIONS, FIELDS, project
from runtime.flight_analytics.state_time import StatePoint, match_states
from telemetry.conversion_contract import integer_value, json_line, string_value
from telemetry.local_io import destination, read_bounded
from ulog_integrity import F01_SOURCE_ID, ULogExpectation, inspect_ulog

PROFILE = "f01-recording-inspection-v1"
STATE_PROFILE = "f01-state-research-v1"
SOURCE_BYTES = 1_594_052
FIRMWARE = "d6f12ad1c4f70ad3230afd7d86e971421e02fef4"
COUNTS = {"vehicle_land_detected": 41, "vehicle_status": 77}
VEHICLE = "f01-research-recording"


def project_state(
    stream: str, ordinal: int, native: dict[str, int]
) -> dict[str, object]:
    """Reuse reviewed field validation with a separate exact-source identity."""
    row = project(stream, ordinal, native)
    row["event_id"] = hashlib.sha256(
        f"{STATE_PROFILE}:{F01_SOURCE_ID}:{stream}:0:{ordinal}".encode()
    ).hexdigest()
    return row


def _original_values(definition: str, data: bytes, offset: int) -> dict[str, int]:
    """Decode scalar state fields independently of the upstream value parser."""
    formats = {
        "uint64_t": "Q",
        "uint32_t": "I",
        "uint16_t": "H",
        "uint8_t": "B",
        "bool": "B",
    }
    position = offset + 5  # message header and uint16 subscription ID
    result = {}
    for declaration in definition.split(":", 1)[1].split(";"):
        if not declaration:
            continue
        field = re.fullmatch(r"(\w+)(?:\[(\d+)\])? (\w+)", declaration)
        if field is None or field[1] not in formats:
            raise ValueError("f01_original_layout")
        kind, count, name = field.groups()
        fmt = "<" + formats[kind]
        if count is None:
            result[name] = int(struct.unpack_from(fmt, data, position)[0])
        position += struct.calcsize(fmt) * (int(count) if count else 1)
    return result


def prepare(source: Path, output: Path, max_age_us: int) -> dict[str, object]:
    """Verify original bytes/values before publishing a fresh local inspection."""
    target = destination(output, output.name)
    if type(max_age_us) is not int or not 0 <= max_age_us <= 60_000_000:
        raise ValueError("inspection_age_limit")
    if version("pyulog") != "1.2.2" or version("numpy") != "2.3.5":
        raise ValueError("unsupported_reader_version")
    data = read_bounded(source, SOURCE_BYTES)
    inspection = inspect_ulog(data, ULogExpectation(F01_SOURCE_ID, SOURCE_BYTES))
    if inspection.firmware_commit != FIRMWARE or inspection.dropout_count:
        raise ValueError("f01_firmware_or_dropout")
    definitions = dict(inspection.definitions)
    streams = {(s.name, s.multi_id): s for s in inspection.streams}
    if (
        ("battery_status", 0) in streams
        or ("vehicle_gps_position", 0) not in streams
        or streams[("vehicle_gps_position", 0)].record_offsets
    ):
        raise ValueError("f01_capability_mismatch")
    for name in FIELDS:
        if (
            name not in definitions
            or hashlib.sha256(definitions[name].encode()).hexdigest()
            != DEFINITIONS[name]
            or (name, 0) not in streams
            or len(streams[(name, 0)].record_offsets) != COUNTS[name]
        ):
            raise ValueError("f01_definition_or_count")
    with (
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        log = ULog(
            io.BytesIO(data),
            message_name_filter_list=list(FIELDS),
            disable_str_exceptions=False,
        )
    if log.file_corruption:
        raise ValueError("f01_parser_corruption")
    states: list[dict[str, object]] = []
    for stream, fields in FIELDS.items():
        datasets = [d for d in log.data_list if d.name == stream and d.multi_id == 0]
        if len(datasets) != 1:
            raise ValueError("f01_parser_stream")
        values = datasets[0].data
        if any(
            field not in values
            or str(values[field].dtype) != kind
            or len(values[field]) != COUNTS[stream]
            for field, kind in fields.items()
        ):
            raise ValueError("f01_parser_fields")
        previous = -1
        for ordinal, offset in enumerate(streams[(stream, 0)].record_offsets):
            native = {field: int(values[field][ordinal]) for field in fields}
            original = _original_values(definitions[stream], data, offset)
            if native != {field: original[field] for field in fields}:
                raise ValueError("f01_original_value_mismatch")
            if native["timestamp"] <= previous:
                raise ValueError("f01_ambiguous_clock")
            previous = native["timestamp"]
            states.append(project_state(stream, ordinal, native))
    timeline = [row for row in states if row["stream"] == "vehicle_status"]
    times = [integer_value(row["native_timestamp_us"]) for row in timeline]
    by_id = {string_value(row["event_id"]): row for row in states}
    matches = {
        stream: match_states(
            times,
            [
                StatePoint(
                    integer_value(row["source_ordinal"]),
                    integer_value(row["native_timestamp_us"]),
                    string_value(row["event_id"]),
                )
                for row in states
                if row["stream"] == stream
            ],
            [],
            max_age_us,
        )
        for stream in FIELDS
    }
    rows = []
    statuses: dict[str, Counter[str]] = {stream: Counter() for stream in FIELDS}
    for index, observation in enumerate(timeline):
        associated: dict[str, object] = {}
        for stream in FIELDS:
            match = matches[stream][index]
            selected = by_id[match.event_id] if match.event_id is not None else None
            associated[stream] = {
                "status": match.status,
                "event_id": match.event_id,
                "age_us": match.age_us,
                "values": None
                if selected is None
                else {
                    field: selected[field]
                    for field in FIELDS[stream]
                    if field != "timestamp"
                },
            }
            statuses[stream][match.status] += 1
        rows.append(
            {
                "observation": {
                    "event_id": observation["event_id"],
                    "source_stream": "vehicle_status:0",
                    "source_ordinal": index,
                    "native_timestamp_us": observation["native_timestamp_us"],
                },
                "gps": None,
                "battery": {
                    "status": "missing_stream",
                    "event_id": None,
                    "age_us": None,
                    "values": None,
                },
                "states": associated,
            }
        )
    body = b"".join(json_line(row) for row in rows)
    report: dict[str, object] = {
        "profile": PROFILE,
        "status": "completed_with_quality_limits",
        "source_id": F01_SOURCE_ID,
        "vehicle_id": VEHICLE,
        "privacy": "restricted",
        "firmware": FIRMWARE,
        "inspection_records": len(rows),
        "inspection_sha256": hashlib.sha256(body).hexdigest(),
        "max_age_us": max_age_us,
        "capabilities": {
            "gps": "empty_stream",
            "battery": "missing_stream",
            "state": "recorded",
        },
        "state_records": COUNTS,
        "definition_sha256": DEFINITIONS,
        "original_values_and_timestamps_match": True,
        "dropout_markers": 0,
        "association_status_counts": {
            "battery": {"missing_stream": len(rows)},
            **{name: dict(sorted(counts.items())) for name, counts in statuses.items()},
        },
        "limitations": [
            "exact-file community research; physical producer unverified",
            "GPS stream has no recorded rows; battery stream absent",
            "commander native-time timeline; no UTC or physical synchronization proof",
            "observed state only; no flight outcome, duration or completeness claim",
        ],
    }
    target.mkdir()
    with (target / "state.jsonl").open("xb") as handle:
        handle.write(b"".join(json_line(row) for row in states))
    with (target / "inspection.jsonl").open("xb") as handle:
        handle.write(body)
    with (target / "recording.json").open("xb") as handle:
        handle.write(json_line(report))
    return report
