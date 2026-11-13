"""Bounded read-only fleet overview from continuous ClickHouse facts."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.conversion_contract import SEMANTIC_FIELDS, json_object
from telemetry.position_file import read_position
from telemetry.serving_projection import _semantic_json
from telemetry.serving_sink import SinkError
from telemetry_reader import EnvelopeError, read_battery_event

MAX_FACTS = 10000


def overview(run_id: str, rows: list[dict[str, object]]) -> dict[str, object]:
    """Summarize recognized measurements; refuse competing or unsupported facts."""
    if len(rows) > MAX_FACTS:
        raise ValueError("gold_fact_limit")
    coordinates: dict[tuple[int, int], tuple[str, str]] = {}
    identities: dict[str, str] = {}
    groups: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    dispositions: Counter[str] = Counter()
    for row in rows:
        partition, offset, kind, raw = (
            row.get(k)
            for k in ("output_partition", "output_offset", "kind", "fact_json")
        )
        if (
            type(partition) is not int
            or not 0 <= partition < 18
            or type(offset) is not int
            or offset < 0
            or type(kind) is not str
            or type(raw) is not str
        ):
            raise ValueError("gold_invalid_coordinate")
        coordinate = (partition, offset)
        previous = coordinates.get(coordinate)
        if previous is not None:
            if previous != (kind, raw):
                raise ValueError("gold_coordinate_conflict")
            continue
        coordinates[coordinate] = (kind, raw)
        fact = json_object(raw.encode("utf-8"))
        if (
            fact.get("format_version") != "continuous-processing-v1"
            or fact.get("run_id") != run_id
            or fact.get("kind") != kind
        ):
            raise ValueError("gold_fact_scope")
        if kind == "window":
            continue
        if kind != "event":
            raise ValueError("gold_unsupported_fact")
        candidate = fact.get("event")
        if not isinstance(candidate, dict):
            raise ValueError("gold_invalid_event")
        if candidate.get("event_type") == "telemetry.battery":
            event = cast(
                dict[str, object],
                read_battery_event(json.dumps(candidate, allow_nan=False).encode()),
            )
        elif candidate.get("event_type") == "telemetry.position":
            event = read_position(candidate)
        else:
            raise ValueError("gold_unsupported_event")
        if cast(dict[str, object], event["delivery"])["dataset_run_id"] != run_id:
            raise ValueError("gold_event_scope")
        semantic = {field: event[field] for field in SEMANTIC_FIELDS}
        semantic["quality_flags"] = sorted(cast(list[str], event["quality_flags"]))
        encoded = _semantic_json(semantic)
        if (
            fact.get("semantic_json") != encoded
            or fact.get("semantic_sha256")
            != hashlib.sha256(encoded.encode()).hexdigest()
        ):
            raise ValueError("gold_semantic_mismatch")
        disposition = fact.get("disposition")
        if disposition not in ("eligible", "late", "duplicate"):
            raise ValueError("gold_unsupported_disposition")
        dispositions[cast(str, disposition)] += 1
        event_id = cast(str, event["event_id"])
        if event_id in identities:
            if identities[event_id] != encoded:
                raise ValueError("gold_identity_conflict")
            continue
        identities[event_id] = encoded
        key = (
            cast(str, event["vehicle_id"]),
            cast(str, event["event_type"]),
            cast(str, event["source_type"]),
            cast(str, event["normalization_version"]),
            cast(str, cast(dict[str, object], event["source_time"])["timestamp_kind"]),
        )
        group = groups.setdefault(
            key,
            {
                "vehicle_id": key[0],
                "event_type": key[1],
                "source_type": key[2],
                "normalization_version": key[3],
                "timestamp_kind": key[4],
                "unique_measurements": 0,
                "first_source_timestamp": cast(str, event["source_timestamp"]),
                "last_source_timestamp": cast(str, event["source_timestamp"]),
                "quality_flags": {},
            },
        )
        group["unique_measurements"] = cast(int, group["unique_measurements"]) + 1
        group["first_source_timestamp"] = min(
            cast(str, group["first_source_timestamp"]),
            cast(str, event["source_timestamp"]),
        )
        group["last_source_timestamp"] = max(
            cast(str, group["last_source_timestamp"]),
            cast(str, event["source_timestamp"]),
        )
        flags = cast(dict[str, int], group["quality_flags"])
        for flag in cast(list[str], event["quality_flags"]):
            flags[flag] = flags.get(flag, 0) + 1
    return {
        "format_version": "gold-fleet-overview-v1",
        "run_id": run_id,
        "status": "observed_unreconciled",
        "unique_measurements": len(identities),
        "vehicles_with_measurements": len({key[0] for key in groups}),
        "event_dispositions": dict(sorted(dispositions.items())),
        "groups": [groups[key] for key in sorted(groups)],
    }


def query(config: HttpConfig, run_id: str) -> dict[str, object]:
    """Read one bounded run using a SELECT-only credential on loopback."""
    if not run_id or len(run_id) > 128:
        raise ValueError("gold_invalid_run")
    data = _request(
        config,
        "SELECT DISTINCT output_partition,output_offset,kind,fact_json "
        "FROM continuous_facts_v1 WHERE run_id={run:String} "
        "ORDER BY output_partition,output_offset,kind,fact_json LIMIT 10001 "
        "SETTINGS max_execution_time=10,max_threads=1,max_memory_usage=268435456,"
        "max_rows_to_read=100000,read_overflow_mode='throw',max_bytes_to_read=16777216 "
        "FORMAT JSONEachRow",
        b"",
        parameters={"database": config.database, "param_run": run_id},
    )
    return overview(run_id, [json_object(line) for line in data.splitlines()])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, required=True, help="existing continuous runtime config"
    )
    args = parser.parse_args()
    try:
        config = json_object(args.config.read_bytes())
        reader = cast(dict[str, str | int], config["reader"])
        run_id = config["run_id"]
        if not isinstance(run_id, str) or not isinstance(reader, dict):
            raise ValueError("gold_invalid_config")
        result = query(HttpConfig(**reader), run_id)  # type: ignore[arg-type]
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        UnicodeError,
        SinkError,
        EnvelopeError,
    ):
        print('{"error":"gold_report_refused"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
