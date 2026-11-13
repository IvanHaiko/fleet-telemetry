"""Authored SQL-boundary invariants; actual ClickHouse is checked by integration."""

import hashlib
import re
import time
from copy import deepcopy
from typing import cast

import pytest
from recording_stream_support import gps

from runtime.clickhouse.transport import HttpConfig
from runtime.continuous import recording_sql
from telemetry.conversion_contract import json_line, json_object, object_value
from telemetry.recording_stream import event_bytes, make_event
from ulog_integrity import F09_SOURCE_ID

type Document = dict[str, object]


def output(ordinal: int = 0, offset: int = 3) -> Document:
    """Authored complete fact shape, with no peer module or original flight data."""
    position = gps(ordinal, 2_000_000 + ordinal)
    event = make_event("vehicle_gps_position:0", position, "authored-sql")
    return {
        "profile": "f09-recording-output-v1",
        "input_source": {
            "cluster_id": "authored-cluster",
            "topic_id": "00000000-0000-0000-0000-000000000001",
            "topic": "authored-recording",
            "partition": 0,
        },
        "input_offset": offset,
        "context_sha256": "a" * 64,
        "fact": {
            "profile": "f09-recording-fact-v1",
            "source_id": F09_SOURCE_ID,
            "run_id": "authored-sql",
            "measurement_id": position["event_id"],
            "native_timestamp_us": position["native_timestamp_us"],
            "input_event_sha256": hashlib.sha256(event_bytes(event)).hexdigest(),
            "inspection": {
                "gps": position,
                "battery": {
                    "status": "matched",
                    "event_id": "sha256:" + "b" * 64,
                    "age_us": 100,
                    "values": {
                        "voltage_v": 12.5,
                        "current_a": -1.5,
                        "remaining_fraction": None,
                    },
                },
                "states": {
                    "vehicle_land_detected": {
                        "status": "matched",
                        "event_id": "c" * 64,
                        "age_us": 200,
                        "values": {"landed": 1, "ground_contact": 0, "maybe_landed": 0},
                    },
                    "vehicle_status": {
                        "status": "matched",
                        "event_id": "d" * 64,
                        "age_us": 300,
                        "values": {"arming_state": 2, "nav_state": 255, "failsafe": 0},
                    },
                },
            },
        },
    }


def inspection(document: Document) -> Document:
    return object_value(object_value(document["fact"])["inspection"])


class Boundary:
    """Fake HTTP responses, not an SQL engine or an independent acceptance oracle."""

    def __init__(self) -> None:
        self.calls: list[
            tuple[HttpConfig, str, bytes, bool, dict[str, str] | None]
        ] = []
        self.created = False
        self.facts: list[Document] = []
        self.progress: list[Document] = []
        self.drop_insert = False
        self.corrupt: tuple[str, object] | None = None
        self.deny_reader = False
        self.reply: bytes | None = None

    def request(
        self,
        config: HttpConfig,
        sql: str,
        body: bytes,
        *,
        write: bool = False,
        parameters: dict[str, str] | None = None,
    ) -> bytes:
        self.calls.append((config, sql, body, write, parameters))
        if sql.startswith("CREATE DATABASE"):
            if self.created:
                raise ValueError("scope_exists")
            self.created = True
            return b""
        if sql.startswith("CREATE"):
            return b""
        if sql.startswith("INSERT"):
            if not self.drop_insert:
                rows = [json_object(line) for line in body.splitlines()]
                (self.progress if ".progress " in sql else self.facts).extend(rows)
            return b""
        if self.deny_reader:
            raise PermissionError("reader_denied")
        assert not write and body == b"" and config.user == "reader"
        assert parameters is not None and parameters["readonly"] == "1"
        if self.reply is not None:
            return self.reply
        if ".progress " in sql:
            stamp = int(sql.split("written_ms=")[1].split()[0])
            rows = [row for row in self.progress if row["written_ms"] == stamp]
        elif "SELECT DISTINCT *" in sql:
            ids_match = re.search(r"event_id IN \(([^)]+)\)", sql)
            offsets_match = re.search(r"input_offset IN \(([^)]+)\)", sql)
            assert ids_match is not None and offsets_match is not None
            identities = set(re.findall(r"'([0-9a-f]{64})'", ids_match[1]))
            offsets = {int(value) for value in offsets_match[1].split(",")}
            rows = [
                row
                for row in self.facts
                if row["event_id"] in identities or row["input_offset"] in offsets
            ]
        else:
            # The only other adapter query selects the complete stable scope.
            names = sql.removeprefix("SELECT DISTINCT ").split(" FROM ")[0].split(", ")
            rows = [{name: row[name] for name in names} for row in self.facts]
        rows = deepcopy(rows)
        if self.corrupt and self.facts and "SELECT DISTINCT *" in sql:
            for row in rows:
                row[self.corrupt[0]] = self.corrupt[1]
        return b"".join(sorted({json_line(row) for row in rows}))


