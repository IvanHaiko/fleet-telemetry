"""Static dashboard contracts; SQL execution and rendered UI need runtime checks."""

import json
import re
from pathlib import Path
from typing import NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "runtime/flight_analytics/dashboards/recording-stream.json"
DATASOURCE = {
    "type": "grafana-clickhouse-datasource",
    "uid": "mvp-f09-clickhouse",
}


def _object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(dict[str, object], value)


def _array(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def _text(value: object) -> str:
    assert isinstance(value, str)
    return value


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        assert key not in result, f"Duplicate JSON key: {key}"
        result[key] = value
    return result


def _nonfinite(value: str) -> NoReturn:
    raise AssertionError(f"Nonfinite JSON constant: {value}")


def _dashboard() -> dict[str, object]:
    return _object(
        json.loads(
            DASHBOARD.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_nonfinite,
        )
    )


def _panels(dashboard: dict[str, object]) -> list[dict[str, object]]:
    return [_object(panel) for panel in _array(dashboard["panels"])]


def _targets(panel: dict[str, object]) -> list[dict[str, object]]:
    return [_object(target) for target in _array(panel.get("targets", []))]


def test_dashboard_scope_pins_and_nonoverlapping_layout() -> None:
    dashboard = _dashboard()
    assert dashboard["uid"] == "mvp-f09-stream"
    assert dashboard["refresh"] == "5s"
    assert dashboard["editable"] is False
    assert _object(dashboard["timepicker"])["hidden"] is True
    requirements = {
        _text(row["id"]): row["version"]
        for item in _array(dashboard["__requires"])
        for row in [_object(item)]
    }
    assert requirements["grafana"] == "13.2.4"
    assert requirements["grafana-clickhouse-datasource"] == "4.23.2"

    variables = _array(_object(dashboard["templating"])["list"])
    assert len(variables) == 1
    variable = _object(variables[0])
    assert variable["name"] == "database"
    assert variable["type"] == "constant"
    assert variable["hide"] == 2
    assert variable["skipUrlSync"] is True
    assert variable["multi"] is variable["includeAll"] is False
    database = _text(variable["query"])
    assert database == "f09_stream_mvp_20261111_001"
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", database)
    assert _object(variable["current"]) == {"text": database, "value": database}
    assert variable["options"] == [
        {"text": database, "value": database, "selected": True}
    ]

    occupied: set[tuple[int, int]] = set()
    identifiers: set[int] = set()
    for panel in _panels(dashboard):
        identifier = panel["id"]
        assert type(identifier) is int and identifier not in identifiers
        identifiers.add(identifier)
        position = _object(panel["gridPos"])
        assert set(position) == {"x", "y", "w", "h"}
        assert all(type(value) is int for value in position.values())
        x, y, width, height = (cast(int, position[key]) for key in ("x", "y", "w", "h"))
        assert 0 <= x < 24 and y >= 0 and 0 < width <= 24 and height > 0
        assert x + width <= 24
        cells = {(a, b) for a in range(x, x + width) for b in range(y, y + height)}
        assert not occupied.intersection(cells), panel["title"]
        occupied.update(cells)
        assert panel["type"] in {"text", "stat", "table", "xychart", "geomap"}
    assert identifiers


def test_queries_use_only_frozen_views_with_finite_read_only_budgets() -> None:
    budgets = {
        "max_execution_time": 10,
        "max_threads": 1,
        "max_memory_usage": 268_435_456,
        "max_rows_to_read": 50_000,
        "max_bytes_to_read": 64_000_000,
        "max_result_rows": 4096,
        "max_result_bytes": 4_194_304,
    }
    queries: list[str] = []
    for panel in _panels(_dashboard()):
        targets = _targets(panel)
        if panel["type"] == "text":
            assert not targets
            continue
        assert targets and panel["datasource"] == DATASOURCE
        references: set[str] = set()
        for target in targets:
            assert target["datasource"] == DATASOURCE
            reference = _text(target["refId"])
            assert reference not in references
            references.add(reference)
            assert target["editorType"] == "sql" and target["queryType"] == "table"
            query = _text(target["rawSql"])
            queries.append(query)
            assert query.startswith("SELECT ")
            assert not any(token in query for token in (";", "--", "/*", "$__"))
            assert not re.search(
                r"\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|SYSTEM|"
                r"UNION|JOIN|WITH|FORMAT|INTO|toDateTime|now|now64|"
                r"coalesce|ifNull|assumeNotNull|toFloat64OrZero)\b",
                query,
                re.IGNORECASE,
            )
            assert re.findall(r"\bFROM\s+(\S+)", query) in (
                ["${database}.measurements"],
                ["${database}.progress"],
            )
            assert re.findall(r"\$\{([^}]+)\}", query) == ["database"]
            limit = re.search(r"\bLIMIT ([1-9][0-9]*) SETTINGS ", query)
            assert limit and 1 <= int(limit[1]) <= 4096
            parts = query.split(" SETTINGS ")
            assert len(parts) == 2
            settings: dict[str, str] = {}
            for entry in parts[1].split(","):
                key, value = entry.split("=", 1)
                assert key not in settings
                settings[key] = value
            assert settings.pop("readonly") == "1"
            assert settings.pop("read_overflow_mode") == "'throw'"
            assert settings.pop("result_overflow_mode") == "'throw'"
            assert set(settings) == set(budgets)
            for setting, ceiling in budgets.items():
                assert re.fullmatch(r"[1-9][0-9]*", settings[setting])
                assert 0 < int(settings[setting]) <= ceiling

    assert any("uniqExact(event_id) AS logical_gps_count" in sql for sql in queries)
    progress = [sql for sql in queries if "FROM ${database}.progress" in sql]
    assert progress
    assert all(
        "ORDER BY written_ms DESC" in sql and "LIMIT 1 " in sql for sql in progress
    )
    assert any(
        sql.startswith("SELECT written_ms,status,input_next,output_count,expected ")
        for sql in progress
    )
    assert any("GROUP BY battery_status" in sql for sql in queries)
    assert any("GROUP BY land_status,vehicle_status_status" in sql for sql in queries)


def test_native_axes_unknowns_and_offline_route_preserve_recording_meaning() -> None:
    dashboard = _dashboard()
    panels = _panels(dashboard)
    explanation = " ".join(
        _text(_object(panel["options"])["content"])
        for panel in panels
        if panel["type"] == "text"
    ).lower()
    for phrase in (
        "historical recording",
        "paused, completed or stopped is not live device connectivity",
        "native boot seconds",
        "missing metrics remain **unknown**",
        "publication-time",
        "one-second age bound",
        "physical simultaneity",
    ):
        assert phrase in explanation

    xy_columns: set[str] = set()
    for panel in panels:
        if panel["type"] == "text":
            continue
        defaults = _object(_object(panel["fieldConfig"])["defaults"])
        assert defaults["noValue"] == "Unknown"
        assert not defaults.get("mappings")
        if panel["type"] != "xychart":
            continue
        assert panel["pluginVersion"] == "13.2.4"
        custom = _object(defaults["custom"])
        assert custom["show"] == "points" and custom["spanNulls"] is False
        options = _object(panel["options"])
        assert options["mapping"] == "auto" and options["series"] == [{}]
        overrides = _array(_object(panel["fieldConfig"])["overrides"])
        axis = _object(overrides[0])
        assert _object(axis["matcher"]) == {"id": "byName", "options": "native_seconds"}
        assert {"id": "unit", "value": "suffix:s"} in _array(axis["properties"])
        targets = _targets(panel)
        assert len(targets) == 1
        sql = _text(targets[0]["rawSql"])
        assert sql.startswith("SELECT native_seconds,")
        assert "ORDER BY native_seconds,event_id LIMIT 4096 " in sql
        assert " WHERE " not in sql, "Unknown chart samples must retain their native X"
        columns = sql.split(" FROM ", 1)[0].removeprefix("SELECT native_seconds,")
        xy_columns.update(columns.split(","))
    assert xy_columns == {
        "ground_speed_m_s",
        "altitude_msl_m",
        "voltage_v",
        "current_a",
        "remaining_fraction",
        "landed",
        "ground_contact",
        "maybe_landed",
        "arming_state",
        "nav_state",
        "failsafe",
        "battery_age_us/1000000.0 AS battery_age_s",
        "land_age_us/1000000.0 AS land_age_s",
        "vehicle_status_age_us/1000000.0 AS vehicle_status_age_s",
    }

    maps = [panel for panel in panels if panel["type"] == "geomap"]
    assert len(maps) == 1
    options = _object(maps[0]["options"])
    view = _object(options["view"])
    assert view["id"] == "fit" and view["allLayers"] is False
    # An inherited zoom default caps fit before maxZoom in the pinned renderer.
    assert view["zoom"] == view["maxZoom"] == 18
    assert "lat" not in view and "lon" not in view
    basemap = _object(options["basemap"])
    assert basemap["type"] == "xyz"
    assert _object(basemap["config"])["url"] == "http://127.0.0.1:1/{z}/{x}/{y}.png"
    layers = [_object(layer) for layer in _array(options["layers"])]
    assert [layer["type"] for layer in layers] == ["geojson", "markers", "markers"]
    assert view["layer"] == layers[1]["name"], "Fit the route, not global geography"
    assert _object(layers[0]["config"])["src"] == "public/maps/countries.geojson"
    queries = {
        _text(target["refId"]): _text(target["rawSql"]) for target in _targets(maps[0])
    }
    for layer in layers[1:]:
        assert layer["location"] == {
            "mode": "coords",
            "latitude": "latitude",
            "longitude": "longitude",
        }
        reference = _text(_object(layer["filterData"])["options"])
        sql = queries[reference]
        assert "latitude_deg AS latitude,longitude_deg AS longitude" in sql
        assert "latitude_deg IS NOT NULL AND longitude_deg IS NOT NULL" in sql
    assert "ORDER BY native_seconds DESC,event_id DESC LIMIT 1 " in queries["A"]
    assert "ORDER BY native_seconds,event_id LIMIT 4096 " in queries["B"]
    # The only absolute URL is the established disabled loopback tile endpoint.
    urls = re.findall(r'https?://[^"\s]+', json.dumps(dashboard))
    assert urls == ["http://127.0.0.1:1/{z}/{x}/{y}.png"]
