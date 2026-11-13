"""Strict manifest and raw Kafka transport admission for the two-lane job."""

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pyflink.common import Row
from pyflink.datastream import DataStream, OutputTag, StreamExecutionEnvironment
from pyflink.datastream.functions import ProcessFunction, RuntimeContext
from pyflink.table import StreamTableEnvironment
from telemetry_reader import MAX_EVENT_BYTES, read_battery_event

from battery_gate import ADMITTED, Admitted, BatteryGate, BatteryScope
from m3_completion_evidence import array, digest, integer, mapping, require, text
from paced_source import receipt


@dataclass(frozen=True)
class TransportRecord:
    partition: int
    offset: int
    index: int
    key_sha256: str
    value_sha256: str


@dataclass(frozen=True)
class PartitionManifest:
    topic: str
    group: str
    ends: tuple[int, int]
    scope: BatteryScope
    records: tuple[TransportRecord, ...]

    @classmethod
    def read(cls, path: Path) -> "PartitionManifest":
        """Read a bounded plan; ends are reservations, not captured high offsets."""
        with path.open("rb") as handle:
            wire = handle.read(1_048_577)
        require(len(wire) <= 1_048_576)
        row = mapping(json.loads(wire, object_pairs_hook=unique_pairs))
        require(
            set(row)
            == {"profile", "topic", "bootstrap", "group", "ends", "scope", "records"}
        )
        require(row["profile"] == "m3-partition-input-v1")
        require(row["bootstrap"] == "kafka:9092")
        topic = text(row["topic"], r"m2\.m3-final-[a-z0-9-]+\.telemetry\.canonical\.v1")
        group = text(row["group"], r"[a-zA-Z0-9._-]{1,128}")
        ends = array(row["ends"])
        require(len(ends) == 2)
        limits = (integer(ends[0], 1, 64), integer(ends[1], 1, 64))
        scope_row = mapping(row["scope"])
        fields = (
            "dataset_run_id",
            "pipeline_version",
            "source_log_id",
            "timestamp_min",
            "timestamp_max",
        )
        require(set(scope_row) == set(fields))
        scope = BatteryScope(*(text(scope_row[key]) for key in fields))
        scope.validate()
        records: list[TransportRecord] = []
        for item in array(row["records"]):
            record = mapping(item)
            require(
                set(record)
                == {"partition", "offset", "index", "key_sha256", "value_sha256"}
            )
            partition = integer(record["partition"], 0, 1)
            records.append(
                TransportRecord(
                    partition,
                    integer(record["offset"], 0, limits[partition] - 1),
                    integer(record["index"], 0, sum(limits) - 1),
                    digest(record["key_sha256"]),
                    digest(record["value_sha256"]),
                )
            )
        require(len(records) == sum(limits))
        require({record.index for record in records} == set(range(sum(limits))))
        require(
            {(record.partition, record.offset) for record in records}
            == {
                (partition, offset)
                for partition in range(2)
                for offset in range(limits[partition])
            }
        )
        return cls(topic, group, limits, scope, tuple(records))


def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Refuse duplicate JSON keys before constructing the source configuration."""
    result: dict[str, object] = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


class PartitionAdmission(BatteryGate):
    def __init__(self, manifest: PartitionManifest, control: Path) -> None:
        super().__init__(manifest.scope)
        self.manifest, self.control = manifest, control

    def open(self, runtime_context: RuntimeContext) -> None:
        super().open(runtime_context)
        self.subtask = runtime_context.get_index_of_this_subtask()
        self.partition: int | None = None
        self.seen: set[tuple[int, int]] = set()
        self.byte_count = 0

    def process_element(  # type: ignore[override]
        self, value: Row, ctx: ProcessFunction.Context
    ) -> Iterator[Admitted | tuple[OutputTag, str]]:
        key, wire, topic, raw_partition, raw_offset = value
        require(
            isinstance(key, (bytes, bytearray)) and isinstance(wire, (bytes, bytearray))
        )
        key, wire = bytes(key), bytes(wire)
        require(len(wire) <= MAX_EVENT_BYTES and len(key) <= MAX_EVENT_BYTES)
        self.byte_count += len(key) + len(wire)
        require(self.byte_count <= 1_048_576)
        require(topic == self.manifest.topic)
        partition = integer(raw_partition, 0, 1)
        offset = integer(raw_offset, 0, self.manifest.ends[partition] - 1)
        require(self.partition is None or self.partition == partition)
        self.partition = partition
        require((partition, offset) not in self.seen)
        self.seen.add((partition, offset))
        planned = next(
            record
            for record in self.manifest.records
            if (record.partition, record.offset) == (partition, offset)
        )
        key_hash, value_hash = sha256(key).hexdigest(), sha256(wire).hexdigest()
        require(key_hash == planned.key_sha256 and value_hash == planned.value_sha256)
        event = read_battery_event(wire)
        require(key == event["vehicle_id"].encode("utf-8"))
        receipt(
            self.control / f"source-{partition}-{offset}.json",
            {
                "partition": partition,
                "offset": offset,
                "index": planned.index,
                "key_sha256": key_hash,
                "value_sha256": value_hash,
                "source_subtask": self.subtask,
                "worker_pid": os.getpid(),
            },
        )
        admitted = False
        for row in super().process_element((planned.index, wire), ctx):
            admitted = type(row[0]) is int
            receipt(self.control / f"gate-{planned.index}.json", {"admitted": admitted})
            yield row


def build_input(
    env: StreamExecutionEnvironment,
    tables: StreamTableEnvironment,
    manifest: PartitionManifest,
    control: Path,
) -> DataStream:
    """Build the raw metadata source with fixed, explicitly reserved offset ends."""
    tables.execute_sql(f"""
    CREATE TEMPORARY TABLE partition_input (
      record_key BYTES, payload BYTES,
      topic_name STRING METADATA FROM 'topic' VIRTUAL,
      partition_id INT METADATA FROM 'partition' VIRTUAL,
      offset_id BIGINT METADATA FROM 'offset' VIRTUAL
    ) WITH (
      'connector'='kafka', 'topic'='{manifest.topic}',
      'properties.bootstrap.servers'='kafka:9092',
      'properties.group.id'='{manifest.group}',
      'properties.enable.auto.commit'='false',
      'properties.auto.offset.reset'='none',
      'properties.commit.offsets.on.checkpoint'='false',
      'scan.parallelism'='2', 'scan.startup.mode'='specific-offsets',
      'scan.startup.specific-offsets'='partition:0,offset:0;partition:1,offset:0',
      'scan.bounded.mode'='specific-offsets',
      'scan.bounded.specific-offsets'='partition:0,offset:{manifest.ends[0]};partition:1,offset:{manifest.ends[1]}',
      'scan.topic-partition-discovery.interval'='0',
      'key.format'='raw', 'key.fields'='record_key',
      'value.format'='raw', 'value.fields-include'='EXCEPT_KEY'
    )
    """)
    raw = tables.to_data_stream(tables.from_path("partition_input"))
    return (
        raw.forward()
        .process(PartitionAdmission(manifest, control), output_type=ADMITTED)
        .name("PartitionAdmission")
        .set_parallelism(2)
        .uid("partition-admission-v1")
    )
