"""Live SITL archival and archive-gated serving on the recording profile.

The archive role stores the input topic in verified segments, as for F09,
with the live session declaration as its control object. The session ends
when the gateway's completion marker names the published count and the
archive reaches it. The serve role has no prepared reference: it recomputes
every fact from the archived input prefix with the same runtime the Flink
operator wraps, and admits a Flink output only if its fact equals the
recomputed one for the same input offset (ADR-0054).
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path

from runtime.continuous.kafka import observation
from runtime.continuous.live_archive_gate import SESSION_KEY, ArchivedFacts
from runtime.continuous.live_gateway import run as gateway
from runtime.continuous.live_sql import FleetSQL, LiveSQL
from runtime.continuous.recording_batch import ServingBatch
from runtime.continuous.recording_config import (
    Document,
    immutable,
    kafka_client,
    lifetime,
    require,
    sql_connection,
    storage,
)
from telemetry.archive_documents import digest
from telemetry.continuous_archive import SegmentedArchive, durable_cursor
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.fleet_runtime import (
    FLEET_PROFILE,
    runtime_session,
)
from telemetry.live_runtime import (
    read_output,
)
from telemetry.local_io import read_bounded


def _published(root: Path) -> int | None:
    """Final published count once the gateway has completed the session."""
    path = root / "gateway-complete.json"
    if not path.exists():
        return None
    marker = json_object(read_bounded(path, 8192))
    require(marker.get("status") == "completed", "live_gateway_marker")
    return integer_value(marker["published"])


def player_states(root: Path) -> dict[str, str]:
    """Each replay player's own status (ADR-0060), by vehicle."""
    states: dict[str, str] = {}
    folder = root / "players"
    if folder.is_dir():
        for path in sorted(folder.glob("*.status.json"))[:16]:
            row = json_object(read_bounded(path, 8192))
            states[string_value(row["vehicle"])] = string_value(row["status"])
    return states


def archive(config: Document, root: Path) -> None:
    kafka = kafka_client(config)
    source = object_value(object_value(config["sources"])["input"])
    topic = string_value(source["topic"])
    writer, reader = storage(config, "writer"), storage(config, "reader")
    plan = object_value(config["archive_plan"])
    cursor = root / "archive-cursor.json"
    consumer = kafka.consumer(string_value(config["run_id"]) + "-archive")
    stopped, deadline = lifetime(config)
    limit = integer_value(config["max_deliveries"])
    rows: list[Document] = []
    try:
        body = json_line(runtime_session(object_value(config["session"])))
        writer.create(SESSION_KEY, body)
        require(
            reader.read(SESSION_KEY, digest(body), len(body)) == body,
            "live_control_readback",
        )
        stream = SegmentedArchive(
            writer, reader, cursor, plan, initialize=not cursor.exists()
        )
        start = stream.next_offset(0)
        position = kafka.sdk.TopicPartition(topic, 0, start)
        low, high = consumer.get_watermark_offsets(position, timeout=5, cached=False)
        require(low <= start <= high <= limit, "live_archive_origin")
        consumer.assign([position])
        last = time.monotonic()

        def flush() -> None:
            if rows:
                require(kafka.describe(topic) == source, "live_archive_source_changed")
                taken = stream.publish(0, rows)
                require(taken > 0, "live_archive_no_progress")
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
                    and integer_value(row["offset"]) < limit,
                    "live_archive_offset",
                )
                rows.append(row)
            if len(rows) >= 64 or time.monotonic() - last >= 0.75:
                flush()
                last = time.monotonic()
            published = _published(root)
            if published is not None and stream.next_offset(0) == published:
                immutable(
                    root / "archive-complete.json",
                    json_line({"deliveries": published, "status": "completed"}),
                )
                return
        flush()
        require(stopped(), "live_archive_deadline")
    finally:
        consumer.close()
        writer.close()
        reader.close()


