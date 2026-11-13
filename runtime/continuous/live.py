"""Serve immediate Flink output; historical transactional output stays separate."""

import argparse
import json
import secrets
import threading
import time
from pathlib import Path
from typing import cast

from runtime.continuous.kafka import Kafka
from runtime.continuous.link_watch import Server
from telemetry.link_watch import LinkWatch
from telemetry.live_state import LiveState


def run(config_path: Path, port: int) -> None:
    config = cast(dict[str, object], json.loads(config_path.read_bytes()))
    source = cast(dict[str, str], config["live_source"])
    kafka = Kafka(
        cast(str, config["bootstrap"]),
        source["cluster_id"],
        config.get("kafka_connection"),
    )
    if kafka.describe(source["topic"]) != source:
        raise ValueError("live_topic_identity")
    vehicles = cast(dict[str, str], config["source_logs"])
    state = LiveState(cast(str, config["run_id"]), vehicles)
    watch = LinkWatch(list(vehicles), secrets.token_hex(16), time.monotonic())
    server = Server(
        ("127.0.0.1", port),
        watch,
        cast(str, config["writer_token"]),
        cast(str, config["reader_token"]),
        live=state,
    )
    stop = threading.Event()

    def collect() -> None:
        consumer = kafka.consumer(cast(str, config["run_id"]) + "-live-view-v1")
        try:
            offsets = dict.fromkeys(map(str, range(18)), 0)
            positions = kafka.positions(source["topic"], offsets)
            highs: dict[str, int] = {}
            for position in positions:
                low, high = consumer.get_watermark_offsets(
                    position, timeout=5, cached=False
                )
                if low != 0:
                    raise ValueError("live_rebuild_retention_gap")
                highs[str(position.partition)] = high
            # This ephemeral latest-value view rebuilds by reading retained facts.
            # It never commits, changes or resets any Kafka group offsets.
            consumer.assign(positions)
            while not stop.is_set():
                message = consumer.poll(0.02)
                with server.lock:
                    if message is not None:
                        if message.error() is not None:
                            raise ValueError("live_source_read_error")
                        body = message.value()
                        if body is None:
                            raise ValueError("live_empty_fact")
                        partition = str(message.partition())
                        is_live = message.offset() >= highs[partition]
                        state.accept(
                            body,
                            time.time_ns() // 1_000_000,
                            time.monotonic() if is_live else None,
                        )
                        offsets[str(message.partition())] = message.offset() + 1
                    state.polled_at = time.monotonic()
                    state.ready = all(offsets[p] >= high for p, high in highs.items())
        except Exception as error:
            with server.lock:
                state.error = type(error).__name__
                state.ready = False
            print(
                json.dumps(
                    {
                        "event": "flink_live_unavailable",
                        "exception": type(error).__name__,
                    }
                ),
                flush=True,
            )
        finally:
            consumer.close()

    collector = threading.Thread(target=collect, daemon=True)
    monitor = threading.Thread(target=server.monitor, args=(stop,), daemon=True)
    collector.start()
    monitor.start()
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        stop.set()
        server.server_close()
        collector.join(timeout=6)
        monitor.join(timeout=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18769)
    args = parser.parse_args()
    run(args.config, args.port)
