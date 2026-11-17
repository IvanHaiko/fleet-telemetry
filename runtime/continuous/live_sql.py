"""SQL projection, collector health and current state of a live SITL session.

Facts use the shared RecordingSQL write path: compare, insert and complete
reader readback, with physical repeats allowed and competing content refused.
Collector rows copy the gateway's own status time, so a stopped gateway or a
stopped serving worker ages that time and never renews health (ADR-0054).
"""

import re
import time
from typing import cast

from runtime.continuous.recording_sql import (
    _MAX_OUTPUT_BYTES,
    RecordingSQL,
    _integer,
    _json,
    _number,
    _text,
    _typed_equal,
)
from telemetry.conversion_contract import json_line, object_value
from telemetry.live_runtime import Document, read_output
from telemetry.recording_output import MAX_EVENTS

_POSITION = (
    "latitude_deg",
    "longitude_deg",
    "altitude_msl_m",
    "relative_altitude_m",
    "ground_speed_m_s",
    "down_speed_m_s",
)
_BATTERY = ("voltage_v", "current_a", "remaining_fraction")
_STATE = {
    "armed": "Nullable(UInt8)",
    "base_mode_code": "Nullable(UInt8)",
    "custom_mode_code": "Nullable(UInt32)",
    "system_status_code": "Nullable(UInt8)",
}
_SCOPE = (
    "source_cluster_id",
    "source_topic_id",
    "source_topic",
    "source_partition",
    "session_sha256",
    "run_id",
)
_COLUMNS = {
    "event_id": "String",
    "input_offset": "UInt64",
    "native_time_boot_ms": "UInt64",
    "native_seconds": "Float64",
    "received_unix_ms": "UInt64",
    "capture_epoch": "String",
    "capture_sequence": "UInt64",
    **{name: "Float64" for name in _POSITION},
    **{
        f"{group}_{part}": kind
        for group in ("battery", "state")
        for part, kind in (
            ("status", "String"),
            ("receipt_age_ms", "Nullable(UInt64)"),
            ("observation_id", "Nullable(String)"),
        )
    },
    **{name: "Nullable(Float64)" for name in _BATTERY},
    **_STATE,
    "source_cluster_id": "String",
    "source_topic_id": "String",
    "source_topic": "String",
    "source_partition": "UInt8",
    "session_sha256": "String",
    "run_id": "String",
    "output_json": "String",
    "fact_json": "String",
}
_IDENTITY = re.compile(r"sha256:[0-9a-f]{64}")
_GATEWAY_STATUSES = {"running", "completed", "stopped", "failed"}
# Receipt and health limit of the live view, as in ADR-0047.
LIVE_LIMIT_MS = 3000


def _identity(value: object) -> str:
    if not isinstance(value, str) or _IDENTITY.fullmatch(value) is None:
        raise ValueError("live_sql_identity")
    return value


def _project(output: Document) -> Document:
    raw = _json(output)
    if len(raw.encode("utf-8")) > _MAX_OUTPUT_BYTES:
        raise ValueError("live_sql_output_bound")
    checked = read_output(json_line(output)[:-1])
    source = object_value(checked["input_source"])
    fact = object_value(checked["fact"])
    capture = object_value(fact["capture"])
    position = object_value(fact["position"])
    boot = _integer(fact["native_time_boot_ms"], 2**32)
    row: Document = {
        "event_id": _identity(fact["measurement_id"]),
        "input_offset": _integer(checked["input_offset"], MAX_EVENTS),
        "native_time_boot_ms": boot,
        "native_seconds": boot / 1000,
        "received_unix_ms": _integer(fact["received_unix_ms"], 2**63),
        "capture_epoch": _text(capture["epoch"], r"[0-9a-f]{32}"),
        "capture_sequence": _integer(capture["sequence"], 2**63),
        **{
            name: None if position[name] is None else _number(position[name])
            for name in _POSITION
        },
        "source_cluster_id": _text(source["cluster_id"], r"[A-Za-z0-9_-]{1,128}"),
        "source_topic_id": _text(source["topic_id"], r"[A-Za-z0-9+/_-]{1,128}"),
        "source_topic": _text(source["topic"], r"[A-Za-z0-9._-]{1,249}"),
        "source_partition": _integer(source["partition"], 1),
        "session_sha256": _text(checked["session_sha256"], r"[0-9a-f]{64}"),
        "run_id": _text(fact["run_id"], r"[A-Za-z0-9._-]{1,128}"),
        "output_json": raw,
        "fact_json": _json(fact),
    }
    for group in ("battery", "state"):
        link = object_value(fact[group])
        age = link["receipt_age_ms"]
        observation = link["observation_id"]
        row[f"{group}_status"] = link["status"]
        row[f"{group}_receipt_age_ms"] = None if age is None else _integer(age, 2**63)
        row[f"{group}_observation_id"] = (
            None if observation is None else _identity(observation)
        )
    battery = link_values(fact, "battery")
    for name in _BATTERY:
        value = battery.get(name)
        row[name] = None if value is None else _number(value)
    state = link_values(fact, "state")
    for name in _STATE:
        value = state.get(name)
        row[name] = None if value is None else int(cast(int | bool, value))
    return row


