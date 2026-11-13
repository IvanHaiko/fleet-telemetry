"""Exact source, archive and SQL reconciliation for the finite live slice."""

import base64
import hashlib
import importlib
import re
import sys
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.position_capture import (
    Dialect,
    Packet,
)
from runtime.s3.archive_store import make_archive_store
from runtime.s3.boto_transport import make_client
from telemetry.archive_documents import digest
from telemetry.continuous_archive import (
    SegmentedArchive,
    segment_rows,
)
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.mavlink_position import (
    make_fact,
    make_input,
    unique_events,
)


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def save(path: Path, value: dict[str, object]) -> None:
    with path.open("xb") as handle:
        handle.write(json_line(value))


def reconcile(root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    plan = json_object((root / "plan.json").read_bytes())
    packet_body = (root / "source-packets.jsonl").read_bytes()
    source = [json_object(line) for line in packet_body.splitlines()]
    report = json_object((root / "producer-report.json").read_bytes())
    require(
        len(source) == 16 and report["flink_output_before_capture_complete"] is True,
        "live_source_count_or_streaming",
    )
    require(
        report["source_packets_sha256"] == hashlib.sha256(packet_body).hexdigest(),
        "source_packets_hash",
    )
    dialect = cast(Dialect, importlib.import_module("pymavlink.dialects.v20.common"))
    events = []
    for record in source:
        decoded = []
        for key, kind in (
            ("position_packet_b64", "GLOBAL_POSITION_INT"),
            ("fix_packet_b64", "GPS_RAW_INT"),
        ):
            frames = dialect.MAVLink(None).parse_buffer(
                base64.b64decode(string_value(record[key]), validate=True)
            )
            require(frames is not None and len(frames) == 1, "source_packet_decode")
            packet = cast(list[Packet], frames)[0]
            require(
                packet.get_type() == kind
                and packet.get_srcSystem() == plan["system_id"]
                and packet.get_srcComponent() == plan["component_id"],
                "source_packet_scope",
            )
            decoded.append(packet.to_dict())
        event = make_input(
            decoded[0],
            string_value(plan["source_boot_session"]),
            integer_value(plan["system_id"]),
            integer_value(plan["component_id"]),
        )
        require(
            event == record["event"] and integer_value(decoded[1]["fix_type"]) >= 3,
            "source_packet_content_or_fix",
        )
        events.append(event)
    require(len(unique_events(events)) == 16, "source_identity_count")
    inputs = list(segment_rows((root / "input-observations.jsonl").read_bytes()))
    outputs = list(segment_rows((root / "output-observations.jsonl").read_bytes()))
    sources = json_object((root / "sources.json").read_bytes())
    require(len(inputs) == 18, "input_delivery_count")
    expected: dict[int, dict[str, object]] = {}
    for offset, (row, event) in enumerate(
        zip(inputs, events + events[:2], strict=True)
    ):
        require(
            row["offset"] == offset
            and all(row[k] == v for k, v in object_value(sources["input"]).items()),
            "input_source_coordinates",
        )
        record_key = base64.b64decode(string_value(row["key_b64"]), validate=True)
        body = base64.b64decode(string_value(row["value_b64"]), validate=True)
        require(body == json_line(event), "source_kafka_bytes")
        expected[offset] = make_fact(
            body, record_key, string_value(plan["input_topic"]), 0, offset
        )
    seen: dict[int, dict[str, object]] = {}
    for offset, row in enumerate(outputs):
        require(
            row["offset"] == offset
            and all(row[k] == v for k, v in object_value(sources["output"]).items()),
            "output_source_coordinates",
        )
        fact = json_object(
            base64.b64decode(string_value(row["value_b64"]), validate=True)
        )
        original_offset = integer_value(fact["input_offset"])
        require(fact == expected.get(original_offset), "flink_fact_content")
        seen[original_offset] = fact
    require(set(seen) == set(range(18)), "flink_input_receipt_coverage")
    require(
        report["acknowledgements"]
        == [
            {"topic": plan["input_topic"], "partition": 0, "offset": i}
            for i in range(18)
        ],
        "producer_ack_coverage",
    )
    return inputs, [seen[i] for i in range(18)]


def archive(
    root: Path, inputs: list[dict[str, object]], credentials: dict[str, object]
) -> dict[str, object]:
    sys.path.insert(0, string_value(credentials["s3_sdk"]))
    plan = json_object((root / "plan.json").read_bytes())
    endpoint, region = "http://127.0.0.1:28333", "us-east-1"
    initializing = not (root / "archive-cursor.json").exists()
    if initializing:
        item = object_value(credentials["admin"])
        client = make_client(
            endpoint=endpoint,
            region=region,
            access_key=string_value(item["access"]),
            secret_key=string_value(item["secret"]),
        )
        try:
            client.create_bucket(Bucket=string_value(plan["bucket"]))
        finally:
            client.close()
    stores = []
    for name in ("writer", "reader"):
        item = object_value(credentials[name])
        stores.append(
            make_archive_store(
                endpoint,
                region,
                string_value(plan["bucket"]),
                string_value(plan["prefix"]),
                string_value(item["access"]),
                string_value(item["secret"]),
            )
        )
    writer, reader = stores
    try:
        packet_body = (root / "source-packets.jsonl").read_bytes()
        writer.create("source-packets.jsonl", packet_body)
        require(
            reader.read("source-packets.jsonl", digest(packet_body), len(packet_body))
            == packet_body,
            "raw_archive_readback",
        )
        source = object_value(
            json_object((root / "sources.json").read_bytes())["input"]
        )
        archive_plan: dict[str, object] = {
            "format_version": "continuous-archive-plan-v1",
            "partitions": 1,
            "source": {k: source[k] for k in ("cluster_id", "topic_id", "topic")},
            "source_packets_sha256": digest(packet_body),
            "source_packets_bytes": len(packet_body),
            "source_export_sha256": digest(
                (root / "source-manifest.json").read_bytes()
            ),
        }
        stream = SegmentedArchive(
            writer,
            reader,
            root / "archive-cursor.json",
            archive_plan,
            initialize=initializing,
        )
        if initializing:
            require(stream.publish(0, inputs) == 18, "archive_publish_count")
        require(stream.next_offset(0) == 18, "archive_cursor_coverage")
        receipt = stream.verify_receipt(0, 0, end=18)
        require(
            receipt is not None and list(segment_rows(receipt[1])) == inputs,
            "archive_full_readback",
        )
        if (root / "archive-plan.json").exists():
            require(
                json_object((root / "archive-plan.json").read_bytes()) == archive_plan,
                "archive_retained_plan_conflict",
            )
        else:
            save(root / "archive-plan.json", archive_plan)
        return {
            "observations": 18,
            "source_packets": 16,
            "objects": len(reader.inventory()),
            "receipt": cast(tuple[dict[str, object], bytes], receipt)[0],
        }
    finally:
        writer.close()
        reader.close()


def sql_check(
    root: Path, facts: list[dict[str, object]], credentials: dict[str, object]
) -> dict[str, object]:
    admin = HttpConfig(
        28133, "default", "position_admin", string_value(credentials["ch_admin"]), 15
    )

    def sql(statement: str, body: bytes = b"") -> bytes:
        return _request(admin, statement, body, write=True)

    sql("CREATE DATABASE IF NOT EXISTS live_positions")
    sql("""CREATE TABLE IF NOT EXISTS live_positions.facts (
      batch String, input_topic String, input_offset UInt64, event_id String,
      source_boot_session String, source_time_ms UInt32,
      latitude_deg Float64, longitude_deg Float64, altitude_msl_m Float64,
      relative_altitude_m Float64, ground_speed_m_s Float64, down_speed_m_s Float64,
      event_json String, fact_json String
    ) ENGINE=MergeTree ORDER BY (input_topic,input_offset,batch)""")
    columns = [
        "input_topic",
        "input_offset",
        "event_id",
        "source_boot_session",
        "source_time_ms",
        "latitude_deg",
        "longitude_deg",
        "altitude_msl_m",
        "relative_altitude_m",
        "ground_speed_m_s",
        "down_speed_m_s",
        "event_json",
        "fact_json",
    ]
    expected = []
    for fact in facts:
        event = object_value(fact["event"])
        expected.append(
            {
                "input_topic": fact["input_topic"],
                "input_offset": fact["input_offset"],
                "event_id": event["event_id"],
                "source_boot_session": event["source_boot_session"],
                "source_time_ms": object_value(event["native"])["time_boot_ms"],
                **object_value(fact["payload"]),
                "event_json": json_line(event).decode().strip(),
                "fact_json": json_line(fact).decode().strip(),
            }
        )
    sql(
        "CREATE VIEW IF NOT EXISTS live_positions.positions "
        "AS SELECT DISTINCT event_id, "
        "source_boot_session, source_time_ms, latitude_deg, longitude_deg, "
        "altitude_msl_m, relative_altitude_m, ground_speed_m_s, down_speed_m_s, "
        "event_json FROM live_positions.facts"
    )
    password = string_value(credentials["ch_reader"])
    require(re.fullmatch("[0-9a-f]{48}", password), "new_reader_password_shape")
    sql(
        f"CREATE USER IF NOT EXISTS position_reader "
        f"IDENTIFIED WITH sha256_password BY '{password}'"
    )
    sql("GRANT SELECT ON live_positions.facts TO position_reader")
    sql("GRANT SELECT ON live_positions.positions TO position_reader")
    reader = HttpConfig(28133, "live_positions", "position_reader", password, 15)

    def read(statement: str) -> list[dict[str, object]]:
        return [
            json_object(line)
            for line in _request(
                reader, statement + " FORMAT JSONEachRow", b""
            ).splitlines()
        ]

    snapshots = []
    require(
        read(
            "SELECT batch FROM live_positions.facts GROUP BY batch "
            "HAVING batch NOT IN ('initial','repeat')"
        )
        == [],
        "sql_unknown_batch",
    )
    for batch in ("initial", "repeat"):
        body = b"".join(json_line({"batch": batch, **row}) for row in expected)
        batch_count = read(
            f"SELECT count() AS n FROM live_positions.facts WHERE batch='{batch}'"
        )[0]["n"]
        require(batch_count in (0, 18), "sql_partial_batch")
        if batch_count == 0:
            sql(
                "INSERT INTO live_positions.facts SETTINGS async_insert=0,"
                "insert_deduplicate=0 FORMAT JSONEachRow",
                body,
            )
        actual = read(
            "SELECT DISTINCT "
            + ",".join(columns)
            + " FROM live_positions.facts ORDER BY input_offset"
        )
        require(actual == expected, "sql_full_content_readback")
        require(
            read(
                "SELECT event_id FROM live_positions.facts GROUP BY event_id "
                "HAVING uniqExact(event_json)>1"
            )
            == [],
            "sql_identity_content_conflict",
        )
        counts = read(
            "SELECT count() AS physical_rows, uniqExact(input_offset) "
            "AS source_deliveries, uniqExact(event_id) "
            "AS unique_measurements FROM live_positions.facts"
            + (" WHERE batch='initial'" if batch == "initial" else "")
        )[0]
        require(
            counts
            == {
                "physical_rows": 18 if batch == "initial" else 36,
                "source_deliveries": 18,
                "unique_measurements": 16,
            },
            "sql_duplicate_counts",
        )
        require(
            read("SELECT count() AS measurements FROM live_positions.positions")
            == [{"measurements": 16}],
            "sql_view_count",
        )
        snapshots.append(counts)
    latest = read(
        "SELECT * FROM live_positions.positions ORDER BY source_time_ms DESC LIMIT 1"
    )[0]
    if (root / "latest-position.json").exists():
        require(
            json_object((root / "latest-position.json").read_bytes()) == latest,
            "sql_latest_changed",
        )
    else:
        save(root / "latest-position.json", latest)
    return {
        "initial": snapshots[0],
        "repeat": snapshots[1],
        "latest": latest,
        "full_content_readback": True,
    }
