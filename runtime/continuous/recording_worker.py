"""Bounded F09 publication, independent input archival and archive-gated serving."""

import argparse
import base64
import fcntl
import json
import time
from pathlib import Path

from runtime.continuous.kafka import observation
from runtime.continuous.recording_archive import VerifiedInputs, archive
from runtime.continuous.recording_batch import AckCursorFault, ServingBatch
from runtime.continuous.recording_config import (
    MAX_BODY,
    MAX_DELIVERIES,
    Document,
    immutable,
    kafka_client,
    lifetime,
    load_inputs,
    require,
    sql_client,
    storage,
)
from runtime.continuous.recording_publish import publish
from telemetry.continuous_archive import durable_cursor
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded
from telemetry.recording_runtime import read_output

__all__ = [
    "VerifiedInputs",
    "archive",
    "MAX_BODY",
    "MAX_DELIVERIES",
    "Document",
    "immutable",
    "kafka_client",
    "lifetime",
    "load_inputs",
    "require",
    "sql_client",
    "storage",
    "publish",
]


def serve(config: Document, root: Path) -> None:
    kafka = kafka_client(config)
    source = object_value(object_value(config["sources"])["output"])
    topic = string_value(source["topic"])
    reader = storage(config, "reader")
    sql = sql_client(config)
    stopped, deadline = lifetime(config)
    consumer = kafka.consumer(string_value(config["run_id"]) + "-serve")
    path = root / "serving-cursor.json"
    state = (
        json_object(read_bounded(path, 65536))
        if path.exists()
        else {"next": dict.fromkeys(map(str, range(kafka.partitions)), 0)}
    )
    next_offsets = object_value(state["next"])
    require(
        set(next_offsets) == set(map(str, range(kafka.partitions))),
        "recording_serving_cursor",
    )
    consumer.assign(
        kafka.positions(topic, {p: integer_value(v) for p, v in next_offsets.items()})
    )
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    logical = 0
    last = 0.0
    gate: VerifiedInputs | None = None
    pending: Document | None = None
    batch = ServingBatch(next_offsets)
    # A test fault exists only when the configuration names one explicitly.
    write = (
        sql.write_facts
        if config.get("serving_fault") is None
        else AckCursorFault(config["serving_fault"], root).wrap(sql.write_facts, batch)
    )
    try:
        while not stopped() and time.monotonic() < deadline:
            # Archive may not yet have registered its immutable control evidence.
            if gate is None:
                if reader.lookup("stream-plan.json") is None:
                    time.sleep(0.1)
                    continue
                gate = VerifiedInputs(config, reader, root)
            gate.advance()
            idle = False
            if pending is None and not batch.full():
                # Gather already fetched outputs without waiting; an empty poll
                # flushes, so a batch adds no delay once serving has caught up.
                message = consumer.poll(0 if batch.outputs else 0.1)
                if message is None:
                    idle = True
                else:
                    pending = observation(message, source)
            if pending is not None and not batch.full():
                partition = integer_value(pending["partition"])
                offset = integer_value(pending["offset"])
                require(
                    0 <= partition < kafka.partitions
                    and offset == batch.expected(partition)
                    and offset < MAX_DELIVERIES * 2,
                    "recording_output_offset",
                )
                raw = base64.b64decode(
                    string_value(pending["value_b64"]), validate=True
                )
                output = read_output(raw)
                if gate.admit(output):
                    immutable(
                        outputs / f"p{partition:02d}-{offset:020d}.json",
                        json_line(pending),
                    )
                    batch.add(partition, offset, output)
                    pending = None
            # A pending output here waits for the archive; write what is verified.
            if batch.full() or idle or pending is not None:
                batch.flush(write, lambda: durable_cursor(path, state))
            now = time.monotonic()
            if now - last < 0.5:
                continue
            last = now
            # SQL, not this process's memory, is authoritative after restarts.
            logical = sql.logical_count()
            sql.progress("running", len(gate.rows), logical, len(gate.facts))
            durable_cursor(
                root / "serving-status.json",
                {
                    "input_archived": len(gate.rows),
                    "logical_facts": logical,
                    "outputs_next": next_offsets,
                    "written_ms": time.time_ns() // 1000000,
                },
            )
            producer_path = root / "producer-status.json"
            producer = (
                json_object(read_bounded(producer_path, 8192))
                if producer_path.exists()
                else {}
            )
            sql.source_progress(
                why(producer, _status(root / "archive-status.json"), len(gate.rows))
            )
            if (
                producer.get("status") == "completed"
                and len(gate.rows) == len(gate.wires)
                and pending is None
                and not batch.outputs
                and logical == len(gate.facts)
                and sql.logical_ids() == set(gate.facts)
            ):
                logical = len(gate.facts)
                highs = {
                    str(p.partition): consumer.get_watermark_offsets(
                        p, timeout=5, cached=False
                    )[1]
                    for p in kafka.positions(
                        topic, dict.fromkeys(map(str, range(kafka.partitions)), 0)
                    )
                }
                if highs == next_offsets:
                    sql.progress("completed", len(gate.rows), logical, len(gate.facts))
                    sql.source_progress(
                        why(producer, _status(root / "archive-status.json"), -1)
                        | {"explanation": "completed", "serving_taken": len(gate.rows)}
                    )
                    immutable(
                        root / "serving-complete.json",
                        json_line(
                            {
                                "input_deliveries": len(gate.rows),
                                "logical_facts": logical,
                                "output_offsets": next_offsets,
                                "status": "completed",
                            }
                        ),
                    )
                    return
        sql.progress(
            "stopped" if stopped() else "failed",
            len(gate.rows) if gate else 0,
            logical,
            len(gate.facts) if gate else 0,
        )
        require(stopped(), "recording_serving_deadline")
    finally:
        consumer.close()
        reader.close()


