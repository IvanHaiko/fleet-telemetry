"""Run the isolated 16-position live PX4 source-to-query demonstration."""

import argparse
import base64
import hashlib
import json
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.live_position_verify import (  # noqa: E402
    archive,
    reconcile,
    require,
    save,
    sql_check,
)
from telemetry.conversion_contract import (  # noqa: E402
    integer_value,
    json_object,
    object_value,
)

__all__ = ["archive", "reconcile", "require", "save", "sql_check"]

PROJECT = "fleetliveposition20261104"
SITL = "fleetmavlink20261104-sitl-1"
SOURCE_NETWORK = "fleetmavlink20261104_live-internal"


def project(root: Path) -> str:
    return PROJECT + "-" + root.name.rsplit("-", 1)[1]


def verify_export(root: Path) -> None:
    manifest = json_object((root / "source-manifest.json").read_bytes())
    actual = {
        path.relative_to(root / "source").as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted((root / "source").rglob("*.py"))
    }
    require(actual == manifest, "frozen_source_export_changed")


def command(args: list[str], *, timeout: int = 90) -> str:
    result = subprocess.run(
        args, cwd=ROOT, capture_output=True, timeout=timeout, check=False
    )
    if result.returncode:
        # Retain diagnostics locally; do not print generated credentials/config.
        raise RuntimeError(
            "local_command_failed: " + result.stderr.decode(errors="replace")[-2000:]
        )
    return result.stdout.decode(errors="strict")


def compose(root: Path, *args: str, timeout: int = 90) -> str:
    return command(
        [
            "docker",
            "compose",
            "--env-file",
            str(root / "runtime.env"),
            "-f",
            "compose/live-position-path.yml",
            "-p",
            project(root),
            *args,
        ],
        timeout=timeout,
    )


def prepare(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=False)
    live = json_object(
        (ROOT / ".local-discovery/mavlink-live-20261104-001/live.json").read_bytes()
    )
    # Explicit existing artifacts, not ambient SDK discovery or installation.
    packages = ROOT / ".local-discovery/sim-map-20261103/linux-packages"
    sdk = ROOT / ".local-discovery/m4-archive-20261022-001/sdk/Lib/site-packages"
    require(packages.is_dir() and sdk.is_dir(), "retained_sdk_required")
    export = root / "source"
    export.mkdir()
    for path in ROOT.glob("*.py"):
        shutil.copy2(path, export / path.name)
    for directory in ("telemetry", "runtime", "scripts"):
        for path in (ROOT / directory).rglob("*.py"):
            if "__pycache__" not in path.parts:
                target = export / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    manifest = {
        path.relative_to(export).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(export.rglob("*.py"))
    }
    save(root / "source-manifest.json", cast(dict[str, object], manifest))
    credentials: dict[str, object] = {
        name: {"access": "live-" + name, "secret": secrets.token_hex(24)}
        for name in ("admin", "writer", "reader")
    }
    credentials.update(
        ch_admin=secrets.token_hex(24),
        ch_reader=secrets.token_hex(24),
        s3_sdk=str(sdk),
    )
    save(root / "credentials.json", credentials)
    bucket = "live-position-20261104"
    identities = []
    for name in ("admin", "writer", "reader"):
        item = object_value(credentials[name])
        actions = (
            ["Admin"]
            if name == "admin"
            else [
                "Read:" + bucket,
                "List:" + bucket,
                *(["Write:" + bucket] if name == "writer" else []),
            ]
        )
        identities.append(
            {
                "name": name,
                "credentials": [
                    {"accessKey": item["access"], "secretKey": item["secret"]}
                ],
                "actions": actions,
            }
        )
    save(root / "s3.json", {"identities": identities})
    cluster = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode().rstrip("=")
    plan: dict[str, object] = {
        "format_version": "live-position-slice-v1",
        "run_id": "live-position-001",
        "cluster_id": cluster,
        "evidence": "/evidence",
        "deliveries": 18,
        "input_topic": "live-position-input-001",
        "output_topic": "live-position-facts-001",
        "group": "live-position-flink-001",
        "source_boot_session": live["source_boot_session"],
        "system_id": live["system_id"],
        "component_id": live["component_id"],
        "bucket": bucket,
        "prefix": "archive-v1/live-position-001/",
    }
    save(root / "plan.json", plan)
    env = {
        "M3_SOURCE_ROOT": export.as_posix(),
        "LIVE_POSITION_EVIDENCE": root.as_posix(),
        "LIVE_POSITION_PACKAGES": packages.as_posix(),
        "LIVE_POSITION_CLUSTER_ID": cluster,
        "M4_S3_CONFIG": (root / "s3.json").as_posix(),
        "LIVE_POSITION_CH_PASSWORD": credentials["ch_admin"],
        "FLIGHT_CH_ADMIN_PASSWORD": credentials["ch_admin"],
        # Compose interpolates the whole extends file, including unused Grafana.
        "FLIGHT_CH_READER_PASSWORD": credentials["ch_reader"],
        "FLIGHT_GRAFANA_PASSWORD": secrets.token_hex(24),
    }
    (root / "runtime.env").write_text(
        "".join(f"{key}={value}\n" for key, value in env.items()), encoding="utf-8"
    )
    compose(root, "config", "--quiet")


def flink_json(path: str) -> dict[str, object]:
    # Explicit numeric loopback; ignore proxy environment and redirects.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("http://127.0.0.1:28081" + path, timeout=5) as response:
        return json_object(response.read(1_048_576))


