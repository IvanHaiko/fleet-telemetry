"""Prepare private inputs for one single-machine F09 recording run.

Runs on the host before Compose starts. It writes only into a new private
directory: generated passwords and S3 keys, the SeaweedFS identity file, the
Compose environment file, a per-run dashboard and a source manifest. It starts
no service, contacts no network and never overwrites an existing directory.
Container paths assume the repository is mounted read-only at /workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "runtime/flight_analytics/dashboards/recording-stream.json"
PLUGIN = (
    ROOT
    / ".local-discovery/gold-grafana-20261104/plugins/grafana-clickhouse-datasource"
)
TEMPLATE_DATABASE = "f09_stream_mvp_20261111_001"
_RUN = re.compile(r"[a-z0-9][a-z0-9-]{2,39}")
_ROLES = {
    "bootstrap": ["Admin", "Read", "Write", "List"],
    "writer": ["Read", "Write", "List"],
    "reader": ["Read", "List"],
}

type Document = dict[str, object]


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def database_name(run_id: str) -> str:
    return run_id.replace("-", "_")


def bucket_name(run_id: str) -> str:
    return "fleet-" + run_id


def container_path(path: Path) -> str:
    """Map a repository file to its read-only /workspace path, or refuse."""
    try:
        relative = path.resolve().relative_to(ROOT)
    except ValueError:
        raise ValueError("recording_prepare_outside_repository") from None
    return "/workspace/" + relative.as_posix()


def file_digest(path: Path) -> Document:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def software() -> Document:
    """Record the code revision; a dirty worktree is evidence, not a refusal."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout

    return {
        "commit": git("rev-parse", "HEAD").strip(),
        "worktree_clean": git("status", "--porcelain") == "",
    }


def _write(path: Path, body: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    path.chmod(0o600)


def _json(path: Path, value: object) -> None:
    _write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def prepare(
    bundle: Path,
    reference: Path,
    source: Path,
    private: Path,
    plugin: Path = PLUGIN,
) -> Document:
    require(not private.exists() and private.parent.is_dir(), "recording_private_scope")
    manifest_path = bundle / "manifest.json"
    require(
        manifest_path.is_file() and (bundle / "events.jsonl").is_file(),
        "recording_bundle_required",
    )
    require(reference.is_file() and source.is_file(), "recording_inputs_required")
    require((plugin / "plugin.json").is_file(), "recording_grafana_plugin_required")
    manifest = json.loads(manifest_path.read_bytes())
    run_id = manifest.get("run_id")
    require(isinstance(run_id, str) and _RUN.fullmatch(run_id), "recording_run_id")
    run = str(run_id)
    database = database_name(run)
    template = DASHBOARD.read_text(encoding="utf-8")
    # The constant variable stores the name in query, current and options.
    require(template.count(TEMPLATE_DATABASE) == 5, "recording_dashboard_template")
    bundle_path, reference_path = container_path(bundle), container_path(reference)

    keys = {
        role: {"access_key": secrets.token_hex(16), "secret_key": secrets.token_hex(32)}
        for role in _ROLES
    }
    passwords = {
        name: secrets.token_hex(32)
        for name in ("ch_bootstrap", "grafana_admin", "grafana_reader")
    }
    reference_digest = file_digest(reference)
    revision = software()
    source_manifest = {
        "format_version": "f09-recording-source-manifest-v1",
        "run_id": run,
        "original": file_digest(source),
        "bundle_manifest": file_digest(manifest_path),
        "reference": reference_digest,
        "software": revision,
    }

    previous = os.umask(0o077)
    try:
        private.mkdir(mode=0o700)
        (private / "dashboards").mkdir(mode=0o700)
        _json(
            private / "s3.json",
            {
                "identities": [
                    {
                        "name": role,
                        "credentials": [
                            {
                                "accessKey": keys[role]["access_key"],
                                "secretKey": keys[role]["secret_key"],
                            }
                        ],
                        "actions": [
                            action
                            if role == "bootstrap"
                            else f"{action}:{bucket_name(run)}"
                            for action in actions
                        ],
                    }
                    for role, actions in _ROLES.items()
                ]
            },
        )
        _json(
            private / "secrets.json",
            {
                "ch_bootstrap": passwords["ch_bootstrap"],
                "grafana_reader": passwords["grafana_reader"],
                "s3": keys,
            },
        )
        _json(
            private / "run.json",
            {
                "format_version": "f09-recording-run-v1",
                "run_id": run,
                "database": database,
                "bucket": bucket_name(run),
                "bundle": bundle_path,
                "reference": reference_path,
                "reference_sha256": reference_digest["sha256"],
                "reference_bytes": reference_digest["bytes"],
                "source_manifest": "/private/source-manifest.json",
            },
        )
        _json(private / "source-manifest.json", source_manifest)
        _write(
            private / "dashboards/recording-stream.json",
            template.replace(TEMPLATE_DATABASE, database),
        )
        # Compose reads this file through --env-file; it holds no key bytes.
        _write(
            private / "compose.env",
            "".join(
                f"{name}={value}\n"
                for name, value in (
                    ("RECORDING_RUN_ID", run),
                    ("RECORDING_PRIVATE", private.resolve().as_posix()),
                    ("RECORDING_GRAFANA_PLUGIN", plugin.resolve().as_posix()),
                    ("RECORDING_CH_BOOTSTRAP_PASSWORD", passwords["ch_bootstrap"]),
                    ("RECORDING_GRAFANA_PASSWORD", passwords["grafana_admin"]),
                    (
                        "RECORDING_GRAFANA_READER_PASSWORD",
                        passwords["grafana_reader"],
                    ),
                )
            ),
        )
    finally:
        os.umask(previous)
    return {
        "run_id": run,
        "database": database,
        "bucket": bucket_name(run),
        "events": manifest.get("events"),
        "reference_bytes": reference_digest["bytes"],
        "worktree_clean": revision["worktree_clean"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = prepare(args.bundle, args.reference, args.source, args.private)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # ValueError carries a fixed reason code; other errors may embed paths.
        category = str(error) if isinstance(error, ValueError) else type(error).__name__
        print(json.dumps({"status": "failed", "category": category[:64]}))
        return 2
    print(json.dumps({"status": "prepared", **summary}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
