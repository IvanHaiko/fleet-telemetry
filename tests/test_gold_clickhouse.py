"""Optional isolated ClickHouse integration; never run against retained data."""

import json
import os
from pathlib import Path

import pytest
from test_gold_overview import example as battery_example
from test_gold_overview import fact as battery_fact
from test_gold_position import fact, source

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.gold import query
from telemetry.position_file import adapt


def test_position_gold_actual_clickhouse() -> None:
    port = os.getenv("GOLD_TEST_CLICKHOUSE_PORT")
    if port is None:
        pytest.skip("requires an isolated empty ClickHouse test container")
    config = HttpConfig(int(port), "default", "goldcheck", "localgoldcheck")
    event = adapt(
        source(),
        run_id="test-run",
        anchor="2026-01-01T00:00:00.000000Z",
        vehicles={1: "vehicle-1"},
    )[0]
    _request(
        config,
        Path("runtime/continuous/facts.sql").read_text(encoding="utf-8"),
        b"",
        write=True,
    )
    battery = battery_example()
    battery["delivery"] = {"dataset_run_id": "test-run", "replay_mode": "synthetic"}
    battery_row = battery_fact(battery, 2)
    rows = [fact(event), fact(event), fact(event, 1), battery_row]
    _request(
        config,
        "INSERT INTO continuous_facts_v1 FORMAT JSONEachRow",
        b"\n".join(json.dumps(row | {"run_id": "test-run"}).encode() for row in rows),
        write=True,
    )
    _request(
        config, "CREATE USER goldreader IDENTIFIED BY 'localreader'", b"", write=True
    )
    _request(
        config,
        "GRANT SELECT ON default.continuous_facts_v1 TO goldreader",
        b"",
        write=True,
    )
    reader = HttpConfig(int(port), "default", "goldreader", "localreader")
    result = query(reader, "test-run")
    assert result["status"] == "observed_unreconciled"
    assert result["unique_measurements"] == 2
    assert result["vehicles_with_measurements"] == 2
    assert result["event_dispositions"] == {"eligible": 3}
