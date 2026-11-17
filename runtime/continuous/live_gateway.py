"""Live MAVLink gateway: durable raw capture, then Kafka publication.

ADR-0054 for one PX4 SITL source; ADR-0060 for a fleet of declared vehicles.

Each start is a new gateway epoch. Every packet from the configured system and
component is appended to the epoch's capture file and fsynced before anything
is published. Position, battery summary and state packets then become
`px4-live-event-v1` events on partition 0 of the run's input topic, each
confirmed at the expected offset and written to an acknowledgement ledger.
Other packets stay in the capture only. SIGUSR1 completes the session; SIGTERM
stops this epoch and a later start continues the same session. The live
worker's `gateway` role is the entry point.
"""

from __future__ import annotations

import base64
import importlib
import os
import secrets
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from runtime.continuous.live_position_worker import Acknowledged, ProducerSDK
from runtime.continuous.recording_config import kafka_client, require
from telemetry.continuous_archive import durable_cursor
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.fleet_runtime import (
    FLEET_PROFILE,
    MAX_VEHICLES,
    runtime_session,
)
from telemetry.live_event import (
    MESSAGES,
    event_bytes,
    event_key,
    make_event,
    replay_scope,
)
from telemetry.live_runtime import (
    Document,
)
from telemetry.local_io import read_bounded

MAX_GATEWAY_SECONDS = 3600


class Message(Protocol):
    def get_type(self) -> str: ...
    def get_srcSystem(self) -> int: ...
    def get_srcComponent(self) -> int: ...
    def get_msgbuf(self) -> bytes | bytearray: ...
    def get_seq(self) -> int: ...
    def to_dict(self) -> dict[str, object]: ...


class Connection(Protocol):
    def recv_msg(self) -> Message | None: ...
    def close(self) -> None: ...


class Mavutil(Protocol):
    def mavlink_connection(self, address: str) -> Connection: ...


def header(raw: bytes) -> tuple[int, int, int] | None:
    """Sequence, system and component from a MAVLink 2 or 1 frame header.

    pymavlink leaves these unset for message IDs outside its dialect, so the
    capture reads them from the packet bytes.
    """
    if len(raw) >= 10 and raw[0] == 0xFD:
        return raw[4], raw[5], raw[6]
    if len(raw) >= 8 and raw[0] == 0xFE:
        return raw[2], raw[3], raw[4]
    return None


@dataclass
class Vehicle:
    """Receive state of one declared system; one refusal stops only it."""

    source: Document
    last_seq: int | None = None
    sequence_gaps: int = 0
    lost_packets: int = 0
    last_receipt_ms: int | None = None
    last_heartbeat_ms: int | None = None
    last_position: tuple[int, bytes] | None = None
    refusal: str | None = None
    published: int = 0

    def summary(self) -> Document:
        source = self.source
        return {
            "label": source.get("label", source["vehicle"]),
            "kind": source["kind"],
            "system": source["system"],
            "last_receipt_ms": self.last_receipt_ms,
            "last_heartbeat_ms": self.last_heartbeat_ms,
            "published": self.published,
            "refusal": self.refusal,
            "sequence_gaps": self.sequence_gaps,
            "lost_packets": self.lost_packets,
        }


def declarations(folder: Path) -> list[Document]:
    """Replay declarations the players wrote (ADR-0060), validated."""
    if not folder.is_dir():
        return []
    return [
        replay_scope(json_object(read_bounded(path, 8192)))
        for path in sorted(folder.glob("*.declaration.json"))[:MAX_VEHICLES]
    ]


