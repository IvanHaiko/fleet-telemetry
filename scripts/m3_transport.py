"""Bounded native Kafka transport and byte-for-byte broker evidence."""

from __future__ import annotations

import importlib
import importlib.metadata
import re
import time
from collections.abc import Callable, Sequence
from typing import cast

from m3_runtime import digest, require
from m3_transport_types import (
    AdminModule,
    ClusterDescription,
    ConfigEntry,
    Consumer,
    Error,
    Kafka,
    Message,
    Record,
    TopicDescription,
)

from telemetry.kafka_compat import require_uuid_boundary

ENDPOINT = "127.0.0.1:19092"
CLUSTER = "AwMDAwMDAwMDAwMDAwMDAw"


class Transport:
    """No implicit offset reset, group commit or simulated broker state."""

    def __init__(self, log: Callable[[str, object], None]) -> None:
        self.log = log
        require_uuid_boundary()
        self.kafka = cast(Kafka, importlib.import_module("confluent_kafka"))
        self.module = cast(
            AdminModule, importlib.import_module("confluent_kafka.admin")
        )
        self.admin = self.module.AdminClient(
            {"bootstrap.servers": ENDPOINT, "socket.timeout.ms": 5000}
        )
        self.producer = self.kafka.Producer(
            {
                "bootstrap.servers": ENDPOINT,
                "enable.idempotence": True,
                "acks": "all",
                "message.timeout.ms": 5000,
                "max.in.flight.requests.per.connection": 5,
                "queue.buffering.max.messages": 128,
                "queue.buffering.max.kbytes": 1024,
            }
        )
        self.log(
            "client_versions",
            {
                "python": importlib.metadata.version("confluent-kafka"),
                "native": self.kafka.libversion(),
            },
        )

    def topic(self, topic: str) -> None:
        require(
            bool(
                re.fullmatch(
                    r"m2\.m3-final-[a-z0-9-]+\.telemetry\.canonical\.v1", topic
                )
            ),
            "topic_scope",
        )

    def identity(self, topic: str, partitions: int) -> dict[str, object]:
        self.topic(topic)
        cluster = cast(
            ClusterDescription, self.admin.describe_cluster(request_timeout=5).result(6)
        )
        require(
            cluster.cluster_id == CLUSTER
            and len(cluster.nodes) == 1
            and all(n.host == "127.0.0.1" and n.port == 19092 for n in cluster.nodes),
            "cluster_identity",
        )
        description = cast(
            TopicDescription,
            self.admin.describe_topics(
                self.kafka.TopicCollection([topic]), request_timeout=5
            )[topic].result(6),
        )
        require(len(description.partitions) == partitions, "partition_count")
        identity: dict[str, object] = {
            "cluster_id": cluster.cluster_id,
            "topic_id": str(description.topic_id),
            "topic": topic,
        }
        require(identity["topic_id"] not in {"", "None"}, "topic_uuid_missing")
        self.log("source_identity", identity)
        return identity

    def create(self, topic: str, partitions: int) -> dict[str, object]:
        self.topic(topic)
        require(partitions in {1, 2}, "partition_bound")
        cluster = cast(
            ClusterDescription, self.admin.describe_cluster(request_timeout=5).result(6)
        )
        require(
            cluster.cluster_id == CLUSTER
            and len(cluster.nodes) == 1
            and all(n.host == "127.0.0.1" and n.port == 19092 for n in cluster.nodes),
            "cluster_identity_before_topic_creation",
        )
        config = {
            "cleanup.policy": "delete",
            "retention.ms": "-1",
            "retention.bytes": "-1",
        }
        new = self.module.NewTopic(
            topic, num_partitions=partitions, replication_factor=1, config=config
        )
        self.admin.create_topics([new], request_timeout=5)[topic].result(6)
        resource = self.module.ConfigResource(2, topic)
        values = self.admin.describe_configs([resource], request_timeout=5)[
            resource
        ].result(6)
        entries = cast(dict[str, ConfigEntry], values)
        actual = {k: entries[k].value for k in config}
        require(actual == config, "topic_retention_policy")
        self.log("topic_configs", {"topic": topic, "configs": actual})
        return self.identity(topic, partitions)

    def send(self, topic: str, record: Record) -> None:
        delivered: list[dict[str, object]] = []

        def callback(error: Error | None, message: Message) -> None:
            delivered.append(
                {
                    "error": error.code() if error else None,
                    "topic": message.topic(),
                    "partition": message.partition(),
                    "offset": message.offset(),
                }
            )

        self.producer.produce(
            topic,
            partition=record.partition,
            key=record.key,
            value=record.value,
            on_delivery=callback,
        )
        pending = self.producer.flush(6)
        self.log(
            "publication",
            {
                "topic": topic,
                "expected": record.proof(),
                "callbacks": delivered,
                "pending": pending,
            },
        )
        require(
            pending == 0
            and delivered
            == [
                {
                    "error": None,
                    "topic": topic,
                    "partition": record.partition,
                    "offset": record.offset,
                }
            ],
            "publish_uncertain",
        )

    def consumer(self, group: str) -> Consumer:
        return self.kafka.Consumer(
            {
                "bootstrap.servers": ENDPOINT,
                "group.id": group,
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "error",
                "enable.partition.eof": True,
                "socket.timeout.ms": 5000,
            }
        )

    def committed(self, topic: str, group: str) -> int:
        consumer = self.consumer(group)
        try:
            positions = consumer.committed(
                [self.kafka.TopicPartition(topic, 0)], timeout=5
            )
            require(len(positions) == 1, "committed_partition")
            self.log(
                "committed_offset",
                {"topic": topic, "group": group, "offset": positions[0].offset},
            )
            return positions[0].offset
        finally:
            consumer.close()

    def readback(
        self, topic: str, expected: Sequence[Record], ends: list[int]
    ) -> list[dict[str, object]]:
        require(len(ends) in {1, 2} and sum(ends) == len(expected), "readback_bounds")
        consumer = self.consumer("m3-independent-" + str(time.monotonic_ns()))
        partitions = [self.kafka.TopicPartition(topic, p, 0) for p in range(len(ends))]
        captured: dict[tuple[int, int], tuple[bytes, bytes]] = {}
        try:
            for p, partition in enumerate(partitions):
                low, high = consumer.get_watermark_offsets(
                    partition, timeout=5, cached=False
                )
                self.log(
                    "source_bounds",
                    {"topic": topic, "partition": p, "low": low, "high": high},
                )
                require(low == 0 and high == ends[p], "source_bounds_changed")
            consumer.assign(partitions)
            end = time.monotonic() + 30
            while len(captured) < sum(ends) and time.monotonic() < end:
                message = consumer.poll(0.2)
                if message is None:
                    continue
                error = message.error()
                if error:
                    require(error.code() == -191, "broker_read_error")
                    continue
                position = (message.partition(), message.offset())
                require(
                    message.topic() == topic
                    and 0 <= position[0] < len(ends)
                    and 0 <= position[1] < ends[position[0]]
                    and position not in captured,
                    "unexpected_broker_position",
                )
                key, value = message.key(), message.value()
                require(
                    isinstance(key, bytes) and isinstance(value, bytes),
                    "null_broker_bytes",
                )
                captured[position] = (cast(bytes, key), cast(bytes, value))
            require(
                captured
                == {(r.partition, r.offset): (r.key, r.value) for r in expected},
                "broker_bytes_differ",
            )
            positions = consumer.position(partitions)
            require(
                {p.partition: p.offset for p in positions} == dict(enumerate(ends)),
                "broker_final_positions",
            )
            result = [
                {
                    "partition": p,
                    "offset": o,
                    "key_sha256": digest(k),
                    "value_sha256": digest(v),
                }
                for (p, o), (k, v) in sorted(captured.items())
            ]
            self.log(
                "readback",
                {
                    "topic": topic,
                    "records": result,
                    "exact_bytes_hex": [
                        {"partition": p, "offset": o, "key": k.hex(), "value": v.hex()}
                        for (p, o), (k, v) in sorted(captured.items())
                    ],
                },
            )
            return result
        finally:
            consumer.close()
