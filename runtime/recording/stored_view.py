"""Serve a stored recording run's dashboard: storage, SQL and Grafana only.

Used by `ops view` (runtime/recording/ops.py). Grafana provisions the
dashboards of one run at a time; the current templates are rendered for the
stored run's database into `.local-discovery/recording-view-<run>/` and its
datasource is made able to read the run (runtime/continuous/recording_view.py).
Data is read where it is; nothing is copied, deleted or rewritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from runtime.recording import live_prepare
from runtime.recording import prepare as recording_prepare
from runtime.recording.ops_view import grafana_view
from runtime.recording.profile import (
    PROJECT,
    ROOT,
    Document,
    Profile,
    RunFailure,
    require,
)
from telemetry.recordings import recording_by_key

VIEW_SERVICES = {"archive", "serving", "grafana"}
DASHBOARDS = {"f09": "mvp-f09-stream", "live": "live-px4-sitl"}


def dashboard_uid(source: str) -> str:
    """Every registered recording shares the recording dashboard's uid."""
    return DASHBOARDS["live" if source == "live" else "f09"]


def render_dashboards(run_id: str, source: str, label: str | None = None) -> Path:
    """Render the current dashboard template for a stored run's database.

    The run's own rendered copy in its private directory stays untouched; the
    view copy lives in `.local-discovery/recording-view-<run>/dashboards/` and
    is replaced on every `view`, because it is derived from the template only.
    """
    live = source == "live"
    template = live_prepare.DASHBOARD if live else recording_prepare.DASHBOARD
    marker = (
        live_prepare.TEMPLATE_DATABASE if live else recording_prepare.TEMPLATE_DATABASE
    )
    text = template.read_text(encoding="utf-8")
    require(text.count(marker) == 5, "view_dashboard_template")
    target = ROOT / ".local-discovery" / f"recording-view-{run_id}" / "dashboards"
    target.mkdir(parents=True, exist_ok=True)
    database = recording_prepare.database_name(run_id)
    rendered = (
        text.replace(marker, database)
        if live
        else recording_prepare.render_dashboard(
            text, database, label or recording_by_key(source).label
        )
    )
    (target / template.name).write_text(rendered, encoding="utf-8", newline="\n")
    return target.resolve()


def view(run: Profile, plan: Document) -> Document:
    """Serve a stored run's dashboard: storage, SQL and Grafana only, no processing.

    Grafana provisions the dashboards of the run whose environment file
    started it, so one stored run is viewable at a time. Data is read where it
    is; nothing is copied. Refuses while any other part of a profile runs,
    because recreating SQL with another run's environment would disturb it.
    """
    containers = cast(dict[str, str], run.status()["containers"])
    busy = [
        name
        for name, state in containers.items()
        if state == "running"
        and name.removeprefix(PROJECT + "-").removesuffix("-1") not in VIEW_SERVICES
    ]
    require(not busy, "profile_busy")
    dashboards = {
        "RECORDING_DASHBOARDS": render_dashboards(
            run.run_id,
            str(plan["source"]),
            cast(str, plan["label"]) if plan.get("label") else None,
        ).as_posix()
    }
    run.docker(*run.compose, "up", "-d", "grafana", env=dashboards)
    # Provisioning misses file changes through a Windows bind mount; a fresh
    # Grafana container reads the rendered files at startup.
    run.docker(
        *run.compose,
        *"up -d --no-deps --force-recreate grafana".split(),
        env=dashboards,
    )

    def readable() -> Document | None:
        try:
            return run.worker("recording_view", timeout=120)
        except RunFailure:
            return None  # SQL may still be starting

    result = cast(Document, run.wait(readable, 120, "datasource_not_readable"))
    run.wait(lambda: grafana_view().get("database") == "ok", 120, "grafana_not_ready")
    run.log("view_ready", rekeyed=result["rekeyed"], points=result["points"])
    return {
        "run_id": run.run_id,
        "status": "ready",
        "dashboard": f"http://127.0.0.1:13003/d/{dashboard_uid(str(plan['source']))}",
        "rekeyed": result["rekeyed"],
        "points": result["points"],
    }
