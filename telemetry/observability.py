"""Read-only, loopback Prometheus exposition of bounded M2 log captures."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import cast

from telemetry_metrics import MetricsError, read_metrics

MAX_BYTES = 1024 * 1024
CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def gauge(name: str, help_text: str, samples: list[str]) -> list[str]:
    """Render fixed-name gauge metadata exactly once per family."""
    return [f"# HELP {name} {help_text}", f"# TYPE {name} gauge", *samples]


def collect(path: Path, max_age_seconds: float) -> tuple[str, str]:
    """Return exposition and a safe cause; omit source samples on any failure.

    File age describes capture metadata, not producer activity. One bounded
    capture represents one command per operation; the latest snapshot replaces
    earlier snapshots completely. Counts are gauges, never summed callbacks.
    """
    if not math.isfinite(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError("invalid_capture_age_limit")
    age: float | None = None
    records: tuple[dict[str, object], ...] = ()
    reason = "ok"
    try:
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise MetricsError("capture_not_regular")
            body = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        if len(body) > MAX_BYTES:
            raise MetricsError("capture_too_large")
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise MetricsError("capture_changed")
        age = time.time() - after.st_mtime
        if age < 0:
            raise MetricsError("capture_clock_error")
        if age > max_age_seconds:
            raise MetricsError("capture_stale")
        if body and not body.endswith(b"\n"):
            raise MetricsError("capture_incomplete")
        records = read_metrics(body.decode("utf-8"))
        if not records:
            raise MetricsError("capture_empty")
        for record in records:
            for value in cast(dict[str, int | float], record["values"]).values():
                try:
                    finite = math.isfinite(value)
                except OverflowError:
                    finite = False
                if not finite:
                    raise MetricsError("capture_numeric_overflow")
    except MetricsError as error:
        reason = str(error)
    except UnicodeError:
        reason = "capture_encoding"
    except OSError:
        reason = "capture_unavailable"
    lines = gauge(
        "fleet_capture_success",
        "One when the entire bounded capture is readable, valid and within age limit.",
        [f"fleet_capture_success {int(reason == 'ok')}"],
    )
    if age is not None and age >= 0:
        lines += gauge(
            "fleet_capture_age_seconds",
            "Wall-clock age of capture file modification; not live source freshness.",
            [f"fleet_capture_age_seconds {age:.6f}"],
        )
    if reason == "ok":
        latest: dict[str, dict[str, object]] = {}
        for record in records:
            latest[cast(str, record["operation"])] = record
        families: dict[str, list[str]] = {}
        for operation, record in sorted(latest.items()):
            labels = f'operation="{operation}",event="{record["event"]}"'
            for key, value in cast(dict[str, int | float], record["values"]).items():
                name = "fleet_m2_snapshot_" + key
                families.setdefault(name, []).append(f"{name}{{{labels}}} {value}")
        for name, samples in sorted(families.items()):
            lines += gauge(
                name, "Latest M2 operation snapshot; not a counter.", samples
            )
    return "\n".join(lines) + "\n", reason


def make_server(path: Path, max_age_seconds: float, port: int) -> HTTPServer:
    """Bind only IPv4 loopback; serialize bounded local capture reads."""
    if not math.isfinite(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError("invalid_capture_age_limit")

    class Handler(BaseHTTPRequestHandler):
        last_reason: str | None = None

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(3)

        def do_GET(self) -> None:
            if self.path != "/metrics":
                self.send_error(404)
                return
            body, reason = collect(path, max_age_seconds)
            if reason != Handler.last_reason:
                print(
                    json.dumps({"event": "metrics_capture", "reason": reason}),
                    file=sys.stderr,
                    flush=True,
                )
                Handler.last_reason = reason
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format: str, *args: object) -> None:
            # Request paths and client-controlled headers never enter logs.
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 0.5
    return server


def main() -> int:
    """Serve until interrupted; lifecycle ownership stays with the caller."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--port", type=int, default=19100)
    parser.add_argument("--max-age-seconds", type=float, default=300)
    options = parser.parse_args()
    try:
        with make_server(
            options.input, options.max_age_seconds, options.port
        ) as server:
            while True:
                server.handle_request()
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, OverflowError):
        print('{"event":"metrics_exporter","reason":"startup_failed"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
