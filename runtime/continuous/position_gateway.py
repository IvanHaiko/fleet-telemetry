"""Forward bounded PX4 SITL MAVLink positions to an isolated Kafka topic."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import time
from pathlib import Path
from typing import Protocol, cast

from runtime.continuous.kafka import Kafka
from telemetry.position_live import PositionView


class MavMessage(Protocol):
    def get_type(self) -> str: ...
    def get_srcSystem(self) -> int: ...
    def to_dict(self) -> dict[str, object]: ...


class MavConnection(Protocol):
    def recv_match(self, *, blocking: bool, timeout: float) -> MavMessage | None: ...
    def close(self) -> None: ...


class Mavutil(Protocol):
    def mavlink_connection(self, address: str) -> MavConnection: ...


def run(config_path: Path, port: int) -> None:
    config = cast(dict[str, object], json.loads(config_path.read_bytes()))
    source = cast(dict[str, str], config["input_source"])
    ids = config["system_ids"]
    if not isinstance(ids, list):
        raise ValueError("position_vehicle_scope")
    view = PositionView(set(ids))
    kafka = Kafka(
        cast(str, config["bootstrap"]),
        source["cluster_id"],
        config.get("kafka_connection"),
    )
    if kafka.describe(source["topic"]) != source:
        raise ValueError("position_input_identity")
    producer = kafka.sdk.Producer(
        {
            **kafka.client_properties(),
            "enable.idempotence": True,
            "acks": "all",
            "linger.ms": 0,
            "message.timeout.ms": 10000,
        }
    )
    mavutil = cast(Mavutil, importlib.import_module("pymavlink.mavutil"))
    connections = [
        mavutil.mavlink_connection(f"udpin:127.0.0.1:{port + instance}")
        for instance in range(10)
    ]
    fixes: dict[int, tuple[int, float]] = {}
    errors = 0
    cursor = 0

    def acknowledged(error: object, message: object) -> None:
        nonlocal errors
        if error is not None:
            errors += 1

    try:
        while True:
            msg = None
            for offset in range(len(connections)):
                index = (cursor + offset) % len(connections)
                msg = connections[index].recv_match(blocking=False, timeout=0.0)
                if msg is not None:
                    cursor = (index + 1) % len(connections)
                    break
            producer.poll(0)
            if errors:
                raise RuntimeError("position_publish_failed")
            if msg is None:
                time.sleep(0.01)
                continue
            system_id = msg.get_srcSystem()
            if system_id not in view.vehicle_ids:
                continue
            data = msg.to_dict()
            now = time.monotonic()
            if msg.get_type() == "GPS_RAW_INT":
                fix = data.get("fix_type")
                if type(fix) is int:
                    fixes[system_id] = (fix, now)
                continue
            if msg.get_type() != "GLOBAL_POSITION_INT":
                continue
            fix = fixes.get(system_id)
            if fix is None or now - fix[1] > 3 or fix[0] < 3:
                continue
            row = {
                "format_version": "simulated-position-v1",
                "source": "px4-sitl",
                "system_id": system_id,
                "boot_ms": data.get("time_boot_ms"),
                "latitude_e7": data.get("lat"),
                "longitude_e7": data.get("lon"),
                "altitude_msl_mm": data.get("alt"),
                "relative_altitude_mm": data.get("relative_alt"),
                "fix_type": fix[0],
            }
            try:
                previous = view.positions.get(system_id)
                boot = row["boot_ms"]
                if previous and type(boot) is int and boot - previous.boot_ms < 200:
                    continue
                if not view.accept(row, now):
                    continue
            except ValueError:
                continue
            key = str(system_id).encode()
            partition = int(hashlib.sha256(key).hexdigest(), 16) % 18
            producer.produce(
                source["topic"],
                partition=partition,
                key=key,
                value=json.dumps(row, separators=(",", ":")).encode(),
                on_delivery=acknowledged,
            )
    finally:
        for connection in connections:
            connection.close()
        if producer.flush(10) or errors:
            print(json.dumps({"event": "position_gateway_unconfirmed"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--port", type=int, default=14540)
    args = parser.parse_args()
    run(args.config, args.port)
