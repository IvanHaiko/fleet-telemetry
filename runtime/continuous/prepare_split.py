"""Render a fresh two-host Kafka candidate offline; never contact Docker or Kafka."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
from pathlib import Path

from runtime.continuous.prepare import CH, FLINK, KAFKA, ROOT, identifier
from runtime.continuous.split_runtime import S3, runtime_recipes


def lan_address(value: str) -> str:
    """Require an explicit RFC1918 address rather than a wildcard or loopback."""
    address = ipaddress.IPv4Address(value)
    ranges = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    if not any(address in ipaddress.IPv4Network(network) for network in ranges):
        raise ValueError("split_requires_rfc1918_ipv4")
    return str(address)


def prepare(target: Path, pc: str, laptop: str, project: str) -> None:
    """Write portable host recipes with one shared quorum and independent disks."""
    pc, laptop = lan_address(pc), lan_address(laptop)
    if pc == laptop:
        raise ValueError("split_hosts_must_differ")
    if not re.fullmatch(r"fleet-split-[a-z0-9][a-z0-9-]{0,31}", project):
        raise ValueError("split_requires_fresh_project_prefix")
    # IDs 1 and 2 are PC controllers; ID 3 is the laptop controller. The existing
    # storage launcher intentionally assigns controller roles to IDs <= 3.
    owners = {1: "pc", 2: "pc", 3: "laptop", 4: "pc", 5: "laptop", 6: "laptop"}
    addresses = {"pc": pc, "laptop": laptop}
    endpoints = {i: f"{addresses[owners[i]]}:{19091 + i}" for i in owners}
    quorum = ",".join(f"{addresses[owners[i]]}:{19190 + i}" for i in (1, 2, 3))
    controllers = ",".join(
        f"{i}@{addresses[owners[i]]}:{19190 + i}:{identifier()}" for i in (1, 2, 3)
    )
    cluster = identifier()
    target = target.resolve()
    target.mkdir(exist_ok=False)
    launcher = (ROOT / "runtime/kafka/continuous-start.sh").read_text(encoding="utf8")
    for host in ("pc", "laptop"):
        directory = target / host
        directory.mkdir()
        (directory / "start.sh").write_text(launcher, encoding="utf8", newline="\n")
        services: dict[str, object] = {}
        volumes: dict[str, object] = {}
        for node, owner in owners.items():
            if owner != host:
                continue
            controller = node <= 3
            tls = "/run/secrets/kafka-tls"
            password = "${file:" + tls + "/passwords.properties:password}"
            config: dict[str, object] = {
                "process.roles": "broker,controller" if controller else "broker",
                "node.id": node,
                "broker.rack": host,
                "controller.quorum.bootstrap.servers": quorum,
                "controller.listener.names": "CONTROLLER",
                "listeners": "LAN://0.0.0.0:9092"
                + (",CONTROLLER://0.0.0.0:9093" if controller else ""),
                "advertised.listeners": f"LAN://{endpoints[node]}"
                + (
                    f",CONTROLLER://{addresses[host]}:{19190 + node}"
                    if controller
                    else ""
                ),
                "listener.security.protocol.map": "LAN:SSL,CONTROLLER:SSL",
                "inter.broker.listener.name": "LAN",
                "ssl.client.auth": "required",
                "ssl.endpoint.identification.algorithm": "https",
                "ssl.keystore.type": "PKCS12",
                "ssl.keystore.location": tls + "/kafka.p12",
                "ssl.keystore.password": password,
                "ssl.key.password": password,
                "ssl.truststore.type": "PKCS12",
                "ssl.truststore.location": tls + "/ca.p12",
                "ssl.truststore.password": password,
                "config.providers": "file",
                "config.providers.file.class": (
                    "org.apache.kafka.common.config.provider.FileConfigProvider"
                ),
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
                "log.retention.ms": -1,
                "log.retention.bytes": -1,
                "log.segment.bytes": 16777216,
                "num.network.threads": 3,
                "num.io.threads": 4,
            }
            (directory / f"node-{node}.properties").write_text(
                "".join(f"{key}={value}\n" for key, value in config.items()),
                encoding="utf8",
                newline="\n",
            )
            volume = f"broker-{node}-data"
            volumes[volume] = {}
            ports = [f"{addresses[host]}:{19091 + node}:9092"]
            if controller:
                ports.append(f"{addresses[host]}:{19190 + node}:9093")
            services[f"kafka-{node}"] = {
                "image": KAFKA,
                "platform": "linux/amd64",
                "pull_policy": "never",
                "user": "10001:10001",
                "entrypoint": ["/bin/bash", "/run/kafka/start.sh"],
                "environment": {
                    "KAFKA_CLUSTER_ID": cluster,
                    "KAFKA_NODE_ID": str(node),
                    "KAFKA_INITIAL_CONTROLLERS": controllers,
                },
                "ports": ports,
                "volumes": [
                    {
                        "type": "volume",
                        "source": volume,
                        "target": "/var/lib/kafka/data",
                    },
                    {
                        "type": "bind",
                        "source": f"./node-{node}.properties",
                        "target": "/run/kafka/node.properties",
                        "read_only": True,
                        "bind": {"create_host_path": False},
                    },
                    {
                        "type": "bind",
                        "source": "./start.sh",
                        "target": "/run/kafka/start.sh",
                        "read_only": True,
                        "bind": {"create_host_path": False},
                    },
                    {
                        "type": "bind",
                        "source": "${KAFKA_TLS_DIR:?Set absolute host TLS directory}"
                        + f"/node-{node}",
                        "target": tls,
                        "read_only": True,
                        "bind": {"create_host_path": False},
                    },
                ],
                "tmpfs": ["/tmp:rw,nosuid,size=128m"],
                "read_only": True,
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "mem_limit": "1536m",
                "cpus": 1,
                "pids_limit": 256,
                "stop_grace_period": "30s",
                "logging": {
                    "driver": "json-file",
                    "options": {"max-size": "5m", "max-file": "2"},
                },
            }
        (directory / "compose.json").write_text(
            json.dumps(
                {
                    "name": project + "-" + host,
                    "services": services,
                    "volumes": volumes,
                },
                indent=2,
            )
            + "\n",
            encoding="utf8",
        )
    runtime_recipes(target, project)
    client = {
        "format_version": "two-host-kafka-client-v1",
        "endpoints": list(endpoints.values()),
        "native_tls": {
            "ca_file": "/private/role/ca.pem",
            "certificate_file": "/private/role/client.pem",
            "key_file": "/private/role/client.key",
        },
        "flink_tls": {
            "truststore_file": "/run/secrets/flink/ca.p12",
            "keystore_file": "/run/secrets/flink/client.p12",
            "password_file": "/run/secrets/flink/passwords.properties",
        },
    }
    (target / "client-connection.example.json").write_text(
        json.dumps(client, indent=2) + "\n", encoding="utf8"
    )
    manifest = {
        "status": "offline-candidate-not-admitted",
        "project": project,
        "run_id": project.removeprefix("fleet-"),
        "cluster_id": cluster,
        "initial_controllers": controllers,
        "bootstrap": ",".join(endpoints.values()),
        "hosts": addresses,
        "owners": owners,
        "image": KAFKA,
        "images": {"pc": [KAFKA, S3, CH], "laptop": [KAFKA, FLINK]},
        "files": {
            path.relative_to(target).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(target.rglob("*"))
            if path.is_file()
        },
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pc-ip", required=True)
    parser.add_argument("--laptop-ip", required=True)
    parser.add_argument("--project", required=True)
    options = parser.parse_args()
    prepare(options.directory, options.pc_ip, options.laptop_ip, options.project)
