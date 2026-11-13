"""Shared bounded local recording projection and exact readback admission."""

import hashlib
import os
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded
from ulog_integrity import F01_SOURCE_ID, F09_SOURCE_ID

DATABASE = "recording_views_v1"
PROJECTION = "recording-view-v1"
PROFILES = {
    "f09-recording-inspection-v1": (F09_SOURCE_ID, "f09-research-vehicle", 21_054),
    "f01-recording-inspection-v1": (F01_SOURCE_ID, "f01-research-recording", 77),
}
VALUE_FIELDS = {
    "latitude_deg": ("gps", "deg"),
    "longitude_deg": ("gps", "deg"),
    "altitude_msl_m": ("gps", "m"),
    "ground_speed_m_s": ("gps", "m/s"),
    "fix_type": ("gps", "code"),
    "voltage_v": ("battery", "V"),
    "current_a": ("battery", "A"),
    "remaining_fraction": ("battery", "fraction"),
    "landed": ("land", "flag"),
    "ground_contact": ("land", "flag"),
    "maybe_landed": ("land", "flag"),
    "arming_state": ("commander", "code"),
    "nav_state": ("commander", "code"),
    "failsafe": ("commander", "flag"),
}
COLUMNS = {
    "recording_id": "String",
    "observation_id": "String",
    "observation_stream": "String",
    "observation_ordinal": "UInt32",
    "native_timestamp_us": "UInt64",
    "receiver_utc": "Nullable(String)",
    **{name: "Nullable(Float64)" for name in VALUE_FIELDS},
    **{name + "_status": "String" for name in ("gps", "battery", "land", "commander")},
    **{
        name + "_age_us": "Nullable(UInt64)"
        for name in ("battery", "land", "commander")
    },
    **{
        name + "_event_id": "Nullable(String)"
        for name in ("battery", "land", "commander")
    },
    "projection_json": "String",
}
REGISTRY_COLUMNS = {
    "recording_id": "String",
    "source_id": "String",
    "vehicle_id": "String",
    "profile": "String",
    "projection_version": "String",
    "max_age_us": "UInt64",
    "records": "UInt32",
    "first_native_us": "UInt64",
    "last_native_us": "UInt64",
    "inspection_sha256": "String",
    "projection_sha256": "String",
    "capabilities_json": "String",
}
BOUNDS = (
    " SETTINGS max_execution_time=10, max_threads=1, "
    "max_memory_usage=268435456, max_rows_to_read=50000, "
    "max_bytes_to_read=64000000, read_overflow_mode='throw'"
)