def link_values(fact: Document, group: str) -> Document:
    values = object_value(fact[group])["values"]
    return {} if values is None else object_value(values)


class LiveSQL(RecordingSQL):
    """Live facts, pipeline progress and collector health in a fresh scope."""

    columns = _COLUMNS
    scope = _SCOPE
    project = staticmethod(_project)
    identity = staticmethod(_identity)

    def initialize(self) -> None:
        """Refuse existing scopes; never replace retained evidence."""
        db = self.database
        self._execute(f"CREATE DATABASE {db}")
        columns = ", ".join(f"{name} {kind}" for name, kind in self.columns.items())
        self._execute(
            f"CREATE TABLE {db}.facts ({columns}) "
            "ENGINE=MergeTree ORDER BY (input_offset,event_id)"
        )
        self._execute(
            f"CREATE TABLE {db}.progress (written_ms Int64, status String, "
            "input_next UInt64, output_count UInt64, published UInt64) "
            "ENGINE=MergeTree ORDER BY written_ms"
        )
        self._execute(
            f"CREATE TABLE {db}.collector (written_ms Int64, gateway_epoch String, "
            "gateway_status String, gateway_written_ms Int64, "
            "last_receipt_ms Nullable(Int64), last_heartbeat_ms Nullable(Int64), "
            "published UInt64) ENGINE=MergeTree ORDER BY written_ms"
        )
        typed = [name for name in self.columns if not name.endswith("_json")]
        self._execute(
            f"CREATE VIEW {db}.measurements AS "
            f"SELECT DISTINCT {', '.join(self.columns)} FROM {db}.facts"
        )
        self._execute(
            f"CREATE VIEW {db}.points AS SELECT DISTINCT {', '.join(typed)} "
            f"FROM {db}.facts"
        )
        # Health comes from the gateway's own status time and serving's
        # progress time; values show only while the source is observed. The
        # latest fact is one scan, so the view stays within reader budgets and
        # still returns its health row before the first fact.
        limit = LIVE_LIMIT_MS
        shown = (*_POSITION, *_BATTERY, *_STATE)
        latest = ", ".join(
            ("received_unix_ms", *shown, "battery_status", "state_status")
        )
        fields = ", ".join(
            f"if(connection = 'observed' AND position_age_ms <= {limit}, "
            f"tupleElement(last, {index + 2}), NULL) AS {name}"
            for index, name in enumerate(shown)
        )
        self._execute(
            f"CREATE VIEW {db}.live_state AS "
            "WITH toUnixTimestamp64Milli(now64(3)) AS now_ms, "
            f"(SELECT max(gateway_written_ms) FROM {db}.collector) AS gateway_ms, "
            "(SELECT argMax(gateway_status, gateway_written_ms) "
            f"FROM {db}.collector) AS gateway_status, "
            "(SELECT argMax(last_heartbeat_ms, gateway_written_ms) "
            f"FROM {db}.collector) AS heartbeat_ms, "
            f"(SELECT max(written_ms) FROM {db}.progress) AS serving_ms, "
            f"(SELECT argMax(tuple({latest}), input_offset) FROM {db}.facts) AS last, "
            "now_ms - toInt64(tupleElement(last, 1)) AS position_age_ms, "
            f"multiIf(gateway_ms = 0 OR now_ms - gateway_ms > {limit} "
            f"OR serving_ms = 0 OR now_ms - serving_ms > {limit} "
            "OR gateway_status != 'running', 'unknown', "
            f"heartbeat_ms IS NULL OR now_ms - heartbeat_ms > {limit}, 'stale', "
            "'observed') AS connection "
            "SELECT connection, now_ms - gateway_ms AS collector_age_ms, "
            "now_ms - serving_ms AS serving_age_ms, "
            "now_ms - heartbeat_ms AS source_receipt_age_ms, "
            f"if(count_facts = 0, NULL, position_age_ms) AS position_receipt_age_ms, "
            f"{fields}, "
            f"if(count_facts = 0, NULL, tupleElement(last, {len(shown) + 2})) "
            "AS battery_status, "
            f"if(count_facts = 0, NULL, tupleElement(last, {len(shown) + 3})) "
            "AS state_status "
            f"FROM (SELECT count() AS count_facts FROM {db}.facts)"
        )

    def progress(
        self, status: str, input_next: int, output_count: int, published: int
    ) -> None:
        """Pipeline observation time, never source time or connectivity."""
        if status not in {"running", "completed", "stopped", "failed"}:
            raise ValueError("live_sql_progress_status")
        for value in (input_next, output_count, published):
            _integer(value, MAX_EVENTS + 1)
        if output_count > input_next:
            raise ValueError("live_sql_progress_count")
        self._insert_one(
            "progress",
            {
                "written_ms": time.time_ns() // 1_000_000,
                "status": status,
                "input_next": input_next,
                "output_count": output_count,
                "published": published,
            },
            {"status": "String"},
        )

    def collector(self, status: Document) -> None:
        """Copy one gateway status snapshot; its own time decides its age."""
        state = status.get("status")
        if not isinstance(state, str) or state not in _GATEWAY_STATUSES:
            raise ValueError("live_sql_collector_status")

        def optional(name: str) -> int | None:
            value = status.get(name)
            return None if value is None else _integer(value, 2**63)

        self._insert_one(
            "collector",
            {
                "written_ms": time.time_ns() // 1_000_000,
                "gateway_epoch": _text(status.get("epoch"), r"[0-9a-f]{32}"),
                "gateway_status": state,
                "gateway_written_ms": _integer(status.get("written_ms"), 2**63),
                "last_receipt_ms": optional("last_receipt_ms"),
                "last_heartbeat_ms": optional("last_heartbeat_ms"),
                "published": _integer(status.get("published"), MAX_EVENTS + 1),
            },
            {"gateway_epoch": "String", "gateway_status": "String"},
        )

    def _insert_one(self, table: str, row: Document, strings: dict[str, str]) -> None:
        self._execute(
            f"INSERT INTO {self.database}.{table} SETTINGS async_insert=0 "
            "FORMAT JSONEachRow",
            json_line(row),
        )
        actual = self.read(
            f"SELECT DISTINCT * FROM {self.database}.{table} "
            f"WHERE written_ms={row['written_ms']}"
        )
        columns = {
            name: strings.get(name, "Nullable(Int64)" if row[name] is None else "Int64")
            for name in row
        }
        if not any(_typed_equal(value, row, columns) for value in actual):
            raise ValueError("live_sql_readback")


