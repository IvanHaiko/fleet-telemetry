"""Long-lived checkpointed Kafka -> battery processing -> Kafka transaction job."""

import argparse
import json
import os
import re
from pathlib import Path
from typing import cast

from pyflink.common import Configuration, Duration, Types, WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import (
    CheckpointingMode,
    DataStream,
    ExternalizedCheckpointRetention,
    KeyedStream,
    OutputTag,
    StreamExecutionEnvironment,
)
from pyflink.datastream.connectors.base import DeliveryGuarantee
from pyflink.datastream.connectors.kafka import (
    KafkaRecordSerializationSchema,
    KafkaSink,
)
from pyflink.java_gateway import get_gateway
from pyflink.table import StreamTableEnvironment
from telemetry.continuous_connection import flink_properties, source_options

from continuous_operator import (
    INVALID,
    PARTITION_OUTPUTS,
    TIMED,
    Battery,
    Gate,
    Timestamp,
)


def partition_watermarks(timed: DataStream, lanes: int = 1) -> None:
    """Keep all three PyFlink timestamp bridge nodes in one partition branch."""
    remove = timed._j_data_stream.getTransformation()
    generator = remove.getInputs().get(0)
    extract = generator.getInputs().get(0)
    if (
        remove.getName() != "Remove-Timestamp"
        or extract.getName() != "Extract-Timestamp"
    ):
        raise ValueError("continuous_timestamp_bridge")
    for node in (extract, generator, remove):
        node.setParallelism(lanes)


def native_side_output(stream: DataStream, tag: OutputTag) -> DataStream:
    """Keep the declared Java type without PyFlink's extra identity Python map."""
    return DataStream(  # type: ignore[no-untyped-call]
        stream._j_data_stream.getSideOutput(tag.get_java_output_tag())  # type: ignore[no-untyped-call]
    )


def check_partition_plan(
    plan: str, native_time: bool = False, battery_parallelism: int = 1
) -> None:
    """Require eighteen isolated watermark-to-state branches in the real plan."""
    nodes = json.loads(plan)["nodes"]
    by_id = {node["id"]: node for node in nodes}
    removes = [
        node
        for node in nodes
        if (
            node["type"].startswith("continuous-partition-time-")
            if native_time
            else node["type"] == "Remove-Timestamp"
        )
    ]
    if len(removes) != 18:
        raise ValueError("continuous_partition_plan_branches")
    seen: dict[int, str] = {}
    for remove in removes:
        current = remove
        while not current["type"].startswith("continuous-partition-input-"):
            if current["parallelism"] != 1:
                raise ValueError("continuous_partition_plan_parallelism")
            edges = current.get("predecessors", [])
            if len(edges) != 1 or edges[0]["ship_strategy"] != "FORWARD":
                raise ValueError("continuous_partition_plan_shuffle")
            current = by_id[edges[0]["id"]]
        if current["parallelism"] != 1:
            raise ValueError("continuous_partition_plan_merge")
        seen[remove["id"]] = current["type"].split(",")[0]
    if set(seen.values()) != {f"continuous-partition-input-{p}" for p in range(18)}:
        raise ValueError("continuous_partition_plan_inputs")
    batteries = [
        node
        for node in nodes
        if node["type"].startswith("continuous-partition-battery-")
    ]
    if len(batteries) != 18:
        raise ValueError("continuous_partition_plan_batteries")
    for battery in batteries:
        current = battery
        while current["id"] not in seen:
            edges = current.get("predecessors", [])
            expected = battery_parallelism if current["id"] == battery["id"] else 1
            if current["parallelism"] != expected or len(edges) != 1:
                raise ValueError("continuous_partition_plan_state_merge")
            current = by_id[edges[0]["id"]]
        suffix = (
            battery["type"].split(",")[0].removeprefix("continuous-partition-battery-")
        )
        if seen[current["id"]] != f"continuous-partition-input-{suffix}":
            raise ValueError("continuous_partition_plan_state_input")


