"""Pinned native Kafka access for the distributed or single-broker profile."""

from __future__ import annotations

import base64
import importlib
import sys
import time
from typing import TYPE_CHECKING, Protocol, cast

from telemetry.continuous_connection import LOCAL_ENDPOINTS, parse_connection
from telemetry.kafka_compat import require_uuid_boundary

if TYPE_CHECKING:
    from scripts.m3_transport_types import (
        Admin,
        AdminModule,
        ClusterDescription,
        Producer,
        TopicDescription,
    )


class Error(Protocol):
    def code(self) -> int: ...


class Position(Protocol):
    topic: str
    partition: int
    offset: int
    error: Error | None


class Message(Protocol):
    def error(self) -> Error | None: ...
    def topic(self) -> str: ...
    def partition(self) -> int: ...
    def offset(self) -> int: ...
    def value(self) -> bytes | None: ...
    def key(self) -> bytes | None: ...
    def headers(self) -> list[tuple[str, bytes | None]] | None: ...
    def timestamp(self) -> tuple[int, int]: ...


class Consumer(Protocol):
    def poll(self, timeout: float) -> Message | None: ...
    def assign(self, positions: list[Position]) -> None: ...
    def committed(
        self, positions: list[Position], *, timeout: float
    ) -> list[Position]: ...
    def commit(
        self, *, offsets: list[Position], asynchronous: bool
    ) -> list[Position]: ...
    def get_watermark_offsets(
        self, position: Position, *, timeout: float, cached: bool
    ) -> tuple[int, int]: ...
    def close(self) -> None: ...


class SDK(Protocol):
    def Consumer(self, config: dict[str, object]) -> Consumer: ...
    def Producer(self, config: dict[str, object]) -> Producer: ...
    def TopicPartition(
        self, topic: str, partition: int, offset: int = 0
    ) -> Position: ...
    def TopicCollection(self, topics: list[str]) -> object: ...


class Kafka:
    bootstrap: str
    cluster_id: str
    sdk: SDK
    admin: Admin
    module: AdminModule

    def __init__(
        self, bootstrap: str, cluster_id: str, connection: object = None
    ) -> None:
        self.connection = parse_connection(connection)
        self.endpoints = (
            frozenset(self.connection.endpoints) if self.connection else LOCAL_ENDPOINTS
        )
        # The legacy local route is the same six-broker, eighteen-partition shape.
        self.brokers = self.connection.brokers if self.connection else 6
        self.partitions = self.connection.partitions if self.connection else 18
        self.replication = self.connection.replication_factor if self.connection else 2
        seeds = bootstrap.split(",")
        if (
            not seeds
            or not set(seeds) <= self.endpoints
            or len(set(seeds)) != len(seeds)
        ):
            raise ValueError("continuous_bootstrap_endpoints")
        if sys.platform != "linux":
            raise ValueError("continuous_linux_profile_required")
        require_uuid_boundary()
        self.bootstrap, self.cluster_id = bootstrap, cluster_id
        self.sdk = cast(SDK, importlib.import_module("confluent_kafka"))
        module = cast("AdminModule", importlib.import_module("confluent_kafka.admin"))
        self.admin = module.AdminClient(
            {**self.client_properties(), "socket.timeout.ms": 5000}
        )
        self.module = module

    def describe(self, topic: str) -> dict[str, object]:
        cluster = cast(
            "ClusterDescription",
            self.admin.describe_cluster(request_timeout=5).result(6),
        )
        if cluster.cluster_id != self.cluster_id or len(cluster.nodes) != self.brokers:
            raise ValueError("continuous_cluster_identity")
        endpoints = {f"{node.host}:{node.port}" for node in cluster.nodes}
        if endpoints != self.endpoints:
            raise ValueError("continuous_broker_endpoints")
        info = cast(
            "TopicDescription",
            self.admin.describe_topics(
                self.sdk.TopicCollection([topic]), request_timeout=5
            )[topic].result(6),
        )
        if len(info.partitions) != self.partitions:
            raise ValueError("continuous_partition_count")
        return {
            "cluster_id": cluster.cluster_id,
            "topic_id": str(info.topic_id),
            "topic": topic,
        }

    def create(self, topic: str) -> dict[str, object]:
        new = self.module.NewTopic(
            topic,
            num_partitions=self.partitions,
            replication_factor=self.replication,
            config={
                "cleanup.policy": "delete",
                "retention.ms": "-1",
                "retention.bytes": "-1",
                "min.insync.replicas": str(self.replication),
            },
        )
        # An existing topic fails here, so only a fresh topic reaches the wait.
        self.admin.create_topics([new], request_timeout=5)[topic].result(6)
        # Metadata can lag creation on a fresh broker; retry only the readback.
        for attempt in range(20):
            try:
                return self.describe(topic)
            except Exception:
                if attempt == 19:
                    raise
                time.sleep(0.5)
        raise AssertionError("unreachable")

    def client_properties(self) -> dict[str, object]:
        """Share endpoint/TLS admission across admin, consumer and producer."""
        return {
            "bootstrap.servers": self.bootstrap,
            **(self.connection.native_properties() if self.connection else {}),
        }

    def consumer(self, group: str) -> Consumer:
        return self.sdk.Consumer(
            {
                **self.client_properties(),
                "group.id": group,
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "error",
                "enable.partition.eof": False,
                "isolation.level": "read_committed",
                "allow.auto.create.topics": False,
                "socket.timeout.ms": 5000,
                "fetch.wait.max.ms": 100,
            }
        )

    def positions(self, topic: str, offsets: dict[str, int]) -> list[Position]:
        return [
            self.sdk.TopicPartition(topic, int(p), offset)
            for p, offset in offsets.items()
        ]

    def commit(
        self, consumer: Consumer, topic: str, partition: int, offset: int
    ) -> None:
        values = consumer.commit(
            offsets=[self.sdk.TopicPartition(topic, partition, offset)],
            asynchronous=False,
        )
        if (
            len(values) != 1
            or values[0].error is not None
            or values[0].offset != offset
        ):
            raise ValueError("continuous_commit_unconfirmed")


def observation(message: Message, source: dict[str, object]) -> dict[str, object]:
    def encoded(body: bytes | None) -> str | None:
        return None if body is None else base64.b64encode(body).decode()

    kind, stamp = message.timestamp()
    if message.error() is not None or kind not in (0, 1, 2):
        raise ValueError("continuous_source_read_error")
    return {
        **source,
        "partition": message.partition(),
        "offset": message.offset(),
        "format_version": "kafka-observation-v1",
        "timestamp_ms": None if kind == 0 else stamp,
        "timestamp_type": {0: "not_available", 1: "create_time", 2: "log_append_time"}[
            kind
        ],
        "key_b64": encoded(message.key()),
        "value_b64": encoded(message.value()),
        "headers": [
            {"name_utf8": name, "value_b64": encoded(value)}
            for name, value in message.headers() or []
        ],
        "measurement": None,
    }
