"""Bounded F09 publication, independent input archival and archive-gated serving."""

import argparse
import base64
import fcntl
import json
import time
from pathlib import Path

from runtime.continuous.kafka import observation
from runtime.continuous.recording_archive import VerifiedInputs, archive
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
    try:
        while not stopped() and time.monotonic() < deadline:
            # Archive may not yet have registered its immutable control evidence.
            if gate is None:
                if reader.lookup("stream-plan.json") is None:
                    time.sleep(0.1)
                    continue
                gate = VerifiedInputs(config, reader, root)
            gate.advance()
            if pending is None:
                message = consumer.poll(0.1)
                if message is not None:
                    pending = observation(message, source)
            if pending is not None:
                partition = integer_value(pending["partition"])
                offset = integer_value(pending["offset"])
                require(
                    0 <= partition < kafka.partitions
                    and offset == next_offsets[str(partition)]
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
                    sql.write_facts([output])
                    next_offsets[str(partition)] = offset + 1
                    durable_cursor(path, state)
                    pending = None
            now = time.monotonic()
            if now - last >= 0.5:
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
                last = now
            producer_path = root / "producer-status.json"
            producer = (
                json_object(read_bounded(producer_path, 8192))
                if producer_path.exists()
                else {}
            )
            if (
                producer.get("status") == "completed"
                and len(gate.rows) == len(gate.wires)
                and pending is None
                and sql.logical_count() == len(gate.facts)
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
