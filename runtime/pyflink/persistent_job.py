"""Finite Kafka job submitted only through the remote Flink CLI context."""

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pyflink.common import Configuration, JobExecutionResult, Types, WatermarkStrategy
from pyflink.common.completable_future import CompletableFuture
from pyflink.datastream import (
    CheckpointingMode,
    ExternalizedCheckpointRetention,
    RuntimeExecutionMode,
    StreamExecutionEnvironment,
)
from pyflink.table import StreamTableEnvironment
from pyflink.version import __version__ as pyflink_version

from battery_gate import ADMITTED, INVALID, BatteryGate, BatteryScope, BatteryTimestamp
from kafka_bounds import SourceBoundsError, after_source, before_source
from persistent_observation import (
    InvalidObservation,
    KafkaObservation,
    ObservedBattery,
    publish,
)


@dataclass(frozen=True)
class Manifest:
    """Validated parent-owned finite input scope; no expected output or offsets."""

    topic: str
    group: str
    end: int
    scope: BatteryScope


def _object(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("persistent_manifest_shape")
    return cast(dict[str, object], value)


def load_manifest(path: Path) -> Manifest:
    """Read a strictly bounded manifest without interpolating untrusted SQL."""
    with path.open("rb") as handle:
        wire = handle.read(16385)
    if len(wire) > 16384:
        raise ValueError("persistent_manifest_size")

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("persistent_manifest_duplicate")
            result[key] = value
        return result

    try:
        decoded: object = json.loads(wire, object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("persistent_manifest_json") from None
    row = _object(decoded, {"profile", "topic", "bootstrap", "group", "end", "scope"})
    topic, group, end = row["topic"], row["group"], row["end"]
    if (
        row["profile"] != "m3-persistent-input-v1"
        or row["bootstrap"] != "kafka:9092"
        or not isinstance(topic, str)
        or re.fullmatch(
            r"m2\.m3-final-[a-z0-9-]{1,64}\.telemetry\.canonical\.v1", topic
        )
        is None
        or not isinstance(group, str)
        or re.fullmatch(r"[a-zA-Z0-9._-]{1,192}", group) is None
        or type(end) is not int
        or not 4 <= end <= 32
    ):
        raise ValueError("persistent_manifest_scope")
    scope_row = _object(
        row["scope"],
        {
            "dataset_run_id",
            "pipeline_version",
            "source_log_id",
            "timestamp_min",
            "timestamp_max",
        },
    )
    if any(
        not isinstance(v, str) or not 1 <= len(v) <= 256 for v in scope_row.values()
    ):
        raise ValueError("persistent_manifest_scope")
    scope = BatteryScope(**cast(dict[str, str], scope_row))
    try:
        scope.validate()
    except (ValueError, TypeError, OverflowError):
        raise ValueError("persistent_manifest_scope") from None
    return Manifest(topic, group, end, scope)


def _state_path(path: Path) -> None:
    if (
        not path.is_absolute()
        or path == Path("/state")
        or not path.is_relative_to("/state")
        or ".." in path.parts
        or re.fullmatch(r"/state/[a-zA-Z0-9_./-]{1,192}", str(path)) is None
        or not path.resolve().is_relative_to("/state")
    ):
        raise ValueError("persistent_state_path")


def build_environment(checkpoints: Path) -> StreamExecutionEnvironment:
    """Use the CLI context, preserving its explicit checkpoint restore settings."""
    _state_path(checkpoints)
    if pyflink_version != "2.2.1":
        raise RuntimeError("persistent_sdk_version")
    os.environ["_python_worker_execution_mode"] = "process"
    # No local/remote environment factory: the CLI supplies a context carrying
    # SavepointRestoreSettings. Stacking config must not replace those settings.
    config = Configuration()
    for key, value in {
        "execution.target": "remote",
        "python.execution-mode": "process",
        "execution.checkpointing.storage": "filesystem",
        "execution.checkpointing.dir": checkpoints.as_uri(),
        "execution.checkpointing.num-retained": "3",
        "restart-strategy.type": "fixed-delay",
        "restart-strategy.fixed-delay.attempts": "2",
        "restart-strategy.fixed-delay.delay": "3 s",
        "table.exec.resource.default-parallelism": "1",
        "table.exec.uid.generation": "ALWAYS",
        "table.exec.uid.format": "persistent-<id>-<transformation>",
    }.items():
        config.set_string(key, value)
    config.set_integer("python.fn-execution.bundle.size", 1)
    env = StreamExecutionEnvironment.get_execution_environment(config)
    # An execution.target override alone can turn a standalone Python invocation
    # into a remote client. Require the actual CLI context instead.
    context_name: object = env._j_stream_execution_environment.getClass().getName()
    if context_name != "org.apache.flink.client.program.StreamContextEnvironment":
        raise RuntimeError("persistent_cli_context_required")
    env.set_parallelism(1)
    env.set_max_parallelism(1)
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
    env.get_config().set_auto_watermark_interval(0)
    env.enable_checkpointing(3_600_000, CheckpointingMode.EXACTLY_ONCE)
    checkpoint_config = env.get_checkpoint_config()
    checkpoint_config.set_externalized_checkpoint_retention(
        ExternalizedCheckpointRetention.RETAIN_ON_CANCELLATION
    )
    checkpoint_config.set_max_concurrent_checkpoints(1)
    checkpoint_config.set_checkpoint_timeout(30_000)
    return env


def attach_graph(
    env: StreamExecutionEnvironment,
    manifest: Manifest,
    control: Path,
    run_tag: str,
    identity_limit: int,
) -> None:
    """Build the same bounded Table bridge and managed graph for every submission."""
    for name in (
        "persistent_observation.py",
        "battery_gate.py",
        "battery_operator.py",
        "worker_probe.py",
        "kafka_bounds.py",
    ):
        env.add_python_file(str(Path(__file__).with_name(name).resolve()))
    tables = StreamTableEnvironment.create(env)
    tables.get_config().set("table.exec.resource.default-parallelism", "1")
    tables.get_config().set("table.exec.uid.generation", "ALWAYS")
    tables.get_config().set("table.exec.uid.format", "persistent-<id>-<transformation>")
    tables.execute_sql(f"""
        CREATE TEMPORARY TABLE persistent_input (
            record_key BYTES, payload BYTES,
            topic_name STRING METADATA FROM 'topic' VIRTUAL,
            partition_id INT METADATA FROM 'partition' VIRTUAL,
            offset_id BIGINT METADATA FROM 'offset' VIRTUAL
        ) WITH (
            'connector' = 'kafka', 'topic' = '{manifest.topic}',
            'properties.bootstrap.servers' = 'kafka:9092',
            'properties.group.id' = '{manifest.group}',
            'properties.enable.auto.commit' = 'false',
            'properties.auto.offset.reset' = 'none',
            'properties.commit.offsets.on.checkpoint' = 'true',
            'scan.startup.mode' = 'specific-offsets',
            'scan.startup.specific-offsets' = 'partition:0,offset:0',
            'scan.bounded.mode' = 'specific-offsets',
            'scan.bounded.specific-offsets' = 'partition:0,offset:{manifest.end}',
            'scan.topic-partition-discovery.interval' = '0',
            'key.format' = 'raw', 'key.fields' = 'record_key',
            'value.format' = 'raw', 'value.fields-include' = 'EXCEPT_KEY'
        )
    """)
    raw = tables.to_data_stream(tables.from_path("persistent_input"))
    observations = (
        raw.map(
            KafkaObservation(control, run_tag, manifest.topic, manifest.end),
            output_type=Types.TUPLE(
                [Types.LONG(), Types.PRIMITIVE_ARRAY(Types.BYTE())]
            ),
        )
        .uid("persistent-kafka-observation-v1")
        .set_parallelism(1)
    )
    gated = (
        observations.process(BatteryGate(manifest.scope), output_type=ADMITTED)
        .uid("persistent-battery-admission-v1")
        .set_parallelism(1)
    )
    timed = (
        gated.assign_timestamps_and_watermarks(
            WatermarkStrategy.for_monotonous_timestamps().with_timestamp_assigner(
                BatteryTimestamp()
            )
        )
        .uid("persistent-terminal-watermarks-v1")
        .set_parallelism(1)
    )
    scope = manifest.scope
    processed = (
        timed.key_by(
            lambda value: (scope.dataset_run_id, value[1]),
            key_type=Types.TUPLE([Types.STRING(), Types.STRING()]),
        )
        .process(
            ObservedBattery(scope, control, run_tag, identity_limit),
            output_type=Types.STRING(),
        )
        .uid("persistent-battery-state-v1")
        .set_parallelism(1)
    )
    invalid = (
        gated.get_side_output(INVALID)
        .map(InvalidObservation(control, run_tag), output_type=Types.STRING())
        .uid("persistent-invalid-diagnostic-v1")
        .set_parallelism(1)
    )
    processed.union(invalid).print().uid("persistent-print-v1").set_parallelism(1)


def _await(future: CompletableFuture, timeout: float | None = None) -> object:
    deadline = None if timeout is None else time.monotonic() + timeout
    while not future.done():
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("persistent_cancel_timeout")
        time.sleep(0.05)
    result: object = future.result()  # type: ignore[no-untyped-call]
    return result


def run(
    manifest_path: Path,
    control: Path,
    checkpoints: Path,
    run_tag: str,
    identity_limit: int,
) -> None:
    """Submit, retain job identity, and require a successful execution result."""
    if (
        run_tag not in ("initial", "cold")
        or type(identity_limit) is not int
        or not (1 <= identity_limit <= 128)
    ):
        raise ValueError("persistent_job_scope")
    _state_path(control)
    _state_path(checkpoints)
    if (
        control == checkpoints
        or control.is_relative_to(checkpoints)
        or (checkpoints.is_relative_to(control))
    ):
        raise ValueError("persistent_overlapping_paths")
    control.mkdir(parents=True, exist_ok=True)
    if (
        any(control.glob(f"*-{run_tag}.json"))
        or any(control.glob(f"*-{run_tag}-*.json"))
        or (control / f"trace-{run_tag}.jsonl").exists()
    ):
        raise ValueError("persistent_run_tag_reused")
    client = None
    job_id: str | None = None
    try:
        manifest = load_manifest(manifest_path)
        low = before_source(manifest.topic, (manifest.end,))
        publish(control, f"admission-{run_tag}.json", {"low_offsets": low})
        env = build_environment(checkpoints)
        attach_graph(env, manifest, control, run_tag, identity_limit)
        client = env.execute_async("persistent-battery-recovery-v1")
        job_id = str(client.get_job_id())
        publish(
            control,
            f"ready-{run_tag}.json",
            {
                "job_id": job_id,
                "client_pid": os.getpid(),
            },
        )
        result = _await(client.get_job_execution_result())
        if not isinstance(result, JobExecutionResult):
            raise RuntimeError("persistent_execution_result_required")
        duration: object = result.get_net_runtime()
        if (
            str(result.get_job_id()) != job_id
            or type(duration) is not int
            or duration < 0
        ):
            raise RuntimeError("persistent_execution_result_invalid")
        after_source(manifest.topic, (manifest.end,), control)
        publish(
            control,
            f"finished-{run_tag}.json",
            {
                "status": "FINISHED",
                "job_id": job_id,
                "net_runtime_ms": duration,
            },
        )
    except BaseException as original:
        try:
            publish(
                control,
                f"failed-{run_tag}.json",
                {
                    "status": "SUBMISSION_OR_EXECUTION_FAILED",
                    "job_id": job_id,
                    "reason": str(original)
                    if isinstance(original, SourceBoundsError)
                    else "persistent_job_failed",
                    "client_pid": os.getpid(),
                },
            )
        except Exception:
            original.add_note("persistent_failure_receipt_failed")
        if client is not None:
            try:
                _await(client.cancel(), 5)
            except BaseException:
                original.add_note("persistent_cancel_unconfirmed")
        raise


def main() -> None:
    """Parse the explicit parent interface; lifecycle control stays external."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--run-tag", choices=("initial", "cold"), required=True)
    parser.add_argument("--identity-limit", type=int, required=True)
    args = parser.parse_args()
    run(
        args.manifest, args.control, args.checkpoints, args.run_tag, args.identity_limit
    )


if __name__ == "__main__":
    main()
