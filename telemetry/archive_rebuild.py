"""Archive-only isolated file reconstruction; incomplete outputs are retained."""

import os
import stat
from pathlib import Path

from telemetry.archive_codec import _fail
from telemetry.archive_documents import canonical, digest
from telemetry.archive_graph import VerifiedArchive, verify_catalog
from telemetry.archive_interfaces import ReadStore


def fresh_destination(destination: Path) -> Path:
    """Check every lexical ancestor without resolving through symlinks/junctions."""
    if ".." in destination.parts:
        _fail("invalid_format", "destination")
    absolute = Path(os.path.abspath(destination))
    for path in (absolute, *absolute.parents):
        if path.is_symlink() or path.is_junction():
            _fail("invalid_format", "destination")
        try:
            info = path.lstat()
        except FileNotFoundError:
            if path != absolute:
                _fail("object_missing", "destination_parent")
            continue
        if path == absolute or not stat.S_ISDIR(info.st_mode):
            _fail("invalid_format", "destination")
    return absolute


def write_file(path: Path, body: bytes) -> None:
    """Create exclusively and fsync data before any completion marker."""
    with path.open("xb") as output:
        output.write(body)
        output.flush()
        os.fsync(output.fileno())


def sync_directory(path: Path) -> None:
    """Require POSIX directory fsync; Windows has no supported equivalent here."""
    if os.name == "nt":
        return
    directory_flag: object = getattr(os, "O_DIRECTORY", None)
    if type(directory_flag) is not int:
        _fail("unsupported_profile", "directory_fsync")
    descriptor = os.open(path, os.O_RDONLY | directory_flag)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def rebuild_archive(
    descriptor: bytes, expected_sha256: str, store: ReadStore, destination: Path
) -> VerifiedArchive:
    """Validate the complete graph before creating a fresh isolated dataset.

    Existing output is refused. Failures retain incomplete data. This operation
    has no source, converter, oracle, Kafka or automatic cleanup fallback.
    The caller owns the destination parent; concurrent filesystem mutation is
    outside this bounded trusted local output profile.
    """
    verified = verify_catalog(descriptor, expected_sha256, store)
    try:
        target = fresh_destination(destination)
        target.mkdir()
        sources = target / "sources"
        sources.mkdir()
        outputs = {
            "observations.jsonl": b"".join(
                canonical(row) for row in verified.coverage.observations
            ),
            "measurements.jsonl": b"".join(
                canonical(event) for event in verified.measurements
            ),
            "descriptor.json": descriptor,
            **verified.blobs,
        }
        for key, body in outputs.items():
            write_file(target / key, body)
        sync_directory(sources)
        sync_directory(target)
        sync_directory(target.parent)
        complete = canonical(
            {
                "format_version": "archive-rebuild-complete-v1",
                "descriptor_sha256": expected_sha256,
                **{
                    key: verified.descriptor[key]
                    for key in ("source", "start_offset", "next_offset")
                },
                "observation_count": len(verified.coverage.observations),
                "measurement_count": len(verified.measurements),
                "durability": {
                    "data_file_fsync": True,
                    "completion_marker_file_fsync": True,
                    "directory_fsync": (
                        "unavailable" if os.name == "nt" else "required"
                    ),
                    "power_loss_validated": False,
                    "host_loss_validated": False,
                },
                "outputs": {
                    key: {"sha256": digest(body), "byte_length": len(body)}
                    for key, body in outputs.items()
                },
            }
        )
        # Files are flushed; directory fsync is required only on POSIX.
        # Marker ordering does not establish power-loss or host-loss durability.
        pending = target / ".complete.pending"
        write_file(pending, complete)
        # Rename only our fully flushed pending marker; retain it on failure.
        pending.rename(target / "complete.json")
        return verified
    except PermissionError:
        _fail("permission_denied", "output")
    except OSError:
        _fail("source_unavailable", "output")
