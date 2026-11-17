"""Play one recorded ULog flight as a virtual PX4 over MAVLink (ADR-0060).

The player owns everything about the file: it plans the packets
(telemetry/ulog_replay.py), claims a free system ID in the session directory,
writes the source declaration the gateway admits, then sends MAVLink 2 over
UDP at the pace of the recording. The gateway sees only MAVLink.

Control is by files beside the declaration, so `ops` can drive a player
without a network port: `<vehicle>.pause` holds every packet, the heartbeat
included, so the vehicle goes stale exactly as a silent physical one would;
`<vehicle>.stop` ends the player. Its status file says `running`, `paused`,
`ended` (end of file) or `stopped`. The ledger lists the identity and a content
hash of every position sent, which `ops verify` compares with the archive.
Output holds counts and states only, never values or coordinates.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import signal
import time
from pathlib import Path
from typing import Protocol, cast

from telemetry.continuous_archive import durable_cursor
from telemetry.conversion_contract import json_line
from telemetry.live_event import replay_position_identity, replay_scope
from telemetry.mavlink_position import native_position
from telemetry.ulog_replay import Packet, ReplayPlan, plan

FIRST_SYSTEM, LAST_SYSTEM = 2, 250
STATUS_PERIOD_S = 0.5


class Mav(Protocol):
    def heartbeat_send(self, *args: int) -> None: ...
    def sys_status_send(self, *args: int) -> None: ...
    def global_position_int_send(self, *args: int) -> None: ...


class Link(Protocol):
    mav: Mav

    def close(self) -> None: ...


def claim_system(folder: Path, vehicle: str) -> int:
    """First free system ID, claimed by exclusive creation; one per vehicle."""
    if (folder / f"{vehicle}.declaration.json").exists():
        raise ValueError("replay_vehicle_already_declared")
    for system in range(FIRST_SYSTEM, LAST_SYSTEM + 1):
        try:
            handle = os.open(
                folder / f"system-{system}.claim", os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
        except FileExistsError:
            continue
        with os.fdopen(handle, "w", encoding="utf-8") as claim:
            claim.write(vehicle)
        return system
    raise ValueError("replay_no_free_system")


def declare(folder: Path, replay: ReplayPlan, system: int) -> dict[str, object]:
    scope = replay_scope(replay.declaration(system))
    path = folder / f"{replay.vehicle}.declaration.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(json_line(scope))
    os.replace(temporary, path)
    return scope


def send(link: Link, packet: Packet) -> None:
    fields = packet.fields
    if packet.message == "HEARTBEAT":
        link.mav.heartbeat_send(
            fields["type"],
            fields["autopilot"],
            fields["base_mode"],
            fields["custom_mode"],
            fields["system_status"],
        )
    elif packet.message == "SYS_STATUS":
        # Sensor bitmasks, load, drop rate and error counters are not recorded.
        link.mav.sys_status_send(
            0,
            0,
            0,
            0,
            fields["voltage_battery"],
            fields["current_battery"],
            fields["battery_remaining"],
            0,
            0,
            0,
            0,
            0,
            0,
        )
    else:
        link.mav.global_position_int_send(
            fields["time_boot_ms"],
            fields["lat"],
            fields["lon"],
            fields["alt"],
            fields["relative_alt"],
            fields["vx"],
            fields["vy"],
            fields["vz"],
            fields["hdg"],
        )


def ledger_row(source_id: str, packet: Packet) -> bytes:
    """Identity and content hash of one position, as the gateway will see it."""
    native = native_position(
        {name: value for name, value in packet.fields.items() if name != "hdg"}
    )
    return json_line(
        {
            "measurement_id": replay_position_identity(
                source_id, packet.fields["time_boot_ms"]
            ),
            "native_sha256": hashlib.sha256(json_line(native)).hexdigest(),
        }
    )


def play(
    source: Path,
    folder: Path,
    host: str,
    port: int,
    start_us: int | None,
    end_us: int | None,
) -> str:
    replay = plan(source, start_us=start_us, end_us=end_us)
    folder.mkdir(mode=0o700, exist_ok=True)
    vehicle = replay.vehicle
    system = claim_system(folder, vehicle)
    (folder / f"{vehicle}.plan.json").write_bytes(json_line(replay.summary()))
    declare(folder, replay, system)
    os.environ["MAVLINK20"] = "1"
    mavutil = importlib.import_module("pymavlink.mavutil")
    link = cast(
        Link,
        mavutil.mavlink_connection(
            f"udpout:{host}:{port}", source_system=system, source_component=1
        ),
    )
    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("now", True))
    sent = 0
    position_us: int | None = None
    last_status = 0.0

    def status(state: str) -> None:
        durable_cursor(
            folder / f"{vehicle}.status.json",
            {
                "vehicle": vehicle,
                "system": system,
                "status": state,
                "sent": sent,
                "total": len(replay.packets),
                "position_native_us": position_us,
                "written_ms": time.time_ns() // 1_000_000,
            },
        )

    pause, halt = folder / f"{vehicle}.pause", folder / f"{vehicle}.stop"
    began = time.monotonic()
    outcome = "ended"
    with (folder / f"{vehicle}.ledger.jsonl").open("ab") as ledger:
        try:
            status("running")
            for packet in replay.packets:
                target = began + (packet.native_us - replay.first_us) / 1e6
                while True:
                    if stop["now"] or halt.exists():
                        outcome = "stopped"
                        break
                    now = time.monotonic()
                    if pause.exists():
                        held = now
                        status("paused")
                        while pause.exists() and not (stop["now"] or halt.exists()):
                            time.sleep(0.05)
                        began += time.monotonic() - held
                        target += time.monotonic() - held
                        status("running")
                        continue
                    if now >= target:
                        break
                    if now - last_status >= STATUS_PERIOD_S:
                        status("running")
                        last_status = now
                    time.sleep(min(0.02, target - now))
                if outcome == "stopped":
                    break
                if packet.message == "GLOBAL_POSITION_INT":
                    ledger.write(ledger_row(replay.source_id, packet))
                    position_us = packet.native_us
                send(link, packet)
                sent += 1
                if time.monotonic() - last_status >= STATUS_PERIOD_S:
                    ledger.flush()
                    os.fsync(ledger.fileno())
                    status("running")
                    last_status = time.monotonic()
            ledger.flush()
            os.fsync(ledger.fileno())
            status(outcome)
        except Exception:
            status("failed")
            raise
        finally:
            link.close()
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--players", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--start-us", type=int)
    parser.add_argument("--end-us", type=int)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.plan_only:
            print(
                json.dumps(
                    plan(
                        args.source, start_us=args.start_us, end_us=args.end_us
                    ).summary()
                )
            )
            return 0
        outcome = play(
            args.source, args.players, args.host, args.port, args.start_us, args.end_us
        )
    except Exception as error:
        # Trust boundary: decoder or socket errors may embed paths or values.
        category = str(error) if isinstance(error, ValueError) else type(error).__name__
        print(json.dumps({"status": "failed", "category": category[:64]}), flush=True)
        return 2
    print(json.dumps({"status": outcome}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
