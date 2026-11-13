"""Connect the live position reader to the existing local Grafana instance."""

import argparse
import base64
import http.client
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from telemetry.conversion_contract import (  # noqa: E402
    json_object,
    object_value,
    string_value,
)


def connect(evidence: Path, grafana_env: Path) -> None:
    settings = dict(
        line.split("=", 1)
        for line in grafana_env.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    password = settings["FLIGHT_GRAFANA_PASSWORD"].strip().strip('"').strip("'")
    credentials = json_object((evidence / "credentials.json").read_bytes())
    auth = "Basic " + base64.b64encode(f"flight_admin:{password}".encode()).decode()

    def request(
        method: str, path: str, value: dict[str, object] | None = None
    ) -> tuple[int, dict[str, object]]:
        client = http.client.HTTPConnection("127.0.0.1", 13002, timeout=30)
        try:
            client.request(
                method,
                path,
                body=None if value is None else json.dumps(value),
                headers={"Authorization": auth, "Content-Type": "application/json"},
            )
            response = client.getresponse()
            body = response.read(2_000_001)
            if len(body) > 2_000_000:
                raise ValueError("grafana_response_bound")
            if response.status not in (200, 201, 404):
                raise ValueError(f"grafana_request_status_{response.status}")
            return response.status, json_object(body)
        finally:
            client.close()

    status, existing = request("GET", "/api/datasources/uid/position-live")
    if status == 200 and (
        existing.get("type") != "grafana-clickhouse-datasource"
        or existing.get("name") != "Live PX4 SQL"
        or object_value(existing["jsonData"]).get("username") != "position_reader"
    ):
        raise ValueError("grafana_existing_datasource_scope")
    source: dict[str, object] = {
        "uid": "position-live",
        "name": "Live PX4 SQL",
        "type": "grafana-clickhouse-datasource",
        "access": "proxy",
        "isDefault": False,
        "editable": True,
        "jsonData": {
            "host": "host.docker.internal",
            "port": 28133,
            "protocol": "http",
            "username": "position_reader",
            "defaultDatabase": "position_stream",
            "dialTimeout": 3,
            "queryTimeout": 10,
        },
        "secureJsonData": {"password": string_value(credentials["ch_reader"])},
    }
    request(
        "POST" if status == 404 else "PUT",
        "/api/datasources" if status == 404 else "/api/datasources/uid/position-live",
        source,
    )
    request("POST", "/api/admin/provisioning/dashboards/reload")
    _, health = request("GET", "/api/datasources/uid/position-live/health")
    if health.get("status") != "OK":
        raise ValueError("grafana_live_datasource_health")
    _, dashboard = request("GET", "/api/dashboards/uid/live-position-stream")
    if (
        object_value(dashboard.get("dashboard", {})).get("uid")
        != "live-position-stream"
    ):
        raise ValueError("grafana_live_dashboard_missing")
    print("Live PX4 dashboard ready: http://127.0.0.1:13002/d/live-position-stream")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--grafana-env", type=Path, required=True)
    args = parser.parse_args()
    connect(args.evidence, args.grafana_env)
