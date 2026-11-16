"""Save one run's operational evidence before history or rotation discards it.

`collect` writes a new directory `<run>/evidence/<UTC stamp>-<label>/` with:

- `snapshot.json`: the operations status snapshot at collection time;
- `flink.json`: the Flink overview and, per job of the run, its details,
  checkpoint statistics and exception history (the JobManager keeps these in
  memory only);
- `logs/`: every container log of the profile and the run's observers, with
  each container's state and log configuration (Docker rotates logs at
  5 MiB x 2 files);
- `kafka.txt` and `kafka.json`: topic descriptions, topic and broker
  configuration, end offsets and the run's consumer groups;
- `progress-files.json` and `volume-inventory.json`: the run's progress files,
  and path, size and SHA-256 of every file of the run in the evidence and
  state volumes;
- `lineage.json` and `working.patch`: code revision, working-tree patch and
  untracked files with hashes, image references and IDs, and versions;
- `manifest.json`: declared scope, actual progress and completion. A run
  without `serving-complete.json` is `partial`, with its actual interval;
- `inventory.json`: path, size and SHA-256 of every file in the run directory
  (this collection included) plus the volume entries.

Raw data and coordinates are never copied into the reports: captures, ledgers,
outputs, bundles and configurations appear only as path, size and hash.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import time
from pathlib import Path
from typing import cast
from urllib.error import URLError

from runtime.recording.profile import (
    PROJECT,
    ROOT,
    WORKER_IMAGE,
    Document,
    Profile,
)

KAFKA_BIN = "/opt/kafka/bin"


def write(path: Path, document: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=1, sort_keys=True) + "\n")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def probe(run: Profile, *args: str, network: bool) -> Document:
    """Run the read-only status module in a short-lived worker container."""
    if network:
        archive = run.inspect(run.container("archive"))
        if not cast(Document, archive["State"]).get("Running"):
            return {"status": "failed", "category": "archive_not_running"}
        where = ["--network", f"container:{archive['Id']}"]
    else:
        where = ["--network", "none"]
    output = run.docker(
        *("run", "--rm", "--read-only", "--user", "10001:10001"),
        *("--entrypoint", "python", *where),
        *("-v", f"{ROOT.as_posix()}:/workspace:ro"),
        *("-v", f"{run.private.resolve().as_posix()}:/private:ro"),
        *("-v", f"{PROJECT}_evidence:/evidence:ro"),
        *("-v", f"{PROJECT}_state:/state:ro"),
        *(WORKER_IMAGE, "-P", "-m", "runtime.continuous.recording_status"),
        *args,
        timeout=600,
        check=False,
    )
    lines = [line for line in output.splitlines() if line.startswith("{")]
    if not lines:
        return {"status": "failed", "category": "no_output"}
    return cast(Document, json.loads(lines[-1]))


def containers(run: Profile) -> list[str]:
    """Service containers of the run's compose profiles and its observers."""
    names = run.docker("ps", "-a", "--format", "{{.Names}}").split()
    selected = {
        run.container(service)
        for service in run.docker(*run.compose, "config", "--services").split()
    }
    services = [n for n in names if n in selected]
    observers = [n for n in names if n.startswith(f"f09-observer-{run.run_id}")]
    return sorted(services) + sorted(observers)


def flink_history(run: Profile) -> Document:
    try:
        overview = run.rest("/overview")
        jobs: list[Document] = []
        for row in run.jobs():
            jid = str(row["jid"])
            detail = run.rest(f"/jobs/{jid}")
            jobs.append(
                {
                    "jid": jid,
                    "state": detail.get("state"),
                    "start_time": detail.get("start-time"),
                    "end_time": detail.get("end-time"),
                    "vertices": [
                        {k: v.get(k) for k in ("name", "status", "parallelism")}
                        for v in cast(list[Document], detail.get("vertices", []))
                    ],
                    "checkpoints": run.rest(f"/jobs/{jid}/checkpoints"),
                    "exceptions": run.rest(f"/jobs/{jid}/exceptions"),
                }
            )
    except (URLError, OSError, ValueError):
        return {
            "error": "flink_rest_unreachable",
            "note": "job, checkpoint and exception history lives in JobManager memory",
        }
    return {"overview": overview, "jobs": jobs}