# Fleet sessions (ADR-0060): the same facts with the vehicle that produced
# them; position fields a replay could not derive are null.
_FLEET_COLUMNS = {
    **{
        name: "Nullable(Float64)" if name in _POSITION[3:] else kind
        for name, kind in _COLUMNS.items()
    },
    "vehicle": "String",
    "vehicle_label": "String",
    "source_kind": "String",
    "system_id": "UInt8",
}
_REPLAY_STATUSES = {"starting", "running", "paused", "ended", "stopped", "failed"}


def _project_fleet(output: Document) -> Document:
    row = _project(output)
    source = object_value(object_value(object_value(output)["fact"])["source"])
    kind = _text(source["kind"], r"px4-sitl|ulog-replay")
    row["vehicle"] = _text(source["vehicle"], r"[A-Za-z0-9._-]{1,128}")
    row["vehicle_label"] = (
        _text(source["label"], r"ULog [0-9a-f]{8}")
        if kind == "ulog-replay"
        else row["vehicle"]
    )
    row["source_kind"] = kind
    row["system_id"] = _integer(source["system"], 256)
    return row


class FleetSQL(LiveSQL):
    """Facts, collector rows and current state per vehicle."""

    columns = _FLEET_COLUMNS
    project = staticmethod(_project_fleet)

    def initialize(self) -> None:
        super().initialize()
        db = self.database
        self._execute(
            f"CREATE TABLE {db}.vehicles (written_ms Int64, gateway_written_ms "
            "Int64, vehicle String, label String, kind String, system_id UInt8, "
            "last_receipt_ms Nullable(Int64), last_heartbeat_ms Nullable(Int64), "
            "published UInt64, refusal Nullable(String), "
            "replay_status Nullable(String)) ENGINE=MergeTree "
            "ORDER BY (vehicle, written_ms)"
        )
        limit = LIVE_LIMIT_MS
        shown = (*_POSITION, *_BATTERY, *_STATE)
        latest = ", ".join(
            ("received_unix_ms", *shown, "battery_status", "state_status")
        )
        fields = ", ".join(
            f"if(connection = 'observed' AND position_age_ms <= {limit}, "
            f"tupleElement(f.last, {index + 2}), NULL) AS {name}"
            for index, name in enumerate(shown)
        )
        # One row per vehicle the gateway has declared. Health needs a
        # current gateway snapshot and current serving progress; a replay
        # whose player says it ended shows `ended` once it falls silent.
        self._execute(
            f"CREATE VIEW {db}.fleet_state AS "
            "WITH toUnixTimestamp64Milli(now64(3)) AS now_ms, "
            f"(SELECT max(written_ms) FROM {db}.progress) AS serving_ms "
            "SELECT v.vehicle AS vehicle, v.label AS label, v.kind AS kind, "
            "v.system_id AS system_id, v.replay_status AS replay_status, "
            "v.refusal AS refusal, "
            "now_ms - v.gateway_ms AS collector_age_ms, "
            "now_ms - v.heartbeat_ms AS source_receipt_age_ms, "
            "if(f.count_facts = 0, NULL, now_ms - toInt64(tupleElement(f.last, 1))) "
            "AS position_receipt_age_ms, "
            "now_ms - toInt64(tupleElement(f.last, 1)) AS position_age_ms, "
            f"multiIf(now_ms - v.gateway_ms > {limit} OR serving_ms = 0 "
            f"OR now_ms - serving_ms > {limit}, 'unknown', "
            f"v.heartbeat_ms IS NULL OR now_ms - v.heartbeat_ms > {limit}, "
            "if(v.replay_status = 'ended', 'ended', 'stale'), 'observed') "
            "AS connection, f.count_facts AS facts, "
            f"{fields}, "
            f"if(f.count_facts = 0, NULL, tupleElement(f.last, {len(shown) + 2})) "
            "AS battery_status, "
            f"if(f.count_facts = 0, NULL, tupleElement(f.last, {len(shown) + 3})) "
            "AS state_status "
            "FROM (SELECT vehicle, argMax(label, written_ms) AS label, "
            "argMax(kind, written_ms) AS kind, "
            "argMax(system_id, written_ms) AS system_id, "
            "argMax(replay_status, written_ms) AS replay_status, "
            "argMax(refusal, written_ms) AS refusal, "
            "max(gateway_written_ms) AS gateway_ms, "
            "argMax(last_heartbeat_ms, written_ms) AS heartbeat_ms "
            f"FROM {db}.vehicles GROUP BY vehicle) AS v "
            "LEFT JOIN (SELECT vehicle, count() AS count_facts, "
            f"argMax(tuple({latest}), input_offset) AS last "
            f"FROM {db}.facts GROUP BY vehicle) AS f ON f.vehicle = v.vehicle"
        )

    def vehicles(
        self,
        status: Document,
        players: dict[str, str],
    ) -> None:
        """One row per vehicle from one gateway snapshot and player states."""
        listed = object_value(status.get("vehicles", {}))
        written = time.time_ns() // 1_000_000
        gateway_ms = _integer(status.get("written_ms"), 2**63)
        rows: list[Document] = []

        def optional(row: Document, name: str) -> int | None:
            value = row.get(name)
            return None if value is None else _integer(value, 2**63)

        for vehicle, value in sorted(listed.items()):
            row = object_value(value)
            refusal = row.get("refusal")
            replay = players.get(vehicle)
            if replay is not None and replay not in _REPLAY_STATUSES:
                raise ValueError("fleet_sql_replay_status")
            rows.append(
                {
                    "written_ms": written,
                    "gateway_written_ms": gateway_ms,
                    "vehicle": _text(vehicle, r"[A-Za-z0-9._-]{1,128}"),
                    "label": _text(row.get("label"), r"[A-Za-z0-9 ._-]{1,64}"),
                    "kind": _text(row.get("kind"), r"px4-sitl|ulog-replay"),
                    "system_id": _integer(row.get("system"), 256),
                    "last_receipt_ms": optional(row, "last_receipt_ms"),
                    "last_heartbeat_ms": optional(row, "last_heartbeat_ms"),
                    "published": _integer(row.get("published"), MAX_EVENTS + 1),
                    "refusal": None
                    if refusal is None
                    else _text(refusal, r"[a-z0-9_]{1,64}"),
                    "replay_status": replay,
                }
            )
        if rows:
            self._execute(
                f"INSERT INTO {self.database}.vehicles SETTINGS async_insert=0 "
                "FORMAT JSONEachRow",
                b"".join(json_line(row) for row in rows),
            )
