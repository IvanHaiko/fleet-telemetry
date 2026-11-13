"""Initialize one fresh single-machine F09 recording scope and its role configs.

Runs once inside the worker container, which shares the storage network
namespace, after Kafka, SeaweedFS and ClickHouse are up. Every scope is fresh:
existing topics, databases, run users, buckets or evidence refuse rather than
being reused. Generated run passwords stay in the evidence volume configs.
Rollback stops the profile and retains every volume; nothing is deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from secrets import token_hex
from typing import Protocol, cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.kafka import Consumer, Kafka, Position
from runtime.continuous.recording_config import MAX_BODY, MAX_LIFETIME_SECONDS
from runtime.continuous.recording_sql import _READ_SETTINGS, RecordingSQL
from runtime.flight_analytics.stream_prepare import load_bundle
from runtime.s3.boto_transport import make_client
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded

type Document = dict[str, object]

CLUSTER_ID = "ZmxlZXQtcmVjb3JkaW5nMQ"
CONNECTION: Document = {
    "format_version": "single-host-kafka-v1",
    "endpoint": "kafka:9092",
    "partitions": 12,
}
S3_ENDPOINT = "http://127.0.0.1:8333"
SQL_PORT = 8123
GRAFANA_USER = "recording_grafana"
# Grafana's own bounded SQL settings; readonly=1 refuses differing per-query values.
GRAFANA_SETTINGS = {
    **_READ_SETTINGS,
    "max_rows_to_read": "50000",
    "max_bytes_to_read": "64000000",
    "max_result_bytes": "4194304",
}


class BucketAdmin(Protocol):
    def create_bucket(self, **kwargs: object) -> object: ...
    def put_bucket_policy(self, **kwargs: object) -> object: ...


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def settings_clause(values: dict[str, str], *, grafana: bool = False) -> str:
    items = []
    for key, value in values.items():
        require(key.replace("_", "").isalnum(), "recording_sql_setting")
        item = key + "=" + (value if value.isdigit() else "'" + value + "'")
        if grafana and key == "max_execution_time":
            # The datasource sends its own timeout; allow only a bounded value.
            item += " MIN 1 MAX 60 CHANGEABLE_IN_READONLY"
        items.append(item)
    return ",".join(items)


def private_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def watermarks(consumer: Consumer, position: Position) -> tuple[int, int]:
    """Partition leadership can lag a new topic's metadata; retry reads only."""
    for attempt in range(20):
        try:
            return consumer.get_watermark_offsets(position, timeout=5, cached=False)
        except Exception:
            if attempt == 19:
                raise
            time.sleep(0.5)
    raise AssertionError("unreachable")


def create_topics(kafka: Kafka, run: str) -> Document:
    """Create fresh topics; an existing name refuses inside create_topics."""
    sources: Document = {}
    for which in ("input", "output"):
        topic = f"telemetry.{run}.{which}.v1"
        sources[which] = kafka.create(topic)
        consumer = kafka.consumer(run + "-empty-admission")
        try:
            for position in kafka.positions(
                topic, dict.fromkeys(map(str, range(kafka.partitions)), 0)
            ):
                require(
                    watermarks(consumer, position) == (0, 0),
                    "recording_topic_not_empty",
                )
        finally:
            consumer.close()
    return sources


def create_sql(bootstrap: HttpConfig, database: str, grafana_password: str) -> Document:
    """Fresh database, INSERT-only writer, readonly reader and Grafana grants."""
    require(
        _request(bootstrap, f"EXISTS DATABASE {database}", b"").strip() == b"0",
        "recording_database_exists",
    )
    roles: Document = {}
    for role in ("writer", "reader"):
        user = f"{database}_{role}"
        require(
            not _request(
                bootstrap,
                f"SELECT name FROM system.users WHERE name='{user}' FORMAT JSONEachRow",
                b"",
            ).strip(),
            "recording_sql_user_exists",
        )
        password = token_hex(32)
        _request(
            bootstrap,
            f"CREATE USER {user} IDENTIFIED WITH sha256_password BY '{password}'",
            b"",
            write=True,
        )
        roles[role] = {
            "port": SQL_PORT,
            "database": database,
            "user": user,
            "password": password,
        }
    writer, reader = (object_value(roles[role]) for role in ("writer", "reader"))
    reader_config = HttpConfig(
        SQL_PORT,
        database,
        string_value(reader["user"]),
        string_value(reader["password"]),
    )
    RecordingSQL(bootstrap, reader_config).initialize()
    for table in ("facts", "progress"):
        _request(
            bootstrap,
            f"GRANT INSERT ON {database}.{table} TO {writer['user']}",
            b"",
            write=True,
        )
    _request(
        bootstrap, f"GRANT SELECT ON {database}.* TO {reader['user']}", b"", write=True
    )
    _request(
        bootstrap,
        f"ALTER USER {reader['user']} SETTINGS {settings_clause(_READ_SETTINGS)}",
        b"",
        write=True,
    )
    # One Grafana identity across runs; each run grants it only its database.
    _request(
        bootstrap,
        f"CREATE USER IF NOT EXISTS {GRAFANA_USER} "
        f"IDENTIFIED WITH sha256_password BY '{grafana_password}'",
        b"",
        write=True,
    )
    _request(
        bootstrap,
        f"ALTER USER {GRAFANA_USER} SETTINGS "
        + settings_clause(GRAFANA_SETTINGS, grafana=True),
        b"",
        write=True,
    )
    _request(
        bootstrap, f"GRANT SELECT ON {database}.* TO {GRAFANA_USER}", b"", write=True
    )
    return roles


