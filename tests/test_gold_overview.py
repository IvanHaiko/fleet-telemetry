"""Observable Gold overview behavior using the existing canonical example."""

import copy
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from runtime.clickhouse.transport import HttpConfig
from runtime.continuous import gold
from telemetry.conversion_contract import SEMANTIC_FIELDS
from telemetry.serving_projection import _semantic_json
from telemetry_reader import read_battery_event


def example() -> dict[str, object]:
    document = (Path(__file__).parents[1] / "docs/data-contracts.md").read_text(
        encoding="utf-8"
    )
    raw = (
        document.split("### Illustrative event", 1)[1]
        .split("```json", 1)[1]
        .split("```", 1)[0]
    )
    return cast(dict[str, object], json.loads(raw))


def fact(
    event: dict[str, object], offset: int, disposition: str = "eligible"
) -> dict[str, object]:
    admitted = read_battery_event(json.dumps(event).encode())
    semantic = {
        field: cast(dict[str, object], admitted)[field] for field in SEMANTIC_FIELDS
    }
    semantic["quality_flags"] = sorted(admitted["quality_flags"])
    encoded = _semantic_json(semantic)
    packet = {
        "format_version": "continuous-processing-v1",
        "run_id": admitted["delivery"]["dataset_run_id"],
        "kind": "event",
        "event": event,
        "disposition": disposition,
        "semantic_json": encoded,
        "semantic_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
    }
    return {
        "output_partition": 0,
        "output_offset": offset,
        "kind": "event",
        "fact_json": json.dumps(packet),
    }


def test_fleet_counts_deduplicate_retries_and_identical_measurements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = example()
    run = cast(dict[str, str], event["delivery"])["dataset_run_id"]
    first = fact(event, 0)
    replay = copy.deepcopy(event)
    replay["ingest_timestamp"] = "2026-01-01T12:01:00.000000Z"
    second = fact(replay, 1, "duplicate")
    rows = [first, first, second]

    def request(
        config: HttpConfig, sql: str, body: bytes, *, parameters: dict[str, str]
    ) -> bytes:
        assert parameters == {"database": "gold_test", "param_run": run}
        assert sql.startswith("SELECT DISTINCT") and body == b""
        return b"\n".join(json.dumps(row).encode() for row in rows)

    monkeypatch.setattr(gold, "_request", request)
    result = gold.query(HttpConfig(8123, "gold_test", "reader", "password"), run)
    assert result["status"] == "observed_unreconciled"
    assert result["unique_measurements"] == 1
    assert result["vehicles_with_measurements"] == 1
    assert result["event_dispositions"] == {"duplicate": 1, "eligible": 1}
    group = cast(list[dict[str, object]], result["groups"])[0]
    assert group["quality_flags"] == {"synthetic_time_anchor": 1}
    assert group["first_source_timestamp"] == event["source_timestamp"]


def test_conflicts_and_unsupported_data_refuse_entire_report() -> None:
    event = example()
    run = cast(dict[str, str], event["delivery"])["dataset_run_id"]
    first = fact(event, 0)
    changed = copy.deepcopy(event)
    cast(dict[str, object], changed["payload"])["voltage_v"] = 9.0
    with pytest.raises(ValueError, match="gold_identity_conflict"):
        gold.overview(run, [first, fact(changed, 1)])
    with pytest.raises(ValueError, match="gold_coordinate_conflict"):
        gold.overview(run, [first, fact(changed, 0)])
    packet = json.loads(cast(str, first["fact_json"]))
    packet["event"]["event_type"] = "telemetry.unknown"
    unknown = {**first, "fact_json": json.dumps(packet)}
    with pytest.raises(ValueError, match="gold_unsupported_event"):
        gold.overview(run, [unknown])
    with pytest.raises(ValueError, match="gold_fact_limit"):
        gold.overview(run, [first] * (gold.MAX_FACTS + 1))
