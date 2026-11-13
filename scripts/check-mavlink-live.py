"""Bounded interruption/recovery drill for the isolated PX4 SITL live profile."""

import argparse
import hashlib
import http.client
import ipaddress
import json
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from telemetry.conversion_contract import (
    integer_value,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded

SITL_IMAGE = (
    "px4io/px4-sitl@sha256:"
    "39d5a950208a5a45fccbbb0670bd8716663ed0b350ef738447581395e0c92d97"
)


def docker(*args: str) -> str:
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True, timeout=20
    ).stdout.strip()


def request(
    token: str, path: str = "/v1/mavlink", method: str = "GET"
) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", 18771, timeout=1)
    try:
        connection.request(method, path, headers={"Authorization": "Bearer " + token})
        response = connection.getresponse()
        body = response.read(1_048_577)
        if len(body) > 1_048_576:
            raise ValueError("live_response_bound")
        return response.status, body
    finally:
        connection.close()


def group(snapshot: dict[str, object], name: str) -> dict[str, object]:
    return object_value(object_value(snapshot["groups"])[name])


def check(config: Path, output: Path, project: str) -> dict[str, object]:
    if output.exists() or not output.parent.is_dir():
        raise ValueError("fresh_report_required")
    if re.fullmatch(r"fleetmavlink[a-z0-9-]{0,40}", project) is None:
        raise ValueError("isolated_sitl_project_required")
    spec = json_object(read_bounded(config, 8192))
    if spec.get("source_kind") != "px4-sitl":
        raise ValueError("simulation_only_drill")
    token = string_value(spec["reader_token"])
    simulator, gateway = project + "-sitl-1", project + "-gateway-1"
    if docker("inspect", simulator, "--format", "{{.Config.Image}}") != SITL_IMAGE:
        raise ValueError("unexpected_simulator_image")
    address = docker(
        "inspect",
        gateway,
        "--format",
        '{{(index .NetworkSettings.Networks "'
        + project
        + '_live-internal").IPAddress}}',
    )
    if not ipaddress.ip_address(address).is_private:
        raise ValueError("private_gateway_required")
    snapshots: dict[str, object] = {}

    def wait(
        name: str, predicate: Callable[[dict[str, object]], bool], seconds: float = 15
    ) -> dict[str, object]:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                status, body = request(token)
                if status == 200:
                    snapshot = json_object(body)
                    if predicate(snapshot):
                        snapshots[name] = snapshot
                        return snapshot
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(0.05)
        raise ValueError("live_drill_deadline_" + name)

    def fresh(snapshot: dict[str, object]) -> bool:
        return (
            snapshot["gateway_ok"] is True
            and snapshot["connection"] == "connected"
            and all(
                group(snapshot, name)["status"] == "fresh"
                for name in ("position", "battery", "state", "gps_fix")
            )
        )

    def start() -> None:
        docker(
            "exec",
            simulator,
            "/opt/px4/bin/px4-mavlink",
            "start",
            "-u",
            "14620",
            "-o",
            str(integer_value(spec["udp_port"])),
            "-t",
            address,
            "-m",
            "onboard",
            "-r",
            "20000",
        )

    baseline = wait("baseline", fresh)
    if request("invalid-token")[0] != 401 or request(token, method="POST")[0] != 405:
        raise ValueError("read_only_api_auth")
    stopped_at = time.monotonic()
    docker("exec", simulator, "/opt/px4/bin/px4-mavlink", "stop-all")
    wait(
        "source_silent",
        lambda row: row["gateway_ok"] is True and row["connection"] == "lost",
    )
    loss_seconds = time.monotonic() - stopped_at
    # The last position/battery can arrive after the last heartbeat. Each must
    # expire against its own receipt time, rather than the heartbeat deadline.
    wait(
        "measurements_stale",
        lambda row: (
            row["connection"] == "lost"
            and all(
                group(row, name)["status"] == "stale"
                for name in ("position", "battery", "state")
            )
        ),
    )
    resume_at = time.monotonic()
    start()
    resumed = wait("source_resumed", fresh)
    recovery_seconds = time.monotonic() - resume_at
    if integer_value(group(resumed, "position")["source_boot_ms"]) <= integer_value(
        group(baseline, "position")["source_boot_ms"]
    ):
        raise ValueError("source_did_not_advance")
    docker("exec", simulator, "/opt/px4/bin/px4-mavlink", "stop-all")
    restart_at = time.monotonic()
    docker("restart", gateway)
    unknown = wait(
        "gateway_restarted_without_source",
        lambda row: row["gateway_ok"] is True and row["connection"] == "unknown",
    )
    if unknown["receiver_epoch"] == resumed["receiver_epoch"] or any(
        group(unknown, name)["values"] is not None
        for name in ("position", "battery", "state")
    ):
        raise ValueError("restart_reused_fresh_state")
    start()
    final = wait("gateway_recovered", fresh)
    restart_seconds = time.monotonic() - restart_at
    for snapshot in (baseline, resumed, final):
        position = group(snapshot, "position")
        boot = integer_value(position["source_boot_ms"])
        expected = (
            "sha256:"
            + hashlib.sha256(
                f"px4-mavlink-position-v1:{spec['source_boot_session']}:{spec['system_id']}:"
                f"{spec['component_id']}:GLOBAL_POSITION_INT:{boot}".encode()
            ).hexdigest()
        )
        if position["event_id"] != expected:
            raise ValueError("position_identity_not_native")
        if (
            group(snapshot, "battery")["event_id"] is not None
            or group(snapshot, "battery")["source_boot_ms"] is not None
        ):
            raise ValueError("invented_battery_identity_or_time")
    if final["source_boot_session"] != baseline["source_boot_session"]:
        raise ValueError("gateway_changed_source_session")
    # Stop only this new simulator's file logger; retain its bounded startup log.
    docker("exec", simulator, "/opt/px4/bin/px4-logger", "stop")
    resources = docker(
        "stats", "--no-stream", "--format", "{{json .}}", gateway, simulator
    )
    oom = {
        name: docker("inspect", name, "--format", "{{.State.OOMKilled}}")
        for name in (gateway, simulator)
    }
    if any(value != "false" for value in oom.values()):
        raise ValueError("live_profile_oom")
    report: dict[str, object] = {
        "status": "passed",
        "source_kind": "px4-sitl",
        "privacy": "restricted",
        "source_stop_to_observed_loss_seconds": loss_seconds,
        "source_resume_to_fresh_seconds": recovery_seconds,
        "gateway_restart_and_source_resume_seconds": restart_seconds,
        "source_session_preserved": True,
        "position_identity_verified": True,
        "restart_unknown_until_new_packets": True,
        "reader_auth_and_no_post": True,
        "snapshots": snapshots,
        "docker_stats": resources,
        "oom_killed": oom,
        "limitations": [
            "one live simulator; no radio or physical flight",
            "receipt age is not physical measurement age",
            "unsigned MAVLink has no general replay protection",
            "no durable archive or integrated Kafka/Flink replay",
        ],
    }
    with output.open("xb") as handle:
        handle.write(json.dumps(report, sort_keys=True, indent=2).encode() + b"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project", default="fleetmavlink20261104")
    args = parser.parse_args()
    result = check(args.config, args.output, args.project)
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key
                in {
                    "status",
                    "source_kind",
                    "source_stop_to_observed_loss_seconds",
                    "source_resume_to_fresh_seconds",
                    "gateway_restart_and_source_resume_seconds",
                }
            }
        )
    )
