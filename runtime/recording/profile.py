"""Host-side access to one run of the single-machine recording profile.

Wraps the Docker CLI, the Flink REST API on its loopback port and the run's
state files, which it reads through the run's observer container. Start,
status and stop are separate methods so that an operations command can reuse
them; stop never removes a volume. Diagnostics from failed Docker commands go
to the run's restricted directory, and raised errors carry fixed categories
only, never paths, credentials or measurement data.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fleet-recording-local"
REST = "http://127.0.0.1:18082"
WORKER_IMAGE = "fleet-telemetry/recording-worker:0.1.0"
SERVICES = ("kafka", "jobmanager", "taskmanager", "archive", "serving")
WORKERS = ("archive-worker", "serving-worker", "publisher")

type Document = dict[str, object]


class RunFailure(RuntimeError):
    """A run step failed; the message is a fixed category, never private data."""


def require(value: object, reason: str) -> None:
    if not value:
        raise RunFailure(reason)


def worker_json(text: str) -> Document:
    """Parse the last JSON document a worker module printed."""
    start = text.rfind("\n{")
    return cast(Document, json.loads(text[start + 1 :] if start >= 0 else text))


@dataclass
class Profile:
    run_id: str
    out: Path
    private: Path
    paused: set[str] = field(default_factory=set)

    @property
    def compose(self) -> list[str]:
        return [
            "compose",
            "-f",
            str(ROOT / "compose/recording.yml"),
            "--env-file",
            str(self.private / "compose.env"),
            "--profile",
            "run",
        ]

    @property
    def observer(self) -> str:
        return f"f09-observer-{self.run_id}"

    @staticmethod
    def container(service: str) -> str:
        return f"{PROJECT}-{service}-1"

    def log(self, event: str, **data: object) -> None:
        row = {"host_ms": time.time_ns() // 1_000_000, "event": event, **data}
        line = json.dumps(row, sort_keys=True)
        with (self.out / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line, flush=True)

    def docker(self, *args: str, timeout: float = 300, check: bool = True) -> str:
        result = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT
        )
        if check and result.returncode != 0:
            with (self.out / "docker-errors.log").open("a", encoding="utf-8") as log:
                stamp = time.time_ns() // 1_000_000
                log.write(f"{stamp} {args[:3]}\n{result.stderr[-4000:]}\n")
            raise RunFailure("docker_" + "_".join(a for a in args[:2] if a.isalpha()))
        return result.stdout

    def worker(self, module: str, *args: str, timeout: float = 600) -> Document:
        """Run one worker module in the initializer container; parse its JSON."""
        output = self.docker(
            *self.compose,
            *"run --rm -T --no-deps initialize".split(),
            "runtime.continuous." + module,
            *"--private /private --evidence /evidence".split(),
            *args,
            timeout=timeout,
            check=False,
        )
        try:
            document = worker_json(output)
        except ValueError:
            document = {"status": "failed", "category": "no_output"}
        if document.get("status") == "failed":
            raise RunFailure(f"{module}_{document.get('category')}")
        return document

    def inspect(self, name: str) -> Document:
        return cast(Document, json.loads(self.docker("inspect", name))[0])

    def state(self, service: str) -> Document:
        return cast(Document, self.inspect(self.container(service))["State"])

    def read_state(self, name: str) -> tuple[int, Document | None]:
        """Observer-clock time and one run state file, read through the observer."""
        raw = self.docker(
            *("exec", self.observer, "sh", "-c"),
            'date +%s%3N; cat "$1" 2>/dev/null || true',
            *("sh", f"/evidence/{self.run_id}/state/{name}"),
            timeout=30,
        )
        first, _, rest = raw.partition("\n")
        try:
            document = json.loads(rest) if rest.strip() else None
        except ValueError:
            document = None  # a status file replaced mid-read; read again later
        return int(first), document

    def clock(self) -> int:
        return self.read_state("producer-status.json")[0]

    @staticmethod
    def rest(path: str, method: str = "GET") -> Document:
        with urlopen(Request(REST + path, method=method), timeout=10) as response:
            body = response.read(4_194_305)
        require(len(body) <= 4_194_304, "rest_limit")
        return cast(Document, json.loads(body or b"{}"))

    def jobs(self) -> list[Document]:
        name = "bounded-recording-" + self.run_id
        rows = cast(list[Document], self.rest("/jobs/overview")["jobs"])
        return [row for row in rows if row.get("name") == name]

    def running_job(self) -> str:
        running = [j for j in self.jobs() if j.get("state") == "RUNNING"]
        require(len(running) == 1, "flink_job_not_running")
        return str(running[0]["jid"])

    def checkpoint(self, job: str, which: str) -> Document | None:
        """The latest `completed` or `restored` checkpoint summary of a job."""
        latest = cast(Document, self.rest(f"/jobs/{job}/checkpoints")["latest"])
        return cast(Document | None, latest.get(which))

    def job_running(self, job: str) -> bool:
        try:
            detail = self.rest(f"/jobs/{job}")
        except (URLError, OSError, ValueError):
            return False
        vertices = cast(list[Document], detail.get("vertices", []))
        return detail.get("state") == "RUNNING" and all(
            v.get("status") == "RUNNING" for v in vertices
        )

    @staticmethod
    def wait(probe: Callable[[], object], seconds: float, reason: str) -> object:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            value = probe()
            if value:
                return value
            time.sleep(0.5)
        raise RunFailure(reason)

    def processing_offset(self) -> int | None:
        """Committed offset of the Flink source group, written on checkpoints."""
        text = self.docker(
            *(
                "exec",
                self.container("kafka"),
                "/opt/kafka/bin/kafka-consumer-groups.sh",
            ),
            *("--bootstrap-server", "kafka:9092", "--describe"),
            *("--group", self.run_id + "-processing"),
            timeout=60,
            check=False,
        )
        topic = f"telemetry.{self.run_id}.input.v1"
        for line in text.splitlines():
            cells = line.split()
            if len(cells) >= 4 and cells[1] == topic and cells[2] == "0":
                return int(cells[3]) if cells[3].isdigit() else None
        return None

    def start(self) -> None:
        """Start the long-running services and wait until each one answers."""
        self.docker(*self.compose, "up", "-d", *SERVICES)
        probe = (
            "import urllib.request,urllib.error\n"
            "for u in ('http://127.0.0.1:8123/ping','http://127.0.0.1:8333/'):\n"
            "  try: urllib.request.urlopen(u, timeout=3)\n"
            "  except urllib.error.HTTPError: pass\n"
        )

        def ready() -> bool:
            health = cast(Document, self.state("kafka").get("Health", {}))
            if health.get("Status") != "healthy":
                return False
            try:
                if cast(int, self.rest("/overview").get("slots-available", 0)) < 1:
                    return False
            except (URLError, OSError, ValueError):
                return False
            storage = subprocess.run(
                [
                    "docker",
                    *self.compose,
                    *"run --rm -T --no-deps --entrypoint python initialize -c".split(),
                    probe,
                ],
                capture_output=True,
                timeout=120,
                cwd=ROOT,
            )
            return storage.returncode == 0

        self.wait(ready, 240, "profile_not_ready")
        self.log("profile_ready")

    def status(self) -> Document:
        rows = self.docker(
            *("ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}"),
            *("--format", "{{.Names}}\t{{.State}}"),
        )
        try:
            jobs = [{"jid": j["jid"], "state": j["state"]} for j in self.jobs()]
        except (URLError, OSError, ValueError):
            jobs = []
        containers = dict(line.split("\t", 1) for line in rows.splitlines() if line)
        return {"containers": containers, "jobs": jobs}

    def stop(self) -> None:
        """Cancel this run's job and stop the containers; every volume is kept."""
        try:
            for job in self.jobs():
                if job.get("state") == "RUNNING":
                    self.rest(f"/jobs/{job['jid']}?mode=cancel", "PATCH")
        except (URLError, OSError, ValueError):
            pass
        self.docker("stop", self.observer, check=False)
        self.docker(*self.compose, "stop", timeout=600)
        self.log("profile_stopped")
