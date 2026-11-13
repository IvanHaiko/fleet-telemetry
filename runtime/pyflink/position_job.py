"""Isolated simulation position Kafka -> Flink -> Kafka processing job."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import cast

from pyflink.common import Configuration, Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import CheckpointingMode, StreamExecutionEnvironment
from pyflink.datastream.connectors.base import DeliveryGuarantee
from pyflink.datastream.connectors.kafka import (
    KafkaRecordSerializationSchema,
    KafkaSink,
)
from pyflink.table import StreamTableEnvironment
from telemetry.continuous_connection import flink_properties, source_options


def run(path: Path) -> None:
    config = cast(dict[str, object], json.loads(path.read_bytes()))
    for name in ("run_id", "input_topic", "output_topic", "processing_group"):
        value = config.get(name)
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[a-zA-Z0-9._-]{1,128}", value) is None
        ):
            raise ValueError("position_config_identifier")
    ids = config.get("system_ids")
    if (
        not isinstance(ids, list)
        or not 1 <= len(ids) <= 10
        or any(type(i) is not int or not 1 <= i <= 255 for i in ids)
    ):
        raise ValueError("position_vehicle_scope")
    properties = flink_properties(config)
    settings = Configuration()
    settings.set_string("execution.checkpointing.storage", "filesystem")
    settings.set_string(
        "execution.checkpointing.dir", "file:///state/position-checkpoints"
    )
    settings.set_integer("python.fn-execution.bundle.size", 16)
    settings.set_integer("python.fn-execution.bundle.time", 50)
    env = StreamExecutionEnvironment.get_execution_environment(settings)
    env.set_parallelism(2)
    env.set_buffer_timeout(10)
    env.enable_checkpointing(10_000, CheckpointingMode.EXACTLY_ONCE)
    env.add_python_file(str(Path(__file__).with_name("position_live.py")))
    tables = StreamTableEnvironment.create(env)
    tables.execute_sql(f"""
        CREATE TEMPORARY TABLE position_input (payload BYTES) WITH (
          'connector'='kafka', 'topic'='{config["input_topic"]}',
          {source_options(properties)},
          'properties.group.id'='{config["processing_group"]}',
          'properties.enable.auto.commit'='false',
          'scan.startup.mode'='earliest-offset', 'format'='raw'
        )
    """)

    def validate(row: object) -> str:
        from position_live import PositionView

        body = cast(bytes, cast(list[object], row)[0])
        event = cast(dict[str, object], json.loads(body))
        system = event.get("system_id")
        if type(system) is not int or system not in ids:
            raise ValueError("position_vehicle_scope")
        PositionView({cast(int, system)}).accept(event, 0.0)
        return json.dumps(event, separators=(",", ":"), sort_keys=True)

    source = tables.to_data_stream(tables.from_path("position_input"))
    validated = source.map(validate, output_type=Types.STRING()).name(
        "validate-simulated-position"
    )
    serializer = (
        KafkaRecordSerializationSchema.builder()
        .set_topic(cast(str, config["output_topic"]))
        .set_value_serialization_schema(SimpleStringSchema())
        .build()
    )
    builder = KafkaSink.builder()
    for key, value in properties.items():
        builder.set_property(key, value)
    sink = (
        builder.set_record_serializer(serializer)
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
        .set_property("acks", "all")
        .set_property("enable.idempotence", "true")
        .set_property("linger.ms", "0")
        .build()
    )
    validated.sink_to(sink).name("position-live-output")
    env.execute("simulated-position-map")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    run(args.config)
