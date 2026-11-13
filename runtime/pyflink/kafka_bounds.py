"""Guard finite retained source intervals independently of connector completion."""

import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import cast


class SourceBoundsError(ValueError):
    """Fixed safe reason suitable for a failed finite-run receipt."""


def offsets(topic: str, partitions: int, *, earliest: bool) -> dict[int, int]:
    if re.fullmatch(r"[a-zA-Z0-9._-]{1,192}", topic) is None:
        raise SourceBoundsError("kafka_source_bounds_unavailable")
    try:
        result = subprocess.run(
            [
                "/opt/kafka/bin/kafka-get-offsets.sh",
                "--bootstrap-server",
                "kafka:9092",
                "--topic",
                "^" + re.escape(topic) + "$",
                "--time",
                "-2" if earliest else "-1",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0 or len(result.stdout) > 16384:
            raise ValueError("unavailable")
        values: dict[int, int] = {}
        for line in result.stdout.splitlines():
            name, partition_text, offset_text = line.split(":")
            partition, offset = int(partition_text), int(offset_text)
            if name != topic or partition in values or offset < 0:
                raise ValueError("bounds")
            values[partition] = offset
        if set(values) != set(range(partitions)):
            raise ValueError("assignment")
        return values
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise SourceBoundsError("kafka_source_bounds_unavailable") from None


def validate_bounds(
    ends: tuple[int, ...],
    low: Mapping[int, int],
    high: Mapping[int, int] | None = None,
) -> None:
    if not ends or any(type(end) is not int or not 1 <= end <= 128 for end in ends):
        raise SourceBoundsError("kafka_source_bounds_unavailable")
    expected = set(range(len(ends)))
    if set(low) != expected or any(type(value) is not int for value in low.values()):
        raise SourceBoundsError("kafka_source_bounds_unavailable")
    if any(value != 0 for value in low.values()):
        raise SourceBoundsError("kafka_source_gap")
    if high is not None and (
        set(high) != expected
        or any(type(high[p]) is not int or high[p] < ends[p] for p in expected)
    ):
        raise SourceBoundsError("kafka_source_gap")


def verify_receipts(topic: str, ends: tuple[int, ...], control: Path) -> None:
    expected = {
        (partition, offset)
        for partition, end in enumerate(ends)
        for offset in range(end)
    }
    observed: dict[tuple[int, int], tuple[str, str]] = {}
    files = list(control.glob("source-*.json"))
    if len(files) > 1024:
        raise SourceBoundsError("kafka_source_gap")
    try:
        for path in files:
            if path.is_symlink() or path.stat().st_size > 65536:
                raise ValueError("receipt")
            row = cast(dict[str, object], json.loads(path.read_bytes()))
            p, offset = row["partition"], row["offset"]
            if (
                type(p) is not int
                or type(offset) is not int
                or row.get("topic", topic) != topic
            ):
                raise ValueError("coordinate")
            hashes = (row["key_sha256"], row["value_sha256"])
            if any(
                type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in hashes
            ):
                raise ValueError("hash")
            coordinate = (p, offset)
            pair = cast(tuple[str, str], hashes)
            if (
                coordinate not in expected
                or coordinate in observed
                and observed[coordinate] != pair
            ):
                raise ValueError("conflict")
            observed[coordinate] = pair
        if set(observed) != expected:
            raise ValueError("coverage")
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise SourceBoundsError("kafka_source_gap") from None


def before_source(topic: str, ends: tuple[int, ...]) -> dict[int, int]:
    low = offsets(topic, len(ends), earliest=True)
    validate_bounds(ends, low)
    return low


def after_source(topic: str, ends: tuple[int, ...], control: Path) -> None:
    validate_bounds(
        ends,
        offsets(topic, len(ends), earliest=True),
        offsets(topic, len(ends), earliest=False),
    )
    verify_receipts(topic, ends, control)
