"""One bounded live position interval: Kafka source receipts -> normalized facts."""

import argparse
import json
import re
from pathlib import Path
from typing import cast

from pyflink.common import Configuration, Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import (
    CheckpointingMode,
    RuntimeExecutionMode,
    StreamExecutionEnvironment,
)
from pyflink.datastream.connectors.base import DeliveryGuarantee
from pyflink.datastream.connectors.kafka import (
    KafkaRecordSerializationSchema,
    KafkaSink,
)
from pyflink.table import StreamTableEnvironment


def run(path: Path) -> None:
    config = cast(dict[str, object], json.loads(path.read_bytes()))
    for name in ("input_topic", "output_topic", "group"):
        if (
            not isinstance(config.get(name), str)
            or re.fullmatch(r"[a-z0-9.-]{1,128}", cast(str, config[name])) is None
        ):
            raise ValueError("position_job_identifier")
    end = config.get("deliveries")
    continuous = config.get("continuous", False)
    if type(continuous) is not bool:
        raise ValueError("position_job_mode")
    limit = 4096 if continuous else 32
    if type(end) is not int or not 1 <= end <= limit:
        raise ValueError("position_job_bound")
    bounded = (
        ""
        if continuous
        else (
            "'scan.bounded.mode'='specific-offsets',"
            f"'scan.bounded.specific-offsets'='partition:0,offset:{end}',"
        )
    )
    settings = Configuration()
    settings.set_string("python.fn-execution.bundle.size", "1")
    settings.set_string("python.fn-execution.bundle.time", "50")
    settings.set_string("execution.checkpointing.storage", "filesystem")
    settings.set_string(
        "execution.checkpointing.dir", "file:///state/live-position-checkpoints"
    )
    env = StreamExecutionEnvironment.get_execution_environment(settings)
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
    env.enable_checkpointing(10_000, CheckpointingMode.EXACTLY_ONCE)
    env.set_parallelism(1)
    env.set_buffer_timeout(10)
    tables = StreamTableEnvironment.create(env)
    tables.execute_sql(f"""
      CREATE TEMPORARY TABLE live_position_input (
        record_key BYTES, payload BYTES,
        partition_id INT METADATA FROM 'partition' VIRTUAL,
        offset_id BIGINT METADATA FROM 'offset' VIRTUAL
      ) WITH (
        'connector'='kafka', 'topic'='{config["input_topic"]}',
        'properties.bootstrap.servers'='kafka:9092',
        'properties.group.id'='{config["group"]}',
        'properties.enable.auto.commit'='false',
        'properties.auto.offset.reset'='none',
        'scan.startup.mode'='specific-offsets',
        'scan.startup.specific-offsets'='partition:0,offset:0',
        {bounded}
        'scan.topic-partition-discovery.interval'='0',
        'key.format'='raw', 'key.fields'='record_key',
        'value.format'='raw', 'value.fields-include'='EXCEPT_KEY'
      )
    """)

    def normalize(row: object) -> str:
        from telemetry.conversion_contract import json_line
        from telemetry.mavlink_position import make_fact

        fields = cast(list[object], row)
        fact = make_fact(
            cast(bytes, fields[1]),
            cast(bytes, fields[0]),
            cast(str, config["input_topic"]),
            cast(int, fields[2]),
            cast(int, fields[3]),
            offset_limit=end if continuous else 32,
        )
        event = cast(dict[str, object], fact["event"])
        if event["source_boot_session"] != config["source_boot_session"]:
            raise ValueError("position_job_source_session")
        return json_line(fact).decode().rstrip("\n")

    source = tables.to_data_stream(tables.from_path("live_position_input"))
    normalized = source.map(normalize, output_type=Types.STRING()).name(
        "normalize-live-native-position"
    )
    serializer = (
        KafkaRecordSerializationSchema.builder()
        .set_topic(cast(str, config["output_topic"]))
        .set_value_serialization_schema(SimpleStringSchema())
        .build()
    )
    sink = (
        KafkaSink.builder()
        .set_bootstrap_servers("kafka:9092")
        .set_record_serializer(serializer)
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
        .set_property("acks", "all")
        .set_property("enable.idempotence", "true")
        .set_property("linger.ms", "0")
        .build()
    )
    normalized.sink_to(sink).name("live-position-fact-output")
    env.execute(
        "continuous-live-px4-position" if continuous else "bounded-live-px4-position"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    run(args.config)