class Gateway:
    """One epoch of capture and publication; caller owns the receive loop."""

    def __init__(self, config: Document, root: Path) -> None:
        self.config, self.root = config, root
        session = object_value(config["session"])
        self.fleet = session.get("profile") == FLEET_PROFILE
        self.session = runtime_session(session)
        self.run_id = string_value(self.session["run_id"])
        self.vehicles: dict[tuple[int, int], Vehicle] = {}
        if not self.fleet:
            self._declare(object_value(self.session["source"]))
        self.limit = integer_value(config["max_deliveries"])
        self.epoch = secrets.token_hex(16)
        self.sequence = 0
        self.published = 0
        self.foreign = self.bad_data = 0
        self.pending: list[bytes] = []
        self.capture = (root / f"capture-{self.epoch}.jsonl").open("xb")
        self.ledger = (root / f"gateway-acks-{self.epoch}.jsonl").open("xb")
        self.refresh()

    def _declare(self, source: Document) -> None:
        address = (integer_value(source["system"]), integer_value(source["component"]))
        known = self.vehicles.get(address)
        if known is not None:
            require(known.source == source, "live_gateway_declaration_changed")
            return
        names = {v.source["vehicle"] for v in self.vehicles.values()}
        require(source["vehicle"] not in names, "live_gateway_vehicle_repeated")
        self.vehicles[address] = Vehicle(source)

    def refresh(self) -> None:
        """Admit vehicles declared since the last look; never forget one."""
        if self.fleet:
            for source in declarations(self.root / "players"):
                self._declare(source)

    def _latest(self, name: str) -> int | None:
        known = [
            value
            for value in (getattr(v, name) for v in self.vehicles.values())
            if value is not None
        ]
        return max(known) if known else None

    def status(self, state: str) -> None:
        refusals = [v.refusal for v in self.vehicles.values() if v.refusal]
        refusal = None
        if refusals:
            refusal = "vehicle_refused" if self.fleet else refusals[0]
        durable_cursor(
            self.root / "gateway-status.json",
            {
                "epoch": self.epoch,
                "status": state,
                "written_ms": time.time_ns() // 1_000_000,
                "last_receipt_ms": self._latest("last_receipt_ms"),
                "last_heartbeat_ms": self._latest("last_heartbeat_ms"),
                "published": self.published,
                "captured": self.sequence,
                "refusal": refusal,
                "sequence_gaps": sum(v.sequence_gaps for v in self.vehicles.values()),
                "lost_packets": sum(v.lost_packets for v in self.vehicles.values()),
                "foreign_packets": self.foreign,
                "bad_data": self.bad_data,
                "vehicles": {
                    string_value(v.source["vehicle"]): v.summary()
                    for v in self.vehicles.values()
                },
            },
        )

    def receive(self, message: Message, received_ms: int) -> bytes | None:
        """Stage one packet's capture record; return the event to publish.

        The caller persists the staged records before publishing any event.
        """
        # Every parsed packet is captured. Only declared systems are
        # published; IDs are filters, not proof of the producer.
        raw = bytes(message.get_msgbuf())
        seq, system, component = header(raw) or (
            message.get_seq(),
            message.get_srcSystem(),
            message.get_srcComponent(),
        )
        vehicle = self.vehicles.get((system, component))
        if vehicle is None and self.fleet:
            self.refresh()
            vehicle = self.vehicles.get((system, component))
        self.foreign += vehicle is None
        kind = message.get_type()
        sequence = self.sequence
        self.sequence += 1
        event: Document | None = None
        if vehicle is not None:
            # MAVLink's 8-bit packet sequence is per sender: loss is per vehicle.
            last = vehicle.last_seq
            if last is not None and seq != (last + 1) % 256:
                vehicle.sequence_gaps += 1
                vehicle.lost_packets += (seq - last - 1) % 256
            vehicle.last_seq = seq
            vehicle.last_receipt_ms = received_ms
            event = self._event(vehicle, kind, message, sequence, received_ms)
        record = {
            "sequence": sequence,
            "received_unix_ms": received_ms,
            "message": kind,
            "system": system,
            "component": component,
            "mavlink_seq": seq,
            "packet_b64": base64.b64encode(raw).decode(),
            "published": event is not None,
        }
        self.pending.append(json_line(record))
        return None if event is None else event_bytes(event)

    def _event(
        self,
        vehicle: Vehicle,
        kind: str,
        message: Message,
        sequence: int,
        received_ms: int,
    ) -> Document | None:
        if kind not in MESSAGES or vehicle.refusal is not None:
            return None
        data = {k: v for k, v in message.to_dict().items() if k != "mavpackettype"}
        try:
            event: Document | None = make_event(
                self.run_id,
                vehicle.source,
                kind,
                data,
                self.epoch,
                sequence,
                received_ms,
            )
        except ValueError as error:
            vehicle.refusal = str(error)
            return None
        if event is not None and kind == "GLOBAL_POSITION_INT":
            event = self._position(vehicle, event)
        if event is not None:
            if kind == "HEARTBEAT":
                vehicle.last_heartbeat_ms = received_ms
            vehicle.published += 1
        return event

    def persist(self) -> None:
        """Durably append every staged capture record with one fsync."""
        if self.pending:
            self.capture.write(b"".join(self.pending))
            self.capture.flush()
            os.fsync(self.capture.fileno())
            self.pending.clear()

    @staticmethod
    def _position(vehicle: Vehicle, event: Document) -> Document | None:
        """ADR-0045 rules: a boot-time decrease or competing content refuses."""
        boot = integer_value(event["native_time_boot_ms"])
        native = json_line(event["native"])
        if vehicle.last_position is not None:
            last_boot, last_native = vehicle.last_position
            if boot < last_boot:
                vehicle.refusal = "source_clock_reset_requires_new_boot_session"
                return None
            if boot == last_boot:
                if native != last_native:
                    vehicle.refusal = "competing_position_at_source_time"
                return None  # a repeated position renews nothing
        vehicle.last_position = (boot, native)
        return event

    def acknowledged(self, first: int, wires: list[bytes]) -> None:
        self.ledger.write(
            b"".join(
                json_line(
                    {
                        "offset": first + index,
                        "key": event_key(json_object(wire)),
                        "bytes": len(wire),
                    }
                )
                for index, wire in enumerate(wires)
            )
        )
        self.ledger.flush()
        os.fsync(self.ledger.fileno())
        self.published += len(wires)

    def close(self) -> None:
        self.capture.close()
        self.ledger.close()