def start_capture(root: Path) -> None:
    verify_export(root)
    compose(
        root,
        "up",
        "-d",
        "--pull",
        "never",
        "kafka",
        "jobmanager",
        "taskmanager",
        "archive",
        "clickhouse",
    )
    deadline = time.monotonic() + 90
    while True:
        try:
            require(
                integer_value(flink_json("/overview")["taskmanagers"]) == 1,
                "flink_not_ready",
            )
            break
        except (OSError, ValueError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)
    print("Runtime ready; initializing fresh topics.", flush=True)
    compose(
        root,
        "run",
        "--rm",
        "--no-deps",
        "worker",
        "initialize",
        "--config",
        "/evidence/plan.json",
    )
    submitted = compose(
        root,
        "exec",
        "-T",
        "jobmanager",
        "/opt/m3/entrypoint.sh",
        "submit",
        "-d",
        "-py",
        "/workspace/runtime/pyflink/mavlink_position_job.py",
        "--config",
        "/evidence/plan.json",
        timeout=90,
    )
    (root / "flink-submit.txt").write_text(submitted, encoding="utf-8")
    match = re.search(r"JobID\s+([0-9a-f]{32})", submitted)
    require(match is not None, "flink_submission_id")
    job_id = cast(re.Match[str], match).group(1)
    save(root / "flink-job.json", {"job_id": job_id})
    print("Flink submitted; capturing new live packets.", flush=True)
    kafka = json.loads(command(["docker", "inspect", project(root) + "-kafka-1"]))
    ip = kafka[0]["NetworkSettings"]["Networks"][SOURCE_NETWORK]["IPAddress"]
    require(isinstance(ip, str) and ip.startswith("10.254.247."), "live_network_target")
    args = [
        "docker",
        "compose",
        "--env-file",
        str(root / "runtime.env"),
        "-f",
        "compose/live-position-path.yml",
        "-p",
        project(root),
        "run",
        "--name",
        project(root) + "-capture",
        "--no-deps",
        "worker",
        "capture",
        "--config",
        "/evidence/plan.json",
    ]
    with (root / "capture-output.txt").open("xb") as output:
        process = subprocess.Popen(args, cwd=ROOT, stdout=output, stderr=output)
        try:
            time.sleep(2)
            command(
                [
                    "docker",
                    "exec",
                    SITL,
                    "/opt/px4/bin/px4-mavlink",
                    "start",
                    "-u",
                    "14621",
                    "-o",
                    "14561",
                    "-t",
                    ip,
                    "-m",
                    "custom",
                    "-r",
                    "20000",
                ]
            )
            for stream in ("GPS_RAW_INT", "GLOBAL_POSITION_INT"):
                command(
                    [
                        "docker",
                        "exec",
                        SITL,
                        "/opt/px4/bin/px4-mavlink",
                        "stream",
                        "-u",
                        "14621",
                        "-s",
                        stream,
                        "-r",
                        "5",
                    ]
                )
            require(
                process.wait(timeout=150) == 0, "live_capture_failed_see_capture_output"
            )
        finally:
            # Disable only the added stream; the original direct monitor stays live.
            command(
                [
                    "docker",
                    "exec",
                    SITL,
                    "/opt/px4/bin/px4-mavlink",
                    "stop",
                    "-u",
                    "14621",
                ]
            )
            if process.poll() is None:
                command(
                    ["docker", "stop", "--time", "5", project(root) + "-capture"],
                    timeout=15,
                )
                process.wait(timeout=15)
    deadline = time.monotonic() + 90
    while True:
        state = flink_json("/jobs/" + job_id)
        if state["state"] == "FINISHED":
            save(root / "flink-finished.json", state)
            break
        require(state["state"] not in ("FAILED", "CANCELED"), "flink_job_failed")
        require(time.monotonic() < deadline, "flink_completion_deadline")
        time.sleep(1)
    compose(
        root,
        "run",
        "--rm",
        "--no-deps",
        "worker",
        "read",
        "--config",
        "/evidence/plan.json",
    )
    print(
        "Kafka input and Flink output retained for independent reconciliation.",
        flush=True,
    )


def verify(root: Path) -> None:
    verify_export(root)
    inputs, facts = reconcile(root)
    credentials = json_object((root / "credentials.json").read_bytes())
    archived = archive(root, inputs, credentials)
    served = sql_check(root, facts, credentials)
    report: dict[str, object] = {
        "format_version": "live-position-verified-v1",
        "status": "verified",
        "live_unique_measurements": 16,
        "acknowledged_deliveries": 18,
        "flink_facts": len(facts),
        "flink_output_during_capture": True,
        "archive": archived,
        "sql": served,
        "limits": [
            "PX4 SITL, unsigned MAVLink",
            "native boot time, no proven UTC",
            "bounded 16+2 slice, no continuous recovery or capacity claim",
        ],
    }
    report_path = root / "verified-report.json"
    if report_path.exists():
        require(
            json_object(report_path.read_bytes()) == report, "verified_report_changed"
        )
    else:
        save(report_path, report)
    controller = Path(__file__).read_bytes()
    identity = hashlib.sha256(controller).hexdigest()
    evidence = root / ("verification-source-" + identity + ".py")
    if not evidence.exists():
        evidence.write_bytes(controller)
    print(
        "Verified: 16 live positions, 18 exact deliveries; S3 and SQL full readback; "
        "repeated SQL insert remains 16 measurements."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "capture", "verify"))
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    destination = args.evidence.resolve()
    require(
        destination.parent == ROOT / ".local-discovery",
        "local_evidence_directory_required",
    )
    if args.stage == "prepare":
        prepare(destination)
    elif args.stage == "capture":
        start_capture(destination)
    else:
        verify(destination)
