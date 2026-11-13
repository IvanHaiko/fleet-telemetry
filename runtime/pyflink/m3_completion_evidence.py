"""Bounded consistency checks for trusted, parent-observed runtime evidence."""

import json
import math
import re
from typing import cast


def require(condition: bool) -> None:
    if not condition:
        raise ValueError("invalid_m3_evidence")


def mapping(value: object) -> dict[str, object]:
    require(type(value) is dict)
    return cast(dict[str, object], value)


def array(value: object) -> list[object]:
    require(type(value) is list)
    result = cast(list[object], value)
    require(len(result) <= 128)
    return result


def integer(value: object, low: int, high: int) -> int:
    require(type(value) is int)
    result = cast(int, value)
    require(low <= result <= high)
    return result


def text(value: object, pattern: str = r"[\x20-\x7e]+") -> str:
    require(type(value) is str)
    result = cast(str, value)
    require(re.fullmatch(pattern, result) is not None)
    return result


def digest(value: object) -> str:
    return text(value, r"[0-9a-f]{64}")


def identity(value: object) -> tuple[str, str, str]:
    row = mapping(value)
    return text(row["cluster_id"]), text(row["topic_id"]), text(row["topic"])


def ids(value: object) -> set[str]:
    rows = array(value)
    result = {text(row, r"sha256:[0-9a-f]{64}") for row in rows}
    require(bool(result) and len(result) == len(rows))
    return result


def json_tree(value: object, ancestors: frozenset[int] = frozenset()) -> None:
    require(len(ancestors) < 128)
    if type(value) in (dict, list):
        require(id(value) not in ancestors)
        ancestors = ancestors | {id(value)}
        if type(value) is dict:
            row = mapping(value)
            require(len(row) <= 128 and all(type(key) is str for key in row))
            children = list(row.values())
        else:
            children = array(value)
        for child in children:
            json_tree(child, ancestors)
    elif type(value) is float:
        require(math.isfinite(value))
    else:
        require(value is None or type(value) in (str, int, bool))


def structural(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def records(value: object, ends: list[int]) -> dict[tuple[int, int], tuple[str, str]]:
    rows = array(value)
    require(len(rows) == sum(ends))
    result: dict[tuple[int, int], tuple[str, str]] = {}
    for item in rows:
        row = mapping(item)
        partition = integer(row["partition"], 0, 1)
        position = (partition, integer(row["offset"], 0, ends[partition] - 1))
        require(position not in result)
        result[position] = (digest(row["key_sha256"]), digest(row["value_sha256"]))
    return result


def _validate(report: object) -> dict[str, object]:
    json_tree(report)
    require(len(structural(report).encode("utf-8")) <= 1_048_576)
    root = mapping(report)
    require(root["profile"] == "m3-local-synthetic-v1")
    kafka = mapping(root["kafka"])
    require(identity(kafka["source_before"]) == identity(kafka["source_after"]))
    raw_ends = array(kafka["ends"])
    require(len(raw_ends) == 2)
    ends = [integer(end, 1, 64) for end in raw_ends]
    require(
        records(kafka["expected_records"], ends)
        == records(kafka["actual_records"], ends)
    )
    idle = mapping(root["idleness"])
    for key, expected in {
        "timeout_ms": 30000,
        "source_parallelism": 2,
        "lane_parallelism": 2,
        "invalid_future_count": 1,
        "late_resume_count": 2,
        "duplicate_resume_count": 1,
    }.items():
        integer(idle[key], expected, expected)
    names = (
        "active_minimum_held",
        "idle_excluded",
        "resumed_old_event",
        "resumed_input_holds_minimum",
        "all_silent_no_eof",
        "resume_after_both_silent",
        "second_resumed_old_event",
        "both_active_advanced",
    )
    phases = array(idle["phases"])
    require(len(phases) == 8)
    for item, name, watermark in zip(
        phases,
        names,
        (-2001, 9999, 9999, 9999, 19999, 29999, 29999, 39999),
        strict=True,
    ):
        phase = mapping(item)
        require(set(phase) == {"name", "watermark_ms"} and phase["name"] == name)
        integer(phase["watermark_ms"], watermark, watermark)
    expected_ids = ids(idle["expected_ids"])
    require(expected_ids == ids(idle["actual_ids"]))
    for key in ("expected_windows", "actual_windows"):
        windows = array(idle[key])
        require(bool(windows))
        for window in windows:
            mapping(window)
    require(structural(idle["expected_windows"]) == structural(idle["actual_windows"]))
    proofs = array(root["recovery"])
    require(len(proofs) == 2)
    domains = ["taskmanager_sigkill", "runtime_restart"]
    for item, kind in zip(proofs, domains, strict=True):
        proof = mapping(item)
        require(proof["kind"] == kind)
        require(identity(proof["source_before"]) == identity(proof["source_after"]))
        require(type(proof["checkpoint_id"]) is int)
        require(cast(int, proof["checkpoint_id"]) > 0)
        require(proof["checkpoint_status"] == "COMPLETED")
        require(
            digest(proof["checkpoint_sha256_before"])
            == digest(proof["checkpoint_sha256_after"])
        )
        offset = integer(proof["next_offset"], 1, 63)
        integer(proof["first_restored_offset"], offset, offset)
        prefix = ids(proof["prefix_ids"])
        require(prefix == ids(proof["restored_ids"]))
        integer(proof["restored_window_unique_events"], len(prefix), len(prefix))
        require(text(proof["runtime_id_before"]) != text(proof["runtime_id_after"]))
        require(proof["source_progress_from_checkpoint"] is True)
        require(proof["reference_match"] is True and proof["status"] == "FINISHED")
    resources = mapping(root["resources"])
    limit = integer(resources["limit_bytes"], 1, 4 * 1024**3)
    peak = integer(resources["peak_bytes"], 1, limit - 1)
    integer(resources["python_rss_peak_bytes"], 1, peak)
    require(resources["oom_killed"] is False)
    state_limit = integer(resources["state_limit"], 1, 128)
    integer(resources["history_at_limit"], state_limit, state_limit)
    require(resources["refused_reason"] == "battery_history_limit")
    watermark = integer(resources["watermark_before"], -(2**63), 2**63 - 1)
    integer(resources["watermark_after"], watermark, watermark)
    return {
        "status": "m3_local_synthetic_verified",
        "partitions": 2,
        "recovery_domains": domains,
        "unique_measurements": len(expected_ids),
        "memory_peak_bytes": peak,
    }


def validate_m3(report: object) -> dict[str, object]:
    """Validate consistency without mutating input or authenticating observations."""
    try:
        return _validate(report)
    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
        UnicodeError,
    ):
        raise ValueError("invalid_m3_evidence") from None