def save_logs(run: Profile, directory: Path) -> list[Document]:
    directory.mkdir()
    rows: list[Document] = []
    for name in containers(run):
        result = subprocess.run(
            ["docker", "logs", "--timestamps", name],
            capture_output=True,
            timeout=300,
            cwd=ROOT,
        )
        (directory / f"{name}.stdout.log").write_bytes(result.stdout)
        (directory / f"{name}.stderr.log").write_bytes(result.stderr)
        detail = run.inspect(name)
        state = cast(Document, detail["State"])
        rows.append(
            {
                "container": name,
                "image": cast(Document, detail["Config"]).get("Image"),
                "image_id": detail.get("Image"),
                "restart_count": detail.get("RestartCount"),
                "state": {
                    k: state.get(k)
                    for k in ("Status", "ExitCode", "OOMKilled", "StartedAt")
                }
                | {"FinishedAt": state.get("FinishedAt")},
                "log_config": cast(Document, detail["HostConfig"]).get("LogConfig"),
            }
        )
    return rows


def save_kafka(run: Profile, directory: Path) -> Document:
    if run.state("kafka").get("Status") != "running":
        return {"error": "broker_not_running"}
    topics = [f"telemetry.{run.run_id}.{w}.v1" for w in ("input", "output")]
    server = "--bootstrap-server kafka:9092"
    script = "\n".join(
        [
            f"echo '## groups'; {KAFKA_BIN}/kafka-consumer-groups.sh {server} --list",
            f"echo '## broker config'; {KAFKA_BIN}/kafka-configs.sh {server} "
            "--describe --entity-type brokers --entity-name 1 --all",
            *(
                f"echo '## topic {t}'; {KAFKA_BIN}/kafka-topics.sh {server} "
                f"--describe --topic {t}; {KAFKA_BIN}/kafka-configs.sh {server} "
                f"--describe --entity-type topics --entity-name {t} --all; "
                f"echo '## offsets {t}'; {KAFKA_BIN}/kafka-get-offsets.sh {server} "
                f"--topic {t}"
                for t in topics
            ),
            f"for g in $({KAFKA_BIN}/kafka-consumer-groups.sh {server} --list "
            f"| grep '^{run.run_id}-'); do echo \"## group $g\"; "
            f"{KAFKA_BIN}/kafka-consumer-groups.sh {server} --describe "
            '--group "$g"; done',
        ]
    )
    text = run.docker(
        "exec", run.container("kafka"), "sh", "-c", script, timeout=300, check=False
    )
    (directory / "kafka.txt").write_text(text, encoding="utf-8", newline="\n")
    ends: dict[str, dict[str, int]] = {}
    for topic in topics:
        for match in re.finditer(rf"^{re.escape(topic)}:(\d+):(\d+)$", text, re.M):
            ends.setdefault(topic, {})[match[1]] = int(match[2])
    retention = sorted(set(re.findall(r"retention\.(?:ms|bytes)=-?\d+", text)))
    return {"end_offsets": ends, "retention_settings_seen": retention}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


def lineage(run: Profile, directory: Path, logs: list[Document]) -> Document:
    patch = git("diff", "HEAD")
    (directory / "working.patch").write_text(patch, encoding="utf-8", newline="\n")
    untracked = [
        {"path": name, "sha256": digest(ROOT / name)}
        for name in git("ls-files", "--others", "--exclude-standard").splitlines()
        if (ROOT / name).is_file()
    ]
    images = {
        str(row["image_id"]): run.docker(
            "image",
            "inspect",
            "--format",
            "{{json .RepoDigests}}",
            str(row["image_id"]),
        ).strip()
        for row in logs
    }
    criterion = run.out / "criterion.json"
    return {
        "code_revision": git("rev-parse", "HEAD").strip(),
        "working_tree_clean": not git("status", "--porcelain").strip(),
        "working_patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "untracked_files": untracked,
        "criterion_sha256": digest(criterion) if criterion.exists() else None,
        "containers": [
            {k: row[k] for k in ("container", "image", "image_id")} for row in logs
        ],
        "image_repo_digests": images,
        "versions": {
            "docker_server": run.docker(
                "version", "--format", "{{.Server.Version}}"
            ).strip(),
            "docker_compose": run.docker("compose", "version", "--short").strip(),
            "host_python": platform.python_version(),
            "host_platform": platform.platform(),
        },
    }


