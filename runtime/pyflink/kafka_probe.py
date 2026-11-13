"""Read an explicitly bounded synthetic Kafka interval through the Table bridge."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from pyflink.common import Row, Types
from pyflink.datastream.functions import MapFunction
from pyflink.table import StreamTableEnvironment

from probe_support import collect_output, execution_environment


class MetadataAudit(MapFunction):
    def map(self, value: Row) -> str:
        """Expose source positions and byte hashes without logging raw payloads."""
        key: object = value[0]
        wire: object = value[1]
        topic: object = value[2]
        partition: object = value[3]
        offset: object = value[4]
        if (
            not isinstance(key, (bytes, bytearray))
            or not isinstance(wire, (bytes, bytearray))
            or not isinstance(topic, str)
            or type(partition) is not int
            or type(offset) is not int
            or len(wire) > 65536
        ):
            raise ValueError("unexpected_kafka_row")
        return json.dumps(
            {
                "topic": topic,
                "partition": partition,
                "offset": offset,
                "key_sha256": hashlib.sha256(key).hexdigest(),
                "value_sha256": hashlib.sha256(wire).hexdigest(),
            }
        )


def run(connector: Path, topic: str, end: int, scratch: Path) -> list[object]:
    """Use fixed partition 0 offsets, no auto-commit and no offset reset fallback."""
    if (
        re.fullmatch(r"m2\.m3-[a-z0-9-]{1,48}\.telemetry\.canonical\.v1", topic) is None
        or not 0 < end <= 32
    ):
        raise ValueError("invalid_bounded_probe_scope")
    env = execution_environment(scratch)
    env.add_python_file(str(Path(__file__).resolve()))
    env.add_jars(connector.resolve().as_uri())
    tables = StreamTableEnvironment.create(env)
    tables.execute_sql(f"""
        CREATE TEMPORARY TABLE probe_input (
            record_key BYTES, payload BYTES,
            topic_name STRING METADATA FROM 'topic' VIRTUAL,
            partition_id INT METADATA FROM 'partition' VIRTUAL,
            offset_id BIGINT METADATA FROM 'offset' VIRTUAL
        ) WITH (
            'connector' = 'kafka', 'topic' = '{topic}',
            'properties.bootstrap.servers' = '127.0.0.1:19092',
            'properties.group.id' = '{topic}.pyflink',
            'properties.enable.auto.commit' = 'false',
            'properties.auto.offset.reset' = 'none',
            'scan.startup.mode' = 'specific-offsets',
            'scan.startup.specific-offsets' = 'partition:0,offset:0',
            'scan.bounded.mode' = 'specific-offsets',
            'scan.bounded.specific-offsets' = 'partition:0,offset:{end}',
            'scan.topic-partition-discovery.interval' = '0',
            'key.format' = 'raw', 'key.fields' = 'record_key',
            'value.format' = 'raw', 'value.fields-include' = 'EXCEPT_KEY'
        )
    """)
    stream = tables.to_data_stream(tables.from_path("probe_input"))
    output = stream.map(MetadataAudit(), output_type=Types.STRING())
    return collect_output(output, end, "m3-kafka-connector-probe")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connector", type=Path, required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "status": "kafka_probe_completed",
                "rows": run(args.connector, args.topic, args.end, args.scratch),
            }
        )
    )


if __name__ == "__main__":
    main()