def serve(config: Document, root: Path) -> None:
    kafka = kafka_client(config)
    source = object_value(object_value(config["sources"])["output"])
    topic = string_value(source["topic"])
    reader = storage(config, "reader")

    fleet = object_value(config["session"]).get("profile") == FLEET_PROFILE
    sql = (FleetSQL if fleet else LiveSQL)(
        sql_connection(config, "sql_admin"), sql_connection(config, "sql_reader")
    )
    stopped, deadline = lifetime(config)
    consumer = kafka.consumer(string_value(config["run_id"]) + "-serve")
    path = root / "serving-cursor.json"
    state = (
        json_object(read_bounded(path, 65536))
        if path.exists()
        else {"next": dict.fromkeys(map(str, range(kafka.partitions)), 0)}
    )
    next_offsets = object_value(state["next"])
    consumer.assign(
        kafka.positions(topic, {p: integer_value(v) for p, v in next_offsets.items()})
    )
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    gate: ArchivedFacts | None = None
    pending: Document | None = None
    batch = ServingBatch(next_offsets)
    logical, last = 0, 0.0
    collected: object = None
    gateway_published = 0
    try:
        while not stopped() and time.monotonic() < deadline:
            if gate is None:
                # The plan is written after the session declaration.
                if reader.lookup("stream-plan.json") is None:
                    time.sleep(0.1)
                    continue
                gate = ArchivedFacts(config, reader, root)
            gate.advance()
            idle = False
            if pending is None and not batch.full():
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
                    and offset == batch.expected(partition),
                    "live_output_offset",
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
            if batch.full() or idle or pending is not None:
                batch.flush(sql.write_facts, lambda: durable_cursor(path, state))
            now = time.monotonic()
            if now - last < 0.5:
                continue
            last = now
            status_path = root / "gateway-status.json"
            if status_path.exists():
                status = json_object(read_bounded(status_path, 65536))
                if status.get("written_ms") != collected:
                    sql.collector(status)
                    if isinstance(sql, FleetSQL):
                        sql.vehicles(status, player_states(root))
                    collected = status.get("written_ms")
                    gateway_published = integer_value(status["published"])
            published = _published(root)
            logical = sql.logical_count()
            sql.progress("running", gate.archived, logical, gateway_published)
            durable_cursor(
                root / "serving-status.json",
                {
                    "input_archived": gate.archived,
                    "logical_facts": logical,
                    "outputs_next": next_offsets,
                    "written_ms": time.time_ns() // 1000000,
                },
            )
            if (
                published is not None
                and gate.archived == published
                and pending is None
                and not batch.outputs
                and logical == len(gate.identities)
                and sql.logical_ids() == gate.identities
            ):
                highs = {
                    str(p.partition): consumer.get_watermark_offsets(
                        p, timeout=5, cached=False
                    )[1]
                    for p in kafka.positions(
                        topic, dict.fromkeys(map(str, range(kafka.partitions)), 0)
                    )
                }
                if highs == next_offsets:
                    sql.progress("completed", gate.archived, logical, published)
                    immutable(
                        root / "serving-complete.json",
                        json_line(
                            {
                                "input_deliveries": gate.archived,
                                "logical_facts": logical,
                                "output_offsets": next_offsets,
                                "status": "completed",
                            }
                        ),
                    )
                    return
        sql.progress(
            "stopped" if stopped() else "failed",
            gate.archived if gate else 0,
            logical,
            0,
        )
        require(stopped(), "live_serving_deadline")
    finally:
        consumer.close()
        reader.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("gateway", "archive", "serve"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    import fcntl  # Linux worker image only; the gate itself is portable.

    try:
        config = json_object(read_bounded(args.config, 262144))
        require(
            config["format_version"] == "px4-live-runtime-v1", "live_runtime_profile"
        )
        root = Path(string_value(config["evidence"]))
        require(root.is_dir(), "live_evidence_required")
        with (root / (args.role + ".lock")).open("a+b") as owner:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.role == "gateway":
                outcome = gateway(config, root)
            else:
                {"archive": archive, "serve": serve}[args.role](config, root)
                outcome = "finished"
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
    print(json.dumps({"role": args.role, "status": outcome}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