def run(config: Document, root: Path) -> str:
    kafka = kafka_client(config)
    topic = string_value(
        object_value(object_value(config["sources"])["input"])["topic"]
    )
    consumer = kafka.consumer(string_value(config["run_id"]) + "-gateway")
    try:
        position = kafka.sdk.TopicPartition(topic, 0, 0)
        _, next_offset = consumer.get_watermark_offsets(
            position, timeout=5, cached=False
        )
    finally:
        consumer.close()
    require((root / "gateway-complete.json").exists() is False, "live_session_done")
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
    mavutil = cast(Mavutil, importlib.import_module("pymavlink.mavutil"))
    link = mavutil.mavlink_connection(
        f"udpin:0.0.0.0:{integer_value(config['udp_port'])}"
    )
    gateway = Gateway(config, root)
    flags = {"stop": False, "complete": False}
    signal.signal(signal.SIGTERM, lambda *_: flags.__setitem__("stop", True))
    signal.signal(signal.SIGUSR1, lambda *_: flags.__setitem__("complete", True))
    seconds = integer_value(config["duration_seconds"])
    require(1 <= seconds <= MAX_GATEWAY_SECONDS, "live_gateway_lifetime")
    deadline = time.monotonic() + seconds
    last_status = 0.0

    def confirm(wires: list[bytes]) -> None:
        """Publish one batch; every event must land at the next offsets in order."""
        nonlocal next_offset
        require(next_offset + len(wires) <= gateway.limit, "live_gateway_limit")
        acks: list[int] = []
        errors: list[str] = []

        def delivered(error: object, supplied: object) -> None:
            if error is not None:
                errors.append("unconfirmed")
            else:
                acks.append(cast(Acknowledged, supplied).offset())

        for wire in wires:
            producer.produce(
                topic,
                partition=0,
                key=event_key(json_object(wire)).encode(),
                value=wire,
                on_delivery=cast(Callable[[object, object], None], delivered),
            )
        expected = list(range(next_offset, next_offset + len(wires)))
        require(
            not producer.flush(10) and not errors and acks == expected,
            "live_gateway_unconfirmed",
        )
        gateway.acknowledged(next_offset, wires)
        next_offset += len(wires)

    outcome = "stopped"
    try:
        gateway.status("running")
        while not flags["stop"] and not flags["complete"]:
            if time.monotonic() >= deadline:
                outcome = "deadline"
                break
            # Drain what has arrived, capture it durably, then publish.
            wires: list[bytes] = []
            for _ in range(256):
                message = link.recv_msg()
                if message is None:
                    break
                if message.get_type() == "BAD_DATA":
                    gateway.bad_data += 1
                else:
                    wire = gateway.receive(message, time.time_ns() // 1_000_000)
                    if wire is not None:
                        wires.append(wire)
            gateway.persist()
            if wires:
                confirm(wires)
            else:
                time.sleep(0.005)
            if time.monotonic() - last_status >= 0.5:
                gateway.refresh()
                gateway.status("running")
                last_status = time.monotonic()
        if flags["complete"]:
            outcome = "completed"
            gateway.status("completed")
            durable_cursor(
                root / "gateway-complete.json",
                {
                    "status": "completed",
                    "published": next_offset,
                    "written_ms": time.time_ns() // 1_000_000,
                },
            )
        else:
            gateway.status("stopped")
        return outcome
    except (OSError, ValueError):
        gateway.status("failed")
        raise
    finally:
        gateway.persist()
        producer.flush(10)
        gateway.close()
        link.close()
