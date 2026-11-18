"""Serve a retained run using its original Compose project and networks."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from runtime.recording.profile import Document


def original_project(folder: Path, entry: Document) -> str | None:
    project = entry.get("compose_project")
    if isinstance(project, str):
        return project
    # Older plans recorded the concrete container names during collection.
    evidence = sorted((folder / "evidence").glob("*/containers.json"))
    if evidence:
        for row in json.loads(evidence[-1].read_bytes()):
            name = row.get("container", "")
            if name.endswith("-archive-1"):
                return str(name.removesuffix("-archive-1"))
    return None


def list_runs(root: Path) -> list[Document]:
    rows = []
    for path in root.glob("*/ops.json"):
        try:
            entry = json.loads(path.read_bytes())
            reports = sorted(path.parent.glob("verify-*.json"))
            result = (
                json.loads(reports[-1].read_bytes()).get("status") if reports else None
            )
            rows.append(
                {
                    "run": path.parent.name,
                    "date": entry.get("declared_utc"),
                    "source": "fleet" if entry.get("fleet") else entry.get("source"),
                    "project": original_project(path.parent, entry),
                    "verified": result,
                }
            )
        except (ValueError, OSError):
            # A concurrent CLI run may still be writing its plan or evidence.
            rows.append(
                {
                    "run": path.parent.name,
                    "date": None,
                    "source": "unknown",
                    "project": None,
                    "verified": "Report unavailable",
                }
            )
    return sorted(rows, key=lambda item: str(item["date"] or ""), reverse=True)


def docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=40
    )
    if result.returncode:
        raise ValueError("Required Docker resources are unavailable.")
    return result.stdout.strip()


def main(action: str, run: str) -> Document:
    from runtime.recording.ops import load
    from runtime.recording.profile import PROJECT
    from runtime.recording.stored_view import VIEW_SERVICES, view

    profile, entry = load(run)
    if original_project(profile.out, entry) != PROJECT:
        raise ValueError("Stored project could not be confirmed.")
    active = set(
        docker(
            "ps",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
            "--format",
            '{{.Label "com.docker.compose.service"}}',
        ).splitlines()
    )
    if action == "close":
        marker = profile.out / "panel-view.active"
        if not marker.exists():
            raise ValueError("This view was not opened by the panel.")
        if active - VIEW_SERVICES:
            raise ValueError("Another session is using this project.")
        profile.require_active_scope()
        profile.docker(*profile.compose, "stop", *sorted(VIEW_SERVICES), timeout=180)
        marker.unlink()
        return {"status": "closed"}
    if action != "view" or active:
        raise ValueError(
            "The original project must be stopped before opening its history."
        )
    for volume in ("serving-data", "grafana-data", "archive-data"):
        docker("volume", "inspect", "--format", "{{.Name}}", f"{PROJECT}_{volume}")
    for network, variable in (
        ("default", "RECORDING_SUBNET"),
        ("live-source", "RECORDING_LIVE_SUBNET"),
    ):
        name = f"{PROJECT}_{network}"
        if name in docker("network", "ls", "--format", "{{.Name}}").splitlines():
            os.environ[variable] = docker(
                "network",
                "inspect",
                "--format",
                "{{(index .IPAM.Config 0).Subnet}}",
                name,
            )
    (profile.out / "panel-view.active").touch(exist_ok=False)
    return view(profile, entry)


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3 or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]{2,39}", sys.argv[2]
        ):
            raise ValueError("Invalid historical run.")
        print(json.dumps(main(sys.argv[1], sys.argv[2])))
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "failed", "category": str(error)[:180]}))
        sys.exit(1)
