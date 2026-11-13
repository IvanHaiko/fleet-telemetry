"""Exact-file F09 state research projection; no flight-phase inference."""

import contextlib
import hashlib
import io
import json
from collections import Counter
from importlib.metadata import version
from itertools import pairwise
from pathlib import Path

from telemetry.conversion_contract import integer_value, json_object, require_keys
from ulog_integrity import F09_SOURCE_ID, ULogExpectation, inspect_ulog

PROFILE = "f09-state-research-v1"
SOURCE_BYTES = 122_463_132
FIRMWARE = "9a2a8d4d3cf3bc74956337d8da8d506073684be0"
DEFINITIONS = {
    "vehicle_land_detected": (
        "27a0f6bb53a636b60bd86e021e3db416a7cc6505701a6285f2bc793fc76cb687"
    ),
    "vehicle_status": (
        "1831131423c63fe4eb3fc837cc6f4cf5aed73a01f475c6e4034aaec6044d26dd"
    ),
}
COUNTS = {"vehicle_land_detected": 2337, "vehicle_status": 4644}
FIELDS = {
    "vehicle_land_detected": {
        "timestamp": "uint64",
        "landed": "int8",
        "ground_contact": "int8",
        "maybe_landed": "int8",
    },
    "vehicle_status": {
        "timestamp": "uint64",
        "arming_state": "uint8",
        "nav_state": "uint8",
        "failsafe": "int8",
    },
}
VALUES = (
    "landed",
    "ground_contact",
    "maybe_landed",
    "arming_state",
    "nav_state",
    "failsafe",
)
MAX_ROWS = 10_000
MAX_BYTES = 8_000_000


def project(stream: str, ordinal: int, native: dict[str, int]) -> dict[str, object]:
    """Preserve recorded state codes and native time under a separate identity."""
    if stream not in FIELDS:
        raise ValueError("unsupported_state_stream")
    if type(ordinal) is not int or not 0 <= ordinal < MAX_ROWS:
        raise ValueError("state_ordinal")
    require_keys(native, set(FIELDS[stream]))
    if any(type(value) is not int for value in native.values()):
        raise ValueError("state_integer")
    if not 0 <= native["timestamp"] < 2**64:
        raise ValueError("state_timestamp")
    for field in FIELDS[stream].keys() - {"timestamp"}:
        value = native[field]
        if field in ("landed", "ground_contact", "maybe_landed", "failsafe"):
            valid = value in (0, 1)
        elif field == "arming_state":
            valid = value in (1, 2)
        else:
            # Preserve all defined and reserved uint8 codes; do not invent labels.
            valid = 0 <= value <= 255
        if not valid:
            raise ValueError("state_value")
    identity = hashlib.sha256(
        f"{PROFILE}:{F09_SOURCE_ID}:{stream}:0:{ordinal}".encode()
    ).hexdigest()
    return {
        "event_id": identity,
        "stream": stream,
        "source_ordinal": ordinal,
        "native_timestamp_us": native["timestamp"],
        **{name: native.get(name) for name in VALUES},
    }


def validate_rows(rows: list[dict[str, object]]) -> None:
    """Reconstruct each strict row and check per-stream order and coverage."""
    if not rows or len(rows) > MAX_ROWS:
        raise ValueError("state_row_limit")
    counts: Counter[str] = Counter()
    previous: dict[str, int] = {}
    for row in rows:
        stream = row.get("stream")
        if not isinstance(stream, str) or stream not in FIELDS:
            raise ValueError("unsupported_state_stream")
        ordinal = integer_value(row.get("source_ordinal"))
        timestamp = integer_value(row.get("native_timestamp_us"))
        if ordinal != counts[stream] or timestamp < previous.get(stream, 0):
            raise ValueError("state_order")
        native = {"timestamp": timestamp}
        native.update(
            {
                name: integer_value(row.get(name))
                for name in FIELDS[stream]
                if name != "timestamp"
            }
        )
        if row != project(stream, ordinal, native):
            raise ValueError("state_row_mismatch")
        counts[stream] += 1
        previous[stream] = timestamp
    if dict(counts) != COUNTS:
        raise ValueError("state_source_count")


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    """Describe observed records, never time-weighted state or flight duration."""
    validate_rows(rows)
    groups: dict[str, object] = {}
    for stream in FIELDS:
        selected = [row for row in rows if row["stream"] == stream]
        times = [integer_value(row["native_timestamp_us"]) for row in selected]
        distributions: dict[str, object] = {}
        transitions: dict[str, int] = {}
        for name in FIELDS[stream].keys() - {"timestamp"}:
            values = [integer_value(row[name]) for row in selected]
            distributions[name] = dict(sorted(Counter(map(str, values)).items()))
            transitions[name] = sum(a != b for a, b in pairwise(values))
        groups[stream] = {
            "records": len(selected),
            "first_native_us": times[0],
            "last_native_us": times[-1],
            "observed_span_us": times[-1] - times[0],
            "max_adjacent_gap_us": max((b - a for a, b in pairwise(times)), default=0),
            "record_value_counts": distributions,
            "adjacent_value_changes": transitions,
        }
    return {
        "profile": "f09-recording-state-gold-v1",
        "source_id": F09_SOURCE_ID,
        "state_profile": PROFILE,
        "streams": groups,
        "privacy": "restricted",
        "scope": "prepared-to-SQL equality; original framing verified at preparation",
        "limitations": [
            "record-weighted counts; no state durations or flight phases",
            "native time since system start; no validated UTC mapping",
            "15 source dropout markers; missing measurement count unknown",
            "no cross-stream temporal association or sealed concurrent SQL snapshot",
            "exact F09 research profile; no general real-device admission",
        ],
    }


