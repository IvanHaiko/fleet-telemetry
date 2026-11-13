"""Bounded F09 publication, independent input archival and archive-gated serving."""

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
    first = integer_value(events[0]["native_timestamp_us"])
    began = time.monotonic()
    count = 0

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
        with (root / "producer-acks.jsonl").open("xb") as ledger:
            for index, wire in enumerate(wires):
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
        status("failed")
        raise
    finally:
        producer.flush(10)
