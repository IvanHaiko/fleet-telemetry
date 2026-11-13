"""Tiny authored ULog bytes, with no copied flight data or upstream fixtures."""

import struct
from hashlib import sha256

from ulog_integrity import ULogExpectation

FIRMWARE_COMMIT = "8583f1da30b63154d6ba0bc187d86135dfe33cf9"


def packet(kind: str, payload: bytes) -> bytes:
    return struct.pack("<HB", len(payload), ord(kind)) + payload


def header() -> bytes:
    return b"ULog\x01\x12\x35\x01" + struct.pack("<Q", 0)


def expectation(data: bytes) -> ULogExpectation:
    """Test-only receipt generation; production receipts must be external."""
    return ULogExpectation("sha256:" + sha256(data).hexdigest(), len(data))


def info(kind: str, key: str, value: bytes) -> bytes:
    typed_key = (kind + " " + key).encode("ascii")
    return packet("I", bytes([len(typed_key)]) + typed_key + value)


def synthetic_parts(
    connected_type: str = "bool",
    invalid_bool: bool = False,
    decreasing_time: bool = False,
    firmware_commit: str | None = FIRMWARE_COMMIT,
) -> tuple[bytes, list[bytes]]:
    prefix = header() + packet("B", bytes(40))
    if firmware_commit is not None:
        prefix += info("char[40]", "ver_sw", firmware_commit.encode("ascii"))
    definition = (
        "battery_status:uint64_t timestamp;float voltage_v;float current_a;"
        f"float remaining;{connected_type} connected;uint8_t source;"
    ).encode("ascii")
    prefix += packet("F", definition)
    prefix += packet("A", struct.pack("<BH", 0, 42) + b"battery_status")
    times = [1_000_000, 999_999 if decreasing_time else 1_000_001, 1_000_002]
    values = [(12.5, 4.25, 0.5, 1), (0.0, -1.0, 0.5, 0), (12.75, 0.0, 0.5, 1)]
    frames = []
    for i, (voltage, current, remaining, connected) in enumerate(values):
        if invalid_bool and i == 1:
            connected = 2
        frames.append(
            packet(
                "D",
                struct.pack(
                    "<HQfffBB",
                    42,
                    times[i],
                    voltage,
                    current,
                    remaining,
                    connected,
                    0,
                ),
            )
        )
    return prefix, frames


def synthetic_log(
    connected_type: str = "bool",
    invalid_bool: bool = False,
    decreasing_time: bool = False,
    firmware_commit: str | None = FIRMWARE_COMMIT,
) -> bytes:
    prefix, frames = synthetic_parts(
        connected_type, invalid_bool, decreasing_time, firmware_commit
    )
    return prefix + b"".join(frames)
