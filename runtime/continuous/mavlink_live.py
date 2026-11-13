"""Receive one live PX4 SITL source; no MAVLink transmit or historical replay."""

import argparse
import importlib
import json
import secrets
import threading
import time
from importlib.metadata import version
from pathlib import Path
from typing import Protocol, cast

from runtime.continuous.link_watch import Handler as LinkHandler
from runtime.continuous.link_watch import Server as LinkServer
from telemetry.conversion_contract import integer_value, json_object, string_value
from telemetry.local_io import read_bounded
from telemetry.mavlink_live import MavlinkView


class Message(Protocol):
    def get_type(self) -> str: ...
    def get_srcSystem(self) -> int: ...
    def get_srcComponent(self) -> int: ...
    def to_dict(self) -> dict[str, object]: ...


class Connection(Protocol):
    def recv_match(
        self, *, blocking: bool, timeout: float | None
    ) -> Message | None: ...
    def close(self) -> None: ...


class Mavutil(Protocol):
    def mavlink_connection(self, address: str) -> Connection: ...


class Server(LinkServer):
    def __init__(
        self, host: str, port: int, view: MavlinkView, writer: str, reader: str
    ) -> None:
        super().__init__((host, port), view.watch, writer, reader)
        self.view = view
        self.RequestHandlerClass = Handler


class Handler(LinkHandler):
    def do_GET(self) -> None:
        server = cast(Server, self.server)
        if self.path == "/":
            self.reply(
                200, Path(__file__).with_suffix(".html").read_bytes(), "text/html"
            )
            return
        if not self.authorized(server.reader):
            return
        with server.lock:
            now = time.monotonic()
            if self.path == "/v1/mavlink":
                self.reply(
                    200, json.dumps(server.view.snapshot(now), allow_nan=False).encode()
                )
            elif self.path == "/metrics":
                values = {
                    "accepted": server.view.accepted,
                    "rejected": server.view.rejected,
                    "ignored": server.view.ignored,
                }
                gateway_ok = int(server.view.snapshot(now)["gateway_ok"] is True)
                body = (
                    server.watch.metrics(now)
                    + (
                        "# TYPE telemetry_mavlink_gateway_ok gauge\n"
                        f"telemetry_mavlink_gateway_ok {gateway_ok}\n"
                    ).encode()
                    + "".join(
                        f"# TYPE telemetry_mavlink_{name} counter\n"
                        f"telemetry_mavlink_{name} {value}\n"
                        for name, value in values.items()
                    ).encode()
                )
                self.reply(200, body, "text/plain; version=0.0.4")
            else:
                self.reply(404, b'{"error":"not_found"}')

    def do_POST(self) -> None:
        self.reply(405, b'{"error":"receive_only"}')


def collect(server: Server, connection: Connection, stop: threading.Event) -> None:
    try:
        while not stop.is_set():
            with server.lock:
                server.view.poll(time.monotonic())
            received = False
            for _ in range(128):
                # A zero SDK timeout can expire before its first socket read.
                message = connection.recv_match(blocking=False, timeout=None)
                if message is None:
                    break
                received = True
                with server.lock:
                    if message.get_type() == "BAD_DATA":
                        server.view.rejected += 1
                        continue
                    try:
                        server.view.accept(
                            message.get_type(),
                            message.to_dict(),
                            message.get_srcSystem(),
                            message.get_srcComponent(),
                            time.monotonic(),
                            time.time_ns() // 1_000_000,
                        )
                    except ValueError:
                        # Fixed counters only; do not log source payloads/coordinates.
                        pass
            if not received:
                stop.wait(0.02)
    except Exception:
        # External SDK boundary: fail visibly without printing packet contents.
        with server.lock:
            server.view.failure = "collector_failed"
        print('{"event":"mavlink_collector_failed"}', flush=True)
    finally:
        connection.close()


def run(config_path: Path, host: str, port: int) -> None:
    config = json_object(read_bounded(config_path, 8192))
    if set(config) != {
        "source_kind",
        "source_boot_session",
        "vehicle_id",
        "system_id",
        "component_id",
        "udp_host",
        "udp_port",
        "writer_token",
        "reader_token",
    }:
        raise ValueError("mavlink_config_fields")
    if config["source_kind"] != "px4-sitl" or config["udp_host"] not in (
        "127.0.0.1",
        "0.0.0.0",
    ):
        raise ValueError("mavlink_simulation_scope")
    udp_port = integer_value(config["udp_port"])
    if not 1024 <= udp_port <= 65535 or not 1024 <= port <= 65535:
        raise ValueError("mavlink_port")
    if version("pymavlink") != "2.4.50":
        raise ValueError("unsupported_mavlink_version")
    view = MavlinkView(
        string_value(config["vehicle_id"]),
        string_value(config["source_boot_session"]),
        integer_value(config["system_id"]),
        integer_value(config["component_id"]),
        secrets.token_hex(16),
        time.monotonic(),
    )
    mavutil = cast(Mavutil, importlib.import_module("pymavlink.mavutil"))
    connection = mavutil.mavlink_connection(f"udpin:{config['udp_host']}:{udp_port}")
    try:
        server = Server(
            host,
            port,
            view,
            string_value(config["writer_token"]),
            string_value(config["reader_token"]),
        )
    except BaseException:
        connection.close()
        raise
    stop = threading.Event()
    workers = [
        threading.Thread(target=server.monitor, args=(stop,), daemon=True),
        threading.Thread(target=collect, args=(server, connection, stop), daemon=True),
    ]
    for worker in workers:
        worker.start()
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        stop.set()
        for worker in workers:
            worker.join(timeout=2)
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=18771)
    args = parser.parse_args()
    run(args.config, args.host, args.port)