def partition_battery(
    stream: DataStream,
    run_id: str,
    partition: int,
    native_time: bool = False,
    battery_parallelism: int = 1,
) -> DataStream:
    """Merge only this gate side output, then assign time and retain keyed state.

    No unrelated partition may hold this branch's watermark back. The gate
    checks the fixed vehicle-to-partition recipe before routing any measurement.
    """
    if native_time:
        jvm = get_gateway().jvm
        function = jvm.telemetry.flink.PartitionTime()
        single_java = (
            stream._j_data_stream.rebalance()
            .map(function)
            .returns(stream._j_data_stream.getType())
            .setParallelism(1)
            .name(f"continuous-partition-input-{partition}")
            .uid(f"continuous-native-input-v1-{partition}")
        )
        strategy = (
            jvm.org.apache.flink.api.common.eventtime.WatermarkStrategy.forBoundedOutOfOrderness(
                jvm.java.time.Duration.ofSeconds(2)
            )
            .withIdleness(jvm.java.time.Duration.ofSeconds(30))
            .withTimestampAssigner(function)
        )
        timed = DataStream(  # type: ignore[no-untyped-call]
            single_java.assignTimestampsAndWatermarks(strategy)
            .setParallelism(1)
            .name(f"continuous-partition-time-{partition}")
            .uid(f"continuous-native-time-v1-{partition}")
        )
        with_key = (
            timed._j_data_stream.map(jvm.telemetry.flink.PartitionTime.AddKey())
            .returns(Types.ROW([Types.STRING(), TIMED]).get_java_type_info())
            .setParallelism(1)
            .name(f"continuous-native-key-{partition}")
        )
        keyed = KeyedStream(
            with_key.keyBy(
                jvm.KeyByKeySelector(), Types.ROW([Types.STRING()]).get_java_type_info()
            ),
            TIMED,
            timed,
        )
        return (
            keyed.process(Battery(run_id), output_type=Types.STRING())
            .set_parallelism(battery_parallelism)
            .name(f"continuous-partition-battery-{partition}")
            .uid(f"continuous-partition-battery-v4-{partition}")
        )
    single = (
        stream.rebalance()
        .map(lambda row: row, output_type=TIMED)
        .set_parallelism(1)
        .name(f"continuous-partition-input-{partition}")
        .uid(f"continuous-partition-input-v3-{partition}")
    )
    timed = (
        single.forward()
        .assign_timestamps_and_watermarks(
            WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_seconds(2))
            .with_idleness(Duration.of_seconds(30))
            .with_timestamp_assigner(Timestamp())
        )
        .set_parallelism(1)
        .uid(f"continuous-partition-time-v3-{partition}")
    )
    partition_watermarks(timed)
    return (
        timed.key_by(lambda row: row[0], key_type=Types.STRING())
        .process(Battery(run_id), output_type=Types.STRING())
        .set_parallelism(battery_parallelism)
        .name(f"continuous-partition-battery-{partition}")
        .uid(f"continuous-partition-battery-v4-{partition}")
    )


