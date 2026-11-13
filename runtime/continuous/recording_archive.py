"""Bounded F09 publication, independent input archival and archive-gated serving."""

import base64
import time
from pathlib import Path

from runtime.continuous.kafka import observation
from runtime.continuous.recording_config import (
    MAX_BODY,
    Document,
    immutable,
    kafka_client,
    lifetime,
    load_inputs,
    require,
    storage,
)
from runtime.s3.archive_store import ArchiveStore
from telemetry.archive_documents import canonical, digest
from telemetry.continuous_archive import SegmentedArchive, durable_cursor, segment_rows
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded


def archive(config: Document, root: Path) -> None:
    _, context, _ = load_inputs(config)
    kafka = kafka_client(config)
    source = object_value(object_value(config["sources"])["input"])
    topic = string_value(source["topic"])
    writer, reader = storage(config, "writer"), storage(config, "reader")
    plan = object_value(config["archive_plan"])
    cursor = root / "archive-cursor.json"
    consumer = kafka.consumer(string_value(config["run_id"]) + "-archive")
    stopped, deadline = lifetime(config)
    expected = integer_value(config["deliveries"])
    rows: list[Document] = []
    try:
        controls = {
            "context.json": json_line(context),
            "bundle-manifest.json": read_bounded(
                Path(string_value(config["bundle"])) / "manifest.json", MAX_BODY
            ),
            "source-manifest.json": read_bounded(
                Path(string_value(config["source_manifest"])), MAX_BODY
            ),
            "reference.jsonl": read_bounded(
                Path(string_value(config["reference"])), MAX_BODY
            ),
        }
        for key, body in controls.items():
            writer.create(key, body)
            require(
                reader.read(key, digest(body), len(body)) == body,
                "recording_control_readback",
            )
        stream = SegmentedArchive(
            writer, reader, cursor, plan, initialize=not cursor.exists()
        )
        start = stream.next_offset(0)
        position = kafka.sdk.TopicPartition(topic, 0, start)
        low, high = consumer.get_watermark_offsets(position, timeout=5, cached=False)
        require(low <= start <= high <= expected, "recording_archive_origin")
        consumer.assign([position])
        last = time.monotonic()

        def flush() -> None:
            if rows:
                require(
                    kafka.describe(topic) == source, "recording_archive_source_changed"
                )
                taken = stream.publish(0, rows)
                require(taken > 0, "recording_archive_no_progress")
                del rows[:taken]
                kafka.commit(consumer, topic, 0, stream.next_offset(0))
            durable_cursor(
                root / "archive-status.json",
                {
                    "input_next": stream.next_offset(0),
                    "buffered": len(rows),
                    "written_ms": time.time_ns() // 1000000,
                },
            )

        while not stopped() and time.monotonic() < deadline:
            message = consumer.poll(0.1)
            if message is not None:
                row = observation(message, source)
                require(
                    row["partition"] == 0
                    and row["offset"] == stream.next_offset(0) + len(rows)
                    and integer_value(row["offset"]) < expected,
                    "recording_archive_offset",
                )
                rows.append(row)
            if len(rows) >= 64 or time.monotonic() - last >= 0.75:
                flush()
                last = time.monotonic()
            if stream.next_offset(0) == expected:
                immutable(
                    root / "archive-complete.json",
                    json_line({"deliveries": expected, "status": "completed"}),
                )
                return
        flush()
        require(stopped(), "recording_archive_deadline")
    finally:
        consumer.close()
        writer.close()
        reader.close()


class VerifiedInputs:
    """Reconstruct available remote receipts; local archive counters grant nothing."""

    def __init__(self, config: Document, reader: ArchiveStore, root: Path) -> None:
        self.config, self.reader = config, reader
        events, context, self.wires = load_inputs(config)
        self.keys = [
            string_value(json_object(wire)["measurement_id"]).encode()
            for wire in self.wires
        ]
        self.rows: list[Document] = []
        self.previous: str | None = None
        self.plan = object_value(config["archive_plan"])
        path = root / "archive-reader-origin.json"
        origin: Document = {
            "format_version": "continuous-archive-cursor-v1",
            "plan_sha256": digest(canonical(self.plan)),
            "partitions": {"0": {"next": 0, "start": 0, "receipt_sha256": None}},
        }
        immutable(path, canonical(origin))
        self.verifier = SegmentedArchive(reader, reader, path, self.plan)
        require(
            reader.read(
                "context.json", digest(json_line(context)), len(json_line(context))
            )
            == json_line(context),
            "recording_context_archive",
        )
        reference = reader.read(
            "reference.jsonl",
            "sha256:" + string_value(config["reference_sha256"]),
            integer_value(config["reference_bytes"]),
        )
        self.facts = {
            string_value(f["measurement_id"]): f
            for f in (json_object(line) for line in reference.splitlines())
        }
        require(
            len(self.facts)
            == sum(e["stream"] == "vehicle_gps_position:0" for e in events),
            "recording_reference_coverage",
        )
        self.first_offsets = {
            string_value(e["measurement_id"]): i
            for i, e in enumerate(events)
            if e["stream"] == "vehicle_gps_position:0"
        }

    def advance(self) -> None:
        while len(self.rows) < len(self.wires):
            checked = self.verifier.verify_receipt(0, len(self.rows))
            if checked is None:
                return
            receipt, body = checked
            require(
                receipt["previous_sha256"] == self.previous, "recording_archive_chain"
            )
            for row in segment_rows(body):
                offset = len(self.rows)
                require(offset < len(self.wires), "recording_archive_extra_input")
                require(
                    base64.b64decode(string_value(row["value_b64"]), validate=True)
                    == self.wires[offset]
                    and base64.b64decode(string_value(row["key_b64"]), validate=True)
                    == self.keys[offset]
                    and row["headers"] == [],
                    "recording_archive_input_content",
                )
                self.rows.append(row)
            self.previous = digest(canonical(receipt))

    def admit(self, output: Document) -> bool:
        source = {
            **object_value(object_value(self.config["sources"])["input"]),
            "partition": 0,
        }
        require(
            output["input_source"] == source
            and output["context_sha256"] == self.config["context_sha256"],
            "recording_output_scope",
        )
        fact = object_value(output["fact"])
        identity = string_value(fact["measurement_id"])
        require(
            self.facts.get(identity) == fact
            and self.first_offsets.get(identity) == output["input_offset"],
            "recording_output_content",
        )
        return integer_value(output["input_offset"]) < len(self.rows)
