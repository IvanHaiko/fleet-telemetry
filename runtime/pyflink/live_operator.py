"""One checkpointed receipt-ordered lane for a live session: SITL or a fleet."""

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
from telemetry.fleet_runtime import (
    MAX_FLEET_HEAD_BYTES,
    FleetRuntime,
    make_runtime,
    runtime_session,
)
from telemetry.live_event import event_bytes, event_key, read_event
from telemetry.live_runtime import (
    MAX_HEAD_BYTES,
    Document,
    LiveRuntime,
    make_output,
)
from telemetry.recording_output import MAX_EVENTS, _identifier, _integer, _topic_id

JOB_PROFILE = "px4-live-job-v1"


def validate_live_config(config: Document) -> None:
    """Check the protected job boundary before creating any Flink resources."""
    if config.get("format_version") != JOB_PROFILE:
        raise ValueError("live_job_version")
    for name in ("run_id", "input_topic", "output_topic", "processing_group"):
        _identifier(config.get(name))
    if config["input_topic"] == config["output_topic"]:
        raise ValueError("live_job_topics")
    source = object_value(config.get("source"))
    require_keys(source, {"cluster_id", "topic_id", "topic"})
    _identifier(source["cluster_id"])
    _identifier(source["topic"])
    _topic_id(source["topic_id"])
    if source["topic"] != config["input_topic"]:
        raise ValueError("live_job_source")
    session = runtime_session(object_value(config.get("session")))
    if session["run_id"] != config["run_id"]:
        raise ValueError("live_job_session")
    if config.get("session_sha256") != hashlib.sha256(json_line(session)).hexdigest():
        raise ValueError("live_job_session_hash")
    _integer(config.get("max_deliveries"), 1, MAX_EVENTS)
    if (
        config.get("checkpoint_directory")
        != f"file:///state/{config['run_id']}-checkpoints"
        or config.get("job_file") != f"/state/{config['run_id']}-job.json"
    ):
        raise ValueError("live_job_state_paths")
    from telemetry.continuous_connection import parse_connection

    connection = parse_connection(config.get("kafka_connection"))
    if connection is None or config.get("bootstrap") != ",".join(connection.endpoints):
        raise ValueError("live_job_connection")


class LiveOperator(KeyedProcessFunction):
    """Managed JSON head plus keyed signatures; the object is only a cache."""

    def __init__(self, config: Document) -> None:
        validate_live_config(config)
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
                        "session_sha256",
                        "max_deliveries",
                    )
                }
            )
        ).hexdigest()

    @property
    def head_limit(self) -> int:
        fleet = isinstance(self.runtime, FleetRuntime)
        return MAX_FLEET_HEAD_BYTES if fleet else MAX_HEAD_BYTES

    def open(self, runtime_context: RuntimeContext) -> None:
        self.state = runtime_context.get_state(
            ValueStateDescriptor("live-runtime-head-v1", Types.STRING())
        )
        self.signatures = runtime_context.get_map_state(
            MapStateDescriptor("live-signatures-v1", Types.STRING(), Types.STRING())
        )
        self.runtime: LiveRuntime | FleetRuntime | None = None
        metrics = runtime_context.get_metrics_group()
        self.counters = {
            name: metrics.counter("live_" + name)
            for name in ("accepted", "duplicate", "position", "rejected")
        }

    def _signature(self, identity: str) -> str | None:
        if self.signatures.contains(identity):
            return cast(str, self.signatures.get(identity))
        return None

    def _load(self) -> LiveRuntime | FleetRuntime:
        if self.runtime is not None:
            return self.runtime
        runtime = make_runtime(
            object_value(self.config["session"]),
            max_events=cast(int, self.config["max_deliveries"]),
        )
        stored = self.state.value()
        head = None
        if stored is not None:
            if len(stored) > self.head_limit:
                raise ValueError("live_operator_state_limit")
            row = json_object(stored.encode("utf-8"))
            require_keys(row, {"binding", "head"})
            if row["binding"] != self.binding:
                raise ValueError("live_operator_state_binding")
            head = object_value(row["head"])
        runtime.attach_managed_signatures(self._signature, self.signatures.put, head)
        self.runtime = runtime
        return runtime

    def process_element(
        self, value: object, ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        try:
            runtime = self._load()
            fields = cast(list[object], value)
            if len(fields) != 5:
                raise ValueError("live_operator_row")
            key, payload, topic, partition, offset = fields
            _integer(partition, 0, 0)
            _integer(offset, 0, cast(int, self.config["max_deliveries"]) - 1)
            if topic != self.config["input_topic"] or offset != runtime.deliveries:
                raise ValueError("live_operator_coordinate")
            if not isinstance(key, (bytes, bytearray)) or not isinstance(
                payload, (bytes, bytearray)
            ):
                raise ValueError("live_operator_bytes")
            event = read_event(bytes(payload))
            if bytes(payload) != event_bytes(event):
                raise ValueError("live_operator_event_encoding")
            if bytes(key) != event_key(event).encode("utf-8"):
                raise ValueError("live_operator_key")
            previous = runtime.signature_count
            fact = runtime.accept(event)
            packet = json_line(
                {"binding": self.binding, "head": runtime.checkpoint_head()}
            )
            if len(packet) > self.head_limit:
                raise ValueError("live_operator_state_limit")
            output = None
            if fact is not None:
                output = make_output(
                    fact,
                    {**object_value(self.config["source"]), "partition": 0},
                    cast(int, offset),
                    cast(str, self.config["session_sha256"]),
                )
            self.state.update(packet.decode("utf-8"))
            duplicate = runtime.signature_count == previous
            self.counters["duplicate" if duplicate else "accepted"].inc()
            if output is not None:
                self.counters["position"].inc()
                yield json_line(output).decode("utf-8").rstrip("\n")
        except (ValueError, TypeError, KeyError, OverflowError):
            self.counters["rejected"].inc()
            # Fixed text keeps Kafka and Python diagnostics free of payloads.
            raise ValueError("live_operator_refused") from None
