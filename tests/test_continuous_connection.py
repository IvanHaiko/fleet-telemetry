"""Network configuration refusal and client propagation without running services."""

import copy
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest

from runtime.continuous import kafka as module
from telemetry.continuous_connection import (
    LOCAL_ENDPOINTS,
    LOCAL_FLINK_BOOTSTRAP,
    Connection,
    flink_properties,
    parse_connection,
    source_options,
)


def connection() -> dict[str, object]:
    return {
        "format_version": "two-host-kafka-client-v1",
        "endpoints": [
            f"192.168.50.{10 if node in (1, 2, 4) else 20}:{19091 + node}"
            for node in range(1, 7)
        ],
        "native_tls": {
            "ca_file": "/private/publisher/ca.pem",
            "certificate_file": "/private/publisher/client.pem",
            "key_file": "/private/publisher/client.key",
        },
        "flink_tls": {
            "truststore_file": "/run/secrets/flink/ca.p12",
            "keystore_file": "/run/secrets/flink/client.p12",
            "password_file": "/run/secrets/flink/passwords.properties",
        },
    }


def test_native_and_jvm_preserve_tls_but_use_their_own_material() -> None:
    config = connection()
    parsed = parse_connection(config)
    assert isinstance(parsed, Connection)
    native = parsed.native_properties()
    jvm = flink_properties({"kafka_connection": config})
    assert native["security.protocol"] == jvm["security.protocol"] == "SSL"
    assert native["ssl.endpoint.identification.algorithm"] == "https"
    assert jvm["ssl.endpoint.identification.algorithm"] == "https"
    assert native["enable.ssl.certificate.verification"] == "true"
    assert native["ssl.key.location"] == "/private/publisher/client.key"
    assert "ssl.key.location" not in jvm
    assert "ssl.keystore.location" not in native
    assert jvm["ssl.keystore.type"] == "PKCS12"
    secret_ref = "${file:/run/secrets/flink/passwords.properties:password}"
    assert jvm["ssl.keystore.password"] == jvm["ssl.key.password"] == secret_ref
    assert jvm["config.providers.file.param.allowed.paths"] == parsed.password_file
    assert jvm["config.providers.file.class"] == (
        "org.apache.flink.kafka.shaded.org.apache.kafka.common.config.provider."
        "FileConfigProvider"
    )
    assert "'properties.ssl.keystore.password'='" + secret_ref + "'" in source_options(
        jvm
    )
    assert flink_properties({}) == {"bootstrap.servers": LOCAL_FLINK_BOOTSTRAP}


@pytest.mark.parametrize(
    "change",
    ["missing_tls", "downgrade", "duplicate", "public", "one_host", "path", "version"],
)
def test_malformed_split_config_refuses_before_sdk_creation(change: str) -> None:
    config = copy.deepcopy(connection())
    endpoints = cast(list[str], config["endpoints"])
    if change == "missing_tls":
        del config["native_tls"]
    elif change == "downgrade":
        cast(dict[str, object], config["native_tls"])["security.protocol"] = "PLAINTEXT"
    elif change == "duplicate":
        endpoints[-1] = endpoints[0]
    elif change == "public":
        endpoints[0] = "8.8.8.8:19092"
    elif change == "one_host":
        config["endpoints"] = [f"192.168.50.10:{port}" for port in range(19092, 19098)]
    elif change == "path":
        cast(dict[str, object], config["flink_tls"])["password_file"] = "/a/'bad"
    else:
        config["format_version"] = "unknown"
    with pytest.raises(ValueError):
        # This guard runs before platform/SDK admission, also on Windows.
        module.Kafka("192.168.50.10:19092", "cluster", config)


def test_all_native_clients_share_tls_and_metadata_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = connection()
    endpoints = cast(list[str], config["endpoints"])
    sdk = MagicMock()
    admin_module = MagicMock()
    admin = admin_module.AdminClient.return_value
    cluster = SimpleNamespace(
        cluster_id="cluster",
        nodes=[
            SimpleNamespace(host=e.split(":")[0], port=int(e.split(":")[1]))
            for e in endpoints
        ],
    )
    admin.describe_cluster.return_value.result.return_value = cluster
    description = SimpleNamespace(topic_id="topic-id", partitions=list(range(18)))
    admin.describe_topics.return_value = {"topic": MagicMock()}
    admin.describe_topics.return_value["topic"].result.return_value = description
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(module, "require_uuid_boundary", lambda: None)
    monkeypatch.setattr(
        module,
        "importlib",
        SimpleNamespace(
            import_module=lambda name: (
                sdk if name == "confluent_kafka" else admin_module
            )
        ),
    )
    client = module.Kafka(",".join(endpoints), "cluster", config)
    client.consumer("group")
    client.sdk.Producer({**client.client_properties(), "acks": "all"})
    assert client.describe("topic")["topic_id"] == "topic-id"
    for call in (
        admin_module.AdminClient.call_args,
        sdk.Consumer.call_args,
        sdk.Producer.call_args,
    ):
        assert call.args[0]["security.protocol"] == "SSL"
        assert call.args[0]["ssl.ca.location"] == "/private/publisher/ca.pem"
    cluster.nodes[0].host = "192.168.50.99"
    with pytest.raises(ValueError, match="continuous_broker_endpoints"):
        client.describe("topic")
    cluster.cluster_id = "replaced"
    with pytest.raises(ValueError, match="continuous_cluster_identity"):
        client.describe("topic")
    with pytest.raises(ValueError, match="continuous_bootstrap_endpoints"):
        module.Kafka("192.168.50.99:19092", "cluster", config)
    legacy = module.Kafka(",".join(sorted(LOCAL_ENDPOINTS)), "cluster")
    assert legacy.client_properties() == {"bootstrap.servers": legacy.bootstrap}
    with pytest.raises(ValueError, match="continuous_bootstrap_endpoints"):
        module.Kafka(",".join(endpoints), "cluster")


