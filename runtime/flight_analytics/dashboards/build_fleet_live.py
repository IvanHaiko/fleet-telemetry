"""Write the fleet dashboard template (ADR-0060): `python -m ...build_fleet_live`.

The dashboard is generated so that every query carries the same reader
limits and the database placeholder appears exactly where `live_prepare`
replaces it. Vehicles are listed from SQL; nothing is configured per vehicle.
"""

from __future__ import annotations

import json
from pathlib import Path

DATABASE = "fleet_template_db"
SOURCE = {"type": "grafana-clickhouse-datasource", "uid": "mvp-f09-clickhouse"}
LIMITS = (
    " SETTINGS readonly=1,max_execution_time=10,max_threads=1,"
    "max_memory_usage=268435456,max_rows_to_read=50000,max_bytes_to_read=64000000,"
    "read_overflow_mode='throw',max_result_rows=4096,max_result_bytes=4194304,"
    "result_overflow_mode='throw'"
)
OUTPUT = Path(__file__).with_name("fleet-live.json")


def target(ref: str, sql: str, time_series: bool = False) -> dict[str, object]:
    return {
        "refId": ref,
        "datasource": SOURCE,
        "queryType": "timeseries" if time_series else "table",
        "editorType": "sql",
        "format": 0 if time_series else 1,
        "rawSql": sql + LIMITS,
    }


def panel(
    ident: int,
    title: str,
    kind: str,
    grid: tuple[int, int, int, int],
    targets: list[dict[str, object]],
    description: str,
    **extra: object,
) -> dict[str, object]:
    x, y, w, h = grid
    return {
        "id": ident,
        "title": title,
        "type": kind,
        "description": description,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": SOURCE,
        "targets": targets,
        "fieldConfig": {"defaults": {"noValue": "Unknown"}, "overrides": []},
        **extra,
    }


FLEET = (
    "SELECT label AS Vehicle, if(kind = 'ulog-replay', 'replay of recording', "
    "'live PX4') AS Source, connection AS Connection, "
    "ifNull(replay_status, '-') AS Player, "
    "round(source_receipt_age_ms / 1000, 1) AS `Receipt age (s)`, "
    "facts AS Positions, round(altitude_msl_m, 1) AS `Altitude MSL (m)`, "
    "round(ground_speed_m_s, 1) AS `Ground speed (m/s)`, "
    "round(voltage_v, 2) AS `Voltage (V)`, "
    "round(remaining_fraction * 100) AS `Battery (%)`, "
    "multiIf(armed IS NULL, 'unknown', armed = 1, 'armed', 'disarmed') AS Armed, "
    "ifNull(refusal, '') AS Refusal "
    "FROM ${database}.fleet_state ORDER BY system_id"
)
TRACKS = (
    "SELECT vehicle_label AS label, system_id, "
    "tupleElement(argMin(tuple(latitude_deg, longitude_deg), native_time_boot_ms), 1) "
    "AS latitude, "
    "tupleElement(argMin(tuple(latitude_deg, longitude_deg), native_time_boot_ms), 2) "
    "AS longitude "
    "FROM ${database}.points GROUP BY vehicle_label, system_id, "
    "intDiv(native_time_boot_ms, 1000) ORDER BY system_id LIMIT 4096"
)
LAST = (
    "SELECT label, system_id, latitude_deg AS latitude, longitude_deg AS longitude "
    "FROM ${database}.fleet_state WHERE latitude_deg IS NOT NULL"
)


def series(column: str, scale: str = "") -> str:
    # Eight vehicles times 512 receipt-time buckets fits the reader's row cap.
    # Include the right endpoint and keep the last sample, even if it is null.
    return (
        "SELECT fromUnixTimestamp64Milli(toInt64(max(received_unix_ms))) AS time, "
        "vehicle_label AS vehicle, "
        f"tupleElement(argMax(tuple({column}{scale}), "
        "tuple(received_unix_ms, input_offset)), 1) AS value "
        "FROM ${database}.points WHERE received_unix_ms BETWEEN ${__from} AND ${__to} "
        "GROUP BY system_id, vehicle_label, intDiv(received_unix_ms - ${__from}, "
        "intDiv(${__to} - ${__from}, 512) + 1) ORDER BY time, vehicle"
    )


