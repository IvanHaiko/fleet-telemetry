"""Portable processing/storage recipes for the existing pinned two-host lab."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from runtime.continuous.prepare import CH, FLINK, ROOT

S3 = (
    "fleet-telemetry/seaweed-m4:4.48-local1@sha256:"
    "460f0162e5fbcfeef1571308be4e5ddb457cb74f35e50e50434902b4549c4097"
)


def bind(source: str, target: str) -> dict[str, object]:
    """Refuse missing configuration instead of creating empty bind directories."""
    return {
        "type": "bind",
        "source": source,
        "target": target,
        "read_only": True,
        "bind": {"create_host_path": False},
    }


def write_json(path: Path, value: object) -> None:
    """Write configuration with portable newlines and no implicit overwrite."""
    with path.open("x", encoding="utf8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def runtime_recipes(target: Path, project: str) -> None:
    """Add same-project overlays; leave the six-broker base recipes unchanged."""
    common: dict[str, object] = {
        "platform": "linux/amd64",
        "pull_policy": "never",
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "stop_grace_period": "30s",
        "logging": {
            "driver": "json-file",
            "options": {"max-size": "5m", "max-file": "2"},
        },
    }
    for host in ("pc", "laptop"):
        assets = target / host / "assets"
        assets.mkdir()
    for name, relative in (
        ("limits.xml", "runtime/clickhouse/limits.xml"),
        ("master.toml", "runtime/s3/archive-master.toml"),
    ):
        shutil.copyfile(ROOT / relative, target / "pc/assets" / name)
    # Copy the admitted wrapper rather than replacing the image JVM configuration.
    for name in ("flink-entrypoint.sh", "flink-reporter.yaml"):
        text = (ROOT / "runtime/observability" / name).read_text(encoding="utf8")
        (target / "laptop/assets" / name).write_text(
            text, encoding="utf8", newline="\n"
        )
    flink: dict[str, object] = {
        **common,
        "image": FLINK,
        "user": "10001:10001",
        "entrypoint": ["/bin/bash", "/opt/observability/flink-entrypoint.sh"],
        "environment": {
            "FLEET_TASK_SLOTS": "18",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        },
        "volumes": [
            "state:/state",
            bind("${FLEET_SOURCE_ROOT:?Set source export directory}", "/workspace"),
            bind("${FLEET_JOB_DIR:?Set private processing config directory}", "/job"),
            bind("${FLEET_ADAPTER_DIR:?Set built adapter directory}", "/adapter"),
            bind(
                "${FLEET_PRIVATE_DIR:?Set host private directory}/roles/flink",
                "/run/secrets/flink",
            ),
            bind(
                "./assets/flink-entrypoint.sh", "/opt/observability/flink-entrypoint.sh"
            ),
            bind(
                "./assets/flink-reporter.yaml", "/opt/observability/flink-reporter.yaml"
            ),
        ],
        "tmpfs": ["/tmp:rw,nosuid,size=256m"],
    }
    services = {
        "jobmanager": {
            **flink,
            "command": ["jobmanager"],
            "mem_limit": "1536m",
            "cpus": 1,
            "pids_limit": 512,
            "ports": ["127.0.0.1:18081:8081"],
        },
        "taskmanager": {
            **flink,
            "command": ["taskmanager"],
            "mem_limit": "4g",
            "cpus": 6,
            "pids_limit": 4096,
            "depends_on": ["jobmanager"],
        },
        "submit": {
            **flink,
            "command": [
                "submit",
                "-py",
                "/workspace/runtime/pyflink/continuous_job.py",
                "--config",
                "/job/processing.json",
            ],
            "profiles": ["submit"],
            "mem_limit": "1536m",
            "cpus": 1,
            "pids_limit": 512,
        },
    }
    write_json(
        target / "laptop/runtime.json",
        {"name": project + "-laptop", "services": services, "volumes": {"state": {}}},
    )
    command = [
        "server",
        "-dir=/data",
        "-ip=127.0.0.1",
        "-ip.bind=127.0.0.1",
        "-master.peers=127.0.0.1:9333",
        "-master.telemetry=false",
        "-master.volumeSizeLimitMB=64",
        "-master.volumePreallocate=false",
        "-master.vacuumDeleteEmptyAfterSeconds=0",
        "-volume.max=128",
        "-volume.minFreeSpace=1GiB",
        "-volume.fileSizeLimitMB=16",
        "-filer=true",
        "-filer.maxMB=16",
        "-filer.exposeDirectoryData=false",
        "-s3=true",
        "-s3.ip.bind=0.0.0.0",
        "-s3.config=/run/secrets/s3.json",
        "-s3.iam=false",
        "-s3.autoCreateBucket=false",
        "-s3.allowDeleteBucketNotEmpty=false",
        "-s3.port.iceberg=0",
        "-s3.port.lance=0",
        "-s3.concurrentUploadLimitMB=32",
        "-s3.readerCacheSizeMB=32",
        "-webdav=false",
        "-sftp=false",
        "-iam=false",
        "-mq.broker=false",
        "-mq.agent=false",
        "-metricsPort=0",
    ]
    storage = {
        "archive": {
            **common,
            "image": S3,
            "user": "10001:10001",
            "mem_limit": "768m",
            "cpus": 1,
            "pids_limit": 128,
            "environment": {"GOMEMLIMIT": "512MiB"},
            "command": command,
            "ports": ["127.0.0.1:18336:8333"],
            "volumes": [
                "archive-data:/data",
                bind("./assets/master.toml", "/etc/seaweedfs/master.toml"),
                bind(
                    "${FLEET_PRIVATE_DIR:?Set host private directory}/s3.json",
                    "/run/secrets/s3.json",
                ),
            ],
            "tmpfs": ["/tmp:rw,noexec,nosuid,size=64m,uid=10001,gid=10001"],
            "networks": ["archive-private"],
        },
        "serving": {
            **common,
            "image": CH,
            "user": "101:101",
            "mem_limit": "2g",
            "cpus": 1,
            "pids_limit": 256,
            "environment": {
                "CLICKHOUSE_USER": "bootstrap",
                "CLICKHOUSE_PASSWORD": "${M4_SERVING_PASSWORD:?Set private password}",
                "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT": "1",
            },
            "ports": ["127.0.0.1:18130:8123"],
            "volumes": [
                "serving-data:/var/lib/clickhouse",
                bind(
                    "./assets/limits.xml", "/etc/clickhouse-server/config.d/limits.xml"
                ),
            ],
            "tmpfs": [
                "/var/log/clickhouse-server:rw,noexec,nosuid,size=32m,uid=101,gid=101",
                "/etc/clickhouse-server/users.d:rw,noexec,nosuid,size=1m,uid=101,gid=101",
                "/tmp:rw,noexec,nosuid,size=64m,uid=101,gid=101",
            ],
        },
    }
    write_json(
        target / "pc/runtime.json",
        {
            "name": project + "-pc",
            "services": storage,
            "volumes": {"archive-data": {}, "serving-data": {}},
            "networks": {"archive-private": {"driver": "bridge"}},
        },
    )
    for host in ("pc", "laptop"):
        (target / host / ".env.example").write_text(
            "# Set absolute host paths; use the WSL Docker CLI on each host.\n"
            "KAFKA_TLS_DIR=/absolute/private/" + host + "\n"
            "FLEET_PRIVATE_DIR=/absolute/private/" + host + "\n"
            "FLEET_SOURCE_ROOT=/absolute/source\n"
            "FLEET_JOB_DIR=/absolute/private/laptop/job\n"
            "FLEET_ADAPTER_DIR=/absolute/adapter\n"
            "# PC only: load M4_SERVING_PASSWORD from private pc/compose.env.\n",
            encoding="utf8",
            newline="\n",
        )
