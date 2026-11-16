"""Rebuild one recording run's facts from its archive into a separate SQL scope.

The inputs are only archive objects: the stream plan, the archived context and
the chained input segments, each read back by digest. Kafka, Flink, the serving
cursor and the original database are not read. The same association runtime
that the Flink operator wraps processes the archived deliveries in offset
order, and the facts go to a new database `<run database>_rebuild_<id>` with
its own writer and reader accounts. Evidence goes to a new directory beside
the run's state. Nothing of the original run is reset, replaced or deleted;
an existing rebuild scope refuses. Runs in the worker container with the
bootstrap SQL account, which only creates the new scope.
"""

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig
from runtime.continuous.recording_batch import MAX_BATCH
from runtime.continuous.recording_config import (
    MAX_DELIVERIES,
    Document,
    immutable,
    require,
    storage,
)
from runtime.continuous.recording_initialize import create_sql
from runtime.continuous.recording_sql import RecordingSQL
from telemetry.archive_documents import canonical, digest
from telemetry.continuous_archive import SegmentedArchive, segment_rows
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded
from telemetry.recording_runtime import RecordingRuntime, make_output
from telemetry.recording_stream import event_bytes, read_event

_REBUILD = re.compile(r"[0-9]{3}", re.ASCII)


def archived_deliveries(config: Document, root: Path) -> tuple[Document, list[bytes]]:
    """Return the archived context and every archived input value, in order."""
    reader = storage(config, "reader")
    try:
        context_sha256 = string_value(config["context_sha256"])
        raw = reader.lookup("context.json")
        require(
            raw is not None and hashlib.sha256(raw).hexdigest() == context_sha256,
            "recording_rebuild_context",
        )
        context = json_object(cast(bytes, raw))
        plan = object_value(config["archive_plan"])
        origin = root / "archive-reader-origin.json"
        immutable(
            origin,
            canonical(
                {
                    "format_version": "continuous-archive-cursor-v1",
                    "plan_sha256": digest(canonical(plan)),
                    "partitions": {
                        "0": {"next": 0, "start": 0, "receipt_sha256": None}
                    },
                }
            ),
        )
        # Reads stream-plan.json back and checks it against the plan binding.
        verifier = SegmentedArchive(reader, reader, origin, plan)
        expected = integer_value(plan["expected_deliveries"])
        values: list[bytes] = []
        previous: str | None = None
        while len(values) < expected:
            checked = verifier.verify_receipt(0, len(values))
            require(checked is not None, "recording_rebuild_archive_incomplete")
            assert checked is not None
            receipt, body = checked
            require(receipt["previous_sha256"] == previous, "recording_rebuild_chain")
            for row in segment_rows(body):
                value = base64.b64decode(string_value(row["value_b64"]), validate=True)
                key = base64.b64decode(string_value(row["key_b64"]), validate=True)
                event = read_event(value)
                require(
                    value == event_bytes(event)
                    and key == string_value(event["measurement_id"]).encode()
                    and row["headers"] == [],
                    "recording_rebuild_input",
                )
                values.append(value)
            previous = digest(canonical(receipt))
        require(
            len(values) == expected and verifier.verify_receipt(0, expected) is None,
            "recording_rebuild_archive_extra",
        )
        return context, values
    finally:
        reader.close()


def process(
    config: Document, context: Document, values: list[bytes], max_age_us: int
) -> list[Document]:
    """Associate archived deliveries exactly as the operator does, one lane."""
    runtime = RecordingRuntime(context, max_age_us=max_age_us)
    source = {
        **object_value(object_value(config["sources"])["input"]),
        "partition": 0,
    }
    context_sha256 = string_value(config["context_sha256"])
    outputs: list[Document] = []
    for offset, value in enumerate(values):
        fact = runtime.accept(read_event(value))
        if fact is not None:
            outputs.append(make_output(fact, source, offset, context_sha256))
    runtime.finish()
    return outputs


def rebuild(private: Path, evidence: Path, rebuild_id: str) -> Document:
    require(_REBUILD.fullmatch(rebuild_id) is not None, "recording_rebuild_id")
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    run = json_object(read_bounded(private / "run.json", 65536))
    run_id = string_value(run["run_id"])
    config = json_object(
        read_bounded(evidence / run_id / "config" / "serve.json", 262144)
    )
    # The job configuration carries the association age policy, not data.
    job = json_object(read_bounded(evidence / run_id / "config" / "job.json", 262144))
    require(
        config["run_id"] == run_id == job["run_id"]
        and job["context_sha256"] == config["context_sha256"],
        "recording_rebuild_binding",
    )
    database = string_value(run["database"]) + "_rebuild_" + rebuild_id
    root = evidence / run_id / f"rebuild-{rebuild_id}"
    root.mkdir(mode=0o700)  # an existing rebuild refuses
    context, values = archived_deliveries(config, root)
    require(1 <= len(values) <= MAX_DELIVERIES, "recording_rebuild_bound")
    outputs = process(config, context, values, integer_value(job["max_age_us"]))
    roles = create_sql(
        HttpConfig(
            8123, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
        ),
        database,
        string_value(secrets["grafana_reader"]),
    )

    def account(role: str) -> HttpConfig:
        row = object_value(roles[role])
        return HttpConfig(
            integer_value(row["port"]),
            database,
            string_value(row["user"]),
            string_value(row["password"]),
            15,
        )

    sql = RecordingSQL(account("writer"), account("reader"))
    for start in range(0, len(outputs), MAX_BATCH):
        sql.write_facts(outputs[start : start + MAX_BATCH])
    identities = {
        string_value(object_value(output["fact"])["measurement_id"])
        for output in outputs
    }
    require(sql.logical_ids() == identities, "recording_rebuild_readback")
    sql.progress("completed", len(values), len(identities), len(identities))
    summary: Document = {
        "status": "completed",
        "rebuild_id": rebuild_id,
        "database": database,
        "archived_deliveries": len(values),
        "outputs": len(outputs),
        "logical_facts": len(identities),
        "outputs_sha256": hashlib.sha256(
            b"".join(json_line(output) for output in outputs)
        ).hexdigest(),
    }
    immutable(root / "rebuild-complete.json", json_line(summary))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--rebuild", required=True, help="three digits, such as 001")
    args = parser.parse_args(argv)
    try:
        summary = rebuild(args.private, args.evidence, args.rebuild)
    except Exception as error:
        # Trust boundary: client exceptions may embed credentials or paths.
        print(json.dumps({"status": "failed", "category": type(error).__name__}))
        return 2
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
