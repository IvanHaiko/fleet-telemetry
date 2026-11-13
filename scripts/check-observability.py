"""Bounded read-only collection and Grafana query check for an owned M6 profile.

Service lifecycle and faults remain parent-owned. No Docker socket or serving
credentials enter the collector. Evidence must be a fresh local directory.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import sys
import time
from pathlib import Path
from typing import cast
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_RESPONSE = 8 * 1024 * 1024
MAX_SERIES_RESPONSE = 64 * 1024 * 1024
# Two Flink targets at 20,000, serving at 5,000, plus scrape-generated series.
MAX_SOURCE_SERIES = 45100
FORBIDDEN = {
    "host",
    "job_id",
    "tm_id",
    "task_id",
    "operator_id",
    "task_attempt_id",
    "task_attempt_num",
    "topic",
    "split",
    "event_id",
    "vehicle_id",
    "dataset_run_id",
}
type Row = dict[str, object]


class CheckError(ValueError):
    """A fixed, non-sensitive admission or query failure reason."""


def require(condition: object, reason: str) -> None:
    if not condition:
        raise CheckError(reason)


def obj(value: object) -> Row:
    require(isinstance(value, dict), "object_required")
    return cast(Row, value)


def array(value: object) -> list[object]:
    require(isinstance(value, list), "array_required")
    return cast(list[object], value)


def save(folder: Path, name: str, value: object) -> None:
    with (folder / name).open("x", encoding="utf8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def http_json(
    url: str,
    deadline: float,
    *,
    body: Row | None = None,
    auth: str | None = None,
    max_bytes: int = MAX_RESPONSE,
) -> Row:
    remaining = deadline - time.monotonic()
    require(remaining > 0, "check_deadline")
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = auth
    request = Request(
        url,
        headers=headers,
        data=None if body is None else json.dumps(body, allow_nan=False).encode(),
    )
    with urlopen(request, timeout=min(5, remaining)) as response:
        raw = response.read(max_bytes + 1)
    require(len(raw) <= max_bytes, "response_limit")
    return obj(json.loads(raw))


def check(folder: Path, private: Path, start: int, end: int) -> None:
    require(0 < end - start <= 1800, "invalid_check_interval")
    folder.mkdir(exist_ok=False)
    deadline = time.monotonic() + 120
    config = obj(json.loads(private.read_bytes()))
    password = config.get("grafana")
    require(isinstance(password, str) and bool(password), "grafana_password_required")
    auth = (
        "Basic "
        + base64.b64encode(("maintainer:" + cast(str, password)).encode()).decode()
    )
    prometheus = "http://127.0.0.1:19090/api/v1/"
    grafana = "http://127.0.0.1:13000"
    targets = http_json(prometheus + "targets", deadline)
    save(folder, "targets.json", targets)
    expected = {
        ("flink", "jobmanager:9249"),
        ("flink", "taskmanager:9249"),
        ("serving", "serving:9363"),
        ("prometheus", "localhost:9090"),
    }
    actual = set()
    for value in array(obj(targets["data"])["activeTargets"]):
        target = obj(value)
        labels = obj(target["labels"])
        actual.add((labels["job"], labels["instance"]))
        require(
            target["health"] == "up" and target["lastError"] == "", "target_unhealthy"
        )
    require(actual == expected, "target_inventory")
    series = http_json(
        prometheus
        + "series?"
        + urlencode(
            {
                "match[]": '{job=~"flink|serving"}',
                "start": start,
                "end": end,
            }
        ),
        deadline,
        max_bytes=MAX_SERIES_RESPONSE,
    )
    save(folder, "series.json", series)
    label_names: set[str] = set()
    source_series = array(series["data"])
    for value in source_series:
        labels = obj(value)
        require(not (FORBIDDEN & labels.keys()), "identity_label_detected")
        require(
            not any("fleet_m3_final" in str(v) for v in labels.values()),
            "run_identity_label_detected",
        )
        label_names.update(labels)
    require(0 < len(source_series) <= MAX_SOURCE_SERIES, "series_limit")
    health = http_json(grafana + "/api/health", deadline, auth=auth)
    require(
        health["version"] == "13.2.4" and health["database"] == "ok", "grafana_version"
    )
    dashboard = obj(
        http_json(
            grafana + "/api/dashboards/uid/fleet-local-runtime", deadline, auth=auth
        )["dashboard"]
    )
    save(folder, "dashboard.json", dashboard)
    provisioned = obj(
        json.loads(
            (ROOT / "runtime/observability/dashboards/local-runtime.json").read_bytes()
        )
    )
    require(dashboard["panels"] == provisioned["panels"], "dashboard_not_provisioned")
    panels: list[Row] = []
    for value in array(dashboard["panels"]):
        panel = obj(value)
        if panel["type"] == "text":
            continue
        expression = obj(array(panel["targets"])[0])["expr"]
        query = http_json(
            prometheus
            + "query_range?"
            + urlencode(
                {
                    "query": expression,
                    "start": start,
                    "end": end,
                    "step": 2,
                }
            ),
            deadline,
        )
        require(query["status"] == "success", "promql_failure")
        save(folder, f"panel-{panel['id']}-prometheus.json", query)
        result = array(obj(query["data"])["result"])
        # No alerts in a healthy interval and no completed checkpoint in the
        # deliberately checkpoint-disabled online profile are valid absences.
        optional = panel["title"] in {
            "Active local alerts",
            "Checkpoint duration (positive samples only)",
        }
        require(optional or bool(result), "required_panel_empty")
        via_grafana = http_json(
            grafana + "/api/ds/query",
            deadline,
            auth=auth,
            body={
                "from": str(start * 1000),
                "to": str(end * 1000),
                "queries": [
                    {
                        "refId": "A",
                        "expr": expression,
                        "datasource": {"type": "prometheus", "uid": "fleet-prometheus"},
                        "intervalMs": 2000,
                        "maxDataPoints": 900,
                        "range": True,
                    }
                ],
            },
        )
        save(folder, f"panel-{panel['id']}-grafana.json", via_grafana)
        grafana_result = obj(obj(via_grafana["results"])["A"])
        require("error" not in grafana_result, "grafana_query_failed")
        frames = array(grafana_result.get("frames", []))
        points = 0
        for frame_value in frames:
            frame = obj(frame_value)
            fields = array(obj(frame["schema"])["fields"])
            columns = array(obj(frame["data"])["values"])
            for field, column in zip(fields, columns, strict=True):
                if obj(field).get("type") == "number":
                    points += sum(
                        1
                        for sample in array(column)
                        if type(sample) in (int, float)
                        and math.isfinite(cast(int | float, sample))
                    )
        require(optional or points > 0, "grafana_panel_empty")
        panels.append(
            {
                "title": panel["title"],
                "series": len(result),
                "grafana_frames": len(frames),
                "grafana_finite_points": points,
            }
        )
    save(
        folder,
        "complete.json",
        {
            "start_epoch_seconds": start,
            "end_epoch_seconds": end,
            "targets": len(actual),
            "source_series": len(source_series),
            "label_names": sorted(label_names),
            "panels": panels,
            "grafana_version": health["version"],
            "bounded_local_monitoring": True,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-config", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    options = parser.parse_args()
    try:
        check(options.evidence, options.private_config, options.start, options.end)
    except CheckError as error:
        print(
            json.dumps(
                {"event": "monitoring_check", "reason": str(error), "state": "failed"}
            ),
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError, KeyError, TimeoutError):
        print('{"event":"monitoring_check","state":"failed"}', file=sys.stderr)
        return 1
    print('{"event":"monitoring_check","state":"passed"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