# Lag in deliveries before a stage is reported behind (health.LAG_WARN).
BEHIND = 100


def _status(path: Path) -> Document:
    try:
        return json_object(read_bounded(path, 8192))
    except (OSError, ValueError):
        return {}


def why(producer: Document, archive: Document, taken: int) -> Document:
    """The serving worker's own explanation of the last progress (ADR-0059).

    A stopped serving worker writes nothing; the panel then shows an old row,
    and `ops status` explains from outside (runtime/recording/stall.py).
    """
    state = producer.get("status")
    acknowledged = producer.get("acknowledged")
    archived = archive.get("input_next")
    ack = acknowledged if isinstance(acknowledged, int) else None
    prefix = archived if isinstance(archived, int) else None
    if prefix is not None and prefix > taken + BEHIND:
        explanation = "serving_behind"
    elif ack is not None and prefix is not None and ack > prefix + BEHIND:
        explanation = "archive_behind"
    elif state == "paused":
        explanation = "replay_paused"
    elif state == "completed":
        explanation = "replay_ended"
    elif state == "running":
        explanation = "advancing"
    else:
        explanation = "unknown"
    position = producer.get("position_native_us")
    declared = producer.get("declared")
    return {
        "explanation": explanation,
        "source_status": state if isinstance(state, str) else "unknown",
        "acknowledged": ack if ack is not None else -1,
        "declared": declared if isinstance(declared, int) else -1,
        "position_native_us": position if isinstance(position, int) else None,
        "archive_next": prefix,
        "serving_taken": taken,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("publish", "archive", "serve"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = json_object(read_bounded(args.config, 262144))
        require(
            config["format_version"] == "f09-recording-runtime-v1",
            "recording_runtime_profile",
        )
        root = Path(string_value(config["evidence"]))
        require(root.is_dir(), "recording_evidence_required")
        with (root / (args.role + ".lock")).open("a+b") as owner:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            {"publish": publish, "archive": archive, "serve": serve}[args.role](
                config, root
            )
    except Exception as error:
        # CLI trust boundary: upstream exceptions may embed private values.
        print(
            json.dumps(
                {
                    "role": args.role,
                    "status": "failed",
                    "category": type(error).__name__,
                }
            ),
            flush=True,
        )
        return 2
    print(json.dumps({"role": args.role, "status": "finished"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
