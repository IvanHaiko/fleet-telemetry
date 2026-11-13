"""Real pinned reader integration with independently authored small binaries."""

import struct
from dataclasses import replace
from hashlib import sha256
from importlib.util import find_spec
from types import SimpleNamespace

import pytest

import ulog_reader
from fleet_telemetry import ClockAnchor, ULogSourceManifest
from ulog_integrity import InputIntegrityError, ULogExpectation
from ulog_reader import PARSER_VERSION, decode_ulog

pytestmark = [
    pytest.mark.ulog,
    pytest.mark.skipif(
        find_spec("pyulog") is None or find_spec("numpy") is None,
        reason="Install the pinned ulog extra for reader integration tests.",
    ),
]

DEFINITION = (
    "battery_status:uint64_t timestamp;float voltage_v;float current_a;"
    "float remaining;bool connected;uint8_t source;"
)


def packet(kind: str, payload: bytes) -> bytes:
    return struct.pack("<HB", len(payload), ord(kind)) + payload


def authored_log(
    *,
    definition: str = DEFINITION,
    connected: int = 0,
    decreasing: bool = False,
    second_stream: bool = False,
    firmware: str | None = None,
) -> bytes:
    data = b"ULog\x01\x12\x35\x01" + struct.pack("<Q", 0)
    data += packet("B", bytes(40)) + packet("F", definition.encode())
    if firmware is not None:
        key = b"char[40] ver_sw"
        data += packet("I", bytes([len(key)]) + key + firmware.encode())
    data += packet("A", struct.pack("<BH", 0, 42) + b"battery_status")
    if second_stream:
        data += packet("A", struct.pack("<BH", 1, 43) + b"battery_status")
    for index, voltage in enumerate((12.5, 0.0, 12.75)):
        time = 1000000 + index
        if decreasing and index == 1:
            time = 999999
        data += packet(
            "D", struct.pack("<HQfffBB", 42, time, voltage, -1.0, 0.5, connected, 0)
        )
        if second_stream:
            data += packet(
                "D", struct.pack("<HQfffBB", 43, time, 12.0, 4.0, 0.25, 1, 0)
            )
    return data


def expectation(data: bytes) -> ULogExpectation:
    return ULogExpectation("sha256:" + sha256(data).hexdigest(), len(data))


def manifest(data: bytes, definition: str = DEFINITION) -> ULogSourceManifest:
    return ULogSourceManifest(
        source_manifest_id="authored-binary-v1",
        source_log_id=expectation(data).source_log_id,
        vehicle_id="authored-vehicle",
        source_stream="battery_status:0",
        native_timestamp_min_us=0,
        native_timestamp_max_us=2000000,
        clock_anchor=ClockAnchor(0, "2026-01-01T00:00:00.000000Z"),
        source_reference="authored-binary-fixture-v1",
        retrieved_at="2026-10-19T00:00:00.000000Z",
        license_evidence="Project-authored independent synthetic bytes.",
        privacy_review="No identifiers or locations.",
        parser_version=PARSER_VERSION,
        vehicle_mapping_version="authored-vehicles-v1",
        producer_evidence="Authored policy cases, no real producer attribution.",
        field_definition_reference="sha256:" + sha256(definition.encode()).hexdigest(),
        source_type="synthetic",
        privacy_classification="synthetic",
    )


def test_real_reader_preserves_all_original_ordinals_and_python_types() -> None:
    data = authored_log(second_stream=True)
    first_subscription = packet("A", struct.pack("<BH", 0, 42) + b"battery_status")
    formats = packet("F", b"unrelated:uint64_t timestamp;child[2] samples;")
    formats += packet("F", b"child:float value;uint8_t[4] _padding0;")
    data = data.replace(first_subscription, formats + first_subscription, 1)
    data += packet("A", struct.pack("<BH", 0, 44) + b"unrelated")
    data += packet("D", struct.pack("<HQ", 44, 1) + bytes(16))
    data += packet("M", b"\x00\x0cchar[1] notea")
    data += packet("M", b"\x01\x0cchar[0] note")
    data += packet("L", b"6" + bytes(8) + b"authored")
    data += packet("S", bytes.fromhex("2f731320250cbb12"))
    result = decode_ulog(data, expectation(data), manifest(data))
    assert [row.source_record_index for row in result.records] == [0, 1, 2]
    assert result.records[1].native_record["voltage_v"] == 0.0
    assert result.records[1].native_record["connected"] is False
    assert type(result.records[0].native_record["timestamp"]) is int
    assert type(result.records[0].native_record["current_a"]) is float
    assert len(result.inspection.streams) == 3
    again = decode_ulog(data, expectation(data), manifest(data))
    assert result == again
    with pytest.raises(InputIntegrityError, match="invalid_sync_message"):
        decode_ulog(
            data[:-1] + b"\x00",
            expectation(data[:-1] + b"\x00"),
            manifest(data[:-1] + b"\x00"),
        )
    with pytest.raises(TypeError):
        result.records[0].native_record["source"] = 1  # type: ignore[index]


