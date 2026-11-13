"""Contract tests using synthetic retained observations, not runtime evidence."""

from copy import deepcopy
from typing import Any

import pytest

from checkpoint_evidence import validate_recovery


def _evidence() -> dict[str, Any]:
    # Literal independent example: four source records, two retained at checkpoint 7.
    return {
        "profile": "m3-kafka-checkpoint-v1",
        "source": {
            "cluster_before": "cluster-A",
            "cluster_after": "cluster-A",
            "topic_before": "topic-A",
            "topic_after": "topic-A",
            "start_offset": 0,
            "end_offset": 4,
            "partition": 0,
            "original_hashes": [
                "0000000000000000000000000000000000000000000000000000000000000000",
                "1111111111111111111111111111111111111111111111111111111111111111",
                "2222222222222222222222222222222222222222222222222222222222222222",
                "3333333333333333333333333333333333333333333333333333333333333333",
            ],
            "retained_hashes": [
                "0000000000000000000000000000000000000000000000000000000000000000",
                "1111111111111111111111111111111111111111111111111111111111111111",
                "2222222222222222222222222222222222222222222222222222222222222222",
                "3333333333333333333333333333333333333333333333333333333333333333",
            ],
        },
        "checkpoint": {
            "id": 7,
            "status": "COMPLETED",
            "external_path": "file:///checkpoints/7",
            "next_offset": 2,
            "prefix_ids": [
                "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ],
        },
        "fault": {
            "kind": "python_worker_exit",
            "requested_exit_code": 87,
            "worker_pid": 123,
            "pid_ended": True,
            "offset": 2,
            "checkpoint_id": 7,
        },
        "restore": {
            "checkpoint_id": 7,
            "count": 1,
            "attempt": 1,
            "first_offset": 2,
            "history_ids": [
                "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ],
            "active_ids": [
                "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ],
            "window_unique_events": 2,
        },
        "completion": {
            "status": "FINISHED",
            "next_offset": 4,
            "conflict_free": True,
            "expected_ids": [
                "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            ],
            "actual_ids": [
                "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ],
            "expected_windows": [
                {"start": 0, "count": 2, "sum": 3, "nullable": None},
                {"start": 10, "count": 2, "sum": 7, "nested": [True, {"label": "x"}]},
            ],
            "actual_windows": [
                {"start": 0, "count": 2, "sum": 3, "nullable": None},
                {"start": 10, "count": 2, "sum": 7, "nested": [True, {"label": "x"}]},
            ],
        },
    }


def _replace(report: dict[str, Any], path: tuple[str, ...], value: object) -> None:
    parent = report
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value


def _reject(report: object) -> None:
    before = deepcopy(report)
    with pytest.raises(ValueError) as caught:
        validate_recovery(report)
    assert str(caught.value).strip(), "A fixed safe reason is required"
    assert report == before


def test_valid_report_has_exact_result_and_is_unchanged() -> None:
    report = _evidence()
    before = deepcopy(report)
    result = validate_recovery(report)
    assert result == {
        "status": "checkpoint_recovery_verified",
        "checkpoint_id": 7,
        "restored_next_offset": 2,
        "completed_next_offset": 4,
        "unique_events": 4,
    }
    assert all(
        type(result[key]) is int
        for key in (
            "checkpoint_id",
            "restored_next_offset",
            "completed_next_offset",
            "unique_events",
        )
    )
    assert report == before


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("profile",), "other"),
        (("source", "cluster_after"), "cluster-B"),
        (("source", "topic_after"), "topic-B"),
        (("source", "topic_before"), "tópico"),
        (("source", "retained_hashes"), ["0" * 64] * 4),
        (("source", "original_hashes"), ["A" * 64] * 4),
        (("source", "retained_hashes"), []),
        (("checkpoint", "status"), "IN_PROGRESS"),
        (("checkpoint", "external_path"), "https://example.invalid/7"),
        (("checkpoint", "next_offset"), 4),
        (("checkpoint", "prefix_ids"), []),
        (("fault", "kind"), "restart"),
        (("fault", "requested_exit_code"), 1),
        (("fault", "pid_ended"), False),
        (("fault", "offset"), 1),
        (("fault", "offset"), 4),
        (("fault", "checkpoint_id"), 8),
        (("restore", "checkpoint_id"), 8),
        (("restore", "count"), 0),
        (("restore", "attempt"), 0),
        (("restore", "first_offset"), 0),
        (("restore", "history_ids"), []),
        (("restore", "active_ids"), []),
        (("restore", "window_unique_events"), 1),
        (("completion", "status"), "RUNNING"),
        (("completion", "next_offset"), 3),
        (("completion", "conflict_free"), False),
        (("completion", "actual_ids"), []),
        (("completion", "expected_windows"), []),
    ],
)
def test_rejects_lost_changed_or_incomplete_evidence(
    path: tuple[str, ...],
    value: object,
) -> None:
    report = _evidence()
    _replace(report, path, value)
    _reject(report)


@pytest.mark.parametrize(
    "section,key",
    [
        ("source", "start_offset"),
        ("source", "end_offset"),
        ("source", "partition"),
        ("checkpoint", "id"),
        ("checkpoint", "next_offset"),
        ("fault", "requested_exit_code"),
        ("fault", "worker_pid"),
        ("fault", "offset"),
        ("fault", "checkpoint_id"),
        ("restore", "checkpoint_id"),
        ("restore", "count"),
        ("restore", "attempt"),
        ("restore", "first_offset"),
        ("restore", "window_unique_events"),
        ("completion", "next_offset"),
    ],
)
@pytest.mark.parametrize("replacement", [True, 1.0])
def test_integer_fields_reject_bool_and_float(
    section: str,
    key: str,
    replacement: object,
) -> None:
    report = _evidence()
    report[section][key] = replacement
    _reject(report)


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "invalid_id",
        "prefix_outside_expected",
        "sum",
        "null",
        "count",
        "order",
    ],
)
def test_identity_and_window_content_are_preserved(case: str) -> None:
    report = _evidence()
    completion = report["completion"]
    if case == "duplicate":
        completion["actual_ids"].append(completion["actual_ids"][0])
    elif case == "invalid_id":
        completion["actual_ids"][0] = "sha256:" + "D" * 64
    elif case == "prefix_outside_expected":
        # Keep final sets equal while removing one retained prefix identity.
        completion["expected_ids"].remove(report["checkpoint"]["prefix_ids"][0])
        completion["actual_ids"].remove(report["checkpoint"]["prefix_ids"][0])
    elif case == "order":
        completion["actual_windows"].reverse()
    else:
        completion["actual_windows"][0][{"null": "nullable"}.get(case, case)] = 99
    _reject(report)


