"""Start and check one guarded continuous PX4 position profile."""

import argparse
import base64
import importlib
import json
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.clickhouse.transport import HttpConfig  # noqa: E402
from runtime.continuous.position_sql import VALUES, PositionSQL  # noqa: E402
from runtime.s3.archive_store import make_archive_store  # noqa: E402
from runtime.s3.boto_transport import make_client  # noqa: E402
from telemetry.continuous_archive import segment_rows  # noqa: E402
from telemetry.conversion_contract import (  # noqa: E402
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.mavlink_position import make_fact  # noqa: E402

PROJECT = "fleetpositionstream20261104"
SITL = "fleetmavlink20261104-sitl-1"
SOURCE_NETWORK = "fleetmavlink20261104_live-internal"


class Base(Protocol):
    def prepare(self, root: Path) -> None: ...
    def command(self, args: list[str], *, timeout: int = 90) -> str: ...
    def flink_json(self, path: str) -> dict[str, object]: ...
    def verify_export(self, root: Path) -> None: ...


base = cast(Base, importlib.import_module("scripts.run-live-position-path"))


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def project(root: Path) -> str:
    return PROJECT + "-" + root.name.rsplit("-", 1)[1]


def compose(root: Path, *args: str, timeout: int = 90) -> str:
    return base.command(
        [
            "docker",
            "compose",
            "--env-file",
            str(root / "runtime.env"),
            "-f",
            "compose/live-position-path.yml",
            "-f",
            "compose/position-continuous.yml",
            "-p",
            project(root),
            "--profile",
            "worker",
            *args,
        ],
        timeout=timeout,
    )


def save(path: Path, value: dict[str, object]) -> None:
    with path.open("xb") as handle:
        handle.write(json_line(value))


def prepare(root: Path) -> None:
    base.prepare(root)
    plan = json_object((root / "plan.json").read_bytes())
    (root / "plan.json").rename(root / "initial-slice-plan.json")
    plan.update(
        format_version="live-position-continuous-v1",
        continuous=True,
        deliveries=3600,
        duration_seconds=3600,
        run_id="position-stream-001",
        input_topic="position-stream-input-001",
        output_topic="position-stream-facts-001",
        group="position-stream-flink-001",
        prefix="archive-v1/position-stream-001/",
    )
    save(root / "plan.json", plan)
    credentials = json_object((root / "credentials.json").read_bytes())
    (root / "credentials.json").rename(root / "initial-credentials.json")
    credentials["ch_writer"] = secrets.token_hex(24)
    save(root / "credentials.json", credentials)
    with (root / "runtime.env").open("a", encoding="utf-8") as handle:
        sdk = Path(string_value(credentials["s3_sdk"]))
        handle.write("POSITION_S3_PACKAGES=" + sdk.as_posix() + "\n")
    compose(root, "config", "--quiet")


def sql_client(root: Path) -> PositionSQL:
    keys = json_object((root / "credentials.json").read_bytes())
    return PositionSQL(
        HttpConfig(
            28133, "default", "position_admin", string_value(keys["ch_admin"]), 15
        ),
        HttpConfig(
            28133, "default", "position_reader", string_value(keys["ch_reader"]), 15
        ),
    )


def stream(root: Path, action: str) -> None:
    if action == "stop":
        base.command(
            ["docker", "exec", SITL, "/opt/px4/bin/px4-mavlink", "stop", "-u", "14622"]
        )
        return
    info = cast(
        list[dict[str, object]],
        json.loads(base.command(["docker", "inspect", project(root) + "-kafka-1"])),
    )
    networks = object_value(object_value(info[0]["NetworkSettings"])["Networks"])
    ip = string_value(object_value(networks[SOURCE_NETWORK])["IPAddress"])
    require(ip.startswith("10.254.247."), "position_source_network")
    base.command(
        [
            "docker",
            "exec",
            SITL,
            "/opt/px4/bin/px4-mavlink",
            "start",
            "-u",
            "14622",
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
    for name, rate in (
        ("HEARTBEAT", "1"),
        ("GPS_RAW_INT", "5"),
        ("GLOBAL_POSITION_INT", "5"),
    ):
        base.command(
            [
                "docker",
                "exec",
                SITL,
                "/opt/px4/bin/px4-mavlink",
                "stream",
                "-u",
                "14622",
                "-s",
                name,
                "-r",
                rate,
            ]
        )


def state(sql: PositionSQL) -> dict[str, object]:
    rows = sql.read("SELECT * FROM position_stream.live_state")
    return rows[0] if rows else {"status": "unknown", **{key: None for key in VALUES}}


def wait_state(sql: PositionSQL, wanted: str, timeout: int = 40) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while True:
        row = state(sql)
        if row["status"] == wanted:
            require(
                wanted == "fresh" or all(row[key] is None for key in VALUES),
                "position_stale_values_visible",
            )
            return row
        require(time.monotonic() < deadline, "position_sql_state_deadline_" + wanted)
        time.sleep(0.2)


def start(root: Path) -> None:
    base.verify_export(root)
    source = cast(
        list[dict[str, object]], json.loads(base.command(["docker", "inspect", SITL]))
    )[0]
    require(
        object_value(source["Config"])["Image"]
        == (
            "px4io/px4-sitl@sha256:"
            "39d5a950208a5a45fccbbb0670bd8716663ed0b350ef738447581395e0c92d97"
        ),
        "position_source_image",
    )
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
            if base.flink_json("/overview")["taskmanagers"] == 1:
                break
        except OSError:
            pass
        require(time.monotonic() < deadline, "position_flink_readiness")
        time.sleep(1)
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
    keys = json_object((root / "credentials.json").read_bytes())
    sys.path.insert(0, string_value(keys["s3_sdk"]))
    item = object_value(keys["admin"])
    s3 = make_client(
        endpoint="http://127.0.0.1:28333",
        region="us-east-1",
        access_key=string_value(item["access"]),
        secret_key=string_value(item["secret"]),
    )
    try:
        plan = json_object((root / "plan.json").read_bytes())
        s3.create_bucket(Bucket=string_value(plan["bucket"]))
    finally:
        s3.close()
    sql = sql_client(root)
    sql.initialize()
    for role in ("reader", "writer"):
        password = string_value(keys["ch_" + role])
        require(re.fullmatch("[0-9a-f]{48}", password), "position_password_shape")
        sql.execute(
            f"CREATE USER position_{role} IDENTIFIED WITH sha256_password "
            f"BY '{password}'"
        )
    sql.execute("GRANT SELECT ON position_stream.* TO position_reader")
    for table in ("facts", "health"):
        sql.execute(
            f"GRANT SELECT, INSERT ON position_stream.{table} TO position_writer"
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
    )
    (root / "flink-submit.txt").write_text(submitted, encoding="utf-8")
    match = re.search(r"JobID\s+([0-9a-f]{32})", submitted)
    require(match is not None, "position_flink_job_id")
    save(root / "flink-job.json", {"job_id": cast(re.Match[str], match).group(1)})
    compose(root, "up", "-d", "collector", "position-store")
    stream(root, "start")
    wait_state(sql, "fresh")
    print("Continuous live source, Flink, S3 and SQL are updating.", flush=True)


def prefix(
    root: Path, sql: PositionSQL, *, limit: int | None = None
) -> dict[str, object]:
    progress = json_object((root / "store-status.json").read_bytes())
    cut = integer_value(progress["input_next"])
    if limit is not None:
        cut = min(cut, limit)
    require(cut >= 5, "position_prefix_too_small")
    deadline = time.monotonic() + 40
    while True:
        facts = sql.read(
            "SELECT DISTINCT input_offset,fact_json FROM position_stream.facts "
            f"WHERE input_offset<{cut} ORDER BY input_offset"
        )
        if len(facts) == cut:
            break
        require(time.monotonic() < deadline, "position_prefix_sql_coverage")
        time.sleep(0.2)
    keys = json_object((root / "credentials.json").read_bytes())
    sys.path.insert(0, string_value(keys["s3_sdk"]))
    plan = json_object((root / "plan.json").read_bytes())
    credential = object_value(keys["reader"])
    reader = make_archive_store(
        "http://127.0.0.1:28333",
        "us-east-1",
        string_value(plan["bucket"]),
        string_value(plan["prefix"]),
        string_value(credential["access"]),
        string_value(credential["secret"]),
    )
    try:
        expected: dict[int, dict[str, object]] = {}
        cursor = 0
        while cursor < cut:
            receipt_body = reader.lookup(f"receipts/p00/{cursor:020d}.json")
            require(receipt_body is not None, "position_prefix_receipt_missing")
            receipt = json_object(cast(bytes, receipt_body))
            body = reader.read(
                string_value(receipt["segment_key"]),
                string_value(receipt["segment_sha256"]),
                integer_value(receipt["segment_bytes"]),
            )
            source = object_value(
                json_object((root / "sources.json").read_bytes())["input"]
            )
            for row in segment_rows(body):
                require(
                    all(row[key] == value for key, value in source.items()),
                    "position_prefix_source_identity",
                )
                offset = integer_value(row["offset"])
                if offset >= cut:
                    break
                require(offset == len(expected), "position_prefix_offset_gap")
                ack = json_object((root / "acks" / f"{offset:020d}.json").read_bytes())
                raw_body = (
                    root / "packets" / f"{integer_value(ack['packet_index']):020d}.json"
                ).read_bytes()
                require(
                    reader.lookup(f"packets/{offset:020d}.json") == raw_body,
                    "position_prefix_raw_bytes",
                )
                value = base64.b64decode(string_value(row["value_b64"]), validate=True)
                require(
                    value == json_line(json_object(raw_body)["event"]),
                    "position_prefix_event_bytes",
                )
                fact = make_fact(
                    value,
                    base64.b64decode(string_value(row["key_b64"]), validate=True),
                    string_value(plan["input_topic"]),
                    0,
                    offset,
                    offset_limit=3600,
                )
                expected[offset] = fact
            cursor = integer_value(receipt["next"])
        actual = {
            integer_value(row["input_offset"]): json_object(
                string_value(row["fact_json"]).encode()
            )
            for row in facts
        }
        require(actual == expected, "position_prefix_full_content")
        unique = {
            string_value(object_value(fact["event"])["event_id"])
            for fact in expected.values()
        }
        return {
            "exact_deliveries": cut,
            "unique_measurements": len(unique),
            "full_source_archive_flink_sql_match": True,
            "source_identity_checked": True,
        }
    finally:
        reader.close()


def check(root: Path) -> None:
    sql = sql_client(root)
    before = wait_state(sql, "fresh")
    print("Checking source silence/resume.", flush=True)
    stopped = time.monotonic()
    stream(root, "stop")
    try:
        stale = wait_state(sql, "stale", 15)
        deadline = time.monotonic() + 15
        while stale.get("connection") != "lost":
            require(time.monotonic() < deadline, "position_heartbeat_loss_deadline")
            time.sleep(0.2)
            stale = state(sql)
        require(
            stale["status"] == "stale" and all(stale[key] is None for key in VALUES),
            "position_loss_values_visible",
        )
        lost_seconds = time.monotonic() - stopped
    finally:
        stream(root, "start")
    resumed = wait_state(sql, "fresh", 30)
    require(
        integer_value(resumed["source_boot_ms"])
        > integer_value(before["source_boot_ms"]),
        "position_resumed_without_new_measurement",
    )
    (root / "repeat-first").touch(exist_ok=False)
    print("Checking SQL-acknowledged write before cursor recovery.", flush=True)
    (root / "pause-after-insert").touch(exist_ok=False)
    deadline = time.monotonic() + 30
    while not (root / "inserted-marker.json").exists():
        require(time.monotonic() < deadline, "position_insert_window_not_reached")
        time.sleep(0.1)
    pending = json_object((root / "inserted-marker.json").read_bytes())
    prior = json_object((root / "serving-cursor.json").read_bytes())
    require(
        integer_value(pending["next"]) > integer_value(prior["next"]),
        "position_not_in_failure_window",
    )
    unknown = wait_state(sql, "unknown", 10)
    base.command(
        ["docker", "kill", "--signal", "KILL", project(root) + "-position-store-1"]
    )
    (root / "pause-after-insert").unlink()
    compose(root, "up", "-d", "position-store")
    after = wait_state(sql, "fresh", 40)
    require(
        integer_value(after["source_boot_ms"])
        > integer_value(resumed["source_boot_ms"]),
        "position_recovery_not_current",
    )
    counts = sql.read(
        "SELECT count() AS physical_rows,uniqExact(input_offset) AS deliveries,"
        "uniqExact(event_id) AS measurements FROM position_stream.facts"
    )[0]
    require(
        integer_value(counts["physical_rows"]) > integer_value(counts["deliveries"]),
        "position_retry_not_observed",
    )
    require(
        integer_value(counts["deliveries"]) - integer_value(counts["measurements"])
        == 1,
        "position_duplicate_measurement_count",
    )
    verified = prefix(root, sql)
    job = json_object((root / "flink-job.json").read_bytes())
    checkpoints = base.flink_json(
        "/jobs/" + string_value(job["job_id"]) + "/checkpoints"
    )
    save(
        root / "continuous-check.json",
        {
            "status": "verified_live_prefix",
            "source_loss_seconds": lost_seconds,
            "before": before,
            "stale": stale,
            "resumed": resumed,
            "worker_unknown": unknown,
            "recovered": after,
            "cursor_before_kill": prior,
            "inserted_before_kill": pending,
            "counts_after_recovery": counts,
            "prefix": verified,
            "checkpoints": checkpoints.get("counts"),
            "continues_after_check": True,
            "guard_seconds": 3600,
            "guard_deliveries": 3600,
        },
    )
    print(
        "Verified source loss/resume, worker write-window recovery, "
        "duplicate-safe SQL and exact archived prefix; recording continues."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "start", "check"))
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence.resolve()
    require(
        root.parent == ROOT / ".local-discovery", "position_local_evidence_required"
    )
    {"prepare": prepare, "start": start, "check": check}[args.stage](root)
