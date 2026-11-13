"""Frozen synthetic source files and a paced continuous native Kafka publisher."""

from __future__ import annotations

import argparse
import json
import signal
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, cast

from fleet_telemetry import (
    ClockAnchor,
    DeliveryMetadata,
    Rejection,
    SourceManifest,
    normalize_battery,
)
from runtime.continuous.kafka import Kafka
from telemetry.archive_documents import canonical
from telemetry.continuous_archive import object_row, require

if TYPE_CHECKING:
    from scripts.m3_transport_types import Error, Message


def native(index: int, timestamp: int) -> dict[str, object]:
    row: dict[str, object] = {
        "source_record_index": index,
        "timestamp_us": timestamp,
        "voltage_mv": 15000 + index % 1000,
    }
    if index % 4 in (0, 2):
        row["current_ma"] = 1000
    if index % 4 in (0, 1):
        row["remaining_pct"] = 50
    return row


@contextmanager
def _stop_on_signal() -> Iterator[Callable[[], bool]]:
    stopped = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopped
        stopped = True

    previous = {
        sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        yield lambda: stopped
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def prepare(
    directory: Path,
    records: int,
    vehicles: int,
    run_id: str,
    interval_us: int = 1_000_000,
) -> None:
    require(
        64 <= records <= 2_000_000 and 18 <= vehicles <= min(1024, records),
        "continuous_generator_bound",
    )
    require(
        type(interval_us) is int and 1_000 <= interval_us <= 1_000_000,
        "continuous_generator_interval",
    )
    directory.mkdir(exist_ok=False)
    manifests: dict[str, object] = {}
    for vehicle_index in range(vehicles):
        vehicle = f"stream-vehicle-{vehicle_index:04d}"
        count = len(range(vehicle_index, records, vehicles))
        rows = [native(i, i * interval_us) for i in range(count)]
        rows.append(native(count, count * interval_us + 20_000_000))
        body = canonical(
            {"generator_version": "continuous-native-v1", "seed": 0, "records": rows}
        )
        (directory / f"{vehicle}.json").write_bytes(body)
        manifest = SourceManifest(
            f"continuous-manifest-{vehicle_index:04d}",
            "sha256:" + sha256(body).hexdigest(),
            vehicle,
            "battery_status:0",
            0,
            count * interval_us + 20_000_000,
            ClockAnchor(0, "2026-01-01T12:00:00.000000Z"),
            f"{vehicle}.json",
            "2026-10-27T00:00:00.000000Z",
            "Project-authored seeded synthetic source.",
            "Synthetic vehicle; no coordinates.",
        )
        manifests[vehicle] = asdict(manifest)
    plan = {
        "run_id": run_id,
        "generator": "continuous-native-v1",
        "seed": 0,
        "records": records,
        "vehicles": vehicles,
        "tail_measurements": vehicles,
        "interval_us": interval_us,
        "source_logs": {
            key: object_row(value)["source_log_id"] for key, value in manifests.items()
        },
        "manifests": manifests,
        "timestamp_min": "2026-01-01T12:00:00.000000Z",
        "timestamp_max": (
            datetime(2026, 1, 1, 12, tzinfo=UTC)
            + timedelta(
                microseconds=((records + vehicles - 1) // vehicles) * interval_us
                + 20_000_000
            )
        ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }
    (directory / "plan.json").write_bytes(canonical(plan))


def publish(
    config_path: Path, fixture: Path, ledger: Path, rate: int, replay: bool = False
) -> None:
    require(1 <= rate <= 10000, "continuous_publisher_rate")
    config = object_row(json.loads(config_path.read_bytes()))
    plan = object_row(json.loads((fixture / "plan.json").read_bytes()))
    interval_value = plan.get("interval_us", 1_000_000)
    require(
        type(interval_value) is int and 1_000 <= interval_value <= 1_000_000,
        "continuous_generator_interval",
    )
    interval_us = cast(int, interval_value)
    require(plan["run_id"] == config["run_id"], "continuous_source_scope")
    kafka = Kafka(
        cast(str, config["bootstrap"]),
        cast(str, object_row(config["source"])["cluster_id"]),
        config.get("kafka_connection"),
    )
    topic = cast(str, config["input_topic"])
    require(kafka.describe(topic) == config["source"], "continuous_source_identity")
    probe = kafka.consumer(cast(str, config["run_id"]) + "-publisher-check-v1")
    try:
        bounds = [
            probe.get_watermark_offsets(p, timeout=5, cached=False)
            for p in kafka.positions(topic, dict.fromkeys(map(str, range(18)), 0))
        ]
        require(all(low == 0 for low, _ in bounds), "continuous_source_retention_gap")
        require(
            replay or all(high == 0 for _, high in bounds),
            "continuous_nonempty_source_requires_explicit_replay",
        )
    finally:
        probe.close()
    producer = kafka.sdk.Producer(
        {
            **kafka.client_properties(),
            "enable.idempotence": True,
            "acks": "all",
            "message.timeout.ms": 120000,
            "queue.buffering.max.messages": 4096,
            "queue.buffering.max.kbytes": 8192,
            "linger.ms": 10,
        }
    )
    manifests = object_row(plan["manifests"])
    models: dict[str, SourceManifest] = {}
    for vehicle, value in manifests.items():
        doc = object_row(value)
        anchor = ClockAnchor(**cast(dict[str, int | str | None], doc["clock_anchor"]))  # type: ignore[arg-type]
        models[vehicle] = SourceManifest(**{**doc, "clock_anchor": anchor})  # type: ignore[arg-type]
        body = (fixture / f"{vehicle}.json").read_bytes()
        require(
            "sha256:" + sha256(body).hexdigest() == models[vehicle].source_log_id,
            "continuous_native_checksum",
        )
        source = object_row(json.loads(body))
        vehicle_index = sorted(manifests).index(vehicle)
        count_for_vehicle = len(
            range(vehicle_index, cast(int, plan["records"]), len(manifests))
        )
        require(
            source.get("records")
            == [native(i, i * interval_us) for i in range(count_for_vehicle)]
            + [native(count_for_vehicle, count_for_vehicle * interval_us + 20_000_000)],
            "continuous_native_plan_mismatch",
        )
    vehicles = sorted(models)
    partitions = {v: int(sha256(v.encode()).hexdigest(), 16) % 18 for v in vehicles}
    require(
        set(partitions.values()) == set(range(18)),
        "continuous_vehicle_partition_coverage",
    )
    started = time.perf_counter()
    acknowledged = 0
    errors = 0
    payload_bytes = 0
    attempted = 0
    with ledger.open("x", encoding="utf8") as stream, _stop_on_signal() as stopped:

        def sent(
            error: Error | None,
            message: Message,
            event_id: str,
            value_hash: str,
            admitted: float,
        ) -> None:
            nonlocal acknowledged, errors
            if error:
                errors += 1
                return
            acknowledged += 1
            stream.write(
                json.dumps(
                    {
                        "event_id": event_id,
                        "value_sha256": value_hash,
                        "partition": message.partition(),
                        "offset": message.offset(),
                        "admission_monotonic": admitted,
                        "ack_monotonic": time.perf_counter(),
                    }
                )
                + "\n"
            )

        count = cast(int, plan["records"])
        for index in range(count + len(vehicles)):
            if stopped():
                break
            require(errors == 0, "continuous_publish_failed")
            elapsed = time.perf_counter() - started
            if index / rate > elapsed:
                time.sleep(index / rate - elapsed)
            if stopped():
                break
            vehicle = (
                vehicles[index % len(vehicles)]
                if index < count
                else vehicles[index - count]
            )
            number = (
                index // len(vehicles)
                if index < count
                else len(range(vehicles.index(vehicle), count, len(vehicles)))
            )
            stamp = number * interval_us + (0 if index < count else 20_000_000)
            admitted = time.perf_counter()
            event = normalize_battery(
                native(number, stamp),
                models[vehicle],
                models[vehicle].clock_anchor,
                DeliveryMetadata(
                    datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    cast(str, config["run_id"]),
                ),
            )
            if isinstance(event, Rejection):
                raise ValueError("continuous_native_rejected")
            wire = canonical(event)
            payload_bytes += len(wire)
            event_id = event["event_id"]
            value_hash = sha256(wire).hexdigest()

            def callback(
                error: Error | None,
                message: Message,
                identity: str = event_id,
                checksum: str = value_hash,
                begin: float = admitted,
            ) -> None:
                sent(error, message, identity, checksum, begin)

            while True:
                try:
                    producer.produce(
                        topic,
                        partition=partitions[vehicle],
                        key=vehicle.encode(),
                        value=wire,
                        on_delivery=callback,
                    )
                    attempted += 1
                    break
                except BufferError:
                    if stopped():
                        break
                    producer.poll(0.1)
            producer.poll(0)
            if index % 256 == 255:
                stream.flush()
        deadline = time.monotonic() + 120
        stop_deadline: float | None = None
        while True:
            if stopped() and stop_deadline is None:
                stop_deadline = time.monotonic() + 10
            remaining = min(deadline, stop_deadline or deadline) - time.monotonic()
            if remaining <= 0:
                pending = producer.flush(0)
                break
            pending = producer.flush(min(1, remaining))
            if pending == 0:
                break
        interrupted = stopped()
        stream.flush()
    ledger.with_suffix(".summary.json").write_bytes(
        canonical(
            {
                "attempted": attempted,
                "acknowledged": acknowledged,
                "unconfirmed": pending,
                "delivery_errors": errors,
                "interrupted": interrupted,
                "payload_bytes": payload_bytes,
                "duration_seconds": time.perf_counter() - started,
                "offered_records_per_second": rate,
                "distinct_ids_in_batch": acknowledged,
                "expected_duplicate_fraction": 1 if replay else 0,
                "mode": "identity-replay" if replay else "fresh-measurements",
                "native_records": count,
                "tail_measurements": len(vehicles),
            }
        )
    )
    print(
        json.dumps(
            {
                "event": "continuous_publisher",
                "acknowledged": acknowledged,
                "interrupted": interrupted,
                "unconfirmed": pending,
            }
        ),
        flush=True,
    )
    require(
        pending == 0 and errors == 0 and acknowledged == attempted,
        "continuous_publish_uncertain",
    )
    if interrupted:
        raise InterruptedError("continuous_publish_interrupted")
    require(attempted == count + len(vehicles), "continuous_publish_incomplete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    make = sub.add_parser("prepare")
    make.add_argument("--directory", type=Path, required=True)
    make.add_argument("--records", type=int, default=20000)
    make.add_argument("--vehicles", type=int, default=128)
    make.add_argument("--interval-us", type=int, default=1_000_000)
    make.add_argument("--run-id", required=True)
    send = sub.add_parser("publish")
    send.add_argument("--config", type=Path, required=True)
    send.add_argument("--fixture", type=Path, required=True)
    send.add_argument("--ledger", type=Path, required=True)
    send.add_argument("--rate", type=int, default=1000)
    send.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(
            args.directory, args.records, args.vehicles, args.run_id, args.interval_us
        )
    else:
        publish(args.config, args.fixture, args.ledger, args.rate, args.replay)
