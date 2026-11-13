"""Protect setup refusal boundaries without downloads or runtime installation."""

import hashlib
import urllib.request
from pathlib import Path
from typing import NoReturn

import pytest

import bootstrap
from bootstrap import ROOT, Artifact, cached_artifact, owned_path


def test_corrupt_cached_archive_is_refused_without_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = Artifact(
        "runtime.tar.gz",
        "https://example.invalid/unused",
        hashlib.sha256(b"expected archive").hexdigest(),
    )
    cached = tmp_path / artifact.filename
    cached.write_bytes(b"corrupted evidence")

    def unexpected_request(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("Existing archive must be verified without a download")

    monkeypatch.setattr(urllib.request, "urlopen", unexpected_request)
    with pytest.raises(ValueError, match="^archive_checksum_mismatch$"):
        cached_artifact(artifact, tmp_path, offline=False)
    assert cached.read_bytes() == b"corrupted evidence"


def test_setup_refuses_project_and_native_parent_directories() -> None:
    native_parent = Path.home() / ".local/share/fleet-telemetry/pyflink"
    for path in (ROOT, Path("/usr"), ROOT / ".local-discovery", native_parent):
        with pytest.raises(ValueError, match="^project_local_directory_required$"):
            owned_path(path)


def test_stale_lock_stops_before_environment_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, directory = tmp_path / "profile", tmp_path / "runtime"
    profile.mkdir()
    directory.mkdir()
    (profile / "uv.lock").write_bytes(b"preserved lock evidence")
    calls: list[list[str]] = []

    def selected_paths(unused: Path) -> dict[str, Path]:
        return {"uv": tmp_path / "uv", "python": tmp_path / "python"}

    def empty_environment(unused: Path) -> dict[str, str]:
        return {}

    def failed_validation(
        args: list[str], env: dict[str, str], cwd: Path, timeout: int = 600
    ) -> dict[str, object]:
        calls.append(args)
        return {
            "command": args,
            "exit_code": 1,
            "timed_out": False,
            "owned_process_group_ended": True,
            "stdout": "",
            "stderr": "stale lock",
        }

    monkeypatch.setattr(bootstrap, "HERE", profile)
    monkeypatch.setattr(bootstrap, "paths", selected_paths)
    monkeypatch.setattr(bootstrap, "environment", empty_environment)
    monkeypatch.setattr(bootstrap, "command", failed_validation)
    result = bootstrap.install(directory, offline=True)
    assert result["exit_code"] == 1 and result["lock_unchanged"]
    assert len(calls) == 1 and calls[0][1:4] == ["lock", "--check", "--offline"]
    assert not (directory / "venv").exists()