@pytest.mark.parametrize("connected", [2, 127, 128, 255])
def test_invalid_native_boolean_rejects_entire_source(connected: int) -> None:
    data = authored_log(connected=connected)
    with pytest.raises(InputIntegrityError, match="invalid_native_bool"):
        decode_ulog(data, expectation(data), manifest(data))


def test_decreasing_native_timestamp_rejects_entire_source() -> None:
    data = authored_log(decreasing=True)
    with pytest.raises(InputIntegrityError, match="decreasing_timestamp"):
        decode_ulog(data, expectation(data), manifest(data))


def test_equal_timestamps_preserve_distinct_native_ordinals() -> None:
    data = authored_log()
    data = data.replace(struct.pack("<Q", 1000001), struct.pack("<Q", 1000000))
    result = decode_ulog(data, expectation(data), manifest(data))
    assert [row.source_record_index for row in result.records] == [0, 1, 2]
    assert result.records[0].native_record["timestamp"] == 1000000
    assert result.records[1].native_record["timestamp"] == 1000000


def test_empty_selected_stream_has_explicit_disposition() -> None:
    data = authored_log()[:-81]
    with pytest.raises(InputIntegrityError, match="missing_selected_stream"):
        decode_ulog(data, expectation(data), manifest(data))


@pytest.mark.parametrize(
    "definition",
    [
        DEFINITION.replace("bool connected", "uint8_t connected"),
        DEFINITION.replace("uint64_t timestamp", "int64_t timestamp"),
        DEFINITION.replace("float voltage_v", "int32_t voltage_v"),
    ],
)
def test_same_width_wrong_embedded_types_are_rejected(definition: str) -> None:
    data = authored_log(definition=definition)
    with pytest.raises(InputIntegrityError, match="unsupported_battery_schema"):
        decode_ulog(data, expectation(data), manifest(data, definition))


def test_complete_definition_digest_must_match_manifest() -> None:
    data = authored_log()
    changed = replace(manifest(data), field_definition_reference="sha256:" + "0" * 64)
    with pytest.raises(InputIntegrityError, match="field_definition_mismatch"):
        decode_ulog(data, expectation(data), changed)


def test_sample_time_definition_is_rejected_even_when_digest_matches() -> None:
    definition = DEFINITION.replace(
        "timestamp;", "timestamp;uint64_t timestamp_sample;"
    )
    # There is no need for data rows: profile rejection precedes upstream parsing.
    data = authored_log(definition=definition)
    # Match the wider definition by adding eight bytes to each D frame.
    cursor = 16
    parts = [data[:cursor]]
    while cursor < len(data):
        size, kind = struct.unpack_from("<HB", data, cursor)
        body = data[cursor + 3 : cursor + 3 + size]
        if kind == ord("D"):
            body = body[:10] + bytes(8) + body[10:]
        parts.append(packet(chr(kind), body))
        cursor += 3 + size
    data = b"".join(parts)
    with pytest.raises(InputIntegrityError, match="unsupported_sample_timestamp"):
        decode_ulog(data, expectation(data), manifest(data, definition))