def create_bucket(bucket: str, keys: Document) -> None:
    client = cast(
        BucketAdmin,
        make_client(
            endpoint=S3_ENDPOINT,
            region="us-east-1",
            access_key=string_value(keys["access_key"]),
            secret_key=string_value(keys["secret_key"]),
        ),
    )
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


def initialize(private: Path, evidence: Path) -> Document:
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    run_plan = json_object(read_bounded(private / "run.json", 65536))
    require(
        run_plan.get("format_version") == "f09-recording-run-v1", "recording_run_plan"
    )
    run = string_value(run_plan["run_id"])
    root = evidence / run
    require(evidence.is_dir() and not root.exists(), "recording_evidence_exists")

    bundle = Path(string_value(run_plan["bundle"]))
    events, context, manifest = load_bundle(bundle)
    require(context["run_id"] == run, "recording_run_binding")
    reference = read_bounded(Path(string_value(run_plan["reference"])), MAX_BODY)
    reference_sha256 = hashlib.sha256(reference).hexdigest()
    require(
        reference_sha256 == run_plan["reference_sha256"]
        and len(reference) == run_plan["reference_bytes"],
        "recording_reference_binding",
    )
    expected_facts = sum(e["stream"] == "vehicle_gps_position:0" for e in events)
    require(len(reference.splitlines()) == expected_facts, "recording_reference_count")
    context_sha256 = hashlib.sha256(json_line(context)).hexdigest()
    bundle_sha256 = hashlib.sha256(json_line(manifest)).hexdigest()
    # Two deliberate repeats exercise duplicate-safe processing and SQL.
    duplicate_indices = [0, len(events) // 2]
    deliveries = len(events) + len(duplicate_indices)

    kafka = Kafka(string_value(CONNECTION["endpoint"]), CLUSTER_ID, CONNECTION)
    sources = create_topics(kafka, run)
    database = string_value(run_plan["database"])
    roles = create_sql(
        HttpConfig(
            SQL_PORT, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
        ),
        database,
        string_value(secrets["grafana_reader"]),
    )
    keys = object_value(secrets["s3"])
    bucket = string_value(run_plan["bucket"])
    create_bucket(bucket, object_value(keys["bootstrap"]))

    storage: Document = {
        "endpoint": S3_ENDPOINT,
        "bucket": bucket,
        "prefix": f"archive-v1/{run}/",
        "writer": keys["writer"],
        "reader": keys["reader"],
    }
    common: Document = {
        "format_version": "f09-recording-runtime-v1",
        "run_id": run,
        "bootstrap": CONNECTION["endpoint"],
        "kafka_connection": CONNECTION,
        "sources": sources,
        "bundle": str(bundle),
        "reference": run_plan["reference"],
        "source_manifest": run_plan["source_manifest"],
        "deliveries": deliveries,
        "duplicate_indices": duplicate_indices,
        "context_sha256": context_sha256,
        "bundle_sha256": bundle_sha256,
        "reference_sha256": reference_sha256,
        "reference_bytes": len(reference),
        "archive_plan": {
            "format_version": "continuous-archive-plan-v1",
            "partitions": 1,
            "source": sources["input"],
            "run_id": run,
            "context_sha256": context_sha256,
            "bundle_sha256": bundle_sha256,
            "expected_deliveries": deliveries,
        },
        "duration_seconds": MAX_LIFETIME_SECONDS,
        "evidence": str(root / "state"),
    }
    configs: dict[str, Document] = {
        "publish": dict(common),
        "archive": {**common, "storage": storage},
        "serve": {
            **common,
            "storage": {k: v for k, v in storage.items() if k != "writer"},
            "sql_admin": roles["writer"],
            "sql_reader": roles["reader"],
        },
        # The job carries no S3 or SQL credentials.
        "job": {
            "format_version": "f09-recording-job-v1",
            "run_id": run,
            "input_topic": object_value(sources["input"])["topic"],
            "output_topic": object_value(sources["output"])["topic"],
            "processing_group": run + "-processing",
            "source": sources["input"],
            "context": context,
            "context_sha256": context_sha256,
            "deliveries": deliveries,
            "max_age_us": 1_000_000,
            "kafka_connection": CONNECTION,
            "bootstrap": CONNECTION["endpoint"],
            "checkpoint_directory": f"file:///state/{run}-checkpoints",
            "job_file": f"/state/{run}-job.json",
        },
    }
    previous = os.umask(0o077)
    try:
        root.mkdir(mode=0o700)
        (root / "config").mkdir(mode=0o700)
        (root / "state").mkdir(mode=0o700)
        for role, document in configs.items():
            private_json(root / "config" / f"{role}.json", document)
    finally:
        os.umask(previous)
    summary: Document = {
        "run_id": run,
        "sources": sources,
        "database": database,
        "bucket": bucket,
        "deliveries": deliveries,
        "expected_facts": expected_facts,
        "partitions": integer_value(CONNECTION["partitions"]),
    }
    private_json(root / "initialized.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = initialize(args.private, args.evidence)
    except Exception as error:
        # Trust boundary: client exceptions may embed credentials or paths.
        print(json.dumps({"status": "failed", "category": type(error).__name__}))
        return 2
    print(json.dumps({"status": "initialized", **summary}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
