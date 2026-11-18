"""Local operator console for the recorded-flight fleet."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.request import urlopen

from runtime.recording.fault_run import RECORDING_INPUTS
from runtime.recording.live_prepare import PACKAGES
from runtime.recording.panel_history import list_runs, original_project
from runtime.recording.panel_services import COOKIE, Monitor, viewer_cookie
from runtime.recording.prepare import PLUGIN
from runtime.recording.profile import ROOT, Document, worker_json
from telemetry.ulog_replay import plan

DATA = ROOT / ".local-discovery"
ASSETS = Path(__file__).with_name("panel_assets")
PROJECT = "fleet-panel-local"
URL = "http://127.0.0.1:18765"
TOKEN = secrets.token_urlsafe(32)
ENV = {
    **os.environ,
    "COMPOSE_PROJECT_NAME": PROJECT,
    "RECORDING_PANEL_SSO": "true",
    "RECORDING_GRAFANA_COOKIE": COOKIE,
    "RECORDING_SUBNET": "10.253.243.16/28",
    "RECORDING_LIVE_SUBNET": "10.253.243.32/28",
}


def document(path: Path) -> Document:
    return cast(Document, json.loads(path.read_bytes()))


def last_sample(path: Path) -> Document:
    if not path.is_file():
        return {}
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 65536))
        for line in reversed(stream.read().splitlines()):
            try:
                return cast(Document, json.loads(line))
            except ValueError:
                continue
    return {}


def execute(*args: str, module: str = "fleet", project: str = PROJECT) -> Document:
    result = subprocess.run(
        [sys.executable, "-m", "runtime.recording." + module, *args],
        cwd=ROOT,
        env={**ENV, "COMPOSE_PROJECT_NAME": project},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=2200,
    )
    try:
        row = worker_json(result.stdout)
    except ValueError as error:
        raise ValueError(
            "Command failed. Check Docker Desktop and the run log."
        ) from error
    if result.returncode or row.get("status") in {"failed", "refused"}:
        raise ValueError(
            str(row.get("category") or row.get("reason") or "Command failed")
        )
    return row


def choose_file() -> str:
    # Tk owns the main thread of a separate process, including on Windows.
    result = subprocess.run(
        [sys.executable, "-m", "runtime.recording.panel", "--pick"],
        capture_output=True,
        encoding="ascii",
        errors="replace",
        cwd=ROOT,
        timeout=600,
    )
    if result.returncode:
        raise ValueError("The local file picker could not open.")
    return str(json.loads(result.stdout))


class Console:
    def __init__(self) -> None:
        DATA.mkdir(exist_ok=True)
        self.file = DATA / "fleet-panel.json"
        self.state: Document = (
            document(self.file)
            if self.file.exists()
            else {
                "run": "",
                "phase": "Idle",
                "sources": {},
                "members": {},
            }
        )
        self.sources = cast(dict[str, str], self.state["sources"])
        for key, (_, path) in RECORDING_INPUTS.items():
            if path.is_file():
                self.sources[key.upper()] = str(path)
        self.lock = threading.RLock()
        self.busy = ""
        self.message = ""
        self.vehicles: Document = {}
        self.sampled = 0.0
        self.polling = False
        self.monitor = Monitor()
        self.history: list[Document] = []
        self.history_at = 0.0

    def save(self) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state), encoding="utf-8")
        tmp.replace(self.file)

    def snapshot(self) -> Document:
        with self.lock:
            run = str(self.state["run"])
            if time.monotonic() - self.history_at > 30:
                self.history = list_runs(DATA)
                self.history_at = time.monotonic()
            if (
                self.state["phase"] in {"Running", "Completed"}
                and not self.polling
                and time.monotonic() - self.sampled >= 6
            ):
                self.polling = True
                threading.Thread(target=self.poll, args=(run,), daemon=True).start()
            shown_run = str(self.state.get("view_run") or run)
            sample = (
                last_sample(DATA / shown_run / "observe.jsonl") if shown_run else {}
            )
            return {
                "run": shown_run,
                "event": last_sample(DATA / shown_run / "events.jsonl").get("event")
                if shown_run
                else None,
                "view": self.state.get("view"),
                "phase": self.state["phase"],
                "health": self.monitor.snapshot(self.project(), shown_run),
                "task": self.busy,
                "message": self.message,
                "history": self.history,
                "sources": [
                    {
                        "id": k,
                        "name": Path(v).name,
                        "info": cast(Document, self.state.get("info", {})).get(k),
                    }
                    for k, v in self.sources.items()
                ],
                "members": self.state["members"],
                "fleet": self.vehicles,
                "stream": {
                    k: sample.get(k)
                    for k in ("ack", "archived", "visible", "error", "t_ms")
                },
            }

    def project(self) -> str:
        if self.state["phase"] == "Viewing":
            run = str(self.state["view_run"])
            for entry in self.history:
                if entry["run"] == run and entry["project"]:
                    return str(entry["project"])
            raise ValueError("Historical project unavailable.")
        return PROJECT

    def sign_in(self, run: object) -> str:
        with self.lock:
            if (
                self.busy in {"start", "view", "close", "stop"}
                or self.state["phase"] not in {"Running", "Completed", "Viewing"}
                or run != (self.state.get("view_run") or self.state["run"])
            ):
                raise ValueError("Open a running session or a historical view first.")
            project = self.project()
        try:
            return viewer_cookie(project)
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError("Grafana sign-in unavailable.") from error

    def poll(self, run: str) -> None:
        try:
            result = execute("status", "--run-id", run)
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            result = {"error": str(exc), "vehicles": []}
        with self.lock:
            if self.state["run"] == run and self.state["phase"] in {
                "Running",
                "Completed",
            }:
                self.vehicles = result
            self.sampled = time.monotonic()
            self.polling = False

    def submit(self, action: str, key: str) -> None:
        allowed = {
            "start": {"Idle", "Stopped"},
            "add": {"Running"},
            "pause": {"Running"},
            "resume": {"Running"},
            "remove": {"Running"},
            "complete": {"Running"},
            "verify": {"Completed"},
            "stop": {"Starting", "Running", "Completed"},
            "view": {"Idle", "Stopped"},
            "close": {"Viewing"},
        }
        with self.lock:
            if self.busy:
                raise ValueError("An operation is already running.")
            if action == "view" and not any(
                row["run"] == key and row["project"] for row in self.history
            ):
                raise ValueError("Original run project is unavailable.")
            if action not in {"browse", "inspect"} and self.state[
                "phase"
            ] not in allowed.get(action, set()):
                raise ValueError("Operation unavailable in this session state.")
            members = cast(dict[str, str], self.state["members"])
            if (
                action in {"inspect", "add", "pause", "resume", "remove"}
                and key not in self.sources
            ):
                raise ValueError("Select a recording first.")
            if action in {"pause", "resume", "remove"} and key not in members:
                raise ValueError("Recording is not in this session.")
            if action == "add" and key in members:
                raise ValueError("Recording already joined this session.")
            self.busy, self.message = action, ""
            threading.Thread(
                target=self.perform, args=(action, key), daemon=False
            ).start()

    def perform(self, action: str, key: str) -> None:
        try:
            if action == "browse":
                selected = choose_file()
                if selected:
                    path = Path(selected).resolve(strict=True)
                    if path.suffix.lower() != ".ulg" or not path.is_file():
                        raise ValueError("Choose a ULog file.")
                    with self.lock:
                        if str(path) not in self.sources.values():
                            self.sources[secrets.token_hex(5)] = str(path)
            elif action == "inspect":
                info = plan(Path(self.sources[key])).summary()
                with self.lock:
                    cast(Document, self.state.setdefault("info", {}))[key] = info
            elif action in {"view", "close"}:
                run = key if action == "view" else str(self.state["view_run"])
                project = original_project(
                    DATA / run, document(DATA / run / "ops.json")
                )
                if not project:
                    raise ValueError("Original project unknown.")
                if action == "view":
                    require_free_ports()
                try:
                    result = execute(
                        action, run, module="panel_history", project=project
                    )
                finally:
                    if (DATA / run / "panel-view.active").exists():
                        with self.lock:
                            self.state.update(phase="Viewing", view_run=run)
                            self.save()
                with self.lock:
                    self.state["view"] = result.get("dashboard")
                    if action == "close":
                        self.state.update(
                            phase="Stopped" if self.state["run"] else "Idle",
                            view_run="",
                        )
            else:
                self.operation(action, key)
            with self.lock:
                self.save()
                self.message = action.capitalize() + " finished."
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            with self.lock:
                self.message = f"{action.capitalize()} failed: {exc}"
        finally:
            with self.lock:
                self.busy = ""
                self.sampled = self.history_at = 0

    def operation(self, action: str, key: str) -> None:
        if action == "start":
            require_free_ports()
            if not (PLUGIN / "plugin.json").is_file() or not any(
                PACKAGES.glob("pymavlink-2.4.50.dist-info")
            ):
                raise ValueError(
                    "Prepare the live packages and Grafana plugin (operations runbook)."
                )
            daemon = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                timeout=25,
            )
            if daemon.returncode:
                raise ValueError("Start Docker Desktop and wait for the engine.")
            with self.lock:
                self.state.update(
                    run=datetime.now(UTC).strftime("panel-%Y%m%d-%H%M%S"),
                    phase="Starting",
                    members={},
                )
                self.vehicles = {}
                self.save()
        run = str(self.state["run"])
        if (
            action == "stop"
            and self.state["phase"] == "Starting"
            and not (DATA / run / "ops.json").exists()
        ):
            with self.lock:
                self.state["phase"] = "Stopped"
            return
        args = [action, "--run-id", run]
        if action in {"add", "pause", "resume", "remove"}:
            args.extend(["--file", self.sources[key]])
        result = execute(*args)
        with self.lock:
            if action == "add":
                cast(Document, self.state["members"])[key] = result["vehicle"]
                cast(Document, self.state.setdefault("info", {}))[key] = result["plan"]
            if action in {"start", "complete", "stop"}:
                self.state["phase"] = {
                    "start": "Running",
                    "complete": "Completed",
                    "stop": "Stopped",
                }[action]
            if action == "stop":
                self.vehicles = {}


def require_free_ports() -> None:
    for port in (13003, 18082):
        with socket.socket() as sock:
            sock.settimeout(0.3)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise ValueError(f"Port {port} is already in use.")


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self) -> None:
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Handler(BaseHTTPRequestHandler):
    console: Console

    def reply(
        self, status: int, body: bytes, mime: str, cookie: str | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; frame-src http://127.0.0.1:13003; "
            "frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.headers.get("Host") != URL.split("//")[1]:
            self.send_error(403)
            return
        if self.path == "/api/state":
            self.reply(
                200, json.dumps(self.console.snapshot()).encode(), "application/json"
            )
            return
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/panel.js": ("panel.js", "text/javascript"),
            "/services.js": ("services.js", "text/javascript"),
            "/panel.css": ("panel.css", "text/css"),
        }
        if self.path not in assets:
            self.send_error(404)
            return
        name, mime = assets[self.path]
        self.reply(
            200,
            (ASSETS / name).read_bytes().replace(b"__PANEL_TOKEN__", TOKEN.encode()),
            mime,
        )

    def do_POST(self) -> None:
        if (
            self.path not in {"/api/action", "/api/grafana-session"}
            or self.headers.get("Origin") != URL
            or self.headers.get("Host") != URL.split("//")[1]
            or self.headers.get("X-Panel-Token") != TOKEN
        ):
            self.send_error(403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 4096:
                raise ValueError("Invalid request size.")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Invalid request.")
            if self.path == "/api/grafana-session":
                self.reply(
                    200,
                    b"{}",
                    "application/json",
                    self.console.sign_in(data.get("run")),
                )
                return
            self.console.submit(str(data.get("action", "")), str(data.get("id", "")))
            self.reply(202, b"{}", "application/json")
        except ValueError as exc:
            self.reply(
                409, json.dumps({"error": str(exc)}).encode(), "application/json"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pick", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    if args.pick:
        from tkinter import Tk, filedialog

        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        print(
            json.dumps(
                filedialog.askopenfilename(
                    parent=root, filetypes=[("PX4 flight logs", "*.ulg")]
                )
            )
        )
        root.destroy()
        return
    try:
        server = LocalServer(("127.0.0.1", 18765), Handler)
    except OSError:
        if args.open:
            with urlopen(URL, timeout=3) as response:
                if b'name="panel-token"' in response.read(8192):
                    webbrowser.open(URL)
                    return
        raise
    with server:
        Handler.console = Console()
        if args.open:
            webbrowser.open(URL)
        server.serve_forever()


if __name__ == "__main__":
    main()
