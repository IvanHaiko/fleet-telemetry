"""Prepare private inputs for one live PX4 SITL session (ADR-0054).

Runs on the host before Compose starts and writes only into a new private
directory: the shared generated keys and passwords, the Compose environment
file and the live session plan. It starts no service, contacts no network and
never overwrites an existing directory. The gateway reuses the retained Linux
package directory of ADR-0045 read-only; nothing is downloaded.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from runtime.recording.prepare import (
    _RUN,
    PLUGIN,
    ROOT,
    _json,
    _write,
    bucket_name,
    database_name,
    private_scope,
    require,
    software,
)

PACKAGES = ROOT / ".local-discovery/sim-map-20261103/linux-packages"
DASHBOARD = ROOT / "runtime/flight_analytics/dashboards/live-sitl.json"
TEMPLATE_DATABASE = "live_sitl_template_db"
MAX_DELIVERIES = 50_000
MAX_SECONDS = 1800
RECEIPT_AGE_MS = 3000
UDP_PORT = 14560

type Document = dict[str, object]


def prepare_live(
    run: str,
    private: Path,
    packages: Path = PACKAGES,
    plugin: Path = PLUGIN,
    vehicle: str = "sitl-1",
) -> Document:
    require(_RUN.fullmatch(run), "live_run_id")
    require(not private.exists() and private.parent.is_dir(), "live_private_scope")
    require(
        any(packages.glob("pymavlink-2.4.50.dist-info"))
        and any(packages.glob("confluent_kafka-2.16.0.dist-info")),
        "live_packages_required",
    )
    require((plugin / "plugin.json").is_file(), "live_grafana_plugin_required")
    template = DASHBOARD.read_text(encoding="utf-8")
    # The constant variable stores the name in query, current and options.
    require(template.count(TEMPLATE_DATABASE) == 5, "live_dashboard_template")
    revision = software()
    plan: Document = {
        "format_version": "px4-live-run-v1",
        "run_id": run,
        "database": database_name(run),
        "bucket": bucket_name(run),
        # One declared boot session per run; a SITL restart needs a new run.
        "source": {
            "kind": "px4-sitl",
            "vehicle": vehicle,
            "boot_session": run + "-boot",
            "system": 1,
            "component": 1,
        },
        "max_receipt_age_ms": RECEIPT_AGE_MS,
        "max_deliveries": MAX_DELIVERIES,
        "duration_seconds": MAX_SECONDS,
        "udp_port": UDP_PORT,
        "software": revision,
    }
    previous = os.umask(0o077)
    try:
        private_scope(
            private,
            run,
            plugin,
            {"RECORDING_LIVE_PACKAGES": packages.resolve().as_posix()},
        )
        _json(private / "live-run.json", plan)
        _write(
            private / "dashboards/live-sitl.json",
            template.replace(TEMPLATE_DATABASE, database_name(run)),
        )
    finally:
        os.umask(previous)
    return {
        "run_id": run,
        "database": plan["database"],
        "bucket": plan["bucket"],
        "worktree_clean": revision["worktree_clean"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--packages", type=Path, default=PACKAGES)
    args = parser.parse_args(argv)
    try:
        summary = prepare_live(args.run_id, args.private, args.packages)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        category = str(error) if isinstance(error, ValueError) else type(error).__name__
        print(json.dumps({"status": "failed", "category": category[:64]}))
        return 2
    print(json.dumps({"status": "prepared", **summary}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
