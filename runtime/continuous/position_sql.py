"""Explicit local SQL projection and expiring receipt health for live positions."""

from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.conversion_contract import json_line, json_object, object_value
from telemetry.local_io import read_bounded

DB = "position_stream"
VALUES = (
    "latitude_deg",
    "longitude_deg",
    "altitude_msl_m",
    "relative_altitude_m",
    "ground_speed_m_s",
    "down_speed_m_s",
)


def read_health_snapshot(path: Path) -> dict[str, object] | None:
    """A transient rename gap does not advance or renew SQL receipt health."""
    try:
        body = read_bounded(path, 8192)
    except FileNotFoundError:
        return None
    return json_object(body)


class PositionSQL:
    def __init__(self, admin: HttpConfig, reader: HttpConfig) -> None:
        self.admin, self.reader = admin, reader

    def execute(self, sql: str, body: bytes = b"") -> bytes:
        return _request(self.admin, sql, body, write=True)

    def read(self, sql: str) -> list[dict[str, object]]:
        return [
            json_object(line)
            for line in _request(
                self.reader, sql + " FORMAT JSONEachRow", b""
            ).splitlines()
        ]

    def initialize(self) -> None:
        self.execute(f"CREATE DATABASE {DB}")
        values = ",".join(name + " Float64" for name in VALUES)
        self.execute(f"""CREATE TABLE {DB}.facts (
          input_offset UInt64, event_id String, boot_ms UInt32,
          event_json String, fact_json String, {values}
        ) ENGINE=MergeTree ORDER BY (input_offset,event_id)""")
        self.execute(f"""CREATE TABLE {DB}.health (
          written_ms Int64, collector_written_ms Int64, position_received_ms Int64,
          selected_event String, connection String, position_status String
        ) ENGINE=MergeTree ORDER BY written_ms""")
        columns = "event_id,boot_ms,event_json," + ",".join(VALUES)
        self.execute(
            f"CREATE VIEW {DB}.positions AS SELECT DISTINCT {columns} FROM {DB}.facts"
        )
        # Both bridge and collector must be alive. Values come exclusively from SQL.
        converted = ",".join(
            f"if(st='fresh',toNullable(p.{name}),NULL) AS {name}" for name in VALUES
        )
        self.execute(f"""CREATE VIEW {DB}.live_state AS
          WITH toUnixTimestamp64Milli(now64(3)) AS n,
          (n>=h.written_ms AND n-h.written_ms<3000
           AND n>=h.collector_written_ms AND n-h.collector_written_ms<3000) AS alive,
          multiIf(NOT alive OR h.position_status='unknown','unknown',
            h.connection='lost','stale',
            p.event_id!=h.selected_event,'catching_up',
            n<h.position_received_ms,'unknown',
            h.position_status!='fresh' OR n-h.position_received_ms>=3000,'stale',
            'fresh') AS st
          SELECT st AS status, if(alive,h.connection,'unknown') AS connection,
          if(st='fresh',toNullable(p.event_id),NULL) AS event_id,
          if(st='fresh',toNullable(p.boot_ms),NULL) AS source_boot_ms,
          {converted}
          FROM (SELECT * FROM {DB}.health ORDER BY written_ms DESC LIMIT 1) h
          LEFT JOIN (SELECT * FROM {DB}.positions ORDER BY boot_ms DESC LIMIT 1) p
          ON 1=1""")

    def write_facts(self, facts: list[dict[str, object]]) -> None:
        if not 0 < len(facts) <= 16:
            raise ValueError("position_sql_batch_bound")
        rows = []
        for fact in facts:
            event = object_value(fact["event"])
            rows.append(
                {
                    "input_offset": fact["input_offset"],
                    "event_id": event["event_id"],
                    "boot_ms": object_value(event["native"])["time_boot_ms"],
                    "event_json": json_line(event).decode().strip(),
                    "fact_json": json_line(fact).decode().strip(),
                    **object_value(fact["payload"]),
                }
            )
        low = min(cast(int, row["input_offset"]) for row in rows)
        high = max(cast(int, row["input_offset"]) for row in rows)
        prior = self.read(
            f"SELECT DISTINCT fact_json FROM {DB}.facts "
            f"WHERE input_offset BETWEEN {low} AND {high}"
        )
        expected = {row["fact_json"] for row in rows}
        if any(row["fact_json"] not in expected for row in prior):
            raise ValueError("position_sql_competing_fact")
        self.execute(
            f"INSERT INTO {DB}.facts SETTINGS async_insert=0,"
            "insert_deduplicate=0 FORMAT JSONEachRow",
            b"".join(json_line(row) for row in rows),
        )
        actual = self.read(
            f"SELECT DISTINCT * FROM {DB}.facts "
            f"WHERE input_offset BETWEEN {low} AND {high}"
        )
        if {row["fact_json"]: row for row in actual} != {
            row["fact_json"]: row for row in rows
        }:
            raise ValueError("position_sql_content_readback")

    def health(self, row: dict[str, object]) -> None:
        self.execute(f"INSERT INTO {DB}.health FORMAT JSONEachRow", json_line(row))
