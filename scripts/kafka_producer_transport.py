"""Bounded native Kafka publication, inspection and unavailable-endpoint probes."""

import socket
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
    TopicCollection,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient
from confluent_kafka.admin._topic import TopicDescription
from kafka_evidence import require
from kafka_reconciliation import Record

from telemetry.kafka_compat import require_uuid_boundary
from telemetry_convert import load_job, verify_job
from telemetry_metrics import emit_metrics
from telemetry_reader import read_battery_event

ENDPOINT = "127.0.0.1:19092"


def fixture(job: Path, run: Path) -> tuple[bytes, ...]:
    """Verify external source/run before publishing original canonical bytes."""
    require_uuid_boundary()
    require(load_job(job).mode == "synthetic", "synthetic_job_required")
    verify_job(job, run)
    with (run / "events.jsonl").open("rb") as source:
        raw = source.read(64 * 1024 * 1024 + 1)
    require(len(raw) <= 64 * 1024 * 1024, "source_bound_exceeded")
    values = tuple(raw.splitlines())
    require(len(values) == 3, "three_event_fixture_required")
    require(
        all(read_battery_event(v)["source_type"] == "synthetic" for v in values),
        "synthetic_values_required",
    )
    return values


def identity(
    admin: AdminClient, topic: str, *, wait_for_creation: bool = False
) -> tuple[str, str]:
    """Bind the one-partition topic to the live loopback cluster and UUID."""
    metadata = admin.list_topics(timeout=15)
    cluster: object = metadata.cluster_id
    require(isinstance(cluster, str) and bool(cluster), "missing_cluster_id")
    require(
        len(metadata.brokers) == 1
        and all(
            b.host == "127.0.0.1" and b.port == 19092 for b in metadata.brokers.values()
        ),
        "unexpected_broker",
    )
    deadline = time.monotonic() + 15
    while True:
        remaining = deadline - time.monotonic()
        require(remaining > 0, "topic_creation_visibility_deadline")
        try:
            description: object = admin.describe_topics(
                TopicCollection([topic]), request_timeout=min(10, remaining)
            )[topic].result(timeout=min(12, remaining))
            break
        except KafkaException as error:
            # Topic creation ACK can precede visibility in the describe API.
            if (
                not wait_for_creation
                or not error.args
                or not isinstance(error.args[0], KafkaError)
                or error.args[0].code() != KafkaError.UNKNOWN_TOPIC_OR_PART
            ):
                raise
            remaining = deadline - time.monotonic()
            require(remaining > 0, "topic_creation_visibility_deadline")
            time.sleep(min(0.1, remaining))
    require(isinstance(description, TopicDescription), "unexpected_description")
    description = cast(TopicDescription, description)
    require(
        description.name == topic
        and len(description.partitions) == 1
        and description.partitions[0].id == 0,
        "unexpected_partition_layout",
    )
    return cast(str, cluster), str(description.topic_id)


def read_records(topic: str, end: int) -> list[Record]:
    """Read a fixed captured interval; never commit or silently reset."""
    consumer = Consumer(
        {
            "bootstrap.servers": ENDPOINT,
            "group.id": topic + ".inspection",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "auto.offset.reset": "error",
            "log_level": 0,
        }
    )
    rows: list[Record] = []
    try:
        partition = TopicPartition(topic, 0)
        require(
            consumer.get_watermark_offsets(partition, timeout=10) == (0, end),
            "interval_differs",
        )
        consumer.assign([TopicPartition(topic, 0, 0)])
        deadline = time.monotonic() + 15
        while len(rows) < end:
            require(time.monotonic() < deadline, "read_deadline")
            message = consumer.poll(1)
            if message is None:
                continue
            require(message.error() is None, "record_error")
            require(
                (message.topic(), message.partition(), message.offset())
                == (topic, 0, len(rows)),
                "observation_position_differs",
            )
            key, value = message.key(), message.value()
            if key is None or value is None:
                raise ValueError("missing_record_bytes")
            read_battery_event(value)
            rows.append(Record(len(rows), key, value))
        require(
            consumer.get_watermark_offsets(partition, timeout=10) == (0, end),
            "interval_changed",
        )
    finally:
        consumer.close()
    return rows


def producer_config(endpoint: str, capacity: int = 1000) -> dict[str, object]:
    """Use bounded native queues and deadlines with explicit idempotence."""
    return {
        "bootstrap.servers": endpoint,
        "enable.idempotence": True,
        "acks": "all",
        "max.in.flight.requests.per.connection": 5,
        "message.timeout.ms": 5000,
        "queue.buffering.max.messages": capacity,
        "queue.buffering.max.kbytes": 4096,
        "log_level": 0,
    }


