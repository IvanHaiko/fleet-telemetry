"""Paced F09 publication to the run's input topic with an acknowledgement ledger.

Delivery `i` of the declared sequence must land at offset `i` of partition 0.
A start after a stop continues at the next undelivered index: the ledger must
be a prefix of the declared deliveries and agree with the broker's end offset
(see `resume_point`).
"""

import hashlib
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from runtime.continuous.live_position_worker import Acknowledged, ProducerSDK
from runtime.continuous.recording_config import (
    Document,
    kafka_client,
    lifetime,
    load_inputs,
    require,
)
from telemetry.continuous_archive import durable_cursor
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded

# One ledger line is about 130 bytes; 50,000 deliveries stay well below this.
MAX_LEDGER = 16 * 1024 * 1024


def resume_point(
    ledger: Path,
    wires: list[bytes],
    topic: str,
    end: int,
    record_at: Callable[[int], bytes],
) -> int:
    """The next delivery index, after checking the ledger against the broker.

    Every ledger line must equal the acknowledgement of the declared delivery at
    its index. The broker's end offset must equal the ledger length, or exceed it
    by one when the process stopped between the broker's acknowledgement and the
    ledger write; that record is admitted only if its bytes equal the next
    declared delivery, and its line is appended. Anything else is lost or foreign
    data, so publication refuses instead of creating a gap or a repeat.
    """

    def line(index: int) -> bytes:
        digest = hashlib.sha256(wires[index]).hexdigest()
        return json_line(
            {"topic": topic, "partition": 0, "offset": index, "sha256": digest}
        )

    if not ledger.exists():
        require(end == 0, "recording_producer_topic_not_empty")
        return 0
    body = read_bounded(ledger, MAX_LEDGER)
    require(not body or body.endswith(b"\n"), "recording_producer_ledger_torn")
    lines = body.splitlines(keepends=True)
    require(
        len(lines) <= len(wires)
        and all(text == line(index) for index, text in enumerate(lines)),
        "recording_producer_ledger_mismatch",
    )
    count = len(lines)
    if end == count + 1 and count < len(wires) and record_at(count) == wires[count]:
        with ledger.open("ab") as handle:
            handle.write(line(count))
            handle.flush()
            os.fsync(handle.fileno())
        return count + 1
    require(end == count, "recording_producer_resume_offset")
    return count


def publish(config: Document, root: Path) -> None:
    events, _, wires = load_inputs(config)
    kafka = kafka_client(config)
    sdk = cast(ProducerSDK, kafka.sdk)
    producer = sdk.Producer(
        {
            **kafka.client_properties(),
            "enable.idempotence": True,
            "acks": "all",
            "linger.ms": 0,
            "message.timeout.ms": 10000,
            "allow.auto.create.topics": False,
        }
    )
    source = object_value(object_value(config["sources"])["input"])
    topic = string_value(source["topic"])
    stopped, deadline = lifetime(config)
    ledger_path = root / "producer-acks.jsonl"
    consumer = kafka.consumer(string_value(config["run_id"]) + "-publisher-resume")
    try:

        def record_at(offset: int) -> bytes:
            consumer.assign([kafka.sdk.TopicPartition(topic, 0, offset)])
            until = time.monotonic() + 10
            while time.monotonic() < until:
                message = consumer.poll(0.5)
                if message is not None:
                    require(
                        message.offset() == offset, "recording_producer_resume_read"
                    )
                    return message.value() or b""
            raise ValueError("recording_producer_resume_read")

        _, end = consumer.get_watermark_offsets(
            kafka.sdk.TopicPartition(topic, 0, 0), timeout=5, cached=False
        )
        start = resume_point(ledger_path, wires, topic, end, record_at)
    finally:
        consumer.close()
    first = integer_value(events[0]["native_timestamp_us"])
    # Native-time pacing restarts at the first undelivered event.
    resumed_us = integer_value(
        events[min(start, len(events) - 1)]["native_timestamp_us"]
    )
    began = time.monotonic() - (resumed_us - first) / 1000000
    count = start

    def status(value: str) -> None:
        durable_cursor(
            root / "producer-status.json",
            {
                "status": value,
                "acknowledged": count,
                "written_ms": time.time_ns() // 1000000,
            },
        )

    def wait_until(target: float) -> None:
        nonlocal began
        while time.monotonic() < target:
            require(
                not stopped() and time.monotonic() < deadline,
                "recording_producer_stopped",
            )
            if (root / "pause-publisher").exists():
                paused = time.monotonic()
                status("paused")
                while (root / "pause-publisher").exists():
                    require(
                        not stopped() and time.monotonic() < deadline,
                        "recording_producer_stopped",
                    )
                    time.sleep(0.05)
                delta = time.monotonic() - paused
                began += delta
                target += delta
            time.sleep(min(0.01, max(0.0, target - time.monotonic())))

    def delivery_callback(
        acknowledgements: list[Document], errors: list[str]
    ) -> Callable[[object, object], None]:
        def acknowledged(error: object, supplied: object) -> None:
            if error is not None:
                errors.append("unconfirmed_delivery")
                return
            message = cast(Acknowledged, supplied)
            acknowledgements.append(
                {
                    "topic": message.topic(),
                    "partition": message.partition(),
                    "offset": message.offset(),
                }
            )

        return acknowledged

    try:
        with ledger_path.open("ab" if ledger_path.exists() else "xb") as ledger:
            for index in range(start, len(wires)):
                wire = wires[index]
                require(
                    not stopped() and time.monotonic() < deadline,
                    "recording_producer_stopped",
                )
                if index < len(events):
                    wait_until(
                        began
                        + (integer_value(events[index]["native_timestamp_us"]) - first)
                        / 1000000
                    )
                acknowledgements: list[Document] = []
                errors: list[str] = []

                event = json_object(wire)
                producer.produce(
                    topic,
                    partition=0,
                    key=string_value(event["measurement_id"]).encode(),
                    value=wire,
                    on_delivery=delivery_callback(acknowledgements, errors),
                )
                require(
                    not producer.flush(10)
                    and not errors
                    and len(acknowledgements) == 1,
                    "recording_producer_unconfirmed",
                )
                ack = acknowledgements[0]
                require(
                    ack == {"topic": topic, "partition": 0, "offset": index},
                    "recording_producer_coordinate",
                )
                ledger.write(
                    json_line({**ack, "sha256": hashlib.sha256(wire).hexdigest()})
                )
                ledger.flush()
                os.fsync(ledger.fileno())
                count += 1
                status("running")
        status("completed")
    except (OSError, ValueError):
        status("stopped" if stopped() else "failed")
        raise
    finally:
        producer.flush(10)
