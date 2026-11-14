"""One checkpointed association lane for the bounded recording runtime."""

import hashlib
from collections.abc import Iterator
from typing import cast

from pyflink.common import Types
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import MapStateDescriptor, ValueStateDescriptor
from telemetry.conversion_contract import (
    json_line,
    json_object,
    object_value,
    require_keys,
)
from telemetry.recording_runtime import (
    MAX_EVENTS,
    Document,
    RecordingRuntime,
    _identifier,
    _integer,
    make_output,
)
from telemetry.recording_stream import event_bytes, event_order, read_event

_MAX_HEAD_BYTES = 4 * 65_536


def validate_config(config: Document) -> None:
    """Check the protected job boundary before creating any Flink resources."""
    if config.get("format_version") != "f09-recording-job-v1":
        raise ValueError("recording_job_version")
    for name in ("run_id", "input_topic", "output_topic", "processing_group"):
        _identifier(config.get(name))
    if config["input_topic"] == config["output_topic"]:
        raise ValueError("recording_job_topics")
    source = object_value(config.get("source"))
    require_keys(source, {"cluster_id", "topic_id", "topic"})
    for value in source.values():
        _identifier(value)
    if source["topic"] != config["input_topic"]:
        raise ValueError("recording_job_source")
    context = object_value(config.get("context"))
    if context.get("run_id") != config["run_id"]:
        raise ValueError("recording_job_context")
    age = _integer(config.get("max_age_us"), 0, 60_000_000)
    RecordingRuntime(context, max_age_us=age)
    if config.get("context_sha256") != hashlib.sha256(json_line(context)).hexdigest():
        raise ValueError("recording_job_context_hash")
    _integer(config.get("deliveries"), 1, MAX_EVENTS)
    if (
        config.get("checkpoint_directory")
        != f"file:///state/{config['run_id']}-checkpoints"
        or config.get("job_file") != f"/state/{config['run_id']}-job.json"
    ):
        raise ValueError("recording_job_state_paths")
    # An explicit topology is required: the two-host mutual-TLS lab or the
    # private single-broker Compose network. The legacy implicit route is refused.
    from telemetry.continuous_connection import parse_connection

    connection = parse_connection(config.get("kafka_connection"))
    if connection is None or config.get("bootstrap") != ",".join(connection.endpoints):
        raise ValueError("recording_job_connection")


class RecordingOperator(KeyedProcessFunction):
    """Managed JSON state survives operator recreation at checkpoint boundaries.

    The Python object is only a cache for the single configured key. It is
    discarded by open(), rebuilt from a bounded head and keyed signatures on
    the first input. After seeding up to three predecessors, each delivery
    writes one head and at most one signature. Sink retries may repeat facts.
    """

    def __init__(self, config: Document) -> None:
        validate_config(config)
        # Detach caller-owned configuration, including nested masks.
        self.config = json_object(json_line(config))
        self.binding = hashlib.sha256(
            json_line(
                {
                    key: config[key]
                    for key in (
                        "run_id",
                        "input_topic",
                        "output_topic",
                        "processing_group",
                        "source",
                        "context_sha256",
                        "deliveries",
                        "max_age_us",
                    )
                }
            )
        ).hexdigest()

    def open(self, runtime_context: RuntimeContext) -> None:
        # Reuse the old descriptor to explicitly reject a v1 checkpoint.
        self.state = runtime_context.get_state(
            ValueStateDescriptor("recording-runtime-state-v1", Types.STRING())
        )
        self.runtime: RecordingRuntime | None = None
        self.signatures = runtime_context.get_map_state(
            MapStateDescriptor(
                "recording-signatures-v2", Types.STRING(), Types.STRING()
            )
        )
        metrics = runtime_context.get_metrics_group()
        self.counters = {
            name: metrics.counter("recording_" + name)
            for name in ("accepted", "duplicate", "late", "gps", "rejected")
        }

    def _signature(self, identity: str) -> str | None:
        if self.signatures.contains(identity):
            return cast(str, self.signatures.get(identity))
        return None

    def _load(self) -> RecordingRuntime:
        if self.runtime is not None:
            return self.runtime
        context = object_value(self.config["context"])
        age = cast(int, self.config["max_age_us"])
        runtime = RecordingRuntime(context, max_age_us=age)
        stored = self.state.value()
        head = None
        if stored is not None:
            # 3 events of at most 64 KiB plus positions, counters and binding.
            if len(stored) > _MAX_HEAD_BYTES:
                raise ValueError("recording_operator_state_limit")
            row = json_object(stored.encode("utf-8"))
            if "runtime" in row:
                raise ValueError("recording_operator_legacy_state")
            require_keys(row, {"binding", "head"})
            if row["binding"] != self.binding:
                raise ValueError("recording_operator_state_binding")
            head = object_value(row["head"])
        runtime.attach_managed_signatures(self._signature, self.signatures.put, head)
        deliveries = cast(int, self.config["deliveries"])
        _integer(runtime.deliveries, 0, deliveries)
        if runtime.deliveries == deliveries:
            runtime.finish()
        self.runtime = runtime
        return self.runtime

    def process_element(
        self,
        value: object,
        ctx: KeyedProcessFunction.Context,
    ) -> Iterator[str]:
        try:
            runtime = self._load()
            fields = cast(list[object], value)
            if len(fields) != 5:
                raise ValueError("recording_operator_row")
            key, payload, topic, partition, offset = fields
            _integer(partition, 0, 0)
            _integer(offset, 0, cast(int, self.config["deliveries"]) - 1)
            if topic != self.config["input_topic"] or offset != runtime.deliveries:
                raise ValueError("recording_operator_coordinate")
            if not isinstance(key, (bytes, bytearray)) or not isinstance(
                payload, (bytes, bytearray)
            ):
                raise ValueError("recording_operator_bytes")
            event = read_event(bytes(payload))
            if bytes(payload) != event_bytes(event):
                raise ValueError("recording_operator_event_encoding")
            if bytes(key) != cast(str, event["measurement_id"]).encode("utf-8"):
                raise ValueError("recording_operator_key")
            previous_count = runtime.signature_count
            fact = runtime.accept(event)
            if runtime.deliveries == self.config["deliveries"]:
                runtime.finish()
            packet = json_line(
                {"binding": self.binding, "head": runtime.checkpoint_head()}
            )
            if len(packet) > _MAX_HEAD_BYTES:
                raise ValueError("recording_operator_state_limit")
            output = None
            if fact is not None:
                output = make_output(
                    fact,
                    {**object_value(self.config["source"]), "partition": 0},
                    cast(int, offset),
                    cast(str, self.config["context_sha256"]),
                )
            self.state.update(packet.decode("utf-8"))
            duplicate = runtime.signature_count == previous_count
            self.counters["duplicate" if duplicate else "accepted"].inc()
            if (
                duplicate
                and runtime.order is not None
                and event_order(event) < runtime.order
            ):
                self.counters["late"].inc()
            if output is not None:
                self.counters["gps"].inc()
                yield json_line(output).decode("utf-8").rstrip("\n")
        except (ValueError, TypeError, KeyError, OverflowError):
            self.counters["rejected"].inc()
            # Fixed text prevents Kafka/Python diagnostics exposing payloads.
            raise ValueError("recording_operator_refused") from None
