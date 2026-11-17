"""Make the Grafana datasource of one stored recording run able to read it.

Runs in a short-lived worker container in the storage network namespace,
started by `ops view` (runtime/recording/ops.py). Every run's datasource
carries that run's generated reader password, while ClickHouse holds one
shared Grafana identity. The module reads the run's `points` view as that
identity; only if ClickHouse refuses the password does it point the identity
at this run through the bootstrap account (the same statements a fresh
initialization runs), then reads again. No table, row or grant is removed.

Output holds a status, whether the identity was re-keyed and a row count.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.recording_initialize import (
    GRAFANA_USER,
    SQL_PORT,
    grafana_identity,
)
from telemetry.conversion_contract import json_object, string_value
from telemetry.local_io import read_bounded
from telemetry.serving_sink import SinkError

type Document = dict[str, object]


def _count(config: HttpConfig, database: str) -> int:
    body = _request(config, f"SELECT count() FROM {database}.points", b"")
    return int(body.decode().strip())


def view(private: Path) -> Document:
    live = (private / "live-run.json").exists()
    plan = json_object(
        read_bounded(private / ("live-run.json" if live else "run.json"), 65536)
    )
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    database = string_value(plan["database"])
    grafana = HttpConfig(
        SQL_PORT, database, GRAFANA_USER, string_value(secrets["grafana_reader"]), 15
    )
    rekeyed = False
    try:
        rows = _count(grafana, database)
    except SinkError as refusal:
        if refusal.category != "permission_denied":
            raise
        bootstrap = HttpConfig(
            SQL_PORT, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
        )
        grafana_identity(bootstrap, database, string_value(secrets["grafana_reader"]))
        rekeyed = True
        rows = _count(grafana, database)
    return {
        "status": "ok",
        "source": "live" if live else "f09",
        "rekeyed": rekeyed,
        "points": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, default=Path("/private"))
    parser.add_argument("--evidence", type=Path, default=Path("/evidence"))
    args = parser.parse_args(argv)
    try:
        document = view(args.private)
    except SinkError as error:
        print(json.dumps({"status": "failed", "category": error.category}))
        return 2
    except Exception as error:
        # Trust boundary: client exceptions may embed credentials or paths.
        print(json.dumps({"status": "failed", "category": type(error).__name__}))
        return 2
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
