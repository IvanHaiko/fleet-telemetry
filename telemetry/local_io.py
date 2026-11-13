"""Bounded regular-file reads and atomic no-replace run publication."""

import ctypes
import errno
import os
import stat
import sys
from pathlib import Path

from telemetry.conversion_contract import ConversionError, string_value

_WINDOWS_PUBLICATION = os.name == "nt"
_LINUX_PUBLICATION = sys.platform == "linux"


def read_bounded(path: Path, limit: int) -> bytes:
    validate_local_path(path)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ConversionError("input_not_regular_file")
    with path.open("rb") as handle:
        if os.fstat(handle.fileno()).st_size > limit:
            raise ConversionError("input_too_large")
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ConversionError("input_too_large")
    return data


def validate_local_path(path: Path) -> None:
    string_value(str(path))
    if "\x00" in str(path) or path.drive.startswith("\\\\"):
        raise ConversionError("unsupported_local_path")


def run_path(path: Path, run_id: str) -> Path:
    validate_local_path(path)
    absolute = path.absolute()
    for candidate in (absolute, *absolute.parents):
        if candidate.is_symlink() or candidate.is_junction():
            raise ConversionError("output_symlink_unsupported")
    parent = absolute.parent.resolve(strict=True)
    if not parent.is_dir() or absolute.name != run_id:
        raise ConversionError("invalid_output_destination")
    target = parent / absolute.name
    return target


def destination(path: Path, run_id: str) -> Path:
    if not (_WINDOWS_PUBLICATION or _LINUX_PUBLICATION):
        raise ConversionError("unsupported_publication_platform")
    target = run_path(path, run_id)
    if os.path.lexists(target):
        raise ConversionError("output_exists")
    return target


def publish_run(stage: Path, target: Path) -> None:
    """Atomically publish without replacing even an empty destination."""
    if _WINDOWS_PUBLICATION:
        os.rename(stage, target)
        return
    if not _LINUX_PUBLICATION:
        raise ConversionError("unsupported_publication_platform")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError):
        raise ConversionError("unsupported_publication_operation") from None
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    # Linux UAPI constants: AT_FDCWD and RENAME_NOREPLACE, not syscall numbers.
    result = renameat2(-100, os.fsencode(stage), -100, os.fsencode(target), 1)
    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
            raise ConversionError("unsupported_publication_operation")
        raise OSError(error, "publication_failed")
