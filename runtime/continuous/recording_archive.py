"""Bounded F09 publication, independent input archival and archive-gated serving."""

import base64
import time
from pathlib import Path
from typing import cast

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

# Archive objects are capped at 16 MiB; the complete F09 reference is 29.6 MB.
REFERENCE_PART_BYTES = 8 * 1024 * 1024
REFERENCE_INDEX = "reference-parts.json"
_REFERENCE_PROFILE = "recording-reference-parts-v1"


def reference_parts(
    body: bytes, part_bytes: int = REFERENCE_PART_BYTES
) -> tuple[bytes, dict[str, bytes]]:
    """Split complete reference lines into immutable objects under the cap.

    The split is deterministic, so a reader can rebuild the exact index from the
    reconstructed bytes. The index is evidence of layout, not of content: the
    configured whole-reference digest remains the authority.
    """
    require(
        0 < len(body) <= MAX_BODY and body.endswith(b"\n"), "recording_reference_body"
    )
    require(1 <= part_bytes <= REFERENCE_PART_BYTES, "recording_reference_part_size")
    parts: list[bytes] = []
    current = bytearray()
    for line in body.splitlines(keepends=True):
        require(len(line) <= part_bytes, "recording_reference_line")
        if len(current) + len(line) > part_bytes:
            parts.append(bytes(current))
            current.clear()
        current += line
    parts.append(bytes(current))
    objects = {f"reference-{i:03d}.jsonl": part for i, part in enumerate(parts)}
    index = canonical(
        {
            "format_version": _REFERENCE_PROFILE,
            "sha256": digest(body),
            "bytes": len(body),
            "parts": [
                {"key": key, "sha256": digest(part), "bytes": len(part)}
                for key, part in objects.items()
            ],
        }
    )
    return index, objects


def read_reference(
    reader: ArchiveStore,
    sha256: str,
    length: int,
    part_bytes: int = REFERENCE_PART_BYTES,
) -> bytes:
    """Rebuild the reference from verified parts and the configured digest."""
    raw = reader.lookup(REFERENCE_INDEX)
    require(raw is not None and len(raw) <= 65536, "recording_reference_index")
    index = json_object(cast(bytes, raw))
    parts = index.get("parts")
    require(
        index.get("format_version") == _REFERENCE_PROFILE
        and index.get("sha256") == "sha256:" + sha256
        and index.get("bytes") == length
        and isinstance(parts, list)
        and 0 < len(parts) <= MAX_BODY // part_bytes + 1,
        "recording_reference_index",
    )
    pieces: list[bytes] = []
    for position, entry in enumerate(cast(list[object], parts)):
        row = object_value(entry)
        require(
            row.get("key") == f"reference-{position:03d}.jsonl",
            "recording_reference_index",
        )
        pieces.append(
            reader.read(
                string_value(row["key"]),
                string_value(row["sha256"]),
                integer_value(row["bytes"]),
            )
        )
    body = b"".join(pieces)
    require(
        len(body) == length
        and digest(body) == "sha256:" + sha256
        and reference_parts(body, part_bytes)[0] == raw,
        "recording_reference_content",
    )
    return body


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
        }
        index, parts = reference_parts(
            read_bounded(Path(string_value(config["reference"])), MAX_BODY)
        )
        # The index is written last, so its presence implies every part exists.
        controls.update(parts)
        controls[REFERENCE_INDEX] = index
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
        reference = read_reference(
            reader,
            string_value(config["reference_sha256"]),
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