def publish(topic: str, values: tuple[bytes, ...], start: int) -> dict[str, object]:
    """Require all native callbacks, exact positions and an empty final queue."""
    config = producer_config(ENDPOINT)
    producer = Producer(config)
    delivered: list[dict[str, object]] = []
    operation = "producer_retry" if start else "producer_initial"
    started = time.monotonic()
    emit_metrics(operation, "started", attempted_records=0, acknowledged_records=0)

    def callback(index: int) -> Callable[[KafkaError | None, Message], None]:
        def complete(error: KafkaError | None, message: Message) -> None:
            delivered.append(
                {
                    "input_position": index,
                    "acknowledged": error is None,
                    "error_code": error.code() if error else None,
                    "topic": message.topic(),
                    "partition": message.partition(),
                    "offset": message.offset(),
                }
            )
            emit_metrics(
                operation,
                "callback",
                acknowledged_records=sum(r["acknowledged"] is True for r in delivered),
                callback_errors=sum(r["acknowledged"] is False for r in delivered),
            )

        return complete

    for i, value in enumerate(values):
        producer.produce(
            topic,
            key=read_battery_event(value)["vehicle_id"].encode(),
            value=value,
            on_delivery=callback(i),
        )
        producer.poll(0)
    pending = producer.flush(10)
    delivered.sort(key=lambda row: int(str(row["input_position"])))
    complete = pending == 0 and delivered == [
        {
            "input_position": i,
            "acknowledged": True,
            "error_code": None,
            "topic": topic,
            "partition": 0,
            "offset": start + i,
        }
        for i in range(3)
    ]
    emit_metrics(
        operation,
        "completed" if complete else "failed",
        attempted_records=len(values),
        enqueued_records=len(values),
        acknowledged_records=sum(r["acknowledged"] is True for r in delivered),
        callback_errors=sum(r["acknowledged"] is False for r in delivered),
        pending_records=pending,
        duration_seconds=time.monotonic() - started,
    )
    require(complete, "publication_incomplete_or_uncertain")
    return {"producer_config": config, "acknowledged": delivered, "pending": pending}


def unavailable(values: tuple[bytes, ...], capacity: int) -> dict[str, object]:
    """Reserve a non-listening loopback port for refusal and queue pressure."""
    with socket.socket() as guard:
        guard.bind(("127.0.0.1", 0))
        endpoint = f"127.0.0.1:{guard.getsockname()[1]}"
        config = producer_config(endpoint, capacity)
        producer = Producer(config)
        queued: list[int] = []
        unqueued: list[int] = []
        callbacks: list[dict[str, object]] = []

        def callback(index: int) -> Callable[[KafkaError | None, Message], None]:
            def complete(error: KafkaError | None, message: Message) -> None:
                callbacks.append(
                    {
                        "input_position": index,
                        "acknowledged": error is None,
                        "error_code": error.code() if error else None,
                    }
                )

            return complete

        started = time.monotonic()
        for i, value in enumerate(values):
            try:
                producer.produce(
                    "m2.unavailable.synthetic", value=value, on_delivery=callback(i)
                )
                queued.append(i)
            except BufferError:
                unqueued.append(i)
        pending = producer.flush(10)
        elapsed = time.monotonic() - started
        emit_metrics(
            "producer_queue_pressure" if capacity == 1 else "producer_unavailable",
            "failed",
            attempted_records=len(values),
            enqueued_records=len(queued),
            unqueued_records=len(unqueued),
            acknowledged_records=sum(r["acknowledged"] is True for r in callbacks),
            callback_errors=sum(r["acknowledged"] is False for r in callbacks),
            pending_records=pending,
            duration_seconds=elapsed,
        )
        callbacks.sort(key=lambda row: int(str(row["input_position"])))
        require(
            pending == 0 and len(callbacks) == len(queued) and elapsed < 15,
            "unavailable_dispositions_incomplete",
        )
        require(
            all(
                r["acknowledged"] is False
                and r["error_code"] == KafkaError._MSG_TIMED_OUT
                for r in callbacks
            ),
            "unexpected_unavailable_callback",
        )
        require(
            queued == ([0] if capacity == 1 else [0, 1, 2])
            and unqueued == ([1, 2] if capacity == 1 else []),
            "queue_dispositions_differ",
        )
        return {
            "publication_status": "failed",
            "producer_config": config,
            "attempted": 3,
            "queued_positions": queued,
            "unqueued_positions": unqueued,
            "callbacks": callbacks,
            "acknowledged": 0,
            "pending": 0,
            "uncertain_positions": queued,
            "elapsed_seconds": round(elapsed, 3),
        }
