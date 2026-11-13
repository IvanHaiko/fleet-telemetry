"""Boundaries for the restricted F09 research view."""

import json
import runpy
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_gps_utc_keeps_integer_microseconds() -> None:
    namespace = runpy.run_path(str(ROOT / "scripts/prepare-f09-gps.py"))
    convert = namespace["gps_utc_text"]
    assert convert(1_755_776_400_000_001).endswith(".000001Z")
    assert convert(1_755_776_400_999_999).endswith(".999999Z")


def test_existing_research_output_refuses_before_reading_input(tmp_path: Path) -> None:
    namespace = runpy.run_path(str(ROOT / "scripts/prepare-f09-gps.py"))
    prepare = namespace["prepare"]
    marker = tmp_path / "preserved.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(ValueError, match="output_exists"):
        prepare(tmp_path / "missing.ulg", tmp_path)
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_map_keeps_selectable_id_and_uses_offline_geography() -> None:
    dashboard = json.loads(
        (ROOT / "runtime/flight_analytics/dashboards/fleet-f09.json").read_bytes()
    )
    panel = dashboard["panels"][1]
    sql = cast(str, panel["targets"][0]["rawSql"])
    assert "vehicle_id" in sql and "gps_utc" not in sql
    assert (
        "${__data.fields.vehicle_id}"
        in panel["fieldConfig"]["defaults"]["links"][0]["url"]
    )
    assert any(
        layer.get("config", {}).get("src") == "public/maps/countries.geojson"
        for layer in panel["options"]["layers"]
    )
    assert panel["options"]["basemap"]["config"]["url"].startswith("http://127.0.0.1:")


def test_battery_charts_keep_unknown_associations_null() -> None:
    dashboard = json.loads(
        (
            ROOT / "runtime/flight_analytics/dashboards/flight-f09-details.json"
        ).read_bytes()
    )
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    for panel_id in (5, 6, 7):
        panel = panels[panel_id]
        query = panel["targets"][0]["rawSql"]
        assert "m.status = 'matched'" in query
        assert "CAST(NULL AS Nullable(Float64))" in query
        assert "join_use_nulls=1" in query
        assert panel["fieldConfig"]["defaults"]["custom"]["spanNulls"] is False
    assert "GROUP BY m.status" in panels[8]["targets"][0]["rawSql"]
    assert "not battery sample time" in panels[1]["options"]["content"]