@pytest.mark.parametrize(
    "case",
    ["missing", "not_dict", "oversize", "array_limit", "nan", "infinity", "native"],
)
def test_rejects_malformed_or_unbounded_reports(case: str) -> None:
    report = _evidence()
    if case == "not_dict":
        _reject([])
        return
    if case == "missing":
        del report["restore"]
    elif case == "oversize":
        report["completion"]["actual_windows"][0]["payload"] = "x" * 1_048_577
    elif case == "array_limit":
        report["completion"]["expected_windows"] = [{}] * 33
        report["completion"]["actual_windows"] = [{}] * 33
    else:
        value = {"nan": float("nan"), "infinity": float("inf"), "native": {1, 2}}[case]
        report["completion"]["expected_windows"][0]["sum"] = value
        report["completion"]["actual_windows"][0]["sum"] = value
    _reject(report)


def test_errors_use_fixed_reasons_without_supplied_secrets() -> None:
    messages: list[str] = []
    for secret in ("SECRET_token_alpha_71", "SECRET_token_beta_92"):
        report = _evidence()
        report["checkpoint"]["external_path"] = (
            "https://user:" + secret + "@private.invalid"
        )
        with pytest.raises(ValueError) as caught:
            validate_recovery(report)
        message = str(caught.value)
        assert message.strip()
        assert secret not in message
        assert "private.invalid" not in message
        assert "https://user:" not in message
        messages.append(message)
    assert messages[0] == messages[1]
