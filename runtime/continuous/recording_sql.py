"""Bounded F09 SQL projection with complete reader-account reconciliation.

One serialized serving writer owns a fresh database. Compare/insert/readback is
not a transaction against concurrent writers. Failures retain physical evidence;
the caller must leave its cursor unchanged and may retry identical outputs.
Schema checks do not authenticate association policy or establish archive coverage.
Each fact write admits 1..64 outputs of at most 64 KiB each. HTTP bodies/results are
capped at 8 MiB; SELECT scans at 65,536 rows and 16 MiB. Retried physical evidence
can eventually exhaust these budgets and must then refuse, not be auto-deleted.
Rollback stops the caller and retains the database; no migration is required.
"""

import hashlib
import math
import re
import time
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.conversion_contract import (
    json_line,
    json_object,
    object_value,
    require_keys,
)
from telemetry.recording_output import MAX_EVENTS
from telemetry.recording_stream import event_bytes, make_event
from ulog_integrity import F09_SOURCE_ID

type Document = dict[str, object]

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}", re.ASCII)
_MAX_OUTPUT_BYTES = 65_536
_MAX_BODY_BYTES = 8 * 1024 * 1024
_MAX_ROWS = 4096
_STATUSES = {"recorded_replay", "running", "paused", "completed", "stopped", "failed"}
_GPS_FIELDS = ("latitude_deg", "longitude_deg", "altitude_msl_m", "ground_speed_m_s")
_GROUPS = {
    "battery": ("voltage_v", "current_a", "remaining_fraction"),
    "land": ("landed", "ground_contact", "maybe_landed"),
    "vehicle_status": ("arming_state", "nav_state", "failsafe"),
}
_SCOPE = (
    "source_cluster_id",
    "source_topic_id",
    "source_topic",
    "source_partition",
    "context_sha256",
    "run_id",
)
_COLUMNS = {
    "event_id": "String",
    "input_offset": "UInt64",
    "native_timestamp_us": "UInt64",
    "native_seconds": "Float64",
    **{name: "Nullable(Float64)" for name in _GPS_FIELDS},
    **{group + "_status": "String" for group in _GROUPS},
    **{group + "_age_us": "Nullable(UInt64)" for group in _GROUPS},
    **{group + "_event_id": "Nullable(String)" for group in _GROUPS},
    **{name: "Nullable(Float64)" for name in _GROUPS["battery"]},
    **{name: "Nullable(UInt8)" for name in _GROUPS["land"] + _GROUPS["vehicle_status"]},
    "source_cluster_id": "String",
    "source_topic_id": "String",
    "source_topic": "String",
    "source_partition": "UInt8",
    "context_sha256": "String",
    "run_id": "String",
    "output_json": "String",
    "fact_json": "String",
    "inspection_json": "String",
}
_READ_SETTINGS = {
    "readonly": "1",
    "max_execution_time": "10",
    "max_threads": "1",
    "max_memory_usage": "268435456",
    "max_rows_to_read": "65536",
    "max_bytes_to_read": "16777216",
    "read_overflow_mode": "throw",
    "max_result_rows": str(_MAX_ROWS),
    "max_result_bytes": str(_MAX_BODY_BYTES),
    "result_overflow_mode": "throw",
    "output_format_json_quote_64bit_integers": "0",
    "output_format_json_quote_denormals": "0",
}


def _integer(value: object, upper: int) -> int:
    if type(value) is not int or not 0 <= value < upper:
        raise ValueError("recording_sql_integer")
    return value


def _text(value: object, pattern: str) -> str:
    if not isinstance(value, str) or re.fullmatch(pattern, value, re.ASCII) is None:
        raise ValueError("recording_sql_identifier")
    return value


def _digest(value: object) -> str:
    if not isinstance(value, str) or _HASH.fullmatch(value) is None:
        raise ValueError("recording_sql_digest")
    return value


def _number(value: object) -> float:
    if type(value) not in (int, float):
        raise ValueError("recording_sql_number")
    numeric = cast(int | float, value)
    try:
        result = float(numeric)
    except OverflowError:
        raise ValueError("recording_sql_number") from None
    if not math.isfinite(result) or result != numeric:
        raise ValueError("recording_sql_number")
    return result


def _json(value: object) -> str:
    try:
        return json_line(value).decode("utf-8").rstrip("\n")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ValueError("recording_sql_json") from None


