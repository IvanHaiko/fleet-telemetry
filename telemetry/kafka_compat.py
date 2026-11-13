"""Lazy, local admission checks for the supported native UUID boundary."""

import base64
import importlib
import importlib.metadata
import sys
from typing import Protocol, cast


class KafkaCompatibilityError(ValueError):
    """Fixed public diagnostic for an unavailable or unsafe native boundary."""


class _Uuid(Protocol):
    def get_most_significant_bits(self) -> object: ...
    def get_least_significant_bits(self) -> object: ...


class _SDK(Protocol):
    def version(self) -> object: ...
    def libversion(self) -> object: ...
    def Uuid(self, a: int, b: int) -> _Uuid: ...


def _version(value: object) -> bool:
    return value == "2.16.0" or (
        isinstance(value, tuple)
        and len(value) == 2
        and value[0] == "2.16.0"
        and type(value[1]) is int
    )


def require_uuid_boundary() -> None:
    """Recheck versions and full signed UUID conversion without creating clients."""
    try:
        if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 13):
            raise ValueError
        if importlib.metadata.version("confluent-kafka") not in {
            "2.16.0",
            "2.16.0+fleet.uuid1",
        }:
            raise ValueError
        sdk = cast(_SDK, importlib.import_module("confluent_kafka"))
        if not _version(sdk.version()) or not _version(sdk.libversion()):
            raise ValueError
        for a, b in (
            (0, 0),
            (-1, -1),
            (2**63 - 1, -(2**63)),
            (-(2**63), 2**63 - 1),
            (1, 2),
            (4294967297, 8589934594),
            (-4294967295, -8589934590),
            (81985529216486895, -81985529216486896),
            (-1, 0),
            (0, -1),
        ):
            value = sdk.Uuid(a, b)
            most = value.get_most_significant_bits()
            least = value.get_least_significant_bits()
            raw = a.to_bytes(8, "big", signed=True) + b.to_bytes(8, "big", signed=True)
            expected = base64.b64encode(raw).decode("ascii").rstrip("=")
            if (
                type(most) is not int
                or type(least) is not int
                or most != a
                or least != b
                or str(value) != expected
            ):
                raise ValueError
    except Exception:
        raise KafkaCompatibilityError("kafka_uuid_boundary_unavailable") from None
