"""Finite native Kafka/MAVLink boundary for the isolated source-to-query slice."""

import argparse
import base64
import hashlib
import importlib
import json
import os
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

from runtime.kafka_archive.native import (
    SDK,
    Admin,
    AdminModule,
    Cluster,
    Consumer,
    Future,
    NativeSliceClient,
    Position,
    Topic,
)
from runtime.kafka_archive.reader import read_slice
from telemetry.archive_codec import encode_observations
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.kafka_compat import require_uuid_boundary
from telemetry.mavlink_live import MavlinkView
from telemetry.mavlink_position import make_input


class TopicAdmin(Admin, Protocol):
    def create_topics(
        self, topics: list[object], *, request_timeout: float
    ) -> Mapping[str, Future]: ...


class TopicModule(AdminModule, Protocol):
    def AdminClient(self, config: dict[str, object]) -> TopicAdmin: ...
    def NewTopic(
        self,
        topic: str,
        *,
        num_partitions: int,
        replication_factor: int,
        config: dict[str, str],
    ) -> object: ...


class ProgressConsumer(Consumer, Protocol):
    def commit(
        self, *, offsets: list[Position], asynchronous: bool
    ) -> list[Position]: ...


class Producer(Protocol):
    def produce(
        self,
        topic: str,
        *,
        partition: int,
        key: bytes,
        value: bytes,
        on_delivery: Callable[[object, object], None],
    ) -> None: ...
    def flush(self, timeout: float) -> int: ...


class ProducerSDK(SDK, Protocol):
    def Consumer(self, config: dict[str, object]) -> ProgressConsumer: ...
    def Producer(self, config: dict[str, object]) -> Producer: ...


class Acknowledged(Protocol):
    def topic(self) -> str: ...
    def partition(self) -> int: ...
    def offset(self) -> int: ...


class KafkaError(Protocol):
    def code(self) -> int: ...


class Packet(Protocol):
    def get_type(self) -> str: ...
    def get_srcSystem(self) -> int: ...
    def get_srcComponent(self) -> int: ...
    def get_msgbuf(self) -> bytearray: ...
    def to_dict(self) -> dict[str, object]: ...


class Connection(Protocol):
    def recv_match(self, *, blocking: bool, timeout: float | None) -> Packet | None: ...
    def close(self) -> None: ...


class Mavutil(Protocol):
    def mavlink_connection(self, address: str) -> Connection: ...


