"""Resource admission, protected inventory, and joined memory sampling."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

PYTHON = (
    "/home/ivan/.local/share/fleet-telemetry/pyflink/"
    "m3-compatibility-002/venv/bin/python"
)
KAFKA_IMAGE = "sha256:676a930ab90762c2c32ef79642ad2293c18e5cea96381fc72af54e51fb3cd1c3"


def require(condition: object, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def obj(value: object) -> dict[str, object]:
    require(isinstance(value, dict), "expected_object")
    result = cast(dict[object, object], value)
    require(all(isinstance(k, str) for k in result), "expected_string_keys")
    return cast(dict[str, object], result)


def array(value: object) -> list[object]:
    require(isinstance(value, list), "expected_array")
    return cast(list[object], value)


def integer(value: object) -> int:
    require(type(value) is int, "expected_integer")
    return cast(int, value)


def text(value: object) -> str:
    require(isinstance(value, str), "expected_string")
    return cast(str, value)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class ResourceRuntime(Protocol):
    source: Path
    evidence: Path
    project: str
    phase: str
    samples: list[dict[str, object]]
    stop_sampler: threading.Event
    sampler: threading.Thread | None
    sampler_error: BaseException | None

    def command(
        self, args: Sequence[str], *, timeout: float = 30, check: bool = True
    ) -> str: ...
    def json_command(self, args: Sequence[str]) -> object: ...
    def dc(self, *args: str) -> str: ...
    def container(self, service: str) -> str: ...
    def log(self, kind: str, data: object) -> None: ...
    def inventory(self) -> list[object]: ...
    def sample(self) -> None: ...


class MemorySampler:
    def __init__(self, runtime: ResourceRuntime) -> None:
        self.runtime = runtime

    def sample(self) -> None:
        code = """import pathlib,os,json,time
r=pathlib.Path('/sys/fs/cgroup'); out={}
for n in ('memory.current','memory.peak','memory.max','memory.events'):
 out[n]= (r/n).read_text().strip()
pids=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid(): continue
 try:
  status=(p/'status').read_text()
  cmd=(p/'cmdline').read_bytes().decode(errors='replace')
  argv0=cmd.split('\\x00',1)[0]; name=pathlib.Path(argv0).name
  kind='java' if name=='java' else 'python' if name.startswith('python') else None
  if kind is None: continue
  vals={x.split(':')[0]:x.split(':')[1].strip()
        for x in status.splitlines() if ':' in x}
  pids.append({'pid':int(p.name),'cmd':cmd,'kind':kind,'argv0':argv0,'rss':vals.get('VmRSS'),'hwm':vals.get('VmHWM')})
 except (FileNotFoundError,ProcessLookupError): pass