def _association(value: object, group: str, timestamp: int) -> Document:
    section = object_value(value)
    require_keys(section, {"status", "event_id", "age_us", "values"})
    status = section["status"]
    gap = "rejection_gap" if group == "battery" else "recording_gap"
    if not isinstance(status, str) or status not in {
        "matched",
        "before_first",
        "stale",
        gap,
    }:
        raise ValueError("recording_sql_association_status")
    row: Document = {group + "_status": status}
    fields = _GROUPS[group]
    if status != "matched":
        if any(section[key] is not None for key in ("event_id", "age_us", "values")):
            raise ValueError("recording_sql_unknown_value")
        row.update({name: None for name in fields})
    else:
        identity = section["event_id"]
        if group == "battery":
            if not isinstance(identity, str) or not identity.startswith("sha256:"):
                raise ValueError("recording_sql_battery_identity")
            _digest(identity[7:])
        else:
            _digest(identity)
        age = _integer(section["age_us"], 60_000_001)
        if age > timestamp:
            raise ValueError("recording_sql_association_age")
        values = object_value(section["values"])
        require_keys(values, set(fields))
        for name in fields:
            value = values[name]
            if group == "battery":
                number = None if value is None else _number(value)
                if (name == "voltage_v" and (number is None or number < 0)) or (
                    name == "remaining_fraction"
                    and number is not None
                    and not 0 <= number <= 1
                ):
                    raise ValueError("recording_sql_battery_value")
                row[name] = number
            else:
                upper = {"nav_state": 256, "arming_state": 3}.get(name, 2)
                code = _integer(value, upper)
                if name == "arming_state" and code == 0:
                    raise ValueError("recording_sql_state_value")
                row[name] = code
    row[group + "_age_us"] = section["age_us"]
    row[group + "_event_id"] = section["event_id"]
    return row


def _project(output: Document) -> Document:
    require_keys(
        output,
        {"profile", "input_source", "input_offset", "context_sha256", "fact"},
    )
    raw = _json(output)
    if len(raw.encode("utf-8")) > _MAX_OUTPUT_BYTES:
        raise ValueError("recording_sql_output_bound")
    if output["profile"] != "f09-recording-output-v1":
        raise ValueError("recording_sql_output_profile")
    source = object_value(output["input_source"])
    require_keys(source, {"cluster_id", "topic_id", "topic", "partition"})
    cluster = _text(source["cluster_id"], r"[A-Za-z0-9_-]{1,128}")
    topic_id = _text(source["topic_id"], r"[A-Za-z0-9_-]{1,128}")
    topic = _text(source["topic"], r"[A-Za-z0-9._-]{1,249}")
    if topic in {".", ".."}:
        raise ValueError("recording_sql_identifier")
    partition = _integer(source["partition"], 1)
    offset = _integer(output["input_offset"], MAX_EVENTS)
    context = _digest(output["context_sha256"])
    fact = object_value(output["fact"])
    require_keys(
        fact,
        {
            "profile",
            "source_id",
            "run_id",
            "measurement_id",
            "native_timestamp_us",
            "input_event_sha256",
            "inspection",
        },
    )
    if fact["profile"] != "f09-recording-fact-v1" or fact["source_id"] != F09_SOURCE_ID:
        raise ValueError("recording_sql_fact_profile")
    run = _text(fact["run_id"], r"[A-Za-z0-9._-]{1,128}")
    stamp = _integer(fact["native_timestamp_us"], 2**64)
    inspection = object_value(fact["inspection"])
    require_keys(inspection, {"gps", "battery", "states"})
    gps = object_value(inspection["gps"])
    event = make_event("vehicle_gps_position:0", gps, run)
    if (
        fact["measurement_id"] != event["measurement_id"]
        or stamp != event["native_timestamp_us"]
        or _digest(fact["input_event_sha256"])
        != hashlib.sha256(event_bytes(event)).hexdigest()
    ):
        raise ValueError("recording_sql_input_mismatch")
    row: Document = {
        "event_id": fact["measurement_id"],
        "input_offset": offset,
        "native_timestamp_us": stamp,
        "native_seconds": stamp / 1_000_000,
        **{
            name: None if gps[name] is None else _number(gps[name])
            for name in _GPS_FIELDS
        },
        "source_cluster_id": cluster,
        "source_topic_id": topic_id,
        "source_topic": topic,
        "source_partition": partition,
        "context_sha256": context,
        "run_id": run,
        "output_json": raw,
        "fact_json": _json(fact),
        "inspection_json": _json(inspection),
    }
    states = object_value(inspection["states"])
    require_keys(states, {"vehicle_land_detected", "vehicle_status"})
    row.update(_association(inspection["battery"], "battery", stamp))
    row.update(_association(states["vehicle_land_detected"], "land", stamp))
    row.update(_association(states["vehicle_status"], "vehicle_status", stamp))
    return row


