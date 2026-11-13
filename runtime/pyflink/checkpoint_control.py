"""Bounded local diagnostic publication, independent of analytical durability."""

import json
import os
from pathlib import Path


def publish(control: Path, name: str, row: dict[str, object]) -> None:
    """Atomically publish a complete observation; refuse to replace evidence."""
    data = json.dumps(row, allow_nan=False, sort_keys=True).encode() + b"\n"
    if len(data) > 65536 or Path(name).name != name:
        raise ValueError("invalid_control_observation")
    temporary = control / f".{name}.{os.getpid()}.tmp"
    with temporary.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(temporary, control / name)
    finally:
        temporary.unlink()


def append_trace(control: Path, row: dict[str, object]) -> None:
    """Append a bounded safe row from the single worker; retain failed attempts."""
    data = json.dumps(row, allow_nan=False, sort_keys=True).encode() + b"\n"
    path = control / "trace.jsonl"
    if len(data) > 65536 or (path.exists() and path.stat().st_size > 1_048_576):
        raise ValueError("checkpoint_trace_limit")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        if os.write(descriptor, data) != len(data):
            raise OSError("checkpoint_trace_short_write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
