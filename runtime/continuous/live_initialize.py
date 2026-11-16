"""Initialize one fresh live PX4 SITL scope on the recording profile (ADR-0054).

Runs once inside the worker container after Kafka, SeaweedFS and ClickHouse
are up. Topics, database, users, bucket and evidence must all be new; an
existing scope refuses. Generated run passwords stay in the evidence volume's
role configs. Rollback stops the profile and retains every volume.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig
from runtime.continuous.kafka import Kafka
from runtime.continuous.live_sql import LiveSQL
from runtime.continuous.recording_initialize import (
    CLUSTER_ID,
    CONNECTION,
    S3_ENDPOINT,
    SQL_PORT,
    create_bucket,
    create_sql,
    create_topics,
    private_json,
    require,
)
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.live_runtime import SESSION_PROFILE, Document, session_config
from telemetry.local_io import read_bounded


def initialize(private: Path, evidence: Path) -> Document:
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    plan = json_object(read_bounded(private / "live-run.json", 65536))
    require(plan.get("format_version") == "px4-live-run-v1", "live_run_plan")
    run = string_value(plan["run_id"])
    root = evidence / run
    require(evidence.is_dir() and not root.exists(), "live_evidence_exists")
    session = session_config(
        {
            "profile": SESSION_PROFILE,
            "run_id": run,
            "source": object_value(plan["source"]),
            "max_receipt_age_ms": plan["max_receipt_age_ms"],
        }
    )
    session_sha256 = hashlib.sha256(json_line(session)).hexdigest()
    limit = integer_value(plan["max_deliveries"])

    kafka = Kafka(string_value(CONNECTION["endpoint"]), CLUSTER_ID, CONNECTION)
    sources = create_topics(kafka, run)
    database = string_value(plan["database"])
    roles = create_sql(
        HttpConfig(
            SQL_PORT, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
        ),
        database,
        string_value(secrets["grafana_reader"]),
        LiveSQL,
        ("facts", "progress", "collector"),
    )
    keys = object_value(secrets["s3"])
    bucket = string_value(plan["bucket"])
    create_bucket(bucket, object_value(keys["bootstrap"]))
    storage: Document = {
        "endpoint": S3_ENDPOINT,
        "bucket": bucket,
        "prefix": f"archive-v1/{run}/",
        "writer": keys["writer"],
        "reader": keys["reader"],
    }
    common: Document = {
        "format_version": "px4-live-runtime-v1",
        "run_id": run,
        "bootstrap": CONNECTION["endpoint"],
        "kafka_connection": CONNECTION,
        "sources": sources,
        "session": session,
        "session_sha256": session_sha256,
        "max_deliveries": limit,
        "archive_plan": {
            "format_version": "continuous-archive-plan-v1",
            "partitions": 1,
            "source": sources["input"],
            "run_id": run,
            "session_sha256": session_sha256,
            "max_deliveries": limit,
        },
        "duration_seconds": integer_value(plan["duration_seconds"]) + 600,
        "evidence": str(root / "state"),
    }
    configs: dict[str, Document] = {
        "gateway": {
            **common,
            "duration_seconds": plan["duration_seconds"],
            "udp_port": plan["udp_port"],
        },
        "archive": {**common, "storage": storage},
        "serve": {
            **common,
            "storage": {k: v for k, v in storage.items() if k != "writer"},
            "sql_admin": roles["writer"],
            "sql_reader": roles["reader"],
        },
        # The job carries no S3 or SQL credentials.
        "job": {
            "format_version": "px4-live-job-v1",
            "run_id": run,
            "input_topic": object_value(sources["input"])["topic"],
            "output_topic": object_value(sources["output"])["topic"],
            "processing_group": run + "-processing",
            "source": sources["input"],
            "session": session,
            "session_sha256": session_sha256,
            "max_deliveries": limit,
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
        "session_sha256": session_sha256,
        "max_deliveries": limit,
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
