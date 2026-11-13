"""Prepare a fresh six-broker local profile without starting services."""

import argparse
import base64
import json
import secrets
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KAFKA = (
    "fleet-telemetry/kafka-probe:4.4.0@sha256:"
    "676a930ab90762c2c32ef79642ad2293c18e5cea96381fc72af54e51fb3cd1c3"
)
FLINK = (
    "fleet-telemetry/pyflink-m3:2.2.1-local2@sha256:"
    "9cd317885a161473064ad7628d807f87c688bff0d3d7335bf8e2c7b5cfd77956"
)
CH = (
    "clickhouse/clickhouse-server:26.8.34.13@sha256:"
    "ed334fbfae35c4f9fa328534821280b59d1c4677df8f3cf0e950cf7501a25bde"
)


def identifier() -> str:
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")


def prepare(target: Path, source: Path) -> None:
    """Create an isolated topology, credentials and shared quorum bootstrap set."""
    target = target.resolve()
    source = source.resolve(strict=True)
    target.mkdir(exist_ok=False)
    cluster = identifier()
    controllers = ",".join(f"{i}@kafka-{i}:9093:{identifier()}" for i in range(1, 4))
    services: dict[str, object] = {}
    volumes: dict[str, object] = {}
    common: dict[str, object] = {
        "platform": "linux/amd64",
        "pull_policy": "never",
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "logging": {
            "driver": "json-file",
            "options": {"max-size": "5m", "max-file": "2"},
        },
        "stop_grace_period": "30s",
        "pids_limit": 256,
    }
    for i in range(1, 7):
        config = {
            "process.roles": "broker,controller" if i <= 3 else "broker",
            "node.id": i,
            "controller.quorum.bootstrap.servers": (
                "kafka-1:9093,kafka-2:9093,kafka-3:9093"
            ),
            "controller.listener.names": "CONTROLLER",
            "listeners": "INTERNAL://0.0.0.0:9092,HOST://0.0.0.0:19092"
            + (",CONTROLLER://0.0.0.0:9093" if i <= 3 else ""),
            "advertised.listeners": (
                f"INTERNAL://kafka-{i}:9092,HOST://127.0.0.1:{19091 + i}"
            ),
            "listener.security.protocol.map": (
                "INTERNAL:PLAINTEXT,HOST:PLAINTEXT,CONTROLLER:PLAINTEXT"
            ),
            "inter.broker.listener.name": "INTERNAL",
            "log.dirs": "/var/lib/kafka/data",
            "auto.create.topics.enable": "false",
            "num.partitions": 18,
            "default.replication.factor": 2,
            "min.insync.replicas": 2,
            "offsets.topic.replication.factor": 3,
            "offsets.topic.num.partitions": 18,
            "transaction.state.log.replication.factor": 3,
            "transaction.state.log.min.isr": 2,
            "transaction.state.log.num.partitions": 18,
            "group.initial.rebalance.delay.ms": 0,
            "log.retention.ms": -1,
            "log.retention.bytes": -1,
            "log.segment.bytes": 16777216,
            "num.network.threads": 3,
            "num.io.threads": 4,
        }
        path = target / f"node-{i}.properties"
        path.write_text(
            "".join(f"{k}={v}\n" for k, v in config.items()), encoding="utf8"
        )
        volume = f"broker-{i}-data"
        volumes[volume] = {}
        services[f"kafka-{i}"] = {
            **common,
            "image": KAFKA,
            "user": "10001:10001",
            "mem_limit": "1536m",
            "cpus": 1,
            "entrypoint": ["/bin/bash", "/run/kafka/start.sh"],
            "environment": {
                "KAFKA_CLUSTER_ID": cluster,
                "KAFKA_NODE_ID": str(i),
                "KAFKA_INITIAL_CONTROLLERS": controllers,
            },
            "ports": [f"127.0.0.1:{19091 + i}:19092"],
            "volumes": [
                f"{volume}:/var/lib/kafka/data",
                f"{path}:/run/kafka/node.properties:ro",
                f"{ROOT / 'runtime/kafka/continuous-start.sh'}:/run/kafka/start.sh:ro",
            ],
            "tmpfs": ["/tmp:rw,nosuid,size=128m"],
        }
    for role, memory in (("jobmanager", "1536m"), ("taskmanager", "4g")):
        services[role] = {
            **common,
            "image": FLINK,
            "user": "10001:10001",
            "mem_limit": memory,
            "pids_limit": 1024 if role == "taskmanager" else 512,
            "cpus": 1 if role == "jobmanager" else 3,
            "command": [role],
            "volumes": ["state:/state", f"{source}:/workspace:ro"],
            "tmpfs": ["/tmp:rw,nosuid,size=256m"],
            **({"ports": ["127.0.0.1:18081:8081"]} if role == "jobmanager" else {}),
        }
    password = secrets.token_hex(32)
    services["serving"] = {
        **common,
        "image": CH,
        "user": "101:101",
        "mem_limit": "2g",
        "cpus": 1,
        "environment": {
            "CLICKHOUSE_USER": "bootstrap",
            "CLICKHOUSE_PASSWORD": password,
            "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT": "1",
        },
        "ports": ["127.0.0.1:18130:8123"],
        "volumes": [
            "serving-data:/var/lib/clickhouse",
            f"{ROOT / 'runtime/clickhouse/limits.xml'}:"
            "/etc/clickhouse-server/config.d/limits.xml:ro",
        ],
        "tmpfs": [
            "/var/log/clickhouse-server:rw,noexec,nosuid,size=32m,uid=101,gid=101",
            "/etc/clickhouse-server/users.d:rw,noexec,nosuid,size=1m,uid=101,gid=101",
            "/tmp:rw,noexec,nosuid,size=64m,uid=101,gid=101",
        ],
    }
    for name in ("state", "serving-data"):
        volumes[name] = {}
    # The existing storage recipe is combined separately to preserve its pins.
    compose = {
        "services": services,
        "volumes": volumes,
        "networks": {
            "default": {"ipam": {"config": [{"subnet": "10.254.243.0/27"}]}},
            "archive-private": {"ipam": {"config": [{"subnet": "10.254.243.32/28"}]}},
        },
    }
    (target / "compose.json").write_text(json.dumps(compose, indent=2) + "\n")
    private = {
        "cluster_id": cluster,
        "bootstrap": ",".join(f"127.0.0.1:{p}" for p in range(19092, 19098)),
        "serving_bootstrap": password,
        "writer": secrets.token_hex(32),
        "reader": secrets.token_hex(32),
        "s3": {
            r: {
                "access_key": secrets.token_hex(12),
                "secret_key": secrets.token_hex(24),
            }
            for r in ("bootstrap", "writer", "reader")
        },
    }
    (target / "private.json").write_text(json.dumps(private, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.directory, args.source)
