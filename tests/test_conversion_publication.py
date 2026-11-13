"""File-boundary evidence: reconciliation, replay and failure before publication."""

import ctypes
import errno
import json
import os
from pathlib import Path

import pytest
from conversion_support import assert_no_output, write_job

import telemetry_convert as converter
from telemetry import local_io
from telemetry_convert import ConversionError, convert_job


def test_existing_run_is_preserved_byte_for_byte(tmp_path: Path) -> None:
    job = write_job(tmp_path)
    target = tmp_path / "run-001"
    convert_job(job, target)
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    with pytest.raises(ConversionError, match="output_exists"):
        convert_job(job, target)
    assert before == {p.name: p.read_bytes() for p in target.iterdir()}


@pytest.mark.parametrize("empty", [False, True])
def test_rename_race_preserves_concurrent_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty: bool
) -> None:
    job = write_job(tmp_path)
    original = os.fsync
    target = tmp_path / "run-001"

    def racing_sync(fd: int) -> None:
        original(fd)
        if not target.exists():
            target.mkdir()
            if not empty:
                (target / "keep.txt").write_text("existing data", encoding="utf-8")

    monkeypatch.setattr(os, "fsync", racing_sync)
    with pytest.raises(OSError):
        convert_job(job, target)
    if empty:
        assert list(target.iterdir()) == []
    else:
        assert (target / "keep.txt").read_text() == "existing data"
    assert not list(tmp_path.glob(".telemetry-stage-*"))


def test_staging_write_failure_cleans_only_owned_temp_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = write_job(tmp_path)

    def fail_sync(fd: int) -> None:
        raise PermissionError("private synthetic diagnostic")

    monkeypatch.setattr(os, "fsync", fail_sync)
    assert (
        converter.main(["--job", str(job), "--output", str(tmp_path / "run-001")]) == 2
    )
    assert_no_output(tmp_path)
    assert (tmp_path / "input.json").exists()


def test_unsupported_publication_platform_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = write_job(tmp_path)
    monkeypatch.setattr(local_io, "_WINDOWS_PUBLICATION", False)
    monkeypatch.setattr(local_io, "_LINUX_PUBLICATION", False)
    with pytest.raises(ConversionError, match="unsupported_publication_platform"):
        convert_job(job, tmp_path / "run-001")
    assert_no_output(tmp_path)


@pytest.mark.parametrize("missing", ["library", "symbol"])
def test_linux_missing_publication_support_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing: str,
) -> None:
    job = write_job(tmp_path)
    monkeypatch.setattr(local_io, "_WINDOWS_PUBLICATION", False)
    monkeypatch.setattr(local_io, "_LINUX_PUBLICATION", True)

    def unavailable(*args: object, **kwargs: object) -> object:
        if missing == "library":
            raise OSError("private loader diagnostic")
        return object()

    monkeypatch.setattr(ctypes, "CDLL", unavailable)
    assert (
        converter.main(["--job", str(job), "--output", str(tmp_path / "run-001")]) == 2
    )
    assert json.loads(capsys.readouterr().err) == {
        "status": "failed",
        "reason": "unsupported_publication_operation",
    }
    assert_no_output(tmp_path)


@pytest.mark.parametrize(
    "error", [errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP, errno.EACCES]
)
def test_linux_publication_errno_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: int,
) -> None:
    job = write_job(tmp_path)
    monkeypatch.setattr(local_io, "_WINDOWS_PUBLICATION", False)
    monkeypatch.setattr(local_io, "_LINUX_PUBLICATION", True)

    class FailedRename:
        argtypes: list[object] = []
        restype: object = None

        def __call__(
            self, oldfd: int, old: bytes, newfd: int, new: bytes, flags: int
        ) -> int:
            assert (oldfd, newfd, flags) == (-100, -100, 1)
            assert Path(os.fsdecode(old)).is_dir()
            assert Path(os.fsdecode(new)) == tmp_path / "run-001"
            ctypes.set_errno(error)
            return -1

    class Library:
        renameat2 = FailedRename()

    monkeypatch.setattr(ctypes, "CDLL", lambda *args, **kwargs: Library())
    assert (
        converter.main(["--job", str(job), "--output", str(tmp_path / "run-001")]) == 2
    )
    assert json.loads(capsys.readouterr().err) == {
        "status": "failed",
        "reason": "validation_or_io_failure"
        if error == errno.EACCES
        else "unsupported_publication_operation",
    }
    assert_no_output(tmp_path)
