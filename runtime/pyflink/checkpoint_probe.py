"""Finite Kafka checkpoint experiment; the external parent controls publication."""

import argparse
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

from pyflink.common import (
    Configuration,
    Duration,
    JobExecutionResult,
    Types,
    WatermarkStrategy,
)
from pyflink.common.completable_future import CompletableFuture
from pyflink.datastream import (
    CheckpointingMode,
    ExternalizedCheckpointRetention,
    RuntimeExecutionMode,
    StreamExecutionEnvironment,
)
from pyflink.table import StreamTableEnvironment
from pyflink.version import __version__ as pyflink_version
from tests.test_reference import scope as reference_scope

from battery_gate import ADMITTED, INVALID, BatteryGate, BatteryScope, BatteryTimestamp
from checkpoint_control import publish
from checkpoint_operator import KafkaObservation, RecoveryBattery


def _await(future: CompletableFuture, deadline: float) -> object:
    while not future.done():
        if time.monotonic() >= deadline:
            raise TimeoutError("checkpoint_control_deadline")
        time.sleep(0.05)
    return future.result()  # type: ignore[no-untyped-call]


def run(
    connector: Path,
    topic: str,
    end: int,
    fault_offset: int,
    control: Path,
    scratch: Path,
    rest_port: int,
) -> None:
    """Submit a real transient job, await finite success, cancel on failure."""
    if (
        re.fullmatch(r"m2\.m3-cp-[a-z0-9-]{1,40}\.telemetry\.canonical\.v1", topic)
        is None
        or not 4 <= end <= 32
        or not 3 <= fault_offset < end
        or not 1024 <= rest_port <= 65535
        or not connector.is_file()
        or not scratch.is_absolute()
        or str(scratch).startswith("/mnt/")
        or scratch.exists()
        or not control.is_absolute()
    ):
        raise ValueError("invalid_checkpoint_probe_scope")
    control.mkdir(parents=True, exist_ok=True)
    if any(control.iterdir()):
        raise ValueError("checkpoint_control_not_empty")
    scratch.mkdir(parents=True, exist_ok=False)
    checkpoints = scratch / "checkpoints"
    checkpoints.mkdir()
    scope = BatteryScope(**asdict(reference_scope()))
    scope.validate()
    # PyFlink 2.2.1 _open() otherwise starts a loopback SDK worker in this client.
    # python.execution-mode alone does not control that private launch selector.
    if pyflink_version != "2.2.1":
        raise RuntimeError("unsupported_checkpoint_worker_sdk")
    os.environ["_python_worker_execution_mode"] = "process"
    client_pid = os.getpid()
    config = Configuration()
    for key, value in {
        "jobmanager.bind-host": "127.0.0.1",
        "jobmanager.rpc.address": "127.0.0.1",
        "taskmanager.bind-host": "127.0.0.1",
        "taskmanager.host": "127.0.0.1",
        "rest.bind-address": "127.0.0.1",
        "rest.address": "127.0.0.1",
        "rest.bind-port": str(rest_port),
        "rest.port": str(rest_port),
        "taskmanager.memory.process.size": "1024m",
        "io.tmp.dirs": str(scratch),
        "python.executable": sys.executable,
        "python.client.executable": sys.executable,
        "python.execution-mode": "process",
        "execution.checkpointing.storage": "filesystem",
        "restart-strategy.type": "fixed-delay",
        "restart-strategy.fixed-delay.attempts": "1",
        "restart-strategy.fixed-delay.delay": "3 s",
        "execution.checkpointing.dir": checkpoints.as_uri(),
    }.items():
        config.set_string(key, value)
    config.set_integer("taskmanager.numberOfTaskSlots", 1)
    config.set_integer("python.fn-execution.bundle.size", 1)
    env = StreamExecutionEnvironment.get_execution_environment(config)
    env.set_parallelism(1)
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
    env.get_config().set_auto_watermark_interval(0)
    env.enable_checkpointing(3_600_000, CheckpointingMode.EXACTLY_ONCE)
    env.get_checkpoint_config().set_externalized_checkpoint_retention(
        ExternalizedCheckpointRetention.RETAIN_ON_CANCELLATION
    )
    for name in (
        "checkpoint_probe.py",
        "checkpoint_control.py",
        "checkpoint_operator.py",
        "battery_gate.py",
        "battery_operator.py",
        "worker_probe.py",
    ):
        env.add_python_file(str(Path(__file__).with_name(name).resolve()))
    env.add_jars(connector.resolve().as_uri())
    tables = StreamTableEnvironment.create(env)
    tables.execute_sql(f"""
        CREATE TEMPORARY TABLE checkpoint_input (
            record_key BYTES, payload BYTES,
            topic_name STRING METADATA FROM 'topic' VIRTUAL,
            partition_id INT METADATA FROM 'partition' VIRTUAL,
            offset_id BIGINT METADATA FROM 'offset' VIRTUAL
        ) WITH (
            'connector' = 'kafka', 'topic' = '{topic}',
            'properties.bootstrap.servers' = '127.0.0.1:19092',
            'properties.group.id' = '{topic}.recovery',
            'properties.enable.auto.commit' = 'false',
            'properties.auto.offset.reset' = 'none',
            'properties.commit.offsets.on.checkpoint' = 'true',
            'scan.startup.mode' = 'specific-offsets',
            'scan.startup.specific-offsets' = 'partition:0,offset:0',
            'scan.bounded.mode' = 'specific-offsets',
            'scan.bounded.specific-offsets' = 'partition:0,offset:{end}',
            'scan.topic-partition-discovery.interval' = '0',
            'key.format' = 'raw', 'key.fields' = 'record_key',
            'value.format' = 'raw', 'value.fields-include' = 'EXCEPT_KEY'
        )
    """)
    raw = tables.to_data_stream(tables.from_path("checkpoint_input"))
    observations = raw.map(
        KafkaObservation(),
        output_type=Types.TUPLE([Types.LONG(), Types.PRIMITIVE_ARRAY(Types.BYTE())]),
    ).uid("checkpoint-kafka-observation-v1")
    gated = observations.process(BatteryGate(scope), output_type=ADMITTED).uid(
        "checkpoint-battery-admission-v1"
    )
    timed = gated.assign_timestamps_and_watermarks(
        WatermarkStrategy.for_bounded_out_of_orderness(
            Duration.of_seconds(2)
        ).with_timestamp_assigner(BatteryTimestamp())
    )
    processed = (
        timed.key_by(
            lambda value: (scope.dataset_run_id, value[1]),
            key_type=Types.TUPLE([Types.STRING(), Types.STRING()]),
        )
        .process(
            RecoveryBattery(scope, control, fault_offset, client_pid),
            output_type=Types.STRING(),
        )
        .uid("checkpoint-battery-state-v1")
    )
    processed.union(gated.get_side_output(INVALID)).print().uid(
        "checkpoint-diagnostic-print-v1"
    )
    client = env.execute_async("m3-kafka-checkpoint-evidence")
    try:
        deadline = time.monotonic() + 210
        execution_result = client.get_job_execution_result()
        job_id = str(client.get_job_id())
        publish(
            control,
            "ready.json",
            {
                "job_id": job_id,
                "rest_port": rest_port,
                "client_pid": client_pid,
            },
        )
        result = _await(execution_result, deadline)
        if not isinstance(result, JobExecutionResult):
            raise RuntimeError("checkpoint_job_result_required")
        result_job_id = str(result.get_job_id())
        net_runtime_ms = result.get_net_runtime()
        if (
            result_job_id != job_id
            or type(net_runtime_ms) is not int
            or net_runtime_ms <= 0
        ):
            raise RuntimeError("invalid_checkpoint_job_result")
        publish(
            control,
            "finished.json",
            {
                "status": "FINISHED",
                "completion_confirmation": "successful_job_execution_result",
                "job_id": result_job_id,
                "net_runtime_ms": net_runtime_ms,
            },
        )
    except BaseException as original:
        try:
            _await(client.cancel(), time.monotonic() + 5)
        except Exception:
            original.add_note(
                "checkpoint_cancel_failed; parent_process_group_check_required"
            )
        raise


def main() -> None:
    """Parse explicit parent-owned paths and finite source bounds."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connector", type=Path, required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--fault-offset", type=int, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--rest-port", type=int, required=True)
    args = parser.parse_args()
    run(
        args.connector,
        args.topic,
        args.end,
        args.fault_offset,
        args.control,
        args.scratch,
        args.rest_port,
    )


if __name__ == "__main__":
    main()