@pytest.fixture
def store(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[recording_sql.RecordingSQL, Boundary]:
    boundary = Boundary()
    monkeypatch.setattr(recording_sql, "_request", boundary.request)
    admin = HttpConfig(8123, "authored_recording", "admin", "authored-password")
    reader = HttpConfig(
        8123, "authored_recording", "reader", "authored-reader-password"
    )
    return recording_sql.RecordingSQL(admin, reader), boundary


def test_fresh_schema_and_database_scope(
    store: tuple[recording_sql.RecordingSQL, Boundary],
) -> None:
    sql, boundary = store
    sql.initialize()
    statements = [call[1] for call in boundary.calls]
    assert len(statements) == 4
    assert statements[0] == "CREATE DATABASE authored_recording"
    assert "ENGINE=MergeTree" in statements[1]
    assert "SELECT DISTINCT" in statements[3]
    assert "output_json" in statements[3] and "inspection_json" in statements[3]
    assert all(call[0] == sql.admin and call[3] for call in boundary.calls)
    assert not any(
        "IF NOT EXISTS" in statement or "DROP" in statement for statement in statements
    )
    with pytest.raises(ValueError, match="scope_exists"):
        sql.initialize()
    assert len(boundary.calls) == 5
    with pytest.raises(ValueError, match="recording_sql_database"):
        recording_sql.RecordingSQL(
            sql.admin, HttpConfig(8123, "different", "reader", "password")
        )


def test_retries_keep_complete_physical_evidence_and_stable_logical_rows(
    store: tuple[recording_sql.RecordingSQL, Boundary],
) -> None:
    sql, boundary = store
    documents = [output(), output(1, 8)]
    before = deepcopy(documents)
    sql.write_facts(documents)
    sql.write_facts([deepcopy(documents[0])])
    assert documents == before
    assert len(boundary.facts) == 3
    assert len({json_line(row) for row in boundary.facts}) == 2
    row = boundary.facts[0]
    assert row["event_id"] == object_value(documents[0]["fact"])["measurement_id"]
    assert row["input_offset"] == 3 and row["native_timestamp_us"] == 2_000_000
    assert row["native_seconds"] == 2.0
    assert (
        row["latitude_deg"],
        row["altitude_msl_m"],
        row["ground_speed_m_s"],
    ) == (0.0, 10.0, 1.0)
    assert (row["voltage_v"], row["current_a"], row["remaining_fraction"]) == (
        12.5,
        -1.5,
        None,
    )
    assert row["nav_state"] == 255 and row["landed"] == 1
    assert (
        row["battery_age_us"],
        row["land_age_us"],
        row["vehicle_status_age_us"],
    ) == (100, 200, 300)
    assert json_object(cast(str, row["output_json"]).encode()) == documents[0]
    assert json_object(cast(str, row["fact_json"]).encode()) == documents[0]["fact"]
    assert json_object(cast(str, row["inspection_json"]).encode()) == inspection(
        documents[0]
    )
    # Both calls end with reader-account content checks, never just an insert ACK.
    assert boundary.calls[-1][0] == sql.reader and not boundary.calls[-1][3]
    assert "SELECT DISTINCT *" in boundary.calls[-1][1]


@pytest.mark.parametrize("status", ["before_first", "stale", "gap"])
def test_unknown_associations_keep_values_references_and_ages_null(
    store: tuple[recording_sql.RecordingSQL, Boundary],
    status: str,
) -> None:
    sql, boundary = store
    document = output()
    selected = inspection(document)
    position = object_value(selected["gps"])
    for field in (
        "latitude_deg",
        "longitude_deg",
        "altitude_msl_m",
        "ground_speed_m_s",
    ):
        position[field] = None
    object_value(document["fact"])["input_event_sha256"] = hashlib.sha256(
        event_bytes(make_event("vehicle_gps_position:0", position, "authored-sql"))
    ).hexdigest()
    states = object_value(selected["states"])
    for name, section in (
        ("battery", object_value(selected["battery"])),
        ("land", object_value(states["vehicle_land_detected"])),
        ("vehicle_status", object_value(states["vehicle_status"])),
    ):
        label = "rejection_gap" if name == "battery" else "recording_gap"
        section.update(
            status=label if status == "gap" else status,
            event_id=None,
            age_us=None,
            values=None,
        )
    sql.write_facts([document])
    row = boundary.facts[0]
    assert row["latitude_deg"] is None and row["ground_speed_m_s"] is None
    for name in ("battery", "land", "vehicle_status"):
        assert row[name + "_age_us"] is None and row[name + "_event_id"] is None
    for name in (
        "voltage_v",
        "current_a",
        "remaining_fraction",
        "landed",
        "ground_contact",
        "maybe_landed",
        "arming_state",
        "nav_state",
        "failsafe",
    ):
        assert row[name] is None
    assert row["battery_status"] == ("rejection_gap" if status == "gap" else status)
    assert row["land_status"] == ("recording_gap" if status == "gap" else status)


@pytest.mark.parametrize("kind", ["measurement", "coordinate", "raw", "scope", "batch"])
def test_competing_content_refuses_before_any_additional_insert(
    store: tuple[recording_sql.RecordingSQL, Boundary],
    kind: str,
) -> None:
    sql, boundary = store
    sql.write_facts([output()])
    changed = output(1, 3) if kind == "coordinate" else output()
    if kind == "measurement":
        changed["input_offset"] = 4
    elif kind == "raw":
        object_value(inspection(changed)["battery"])["age_us"] = 101
    elif kind == "scope":
        changed = output(1, 8)
        changed["context_sha256"] = "e" * 64
    batch = [changed, output(1, 3)] if kind == "batch" else [changed]
    with pytest.raises(
        ValueError, match="recording_sql_(competing_fact|scope_conflict)"
    ):
        sql.write_facts(batch)
    assert len(boundary.facts) == 1


@pytest.mark.parametrize(
    "corrupt",
    [("output_json", "{}"), ("latitude_deg", 1.0), ("input_offset", True)],
)
def test_ack_with_changed_typed_or_raw_readback_refuses(
    store: tuple[recording_sql.RecordingSQL, Boundary],
    corrupt: tuple[str, object],
) -> None:
    sql, boundary = store
    boundary.corrupt = corrupt
    with pytest.raises(ValueError, match="recording_sql_competing_fact"):
        sql.write_facts([output()])
    assert len(boundary.facts) == 1  # Retain ambiguous evidence; no cleanup.


def test_missing_or_denied_readback_cannot_publish_success(
    store: tuple[recording_sql.RecordingSQL, Boundary],
) -> None:
    sql, boundary = store
    boundary.drop_insert = True
    with pytest.raises(ValueError, match="recording_sql_content_readback"):
        sql.write_facts([output()])
    boundary.drop_insert = False
    sql.write_facts([output()])
    boundary.deny_reader = True
    with pytest.raises(PermissionError, match="reader_denied"):
        sql.write_facts([output(1, 8)])
    assert len(boundary.facts) == 1


@pytest.mark.parametrize(
    "case",
    [
        "unknown",
        "version",
        "bool",
        "nonfinite",
        "gps_hash",
        "identifier",
        "oversize",
        "age",
        "state",
    ],
)
def test_invalid_documents_refuse_without_transport_calls(
    store: tuple[recording_sql.RecordingSQL, Boundary],
    case: str,
) -> None:
    sql, boundary = store
    document = output()
    battery = object_value(inspection(document)["battery"])
    if case == "unknown":
        battery["status"] = "stale"
    elif case == "version":
        document["profile"] = "future-version"
    elif case == "bool":
        document["input_offset"] = True
    elif case == "nonfinite":
        object_value(battery["values"])["voltage_v"] = float("inf")
    elif case == "gps_hash":
        object_value(inspection(document)["gps"])["altitude_msl_m"] = 11.0
    elif case == "identifier":
        object_value(document["input_source"])["topic"] = "unsafe' topic"
    elif case == "oversize":
        object_value(document["fact"])["run_id"] = "x" * 65_536
    elif case == "age":
        battery["age_us"] = 2_000_001
    else:
        section = object_value(
            object_value(inspection(document)["states"])["vehicle_status"]
        )
        object_value(section["values"])["failsafe"] = True
    with pytest.raises(ValueError):
        sql.write_facts([document])
    assert boundary.calls == []


def test_batch_and_select_limits_and_pipeline_progress(
    store: tuple[recording_sql.RecordingSQL, Boundary],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sql, boundary = store
    for batch in ([], [output()] * 65):
        with pytest.raises(ValueError, match="recording_sql_batch_bound"):
            sql.write_facts(batch)
    for query in ("DROP TABLE facts", "SELECT 1; SELECT 2", "SELECT " + "x" * 32_768):
        with pytest.raises(ValueError, match="recording_sql_select"):
            sql.read(query)
    assert boundary.calls == []
    monkeypatch.setattr(time, "time_ns", lambda: 1_234_567_000_000)
    statuses = {
        "recorded_replay",
        "running",
        "paused",
        "completed",
        "stopped",
        "failed",
    }
    for status in statuses:
        sql.progress(status, 8, 2, 2)
    assert {row["status"] for row in boundary.progress} == statuses
    assert all(row["written_ms"] == 1_234_567 for row in boundary.progress)
    for values in (
        ("live", 0, 0, 2),
        ("running", True, 0, 2),
        ("running", 4097, 0, 2),
        ("completed", 8, 1, 2),
        ("running", 1, 2, 2),
    ):
        with pytest.raises(ValueError):
            sql.progress(*values)
    boundary.drop_insert = True
    monkeypatch.setattr(time, "time_ns", lambda: 2_000_000_000_000)
    with pytest.raises(ValueError, match="recording_sql_progress_readback"):
        sql.progress("running", 8, 2, 2)
    # Exercise both the admitted maximum batch and the hard result budgets.
    boundary.drop_insert = False
    sql.write_facts([output(i, i) for i in range(64)])
    assert len(boundary.facts) == 64
    for reply in (b'{"n":0}\n' * 4097, b"x" * (8 * 1024 * 1024 + 1)):
        boundary.reply = reply
        with pytest.raises(ValueError, match="recording_sql_read_bound"):
            sql.read("SELECT count() AS n FROM authored_recording.measurements")
