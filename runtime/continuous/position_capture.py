"""Guarded continuous collector and independent archive/SQL position worker."""

import base64
import importlib
import os
import secrets
import time
from pathlib import Path
from typing import Protocol, cast

from runtime.continuous.live_position_worker import (
    Acknowledged,
    Mavutil,
    ProducerSDK,
)
from telemetry.continuous_archive import durable_cursor
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


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def immutable(path: Path, body: bytes) -> None:
    if path.exists():
        require(path.read_bytes() == body, "position_local_evidence_conflict")
        return
    with path.open("xb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())


def collector(plan: dict[str, object], root: Path) -> None:
    require_uuid_boundary()
    sdk = cast(ProducerSDK, importlib.import_module("confluent_kafka"))
    connection = cast(
        Mavutil, importlib.import_module("pymavlink.mavutil")
    ).mavlink_connection("udpin:0.0.0.0:14561")
    producer = sdk.Producer(
        {
            "bootstrap.servers": "127.0.0.1:19092",
            "acks": "all",
            "enable.idempotence": True,
            "message.timeout.ms": 10000,
        }
    )
    system, component = (
        integer_value(plan["system_id"]),
        integer_value(plan["component_id"]),
    )
    boot = string_value(plan["source_boot_session"])
    view = MavlinkView(
        "position-stream",
        boot,
        system,
        component,
        secrets.token_hex(12),
        time.monotonic(),
    )
    packets = root / "packets"
    packets.mkdir(exist_ok=True)
    require(not list(packets.iterdir()), "collector_resume_requires_publication_review")
    maximum = integer_value(plan["deliveries"])
    deadline = time.monotonic() + integer_value(plan["duration_seconds"])
    count, seq, last_boot = 0, 0, -1000
    last_status = 0.0
    selected_event, received_ms, received_mono = "", 0, -1.0
    fix_wire: bytes | None = None
    first: bytes | None = None
    failures: list[str] = []
    acks = root / "acks"
    acks.mkdir(exist_ok=True)

    def ack(error: object, supplied: object) -> None:
        if error is not None:
            failures.append("unconfirmed")
            return
        message = cast(Acknowledged, supplied)
        require(
            message.partition() == 0 and message.topic() == plan["input_topic"],
            "position_ack_scope",
        )
        immutable(
            acks / f"{message.offset():020d}.json",
            json_line(
                {
                    "offset": message.offset(),
                    "packet_index": count,
                }
            ),
        )

    def publish(body: bytes) -> None:
        nonlocal count
        event = json_object(body)
        producer.produce(
            string_value(plan["input_topic"]),
            partition=0,
            key=string_value(event["event_id"]).encode(),
            value=body,
            on_delivery=ack,
        )
        require(
            producer.flush(10) == 0 and not failures, "position_publish_unconfirmed"
        )
        count += 1

    completed = False
    try:
        while (
            count < maximum
            and time.monotonic() < deadline
            and not (root / "stop-collector").exists()
        ):
            now = time.monotonic()
            view.poll(now)
            view.watch.tick(now)
            if now - last_status >= 0.25:
                snapshot = view.snapshot(now)
                group = object_value(object_value(snapshot["groups"])["position"])
                status = string_value(group["status"])
                if received_mono < 0 or now - received_mono >= 3:
                    status = "stale" if selected_event else "unknown"
                durable_cursor(
                    root / "collector-status.json",
                    {
                        "epoch": view.watch.epoch,
                        "sequence": seq,
                        "collector_written_ms": time.time_ns() // 1_000_000,
                        "position_received_ms": received_ms,
                        "selected_event": selected_event,
                        "connection": snapshot["connection"],
                        "position_status": status
                        if snapshot["gateway_ok"]
                        else "unknown",
                        "accepted_deliveries": count,
                    },
                )
                seq += 1
                last_status = now
            if (root / "repeat-first").exists() and first is not None:
                original = (packets / "00000000000000000000.json").read_bytes()
                immutable(packets / f"{count:020d}.json", original)
                publish(first)
                (root / "repeat-first").unlink()
                continue
            packet = connection.recv_match(blocking=False, timeout=None)
            if packet is None:
                time.sleep(0.01)
                continue
            kind = packet.get_type()
            if kind not in ("GPS_RAW_INT", "GLOBAL_POSITION_INT", "HEARTBEAT"):
                continue
            data = packet.to_dict()
            accepted = view.accept(
                kind,
                data,
                packet.get_srcSystem(),
                packet.get_srcComponent(),
                now,
                time.time_ns() // 1_000_000,
            )
            if not accepted:
                continue
            if kind == "GPS_RAW_INT":
                fix_wire = bytes(packet.get_msgbuf())
                continue
            if kind != "GLOBAL_POSITION_INT":
                continue
            position = view.observations.get("position")
            if (
                position is None
                or position.boot_ms is None
                or fix_wire is None
                or position.qualification != "fix_qualified"
                or position.boot_ms - last_boot < 1000
            ):
                continue
            event = make_input(data, boot, system, component)
            body = json_line(event)
            immutable(
                packets / f"{count:020d}.json",
                json_line(
                    {
                        "event": event,
                        "position_packet_b64": base64.b64encode(
                            bytes(packet.get_msgbuf())
                        ).decode(),
                        "fix_packet_b64": base64.b64encode(fix_wire).decode(),
                    }
                ),
            )
            publish(body)
            first = first or body
            last_boot = position.boot_ms
            selected_event, received_ms, received_mono = (
                string_value(event["event_id"]),
                time.time_ns() // 1_000_000,
                now,
            )
        completed = True
    finally:
        connection.close()
        immutable(
            root / "collector-finished.json",
            json_line(
                {
                    "deliveries": count,
                    "status": "complete" if completed else "failed",
                }
            ),
        )


class Packet(Protocol):
    def get_type(self) -> str: ...
    def get_srcSystem(self) -> int: ...
    def get_srcComponent(self) -> int: ...
    def to_dict(self) -> dict[str, object]: ...


class Parser(Protocol):
    def parse_buffer(self, body: bytes) -> list[Packet] | None: ...


class Dialect(Protocol):
    def MAVLink(self, sink: object) -> Parser: ...


def validate_packet(body: bytes, plan: dict[str, object]) -> dict[str, object]:
    raw = json_object(body)
    dialect = cast(Dialect, importlib.import_module("pymavlink.dialects.v20.common"))
    values = []
    for key, kind in (
        ("position_packet_b64", "GLOBAL_POSITION_INT"),
        ("fix_packet_b64", "GPS_RAW_INT"),
    ):
        packets = dialect.MAVLink(None).parse_buffer(
            base64.b64decode(string_value(raw[key]), validate=True)
        )
        require(packets is not None and len(packets) == 1, "position_packet_shape")
        packet = cast(list[Packet], packets)[0]
        require(
            packet.get_type() == kind
            and packet.get_srcSystem() == plan["system_id"]
            and packet.get_srcComponent() == plan["component_id"],
            "position_packet_scope",
        )
        values.append(packet.to_dict())
    event = make_input(
        values[0],
        string_value(plan["source_boot_session"]),
        integer_value(plan["system_id"]),
        integer_value(plan["component_id"]),
    )
    require(
        event == raw["event"] and integer_value(values[1]["fix_type"]) >= 3,
        "position_packet_content",
    )
    return event
