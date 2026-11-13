"""Loopback live heartbeat receiver and dashboard; no Kafka/checkpoint dependency."""

from __future__ import annotations

import argparse
import json
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, cast

from telemetry.link_watch import LinkWatch

if TYPE_CHECKING:
    from telemetry.live_state import LiveState

POLL_SECONDS = 0.1
MAX_BODY = 1024


class Server(ThreadingHTTPServer):
    """Reject overload rather than accumulating threads or heartbeat queues."""

    daemon_threads = True
    request_queue_size = 16

    def __init__(
        self,
        address: tuple[str, int],
        watch: LinkWatch,
        writer: str,
        reader: str,
        live: LiveState | None = None,
    ) -> None:
        if address[0] not in ("127.0.0.1", "0.0.0.0"):
            raise ValueError("link_watch_bind")
        if min(len(writer), len(reader)) < 32 or writer == reader:
            raise ValueError("link_watch_credentials")
        self.watch, self.writer, self.reader = watch, writer, reader
        self.live = live
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(address, Handler)

    def process_request(
        self,
        request: socket.socket | tuple[bytes, socket.socket],
        client_address: object,
    ) -> None:
        if not isinstance(request, socket.socket):
            raise ValueError("link_watch_tcp_required")
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            request.settimeout(0.5)
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(
        self,
        request: socket.socket | tuple[bytes, socket.socket],
        client_address: object,
    ) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def monitor(self, stop: threading.Event) -> None:
        while not stop.wait(POLL_SECONDS):
            with self.lock:
                transitions = self.watch.tick(time.monotonic())
            for row in transitions:
                # Only transitions, fixed fleet bound; no payload/identifier metrics.
                print(json.dumps(row), flush=True)


class Handler(BaseHTTPRequestHandler):
    def reply(self, status: int, body: bytes, mime: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, token: str) -> bool:
        if secrets.compare_digest(
            self.headers.get("Authorization", "").encode(), ("Bearer " + token).encode()
        ):
            return True
        self.reply(401, b'{"error":"unauthorized"}')
        return False

    def do_GET(self) -> None:
        server = cast(Server, self.server)
        if self.path == "/":
            self.reply(
                200, Path(__file__).with_suffix(".html").read_bytes(), "text/html"
            )
            return
        if self.path == "/telemetry" and server.live is not None:
            self.reply(
                200, Path(__file__).with_name("live.html").read_bytes(), "text/html"
            )
            return
        token = server.writer if self.path == "/v1/session" else server.reader
        if not self.authorized(token):
            return
        mime = "application/json"
        status = 200
        with server.lock:
            now = time.monotonic()
            if self.path == "/v1/session":
                body = json.dumps({"receiver_epoch": server.watch.epoch}).encode()
            elif self.path == "/v1/links":
                body = json.dumps(server.watch.snapshot(now)).encode()
            elif self.path == "/v1/telemetry" and server.live is not None:
                body = json.dumps(server.live.snapshot(now)).encode()
            elif self.path == "/metrics":
                body = server.watch.metrics(now)
                mime = "text/plain; version=0.0.4"
            else:
                status, body = 404, b'{"error":"not_found"}'
        self.reply(status, body, mime)

    def do_POST(self) -> None:
        server = cast(Server, self.server)
        if self.path != "/v1/heartbeat":
            self.reply(404, b'{"error":"not_found"}')
            return
        if not self.authorized(server.writer):
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= MAX_BODY or self.headers.get("Transfer-Encoding"):
                raise ValueError("link_watch_body_bound")
            body = self.rfile.read(size)
            if len(body) != size:
                raise ValueError("link_watch_incomplete_body")
            row = json.loads(body)
            if not isinstance(row, dict):
                raise ValueError("link_watch_format")
            with server.lock:
                server.watch.heartbeat(
                    row, time.monotonic(), time.time_ns() // 1_000_000
                )
        except (ValueError, UnicodeError) as error:
            category = (
                str(error) if str(error).startswith("link_watch_") else "invalid_json"
            )
            self.reply(400, json.dumps({"error": category}).encode())
            return
        self.reply(202, b'{"accepted":true}')

    def log_message(self, format: str, *args: object) -> None:
        pass


def run(config: Path, host: str, port: int) -> None:
    row = json.loads(config.read_bytes())
    watch = LinkWatch(
        row["vehicles"],
        secrets.token_hex(16),
        time.monotonic(),
        timeout=row.get("timeout_seconds", 3.0),
        max_age=row.get("max_gateway_age_seconds", 1.0),
    )
    server = Server((host, port), watch, row["writer_token"], row["reader_token"])
    stop = threading.Event()
    thread = threading.Thread(target=server.monitor, args=(stop,), daemon=True)
    thread.start()
    try:
        server.serve_forever(poll_interval=POLL_SECONDS)
    finally:
        stop.set()
        server.server_close()
        thread.join(timeout=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18768)
    args = parser.parse_args()
    run(args.config, args.host, args.port)
