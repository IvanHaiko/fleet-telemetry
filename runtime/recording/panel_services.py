"""Bounded, project-scoped checks and viewer sign-in for the local panel."""

import json
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie

from runtime.recording.profile import Document

COOKIE = "fleet_panel_grafana"
VIEWER = "fleet_panel_viewer"
SERVICES = ("kafka", "jobmanager", "archive", "serving", "grafana")


class Monitor:
    """Sample outside the HTTP thread and discard samples from a previous view."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.scope = ("", "")
        self.result: Document = {}
        self.next_check = 0.0
        self.busy = False

    def snapshot(self, project: str, run: str) -> Document:
        scope = (project, run)
        with self.lock:
            if scope != self.scope:
                self.scope, self.result, self.next_check = scope, {}, 0
            if not self.busy and time.monotonic() >= self.next_check:
                self.busy = True
                threading.Thread(target=self.sample, args=(scope,), daemon=True).start()
            return self.result

    def sample(self, scope: tuple[str, str]) -> None:
        try:
            result = health(scope[0])
        except (OSError, subprocess.SubprocessError, ValueError):
            result = {"at": time.time(), "error": "Docker unavailable", "services": {}}
        with self.lock:
            if self.scope == scope:
                self.result, self.next_check = result, time.monotonic() + 8
            self.busy = False


def docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=8,
        encoding="utf-8",
        errors="replace",
    )


def probe(name: str, container: str, status: str, sql: str | None) -> Document:
    if name == "kafka":
        if "(healthy)" in status:
            return {"state": "Live", "detail": "Broker lists topics"}
        return {
            "state": "Starting" if "starting" in status else "Unhealthy",
            "detail": status,
        }
    if name == "jobmanager":
        response = docker(
            "exec",
            container,
            "python",
            "-c",
            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8081/overview',timeout=3).read().decode())",
        )
        if response.returncode == 0:
            overview = json.loads(response.stdout)
            jobs = overview["jobs-running"]
            return {
                "state": "Live",
                "jobs": jobs,
                "detail": f"{jobs} running · {overview['taskmanagers']} TaskManagers",
            }
    elif name == "grafana":
        response = docker(
            "exec",
            container,
            "curl",
            "-fsS",
            "--max-time",
            "3",
            "http://127.0.0.1:3000/api/health",
        )
        if (
            response.returncode == 0
            and json.loads(response.stdout).get("database") == "ok"
        ):
            return {"state": "Live", "detail": "Database ready"}
    elif name == "archive":
        if not sql:
            return {"state": "Unknown", "detail": "S3 probe namespace unavailable"}
        # The SQL container shares the archive's loopback network namespace.
        response = docker(
            "exec",
            sql,
            "wget",
            "--tries=1",
            "--timeout=3",
            "-S",
            "-O",
            "/dev/null",
            "http://127.0.0.1:8333/",
        )
        if response.returncode == 0 or re.search(
            r"HTTP/1\.[01] 403\b", response.stderr
        ):
            return {"state": "Live", "detail": "S3 endpoint responds"}
    else:
        response = docker(
            "exec",
            container,
            "wget",
            "--tries=1",
            "--timeout=3",
            "-qO-",
            "http://127.0.0.1:8123/ping",
        )
        if response.returncode == 0 and response.stdout.strip() == "Ok.":
            return {"state": "Live", "detail": "HTTP ping OK"}
    return {"state": "Unhealthy", "detail": "Endpoint did not confirm readiness"}


def health(project: str) -> Document:
    command = docker(
        "ps",
        "-a",
        "--filter",
        f"label=com.docker.compose.project={project}",
        "--filter",
        "label=com.docker.compose.oneoff=False",
        "--format",
        '{{.Label "com.docker.compose.service"}}\t{{.ID}}\t{{.State}}\t{{.Status}}',
    )
    if command.returncode:
        raise ValueError("Docker unavailable")
    containers = {}
    for line in command.stdout.splitlines():
        service, cid, state, status = line.split("\t", 3)
        containers[service] = (cid, state, status)
    rows: Document = {}
    sql, state, _ = containers.get("serving", ("", "", ""))
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = {}
        for service in SERVICES:
            cid, state_now, status = containers.get(service, ("", "stopped", ""))
            if state_now == "running":
                probes[service] = pool.submit(
                    probe, service, cid, status, sql if state == "running" else None
                )
            else:
                rows[service] = {
                    "state": state_now.capitalize(),
                    "detail": "Container status",
                }
        for service, task in probes.items():
            try:
                rows[service] = task.result()
            except (OSError, subprocess.SubprocessError, ValueError, KeyError):
                rows[service] = {"state": "Unknown", "detail": "Probe unavailable"}
    return {"services": rows, "at": time.time()}


def viewer_cookie(project: str) -> str:
    # Trust only the Compose Grafana container that publishes this exact port.
    found = docker(
        "ps",
        "-q",
        "--filter",
        f"label=com.docker.compose.project={project}",
        "--filter",
        "label=com.docker.compose.service=grafana",
    )
    cid = found.stdout.strip()
    if found.returncode or not re.fullmatch("[0-9a-f]{12,64}", cid):
        raise ValueError("Grafana is unavailable.")
    binding = docker("port", cid, "3000/tcp")
    if binding.returncode or binding.stdout.strip() != "127.0.0.1:13003":
        raise ValueError("Grafana binding differs from this panel.")
    # The trusted request originates on loopback inside Grafana. Browsers use
    # its ordinary HttpOnly session cookie; never log the response headers.
    args = (
        "exec",
        cid,
        "curl",
        "-fsS",
        "--max-time",
        "4",
        "-H",
        f"X-Fleet-Panel-Viewer: {VIEWER}",
    )
    user = docker(*args, "http://127.0.0.1:3000/api/user")
    orgs = docker(*args, "http://127.0.0.1:3000/api/user/orgs")
    if user.returncode or orgs.returncode:
        raise ValueError("Viewer sign-in is unavailable.")
    account = json.loads(user.stdout)
    memberships = json.loads(orgs.stdout)
    if (
        account.get("login") != VIEWER
        or account.get("isGrafanaAdmin") is not False
        or not memberships
        or any(m.get("role") != "Viewer" for m in memberships)
    ):
        raise ValueError("Viewer role could not be confirmed.")
    result = docker(*args, "-D", "-", "-o", "/dev/null", "http://127.0.0.1:3000/login")
    if not result.returncode:
        for line in result.stdout.splitlines():
            if line.lower().startswith("set-cookie:"):
                cookies = SimpleCookie()
                cookies.load(line.partition(":")[2].strip())
                if COOKIE in cookies and re.fullmatch(
                    "[0-9a-zA-Z_-]{16,256}", cookies[COOKIE].value
                ):
                    value = cookies[COOKIE].value
                    return f"{COOKIE}={value}; Path=/; HttpOnly; SameSite=Strict"
    raise ValueError("Grafana did not issue a viewer session.")
