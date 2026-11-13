"""Finite source-to-query demonstration against an already started fresh profile.

Run on the admitted Linux Python/SDK profile. No service lifecycle or DDL ownership
is hidden here: the caller starts/stops a dedicated Compose project and creates
the tables/users. All commands are bounded; existing evidence is never replaced.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import cast

from m3_transport import Transport
from m3_transport_types import Record

from runtime.archive_runtime.config import load_config
from runtime.archive_runtime.supervisor import Supervisor
from runtime.clickhouse.transport import HttpConfig, HttpReader, HttpWriter
from runtime.kafka_archive.commit import NativeCommitter
from runtime.s3.archive_store import make_archive_store
from scripts.slice_measurement import SliceMeasurement
from scripts.slice_queries import insert, reconcile
from scripts.slice_run import exact6
from telemetry.archive_documents import digest, reference
from telemetry.archive_graph import verify_catalog
from telemetry.serving_projection import ServingScope, project_archive
from telemetry.serving_sink import SinkError, publish_archive
from telemetry_convert import convert_job, verify_job
from telemetry_reference import (
    EndOfInput,
    Observation,
    ReferenceScope,
    calculate_windows,
)

ROOT = Path(__file__).resolve().parents[1]
DOCKER = shutil.which("docker.exe") or shutil.which("docker") or "docker"
METRICS = ("voltage_v", "current_a", "remaining_fraction")
type Row = dict[str, object]


def require(condition: object, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def obj(value: object) -> Row:
    require(isinstance(value, dict), "object_required")
    return cast(Row, value)


def rows(body: bytes) -> list[Row]:
    return [obj(json.loads(line)) for line in body.splitlines()]


def save(evidence: Path, name: str, value: object) -> None:
    with (evidence / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def command(
    evidence: Path,
    name: str,
    argv: list[str],
    timeout: int = 120,
    input_text: str | None = None,
) -> str:
    if argv[0] == "docker":
        argv[0] = DOCKER
    result = subprocess.run(
        argv, input=input_text, capture_output=True, text=True, timeout=timeout
    )
    save(
        evidence,
        name,
        {
            "argv": argv,
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )
    require(result.returncode == 0, "command_failed")
    return result.stdout


def run(evidence: Path, private: Path, project: str, observations: int = 4) -> None:
    require(sys.platform == "linux", "linux_profile_required")
    require(type(observations) is int and 4 <= observations <= 32, "observation_bound")
    require(re.fullmatch(r"fleet-m4-slice-[0-9]{3}", project), "project_scope")
    evidence.mkdir(exist_ok=False)
    config = obj(json.loads(private.read_bytes()))
    storage = load_config(Path(cast(str, config["archive_config"])), publish=True)
    writer = HttpConfig(**cast(dict[str, str | int], config["writer"]))  # type: ignore[arg-type]
    reader = HttpConfig(**cast(dict[str, str | int], config["reader"]))  # type: ignore[arg-type]
    run_id = project + "-" + evidence.name.rsplit("-", 1)[-1]
    scope = ServingScope(run_id, "source-query-v1")
    fixture = ROOT / "tests/fixtures/synthetic-conversion-job.json"
    job_body = fixture.read_bytes()
    source_body = (fixture.parent / "synthetic-battery-v1.json").read_bytes()
    measurement = SliceMeasurement(evidence, observations)
    conversion = convert_job(fixture, evidence / "demo-synthetic-001")
    verify_job(fixture, conversion.output_directory)
    values = (conversion.output_directory / "events.jsonl").read_bytes().splitlines()
    require(len(values) == 3, "fixture_changed")
    values = [values[index % 3] for index in range(observations)]
    measurement.mark("source_converted")
    events = [obj(json.loads(value)) for value in values]
    original = obj(json.loads(job_body))
    manifest = obj(original["manifest"])
    reference_scope = ReferenceScope(
        "demo-synthetic-001",
        scope.pipeline_version,
        cast(str, manifest["source_log_id"]),
        "2026-01-01T12:00:00.000000Z",
        "2026-01-01T12:00:02.000000Z",
    )
    reference_result = calculate_windows(
        reference_scope, [*[Observation(value) for value in values], EndOfInput()]
    )
    save(
        evidence,
        "reference.json",
        json.loads(json.dumps(asdict(reference_result), default=str)),
    )
    topic = f"m2.m3-final-{run_id}.telemetry.canonical.v1"
    transport = Transport(
        lambda kind, value: save(
            evidence, f"kafka-{kind}-{len(list(evidence.iterdir()))}.json", value
        )
    )
    source = {**transport.create(topic, 1), "partition": 0}
    for index, value in enumerate(values):
        transport.send(
            topic,
            Record(0, index, index, value, str(events[index]["vehicle_id"]).encode()),
        )
    measurement.mark("producer_acked")
    # Full UUID comparison with broker-owned metadata, independent of SDK spelling.
    cli = command(
        evidence,
        "broker-topic.json",
        [
            "docker",
            "exec",
            project + "-kafka-1",
            "/opt/kafka/bin/kafka-topics.sh",
            "--bootstrap-server",
            "kafka:9092",
            "--describe",
            "--topic",
            topic,
        ],
    )
    import base64

    match = re.search(r"TopicId:\s*(\S+)", cli)
    require(match is not None, "broker_uuid_missing")
    assert match is not None
    require(
        base64.urlsafe_b64decode(match[1] + "==")
        == base64.b64decode(cast(str, source["topic_id"]) + "=="),
        "topic_uuid_mismatch",
    )
    save(evidence, "source.json", source)
    # Initialize only this newly created topic/group at its proven empty origin.
    committer = NativeCommitter("127.0.0.1:19092", "m4-reader-" + run_id, source)
    try:
        committer.commit(0, 10)
    finally:
        committer.close()
    # Existing supervised archive path remains independent of Flink and serving.
    blobs = {}
    lineage = []
    for role, body in (("original_source", source_body), ("source_manifest", job_body)):
        ref = reference(body, "source")
        blobs[cast(str, ref["key"])] = body
        lineage.append(
            {
                "role": role,
                "object": ref,
                "source_log_id": manifest["source_log_id"],
                "schema_version": "1.0.0",
                "normalization_version": "battery-v1",
                "source_dataset_run_id": "demo-synthetic-001",
                "privacy_classification": "synthetic",
                "semantic_projection": "battery-semantic-v1",
            }
        )
    archive_job = {
        "archive_run_id": run_id,
        "bucket": storage.bucket,
        "source": source,
        "start_offset": 0,
        "next_offset": observations,
        "lineage": lineage,
        "writer_version": digest(Path(__file__).read_bytes()),
        "verified_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "batch_size": min(16, max(2, observations // 2)),
    }
    scratch = evidence / "scratch"
    scratch.mkdir()
    roots = evidence / "roots"
    roots.mkdir()
    archive_result = Supervisor(storage, scratch, 120).publish(
        archive_job, blobs, "m4-reader-" + run_id, roots, None
    )
    save(evidence, "archive.json", archive_result)
    descriptor = (roots / run_id / "descriptor.json").read_bytes()
    sha = digest(descriptor)
    store = make_archive_store(
        storage.endpoint,
        storage.region,
        storage.bucket,
        f"archive-v1/{run_id}/",
        storage.reader.access_key,
        storage.reader.secret_key,
    )
    try:
        archive = verify_catalog(descriptor, sha, store)
        require(
            [obj(row)["value_b64"] for row in archive.coverage.observations]
            == [base64.b64encode(value).decode() for value in values],
            "archive_bytes_mismatch",
        )
        require(
            {row["event_id"] for row in archive.measurements}
            == {row["event_id"] for row in events},
            "archive_identities_mismatch",
        )
        measurement.mark("archive_graph_verified")
        flink_manifest = {
            "profile": "m3-persistent-input-v1",
            "topic": topic,
            "bootstrap": "kafka:9092",
            "group": run_id + "-flink",
            "end": observations,
            "scope": asdict(reference_scope),
        }
        save(evidence, "flink-manifest.json", flink_manifest)
        command(
            evidence,
            "copy-manifest.json",
            [
                "docker",
                "exec",
                "-i",
                project + "-jobmanager-1",
                "sh",
                "-c",
                "cat > /state/input.json",
            ],
            input_text=json.dumps(flink_manifest),
        )
        command(
            evidence,
            "flink-command.json",
            [
                "docker",
                "exec",
                project + "-jobmanager-1",
                "/opt/m3/entrypoint.sh",
                "submit",
                "-py",
                "/workspace/runtime/pyflink/persistent_job.py",
                "--manifest",
                "/state/input.json",
                "--control",
                "/state/slice-" + run_id,
                "--checkpoints",
                "/state/checkpoints-" + run_id,
                "--run-tag",
                "initial",
                "--identity-limit",
                "128",
            ],
            180,
        )
        measurement.mark("flink_finished")
        output = command(
            evidence,
            "flink-trace-command.json",
            [
                "docker",
                "exec",
                project + "-jobmanager-1",
                "cat",
                "/state/slice-" + run_id + "/trace-initial.jsonl",
            ],
        )
        trace = rows(output.encode())
        save(evidence, "flink-trace.json", trace)
        for index, value in enumerate(values):
            audit = obj(
                json.loads(
                    command(
                        evidence,
                        f"flink-source-{index}.json",
                        [
                            "docker",
                            "exec",
                            project + "-jobmanager-1",
                            "cat",
                            f"/state/slice-{run_id}/source-initial-0-{index}.json",
                        ],
                    )
                )
            )
            require(
                audit["topic"] == topic
                and audit["partition"] == 0
                and audit["offset"] == index
                and audit["value_sha256"] == digest(value)[7:]
                and audit["key_sha256"]
                == digest(str(events[index]["vehicle_id"]).encode())[7:],
                "flink_source_bytes_mismatch",
            )
        dispositions = [row for row in trace if row["kind"] == "disposition"]
        require(
            [
                (row["observation_index"], row["disposition"], row["event_id"])
                for row in dispositions
            ]
            == [
                (d.observation_index, d.kind, d.event_id)
                for d in reference_result.dispositions
            ],
            "flink_dispositions_mismatch",
        )
        raw_windows = [row for row in trace if row["kind"] == "window"]
        require(len(raw_windows) == len(reference_result.windows) == 1, "window_count")
        expected_window = reference_result.windows[0]
        actual_window = raw_windows[0]
        for field in (
            "dataset_run_id",
            "pipeline_version",
            "vehicle_id",
            "start_ms",
            "end_ms",
            "unique_events",
        ):
            require(
                actual_window[field] == getattr(expected_window, field),
                "window_mismatch",
            )
        windows: list[Row] = []
        for metric, summary in zip(
            METRICS,
            (
                expected_window.voltage,
                expected_window.current,
                expected_window.remaining,
            ),
            strict=True,
        ):
            measure = cast(list[object], obj(actual_window["measures"])[metric])
            require(
                measure[0] == summary.count
                and Fraction(cast(str, measure[1])) == (summary.total or Fraction(0)),
                "window_sum_mismatch",
            )
            # The tiny fixture is exactly representable; refuse rounding elsewhere.
            total = Fraction(cast(str, measure[1]))
            value_sum = exact6(total)
            windows.append(
                {
                    "dataset_run_id": scope.dataset_run_id,
                    "pipeline_version": scope.pipeline_version,
                    "vehicle_id": actual_window["vehicle_id"],
                    "start_ms": actual_window["start_ms"],
                    "end_ms": actual_window["end_ms"],
                    "metric": metric,
                    "unique_events": actual_window["unique_events"],
                    "valid_count": measure[0],
                    "value_sum": value_sum,
                    "archive_descriptor_sha256": sha,
                }
            )
        facts = [
            {
                "dataset_run_id": scope.dataset_run_id,
                "pipeline_version": scope.pipeline_version,
                **{
                    key: row[key]
                    for key in (
                        "observation_index",
                        "event_id",
                        "disposition",
                        "reason",
                        "watermark_ms",
                    )
                },
                "archive_descriptor_sha256": sha,
            }
            for row in dispositions
        ]
        measurement.mark("flink_facts_reconciled")
        projection = project_archive(descriptor, sha, store, scope)

        # A real upstream write succeeds, then the caller loses its acknowledgement.
        class LostAck:
            def write(self, body: bytes) -> None:
                HttpWriter(writer).write(body)
                raise ConnectionResetError("injected_after_upstream_success")

        try:
            publish_archive(
                descriptor,
                sha,
                store,
                scope,
                LostAck(),
                HttpReader(reader),
                batch_size=2,
            )
        except SinkError as error:
            require(error.category == "write_ambiguous", "unexpected_failure")
            save(
                evidence,
                "lost-ack.json",
                {
                    "error": error.category,
                    "injection": "caller loses response after real upstream success",
                },
            )
        else:
            raise ValueError("lost_ack_not_observed")
        receipt = publish_archive(
            descriptor,
            sha,
            store,
            scope,
            HttpWriter(writer),
            HttpReader(reader),
            batch_size=1,
        )
        insert(writer, "slice_dispositions_v1", facts, 2)
        insert(writer, "slice_windows_v1", windows, 2)
        before = reconcile(reader, scope, facts, windows)
        measurement.mark("first_verified_sql_visibility")
        publish_archive(
            descriptor,
            sha,
            store,
            scope,
            HttpWriter(writer),
            HttpReader(reader),
            batch_size=3,
        )
        insert(writer, "slice_dispositions_v1", facts, 1)
        insert(writer, "slice_windows_v1", windows, 1)
        after = reconcile(reader, scope, facts, windows)
        require(before == after, "retry_changed_query_results")
        require(
            {row.event_id for row in projection.rows}
            == {row["event_id"] for row in events},
            "serving_identity_mismatch",
        )
        measurement.finish(len(projection.rows), sum(map(len, values)))
        save(evidence, "queries.json", after)
        save(
            evidence,
            "complete.json",
            {
                "scope": asdict(scope),
                "archive": archive_result,
                "event_receipt": asdict(receipt),
                "source_counts": conversion.run_manifest["counts"],
                "query_retry_unchanged": True,
                "online_late_tested": False,
            },
        )
    finally:
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--private-config", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--observations", type=int, default=4, choices=range(4, 33))
    arguments = parser.parse_args()
    run(
        arguments.evidence.resolve(),
        arguments.private_config.resolve(),
        arguments.project,
        arguments.observations,
    )
