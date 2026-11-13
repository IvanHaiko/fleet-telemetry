"""Finite, exact, read-only observation retrieval."""

import math
import time
from collections.abc import Mapping

from runtime.kafka_archive.types import SliceClient, SourceInfo
from telemetry.archive_codec import (
    _fail,
    _integer,
    _source,
    decode_observations,
    encode_observations,
)


def deadline(timeout: float) -> float:
    if (
        type(timeout) not in (int, float)
        or not 0 < timeout <= 120
        or not math.isfinite(timeout)
    ):
        _fail()
    return time.monotonic() + timeout


def remaining(end: float) -> float:
    value = end - time.monotonic()
    if value <= 0:
        _fail("deadline_exceeded", "source")
    return value


def _snapshot(
    info: SourceInfo, source: Mapping[str, object], start: int, end: int
) -> int:
    if _source(info.source) != source:
        _fail("source_identity", "source")
    if info.delete_only is not True:
        _fail("unsupported_profile", "cleanup_policy")
    low = _integer(info.low, 0, 2**63 - 1)
    high = _integer(info.high, 0, 2**63 - 1)
    if not low <= start < end <= high:
        _fail("source_gap", "retention")
    if type(info.committed) is not int or info.committed not in (start, end):
        _fail("progress_mismatch", "committed")
    return info.committed


def read_slice(
    client: SliceClient,
    source: Mapping[str, object],
    start: int,
    next_offset: int,
    *,
    timeout_seconds: float = 30,
) -> tuple[dict[str, object], ...]:
    expected = _source(source)
    if expected["partition"] != 0:
        _fail("unsupported_profile", "assignment")
    start = _integer(start, 0, 2**63 - 1)
    end = _integer(next_offset, 0, 2**63 - 1)
    if start >= end:
        _fail()
    if end - start > 32:
        _fail("limit_exceeded", "interval")
    expires = deadline(timeout_seconds)
    rows: list[dict[str, object]] = []

    def assignment() -> None:
        remaining(expires)
        if client.assigned() is not True:
            _fail("unsupported_profile", "assignment")
        remaining(expires)

    try:
        progress = _snapshot(client.inspect(remaining(expires)), expected, start, end)
        remaining(expires)
        client.assign(start)
        assignment()
        while len(rows) < end - start:
            row = client.poll(remaining(expires))
            remaining(expires)
            assignment()
            if row is None:
                continue
            owned = decode_observations(encode_observations([row]))[0]
            if _source({key: owned[key] for key in expected}) != expected:
                _fail("source_identity", "source")
            if owned["offset"] != start + len(rows):
                _fail("source_gap", "offset")
            if owned["measurement"] is not None:
                _fail()
            rows.append(owned)
        for index in range(0, len(rows), 16):
            encode_observations(rows[index : index + 16])
        final = _snapshot(client.inspect(remaining(expires)), expected, start, end)
        remaining(expires)
        if final != progress:
            _fail("progress_mismatch", "committed")
        assignment()
        return tuple(rows)
    except PermissionError:
        _fail("permission_denied", "source")
    except TimeoutError:
        _fail("deadline_exceeded", "source")
    except OSError:
        _fail("source_unavailable", "source")