def project(directory: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Read protected prepared artifacts, retaining recording and observation scope.

    A manifest/digest is local integrity evidence, not source authentication.
    Original-source admission belongs to the preceding adapter command.
    """
    report = json_object(read_bounded(directory / "recording.json", 32_000))
    profile = string_value(report["profile"])
    if profile not in PROFILES:
        raise ValueError("unsupported_recording_profile")
    source, vehicle, count = PROFILES[profile]
    if (
        report.get("source_id") != source
        or report.get("vehicle_id") != vehicle
        or report.get("inspection_records") != count
    ):
        raise ValueError("recording_scope_mismatch")
    max_age = integer_value(report["max_age_us"])
    if not 0 <= max_age <= 60_000_000:
        raise ValueError("inspection_age_limit")
    body = read_bounded(directory / "inspection.jsonl", 64 * 1024 * 1024)
    digest = hashlib.sha256(body).hexdigest()
    if digest != report["inspection_sha256"]:
        raise ValueError("inspection_digest_mismatch")
    raw_rows = [json_object(line) for line in body.splitlines()]
    if len(raw_rows) != count:
        raise ValueError("inspection_count_mismatch")
    recording_id = hashlib.sha256(
        f"{PROJECTION}:{source}:{profile}:{max_age}".encode()
    ).hexdigest()
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    previous = -1
    for ordinal, raw in enumerate(raw_rows):
        gps = None if raw["gps"] is None else object_value(raw["gps"])
        if (gps is None) != (profile == "f01-recording-inspection-v1"):
            raise ValueError("recording_timeline_mismatch")
        observation = object_value(raw["observation"]) if gps is None else gps
        stamp = integer_value(observation["native_timestamp_us"])
        identity = string_value(observation["event_id"])
        identity_profile, identity_stream = (
            ("f01-state-research-v1", "vehicle_status")
            if gps is None
            else ("f09-gps-research-v1", "vehicle_gps_position")
        )
        expected_id = hashlib.sha256(
            f"{identity_profile}:{source}:{identity_stream}:0:{ordinal}".encode()
        ).hexdigest()
        if identity != expected_id or (
            gps is None and observation.get("source_stream") != "vehicle_status:0"
        ):
            raise ValueError("recording_observation_identity")
        if (
            observation["source_ordinal"] != ordinal
            or stamp <= previous
            or not 0 <= stamp < 2**64
            or identity in seen
        ):
            raise ValueError("inspection_observation_order")
        previous = stamp
        seen.add(identity)
        row: dict[str, object] = {
            "recording_id": recording_id,
            "observation_id": identity,
            "observation_stream": "vehicle_gps_position:0"
            if gps is not None
            else string_value(observation["source_stream"]),
            "observation_ordinal": ordinal,
            "native_timestamp_us": stamp,
            "receiver_utc": None if gps is None else gps["gps_utc"],
            "gps_status": "empty_stream" if gps is None else "recorded",
        }
        for field, (group, _) in VALUE_FIELDS.items():
            if group == "gps":
                row[field] = None if gps is None else gps[field]
        states = object_value(raw["states"])
        for group, section in (
            ("battery", object_value(raw["battery"])),
            ("land", object_value(states["vehicle_land_detected"])),
            ("commander", object_value(states["vehicle_status"])),
        ):
            status = string_value(section["status"])
            allowed = {"matched", "before_first", "stale"}
            allowed.add("rejection_gap" if group == "battery" else "recording_gap")
            if gps is None and group == "battery":
                allowed = {"missing_stream"}
            if status not in allowed:
                raise ValueError("inspection_association_status")
            if status == "matched":
                values = object_value(section["values"])
                age = integer_value(section["age_us"])
                if not 0 <= age <= max_age:
                    raise ValueError("inspection_association_age")
                string_value(section["event_id"])
            else:
                if any(
                    section[key] is not None for key in ("values", "event_id", "age_us")
                ):
                    raise ValueError("inspection_unknown_value")
                values = {}
            row[group + "_status"] = status
            row[group + "_age_us"] = section["age_us"]
            row[group + "_event_id"] = section["event_id"]
            for field, (owner, _) in VALUE_FIELDS.items():
                if owner == group:
                    row[field] = values[field] if status == "matched" else None
        row["projection_json"] = json_line(row).decode().rstrip("\n")
        rows.append(row)
    projection_digest = hashlib.sha256(
        b"".join(json_line(row) for row in rows)
    ).hexdigest()
    capabilities = report.get(
        "capabilities", {"gps": "recorded", "battery": "recorded", "state": "recorded"}
    )
    registry: dict[str, object] = {
        "recording_id": recording_id,
        "source_id": source,
        "vehicle_id": vehicle,
        "profile": profile,
        "projection_version": PROJECTION,
        "max_age_us": max_age,
        "records": len(rows),
        "first_native_us": rows[0]["native_timestamp_us"],
        "last_native_us": rows[-1]["native_timestamp_us"],
        "inspection_sha256": digest,
        "projection_sha256": projection_digest,
        "capabilities_json": json_line(capabilities).decode().strip(),
    }
    return registry, rows


def _select(
    config: HttpConfig, sql: str, parameters: dict[str, str]
) -> list[dict[str, object]]:
    return [
        json_object(line)
        for line in _request(
            config, sql + BOUNDS + " FORMAT JSONEachRow", b"", parameters=parameters
        ).splitlines()
    ]


def reconcile(
    config: HttpConfig, registry: dict[str, object], rows: list[dict[str, object]]
) -> None:
    """Compare every distinct typed field and raw projection in finite batches."""
    parameters = {"param_id": string_value(registry["recording_id"])}
    count = _select(
        config,
        f"SELECT count() AS n FROM (SELECT DISTINCT * FROM {DATABASE}.observations "
        "WHERE recording_id={id:String})",
        parameters,
    )
    if count != [{"n": len(rows)}]:
        raise ValueError("recording_sql_count")
    for start in range(0, len(rows), 500):
        batch = _select(
            config,
            f"SELECT DISTINCT * FROM {DATABASE}.observations "
            "WHERE recording_id={id:String} AND observation_ordinal >= {lo:UInt32} "
            "AND observation_ordinal < {hi:UInt32} ORDER BY observation_ordinal",
            {**parameters, "param_lo": str(start), "param_hi": str(start + 500)},
        )
        if batch != rows[start : start + 500]:
            raise ValueError("recording_sql_values")


def load(directory: Path, port: int = 28132) -> dict[str, object]:
    """Admit a fresh recording, or verify an identical existing delivery read-only.

    Local admissions must be serialized. Ambiguous writes and partial scopes
    refuse; this function never deletes, resumes or replaces existing records.
    """
    registry, rows = project(directory)
    admin = HttpConfig(
        port,
        "default",
        "flight_admin",
        os.environ["FLIGHT_CH_ADMIN_PASSWORD"],
        timeout_seconds=15,
    )
    reader = HttpConfig(
        port,
        "default",
        "flight_reader",
        os.environ["FLIGHT_CH_READER_PASSWORD"],
        timeout_seconds=15,
    )
    databases = _select(
        admin, f"SELECT count() AS n FROM system.databases WHERE name='{DATABASE}'", {}
    )
    if databases == [{"n": 0}]:
        _request(admin, f"CREATE DATABASE {DATABASE}", b"", write=True)
    for table, columns in (("observations", COLUMNS), ("recordings", REGISTRY_COLUMNS)):
        schema = ", ".join(name + " " + kind for name, kind in columns.items())
        order = (
            "(recording_id, observation_ordinal)"
            if table == "observations"
            else "recording_id"
        )
        schema_query = (
            f"SELECT name, type FROM system.columns "
            f"WHERE database='{DATABASE}' AND table='{table}' ORDER BY position"
        )
        actual = _select(admin, schema_query, {})
        if not actual:
            _request(
                admin,
                f"CREATE TABLE {DATABASE}.{table} ({schema}) "
                f"ENGINE=MergeTree ORDER BY {order}",
                b"",
                write=True,
            )
        actual = _select(
            admin,
            schema_query,
            {},
        )
        if actual != [{"name": name, "type": kind} for name, kind in columns.items()]:
            raise ValueError("recording_sql_schema")
    parameters = {"param_id": string_value(registry["recording_id"])}
    existing = _select(
        admin,
        f"SELECT DISTINCT * FROM {DATABASE}.recordings "
        "WHERE recording_id={id:String}",
        parameters,
    )
    if existing:
        if existing != [registry]:
            raise ValueError("recording_registry_conflict")
        reconcile(reader, registry, rows)
        return {
            "status": "verified_existing",
            "recording_id": registry["recording_id"],
            "records": len(rows),
        }
    present = _select(
        admin,
        f"SELECT count() AS n FROM {DATABASE}.observations "
        "WHERE recording_id={id:String}",
        parameters,
    )
    if present != [{"n": 0}]:
        raise ValueError("recording_partial_scope")
    for start in range(0, len(rows), 500):
        _request(
            admin,
            f"INSERT INTO {DATABASE}.observations "
            "SETTINGS async_insert=0 FORMAT JSONEachRow",
            b"".join(json_line(row) for row in rows[start : start + 500]),
            write=True,
        )
    reconcile(admin, registry, rows)
    _request(
        admin,
        f"INSERT INTO {DATABASE}.recordings SETTINGS async_insert=0 FORMAT JSONEachRow",
        json_line(registry),
        write=True,
    )
    for table in ("observations", "recordings"):
        _request(
            admin,
            f"GRANT SELECT ON {DATABASE}.{table} TO flight_reader",
            b"",
            write=True,
        )
    if _select(
        reader,
        f"SELECT DISTINCT * FROM {DATABASE}.recordings "
        "WHERE recording_id={id:String}",
        parameters,
    ) != [registry]:
        raise ValueError("recording_registry_readback")
    reconcile(reader, registry, rows)
    return {
        "status": "loaded_and_verified",
        "recording_id": registry["recording_id"],
        "records": len(rows),
    }