def _typed_equal(actual: Document, expected: Document, columns: dict[str, str]) -> bool:
    if actual.keys() != expected.keys():
        return False
    for name, kind in columns.items():
        value = actual[name]
        if value is None and kind.startswith("Nullable("):
            pass
        elif "String" in kind:
            if type(value) is not str:
                return False
        elif "Float64" in kind:
            try:
                _number(value)
            except ValueError:
                return False
        elif type(value) is not int:
            return False
        if value != expected[name]:
            return False
    return True


class RecordingSQL:
    """Fresh, bounded recording scope; reader credentials must be SELECT-only."""

    def __init__(self, admin: HttpConfig, reader: HttpConfig) -> None:
        if (
            admin.database != reader.database
            or _IDENTIFIER.fullmatch(admin.database) is None
        ):
            raise ValueError("recording_sql_database")
        self.admin, self.reader = admin, reader
        self.database = admin.database

    def initialize(self) -> None:
        """Refuse existing or incomplete scopes; never replace retained evidence."""
        self._execute(f"CREATE DATABASE {self.database}")
        columns = ", ".join(f"{name} {kind}" for name, kind in _COLUMNS.items())
        self._execute(
            f"CREATE TABLE {self.database}.facts ({columns}) "
            "ENGINE=MergeTree ORDER BY (input_offset,event_id)"
        )
        self._execute(
            f"CREATE TABLE {self.database}.progress ("
            "written_ms Int64, status String, input_next UInt64, "
            "output_count UInt64, expected UInt64) "
            "ENGINE=MergeTree ORDER BY written_ms"
        )
        self._execute(
            f"CREATE VIEW {self.database}.measurements AS "
            f"SELECT DISTINCT {', '.join(_COLUMNS)} FROM {self.database}.facts"
        )
        # Dashboards read typed values only. Excluding the raw JSON columns keeps
        # a complete-flight scan inside the datasource byte budget.
        typed = [name for name in _COLUMNS if not name.endswith("_json")]
        self._execute(
            f"CREATE VIEW {self.database}.points AS "
            f"SELECT DISTINCT {', '.join(typed)} FROM {self.database}.facts"
        )

    def _execute(self, sql: str, body: bytes = b"") -> None:
        if len(body) > _MAX_BODY_BYTES:
            raise ValueError("recording_sql_body_bound")
        _request(self.admin, sql, body, write=True)

    def read(self, sql: str) -> list[Document]:
        """Finite SELECT via the reader; HTTP settings also enforce readonly=1."""
        if (
            not isinstance(sql, str)
            or len(sql) > 32_768
            or re.match(r"\s*SELECT\b", sql, re.IGNORECASE) is None
            or any(char in sql for char in ";\0")
        ):
            raise ValueError("recording_sql_select")
        body = _request(
            self.reader,
            sql + " FORMAT JSONEachRow",
            b"",
            parameters=dict(_READ_SETTINGS),
        )
        if len(body) > _MAX_BODY_BYTES:
            raise ValueError("recording_sql_read_bound")
        lines = body.splitlines()
        if len(lines) > _MAX_ROWS:
            raise ValueError("recording_sql_read_bound")
        return [json_object(line) for line in lines]

    def write_facts(self, outputs: list[Document]) -> None:
        """Return only after the complete typed and raw batch is reader-visible."""
        if not isinstance(outputs, list) or not 1 <= len(outputs) <= 64:
            raise ValueError("recording_sql_batch_bound")
        rows = [_project(object_value(output)) for output in outputs]
        expected: dict[str, Document] = {}
        offsets: dict[int, str] = {}
        scope = {name: rows[0][name] for name in _SCOPE}
        for row in rows:
            identity = cast(str, row["event_id"])
            offset = cast(int, row["input_offset"])
            if (
                any(row[name] != scope[name] for name in _SCOPE)
                or (identity in expected and row != expected[identity])
                or (offset in offsets and offsets[offset] != identity)
            ):
                raise ValueError("recording_sql_competing_fact")
            expected[identity], offsets[offset] = row, identity
        prior_scope = self.read(
            f"SELECT DISTINCT {', '.join(_SCOPE)} FROM {self.database}.facts LIMIT 2"
        )
        scope_columns = {name: _COLUMNS[name] for name in _SCOPE}
        if any(
            not _typed_equal(actual, scope, scope_columns) for actual in prior_scope
        ):
            raise ValueError("recording_sql_scope_conflict")
        # Only validated hexadecimal IDs and bounded integers enter this query.
        ids = ",".join(f"'{identity}'" for identity in expected)
        positions = ",".join(str(offset) for offset in offsets)
        query = (
            f"SELECT DISTINCT * FROM {self.database}.facts "
            f"WHERE event_id IN ({ids}) OR input_offset IN ({positions})"
        )

        def check(actual: list[Document], *, complete: bool) -> None:
            seen: set[str] = set()
            for row in actual:
                identity = row.get("event_id")
                if (
                    not isinstance(identity, str)
                    or identity not in expected
                    or not _typed_equal(row, expected[identity], _COLUMNS)
                ):
                    raise ValueError("recording_sql_competing_fact")
                seen.add(identity)
            if complete and seen != expected.keys():
                raise ValueError("recording_sql_content_readback")

        check(self.read(query), complete=False)
        self._execute(
            f"INSERT INTO {self.database}.facts SETTINGS async_insert=0, "
            "insert_deduplicate=0, input_format_skip_unknown_fields=0 "
            "FORMAT JSONEachRow",
            b"".join(json_line(row) for row in rows),
        )
        check(self.read(query), complete=True)

    def logical_count(self) -> int:
        """Count distinct identities by scanning only the event_id column.

        The DISTINCT measurements view reads every raw JSON column, so it exceeds
        the scan budget well before a complete flight. write_facts refuses
        competing content, so distinct identities equal logical measurements.
        """
        rows = self.read(f"SELECT uniqExact(event_id) AS n FROM {self.database}.facts")
        if len(rows) != 1 or set(rows[0]) != {"n"}:
            raise ValueError("recording_sql_count_readback")
        return _integer(rows[0]["n"], MAX_EVENTS + 1)

    def logical_ids(self) -> set[str]:
        """Read the complete identity set in ordered keyset pages."""
        result: set[str] = set()
        last = ""
        for _ in range(MAX_EVENTS // _MAX_ROWS + 2):
            # Only a validated hexadecimal identity enters the page condition.
            rows = self.read(
                f"SELECT DISTINCT event_id FROM {self.database}.facts "
                f"WHERE event_id > '{last}' ORDER BY event_id LIMIT {_MAX_ROWS}"
            )
            for row in rows:
                if set(row) != {"event_id"}:
                    raise ValueError("recording_sql_identity_readback")
                identity = _digest(row["event_id"])
                if identity <= last:
                    raise ValueError("recording_sql_identity_order")
                result.add(identity)
                last = identity
            if len(result) > MAX_EVENTS:
                raise ValueError("recording_sql_identity_bound")
            if len(rows) < _MAX_ROWS:
                return result
        raise ValueError("recording_sql_identity_bound")

    def progress(
        self, status: str, input_next: int, output_count: int, expected: int
    ) -> None:
        """Record pipeline observation time, never source time or connectivity."""
        if not isinstance(status, str) or status not in _STATUSES:
            raise ValueError("recording_sql_progress_status")
        _integer(input_next, MAX_EVENTS + 1)
        _integer(output_count, MAX_EVENTS + 1)
        _integer(expected, MAX_EVENTS + 1)
        if (
            expected < 1
            or output_count > min(expected, input_next)
            or (status == "completed" and output_count != expected)
        ):
            raise ValueError("recording_sql_progress_count")
        row: Document = {
            "written_ms": time.time_ns() // 1_000_000,
            "status": status,
            "input_next": input_next,
            "output_count": output_count,
            "expected": expected,
        }
        self._execute(
            f"INSERT INTO {self.database}.progress SETTINGS async_insert=0 "
            "FORMAT JSONEachRow",
            json_line(row),
        )
        actual = self.read(
            f"SELECT DISTINCT * FROM {self.database}.progress "
            f"WHERE written_ms={row['written_ms']}"
        )
        columns = {name: "String" if name == "status" else "Int64" for name in row}
        if not any(_typed_equal(value, row, columns) for value in actual):
            raise ValueError("recording_sql_progress_readback")
