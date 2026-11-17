"""Stream positions, ordinals and loss evidence retained by ULog inspection."""

import struct
from dataclasses import FrozenInstanceError

import pytest
from ulog_binary import (
    FIRMWARE_COMMIT,
    expectation,
    info,
    packet,
    synthetic_log,
    synthetic_parts,
)

from ulog_integrity import inspect_ulog


def test_inspection_retains_exact_original_stream_positions() -> None:
    prefix, frames = synthetic_parts()
    data = prefix + b"".join(frames)
    receipt = expectation(data)
    inspection = inspect_ulog(data, receipt)
    assert inspection.source_log_id == receipt.source_log_id
    assert inspection.size_bytes == len(data)
    assert inspection.firmware_commit == FIRMWARE_COMMIT
    assert inspection.dropout_count == inspection.dropout_duration_ms == 0
    (stream,) = inspection.streams
    assert (stream.name, stream.multi_id, stream.msg_id) == ("battery_status", 0, 42)
    assert stream.record_offsets == (
        len(prefix),
        len(prefix) + len(frames[0]),
        len(prefix) + len(frames[0]) + len(frames[1]),
    )
    assert stream.payload_sizes == (22, 22, 22)
    assert inspection.definitions == (
        (
            "battery_status",
            "battery_status:uint64_t timestamp;float voltage_v;float current_a;"
            "float remaining;bool connected;uint8_t source;",
        ),
    )
    assert inspect_ulog(data, receipt) == inspection
    with pytest.raises(FrozenInstanceError):
        inspection.size_bytes = 0  # type: ignore[misc]


def test_every_stream_and_invalid_value_still_has_an_ordinal() -> None:
    prefix, frames = synthetic_parts(invalid_bool=True)
    second = packet("A", struct.pack("<BH", 1, 43) + b"battery_status")
    second_data = packet("D", struct.pack("<H", 43) + frames[0][5:])
    data = prefix + second + frames[0] + second_data + frames[1] + frames[2]
    streams = inspect_ulog(data, expectation(data)).streams
    assert [(s.multi_id, len(s.record_offsets)) for s in streams] == [(0, 3), (1, 1)]
    assert streams[0].record_offsets[1] > streams[1].record_offsets[0]


def test_dropout_marks_are_retained_as_loss_evidence() -> None:
    data = synthetic_log() + packet("O", struct.pack("<H", 123))
    data += packet("O", struct.pack("<H", 456))
    data += packet("M", b"\x00" + info("char[1]", "note", b"a")[3:])
    data += packet("M", b"\x01" + info("char[2]", "note", b"bc")[3:])
    data += packet("M", b"\x01" + info("char[0]", "note", b"")[3:])
    data += packet("L", b"6" + struct.pack("<Q", 1) + b"authored")
    data += packet("S", bytes.fromhex("2f731320250cbb12"))
    result = inspect_ulog(data, expectation(data))
    assert (result.dropout_count, result.dropout_duration_ms) == (2, 579)
    assert len(result.streams[0].record_offsets) == 3
