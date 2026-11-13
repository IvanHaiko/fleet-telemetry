"""Loopback-only map for an isolated, simulation-only Flink output topic."""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from runtime.continuous.kafka import Kafka
from telemetry.position_live import PositionView


def run(config_path: Path, port: int) -> None:
    config = cast(dict[str, object], json.loads(config_path.read_bytes()))
    source = cast(dict[str, str], config["output_source"])
    kafka = Kafka(
        cast(str, config["bootstrap"]),
        source["cluster_id"],
        config.get("kafka_connection"),
    )
    if kafka.describe(source["topic"]) != source:
        raise ValueError("position_output_identity")
    ids = config["system_ids"]
    if not isinstance(ids, list):
        raise ValueError("position_vehicle_scope")
    view = PositionView(set(ids))
    lock = threading.Lock()
    stop = threading.Event()
    state: dict[str, object] = {"healthy": False, "last_poll": None}

    def collect() -> None:
        consumer = kafka.consumer(cast(str, config["run_id"]) + "-position-view")
        try:
            offsets = dict.fromkeys(map(str, range(18)), 0)
            positions = kafka.positions(source["topic"], offsets)
            highs = {}
            for position in positions:
                low, high = consumer.get_watermark_offsets(
                    position, timeout=5, cached=False
                )
                if low != 0:
                    raise ValueError("position_retention_gap")
                highs[str(position.partition)] = high
            consumer.assign(positions)
            while not stop.is_set():
                message = consumer.poll(0.1)
                with lock:
                    if message is not None:
                        body = message.value()
                        if message.error() is not None or body is None:
                            raise ValueError("position_kafka_message")
                        row = json.loads(body)
                        if not isinstance(row, dict):
                            raise ValueError("position_message")
                        partition = str(message.partition())
                        observed = (
                            time.monotonic()
                            if message.offset() >= highs[partition]
                            else None
                        )
                        view.accept(row, observed)
                        offsets[partition] = message.offset() + 1
                    state["last_poll"] = time.monotonic()
                    state["healthy"] = all(
                        offsets[p] >= high for p, high in highs.items()
                    )
        except Exception as error:
            with lock:
                state["healthy"] = False
            print(
                json.dumps(
                    {
                        "event": "position_collector_unavailable",
                        "exception": type(error).__name__,
                    }
                ),
                flush=True,
            )
        finally:
            consumer.close()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                body = Path(__file__).with_suffix(".html").read_bytes()
                content_type = "text/html; charset=utf-8"
            elif self.path == "/v1/positions":
                now = time.monotonic()
                with lock:
                    result = view.snapshot(now)
                    last = state["last_poll"]
                    result["collection_ok"] = bool(
                        state["healthy"]
                        and isinstance(last, float)
                        and 0 <= now - last <= 2
                    )
                body = json.dumps(result).encode()
                content_type = "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=collect, daemon=True)
    thread.start()
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        stop.set()
        server.server_close()
        thread.join(timeout=6)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18770)
    args = parser.parse_args()
    run(args.config, args.port)
