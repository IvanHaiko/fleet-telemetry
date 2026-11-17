"""Typed Kafka SDK contracts and immutable publication records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from m3_runtime import digest

from telemetry.kafka_protocols import (
    Admin,
    AdminModule,
    ClusterDescription,
    ConfigEntry,
    Consumer,
    Error,
    Future,
    Kafka,
    Message,
    Node,
    Position,
    Producer,
    TopicDescription,
)

__all__ = [
    "Admin",
    "AdminModule",
    "ClusterDescription",
    "ConfigEntry",
    "Consumer",
    "Error",
    "Fixtures",
    "Future",
    "Kafka",
    "Message",
    "Node",
    "Position",
    "Producer",
    "Record",
    "TopicDescription",
]


class Fixtures(Protocol):
    def event(
        self,
        index: int = 0,
        timestamp: str = "1970-01-01T00:00:00.000000Z",
        vehicle: str = "vehicle-a",
        voltage: float = 1.1,
        current: float | None = None,
        remaining: float | None = None,
    ) -> dict[str, object]: ...
    def scope(self, **changes: str) -> object: ...


@dataclass(frozen=True)
class Record:
    partition: int
    offset: int
    index: int
    value: bytes
    key: bytes = b"vehicle-a"

    def proof(self, *, index: bool = False) -> dict[str, object]:
        row: dict[str, object] = {
            "partition": self.partition,
            "offset": self.offset,
            "key_sha256": digest(self.key),
            "value_sha256": digest(self.value),
        }
        if index:
            row["index"] = self.index
        return row
