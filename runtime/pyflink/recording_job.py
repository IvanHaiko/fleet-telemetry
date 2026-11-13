"""Submit the bounded recording Kafka -> managed association -> Kafka job."""

import argparse
import os
import re
from pathlib import Path
from typing import cast

from pyflink.common import Configuration, Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import (
    CheckpointingMode,
    ExternalizedCheckpointRetention,
    RuntimeExecutionMode,
    StreamExecutionEnvironment,
)
from pyflink.datastream.connectors.base import DeliveryGuarantee
from pyflink.datastream.connectors.kafka import (
    KafkaRecordSerializationSchema,
    KafkaSink,
)
from pyflink.table import StreamTableEnvironment
from telemetry.continuous_connection import flink_properties, source_options
from telemetry.conversion_contract import json_line, json_object
from telemetry.recording_runtime import MAX_SNAPSHOT_BYTES

from recording_operator import RecordingOperator, validate_config


def run(path: Path) -> None:
    """Submit only to the configured remote runtime; never start a service."""
    with path.open("rb") as handle:
        raw_config = handle.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw_config) > MAX_SNAPSHOT_BYTES:
        raise ValueError("recording_job_config_limit")
    config = json_object(raw_config)
    validate_config(config)
    job_path = Path(cast(str, config["job_file"]))
    plan_path = job_path.with_name(f"{config['run_id']}-execution-plan.json")
    checkpoint_path = Path("/state") / f"{config['run_id']}-checkpoints"
    if (
        Path("/state").is_symlink()
        or not Path("/state").is_dir()
        or checkpoint_path.exists()
        or checkpoint_path.is_symlink()
        or job_path.exists()
        or job_path.is_symlink()
        or plan_path.exists()
        or plan_path.is_symlink()
    ):
        raise ValueError("recording_job_scope_not_fresh")
    properties = flink_properties(config)
    properties["allow.auto.create.topics"] = "false"
    os.environ["_python_worker_execution_mode"] = "process"
    settings = Configuration()
    for key, value in {
        "python.execution-mode": "process",
        "execution.target": "remote",
        "execution.checkpointing.storage": "filesystem",
        "execution.checkpointing.dir": cast(str, config["checkpoint_directory"]),
        "restart-strategy.type": "fixed-delay",
        "restart-strategy.fixed-delay.attempts": "3",
        "restart-strategy.fixed-delay.delay": "3 s",
        "table.exec.resource.default-parallelism": "1",
        "table.exec.uid.generation": "ALWAYS",
        "table.exec.uid.format": "recording-<id>-<transformation>",
    }.items():
        settings.set_string(key, value)
    settings.set_integer("python.fn-execution.bundle.size", 1)
    settings.set_integer("python.fn-execution.bundle.time", 50)
    env = StreamExecutionEnvironment.get_execution_environment(settings)
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
    env.set_parallelism(1)
    env.set_max_parallelism(1)
    env.set_buffer_timeout(10)
    env.enable_checkpointing(10_000, CheckpointingMode.EXACTLY_ONCE)
    checkpoints = env.get_checkpoint_config()
    checkpoints.set_checkpoint_timeout(120_000)
    checkpoints.set_max_concurrent_checkpoints(1)
    checkpoints.set_externalized_checkpoint_retention(
        ExternalizedCheckpointRetention.RETAIN_ON_CANCELLATION
    )
    env.add_python_file(str(Path(__file__).with_name("recording_operator.py")))
    tables = StreamTableEnvironment.create(env)
    offsets = ";".join(f"partition:{partition},offset:0" for partition in range(18))
    tables.execute_sql(f"""
      CREATE TEMPORARY TABLE recording_input (
        record_key BYTES, payload BYTES,
        topic_name STRING METADATA FROM 'topic' VIRTUAL,
        partition_id INT METADATA FROM 'partition' VIRTUAL,
        offset_id BIGINT METADATA FROM 'offset' VIRTUAL
      ) WITH (
        'connector'='kafka', 'topic'='{config["input_topic"]}',
        {source_options(properties)},
        'properties.group.id'='{config["processing_group"]}',
        'properties.enable.auto.commit'='false',
        'properties.auto.offset.reset'='none',
        'properties.commit.offsets.on.checkpoint'='true',
        'scan.startup.mode'='specific-offsets',
        'scan.startup.specific-offsets'='{offsets}',
        'scan.parallelism'='1',
        'scan.topic-partition-discovery.interval'='0',
        'key.format'='raw', 'key.fields'='record_key', 'value.format'='raw',
        'value.fields-include'='EXCEPT_KEY'
      )
    """)
    source = tables.to_data_stream(tables.from_path("recording_input"))
    processed = (
        source.key_by(lambda row: "recording", key_type=Types.STRING())
        .process(RecordingOperator(config), output_type=Types.STRING())
        .set_parallelism(1)
        .name("recording-association")
        .uid("recording-association-v1")
    )
    serializer = (
        KafkaRecordSerializationSchema.builder()
        .set_topic(cast(str, config["output_topic"]))
        .set_value_serialization_schema(SimpleStringSchema())
        .build()
    )
    builder = KafkaSink.builder()
    for key, value in properties.items():
        if key != "allow.auto.create.topics":
            builder.set_property(key, value)
    sink = (
        builder.set_record_serializer(serializer)
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
        .set_property("acks", "all")
        .set_property("enable.idempotence", "true")
        .set_property("linger.ms", "0")
        .build()
    )
    processed.sink_to(sink).set_parallelism(1).name("recording-output").uid(
        "recording-output-v1"
    )
    plan = env.get_execution_plan()
    # Exclusive files avoid overwriting earlier evidence. An interrupted submit
    # can leave an empty job file; it is never a successful job-ID receipt.
    with job_path.open("x", encoding="utf-8") as receipt:
        with plan_path.open("x", encoding="utf-8") as handle:
            handle.write(plan)
        client = env.execute_async("bounded-recording-" + cast(str, config["run_id"]))
        job_id = str(client.get_job_id())
        if re.fullmatch(r"[0-9a-f]{32}", job_id) is None:
            raise ValueError("recording_job_id")
        receipt.write(json_line({"job_id": job_id}).decode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    run(args.config)
