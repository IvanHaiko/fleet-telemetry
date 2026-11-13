"""Scoped Docker/REST control and retained observations for the parent harness."""

from __future__ import annotations

import http.client
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import BinaryIO, cast

from m3_resources import (
    PYTHON,
    MemorySampler,
    array,
    digest,
    integer,
    inventory,
    obj,
    preflight,
    require,
    text,
)

__all__ = ["Runtime", "array", "digest", "integer", "obj", "require", "text"]


class Runtime:
    """Every mutation is explicitly scoped to one fresh Compose project."""

    def __init__(self, source: Path, evidence: Path, project: str) -> None:
        require(re.fullmatch(r"fleet-m3-final-[0-9]+", project), "project_scope")
        require(not os.environ.get("DOCKER_HOST"), "docker_host_override")
        require(not os.environ.get("DOCKER_CONTEXT"), "docker_context_override")
        self.source = source.resolve(strict=True)
        self.compose = self.source / "compose" / "m3.yml"
        require(self.compose.is_file(), "missing_compose")
        evidence.mkdir(parents=False, exist_ok=False)
        self.evidence = evidence.resolve()
        self.project = project
        self.env = {**os.environ, "M3_SOURCE_ROOT": str(self.source)}
        self.lock = threading.Lock()
        self.clients: list[tuple[subprocess.Popen[bytes], BinaryIO, BinaryIO]] = []
        self.client_names: list[str] = []
        self.client_tags: dict[str, subprocess.Popen[bytes]] = {}
        self.owned = False
        self.started = time.monotonic()
        self.lane_deadline = self.started + 360
        self.phase = "preflight"
        self.samples: list[dict[str, object]] = []
        self.stop_sampler = threading.Event()
        self.sampler: threading.Thread | None = None
        self.sampler_error: BaseException | None = None
        self._memory_sampler = MemorySampler(self)

    def log(self, kind: str, data: object) -> None:
        with (
            self.lock,
            (self.evidence / "operations.jsonl").open("a", encoding="utf8") as f,
        ):
            f.write(
                json.dumps(
                    {
                        "monotonic": time.monotonic(),
                        "phase": self.phase,
                        "kind": kind,
                        "data": data,
                    },
                    allow_nan=False,
                )
                + "\n"
            )

    def command(
        self, args: Sequence[str], *, timeout: float = 30, check: bool = True
    ) -> str:
        argv = list(args)
        remaining = self.lane_deadline - time.monotonic()
        require(remaining > 0, "whole_lane_deadline")
        timeout = min(timeout, remaining)
        try:
            result = subprocess.run(
                argv, env=self.env, capture_output=True, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired as error:
            self.log(
                "command_timeout",
                {
                    "argv": argv,
                    "stdout": (error.stdout or b"").decode("utf8", "replace"),
                    "stderr": (error.stderr or b"").decode("utf8", "replace"),
                },
            )
            raise RuntimeError("command_deadline") from error
        out = result.stdout.decode("utf8", "replace")
        self.log(
            "command",
            {
                "argv": argv,
                "exit": result.returncode,
                "stdout": out,
                "stderr": result.stderr.decode("utf8", "replace"),
            },
        )
        require(not check or result.returncode == 0, "command_failed")
        return out

    def dc(self, *args: str) -> str:
        return self.command(
            ["docker", "compose", "-p", self.project, "-f", str(self.compose), *args],
            timeout=60,
        )

    def json_command(self, args: Sequence[str]) -> object:
        return cast(object, json.loads(self.command(args)))

    def inventory(self) -> list[object]:
        return inventory(self)

    def preflight(self) -> list[object]:
        return preflight(self)

    def start(self) -> None:
        self.owned = True
        self.dc(
            "up",
            "-d",
            "--no-build",
            "--pull",
            "never",
            "kafka",
            "jobmanager",
            "taskmanager",
        )
        self.wait(self.ready, "rest_ready")

    def ready(self) -> object:
        try:
            return self.rest("/overview")
        except urllib.error.HTTPError as error:
            if error.code != 503:
                raise
            return None
        except (
            urllib.error.URLError,
            http.client.RemoteDisconnected,
            ConnectionError,
            TimeoutError,
        ) as error:
            self.log("readiness_transport_retry", {"error": repr(error)})
            return None

    def container(self, service: str) -> str:
        require(service in {"kafka", "jobmanager", "taskmanager"}, "service_scope")
        cid = self.dc("ps", "-q", service).strip()
        require(bool(re.fullmatch("[a-f0-9]{12,64}", cid)), "missing_owned_container")
        return cid

    def execute(
        self, service: str, code: str, *args: str, user: str | None = None
    ) -> str:
        command = ["docker", "exec"]
        if user:
            command += ["-u", user]
        return self.command(
            [*command, self.container(service), PYTHON, "-c", code, *args]
        )

    def control(self, path: str) -> object | None:
        require(path.startswith("/state/"), "control_scope")
        raw = self.execute(
            "jobmanager",
            "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
            'print(p.read_text() if p.exists() else "null")',
            path,
        )
        require(len(raw.encode()) <= 1048576, "control_size")
        value: object = json.loads(raw)
        self.log("control", {"path": path, "value": value})
        return value

    def lines(self, path: str) -> list[object]:
        require(path.startswith("/state/"), "trace_scope")
        raw = self.execute(
            "jobmanager",
            "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
            "assert p.stat().st_size<=1048576; print(p.read_text())",
            path,
        )
        return [
            cast(object, json.loads(line)) for line in raw.splitlines() if line.strip()
        ]

    def rest(self, path: str, body: object | None = None) -> object:
        require(bool(re.fullmatch(r"/[a-zA-Z0-9/_-]*", path)), "rest_path")
        request = urllib.request.Request(
            "http://127.0.0.1:18081" + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read(1048577)
                self.log(
                    "rest",
                    {
                        "path": path,
                        "body": body,
                        "status": response.status,
                        "raw": raw.decode("utf8", "replace"),
                    },
                )
                require(len(raw) <= 1048576, "rest_body_bound")
                return cast(object, json.loads(raw))
        except urllib.error.HTTPError as error:
            self.log(
                "rest_error",
                {
                    "path": path,
                    "status": error.code,
                    "raw": error.read(1048577).decode("utf8", "replace"),
                },
            )
            raise

    def wait(
        self, probe: Callable[[], object], reason: str, seconds: float = 60
    ) -> object:
        end = min(time.monotonic() + seconds, self.lane_deadline)
        while time.monotonic() < end:
            if self.sampler_error:
                raise RuntimeError("memory_sampling_failed") from self.sampler_error
            value = probe()
            if value:
                return value
            time.sleep(0.1)
        raise RuntimeError(reason + "_deadline")

    def begin_lane(self, phase: str) -> None:
        self.phase = phase
        self.lane_deadline = time.monotonic() + 360

    def manifest(self, tag: str, value: dict[str, object]) -> str:
        destination = "/state/inputs/" + tag + ".json"
        self.execute(
            "jobmanager",
            'import pathlib; pathlib.Path("/state/inputs").mkdir('
            "parents=True,exist_ok=True)",
            user="10001",
        )
        host = self.evidence / (tag + "-manifest.json")
        with host.open("x", encoding="utf8") as file:
            json.dump(value, file, sort_keys=True, allow_nan=False)
        self.log("manifest", {"path": str(host), "sha256": digest(host.read_bytes())})
        self.command(
            [
                "docker",
                "cp",
                str(host),
                self.container("jobmanager") + ":" + destination,
            ]
        )
        return destination

    def submit(
        self, tag: str, job: str, args: Sequence[str], restore: str | None = None
    ) -> None:
        require(job in {"partition_job.py", "persistent_job.py"}, "job_scope")
        require(bool(re.fullmatch("[a-z0-9_-]+", tag)), "client_tag")
        argv = [
            "docker",
            "compose",
            "-p",
            self.project,
            "-f",
            str(self.compose),
            "run",
            "--name",
            self.project + "-client-" + tag,
            "--no-deps",
            "--pull",
            "never",
            "submit",
            "submit",
        ]
        if restore:
            require(restore.startswith("file:///state/checkpoints/"), "restore_scope")
            help_text = self.execute(
                "jobmanager",
                'import os,subprocess; cmd=[os.environ["FLINK_HOME"]+'
                '"/bin/flink","run","--help"]; '
                "r=subprocess.run(cmd,capture_output=True,text=True,timeout=10); "
                "print(r.stdout); print(r.stderr); assert r.returncode==0",
            )
            self.log("restore_cli_help", help_text)
            argv += ["-s", restore]
            if "--claimMode" in help_text:
                require("no_claim" in help_text, "restore_claim_mode_unknown")
                argv += ["--claimMode", "no_claim"]
        argv += ["-py", "/workspace/runtime/pyflink/" + job, *args]
        stdout = (self.evidence / (tag + ".stdout")).open("xb")
        stderr = (self.evidence / (tag + ".stderr")).open("xb")
        try:
            child = subprocess.Popen(argv, env=self.env, stdout=stdout, stderr=stderr)
        except BaseException:
            stdout.close()
            stderr.close()
            raise
        self.clients.append((child, stdout, stderr))
        self.client_tags[tag] = child
        self.client_names.append(self.project + "-client-" + tag)
        self.log("popen", {"argv": argv, "pid": child.pid})

    def finished(self, control: str, tag: str | None = None) -> str:
        suffix = "-" + tag if tag else ""

        def ready_probe() -> object:
            child = self.clients[-1][0]
            require(child.poll() in (None, 0), "submission_client_failed")
            return self.control(control + "/ready" + suffix + ".json")

        ready = obj(self.wait(ready_probe, "job_ready"))
        job_id = text(ready["job_id"])
        require(bool(re.fullmatch("[a-f0-9]{32}", job_id)), "job_id")
        return job_id

    def await_finished(self, control: str, job: str, tag: str | None = None) -> None:
        suffix = "-" + tag if tag else ""
        receipt = obj(
            self.wait(
                lambda: self.control(control + "/finished" + suffix + ".json"),
                "job_finished",
                120,
            )
        )
        require(
            receipt.get("status") == "FINISHED" and receipt.get("job_id") == job,
            "invalid_finished_receipt",
        )
        self.wait(
            lambda: obj(self.rest("/jobs/" + job)).get("state") == "FINISHED",
            "rest_finished",
            120,
        )

    def client_exit(self, tag: str, *, interrupted: bool = False) -> None:
        child = self.client_tags[tag]
        result = child.wait(timeout=60)
        self.log(
            "client_result",
            {"tag": tag, "exit": result, "expected_interrupted": interrupted},
        )
        require(result != 0 if interrupted else result == 0, "unexpected_client_exit")

    def checkpoint_inventory(
        self, lane: str | None = None, *, retain: bool = False
    ) -> dict[str, object]:
        require(
            lane is None or lane in {"taskmanager_sigkill", "runtime_restart"},
            "retention_lane",
        )
        code = """import pathlib,hashlib,json,sys,shutil
source=pathlib.Path('/state/checkpoints'); lane=sys.argv[1]; retain=sys.argv[2]=='True'
root=pathlib.Path('/state/retained')/lane if lane else source
def inventory(base):
 files=list(base.rglob('*')); assert len(files)<=512
 assert not any(p.is_symlink() for p in files)
 files=[p for p in files if p.is_file()]
 assert 0<len(files)<=128 and sum(p.stat().st_size for p in files)<=268435456
 return {str(p.relative_to(base)):{'size':p.stat().st_size,
 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
if retain:
 before=inventory(source); root.parent.mkdir(exist_ok=True)
 shutil.copytree(source,root); assert inventory(source)==before==inventory(root)
rows=inventory(root)
print(json.dumps({str(source/k):v for k,v in rows.items()},sort_keys=True))"""
        result = obj(
            json.loads(self.execute("jobmanager", code, lane or "", str(retain)))
        )
        self.log(
            "checkpoint_inventory",
            {
                "lane": lane,
                "independent_copy": bool(lane),
                "retained_now": retain,
                "files": result,
            },
        )
        return result

    def sample(self) -> None:
        self._memory_sampler.sample()

    def sampling(self) -> None:
        self._memory_sampler.sampling()

    def pause_sampling(self) -> None:
        self._memory_sampler.pause_sampling()

    def stop_services(self) -> None:
        try:
            self.dc("stop", "--timeout", "20")
        finally:
            for name in self.client_names:
                self.command(["docker", "stop", "--time", "20", name], check=False)

    def close(self) -> None:
        self.phase = "cleanup"
        self.lane_deadline = float("inf")
        self.stop_sampler.set()
        if self.sampler:
            self.sampler.join(60)
        try:
            try:
                require(
                    self.sampler is None or not self.sampler.is_alive(),
                    "sampler_stop_deadline",
                )
            finally:
                if self.owned:
                    self.stop_services()
                    ids = self.dc("ps", "-aq").split()
                    if ids:
                        rows = array(self.json_command(["docker", "inspect", *ids]))
                        self.log("owned_final_states", rows)
                        require(
                            all(not obj(obj(r)["State"])["Running"] for r in rows),
                            "owned_services_still_running",
                        )
        finally:
            for child, stdout, stderr in self.clients:
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
                self.log("client_exit", {"pid": child.pid, "exit": child.returncode})
                stdout.close()
                stderr.close()