def build() -> dict[str, object]:
    reader_note = (
        "**Fleet of virtual vehicles.** Each recorded ULog file plays as its own "
        "virtual PX4 and sends MAVLink to the same gateway a physical PX4 would "
        "use (ADR-0060). Rows marked *replay of recording* are recordings, not "
        "live aircraft. **Connection** is *observed* while that vehicle's "
        "heartbeat arrived in the last 3 s and the gateway and serving reports "
        "are current; *stale* when it falls silent (a paused player); *ended* "
        "when its file is over; *unknown* when the gateway or serving report is "
        "missing. A value the file does not contain stays Unknown; the player's "
        "own heartbeat never becomes a recorded state."
    )
    color = {
        "color": {"field": "system_id", "fixed": "orange"},
        "size": {"fixed": 3},
        "opacity": 0.7,
    }
    panels = [
        panel(
            1,
            "Fleet",
            "text",
            (0, 0, 24, 3),
            [],
            "What the dashboard shows.",
            options={"mode": "markdown", "content": reader_note},
        ),
        panel(
            2,
            "Vehicles",
            "table",
            (0, 3, 24, 7),
            [target("A", FLEET)],
            "One row per declared vehicle, from fleet_state.",
        ),
        panel(
            3,
            "Tracks and last positions",
            "geomap",
            (0, 10, 14, 14),
            [target("A", TRACKS), target("B", LAST)],
            "One point per native second per vehicle; the larger marker is the "
            "last position while observed. No external tiles.",
            options={
                "view": {
                    "id": "fit",
                    "allLayers": False,
                    "layer": "Tracks",
                    "lastOnly": False,
                    "padding": 10,
                    "maxZoom": 17,
                    "zoom": 15,
                },
                "basemap": {
                    "type": "xyz",
                    "name": "No external tiles",
                    "config": {"url": "http://127.0.0.1:1/{z}/{x}/{y}.png"},
                },
                "controls": {"showZoom": True, "mouseWheelZoom": True},
                "layers": [
                    {
                        "name": "Offline country boundaries",
                        "type": "geojson",
                        "tooltip": False,
                        "opacity": 1,
                        "config": {
                            "src": "public/maps/countries.geojson",
                            "rules": [],
                            "style": {
                                "color": {"fixed": "#5794F2"},
                                "opacity": 0.2,
                                "size": {"fixed": 2},
                            },
                        },
                    },
                    {
                        "type": "markers",
                        "name": "Tracks",
                        "filterData": {"id": "byRefId", "options": "A"},
                        "location": {
                            "mode": "coords",
                            "latitude": "latitude",
                            "longitude": "longitude",
                        },
                        "config": {"showLegend": False, "style": color},
                    },
                    {
                        "type": "markers",
                        "name": "Last position",
                        "filterData": {"id": "byRefId", "options": "B"},
                        "location": {
                            "mode": "coords",
                            "latitude": "latitude",
                            "longitude": "longitude",
                        },
                        "config": {
                            "showLegend": False,
                            "style": {
                                **color,
                                "size": {"fixed": 12},
                                "opacity": 1,
                                "text": {"field": "label", "mode": "field"},
                                "textConfig": {"fontSize": 12, "offsetY": -14},
                            },
                        },
                    },
                ],
            },
            fieldConfig={
                "defaults": {
                    "noValue": "Unknown",
                    "color": {"mode": "continuous-GrYlRd"},
                    "min": 2,
                    "max": 9,
                },
                "overrides": [],
            },
        ),
        panel(
            4,
            "Altitude MSL by vehicle",
            "timeseries",
            (14, 10, 10, 7),
            [target("A", series("altitude_msl_m"), time_series=True)],
            "Latest altitude per vehicle in each receipt-time bucket "
            "of the selected range.",
            fieldConfig={
                "defaults": {
                    "noValue": "Unknown",
                    "unit": "lengthm",
                    "displayName": "${__field.labels.vehicle}",
                },
                "overrides": [],
            },
        ),
        panel(
            5,
            "Battery remaining by vehicle",
            "timeseries",
            (14, 17, 10, 7),
            [target("A", series("remaining_fraction", " * 100"), time_series=True)],
            "Latest sample per vehicle in each receipt-time bucket of the selected "
            "range. An unknown battery reading leaves a gap.",
            fieldConfig={
                "defaults": {
                    "noValue": "Unknown",
                    "unit": "percent",
                    "min": 0,
                    "displayName": "${__field.labels.vehicle}",
                },
                "overrides": [],
            },
        ),
    ]
    return {
        "__requires": [
            {
                "type": "grafana",
                "id": "grafana",
                "name": "Grafana",
                "version": "13.2.4",
            },
            {
                "type": "datasource",
                "id": "grafana-clickhouse-datasource",
                "name": "ClickHouse",
                "version": "4.23.2",
            },
        ],
        "uid": "fleet-live",
        "title": "Fleet: recorded flights as virtual vehicles",
        "description": "Replay players over MAVLink (ADR-0060).",
        "schemaVersion": 39,
        "version": 1,
        "editable": False,
        "timezone": "utc",
        "tags": ["telemetry", "live", "fleet", "replay"],
        "refresh": "5s",
        "time": {"from": "now-15m", "to": "now"},
        "templating": {
            "list": [
                {
                    "name": "database",
                    "type": "constant",
                    "hide": 2,
                    "skipUrlSync": True,
                    "query": DATABASE,
                    "current": {"text": DATABASE, "value": DATABASE},
                    "options": [
                        {"text": DATABASE, "value": DATABASE, "selected": True}
                    ],
                    "multi": False,
                    "includeAll": False,
                }
            ]
        },
        "panels": panels,
    }


def main() -> None:
    text = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    OUTPUT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
