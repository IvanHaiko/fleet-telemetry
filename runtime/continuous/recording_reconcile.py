"""Independent post-run reconciliation of one recording SQL scope.

Compares the SHA-256 set of SQL `fact_json` values with the run's reference
lines, and reports physical rows, logical identities, conflicting content,
association counts and, for the original scope, output-topic records and the
rows written for the batch of a serving test fault. It prints counts and
digests only: no coordinates, measurement values or identifiers. It runs in the
worker container with the bootstrap SQL account and changes nothing.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.recording_batch import FAULT_MARKER
from runtime.continuous.recording_config import MAX_BODY, require
from telemetry.conversion_contract import (
    integer_value,
    json_object,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded

type Document = dict[str, object]
_DATABASE = re.compile(r"[a-z0-9_]{1,64}", re.ASCII)


def reconcile(private: Path, evidence: Path, database: str | None) -> Document:
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    run = json_object(read_bounded(private / "run.json", 65536))
    original = string_value(run["database"])
    scope = original if database is None else database
    require(
        _DATABASE.fullmatch(scope) is not None
        and (scope == original or scope.startswith(original + "_rebuild_")),
        "recording_reconcile_scope",
    )
    sql = HttpConfig(
        8123, scope, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
    )

    def rows(query: str) -> list[list[object]]:
        body = _request(sql, query + " FORMAT JSONCompactEachRow", b"")
        return [json.loads(line) for line in body.splitlines()]

    def one(query: str) -> object:
        return rows(query)[0][0]

    lines = read_bounded(Path(string_value(run["reference"])), MAX_BODY).splitlines()
    reference = {hashlib.sha256(line).hexdigest() for line in lines}
    hashes = {
        str(row[0])
        for row in rows(
            f"SELECT DISTINCT lower(hex(SHA256(fact_json))) FROM {scope}.facts"
        )
    }
    result: Document = {
        "database": scope,
        "reference_lines": len(lines),
        "reference_unique_hashes": len(reference),
        "sql_distinct_fact_hashes": len(hashes),
        "fact_hash_sets_equal": hashes == reference,
        "fact_hash_set_sha256": hashlib.sha256(
            "\n".join(sorted(hashes)).encode()
        ).hexdigest(),
        "physical_rows": one(f"SELECT count() FROM {scope}.facts"),
        "distinct_event_ids": one(f"SELECT uniqExact(event_id) FROM {scope}.facts"),
        "distinct_full_rows_view": one(f"SELECT count() FROM {scope}.measurements"),
        "max_rows_per_event": one(
            f"SELECT max(c) FROM (SELECT count() c FROM {scope}.facts "
            "GROUP BY event_id)"
        ),
        "events_with_physical_repeats": one(
            f"SELECT count() FROM (SELECT count() c FROM {scope}.facts "
            "GROUP BY event_id HAVING c > 1)"
        ),
        "conflicting_events": one(
            f"SELECT count() FROM (SELECT event_id FROM {scope}.facts "
            "GROUP BY event_id HAVING uniqExact(fact_json) > 1)"
        ),
        "progress_last": rows(
            f"SELECT status, input_next, output_count, expected FROM {scope}.progress "
            "ORDER BY written_ms DESC, input_next DESC, output_count DESC LIMIT 1"
        )[0],
        "association_counts": {
            name: rows(
                f"SELECT {name}_status, count() FROM {scope}.points "
                "GROUP BY 1 ORDER BY 1"
            )
            for name in ("battery", "land", "vehicle_status")
        },
    }
    result["zero_logical_repeats"] = (
        result["distinct_event_ids"] == result["distinct_full_rows_view"] == len(lines)
        and result["conflicting_events"] == 0
    )
    if scope != original:
        return result
    result["gps_input_offsets"] = [
        integer_value(row[0])
        for row in rows(
            f"SELECT DISTINCT input_offset FROM {scope}.facts ORDER BY input_offset"
        )
    ]
    state = evidence / string_value(run["run_id"]) / "state"
    marker = state / FAULT_MARKER
    if marker.exists():
        fault = json_object(read_bounded(marker, 65536))
        listed_offsets = cast(list[object], fault["input_offsets"])
        offsets = [integer_value(value) for value in listed_offsets]
        require(offsets and len(offsets) <= 64, "recording_reconcile_fault")
        listed = ",".join(str(value) for value in offsets)
        counts = rows(
            f"SELECT count(), uniqExact(fact_json) FROM {scope}.facts "
            f"WHERE input_offset IN ({listed}) GROUP BY input_offset"
        )
        result["fault_batch"] = {
            "members": len(offsets),
            "members_in_sql": len(counts),
            "min_physical_rows_per_member": min(integer_value(c[0]) for c in counts),
            "max_distinct_content_per_member": max(integer_value(c[1]) for c in counts),
            "cursor_before": object_value(fault["cursor"]),
        }
    return result


def output_repeats(evidence: Path, run_id: str, gps: list[int]) -> Document:
    """Count output-topic records and the GPS input ranges emitted more than once.

    After a checkpoint restore, the at-least-once sink re-emits the facts of
    the deliveries between the restored source position and the failure. Each
    range lists the first and last input offset, in GPS order, and its facts.
    """
    from runtime.continuous.recording_config import kafka_client

    config = json_object(
        read_bounded(evidence / run_id / "config" / "serve.json", 262144)
    )
    kafka = kafka_client(config)
    topic = string_value(
        object_value(object_value(config["sources"])["output"])["topic"]
    )
    consumer = kafka.consumer(run_id + "-reconcile")
    emitted: dict[int, int] = {}
    total = 0
    try:
        positions = kafka.positions(
            topic, dict.fromkeys(map(str, range(kafka.partitions)), 0)
        )
        highs = {
            p.partition: consumer.get_watermark_offsets(p, timeout=5, cached=False)[1]
            for p in positions
        }
        total = sum(highs.values())
        consumer.assign(positions)
        seen = 0
        idle = 0
        while seen < total and idle < 100:
            message = consumer.poll(0.2)
            if message is None:
                idle += 1
                continue
            require(message.error() is None, "recording_reconcile_output")
            raw = message.value() or b""
            require(len(raw) <= 65536, "recording_reconcile_output")
            offset = integer_value(json_object(raw)["input_offset"])
            emitted[offset] = emitted.get(offset, 0) + 1
            seen += 1
        require(seen == total, "recording_reconcile_output_incomplete")
    finally:
        consumer.close()
    require(set(emitted) == set(gps), "recording_reconcile_output_coverage")
    ranges: list[list[int]] = []
    last = -2
    for index, offset in enumerate(gps):
        if emitted[offset] < 2:
            continue
        if ranges and last == index - 1:
            ranges[-1][1] = offset
            ranges[-1][2] += 1
        else:
            ranges.append([offset, offset, 1])
        last = index
    return {"output_topic_records": total, "repeated_output_ranges": ranges}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--database")
    parser.add_argument(
        "--restore-positions",
        default="",
        help="comma-separated source offsets; reports the first GPS offset at each",
    )
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.private, args.evidence, args.database)
        if args.database is None:
            run = json_object(read_bounded(args.private / "run.json", 65536))
            gps = cast(list[int], result.pop("gps_input_offsets"))
            result.update(
                output_repeats(args.evidence, string_value(run["run_id"]), gps)
            )
            result["restore_positions"] = {
                text: next((o for o in gps if o >= int(text)), None)
                for text in args.restore_positions.split(",")
                if text.isdigit()
            }
    except Exception as error:
        print(json.dumps({"status": "failed", "category": type(error).__name__}))
        return 2
    print(json.dumps({"status": "reconciled", **result}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
