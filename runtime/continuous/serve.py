"""Read-committed Kafka fact materialization with exact SQL acknowledgement."""

import argparse
import fcntl
import json
import signal
import time
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.kafka import Kafka
from telemetry.archive_documents import canonical, digest
from telemetry.continuous_archive import durable_cursor, object_row, require
from telemetry.serving_sink import SinkError


def request_with_retry(
    config: HttpConfig,
    sql: str,
    body: bytes,
    *,
    write: bool = False,
    parameters: dict[str, str] | None = None,
) -> bytes:
    """Retry identical bytes; progress still requires exact independent readback."""
    for attempt in range(4):
        try:
            return _request(config, sql, body, write=write, parameters=parameters)
        except SinkError as error:
            if (
                error.category not in {"sink_unavailable", "write_ambiguous"}
                or attempt == 3
            ):
                raise
            print(
                json.dumps(
                    {
                        "event": "continuous_serving_retry",
                        "attempt": attempt + 1,
                        "category": error.category,
                    }
                ),
                flush=True,
            )
            time.sleep(2**attempt)
    raise AssertionError("unreachable_retry")


def run(config_path: Path, state: Path, initialize: bool) -> None:
    config = object_row(json.loads(config_path.read_bytes()))
    source = object_row(config["output_source"])
    topic = cast(str, source["topic"])
    kafka = Kafka(
        cast(str, config["bootstrap"]),
        cast(str, source["cluster_id"]),
        config.get("kafka_connection"),
    )
    require(kafka.describe(topic) == source, "serving_source_identity")
    writer = HttpConfig(**cast(dict[str, str | int], config["writer"]))  # type: ignore[arg-type]
    reader = HttpConfig(**cast(dict[str, str | int], config["reader"]))  # type: ignore[arg-type]
    run_id = cast(str, config["run_id"])
    # run_id is supplied as a typed ClickHouse parameter, never interpolated.
    params = {"database": writer.database, "param_run": run_id}
    state.mkdir(mode=0o700, exist_ok=True)
    consumer = kafka.consumer(cast(str, config["serving_group"]))
    stopping = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    with (state / "owner.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = state / "cursor.json"
        binding = digest(canonical(source))
        if initialize:
            require(not path.exists(), "serving_scope_exists")
            durable_cursor(
                path,
                {
                    "format_version": "continuous-serving-cursor-v1",
                    "source_sha256": binding,
                    "next": {str(p): 0 for p in range(18)},
                },
            )
        require(
            path.is_file() and path.stat().st_size <= 65536, "serving_cursor_required"
        )
        cursor = object_row(json.loads(path.read_bytes()))
        require(
            cursor.get("format_version") == "continuous-serving-cursor-v1"
            and cursor.get("source_sha256") == binding,
            "serving_cursor_binding",
        )
        offsets = cast(dict[str, int], object_row(cursor["next"]))
        require(
            set(offsets) == {str(i) for i in range(18)}
            and all(type(v) is int and v >= 0 for v in offsets.values()),
            "serving_cursor_shape",
        )
        for position in consumer.committed(kafka.positions(topic, offsets), timeout=5):
            expected = offsets[str(position.partition)]
            low, high = consumer.get_watermark_offsets(
                position, timeout=5, cached=False
            )
            require(low <= expected <= high, "serving_retention_gap")
            if initialize:
                require(
                    low == high == expected == 0 and position.offset < 0,
                    "serving_initial_origin",
                )
            else:
                require(0 <= position.offset <= expected, "serving_progress_ahead")
            if position.offset != expected:
                kafka.commit(consumer, topic, position.partition, expected)
        consumer.assign(kafka.positions(topic, offsets))
        batch: list[dict[str, object]] = []
        last = time.monotonic()
        total = 0

        def flush() -> None:
            nonlocal total, last
            if not batch:
                return
            require(kafka.describe(topic) == source, "serving_source_identity")
            body = b"".join(canonical(row) for row in batch)
            require(len(body) <= 1_048_576, "serving_batch_limit")
            request_with_retry(
                writer,
                "INSERT INTO continuous_facts_v1 SETTINGS async_insert=0,"
                "insert_deduplicate=0 FORMAT JSONEachRow",
                body,
                write=True,
                parameters=params,
            )
            clauses = []
            for p in {cast(int, row["output_partition"]) for row in batch}:
                values = [
                    cast(int, row["output_offset"])
                    for row in batch
                    if row["output_partition"] == p
                ]
                clauses.append(
                    f"(output_partition={p} AND output_offset BETWEEN "
                    f"{min(values)} AND {max(values)})"
                )
            raw = request_with_retry(
                reader,
                "SELECT DISTINCT run_id,output_partition,output_offset,kind,fact_json "
                "FROM continuous_facts_v1 WHERE run_id={run:String} AND ("
                + " OR ".join(clauses)
                + ") SETTINGS max_execution_time=10,max_threads=1,"
                "max_memory_usage=268435456 FORMAT JSONEachRow",
                b"",
                parameters=params,
            )
            actual = [json.loads(line) for line in raw.splitlines()]
            require(
                sorted(map(canonical, actual)) == sorted(map(canonical, batch)),
                "serving_fact_readback",
            )
            for row in batch:
                partition_key = str(row["output_partition"])
                offsets[partition_key] = max(
                    offsets[partition_key], cast(int, row["output_offset"]) + 1
                )
            durable_cursor(path, cursor)
            for p in {cast(int, row["output_partition"]) for row in batch}:
                kafka.commit(consumer, topic, p, offsets[str(p)])
            total += len(batch)
            batch.clear()
            last = time.monotonic()
            print(
                json.dumps({"event": "continuous_serving", "verified_facts": total}),
                flush=True,
            )

        try:
            while not stopping:
                message = consumer.poll(0.1)
                if message is not None:
                    require(
                        message.error() is None and message.topic() == topic,
                        "serving_source_read_error",
                    )
                    wire = message.value()
                    require(
                        wire is not None and len(wire) <= 65536, "serving_fact_limit"
                    )
                    fact = object_row(json.loads(cast(bytes, wire)))
                    require(
                        fact.get("format_version") == "continuous-processing-v1"
                        and fact.get("run_id") == run_id
                        and fact.get("kind") in {"event", "invalid", "window"},
                        "serving_fact_scope",
                    )
                    batch.append(
                        {
                            "run_id": run_id,
                            "output_partition": message.partition(),
                            "output_offset": message.offset(),
                            "kind": fact["kind"],
                            "fact_json": cast(bytes, wire).decode("utf8"),
                        }
                    )
                if len(batch) >= 128 or time.monotonic() - last >= 1:
                    flush()
            flush()
        finally:
            consumer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    run(args.config, args.state, args.initialize)