def single_host() -> dict[str, object]:
    return {
        "format_version": "single-host-kafka-v1",
        "endpoint": "kafka:9092",
        "partitions": 12,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("endpoint", "127.0.0.1:9092"),
        ("endpoint", "kafka:80"),
        ("endpoint", "Kafka:9092"),
        ("partitions", 0),
        ("partitions", True),
        ("extra", "x"),
    ],
)
def test_single_host_connection_refuses_other_shapes(field: str, value: object) -> None:
    config = single_host()
    config[field] = value
    with pytest.raises(ValueError):
        parse_connection(config)


def test_single_broker_topology_is_enforced_without_tls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One broker and twelve partitions replace, not relax, the six-broker checks."""
    parsed = parse_connection(single_host())
    assert parsed is not None and (parsed.brokers, parsed.partitions) == (1, 12)
    assert flink_properties({"kafka_connection": single_host()}) == {
        "bootstrap.servers": "kafka:9092"
    }
    sdk, admin_module = MagicMock(), MagicMock()
    admin = admin_module.AdminClient.return_value
    cluster = SimpleNamespace(
        cluster_id="cluster", nodes=[SimpleNamespace(host="kafka", port=9092)]
    )
    admin.describe_cluster.return_value.result.return_value = cluster
    description = SimpleNamespace(topic_id="topic-id", partitions=list(range(12)))
    admin.describe_topics.return_value = {"topic": MagicMock()}
    admin.describe_topics.return_value["topic"].result.return_value = description
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(module, "require_uuid_boundary", lambda: None)
    monkeypatch.setattr(
        module,
        "importlib",
        SimpleNamespace(
            import_module=lambda name: (
                sdk if name == "confluent_kafka" else admin_module
            )
        ),
    )
    client = module.Kafka("kafka:9092", "cluster", single_host())
    assert client.client_properties() == {"bootstrap.servers": "kafka:9092"}
    assert client.describe("topic")["topic_id"] == "topic-id"
    client.create("topic")
    new_topic = admin_module.NewTopic.call_args
    assert new_topic.kwargs["num_partitions"] == 12
    assert new_topic.kwargs["replication_factor"] == 1
    assert new_topic.kwargs["config"]["min.insync.replicas"] == "1"
    description.partitions = list(range(18))
    with pytest.raises(ValueError, match="continuous_partition_count"):
        client.describe("topic")
    description.partitions = list(range(12))
    cluster.nodes.append(SimpleNamespace(host="kafka-2", port=9092))
    with pytest.raises(ValueError, match="continuous_cluster_identity"):
        client.describe("topic")
    with pytest.raises(ValueError, match="continuous_bootstrap_endpoints"):
        module.Kafka("kafka-2:9092", "cluster", single_host())


def test_create_waits_for_lagging_metadata_but_never_reuses_a_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reproduced on a fresh broker: describe right after create can fail."""
    sdk, admin_module = MagicMock(), MagicMock()
    admin = admin_module.AdminClient.return_value
    cluster = SimpleNamespace(
        cluster_id="cluster", nodes=[SimpleNamespace(host="kafka", port=9092)]
    )
    admin.describe_cluster.return_value.result.return_value = cluster
    ready = SimpleNamespace(topic_id="topic-id", partitions=list(range(12)))
    lagging = MagicMock()
    lagging.result.side_effect = [RuntimeError("unknown topic"), ready]
    admin.describe_topics.return_value = {"topic": lagging}
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(module, "require_uuid_boundary", lambda: None)
    monkeypatch.setattr("runtime.continuous.kafka.time.sleep", lambda seconds: None)
    monkeypatch.setattr(
        module,
        "importlib",
        SimpleNamespace(
            import_module=lambda name: (
                sdk if name == "confluent_kafka" else admin_module
            )
        ),
    )
    client = module.Kafka("kafka:9092", "cluster", single_host())
    assert client.create("topic")["topic_id"] == "topic-id"
    admin.create_topics.return_value = {"topic": MagicMock()}
    admin.create_topics.return_value["topic"].result.side_effect = RuntimeError(
        "topic already exists"
    )
    with pytest.raises(RuntimeError, match="already exists"):
        client.create("topic")
