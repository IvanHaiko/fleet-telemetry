"""Remote CLI-context job; source publication and runtime lifecycle are parent-owned."""

import argparse
import fcntl
import json
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, cast

from pyflink.common import Configuration, Duration, Types, WatermarkStrategy
from pyflink.common.job_execution_result import JobExecutionResult
from pyflink.datastream import (
    DataStream,
    RuntimeExecutionMode,
    StreamExecutionEnvironment,
)
from pyflink.datastream.functions import (
    KeyedProcessFunction,
    MapFunction,
    RuntimeContext,
)
from pyflink.datastream.time_domain import TimeDomain
from pyflink.table import StreamTableEnvironment

from battery_gate import INVALID, Admitted, BatteryTimestamp
from battery_operator import BatteryOperator
from kafka_bounds import after_source, before_source
from m3_completion_evidence import require
from paced_source import receipt
from partition_input import PartitionManifest, build_input
from watermark_probe import ObservedBattery


def append_trace(control: Path, row: str, *, invalid: bool = False) -> None:
    """Append bounded safe operator rows; invalid rows have their own writer lane."""
    require(len(row.encode()) <= 65536)
    path = control / "trace.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0, 2)
        require(handle.tell() + len(row.encode()) + 1 <= 1_048_576)
        handle.write(row + "\n")


class CheckpointSwitch(Protocol):
    def disableCheckpointing(self) -> None: ...


class JavaClass(Protocol):
    def getName(self) -> str: ...


class JavaEnvironment(Protocol):
    def getClass(self) -> JavaClass: ...


class TransformationInputs(Protocol):
    def size(self) -> int: ...
    def get(self, index: int) -> "Transformation": ...


class Transformation(Protocol):
    def getName(self) -> str: ...
    def setName(self, name: str) -> None: ...
    def setParallelism(self, parallelism: int) -> None: ...
    def getInputs(self) -> TransformationInputs: ...


class JavaStream(Protocol):
    def getTransformation(self) -> Transformation: ...


def name_timestamp_bridge(timed: DataStream) -> None:
    """Name the SDK 2.2.1 bridge through public Java Transformation methods."""
    remove = cast(JavaStream, timed._j_data_stream).getTransformation()
    require(remove.getName() == "Remove-Timestamp")
    require(remove.getInputs().size() == 1)
    generator = remove.getInputs().get(0)
    require(generator.getInputs().size() == 1)
    extract = generator.getInputs().get(0)
    require(extract.getName() == "Extract-Timestamp")
    for node, name in (
        (extract, "Extract-Timestamp"),
        (generator, "Watermark-Generator"),
        (remove, "Remove-Timestamp"),
    ):
        node.setName(name)
        node.setParallelism(2)


