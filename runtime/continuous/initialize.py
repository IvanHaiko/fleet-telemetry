"""Initialize one fresh local continuous scope; never reuse existing progress."""

import argparse
import json
from pathlib import Path
from secrets import token_hex
from typing import Protocol, cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.kafka import Kafka
from runtime.s3.archive_store import make_archive_store
from runtime.s3.boto_transport import make_client
from telemetry.archive_documents import canonical, digest
from telemetry.continuous_archive import object_row, require
from telemetry.continuous_connection import parse_connection


class BucketAdmin(Protocol):
    def create_bucket(self, **kwargs: object) -> object: ...
    def put_bucket_policy(self, **kwargs: object) -> object: ...


def initialize(
    private: Path,
    fixture: Path,
    output: Path,
    resume: bool = False,
    partition_time_jar: str | None = None,
    battery_parallelism: int = 1,
) -> None:
    require(not output.exists(), "continuous_config_exists")
    require(
        type(battery_parallelism) is int and 1 <= battery_parallelism <= 4,
        "continuous_battery_parallelism",
    )
    require(
        battery_parallelism == 1 or partition_time_jar is not None,
        "continuous_battery_parallelism_requires_native_time",
    )
    secrets = object_row(json.loads(private.read_bytes()))
    plan = object_row(json.loads((fixture / "plan.json").read_bytes()))
    run = cast(str, plan["run_id"])
    require(run.replace("-", "").isalnum(), "continuous_scope_identifier")
    connection = secrets.get("kafka_connection")
    parse_connection(connection)
    kafka = Kafka(
        cast(str, secrets["bootstrap"]), cast(str, secrets["cluster_id"]), connection
    )
    topic = f"telemetry.continuous.{run}.input.v1"
    target = f"telemetry.continuous.{run}.output.v1"
    source = kafka.describe(topic) if resume else kafka.create(topic)
    destination = kafka.describe(target) if resume else kafka.create(target)
    live: dict[str, object] = {}
    if partition_time_jar is not None:
        require(partition_time_jar.startswith("file:///"), "continuous_native_jar_uri")
        live_topic = f"telemetry.continuous.{run}.live.v1"
        live = {
            "live_output_topic": live_topic,
            "live_source": kafka.describe(live_topic)
            if resume
            else kafka.create(live_topic),
            "partition_time_jar": partition_time_jar,
            "writer_token": token_hex(32),
            "reader_token": token_hex(32),
        }
    group = run + "-processing-v1"
    consumer = kafka.consumer(group)
    try:
        positions = kafka.positions(topic, dict.fromkeys(map(str, range(18)), 0))
        require(
            all(p.offset <= 0 for p in consumer.committed(positions, timeout=5)),
            "continuous_group_exists",
        )
        for p in positions:
            require(
                consumer.get_watermark_offsets(p, timeout=5, cached=False) == (0, 0),
                "continuous_topic_not_empty",
            )
            kafka.commit(consumer, topic, p.partition, 0)
        for p in kafka.positions(target, dict.fromkeys(map(str, range(18)), 0)):
            require(
                consumer.get_watermark_offsets(p, timeout=5, cached=False) == (0, 0),
                "continuous_output_not_empty",
            )
    finally:
        consumer.close()
    database = "continuous_" + run.replace("-", "_")
    admin = HttpConfig(
        18130, "default", "bootstrap", cast(str, secrets["serving_bootstrap"])
    )
    sql = [f"CREATE DATABASE IF NOT EXISTS {database}"]
    # Every request chooses its database explicitly; no session state is assumed.
    _request(admin, sql[0], b"", write=True)
    table = (
        Path(__file__)
        .with_name("facts.sql")
        .read_text()
        .replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
    )
    _request(admin, table, b"", write=True, parameters={"database": database})
    require(
        _request(
            admin,
            "SELECT count() FROM continuous_facts_v1",
            b"",
            parameters={"database": database},
        ).strip()
        == b"0",
        "continuous_serving_not_empty",
    )
    roles: dict[str, object] = {}
    for role, grant in (("writer", "INSERT"), ("reader", "SELECT")):
        username = role + "_" + run.replace("-", "_")
        password = cast(str, secrets[role])
        require(
            len(password) == 64 and all(c in "0123456789abcdef" for c in password),
            "continuous_password_format",
        )
        _request(
            admin,
            f"CREATE USER IF NOT EXISTS {username} "
            f"IDENTIFIED WITH sha256_password BY '{password}'",
            b"",
            write=True,
        )
        _request(
            admin,
            f"GRANT {grant} ON {database}.continuous_facts_v1 TO {username}",
            b"",
            write=True,
        )
        roles[role] = {
            "port": 18130,
            "database": database,
            "user": username,
            "password": password,
        }
    bucket = "fleet-" + run
    s3 = object_row(secrets["s3"])
    admin_keys = cast(dict[str, str], s3["bootstrap"])
    client = cast(
        BucketAdmin,
        make_client(
            endpoint="http://127.0.0.1:18336", region="us-east-1", **admin_keys
        ),
    )
    if not resume:
        client.create_bucket(Bucket=bucket)
    client.put_bucket_policy(
        Bucket=bucket,
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": [
                            "s3:DeleteObject",
                            "s3:DeleteObjectVersion",
                            "s3:DeleteBucket",
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{bucket}",
                            f"arn:aws:s3:::{bucket}/*",
                        ],
                    }
                ],
            }
        ),
    )
    prefix = f"archive-v1/{run}/"
    writer = make_archive_store(
        "http://127.0.0.1:18336",
        "us-east-1",
        bucket,
        prefix,
        **cast(dict[str, str], s3["writer"]),
    )
    reader = make_archive_store(
        "http://127.0.0.1:18336",
        "us-east-1",
        bucket,
        prefix,
        **cast(dict[str, str], s3["reader"]),
    )
    originals: list[dict[str, object]] = []
    try:
        for path in sorted(fixture.glob("*.json")):
            body = path.read_bytes()
            key = "originals/" + path.name
            writer.create(key, body)
            checksum = digest(body)
            require(
                reader.read(key, checksum, len(body)) == body,
                "continuous_original_readback",
            )
            originals.append({"key": key, "sha256": digest(body), "bytes": len(body)})
    finally:
        writer.close()
        reader.close()
    config = {
        **live,
        "run_id": run,
        "bootstrap": secrets["bootstrap"],
        "input_topic": topic,
        "output_topic": target,
        "source": source,
        "output_source": destination,
        "processing_group": group,
        "archive_group": run + "-archive-v1",
        "serving_group": run + "-serving-v1",
        "source_logs": plan["source_logs"],
        "timestamp_min": plan["timestamp_min"],
        "timestamp_max": plan["timestamp_max"],
        "archive_plan": {
            "format_version": "continuous-archive-plan-v1",
            "source": source,
            "partitions": 18,
            "originals": originals,
        },
        "storage": {
            "endpoint": "http://127.0.0.1:18336",
            "bucket": bucket,
            "prefix": prefix,
            "writer": s3["writer"],
            "reader": s3["reader"],
        },
        **roles,
    }
    if connection is not None:
        config["kafka_connection"] = connection
    output.write_bytes(canonical(config))
    output.chmod(0o600)
    processing = {
        k: config[k]
        for k in (
            "run_id",
            "input_topic",
            "output_topic",
            "processing_group",
            "source",
            "source_logs",
            "timestamp_min",
            "timestamp_max",
        )
    }
    if live:
        processing.update(
            {k: live[k] for k in ("live_output_topic", "partition_time_jar")}
        )
    if connection is not None:
        processing["kafka_connection"] = connection
    if battery_parallelism != 1:
        processing["battery_parallelism"] = battery_parallelism
    output.with_suffix(".processing.json").write_bytes(canonical(processing))
    print(
        json.dumps(
            {
                "event": "continuous_initialized",
                "source": source,
                "output_source": destination,
                "original_files": len(originals),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume-initialization", action="store_true")
    parser.add_argument(
        "--partition-time-jar",
        help="Enable live output using a built file:/// JVM adapter",
    )
    parser.add_argument(
        "--battery-parallelism", type=int, choices=range(1, 5), default=1
    )
    args = parser.parse_args()
    initialize(
        args.private,
        args.fixture,
        args.output,
        args.resume_initialization,
        args.partition_time_jar,
        args.battery_parallelism,
    )
