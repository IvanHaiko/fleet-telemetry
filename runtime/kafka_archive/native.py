"""Pinned read-only Kafka SDK boundary; no progress mutation API."""

import base64
import importlib
import platform
import re
import sys
from collections.abc import Mapping, Sequence
from typing import NoReturn, Protocol, cast

import telemetry.kafka_compat as kafka_compat
from runtime.kafka_archive.reader import deadline, remaining
from runtime.kafka_archive.types import SourceInfo
from telemetry.archive_codec import ArchiveError, _fail, _integer, _source


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
    def timestamp(self) -> tuple[int, int]: ...
    def key(self) -> bytes | None: ...
    def value(self) -> bytes | None: ...
    def headers(self) -> list[tuple[str, bytes | None]] | None: ...


class Consumer(Protocol):
    def assign(self, partitions: list[Position]) -> None: ...
    def assignment(self) -> list[Position]: ...
    def poll(self, timeout: float) -> Message | None: ...
    def committed(
        self, partitions: list[Position], *, timeout: float
    ) -> list[Position]: ...
    def get_watermark_offsets(
        self, partition: Position, *, timeout: float, cached: bool
    ) -> tuple[int, int]: ...
    def close(self) -> None: ...


class SDK(Protocol):
    KafkaException: type[Exception]
    KafkaError: object

    def Consumer(self, config: dict[str, object]) -> Consumer: ...
    def TopicCollection(self, topics: list[str]) -> object: ...
    def TopicPartition(
        self, topic: str, partition: int, offset: int = 0
    ) -> Position: ...


class Future(Protocol):
    def result(self, timeout: float) -> object: ...


class Admin(Protocol):
    def describe_cluster(self, *, request_timeout: float) -> Future: ...
    def describe_topics(
        self, topics: object, *, request_timeout: float
    ) -> Mapping[str, Future]: ...
    def describe_configs(
        self, resources: list[object], *, request_timeout: float
    ) -> Mapping[object, Future]: ...


class AdminModule(Protocol):
    def AdminClient(self, config: dict[str, object]) -> Admin: ...
    def ConfigResource(self, kind: int, name: str) -> object: ...


class Node(Protocol):
    host: str
    port: int


class Cluster(Protocol):
    cluster_id: str
    nodes: Sequence[Node]


class Partition(Protocol):
    id: int


class TopicId(Protocol):
    def __str__(self) -> str: ...


class Topic(Protocol):
    topic_id: TopicId
    partitions: Sequence[Partition]


class Config(Protocol):
    value: str


def _cap(expires: float) -> float:
    return min(5.0, remaining(expires))


def _binary(value: bytes | None) -> str | None:
    if value is None:
        return None
    if type(value) is not bytes:
        _fail()
    return base64.b64encode(value).decode("ascii")