def run(config: Path, stage: str) -> dict[str, object]:
    plan = json_object(config.read_bytes())
    root = Path(string_value(plan["evidence"]))
    require_uuid_boundary()
    sdk = cast(ProducerSDK, importlib.import_module("confluent_kafka"))
    module = cast(TopicModule, importlib.import_module("confluent_kafka.admin"))
    admin = module.AdminClient({"bootstrap.servers": "127.0.0.1:19092"})
    cluster = cast(Cluster, admin.describe_cluster(request_timeout=5).result(6))
    if cluster.cluster_id != plan["cluster_id"] or len(cluster.nodes) != 1:
        raise ValueError("position_cluster_identity")
    topics = [string_value(plan["input_topic"]), string_value(plan["output_topic"])]
    if stage == "initialize":
        for topic in topics:
            new = module.NewTopic(
                topic,
                num_partitions=1,
                replication_factor=1,
                config={
                    "cleanup.policy": "delete",
                    "retention.ms": "3600000",
                    "retention.bytes": "67108864",
                },
            )
            admin.create_topics([new], request_timeout=5)[topic].result(6)
        created_sources = []
        for topic in topics:
            # CreateTopics acknowledgement can precede DescribeTopics visibility.
            deadline = time.monotonic() + 15
            while True:
                try:
                    metadata = cast(
                        Topic,
                        admin.describe_topics(
                            sdk.TopicCollection([topic]), request_timeout=5
                        )[topic].result(6),
                    )
                    break
                except sdk.KafkaException as error:
                    cause = cast(KafkaError, error.args[0])
                    if cause.code() != 3 or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.2)
            if len(metadata.partitions) != 1 or metadata.partitions[0].id != 0:
                raise ValueError("position_topic_partitions")
            created_sources.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "topic_id": str(metadata.topic_id),
                    "topic": topic,
                    "partition": 0,
                }
            )
        result: dict[str, object] = {
            "input": created_sources[0],
            "output": created_sources[1],
        }
        with (root / "sources.json").open("xb") as handle:
            handle.write(json_line(result))
        return result
    sources = json_object((root / "sources.json").read_bytes())

    def reader(which: str, suffix: str) -> NativeSliceClient:
        source = object_value(sources[which])
        group = "m4-reader-" + string_value(plan["run_id"]) + "-" + suffix
        consumer = sdk.Consumer(
            {
                "bootstrap.servers": "127.0.0.1:19092",
                "group.id": group,
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "error",
            }
        )
        try:
            position = sdk.TopicPartition(string_value(source["topic"]), 0, 0)
            existing = consumer.committed([position], timeout=5)
            if len(existing) != 1 or existing[0].offset not in (-1001, 0):
                raise ValueError("position_reader_progress")
            if existing[0].offset < 0:
                consumer.commit(offsets=[position], asynchronous=False)
        finally:
            consumer.close()
        return NativeSliceClient("127.0.0.1:19092", group, source)

    if stage == "read":
        result = {}
        for which in ("input", "output"):
            client = reader(which, which)
            try:
                info = client.inspect(5)
                end = (
                    integer_value(plan["deliveries"]) if which == "input" else info.high
                )
                if not integer_value(plan["deliveries"]) <= end <= 32:
                    raise ValueError("position_source_count")
                rows = read_slice(client, object_value(sources[which]), 0, end)
                body = b"".join(
                    encode_observations(rows[i : i + 16])
                    for i in range(0, len(rows), 16)
                )
                with (root / (which + "-observations.jsonl")).open("xb") as handle:
                    handle.write(body)
                result[which] = len(rows)
            finally:
                client.close()
        return result
    if stage != "capture":
        raise ValueError("position_worker_stage")
    mavutil = cast(Mavutil, importlib.import_module("pymavlink.mavutil"))
    connection = mavutil.mavlink_connection("udpin:0.0.0.0:14561")
    system, component = (
        integer_value(plan["system_id"]),
        integer_value(plan["component_id"]),
    )
    view = MavlinkView(
        "live-position-source",
        string_value(plan["source_boot_session"]),
        system,
        component,
        "capture",
        time.monotonic(),
    )
    producer = sdk.Producer(
        {
            "bootstrap.servers": "127.0.0.1:19092",
            "enable.idempotence": True,
            "acks": "all",
            "linger.ms": 0,
            "message.timeout.ms": 10000,
        }
    )
    acknowledgements: list[dict[str, object]] = []
    failures: list[str] = []
    source_topic = topics[0]

    def acknowledged(error: object, supplied: object) -> None:
        if error is not None:
            failures.append("unconfirmed_delivery")
            return
        message = cast(Acknowledged, supplied)
        acknowledgements.append(
            {
                "topic": message.topic(),
                "partition": message.partition(),
                "offset": message.offset(),
            }
        )

    def publish(body: bytes) -> None:
        event = json_object(body)
        producer.produce(
            source_topic,
            partition=0,
            key=string_value(event["event_id"]).encode(),
            value=body,
            on_delivery=acknowledged,
        )
        if producer.flush(10) or failures:
            raise ValueError("position_producer_unconfirmed")

    observer = reader("output", "observe")
    bodies: list[bytes] = []
    last_boot = -1000
    fix_wire: bytes | None = None
    observed_before_done = False
    try:
        with (root / "source-packets.jsonl").open("xb") as retained:
            deadline = time.monotonic() + 90
            while len(bodies) < 16 and time.monotonic() < deadline:
                view.poll(time.monotonic())
                packet = connection.recv_match(blocking=False, timeout=None)
                if packet is None:
                    time.sleep(0.01)
                    continue
                kind = packet.get_type()
                if kind not in ("GPS_RAW_INT", "GLOBAL_POSITION_INT"):
                    continue
                data = packet.to_dict()
                accepted = view.accept(
                    kind,
                    data,
                    packet.get_srcSystem(),
                    packet.get_srcComponent(),
                    time.monotonic(),
                    time.time_ns() // 1_000_000,
                )
                if not accepted:
                    continue
                if kind == "GPS_RAW_INT":
                    fix_wire = bytes(packet.get_msgbuf())
                    continue
                position = view.observations.get("position")
                if (
                    position is None
                    or position.qualification != "fix_qualified"
                    or position.boot_ms is None
                    or position.boot_ms - last_boot < 500
                    or fix_wire is None
                ):
                    continue
                event = make_input(
                    data, string_value(plan["source_boot_session"]), system, component
                )
                if event["event_id"] != position.event_id:
                    raise ValueError("position_live_identity_changed")
                body = json_line(event)
                raw = {
                    "event": event,
                    "position_packet_b64": base64.b64encode(
                        bytes(packet.get_msgbuf())
                    ).decode(),
                    "fix_packet_b64": base64.b64encode(fix_wire).decode(),
                }
                retained.write(json_line(raw))
                retained.flush()
                os.fsync(retained.fileno())
                publish(body)
                bodies.append(body)
                last_boot = position.boot_ms
                if len(bodies) == 1:
                    wait_until = time.monotonic() + 40
                    while (
                        time.monotonic() < wait_until and observer.inspect(5).high == 0
                    ):
                        time.sleep(0.1)
                    if observer.inspect(5).high == 0:
                        raise ValueError("no_flink_output_during_live_capture")
                    observed_before_done = True
            if len(bodies) != 16:
                raise ValueError("position_live_capture_deadline")
        for body in bodies[:2]:
            publish(body)
        if acknowledgements != [
            {"topic": source_topic, "partition": 0, "offset": i} for i in range(18)
        ]:
            raise ValueError("position_acknowledgement_coverage")
        result = {
            "unique_packets": len(bodies),
            "acknowledgements": acknowledgements,
            "flink_output_before_capture_complete": observed_before_done,
            "source_packets_sha256": hashlib.sha256(
                (root / "source-packets.jsonl").read_bytes()
            ).hexdigest(),
        }
        with (root / "producer-report.json").open("xb") as handle:
            handle.write(json_line(result))
        return result
    finally:
        connection.close()
        observer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("initialize", "capture", "read"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    report = run(args.config, args.stage)
    print(json.dumps({"stage": args.stage, "status": "completed"}))