out['processes']=pids; print(json.dumps(out))"""
        for service in ("jobmanager", "taskmanager"):
            cid = self.runtime.container(service)
            raw = self.runtime.command(["docker", "exec", cid, PYTHON, "-c", code])
            row = {
                "container": cid,
                "service": service,
                "phase": self.runtime.phase,
                "monotonic": time.monotonic(),
                **obj(json.loads(raw)),
            }
            self.runtime.samples.append(row)
            self.runtime.log("memory", row)

    def sampling(self) -> None:
        def loop() -> None:
            try:
                while not self.runtime.stop_sampler.wait(1):
                    self.runtime.sample()
            except (
                RuntimeError,
                OSError,
                ValueError,
                KeyError,
                subprocess.SubprocessError,
            ) as error:
                self.runtime.sampler_error = error

        self.runtime.sampler = threading.Thread(target=loop, daemon=True)
        self.runtime.sampler.start()

    def pause_sampling(self) -> None:
        self.runtime.stop_sampler.set()
        if self.runtime.sampler:
            self.runtime.sampler.join(60)
            require(not self.runtime.sampler.is_alive(), "sampler_stop_deadline")
        self.runtime.sampler = None
        self.runtime.stop_sampler.clear()
        require(self.runtime.sampler_error is None, "sampler_failure")


def inventory(runtime: ResourceRuntime) -> list[object]:
    names = (
        "fleet-kafka-440-probe-kafka-1",
        "fleet-m3-checkpoint-kafka-1",
        "fleet-fixture-policy-001-kafka-1",
    )
    rows = array(runtime.json_command(["docker", "inspect", *names]))
    require(len(rows) == len(names), "protected_inventory_missing")
    result: list[object] = []
    for name, value in zip(names, rows, strict=True):
        row = obj(value)
        state = obj(row["State"])
        require(
            row["Name"] == "/" + name
            and state["Status"] == "exited"
            and state["Running"] is False,
            "protected_container_not_stopped",
        )
        result.append(
            {key: row[key] for key in ("Name", "Id", "Image", "Mounts")}
            | {"State.Status": state["Status"]}
        )
    return result


def preflight(runtime: ResourceRuntime) -> list[object]:
    context = runtime.command(["docker", "context", "show"]).strip()
    require(context in {"default", "desktop-linux"}, "remote_context")
    contexts = array(runtime.json_command(["docker", "context", "inspect", context]))
    host = text(obj(obj(obj(contexts[0])["Endpoints"])["docker"])["Host"])
    require(host.startswith(("npipe://", "unix://")), "remote_context_endpoint")
    old = runtime.inventory()
    runtime.log("historical_before", old)
    containers = runtime.command(["docker", "ps", "-a", "--format", "{{json .}}"])
    for line in text(containers).splitlines():
        row = obj(json.loads(line))
        require("19092" not in text(row.get("Ports", "")), "published_broker_exists")
        require(
            runtime.project not in text(row.get("Names", "")),
            "project_container_exists",
        )
    volumes = runtime.command(
        [
            "docker",
            "volume",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={runtime.project}",
            "-q",
        ]
    )
    require(not volumes.strip(), "project_volume_exists")
    config = obj(
        json.loads(runtime.dc("--profile", "submit", "config", "--format", "json"))
    )
    services = obj(config["services"])
    require(
        set(services) == {"kafka", "jobmanager", "taskmanager", "submit"},
        "unexpected_compose_services",
    )
    for name, service in services.items():
        spec = obj(service)
        require(not spec.get("privileged"), "privileged_service")
        require(not spec.get("external_links"), "external_links")
        require(
            not spec.get("container_name") and not spec.get("network_mode"),
            "unscoped_service",
        )
        image = text(spec["image"])
        inspected = array(runtime.json_command(["docker", "image", "inspect", image]))
        runtime.log("image", inspected)
        if name == "kafka":
            require(obj(inspected[0])["Id"] == KAFKA_IMAGE, "kafka_image_id")
        for mount in array(spec.get("volumes", [])):
            m = obj(mount)
            if m.get("type") == "bind":
                require(
                    Path(text(m["source"])).resolve() == runtime.source
                    and m.get("read_only") is True,
                    "unsafe_bind",
                )
            else:
                require(m.get("type") == "volume", "unsafe_mount")
    for volume in obj(config.get("volumes", {})).values():
        v = obj(volume)
        require(
            not v.get("external")
            and not v.get("driver_opts")
            and text(v["name"]).startswith(runtime.project + "_"),
            "external_volume",
        )
        require(
            not runtime.command(
                [
                    "docker",
                    "volume",
                    "ls",
                    "--filter",
                    "name=^" + text(v["name"]) + "$",
                    "-q",
                ]
            ).strip(),
            "existing_named_volume",
        )
    for network in obj(config.get("networks", {})).values():
        n = obj(network)
        require(
            not n.get("external") and text(n["name"]).startswith(runtime.project + "_"),
            "external_network",
        )
    runtime.log("compose_config", config)
    runtime.log(
        "docker_info",
        runtime.json_command(["docker", "info", "--format", "{{json .}}"]),
    )
    runtime.log(
        "source_hashes",
        {
            str(p.relative_to(runtime.source)): digest(p.read_bytes())
            for p in runtime.source.rglob("*")
            if p.is_file() and p.suffix in {".py", ".yml", ".toml", ".lock"}
        },
    )
    return old


def storage(runtime: ResourceRuntime) -> None:
    require(
        shutil.disk_usage(runtime.evidence).free >= 1536 * 1024**2,
        "evidence_device_space",
    )
    cid = runtime.container("kafka")
    inspected = obj(array(runtime.json_command(["docker", "inspect", cid]))[0])
    mounts = [
        obj(v) for v in array(inspected["Mounts"]) if obj(v).get("Type") == "volume"
    ]
    require(len(mounts) == 1, "broker_volume_placement_unknown")
    mount = mounts[0]
    path = text(mount["Destination"])
    require(path.startswith("/") and ".." not in path.split("/"), "broker_mount_scope")
    allocated = runtime.command(["docker", "exec", cid, "du", "-sk", path]).split()
    filesystem = runtime.command(
        ["docker", "exec", cid, "df", "-Pk", path]
    ).splitlines()
    require(len(allocated) >= 2 and len(filesystem) == 2, "storage_observation_unknown")
    used = int(allocated[0]) * 1024
    free = int(filesystem[1].split()[3]) * 1024
    require(
        used + 512 * 1024**2 <= 50 * 1024**3 and free >= 1536 * 1024**2,
        "storage_admission",
    )
    runtime.log(
        "storage_admission",
        {
            "volume": mount,
            "allocated": used,
            "broker_free": free,
            "evidence_device": str(runtime.evidence.anchor),
            "evidence_free": shutil.disk_usage(runtime.evidence).free,
        },
    )
