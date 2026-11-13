"""Reconcile acknowledged source bytes, retained segments and query facts."""

import argparse
import base64
import json
import sqlite3
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.s3.archive_store import make_archive_store
from telemetry.archive_documents import canonical, digest
from telemetry.continuous_archive import (
    SegmentedArchive,
    object_row,
    require,
    segment_rows,
)
from telemetry.conversion_contract import SEMANTIC_FIELDS
from telemetry.serving_projection import _semantic_json
from telemetry_reference import epoch_milliseconds

METRICS = ("voltage_v", "current_a", "remaining_fraction")


def verify(config_path: Path, state: Path, ledger: Path, output: Path) -> None:
    require(not output.exists(), "verification_output_exists")
    config = object_row(json.loads(config_path.read_bytes()))
    db = sqlite3.connect(output.with_suffix(".sqlite"))
    db.execute(
        "CREATE TABLE expected (partition INTEGER, offset INTEGER, "
        "event_id TEXT, hash TEXT, PRIMARY KEY(partition,offset))"
    )
    db.execute(
        "CREATE TABLE seen (partition INTEGER, offset INTEGER, "
        "event_id TEXT, semantic TEXT, PRIMARY KEY(partition,offset))"
    )
    expected_count = 0
    with ledger.open(encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            db.execute(
                "INSERT INTO expected VALUES (?,?,?,?)",
                (row["partition"], row["offset"], row["event_id"], row["value_sha256"]),
            )
            expected_count += 1
    db.commit()
    storage = object_row(config["storage"])
    reader_store = make_archive_store(
        cast(str, storage["endpoint"]),
        "us-east-1",
        cast(str, storage["bucket"]),
        cast(str, storage["prefix"]),
        **cast(dict[str, str], storage["reader"]),
    )
    # The verifier only uses read methods; the supplied writer port is never invoked.
    archive = SegmentedArchive(
        reader_store,
        reader_store,
        state / "archive/cursor.json",
        object_row(config["archive_plan"]),
    )
    archived = segments = archive_bytes = 0
    try:
        for part in range(18):
            offset = 0
            previous: str | None = None
            while offset < archive.next_offset(part):
                found = archive.verify_receipt(part, offset)
                require(found is not None, "archive_receipt_missing")
                receipt, data = cast(tuple[dict[str, object], bytes], found)
                require(receipt["previous_sha256"] == previous, "archive_chain_broken")
                for row in segment_rows(data):
                    wire = base64.b64decode(cast(str, row["value_b64"]), validate=True)
                    event = json.loads(wire)
                    expected = db.execute(
                        "SELECT event_id,hash FROM expected "
                        "WHERE partition=? AND offset=?",
                        (part, row["offset"]),
                    ).fetchone()
                    require(
                        expected == (event["event_id"], sha256(wire).hexdigest()),
                        "archive_acknowledgement_mismatch",
                    )
                    archived += 1
                offset = cast(int, receipt["next"])
                previous = digest(canonical(receipt))
                segments += 1
                archive_bytes += len(data)
            require(
                previous == object_row(archive.positions[str(part)])["receipt_sha256"],
                "archive_cursor_chain_mismatch",
            )
    finally:
        reader_store.close()
    require(archived == expected_count, "archive_coverage_mismatch")
    reader = HttpConfig(**cast(dict[str, str | int], config["reader"]))  # type: ignore[arg-type]
    params = {"database": reader.database, "param_run": cast(str, config["run_id"])}
    windows: dict[tuple[str, int], dict[str, object]] = {}
    actual_windows: dict[tuple[str, int], dict[str, object]] = {}
    dispositions: Counter[str] = Counter()
    partition_watermarks: dict[int, int] = {}
    vehicle_partitions: dict[str, int] = {}
    facts = 0
    for part in range(18):
        after = -1
        while True:
            raw = _request(
                reader,
                "SELECT DISTINCT output_partition,output_offset,"
                "kind,fact_json FROM continuous_facts_v1 WHERE run_id={run:String} "
                f"AND output_partition={part} AND output_offset>{after} "
                "ORDER BY output_offset LIMIT 128 SETTINGS max_execution_time=10,"
                "max_memory_usage=268435456 FORMAT JSONEachRow",
                b"",
                parameters=params,
            )
            if not raw:
                break
            for fact_line in raw.splitlines():
                row = json.loads(fact_line)
                require(row["output_offset"] > after, "serving_output_conflict")
                after = row["output_offset"]
                fact = json.loads(row["fact_json"])
                facts += 1
                require(fact["run_id"] == config["run_id"], "serving_scope_mismatch")
                if fact["kind"] == "window":
                    key = (fact["vehicle_id"], fact["start_ms"])
                    require(key not in actual_windows, "duplicate_window_fact")
                    actual_windows[key] = fact
                    continue
                require(fact["kind"] == "event", "unexpected_invalid_fact")
                event, coordinate = fact["event"], fact["source"]
                vehicle, partition = event["vehicle_id"], coordinate["partition"]
                require(
                    vehicle_partitions.setdefault(vehicle, partition) == partition,
                    "serving_vehicle_partition_conflict",
                )
                meaning = {key: event[key] for key in SEMANTIC_FIELDS}
                meaning["quality_flags"] = sorted(event["quality_flags"])
                require(
                    fact["semantic_json"] == _semantic_json(meaning),
                    "serving_semantic_content_mismatch",
                )
                expected = db.execute(
                    "SELECT event_id,hash FROM expected WHERE partition=? AND offset=?",
                    (coordinate["partition"], coordinate["offset"]),
                ).fetchone()
                require(
                    expected
                    == (event["event_id"], sha256(canonical(event)).hexdigest()),
                    "serving_source_bytes_mismatch",
                )
                require(
                    all(
                        coordinate[k] == v
                        for k, v in object_row(config["source"]).items()
                    ),
                    "serving_source_identity_mismatch",
                )
                db.execute(
                    "INSERT INTO seen VALUES (?,?,?,?)",
                    (
                        coordinate["partition"],
                        coordinate["offset"],
                        event["event_id"],
                        fact["semantic_sha256"],
                    ),
                )
                require(
                    sha256(fact["semantic_json"].encode()).hexdigest()
                    == fact["semantic_sha256"],
                    "serving_semantic_hash_mismatch",
                )
                kind = fact["disposition"]
                require(
                    kind in {"eligible", "late", "duplicate"}, "semantic_conflict_fact"
                )
                dispositions[kind] += 1
                watermark = fact["watermark_ms"]
                partition_watermarks[partition] = max(
                    partition_watermarks.get(partition, -(2**63)), watermark
                )
                start = epoch_milliseconds(event["source_timestamp"]) // 10000 * 10000
                if kind in {"eligible", "late"}:
                    require(
                        (watermark >= start + 9999) == (kind == "late"),
                        "incorrect_late_disposition",
                    )
                if kind != "eligible":
                    continue
                key = (event["vehicle_id"], start)
                window = windows.setdefault(
                    key,
                    {"unique_events": 0, "measures": {m: [0, "0"] for m in METRICS}},
                )
                window["unique_events"] = cast(int, window["unique_events"]) + 1
                measures = cast(dict[str, list[int | str]], window["measures"])
                for metric in METRICS:
                    value = event["payload"][metric]
                    if value is not None:
                        measures[metric] = [
                            cast(int, measures[metric][0]) + 1,
                            str(Fraction(measures[metric][1]) + Fraction(str(value))),
                        ]
    db.commit()
    seen = db.execute("SELECT count(*) FROM seen").fetchone()[0]
    require(seen == expected_count, "serving_delivery_loss")
    require(
        db.execute(
            "SELECT event_id FROM seen GROUP BY event_id "
            "HAVING count(DISTINCT semantic)>1 LIMIT 1"
        ).fetchone()
        is None,
        "persistent_semantic_conflict",
    )
    for key, fact in actual_windows.items():
        require(
            key in windows
            and fact["unique_events"] == windows[key]["unique_events"]
            and fact["measures"] == windows[key]["measures"],
            "window_reference_mismatch",
        )
    for key in windows:
        if key[1] + 9999 <= partition_watermarks[vehicle_partitions[key[0]]]:
            require(key in actual_windows, "closed_window_missing")
    unique = db.execute("SELECT count(DISTINCT event_id) FROM seen").fetchone()[0]
    report = {
        "acknowledged_deliveries": expected_count,
        "archived_deliveries": archived,
        "query_delivery_facts": seen,
        "unique_measurements": unique,
        "archive_segments": segments,
        "archive_bytes": archive_bytes,
        "processing_facts": facts,
        "closed_windows": len(actual_windows),
        "open_windows": len(windows) - len(actual_windows),
        "dispositions": dict(dispositions),
        "exact_window_sums_verified": True,
    }
    output.write_bytes(canonical(report))
    db.close()
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.config, args.state, args.ledger, args.output)