@pytest.mark.parametrize("tail", [b"\x01", b"\x01\x00", b"\x04\x00D\x00"])
def test_truncated_tail_fails_before_loading_reader(
    tail: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden() -> object:
        pytest.fail("upstream reader invoked before complete framing")

    monkeypatch.setattr(ulog_reader, "_load_reader", forbidden)
    data = authored_log() + tail
    with pytest.raises(InputIntegrityError):
        decode_ulog(data, expectation(data), manifest(data))


def test_clean_boundary_cut_is_detected_against_registered_expectation() -> None:
    complete = authored_log()
    with pytest.raises(InputIntegrityError):
        decode_ulog(complete[:-27], expectation(complete), manifest(complete))


def test_unknown_flags_reject_before_decoding() -> None:
    data = bytearray(authored_log())
    data[27] = 2
    modified = bytes(data)
    with pytest.raises(InputIntegrityError):
        decode_ulog(modified, expectation(modified), manifest(modified))


@pytest.mark.parametrize("firmware", [None, "0" * 40])
def test_real_source_requires_matching_embedded_firmware(firmware: str | None) -> None:
    data = authored_log(firmware=firmware)
    real = replace(
        manifest(data), source_type="ulog", privacy_classification="restricted"
    )
    with pytest.raises(InputIntegrityError, match="firmware_metadata_mismatch"):
        decode_ulog(data, expectation(data), real)


def test_matching_embedded_firmware_does_not_replace_caller_attestation() -> None:
    from fleet_telemetry import ULOG_FIRMWARE

    data = authored_log(firmware=ULOG_FIRMWARE)
    real = replace(
        manifest(data), source_type="ulog", privacy_classification="restricted"
    )
    assert len(decode_ulog(data, expectation(data), real).records) == 3
    missing = replace(real, producer_evidence=" ")
    with pytest.raises(InputIntegrityError, match="missing_producer_attestation"):
        decode_ulog(data, expectation(data), missing)


def test_native_import_failure_has_safe_disposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(name: str) -> object:
        raise OSError("PRIVATE PATH AND PAYLOAD")

    monkeypatch.setattr(ulog_reader, "import_module", unavailable)
    data = authored_log()
    with pytest.raises(
        InputIntegrityError, match="reader_initialization_failure"
    ) as err:
        decode_ulog(data, expectation(data), manifest(data))
    assert "PRIVATE" not in str(err.value)


def test_unselected_stream_must_also_reconcile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = authored_log(second_stream=True)
    real_constructor = ulog_reader._load_reader()

    def missing_other_stream(*args: object, **kwargs: object) -> object:
        parsed = real_constructor(args[0], disable_str_exceptions=False)  # type: ignore[arg-type]
        return SimpleNamespace(
            file_corruption=False,
            data_list=[
                dataset for dataset in parsed.data_list if dataset.multi_id == 0
            ],
        )

    monkeypatch.setattr(ulog_reader, "_load_reader", lambda: missing_other_stream)
    with pytest.raises(InputIntegrityError, match="reader_stream_mismatch"):
        decode_ulog(data, expectation(data), manifest(data))


def test_reader_version_and_namespace_are_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = authored_log()
    monkeypatch.setattr(ulog_reader, "version", lambda name: "0.0.0")
    with pytest.raises(InputIntegrityError, match="unsupported_reader_version"):
        decode_ulog(data, expectation(data), manifest(data))
    monkeypatch.setattr(
        ulog_reader, "version", lambda name: "1.2.2" if name == "pyulog" else "2.3.5"
    )
    monkeypatch.setattr(
        ulog_reader, "import_module", lambda name: SimpleNamespace(ULog=lambda: None)
    )
    with pytest.raises(InputIntegrityError, match="unsupported_reader_namespace"):
        decode_ulog(data, expectation(data), manifest(data))


@pytest.mark.parametrize(
    "fault", ["exception", "corruption", "missing_stream", "count"]
)
def test_upstream_faults_fail_atomically_and_hide_diagnostics(
    fault: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    data = authored_log()
    real_constructor = ulog_reader._load_reader()

    def faulty(*args: object, **kwargs: object) -> object:
        print("PRIVATE NATIVE PAYLOAD")
        if fault == "exception":
            raise ValueError("PRIVATE NATIVE PAYLOAD")
        parsed = real_constructor(args[0], disable_str_exceptions=False)  # type: ignore[arg-type]
        if fault == "corruption":
            return SimpleNamespace(file_corruption=True)
        if fault == "missing_stream":
            return SimpleNamespace(file_corruption=False, data_list=[])
        dataset = parsed.data_list[0]
        return SimpleNamespace(
            file_corruption=False,
            data_list=[
                SimpleNamespace(name=dataset.name, multi_id=dataset.multi_id, data={})
            ],
        )

    monkeypatch.setattr(ulog_reader, "_load_reader", lambda: faulty)
    with pytest.raises(InputIntegrityError) as raised:
        decode_ulog(data, expectation(data), manifest(data))
    assert "PRIVATE" not in str(raised.value)
    assert "PRIVATE" not in capsys.readouterr().out