def prepare(source: Path, output: Path) -> dict[str, object]:
    """Verify registered original bytes before parsing just two selected streams."""
    from pyulog import ULog  # type: ignore[import-untyped]

    if output.exists():
        raise ValueError("output_exists")
    if version("pyulog") != "1.2.2" or version("numpy") != "2.3.5":
        raise ValueError("unsupported_reader_version")
    if source.stat().st_size != SOURCE_BYTES:
        raise ValueError("source_size")
    data = source.read_bytes()
    inspection = inspect_ulog(data, ULogExpectation(F09_SOURCE_ID, SOURCE_BYTES))
    if inspection.firmware_commit != FIRMWARE:
        raise ValueError("state_firmware")
    embedded = dict(inspection.definitions)
    for name, expected in DEFINITIONS.items():
        definition = embedded.get(name)
        if (
            definition is None
            or hashlib.sha256(definition.encode()).hexdigest() != expected
        ):
            raise ValueError("state_definition")
        streams = [s for s in inspection.streams if s.name == name and s.multi_id == 0]
        if len(streams) != 1 or len(streams[0].record_offsets) != COUNTS[name]:
            raise ValueError("state_framed_count")
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
        raise ValueError("state_parser_corruption")
    rows: list[dict[str, object]] = []
    for name, fields in FIELDS.items():
        datasets = [d for d in log.data_list if d.name == name and d.multi_id == 0]
        if len(datasets) != 1:
            raise ValueError("state_parser_stream")
        values = datasets[0].data
        if any(
            field not in values
            or str(values[field].dtype) != dtype
            or len(values[field]) != COUNTS[name]
            for field, dtype in fields.items()
        ):
            raise ValueError("state_parser_fields")
        for ordinal in range(COUNTS[name]):
            rows.append(
                project(
                    name,
                    ordinal,
                    {field: int(values[field][ordinal]) for field in fields},
                )
            )
    validate_rows(rows)
    body = b"".join(
        (json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n").encode()
        for row in rows
    )
    if len(body) > MAX_BYTES:
        raise ValueError("state_byte_limit")
    manifest: dict[str, object] = {
        "profile": PROFILE,
        "source_id": F09_SOURCE_ID,
        "firmware": FIRMWARE,
        "definition_sha256": DEFINITIONS,
        "records": COUNTS,
        "rows_sha256": hashlib.sha256(body).hexdigest(),
        "dropout_markers": inspection.dropout_count,
        "dropout_duration_ms": inspection.dropout_duration_ms,
        "privacy": "restricted",
        "clock": "microseconds since system start",
    }
    output.mkdir(parents=False)
    with (output / "state.jsonl").open("xb") as target:
        target.write(body)
    with (output / "manifest.json").open("x", encoding="utf-8") as target:
        json.dump(manifest, target, sort_keys=True, indent=2)
        target.write("\n")
    return manifest


def read_prepared(directory: Path) -> list[dict[str, object]]:
    """Check bounded artifacts; a self-written manifest is not authentication."""
    manifest_path = directory / "manifest.json"
    path = directory / "state.jsonl"
    if manifest_path.stat().st_size > 8192 or path.stat().st_size > MAX_BYTES:
        raise ValueError("state_byte_limit")
    manifest = json_object(manifest_path.read_bytes())
    body = path.read_bytes()
    if (
        len(body) > MAX_BYTES
        or manifest.get("profile") != PROFILE
        or manifest.get("source_id") != F09_SOURCE_ID
        or manifest.get("firmware") != FIRMWARE
        or manifest.get("definition_sha256") != DEFINITIONS
        or manifest.get("records") != COUNTS
        or manifest.get("rows_sha256") != hashlib.sha256(body).hexdigest()
    ):
        raise ValueError("state_artifact_mismatch")
    rows = [json_object(line) for line in body.splitlines()]
    validate_rows(rows)
    return rows