def actual_interval(run: Profile, progress: Document, snapshot: Document) -> Document:
    """Progress from the volume's files, which stay readable while stopped."""
    producer = cast(Document, progress.get("producer-status.json") or {})
    gateway = cast(Document, progress.get("gateway-status.json") or {})
    archive = cast(Document, progress.get("archive-status.json") or {})
    serving = cast(Document, progress.get("serving-status.json") or {})
    sent = producer.get("acknowledged", gateway.get("published"))
    out: Document = {
        "source_status": producer.get("status", gateway.get("status")),
        "acknowledged_deliveries": sent,
        "archived_prefix": archive.get("input_next"),
        "serving_logical_facts": serving.get("logical_facts"),
        "input_end_offset": cast(
            Document, cast(Document, snapshot.get("inside") or {}).get("kafka") or {}
        ).get("input_end"),
    }
    if gateway:
        out["note"] = "gateway counts are per epoch; the input end offset is the total"
    events = run.out / "bundle" / "events.jsonl"
    if events.exists() and isinstance(sent, int) and sent > 0:
        lines = events.read_bytes().splitlines()
        first = json.loads(lines[0])["native_timestamp_us"]
        last = json.loads(lines[min(sent, len(lines)) - 1])["native_timestamp_us"]
        out["acknowledged_native_time_us"] = [first, last]
    return out


def manifest(
    run: Profile, label: str, snapshot: Document, progress: Document
) -> Document:
    complete = "serving-complete.json" in progress
    ops = run.out / "ops.json"
    return {
        "run_id": run.run_id,
        "label": label,
        "collected_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared": json.loads(ops.read_text()) if ops.exists() else None,
        "completion": "completed" if complete else "partial",
        "completion_basis": "serving-complete.json "
        + ("present" if complete else "absent: a partial run, not a completed one"),
        "actual": actual_interval(run, progress, snapshot),
        "sql": cast(Document, snapshot.get("inside") or {}).get("sql"),
        "progress_files_present": sorted(progress),
    }


def file_inventory(run: Profile, skip: Path) -> list[Document]:
    rows: list[Document] = []
    for path in sorted(run.out.rglob("*")):
        if path.is_file() and not path.is_symlink() and path != skip:
            rows.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
    return rows


def collect(run: Profile, label: str, snapshot: Document) -> Document:
    """Write one evidence collection; return its directory and inventory hash."""
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    directory = run.out / "evidence" / f"{stamp}-{label}"
    directory.mkdir(parents=True)
    write(directory / "snapshot.json", snapshot)
    write(directory / "flink.json", flink_history(run))
    logs = save_logs(run, directory / "logs")
    write(directory / "containers.json", logs)
    write(directory / "kafka.json", save_kafka(run, directory))
    volume = probe(run, "inventory", "--run-id", run.run_id, network=False)
    progress = cast(Document, volume.get("progress_files") or {})
    write(directory / "progress-files.json", progress)
    entries = cast(list[Document], volume.get("files") or [])
    write(
        directory / "volume-inventory.json",
        {"status": volume.get("status"), "files": entries},
    )
    write(directory / "lineage.json", lineage(run, directory, logs))
    document = manifest(run, label, snapshot, progress)
    write(directory / "manifest.json", document)
    target = directory / "inventory.json"
    files = file_inventory(run, target) + entries
    write(
        target,
        {
            "run_id": run.run_id,
            "collection": directory.name,
            "volume_inventory": volume.get("status"),
            "files": files,
        },
    )
    result: Document = {
        "directory": directory.relative_to(ROOT).as_posix(),
        "inventory_sha256": digest(target),
        "files": len(files),
        "completion": document["completion"],
    }
    run.log("evidence_collected", **result)
    return result