def run(path: Path) -> None:
    config = cast(dict[str, object], json.loads(path.read_bytes()))
    kafka_properties = flink_properties(config)
    for name in ("run_id", "input_topic", "output_topic", "processing_group"):
        if (
            not isinstance(config[name], str)
            or re.fullmatch(r"[a-zA-Z0-9._-]{1,128}", cast(str, config[name])) is None
        ):
            raise ValueError("continuous_config_identifier")
    sources = config["source_logs"]
    if not isinstance(sources, dict) or not 1 <= len(sources) <= 1024:
        raise ValueError("continuous_vehicle_bound")
    live_topic = config.get("live_output_topic")
    jar = config.get("partition_time_jar")
    battery_parallelism = config.get("battery_parallelism", 1)
    if (
        type(battery_parallelism) is not int
        or not 1 <= battery_parallelism <= 4
        or (battery_parallelism > 1 and not jar)
    ):
        raise ValueError("continuous_battery_parallelism")
    if live_topic and (not isinstance(jar, str) or not jar.startswith("file:///")):
        raise ValueError("continuous_live_native_jar_required")
    if live_topic is not None and (
        not isinstance(live_topic, str)
        or re.fullmatch(r"[a-zA-Z0-9._-]{1,128}", live_topic) is None
        or live_topic in (config["input_topic"], config["output_topic"])
    ):
        raise ValueError("continuous_live_topic")
    os.environ["_python_worker_execution_mode"] = "process"
    settings = Configuration()
    for key, value in {
        "python.execution-mode": "process",
        "execution.target": "remote",
        "execution.checkpointing.storage": "filesystem",
        "execution.checkpointing.dir": "file:///state/continuous-checkpoints",
        "restart-strategy.type": "fixed-delay",
        "restart-strategy.fixed-delay.attempts": "10",
        "restart-strategy.fixed-delay.delay": "3 s",
        "table.exec.resource.default-parallelism": "18",
        "table.exec.uid.generation": "ALWAYS",
        "table.exec.uid.format": "continuous-<id>-<transformation>",
    }.items():
        settings.set_string(key, value)
    settings.set_integer("python.fn-execution.bundle.size", 128)
    settings.set_integer("python.fn-execution.bundle.time", 50 if live_topic else 100)
    env = StreamExecutionEnvironment.get_execution_environment(settings)
    native_time = bool(config.get("partition_time_jar"))
    if native_time:
        env.add_jars(cast(str, config["partition_time_jar"]))
    env.set_parallelism(18)
    env.set_max_parallelism(128)
    if live_topic:
        env.set_buffer_timeout(10)
    env.get_config().set_auto_watermark_interval(500)
    env.enable_checkpointing(10_000, CheckpointingMode.EXACTLY_ONCE)
    checkpoints = env.get_checkpoint_config()
    checkpoints.set_checkpoint_timeout(120_000)
    checkpoints.set_max_concurrent_checkpoints(1)
    checkpoints.set_externalized_checkpoint_retention(
        ExternalizedCheckpointRetention.RETAIN_ON_CANCELLATION
    )
    env.add_python_file(str(Path(__file__).with_name("continuous_operator.py")))
    for module in (
        "fleet_telemetry.py",
        "telemetry_reader.py",
        "telemetry_reference.py",
    ):
        env.add_python_file("/workspace/" + module)
    tables = StreamTableEnvironment.create(env)
    tables.execute_sql(f"""
        CREATE TEMPORARY TABLE continuous_input (
          record_key BYTES, payload BYTES,
          topic_name STRING METADATA FROM 'topic' VIRTUAL,
          partition_id INT METADATA FROM 'partition' VIRTUAL,
          offset_id BIGINT METADATA FROM 'offset' VIRTUAL
        ) WITH (
          'connector'='kafka', 'topic'='{config["input_topic"]}',
          {source_options(kafka_properties)},
          'properties.group.id'='{config["processing_group"]}',
          'properties.enable.auto.commit'='false',
          'properties.auto.offset.reset'='none',
          'properties.commit.offsets.on.checkpoint'='true',
          'scan.startup.mode'='group-offsets', 'scan.parallelism'='18',
          'scan.topic-partition-discovery.interval'='0',
          'key.format'='raw', 'key.fields'='record_key', 'value.format'='raw',
          'value.fields-include'='EXCEPT_KEY'
        )
    """)
    raw = tables.to_data_stream(tables.from_path("continuous_input"))
    gated = (
        raw.forward()
        .process(Gate(config), output_type=TIMED)
        .set_parallelism(18)
        .uid("continuous-partition-gate-v3")
    )
    branches = [
        partition_battery(
            (
                native_side_output(gated, tag)
                if native_time
                else gated.get_side_output(tag)
            ),
            cast(str, config["run_id"]),
            p,
            native_time,
            battery_parallelism,
        )
        for p, tag in enumerate(PARTITION_OUTPUTS)
    ]
    processed = branches[0].union(*branches[1:])
    serializer = (
        KafkaRecordSerializationSchema.builder()
        .set_topic(cast(str, config["output_topic"]))
        .set_value_serialization_schema(SimpleStringSchema())
        .build()
    )
    history_builder = KafkaSink.builder()
    for key, value in kafka_properties.items():
        history_builder.set_property(key, value)
    sink = (
        history_builder.set_record_serializer(serializer)
        .set_delivery_guarantee(DeliveryGuarantee.EXACTLY_ONCE)
        .set_property("transaction.timeout.ms", "600000")
        .set_transactional_id_prefix(cast(str, config["run_id"]) + "-processing-")
        .build()
    )
    invalid = (
        native_side_output(gated, INVALID)
        if native_time
        else gated.get_side_output(INVALID)
    )
    processed.union(invalid).sink_to(sink).name(
        "continuous-history-output"
    ).set_parallelism(2).uid("continuous-kafka-output-v1")
    if live_topic:
        # Processing state remains checkpointed exactly once. This separate sink
        # exposes updates immediately and may repeat them after recovery.
        live_builder = KafkaSink.builder()
        for key, value in kafka_properties.items():
            live_builder.set_property(key, value)
        live_sink = (
            live_builder.set_record_serializer(
                KafkaRecordSerializationSchema.builder()
                .set_topic(live_topic)
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
            )
            .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
            .set_property("acks", "all")
            .set_property("enable.idempotence", "true")
            .set_property("linger.ms", "0")
            .build()
        )
        processed.sink_to(live_sink).name("continuous-live-output").set_parallelism(
            2
        ).uid("continuous-live-output-v1")
    plan = env.get_execution_plan()
    check_partition_plan(plan, native_time, battery_parallelism)
    Path("/state/continuous-execution-plan.json").write_text(plan)
    client = env.execute_async("continuous-battery-partition-v4")
    Path("/state/continuous-job.json").write_text(
        json.dumps({"job_id": str(client.get_job_id())})
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    run(args.config)
