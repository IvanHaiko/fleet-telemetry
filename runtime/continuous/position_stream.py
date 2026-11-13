"""Guarded continuous collector and independent archive/SQL position worker."""

import argparse
import base64
import fcntl
import signal
import time
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig
from runtime.continuous.position_capture import (
    Dialect,
    Packet,
    Parser,
    collector,
    immutable,
    require,
    validate_packet,
)
from runtime.continuous.position_sql import PositionSQL, read_health_snapshot
from runtime.kafka_archive.native import NativeSliceClient
from runtime.s3.archive_store import make_archive_store
from telemetry.archive_documents import digest
from telemetry.continuous_archive import SegmentedArchive, durable_cursor, segment_rows
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.mavlink_position import make_fact

__all__ = [
    "Dialect",
    "Packet",
    "Parser",
    "collector",
    "immutable",
    "require",
    "validate_packet",
]


def store(plan: dict[str, object], root: Path) -> None:
    sources = json_object((root / "sources.json").read_bytes())
    keys = json_object((root / "credentials.json").read_bytes())
    writer = make_archive_store(
        "http://127.0.0.1:8333",
        "us-east-1",
        string_value(plan["bucket"]),
        string_value(plan["prefix"]),
        string_value(object_value(keys["writer"])["access"]),
        string_value(object_value(keys["writer"])["secret"]),
    )
    reader = make_archive_store(
        "http://127.0.0.1:8333",
        "us-east-1",
        string_value(plan["bucket"]),
        string_value(plan["prefix"]),
        string_value(object_value(keys["reader"])["access"]),
        string_value(object_value(keys["reader"])["secret"]),
    )
    sql = PositionSQL(
        HttpConfig(
            8123, "default", "position_writer", string_value(keys["ch_writer"]), 15
        ),
        HttpConfig(
            8123, "default", "position_reader", string_value(keys["ch_reader"]), 15
        ),
    )
    source = object_value(sources["input"])
    archive_plan: dict[str, object] = {
        "format_version": "continuous-archive-plan-v1",
        "partitions": 1,
        "source": {k: source[k] for k in ("cluster_id", "topic_id", "topic")},
        "packet_key_recipe": "packets/<input-offset-20-digits>.json",
        "source_boot_session": plan["source_boot_session"],
    }
    stream = SegmentedArchive(
        writer,
        reader,
        root / "archive-cursor.json",
        archive_plan,
        initialize=not (root / "archive-cursor.json").exists(),
    )
    clients = {}
    for which in ("input", "output"):
        scoped = object_value(sources[which])
        client = NativeSliceClient(
            "127.0.0.1:19092", "m4-reader-position-stream-" + which, scoped
        )
        clients[which] = client
    progress = root / "serving-cursor.json"
    output_next = (
        integer_value(json_object(progress.read_bytes())["next"])
        if progress.exists()
        else 0
    )
    expected: dict[int, dict[str, object]] = {}
    events: dict[str, dict[str, object]] = {}

    def accept_input(row: dict[str, object], *, archived: bool) -> None:
        offset = integer_value(row["offset"])
        value = base64.b64decode(string_value(row["value_b64"]), validate=True)
        key = base64.b64decode(string_value(row["key_b64"]), validate=True)
        fact = make_fact(
            value,
            key,
            string_value(source["topic"]),
            0,
            offset,
            offset_limit=integer_value(plan["deliveries"]),
        )
        event = object_value(fact["event"])
        identity = string_value(event["event_id"])
        require(
            event["source_boot_session"] == plan["source_boot_session"],
            "position_archive_session",
        )
        require(
            identity not in events or events[identity] == event,
            "position_competing_event",
        )
        packet_key = f"packets/{offset:020d}.json"
        if archived:
            raw = reader.lookup(packet_key)
            require(raw is not None, "position_archived_packet_missing")
            packet_body = cast(bytes, raw)
        else:
            ack_path = root / "acks" / f"{offset:020d}.json"
            wait_until = time.monotonic() + 2
            while not ack_path.exists() and time.monotonic() < wait_until:
                time.sleep(0.01)
            ack = json_object(ack_path.read_bytes())
            packet_body = (
                root / "packets" / f"{integer_value(ack['packet_index']):020d}.json"
            ).read_bytes()
            writer.create(packet_key, packet_body)
            require(
                reader.read(packet_key, digest(packet_body), len(packet_body))
                == packet_body,
                "position_packet_readback",
            )
        require(
            validate_packet(packet_body, plan) == event and value == json_line(event),
            "position_source_bytes",
        )
        expected[offset], events[identity] = fact, event

    start = 0
    while start < stream.next_offset(0):
        receipt = stream.verify_receipt(0, start)
        require(receipt is not None, "position_archive_receipt_missing")
        document, body = cast(tuple[dict[str, object], bytes], receipt)
        for row in segment_rows(body):
            accept_input(row, archived=True)
        start = integer_value(document["next"])
    input_next = stream.next_offset(0)
    clients["input"].assign(input_next)
    clients["output"].assign(output_next)
    last_health = 0.0
    output_pending: list[dict[str, object]] = []
    stopping = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    try:
        while not stopping:
            for which in ("input", "output"):
                client = clients[which]
                info = client.inspect(5)
                cursor = input_next if which == "input" else output_next
                require(
                    info.low
                    <= cursor
                    <= info.high
                    <= integer_value(plan["deliveries"])
                    * (1 if which == "input" else 2),
                    "position_retention_or_budget",
                )
                rows = output_pending if which == "output" else []
                if not rows:
                    # Reset a queued EOF from the previously observed high watermark.
                    # Only read the interval proven present by the current inspection.
                    if info.high > cursor:
                        client.assign(cursor)
                    for offset in range(cursor, min(cursor + 16, info.high)):
                        supplied = client.poll(5)
                        require(
                            supplied is not None and supplied["offset"] == offset,
                            "position_offset_gap",
                        )
                        rows.append(dict(cast(dict[str, object], supplied)))
                if not rows:
                    continue
                if which == "input":
                    for row in rows:
                        accept_input(row, archived=False)
                    require(
                        stream.publish(0, rows) == len(rows), "position_archive_count"
                    )
                    input_next += len(rows)
                else:
                    facts = []
                    for row in rows:
                        fact = json_object(
                            base64.b64decode(
                                string_value(row["value_b64"]), validate=True
                            )
                        )
                        input_offset = integer_value(fact["input_offset"])
                        if input_offset >= input_next:
                            break
                        require(
                            expected.get(input_offset) == fact,
                            "position_flink_content_or_unarchived_input",
                        )
                        facts.append(fact)
                    if len(facts) != len(rows):
                        output_pending = rows
                        continue
                    output_pending = []
                    sql.write_facts(facts)
                    if (root / "pause-after-insert").exists():
                        durable_cursor(
                            root / "inserted-marker.json",
                            {"next": output_next + len(rows)},
                        )
                        time.sleep(20)
                    output_next += len(rows)
                    durable_cursor(progress, {"next": output_next})
            now = time.monotonic()
            if now - last_health >= 0.5:
                path = root / "collector-status.json"
                status = read_health_snapshot(path)
                if status is not None:
                    sql.health(
                        {
                            key: status[key]
                            for key in (
                                "collector_written_ms",
                                "position_received_ms",
                                "selected_event",
                                "connection",
                                "position_status",
                            )
                        }
                        | {"written_ms": time.time_ns() // 1_000_000}
                    )
                durable_cursor(
                    root / "store-status.json",
                    {
                        "input_next": input_next,
                        "output_next": output_next,
                        "unique_measurements": len(events),
                        "written_ms": time.time_ns() // 1_000_000,
                    },
                )
                last_health = now
            if (root / "collector-finished.json").exists():
                completion = json_object(
                    (root / "collector-finished.json").read_bytes()
                )
                require(completion["status"] == "complete", "position_collector_failed")
                total = integer_value(completion["deliveries"])
                seen = sql.read(
                    "SELECT DISTINCT input_offset FROM position_stream.facts "
                    "ORDER BY input_offset"
                )
                if input_next == total and {
                    integer_value(row["input_offset"]) for row in seen
                } == set(range(total)):
                    immutable(
                        root / "stream-finished.json",
                        json_line(
                            {
                                "input_deliveries": total,
                                "output_receipts": output_next,
                                "unique_measurements": len(events),
                            }
                        ),
                    )
                    break
            time.sleep(0.1)
    finally:
        for client in clients.values():
            client.close()
        writer.close()
        reader.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("collector", "store"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json_object(args.config.read_bytes())
    evidence = Path(string_value(config["evidence"]))
    with (evidence / (args.role + ".lock")).open("a+b") as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (collector if args.role == "collector" else store)(config, evidence)
