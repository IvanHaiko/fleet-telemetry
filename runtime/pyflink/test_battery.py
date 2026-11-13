"""Purposeful preflight and incomplete-evidence refusals for the bounded probe."""

from pathlib import Path

import pytest

from battery_gate import MAX_INPUT_BYTES, MAX_OBSERVATIONS, BatteryScope, bounded_input
from battery_operator import BatteryOperator
from check_battery import verify
from paced_source import PacedSource


def test_input_budgets_before_job_submission() -> None:
    assert bounded_input([b"x"] * MAX_OBSERVATIONS)[-1][0] == MAX_OBSERVATIONS - 1
    with pytest.raises(ValueError, match="count_or_type"):
        bounded_input([b""] * (MAX_OBSERVATIONS + 1))
    with pytest.raises(ValueError, match="input_bytes"):
        bounded_input([b"x" * (MAX_INPUT_BYTES + 1)])


def test_invalid_trusted_scope_refuses_submission() -> None:
    selected = BatteryScope(
        "run",
        "pipeline",
        "sha256:" + "a" * 64,
        "1970-01-02T00:00:00.000000Z",
        "1970-01-01T00:00:00.000000Z",
    )
    with pytest.raises(ValueError, match="scope_bounds"):
        selected.validate()


def test_missing_disposition_cannot_release_partial_result() -> None:
    with pytest.raises(ValueError, match="incomplete_operator_dispositions"):
        verify([b"{}"], [])


def test_identity_budget_is_explicit_and_bounded() -> None:
    selected = BatteryScope(
        "run",
        "pipeline",
        "sha256:" + "a" * 64,
        "1970-01-01T00:00:00.000000Z",
        "1970-01-02T00:00:00.000000Z",
    )
    for limit in (0, MAX_OBSERVATIONS + 1, True):
        with pytest.raises(ValueError, match="invalid_battery_identity_limit"):
            BatteryOperator(selected, identity_limit=limit)


def test_paced_source_ends_when_client_startup_fails(tmp_path: Path) -> None:
    source = PacedSource([], tmp_path)
    with pytest.raises(RuntimeError, match="deliberate_client_startup_failure"):
        with source:
            raise RuntimeError("deliberate_client_startup_failure")
    assert not source.thread.is_alive()
    assert source.listener.fileno() == -1
