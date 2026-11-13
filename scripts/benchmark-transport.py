# ruff: noqa: E402
"""Bounded synthetic Kafka/ClickHouse replay baseline; no service lifecycle."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from fleet_telemetry import (
    ClockAnchor,
    DeliveryMetadata,
    Rejection,
    SourceManifest,
    normalize_battery,
)
from runtime.clickhouse.transport import HttpConfig, _request
from scripts.m3_transport import Transport
from scripts.m3_transport_types import Error, Message
from telemetry.archive_documents import canonical
from telemetry.conversion_contract import SEMANTIC_FIELDS
from telemetry.serving_projection import _decimal, _semantic_json
from telemetry_reader import read_battery_event

type Row = dict[str, object]
UNIQUE = 128
BATCH = 128


def require(condition: object, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def save(path: Path, value: object) -> None:
    with path.open("xb") as stream:
        stream.write(canonical(value))


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def source(folder: Path) -> tuple[list[Row], SourceManifest]:
    records: list[Row] = []
    for i in range(UNIQUE):
        row: Row = {
            "source_record_index": i,
            "timestamp_us": i * 1000,
            "voltage_mv": 15000 + i,
        }
        if i % 4 in (0, 2):
            row["current_ma"] = 1000
        if i % 4 in (0, 1):
            row["remaining_pct"] = 50
        records.append(row)
    raw = canonical(
        {"generator_version": "m6-replay-load-v1", "seed": 0, "records": records}
    )
    (folder / "native.json").write_bytes(raw)
    manifest = SourceManifest(
        "m6-load-manifest-v1",
        "sha256:" + sha256(raw).hexdigest(),
        "synthetic-load-vehicle-001",
        "battery_status:0",
        0,
        127000,
        ClockAnchor(0, "2026-01-01T12:00:00.000000Z"),
        "native.json",
        now(),
        "Original project-authored synthetic fixture.",
        "Synthetic vehicle and values; no real coordinates.",
    )
    save(folder / "manifest.json", asdict(manifest))
    return records, manifest


def normalize(row: Row, manifest: SourceManifest, run_id: str) -> bytes:
    event = normalize_battery(
        row, manifest, manifest.clock_anchor, DeliveryMetadata(now(), run_id)
    )
    require(not isinstance(event, Rejection), "normalization_rejected")
    return canonical(event)


def projection(wire: bytes, run_id: str) -> Row:
    event = read_battery_event(wire)
    payload = event["payload"]
    semantic = {key: cast(Row, event)[key] for key in SEMANTIC_FIELDS}
    semantic["quality_flags"] = sorted(event["quality_flags"])
    return {
        "dataset_run_id": run_id,
        "pipeline_version": "transport-load-v1",
        "event_id": event["event_id"],
        "vehicle_id": event["vehicle_id"],
        "source_timestamp": event["source_timestamp"],
        "voltage_v": _decimal(payload["voltage_v"], "voltage_v"),
        "current_a": _decimal(payload["current_a"], "current_a"),
        "remaining_fraction": _decimal(
            payload["remaining_fraction"], "remaining_fraction"
        ),
        "disposition": "eligible",
        "quality_flags": event["quality_flags"],
        "semantic_json": _semantic_json(semantic),
    }


def sql(
    config: HttpConfig, statement: str, body: bytes = b"", *, write: bool = False
) -> bytes:
    return _request(
        config, statement, body, write=write, parameters={"database": config.database}
    )


def visible(reader: HttpConfig, run_id: str, expected: list[Row]) -> None:
    where = f" WHERE dataset_run_id='{run_id}' AND pipeline_version='transport-load-v1'"
    sql(reader, "SELECT throwIf(count()>0,'identity_conflict') FROM conflicts" + where)
    expressions = [
        f"toDecimalString({key},6) AS {key}"
        if key in {"voltage_v", "current_a", "remaining_fraction"}
        else "formatDateTime(source_timestamp,'%Y-%m-%dT%H:%i:%S.%fZ','UTC') "
        "AS source_timestamp"
        if key == "source_timestamp"
        else key
        for key in expected[0]
    ]
    result = sql(
        reader,
        "SELECT "
        + ",".join(expressions)
        + " FROM unique_events"
        + where
        + " SETTINGS max_execution_time=5,max_threads=1,"
        "max_memory_usage=268435456,max_rows_to_read=32768 "
        "FORMAT JSONEachRow",
    )
    actual = [json.loads(line) for line in result.splitlines()]
    require(
        sorted(map(canonical, actual)) == sorted(map(canonical, expected)),
        "full_unique_content_mismatch",
    )


def run_one(
    folder: Path,
    records: list[Row],
    manifest: SourceManifest,
    writer: HttpConfig,
    reader: HttpConfig,
    prefix: str,
    number: int,
    count: int,
    stop: Path,
    deadline: float,
) -> Row:
    run_id = f"{prefix}-{number:03d}"
    topic = f"m2.m3-final-{run_id}.telemetry.canonical.v1"
    expected = [projection(normalize(row, manifest, run_id), run_id) for row in records]
    transport = Transport(
        lambda kind, value: save(folder / f"{number:03d}-{kind}.json", value)
    )
    identity = transport.create(topic, 1)
    consumer = transport.kafka.Consumer(
        {
            "bootstrap.servers": "127.0.0.1:19092",
            "group.id": run_id + "-read",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "auto.offset.reset": "error",
            "enable.partition.eof": False,
            "socket.timeout.ms": 5000,
        }
    )
    consumer.assign([transport.kafka.TopicPartition(topic, 0, 0)])
    admissions: dict[str, float] = {}
    samples: list[Row] = []
    payload_bytes = 0
    acknowledged = 0
    started = time.perf_counter()
    ack_end = started
    callback_errors = 0

    def callback(error: Error | None, message: Message) -> None:
        nonlocal acknowledged, callback_errors
        if error:
            callback_errors += 1
        else:
            acknowledged += 1

    try:
        for start in range(0, count, BATCH):
            require(not stop.exists(), "resource_stop_requested")
            require(time.monotonic() < deadline, "benchmark_deadline")
            wires: list[bytes] = []
            for index in range(start, start + BATCH):
                admitted = time.perf_counter()
                wire = normalize(records[index % UNIQUE], manifest, run_id)
                event_id = read_battery_event(wire)["event_id"]
                admissions.setdefault(event_id, admitted)
                wires.append(wire)
                payload_bytes += len(wire)
                transport.producer.produce(
                    topic,
                    partition=0,
                    key=b"synthetic-load-vehicle-001",
                    value=wire,
                    on_delivery=callback,
                )
            require(
                transport.producer.flush(6) == 0 and callback_errors == 0,
                "ambiguous_or_failed_publication",
            )
            ack_end = time.perf_counter()
            rows: list[Row] = []
            for offset, wire in enumerate(wires, start):
                message = consumer.poll(5)
                require(message is not None, "source_read_timeout")
                assert message is not None
                require(
                    message.error() is None
                    and message.offset() == offset
                    and message.partition() == 0
                    and message.topic() == topic
                    and message.value() == wire
                    and message.key() == b"synthetic-load-vehicle-001",
                    "source_mismatch",
                )
                rows.append(projection(wire, run_id))
            sql(
                writer,
                "INSERT INTO events SETTINGS async_insert=0,"
                "insert_deduplicate=0,date_time_input_format='best_effort' "
                "FORMAT JSONEachRow",
                b"".join(canonical(row) for row in rows),
                write=True,
            )
            visible(reader, run_id, expected)
            visibility = time.perf_counter()
            if start == 0:
                samples = [
                    {
                        "event_id": key,
                        "admission_monotonic": value,
                        "visible_monotonic": visibility,
                        "latency_seconds": visibility - value,
                    }
                    for key, value in admissions.items()
                ]
        finished = time.perf_counter()
        require(acknowledged == count and len(samples) == UNIQUE, "count_mismatch")
        bounds = consumer.get_watermark_offsets(
            transport.kafka.TopicPartition(topic, 0), timeout=5, cached=False
        )
        require(bounds == (0, count), "source_coverage_mismatch")
    finally:
        consumer.close()
    latency = sorted(cast(float, sample["latency_seconds"]) for sample in samples)
    duration = finished - started
    result: Row = {
        "run_id": run_id,
        "source_identity": identity,
        "attempted": count,
        "acknowledged": acknowledged,
        "unique_visible": UNIQUE,
        "payload_bytes": payload_bytes,
        "measurement_seconds": duration,
        "ack_interval_seconds": ack_end - started,
        "drain_after_last_ack_seconds": finished - ack_end,
        "attempted_per_second": count / duration,
        "acknowledged_per_second": acknowledged / (ack_end - started),
        "unique_visible_per_second": UNIQUE / duration,
        "latency_seconds": {
            name: latency[math.ceil(q * len(latency)) - 1]
            for name, q in [("p50", 0.5), ("p95", 0.95), ("p99", 0.99)]
        },
        "latency_sample_count": len(samples),
        "callback_errors": callback_errors,
        "historical_source_age_seconds": (
            datetime.now(UTC) - datetime(2026, 1, 1, 12, tzinfo=UTC)
        ).total_seconds(),
    }
    save(folder / f"{number:03d}-latency.json", samples)
    save(folder / f"{number:03d}-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-config", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--stop-file", type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    options = parser.parse_args()
    import re

    require(re.fullmatch(r"m6-load-[0-9]{3}", options.run_prefix), "run_prefix_scope")
    folder = options.evidence
    folder.mkdir(exist_ok=False)
    config = cast(Row, json.loads(options.private_config.read_bytes()))
    writer = HttpConfig(**cast(dict[str, str | int], config["writer"]))  # type: ignore[arg-type]
    reader = HttpConfig(**cast(dict[str, str | int], config["reader"]))  # type: ignore[arg-type]
    records, manifest = source(folder)
    deadline = time.monotonic() + 540
    results = [
        run_one(
            folder,
            records,
            manifest,
            writer,
            reader,
            options.run_prefix,
            i,
            count,
            options.stop_file,
            deadline,
        )
        for i, count in enumerate((1024, 8192, 8192, 8192))
    ]
    save(
        folder / "complete.json",
        {
            "warmup": results[0],
            "measured": results[1:],
            "profile": "transport-serving-replay-v1",
            "flink_or_archive": False,
            "generator": "m6-replay-load-v1",
            "seed": 0,
            "vehicles": 1,
            "unique_per_run": UNIQUE,
            "batch_size": BATCH,
            "duplicate_fraction": 1 - UNIQUE / 8192,
            "late_fraction": 0,
            "target_replay_rate": "unpaced_serial_batches",
            "query_method": "synchronous guarded full unique read per batch",
        },
    )
    print("Three measured transport/serving repetitions reconciled", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
