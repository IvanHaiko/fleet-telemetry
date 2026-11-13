"""Offline split topology invariants; no clients, Docker or running services."""

import hashlib
import json
from pathlib import Path

import pytest

from runtime.continuous.prepare_split import prepare
from telemetry.continuous_connection import parse_connection


def properties(path: Path) -> dict[str, str]:
    return dict(line.split("=", 1) for line in path.read_text().splitlines())


def test_split_is_portable_shared_quorum_with_host_failure_domains(
    tmp_path: Path,
) -> None:
    target = tmp_path / "split"
    prepare(target, "192.168.50.10", "192.168.50.20", "fleet-split-test")
    manifest = json.loads((target / "manifest.json").read_text())
    client = parse_connection(
        json.loads((target / "client-connection.example.json").read_text())
    )
    assert client is not None
    assert ",".join(client.endpoints) == manifest["bootstrap"]
    controllers: set[str] = set()
    clusters: set[str] = set()
    nodes: set[int] = set()
    for host, expected in (("pc", {1, 2, 4}), ("laptop", {3, 5, 6})):
        recipe = json.loads((target / host / "compose.json").read_text())
        assert set(recipe["services"]) == {f"kafka-{node}" for node in expected}
        for node in expected:
            service = recipe["services"][f"kafka-{node}"]
            config = properties(target / host / f"node-{node}.properties")
            nodes.add(node)
            controllers.add(service["environment"]["KAFKA_INITIAL_CONTROLLERS"])
            clusters.add(service["environment"]["KAFKA_CLUSTER_ID"])
            assert config["broker.rack"] == host
            assert config["advertised.listeners"] == (
                f"LAN://{manifest['hosts'][host]}:{19091 + node}"
                + (
                    f",CONTROLLER://{manifest['hosts'][host]}:{19190 + node}"
                    if node <= 3
                    else ""
                )
            )
            assert config["controller.quorum.bootstrap.servers"] == (
                "192.168.50.10:19191,192.168.50.10:19192,192.168.50.20:19193"
            )
            assert config["listener.security.protocol.map"] == "LAN:SSL,CONTROLLER:SSL"
            assert config["ssl.client.auth"] == "required"
            assert config["ssl.endpoint.identification.algorithm"] == "https"
            assert "${file:" in config["ssl.keystore.password"]
            assert (
                "CONTROLLER://" in config["listeners"]
                if node <= 3
                else ("CONTROLLER://" not in config["listeners"])
            )
            assert config["min.insync.replicas"] == "2"
            assert config["default.replication.factor"] == "2"
            assert service["pull_policy"] == "never"
            binds = [v for v in service["volumes"] if v["type"] == "bind"]
            assert all(v["bind"]["create_host_path"] is False for v in binds)
            assert all(str(tmp_path) not in v["source"] for v in binds)
        assert b"\r" not in (target / host / "start.sh").read_bytes()
    assert nodes == set(range(1, 7))
    assert len(controllers) == len(clusters) == 1
    assert clusters == {manifest["cluster_id"]}
    assert len(next(iter(controllers)).split(",")) == 3
    for name, expected_hash in manifest["files"].items():
        assert hashlib.sha256((target / name).read_bytes()).hexdigest() == expected_hash
    before = (target / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        prepare(target, "192.168.50.10", "192.168.50.20", "fleet-split-test")
    assert (target / "manifest.json").read_bytes() == before


@pytest.mark.parametrize(
    ("pc", "laptop", "project"),
    [
        ("127.0.0.1", "192.168.50.20", "fleet-split-test"),
        ("0.0.0.0", "192.168.50.20", "fleet-split-test"),
        ("8.8.8.8", "192.168.50.20", "fleet-split-test"),
        ("192.168.50.10", "192.168.50.10", "fleet-split-test"),
        ("192.168.50.10", "192.168.50.20", "fleet-live-001"),
    ],
)
def test_invalid_plan_creates_nothing(
    tmp_path: Path, pc: str, laptop: str, project: str
) -> None:
    target = tmp_path / "refused"
    with pytest.raises(ValueError):
        prepare(target, pc, laptop, project)
    assert not target.exists()
