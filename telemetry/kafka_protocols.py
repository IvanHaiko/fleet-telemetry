"""Structural types for the Kafka client and admin interfaces used by telemetry."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol


class Error(Protocol):
    def code(self) -> int: ...


class Message(Protocol):
    def error(self) -> Error | None: ...
    def partition(self) -> int: ...
    def offset(self) -> int: ...
    def key(self) -> bytes | None: ...
    def value(self) -> bytes | None: ...
    def topic(self) -> str: ...


class Position(Protocol):
    partition: int
    offset: int


class Producer(Protocol):
    def produce(
        self,
        topic: str,
        *,
        partition: int,
        key: bytes,
        value: bytes,
        on_delivery: Callable[[Error | None, Message], None],
    ) -> None: ...
    def poll(self, timeout: float) -> int: ...
    def flush(self, timeout: float) -> int: ...


class Consumer(Protocol):
    def assign(self, partitions: Sequence[Position]) -> None: ...
    def poll(self, timeout: float) -> Message | None: ...
    def get_watermark_offsets(
        self, partition: Position, *, timeout: float, cached: bool
    ) -> tuple[int, int]: ...
    def position(self, partitions: Sequence[Position]) -> list[Position]: ...
    def committed(
        self, partitions: Sequence[Position], *, timeout: float
    ) -> list[Position]: ...
    def close(self) -> None: ...


class Kafka(Protocol):
    def Producer(self, config: dict[str, object]) -> Producer: ...
    def Consumer(self, config: dict[str, object]) -> Consumer: ...
    def TopicPartition(
        self, topic: str, partition: int, offset: int = 0
    ) -> Position: ...
    def TopicCollection(self, topics: list[str]) -> object: ...
    def libversion(self) -> tuple[str, int]: ...


class Future(Protocol):
    def result(self, timeout: float) -> object: ...


class Admin(Protocol):
    def create_topics(
        self, topics: list[object], *, request_timeout: float
    ) -> dict[str, Future]: ...
    def describe_topics(
        self, topics: object, *, request_timeout: float
    ) -> dict[str, Future]: ...
    def describe_cluster(self, *, request_timeout: float) -> Future: ...
    def describe_configs(
        self, resources: list[object], *, request_timeout: float
    ) -> dict[object, Future]: ...


class AdminModule(Protocol):
    def AdminClient(self, config: dict[str, object]) -> Admin: ...
    def NewTopic(
        self,
        topic: str,
        *,
        num_partitions: int,
        replication_factor: int,
        config: dict[str, str],
    ) -> object: ...
    def ConfigResource(self, kind: int, name: str) -> object: ...


class Node(Protocol):
    host: str
    port: int


class ClusterDescription(Protocol):
    cluster_id: str
    nodes: Sequence[Node]


class TopicDescription(Protocol):
    topic_id: object
    partitions: Sequence[object]


class ConfigEntry(Protocol):
    value: str