class TraceBattery(ObservedBattery):
    def open(self, runtime_context: RuntimeContext) -> None:
        super().open(runtime_context)
        self.deadline = time.monotonic() + 300
        self.rows = 0

    def emit(self, rows: Iterator[str]) -> Iterator[str]:
        for row in rows:
            self.rows += 1
            require(self.rows <= 512)
            append_trace(self.control, row)
            yield row

    def process_element(
        self, value: Admitted, ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        yield from self.emit(super().process_element(value, ctx))

    def on_timer(
        self, timestamp: int, ctx: KeyedProcessFunction.OnTimerContext
    ) -> Iterator[str]:
        if ctx.time_domain() == TimeDomain.EVENT_TIME:
            yield from self.emit(BatteryOperator.on_timer(self, timestamp, ctx))
            self.publish(ctx)
        else:
            require(time.monotonic() < self.deadline)
            self.publish(ctx)
            ctx.timer_service().register_processing_time_timer(
                cast(int, ctx.timer_service().current_processing_time()) + 100  # type: ignore[no-untyped-call]
            )


class InvalidTrace(MapFunction):
    def __init__(self, control: Path) -> None:
        self.control = control
        self.seen: set[int] = set()

    def map(self, value: str) -> str:
        row = cast(dict[str, object], json.loads(value))
        index = row["observation_index"]
        require(type(index) is int)
        index = cast(int, index)
        require(index not in self.seen and len(self.seen) < 128)
        self.seen.add(index)
        # A file lock serializes this lane with the keyed observer writer.
        # Invalid input never enters the watermark observer.
        append_trace(self.control, value, invalid=True)
        return value


def run(manifest: PartitionManifest, control: Path, scratch: Path) -> None:
    """Submit through the CLI context and await its actual execution result."""
    require(control.is_absolute() and scratch.is_absolute())
    control.mkdir(parents=True, exist_ok=False)
    scratch.mkdir(parents=True, exist_ok=False)
    before_source(manifest.topic, manifest.ends)
    config = Configuration()
    for key, value in {
        "parallelism.default": "2",
        "restart-strategy.type": "none",
        "python.execution-mode": "process",
        "python.fn-execution.bundle.size": "1",
        "python.fn-execution.bundle.time": "50",
        "python.pythonpath": "/workspace:/workspace/runtime/pyflink",
        "io.tmp.dirs": str(scratch),
    }.items():
        config.set_string(key, value)
    env = StreamExecutionEnvironment.get_execution_environment(config)
    # Refuse the local fallback supplied outside the remote Flink CLI context.
    require(
        cast(JavaEnvironment, env._j_stream_execution_environment).getClass().getName()
        == "org.apache.flink.client.program.StreamContextEnvironment"
    )
    env.set_parallelism(2)
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
    env.get_config().set_auto_watermark_interval(100)
    checkpoint = env.get_checkpoint_config()
    cast(CheckpointSwitch, checkpoint._j_checkpoint_config).disableCheckpointing()
    require(not checkpoint.is_checkpointing_enabled())
    modules = (
        "partition_input.py",
        "kafka_bounds.py",
        "partition_job.py",
        "m3_completion_evidence.py",
        "battery_gate.py",
        "battery_operator.py",
        "worker_probe.py",
        "paced_source.py",
        "watermark_probe.py",
        "probe_support.py",
    )
    for module in modules:
        env.add_python_file(str(Path(__file__).with_name(module).resolve()))
    for module in ("telemetry_reader.py", "fleet_telemetry.py"):
        env.add_python_file(str(Path("/workspace", module)))
    tables = StreamTableEnvironment.create(env)
    tables.get_config().get_configuration().set_integer("parallelism.default", 2)
    gated = build_input(env, tables, manifest, control)
    strategy = (
        WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_seconds(2))
        .with_idleness(Duration.of_seconds(30))
        .with_timestamp_assigner(BatteryTimestamp())
    )
    timed = (
        gated.forward().assign_timestamps_and_watermarks(strategy).set_parallelism(2)
    )
    name_timestamp_bridge(timed)
    observed = (
        timed.key_by(
            lambda value: (manifest.scope.dataset_run_id, value[1]),
            key_type=Types.TUPLE([Types.STRING(), Types.STRING()]),
        )
        .process(TraceBattery(manifest.scope, control, 128), output_type=Types.STRING())
        .name("ObservedBattery")
        .set_parallelism(1)
    )
    observed.print().set_parallelism(1)
    gated.get_side_output(INVALID).map(
        InvalidTrace(control), output_type=Types.STRING()
    ).set_parallelism(1).print().set_parallelism(1)
    plan = env.get_execution_plan()
    (control / "execution-plan.json").write_text(plan)
    graph = cast(dict[str, object], json.loads(plan))
    nodes = cast(list[dict[str, object]], graph["nodes"])
    # Flink 2.2.1 StreamGraph JSON uses "type" for the display name and
    # predecessor "id" for the actual upstream node.
    lane = []
    for name, parallelism in (
        ("PartitionAdmission", 2),
        ("Extract-Timestamp", 2),
        ("Watermark-Generator", 2),
        ("Remove-Timestamp", 2),
        ("ObservedBattery", 1),
    ):
        matches = [node for node in nodes if node.get("type") == name]
        require(len(matches) == 1)
        node = matches[0]
        require(node.get("parallelism") == parallelism)
        lane.append(node)
    for upstream, downstream in zip(lane[:3], lane[1:4], strict=True):
        edges = cast(list[dict[str, object]], downstream.get("predecessors", []))
        require(len(edges) == 1)
        require(edges[0].get("id") == upstream["id"])
        require(edges[0].get("ship_strategy") == "FORWARD")
    client = env.execute_async("m3-partition-idleness")
    require(client is not None)
    job_id = str(client.get_job_id())
    receipt(control / "ready.json", {"job_id": job_id, "client_pid": os.getpid()})
    result: object = client.get_job_execution_result().result()  # type: ignore[no-untyped-call]
    require(isinstance(result, JobExecutionResult))
    result = cast(JobExecutionResult, result)
    after_source(manifest.topic, manifest.ends, control)
    receipt(
        control / "finished.json",
        {
            "status": "FINISHED",
            "job_id": job_id,
            "net_runtime_ms": result.get_net_runtime(),
        },
    )


class Arguments(argparse.Namespace):
    manifest: Path
    control: Path
    scratch: Path


def main() -> None:
    """CLI entry point for remote standalone submission."""
    parser = argparse.ArgumentParser()
    for name in ("manifest", "control", "scratch"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(namespace=Arguments())
    run(PartitionManifest.read(args.manifest), args.control, args.scratch)


if __name__ == "__main__":
    main()
