"""Prepare restricted GPS research rows from the registered F09 source only."""

import argparse
import contextlib
import hashlib
import io
import json
import math
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path

from pyulog import ULog  # type: ignore[import-untyped]

from ulog_integrity import F09_SOURCE_ID, ULogExpectation, inspect_ulog

SOURCE_BYTES = 122_463_132
FIRMWARE = "9a2a8d4d3cf3bc74956337d8da8d506073684be0"
GPS_DEFINITION = "e01e4b9dfff5a5b7332eca486e78460ddacf9bb36363a8cb450c176eda18675e"
FIELDS = {
    "timestamp": "uint64",
    "timestamp_sample": "uint64",
    "time_utc_usec": "uint64",
    "timestamp_time_relative": "int32",
    "latitude_deg": "float64",
    "longitude_deg": "float64",
    "altitude_msl_m": "float64",
    "vel_m_s": "float32",
    "vel_ned_valid": "int8",
    "fix_type": "uint8",
}


def gps_utc_text(microseconds: int) -> str:
    """Convert an integral GPS UTC value without floating-point rounding."""
    return (
        (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=microseconds))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def prepare(source: Path, output: Path) -> dict[str, object]:
    """Verify exact bytes and selected stream before writing fresh local output."""
    if output.exists():
        raise ValueError("output_exists")
    if version("pyulog") != "1.2.2" or version("numpy") != "2.3.5":
        raise ValueError("unsupported_reader_version")
    if source.stat().st_size != SOURCE_BYTES:
        raise ValueError("source_size")
    data = source.read_bytes()
    inspection = inspect_ulog(data, ULogExpectation(F09_SOURCE_ID, SOURCE_BYTES))
    if inspection.firmware_commit != FIRMWARE:
        raise ValueError("firmware")
    definition = dict(inspection.definitions).get("vehicle_gps_position")
    if (
        definition is None
        or hashlib.sha256(definition.encode()).hexdigest() != GPS_DEFINITION
    ):
        raise ValueError("gps_definition")
    streams = [
        s
        for s in inspection.streams
        if s.name == "vehicle_gps_position" and s.multi_id == 0
    ]
    if len(streams) != 1:
        raise ValueError("gps_stream")
    with (
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        log = ULog(
            io.BytesIO(data),
            message_name_filter_list=["vehicle_gps_position"],
            disable_str_exceptions=False,
        )
    datasets = [
        d for d in log.data_list if d.name == "vehicle_gps_position" and d.multi_id == 0
    ]
    if log.file_corruption or len(datasets) != 1:
        raise ValueError("gps_parser")
    values = datasets[0].data
    if any(
        name not in values or str(values[name].dtype) != kind
        for name, kind in FIELDS.items()
    ):
        raise ValueError("gps_fields")
    n = len(values["timestamp"])
    if n != len(streams[0].record_offsets) or any(
        len(values[name]) != n for name in FIELDS
    ):
        raise ValueError("gps_stream_count")
    rows = []
    previous = -1
    valid_positions = valid_speed = gps_utc = 0
    for index in range(n):
        timestamp = int(values["timestamp"][index])
        sample = int(values["timestamp_sample"][index])
        utc = int(values["time_utc_usec"][index])
        relative = int(values["timestamp_time_relative"][index])
        if timestamp < previous:
            raise ValueError("gps_time_order")
        previous = timestamp
        fix = int(values["fix_type"][index])
        lat = float(values["latitude_deg"][index])
        lon = float(values["longitude_deg"][index])
        alt = float(values["altitude_msl_m"][index])
        speed = float(values["vel_m_s"][index])
        valid_position = (
            fix in (3, 4, 5, 6)
            and math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        )
        valid_alt = valid_position and math.isfinite(alt)
        velocity_valid_flag = int(values["vel_ned_valid"][index])
        if velocity_valid_flag not in (0, 1):
            raise ValueError("gps_velocity_flag")
        valid_velocity = (
            velocity_valid_flag == 1 and math.isfinite(speed) and speed >= 0
        )
        if utc:
            try:
                utc_text = gps_utc_text(utc)
            except (ValueError, OverflowError, OSError):
                raise ValueError("gps_utc_range") from None
            gps_utc += 1
        else:
            utc_text = None
        valid_positions += int(valid_position)
        valid_speed += int(valid_velocity)
        identity = hashlib.sha256(
            f"f09-gps-research-v1:{F09_SOURCE_ID}:vehicle_gps_position:0:{index}".encode()
        ).hexdigest()
        rows.append(
            {
                "event_id": identity,
                "vehicle_id": "f09-research-vehicle",
                "source_ordinal": index,
                "native_timestamp_us": timestamp,
                "native_sample_us": sample,
                "gps_utc": utc_text,
                "gps_time_relative_us": relative,
                "latitude_deg": lat if valid_position else None,
                "longitude_deg": lon if valid_position else None,
                "altitude_msl_m": alt if valid_alt else None,
                "ground_speed_m_s": speed if valid_velocity else None,
                "fix_type": fix,
            }
        )
    if not rows:
        raise ValueError("gps_empty")
    report: dict[str, object] = {
        "profile": "f09-gps-research-v1",
        "source_id": F09_SOURCE_ID,
        "firmware": FIRMWARE,
        "gps_definition_sha256": GPS_DEFINITION,
        "stream": "vehicle_gps_position:0",
        "records": n,
        "valid_positions": valid_positions,
        "valid_ground_speed": valid_speed,
        "gps_utc_nonzero": gps_utc,
        "dropout_markers": inspection.dropout_count,
        "dropout_duration_ms": inspection.dropout_duration_ms,
        "source_time_semantics": (
            "boot-relative; GPS UTC is not a proven sample-time mapping"
        ),
        "privacy": "restricted",
        "scope": "exact F09 source; parser/framing agreement only",
    }
    output.mkdir(parents=False)
    with (output / "gps.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
    report["rows_sha256"] = hashlib.sha256(
        (output / "gps.jsonl").read_bytes()
    ).hexdigest()
    with (output / "manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
