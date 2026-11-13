"""One fixed-assignment continuous archiver; buffers and objects remain bounded."""

import argparse
import fcntl
import json
import signal
import time
from pathlib import Path
from typing import cast

from runtime.continuous.kafka import Kafka, observation
from runtime.s3.archive_store import make_archive_store
from telemetry.continuous_archive import SegmentedArchive, object_row, require


def run(config_path: Path, state: Path, initialize: bool) -> None:
    config = object_row(json.loads(config_path.read_bytes()))
    plan = object_row(config["archive_plan"])
    source = object_row(plan["source"])
    kafka = Kafka(
        cast(str, config["bootstrap"]),
        cast(str, source["cluster_id"]),
        config.get("kafka_connection"),
    )
    topic = cast(str, source["topic"])
    require(kafka.describe(topic) == source, "archive_source_identity")
    storage = object_row(config["storage"])
    stores = [
        make_archive_store(
            cast(str, storage["endpoint"]),
            "us-east-1",
            cast(str, storage["bucket"]),
            cast(str, storage["prefix"]),
            **cast(dict[str, str], storage[role]),
        )
        for role in ("writer", "reader")
    ]
    state.mkdir(mode=0o700, exist_ok=True)
    consumer = kafka.consumer(cast(str, config["archive_group"]))
    stopping = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with (state / "owner.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        archive = SegmentedArchive(
            stores[0], stores[1], state / "cursor.json", plan, initialize=initialize
        )
        offsets = {str(p): archive.next_offset(p) for p in range(18)}
        committed = consumer.committed(kafka.positions(topic, offsets), timeout=5)
        for position in committed:
            expected = offsets[str(position.partition)]
            low, high = consumer.get_watermark_offsets(
                position, timeout=5, cached=False
            )
            require(low <= expected <= high, "archive_retention_gap")
            if initialize:
                require(
                    low == high == expected == 0 and position.offset < 0,
                    "archive_initial_origin",
                )
            else:
                require(
                    0 <= position.offset <= expected,
                    "archive_broker_ahead_or_state_missing",
                )
            if position.offset != expected:
                kafka.commit(consumer, topic, position.partition, expected)
        consumer.assign(kafka.positions(topic, offsets))
        buffers: dict[int, list[dict[str, object]]] = {p: [] for p in range(18)}
        sizes = dict.fromkeys(range(18), 0)
        last = time.monotonic()
        accepted = 0

        def flush(partition: int) -> None:
            nonlocal accepted
            rows = buffers[partition]
            if not rows:
                return
            require(kafka.describe(topic) == source, "archive_source_identity")
            low, high = consumer.get_watermark_offsets(
                kafka.sdk.TopicPartition(topic, partition), timeout=5, cached=False
            )
            require(
                low <= archive.next_offset(partition) <= high, "archive_retention_gap"
            )
            taken = archive.publish(partition, rows)
            if taken:
                require(kafka.describe(topic) == source, "archive_source_identity")
                kafka.commit(consumer, topic, partition, archive.next_offset(partition))
                accepted += taken
                del rows[:taken]
                sizes[partition] = sum(len(json.dumps(row)) for row in rows)

        try:
            while not stopping:
                message = consumer.poll(0.1)
                if message is not None:
                    require(message.error() is None, "archive_source_read_error")
                    partition = message.partition()
                    row = observation(message, source)
                    expected = archive.next_offset(partition) + len(buffers[partition])
                    require(row["offset"] == expected, "archive_offset_gap")
                    size = len(json.dumps(row))
                    require(size <= 256 * 1024, "archive_record_limit")
                    if sizes[partition] + size > 512 * 1024:
                        flush(partition)
                    buffers[partition].append(row)
                    sizes[partition] += size
                    if len(buffers[partition]) >= 128:
                        flush(partition)
                if time.monotonic() - last >= 2:
                    for partition in range(18):
                        flush(partition)
                    print(
                        json.dumps(
                            {
                                "event": "continuous_archive",
                                "archived_observations": accepted,
                                "buffered_observations": sum(
                                    map(len, buffers.values())
                                ),
                            }
                        ),
                        flush=True,
                    )
                    last = time.monotonic()
            for partition in range(18):
                while buffers[partition]:
                    before = len(buffers[partition])
                    flush(partition)
                    require(
                        len(buffers[partition]) < before, "archive_incomplete_retry"
                    )
        finally:
            consumer.close()
            for store in stores:
                store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    run(args.config, args.state, args.initialize)
