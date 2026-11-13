"""Bounded source ZIP export and read-only manifest verification for lab transfer."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from runtime.continuous.prepare import ROOT
from runtime.continuous.split_runtime import write_json

DIRECTORIES = {
    "compose",
    "telemetry",
    "runtime",
    "scripts",
    "tests",
    "docs",
    "contributions",
    ".github",
}
SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".xml",
    ".sql",
    ".sh",
    ".ps1",
    ".java",
    ".lock",
    ".patch",
    ".ini",
    ".cfg",
    ".txt",
    ".c",
    ".h",
}
ROOT_FILES = {
    "compose.yaml",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".gitignore",
    ".gitattributes",
}


def checksum(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def safe_relative(name: str) -> PurePosixPath:
    """Reject drive paths, traversal and aliases before opening transferred data."""
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or "\\" in name
        or ":" in name
        or not name
        or any(part in (".", "..", "") for part in name.split("/"))
    ):
        raise ValueError("split_unsafe_relative_path")
    return path


def allowed_source(name: str) -> bool:
    """Use a source allowlist; ignored/private/runtime data never enter the ZIP."""
    path = safe_relative(name)
    if path.name.lower() in {
        "agents.md",
        "agents.override.md",
        "claude.md",
        "gemini.md",
        "skill.md",
        "copilot-instructions.md",
    } or path.parts[:2] in {(".github", "instructions"), (".github", "prompts")}:
        return False
    if any(part.startswith(".") and part != ".github" for part in path.parts[:-1]):
        return False
    if any(
        part in ("__pycache__", "node_modules", "venv", "data", "checkpoints")
        for part in path.parts
    ):
        return False
    if any(
        word in path.name.lower()
        for word in ("private", "password", "credential", "secret")
    ):
        # This module's name describes its source, not credential material.
        return name == "runtime/continuous/split_credentials.py"
    if len(path.parts) == 1:
        return (
            name in ROOT_FILES
            or path.suffix == ".py"
            or (path.name.startswith("compose.") and path.suffix == ".yml")
        )
    return path.parts[0] in DIRECTORIES and (
        path.suffix in SUFFIXES
        or (path.parts[:2] == ("docs", "assets") and path.suffix == ".png")
        or path.name in {"Dockerfile", "LICENSE", "SHA256SUMS"}
        or name
        in {
            "runtime/continuous/live.html",
            "runtime/continuous/link_watch.html",
            "runtime/continuous/position_map.html",
            "runtime/continuous/mavlink_live.html",
            "runtime/kafka/kafka-probe.properties",
            "runtime/pyflink/container/Dockerfile.backport",
            "docs/mvp-target.png",
        }
    )


def export_source(target: Path, root: Path = ROOT) -> None:
    """Freeze current tracked/untracked source bytes without requiring a commit."""
    root = root.resolve(strict=True)
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            timeout=15,
        )
        .decode("utf8")
        .split("\0")
    )
    selected = sorted({name for name in names if name and allowed_source(name)})
    if not selected or len(selected) > 2048:
        raise ValueError("split_source_file_bound")
    target.mkdir(exist_ok=False)
    inventory: dict[str, object] = {}
    total = 0
    with zipfile.ZipFile(target / "source.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for name in selected:
            path = root / name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("split_source_link")
            if not path.is_file() or path.stat().st_size > 8 * 1024**2:
                raise ValueError("split_source_file_size")
            body = path.read_bytes()
            total += len(body)
            if total > 128 * 1024**2:
                raise ValueError("split_source_total_size")
            inventory[name] = {"bytes": len(body), "sha256": checksum(body)}
            # A fixed timestamp avoids leaking host file times and simplifies review.
            item = zipfile.ZipInfo(name, date_time=(2026, 10, 27, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, body)
    write_json(target / "source-manifest.json", inventory)
    for name in ("source.zip", "source-manifest.json"):
        (target / (name + ".sha256")).write_text(
            checksum((target / name).read_bytes()) + "\n"
        )


def verify_source(directory: Path) -> None:
    """Check archive bytes, exact inventory and bounded contents before extraction."""
    for name in ("source.zip", "source-manifest.json"):
        expected = (directory / (name + ".sha256")).read_text().strip()
        if checksum((directory / name).read_bytes()) != expected:
            raise ValueError("split_source_archive_checksum")
    manifest = json.loads((directory / "source-manifest.json").read_text())
    with zipfile.ZipFile(directory / "source.zip") as archive:
        members = archive.infolist()
        if (
            len(members) > 2048
            or len({m.filename for m in members}) != len(members)
            or sum(m.file_size for m in members) > 128 * 1024**2
            or {m.filename for m in members} != set(manifest)
        ):
            raise ValueError("split_source_archive_inventory")
        for item in members:
            if not allowed_source(item.filename) or item.file_size > 8 * 1024**2:
                raise ValueError("split_source_archive_member")
            body = archive.read(item)
            if manifest[item.filename] != {
                "bytes": len(body),
                "sha256": checksum(body),
            }:
                raise ValueError("split_source_member_checksum")


def verify_bundle(directory: Path) -> None:
    """Verify a generated public configuration inventory without executing it."""
    manifest = json.loads((directory / "manifest.json").read_text())
    files = manifest["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= 256:
        raise ValueError("split_bundle_inventory_bound")
    for name, digest in files.items():
        path = directory / str(safe_relative(name))
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("split_bundle_link")
        if path.stat().st_size > 8 * 1024**2 or checksum(path.read_bytes()) != digest:
            raise ValueError("split_bundle_checksum")


def export_bundle(bundle: Path, target: Path) -> None:
    """Package only hashed public configuration, excluding extra private files."""
    verify_bundle(bundle)
    manifest = json.loads((bundle / "manifest.json").read_text())
    target.mkdir(exist_ok=False)
    with zipfile.ZipFile(
        target / "configuration.zip", "x", zipfile.ZIP_DEFLATED
    ) as archive:
        for name in ["manifest.json", *sorted(manifest["files"])]:
            item = zipfile.ZipInfo(name, date_time=(2026, 10, 27, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, (bundle / name).read_bytes())
    (target / "configuration.zip.sha256").write_text(
        checksum((target / "configuration.zip").read_bytes()) + "\n"
    )
