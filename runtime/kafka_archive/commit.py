"""Explicit synchronous commit port for the pinned native SDK."""

import importlib
import platform
import re
import sys
from collections.abc import Mapping
from typing import Protocol, cast

import telemetry.kafka_compat as kafka_compat
from runtime.kafka_archive.native import Error, Position
from runtime.kafka_archive.reader import deadline, remaining
from telemetry.archive_codec import _fail, _integer, _source
from telemetry.archive_interfaces import CommitAmbiguous


class Consumer(Protocol):
    def commit(
        self, *, offsets: list[Position], asynchronous: bool
    ) -> list[Position]: ...
    def close(self) -> None: ...


class SDK(Protocol):
    KafkaException: type[Exception]
    KafkaError: object

    def Consumer(self, config: dict[str, object]) -> Consumer: ...
    def TopicPartition(self, topic: str, partition: int, offset: int) -> Position: ...


class NativeCommitter:
    def __init__(self, endpoint: str, group: str, source: Mapping[str, object]) -> None:
        owned = _source(source)
        if (
            owned["partition"] != 0
            or endpoint != "127.0.0.1:19092"
            or type(group) is not str
            or re.fullmatch(r"m4-reader-[a-z0-9-]{1,64}", group) is None
            or sys.platform != "linux"
            or sys.version_info[:2] != (3, 13)
            or platform.machine().lower() != "x86_64"
            or platform.python_implementation() != "CPython"
        ):
            _fail("unsupported_profile", "source")
        try:
            kafka_compat.require_uuid_boundary()
        except kafka_compat.KafkaCompatibilityError:
            _fail("unsupported_profile", "source")
        self.topic = cast(str, owned["topic"])
        self.sdk = cast(SDK, importlib.import_module("confluent_kafka"))
        try:
            self.consumer = self.sdk.Consumer(
                {
                    "bootstrap.servers": endpoint,
                    "group.id": group,
                    "enable.auto.commit": False,
                    "enable.auto.offset.store": False,
                    "auto.offset.reset": "error",
                    "allow.auto.create.topics": False,
                    "isolation.level": "read_committed",
                    "socket.timeout.ms": 1000,
                }
            )
        except self.sdk.KafkaException:
            _fail("source_unavailable", "commit")

    def _error(self, error: Error | None) -> None:
        if error is None:
            return
        for name in (
            "TOPIC_AUTHORIZATION_FAILED",
            "GROUP_AUTHORIZATION_FAILED",
            "CLUSTER_AUTHORIZATION_FAILED",
            "_AUTHENTICATION",
            "SASL_AUTHENTICATION_FAILED",
        ):
            if error.code() == getattr(self.sdk.KafkaError, name, None):
                _fail("permission_denied", "commit")
        raise CommitAmbiguous() from None

    def commit(self, next_offset: int, timeout: float) -> None:
        expires = deadline(timeout)
        offset = _integer(next_offset, 0, 2**63 - 1)
        position = self.sdk.TopicPartition(self.topic, 0, offset)
        try:
            # The actual synchronous C API has no timeout keyword. The supervisor
            # bounds its process lifetime; socket timeout bounds network requests.
            result = self.consumer.commit(offsets=[position], asynchronous=False)
        except self.sdk.KafkaException as error:
            if error.args and callable(getattr(error.args[0], "code", None)):
                self._error(cast(Error, error.args[0]))
            raise CommitAmbiguous() from None
        except (TimeoutError, OSError):
            raise CommitAmbiguous() from None
        self._error(position.error)
        if not isinstance(result, list) or not result:
            raise CommitAmbiguous()
        for item in result:
            self._error(item.error)
        if len(result) != 1 or (
            result[0].topic != self.topic
            or type(result[0].partition) is not int
            or result[0].partition != 0
            or type(result[0].offset) is not int
            or result[0].offset != offset
        ):
            _fail("progress_mismatch", "commit")
        if remaining(expires) <= 0:
            raise CommitAmbiguous()

    def close(self) -> None:
        try:
            self.consumer.close()
        except self.sdk.KafkaException:
            _fail("source_unavailable", "commit")
