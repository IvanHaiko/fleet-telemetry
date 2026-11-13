"""Validate bounded, trusted-parent checkpoint observations without SDK imports."""

import json
import math
import re
from typing import cast
from urllib.parse import urlsplit


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("invalid_checkpoint_evidence")


def _json(value: object, depth: int = 0) -> None:
    _require(depth <= 64)
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        _require(math.isfinite(value))
    elif type(value) is list:
        for item in cast(list[object], value):
            _json(item, depth + 1)
    elif type(value) is dict:
        for key, item in cast(dict[object, object], value).items():
            _require(type(key) is str)
            _json(item, depth + 1)
    else:
        _require(False)


def _section(value: object) -> dict[str, object]:
    _require(type(value) is dict)
    return cast(dict[str, object], value)


def _integer(section: dict[str, object], key: str, low: int, high: int | None) -> int:
    value = section.get(key)
    _require(type(value) is int)
    number = cast(int, value)
    _require(low <= number and (high is None or number <= high))
    return number


def _array(section: dict[str, object], key: str) -> list[object]:
    value = section.get(key)
    _require(type(value) is list)
    result = cast(list[object], value)
    _require(0 < len(result) <= 32)
    return result


def _ids(section: dict[str, object], key: str) -> set[str]:
    values = _array(section, key)
    _require(
        all(
            type(v) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", v) is not None
            for v in values
        )
    )
    result = set(cast(list[str], values))
    _require(len(result) == len(values))
    return result


def _same(left: object, right: object) -> bool:
    # Python's ordinary equality conflates booleans with numeric counts.
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        a, b = cast(dict[str, object], left), cast(dict[str, object], right)
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if type(left) is list:
        a_list, b_list = cast(list[object], left), cast(list[object], right)
        return len(a_list) == len(b_list) and all(
            _same(a, b) for a, b in zip(a_list, b_list, strict=True)
        )
    return bool(left == right)


def validate_recovery(report: object) -> dict[str, object]:
    """Reject incomplete or contradictory retained observations with a safe error."""
    try:
        return _validate(report)
    except (ValueError, TypeError, OverflowError, RecursionError, KeyError):
        raise ValueError("invalid_checkpoint_evidence") from None


def _validate(report: object) -> dict[str, object]:
    _json(report)
    _require(len(json.dumps(report, allow_nan=False).encode()) <= 1_048_576)
    root = _section(report)
    _require(root.get("profile") == "m3-kafka-checkpoint-v1")
    source = _section(root.get("source"))
    cp = _section(root.get("checkpoint"))
    fault = _section(root.get("fault"))
    restore = _section(root.get("restore"))
    done = _section(root.get("completion"))
    end = _integer(source, "end_offset", 4, 32)
    _integer(source, "start_offset", 0, 0)
    _integer(source, "partition", 0, 0)
    for name in ("cluster", "topic"):
        before, after = source.get(name + "_before"), source.get(name + "_after")
        _require(
            type(before) is str
            and bool(before)
            and before.isascii()
            and before == after
        )
    original = _array(source, "original_hashes")
    retained = _array(source, "retained_hashes")
    _require(len(original) == end and original == retained)
    _require(
        all(
            type(v) is str and re.fullmatch(r"[0-9a-f]{64}", v) is not None
            for v in original
        )
    )
    checkpoint_id = _integer(cp, "id", 1, None)
    prefix = _integer(cp, "next_offset", 1, end - 1)
    prefix_ids = _ids(cp, "prefix_ids")
    _require(cp.get("status") == "COMPLETED")
    path = cp.get("external_path")
    _require(type(path) is str and bool(path))
    uri = urlsplit(cast(str, path))
    _require(uri.scheme == "file" and bool(uri.path))
    _require(fault.get("kind") == "python_worker_exit")
    _integer(fault, "requested_exit_code", 87, 87)
    _integer(fault, "worker_pid", 1, None)
    _require(fault.get("pid_ended") is True)
    _integer(fault, "offset", prefix, end - 1)
    _integer(fault, "checkpoint_id", checkpoint_id, checkpoint_id)
    _integer(restore, "checkpoint_id", checkpoint_id, checkpoint_id)
    _integer(restore, "count", 1, None)
    _integer(restore, "attempt", 1, None)
    _integer(restore, "first_offset", prefix, prefix)
    _require(_ids(restore, "history_ids") == prefix_ids)
    _require(_ids(restore, "active_ids") == prefix_ids)
    _integer(restore, "window_unique_events", len(prefix_ids), len(prefix_ids))
    _require(done.get("status") == "FINISHED" and done.get("conflict_free") is True)
    _integer(done, "next_offset", end, end)
    expected = _ids(done, "expected_ids")
    _require(prefix_ids <= expected and expected == _ids(done, "actual_ids"))
    windows = _array(done, "expected_windows")
    actual = _array(done, "actual_windows")
    _require(all(type(v) is dict for v in windows + actual))
    _require(_same(windows, actual))
    return {
        "status": "checkpoint_recovery_verified",
        "checkpoint_id": checkpoint_id,
        "restored_next_offset": prefix,
        "completed_next_offset": end,
        "unique_events": len(expected),
    }
