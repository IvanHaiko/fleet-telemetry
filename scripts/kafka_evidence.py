"""Explicit validation and fsynced evidence writes for the producer experiment."""

import json
import os
from pathlib import Path
from typing import cast


class BrokerQuarantined(ValueError):
    """The historical local broker must remain stopped after retention loss."""


def require_mutable_profile(project: str, context: str) -> None:
    """Block the retired Desktop profile before subprocess or broker access."""
    if (project, context) == ("fleet-kafka-440-probe", "desktop-linux"):
        raise BrokerQuarantined("historical_broker_quarantined")


def require(condition: bool, reason: str) -> None:
    """Keep verification active under optimized Python."""
    if not condition:
        raise ValueError(reason)


def obj(value: object) -> dict[str, object]:
    """Check JSON object boundaries before reading fields."""
    require(isinstance(value, dict), "expected_object")
    value = cast(dict[object, object], value)
    require(all(isinstance(k, str) for k in value), "expected_string_keys")
    return cast(dict[str, object], value)


def save(path: Path, value: object) -> None:
    """Persist new bounded evidence without overwriting prior progress."""
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    require(len(raw) <= 1024 * 1024, "evidence_bound_exceeded")
    with path.open("xb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    require(path.read_bytes() == raw, "evidence_write_differs")