class NativeSliceClient:
    """Manually assigned consumer restricted to the disposable local profile."""

    def __init__(self, endpoint: str, group: str, source: Mapping[str, object]) -> None:
        self._source = _source(source)
        if self._source["partition"] != 0:
            _fail("unsupported_profile", "assignment")
        if (
            type(endpoint) is not str
            or endpoint != "127.0.0.1:19092"
            or type(group) is not str
            or re.fullmatch(r"m4-reader-[a-z0-9-]{1,64}", group) is None
        ):
            _fail("unsupported_profile", "source")
        if (
            sys.platform not in ("linux", "win32")
            or platform.system() not in ("Linux", "Windows")
            or platform.python_implementation() != "CPython"
            or platform.machine().lower() not in ("x86_64", "amd64")
            or sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 13)
        ):
            _fail("unsupported_profile", "source")
        try:
            kafka_compat.require_uuid_boundary()
        except kafka_compat.KafkaCompatibilityError:
            _fail("unsupported_profile", "source")
        self._topic = cast(str, self._source["topic"])
        try:
            self._sdk = cast(SDK, importlib.import_module("confluent_kafka"))
            admin = cast(AdminModule, importlib.import_module("confluent_kafka.admin"))
        except ImportError:
            _fail("source_unavailable", "source")
        self._topics = self._sdk.TopicCollection([self._topic])
        self._resource = admin.ConfigResource(2, self._topic)
        try:
            self._admin = admin.AdminClient({"bootstrap.servers": endpoint})
            self._consumer = self._sdk.Consumer(
                {
                    "bootstrap.servers": endpoint,
                    "group.id": group,
                    "enable.auto.commit": False,
                    "enable.auto.offset.store": False,
                    "auto.offset.reset": "error",
                    "isolation.level": "read_committed",
                    "enable.partition.eof": True,
                    "allow.auto.create.topics": False,
                    "queued.max.messages.kbytes": 1024,
                    "queued.min.messages": 1,
                    "fetch.max.bytes": 1048576,
                    "max.partition.fetch.bytes": 1048576,
                    "receive.message.max.bytes": 2097152,
                }
            )
        except self._sdk.KafkaException as error:
            self._exception(error)
        except TimeoutError:
            _fail("deadline_exceeded", "source")
        except PermissionError:
            _fail("permission_denied", "source")
        except OSError:
            _fail("source_unavailable", "source")

    def _error(self, error: Error | None) -> None:
        if error is None:
            return
        code = error.code()
        constants = self._sdk.KafkaError
        for name in ("_PARTITION_EOF", "OFFSET_OUT_OF_RANGE", "_AUTO_OFFSET_RESET"):
            if code == getattr(constants, name, None):
                _fail("source_gap", "offset")
        for name in (
            "TOPIC_AUTHORIZATION_FAILED",
            "GROUP_AUTHORIZATION_FAILED",
            "CLUSTER_AUTHORIZATION_FAILED",
            "_AUTHENTICATION",
            "SASL_AUTHENTICATION_FAILED",
        ):
            if code == getattr(constants, name, None):
                _fail("permission_denied", "source")
        _fail("source_unavailable", "source")

    def _exception(self, error: Exception) -> NoReturn:
        if error.args and callable(getattr(error.args[0], "code", None)):
            self._error(cast(Error, error.args[0]))
        _fail("source_unavailable", "source")

    def inspect(self, timeout: float) -> SourceInfo:
        expires = deadline(timeout)
        try:
            future = self._admin.describe_cluster(request_timeout=_cap(expires))
            cluster = cast(Cluster, future.result(timeout=_cap(expires)))
            if (
                len(cluster.nodes) != 1
                or cluster.nodes[0].host != "127.0.0.1"
                or type(cluster.nodes[0].port) is not int
                or cluster.nodes[0].port != 19092
            ):
                _fail("unsupported_profile", "source")
            futures = self._admin.describe_topics(
                self._topics, request_timeout=_cap(expires)
            )
            topic = cast(Topic, futures[self._topic].result(timeout=_cap(expires)))
            if (
                len(topic.partitions) != 1
                or type(topic.partitions[0].id) is not int
                or topic.partitions[0].id != 0
            ):
                _fail("unsupported_profile", "assignment")
            topic_id = str(topic.topic_id)
            if re.fullmatch(r"[A-Za-z0-9+/]{22}", topic_id) is None:
                _fail("source_identity", "source")
            uuid_bytes = base64.b64decode(topic_id + "==", validate=True)
            if (
                len(uuid_bytes) != 16
                or uuid_bytes == bytes(16)
                or base64.b64encode(uuid_bytes).decode("ascii").rstrip("=") != topic_id
            ):
                _fail("source_identity", "source")
            source = _source(
                dict(self._source, cluster_id=cluster.cluster_id, topic_id=topic_id)
            )
            if source != self._source:
                _fail("source_identity", "source")
            futures_config = self._admin.describe_configs(
                [self._resource], request_timeout=_cap(expires)
            )
            configs = cast(
                Mapping[str, Config],
                futures_config[self._resource].result(timeout=_cap(expires)),
            )
            if configs["cleanup.policy"].value != "delete":
                _fail("unsupported_profile", "cleanup_policy")
            position = self._sdk.TopicPartition(self._topic, 0)
            low, high = self._consumer.get_watermark_offsets(
                position, timeout=_cap(expires), cached=False
            )
            self._error(position.error)
            committed = self._consumer.committed([position], timeout=_cap(expires))
            if len(committed) != 1:
                _fail("source_unavailable", "source")
            entry = committed[0]
            self._error(entry.error)
            if (
                entry.topic != self._topic
                or type(entry.partition) is not int
                or entry.partition != 0
            ):
                _fail("source_identity", "source")
            progress = entry.offset
            if type(progress) is not int:
                _fail()
            remaining(expires)
            return SourceInfo(
                source,
                _integer(low, 0, 2**63 - 1),
                _integer(high, 0, 2**63 - 1),
                None if progress == -1001 else _integer(progress, 0, 2**63 - 1),
                configs["cleanup.policy"].value == "delete",
            )
        except self._sdk.KafkaException as error:
            self._exception(error)
        except TimeoutError:
            _fail("deadline_exceeded", "source")
        except PermissionError:
            _fail("permission_denied", "source")
        except OSError:
            _fail("source_unavailable", "source")
        except (KeyError, AttributeError, ValueError) as error:
            if isinstance(error, ArchiveError):
                raise
            _fail("invalid_format", "source")
        _fail("source_unavailable", "source")

    def assign(self, start: int) -> None:
        offset = _integer(start, 0, 2**63 - 1)
        try:
            self._consumer.assign([self._sdk.TopicPartition(self._topic, 0, offset)])
        except self._sdk.KafkaException as error:
            self._exception(error)
        except TimeoutError:
            _fail("deadline_exceeded", "source")
        except PermissionError:
            _fail("permission_denied", "source")
        except OSError:
            _fail("source_unavailable", "source")

    def assigned(self) -> bool:
        try:
            assigned = self._consumer.assignment()
            for position in assigned:
                self._error(position.error)
            return (
                len(assigned) == 1
                and assigned[0].topic == self._topic
                and type(assigned[0].partition) is int
                and assigned[0].partition == 0
            )
        except self._sdk.KafkaException as error:
            self._exception(error)
        except TimeoutError:
            _fail("deadline_exceeded", "source")
        except PermissionError:
            _fail("permission_denied", "source")
        except OSError:
            _fail("source_unavailable", "source")
        return False

    def poll(self, timeout: float) -> Mapping[str, object] | None:
        expires = deadline(timeout)
        try:
            message = self._consumer.poll(_cap(expires))
            remaining(expires)
            if message is None:
                return None
            self._error(message.error())
            kind, timestamp = message.timestamp()
            if type(kind) is not int or kind not in (0, 1, 2):
                _fail()
            _integer(timestamp, -(2**63), 2**63 - 1)
            if kind == 0 and timestamp != -1:
                _fail()
            headers: list[dict[str, object]] = []
            try:
                supplied = message.headers()
            except (UnicodeError, SystemError):
                _fail()
            if supplied is not None:
                if type(supplied) is not list:
                    _fail()
                for header in supplied:
                    if type(header) is not tuple or len(header) != 2:
                        _fail()
                    name, value = header
                    if type(name) is not str or "\x00" in name:
                        _fail()
                    if name.encode("utf-8", "strict").decode("utf-8", "strict") != name:
                        _fail()
                    headers.append({"name_utf8": name, "value_b64": _binary(value)})
            remaining(expires)
            return dict(
                self._source,
                topic=message.topic(),
                partition=message.partition(),
                offset=message.offset(),
                format_version="kafka-observation-v1",
                timestamp_type=("not_available", "create_time", "log_append_time")[
                    kind
                ],
                timestamp_ms=None if kind == 0 else timestamp,
                key_b64=_binary(message.key()),
                value_b64=_binary(message.value()),
                headers=headers,
                measurement=None,
            )
        except self._sdk.KafkaException as error:
            self._exception(error)
        except TimeoutError:
            _fail("deadline_exceeded", "source")
        except PermissionError:
            _fail("permission_denied", "source")
        except OSError:
            _fail("source_unavailable", "source")
        except ArchiveError:
            raise
        except (ValueError, AttributeError):
            _fail()
        return None

    def close(self) -> None:
        try:
            self._consumer.close()
        except self._sdk.KafkaException as error:
            self._exception(error)
        except TimeoutError:
            _fail("deadline_exceeded", "source")
        except PermissionError:
            _fail("permission_denied", "source")
        except OSError:
            _fail("source_unavailable", "source")
