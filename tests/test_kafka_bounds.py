"""Regression for falsely successful finite Kafka input after retention loss."""

import json
from pathlib import Path

import pytest

from runtime.pyflink.kafka_bounds import (
    SourceBoundsError,
    validate_bounds,
    verify_receipts,
)


def test_declared_interval_must_survive_until_completion() -> None:
    validate_bounds((4,), {0: 0})  # Producers may still be publishing the suffix.
    validate_bounds((4,), {0: 0}, {0: 4})
    for low, high in (({0: 5}, {0: 5}), ({0: 1}, {0: 4}), ({0: 0}, {0: 3})):
        with pytest.raises(SourceBoundsError, match="kafka_source_gap"):
            validate_bounds((4,), low, high)


def test_flink_finished_cannot_hide_missing_or_conflicting_receipts(
    tmp_path: Path,
) -> None:
    with pytest.raises(SourceBoundsError, match="kafka_source_gap"):
        verify_receipts("battery", (4,), tmp_path)
    for offset in range(4):
        (tmp_path / f"source-initial-0-{offset}.json").write_text(
            json.dumps(
                {
                    "topic": "battery",
                    "partition": 0,
                    "offset": offset,
                    "key_sha256": "a" * 64,
                    "value_sha256": "b" * 64,
                }
            )
        )
    verify_receipts("battery", (4,), tmp_path)
    duplicate = tmp_path / "source-cold-0-2.json"
    value = json.loads((tmp_path / "source-initial-0-2.json").read_text())
    duplicate.write_text(json.dumps(value))
    verify_receipts("battery", (4,), tmp_path)
    value["value_sha256"] = "c" * 64
    duplicate.write_text(json.dumps(value))
    with pytest.raises(SourceBoundsError, match="kafka_source_gap"):
        verify_receipts("battery", (4,), tmp_path)
