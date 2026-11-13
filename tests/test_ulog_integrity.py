"""Whole-input integrity invariants on independently authored tiny binaries."""

import struct
from dataclasses import FrozenInstanceError

import pytest
from ulog_binary import (
    FIRMWARE_COMMIT,
    expectation,
    header,
    info,
    packet,
    synthetic_log,
    synthetic_parts,
)

import ulog_integrity
from ulog_integrity import (
    MAX_INPUT_BYTES,
    MAX_RECORDS,
    InputIntegrityError,
    ULogExpectation,
    inspect_ulog,
)


def rejected(data: bytes, reason: str) -> InputIntegrityError:
    with pytest.raises(InputIntegrityError) as caught:
        inspect_ulog(data, expectation(data))
    assert caught.value.reason == reason
    return caught.value


def definition_log(definition: bytes, payload: bytes = b"", msg_id: int = 7) -> bytes:
    name = definition.split(b":")[0]
    prefix = header() + packet("B", bytes(40)) + packet("F", definition)
    prefix += packet("A", struct.pack("<BH", 0, msg_id) + name)
    return prefix + packet("D", struct.pack("<H", msg_id) + payload)


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


@pytest.mark.parametrize("registered_key", ["F09_SOURCE_ID", "F01_SOURCE_ID"])
def test_registered_extended_messages_are_scoped_and_validated(
    monkeypatch: pytest.MonkeyPatch,
    registered_key: str,
) -> None:
    flags = bytearray(40)
    flags[0] = 1
    data = synthetic_log().replace(packet("B", bytes(40)), packet("B", bytes(flags)))
    parameter = packet("Q", b"\x01" + info("int32_t", "p", bytes(4))[3:])
    binary = packet("M", b"\x00" + info("uint8_t[2]", "note", b"ab")[3:])
    data += parameter + binary
    rejected(data, "unsupported_compatibility_flags")
    monkeypatch.setattr(ulog_integrity, registered_key, expectation(data).source_log_id)
    assert len(inspect_ulog(data, expectation(data)).streams[0].record_offsets) == 3

    invalid = data.replace(parameter, packet("Q", b"\x00" + parameter[4:]))
    monkeypatch.setattr(
        ulog_integrity, registered_key, expectation(invalid).source_log_id
    )
    rejected(invalid, "invalid_default_parameter")


def test_optional_firmware_metadata_is_not_invented() -> None:
    data = synthetic_log(firmware_commit=None)
    assert inspect_ulog(data, expectation(data)).firmware_commit is None


@pytest.mark.parametrize("length", [0, 1, 7, 8, 15])
def test_short_file_header_fails(length: int) -> None:
    rejected(header()[:length], "truncated_file_header")


def test_magic_and_version_are_checked() -> None:
    rejected(b"X" + header()[1:], "invalid_magic")
    rejected(header()[:7] + b"\x02" + header()[8:], "unsupported_file_version")


def test_mutable_byte_buffer_is_not_accepted_as_registered_snapshot() -> None:
    data = synthetic_log()
    with pytest.raises(InputIntegrityError, match="invalid_input_type"):
        inspect_ulog(bytearray(data), expectation(data))


@pytest.mark.parametrize("tail", [b"\x01", b"\x01\x00"])
def test_incomplete_tail_header_cannot_be_silently_discarded(tail: bytes) -> None:
    data = synthetic_log() + tail
    assert rejected(data, "truncated_message_header").offset == len(data) - len(tail)


@pytest.mark.parametrize("missing", [1, 5, 22])
def test_incomplete_tail_payload_cannot_be_silently_discarded(missing: int) -> None:
    prefix, frames = synthetic_parts()
    data = prefix + b"".join(frames)
    error = rejected(data[:-missing], "truncated_message_payload")
    assert error.offset == len(prefix) + len(frames[0]) + len(frames[1])


def test_clean_frame_boundary_cut_requires_registered_source_receipt() -> None:
    prefix, frames = synthetic_parts()
    complete = prefix + b"".join(frames)
    cut = prefix + b"".join(frames[:2])
    with pytest.raises(InputIntegrityError, match="source_size_mismatch"):
        inspect_ulog(cut, expectation(complete))
    # Framing alone cannot detect acquisition loss before registration.
    assert len(inspect_ulog(cut, expectation(cut)).streams[0].record_offsets) == 2


def test_checksum_precedes_any_content_interpretation() -> None:
    original = synthetic_log()
    altered = b"X" + original[1:]
    with pytest.raises(InputIntegrityError) as caught:
        inspect_ulog(altered, expectation(original))
    assert caught.value.reason == "source_checksum_mismatch"
    assert caught.value.offset is None


@pytest.mark.parametrize("wrong_size", [-1, True, MAX_INPUT_BYTES + 1])
def test_invalid_expected_size(wrong_size: int) -> None:
    data = synthetic_log()
    with pytest.raises(InputIntegrityError, match="invalid_expectation"):
        inspect_ulog(data, ULogExpectation(expectation(data).source_log_id, wrong_size))


@pytest.mark.parametrize("checksum", ["", "0" * 64, "sha256:" + "A" * 64])
def test_invalid_expected_checksum(checksum: str) -> None:
    data = synthetic_log()
    with pytest.raises(InputIntegrityError, match="invalid_expectation"):
        inspect_ulog(data, ULogExpectation(checksum, len(data)))


def test_input_byte_limit_precedes_hashing_and_framing() -> None:
    data = bytes(MAX_INPUT_BYTES + 1)
    with pytest.raises(InputIntegrityError, match="input_size_limit"):
        inspect_ulog(data, ULogExpectation("invalid", 0))


def test_frame_limit_bounds_even_metadata_only_input() -> None:
    marker = packet("O", b"\x01\x00")
    within = header() + marker * MAX_RECORDS
    assert inspect_ulog(within, expectation(within)).dropout_count == MAX_RECORDS
    rejected(within + marker, "record_count_limit")


@pytest.mark.parametrize("delta", [-1, 1])
def test_wrong_size_middle_data_frame_fails_whole_input(delta: int) -> None:
    prefix, frames = synthetic_parts()
    payload = frames[1][3:]
    payload = payload[:-1] if delta < 0 else payload + b"\x00"
    data = prefix + frames[0] + packet("D", payload) + frames[2]
    error = rejected(data, "data_size_mismatch")
    assert error.offset == len(prefix) + len(frames[0])


@pytest.mark.parametrize(
    "flag_offset,reason",
    [
        (0, "unsupported_compatibility_flags"),
        (8, "unsupported_incompatibility_flags"),
        (9, "unsupported_incompatibility_flags"),
        (16, "unsupported_appended_sections"),
        (39, "unsupported_appended_sections"),
    ],
)
def test_unknown_flags_and_appended_sections_fail(
    flag_offset: int, reason: str
) -> None:
    flags = bytearray(40)
    flags[flag_offset] = 1
    rejected(header() + packet("B", bytes(flags)), reason)


def test_flags_size_position_and_duplication_fail() -> None:
    rejected(header() + packet("B", bytes(41)), "unsupported_flags_size")
    rejected(synthetic_log() + packet("B", bytes(40)), "invalid_flags_position")


@pytest.mark.parametrize("kind", ["?", "Q", "C", "\x00"])
def test_unknown_or_unsupported_message_kinds_are_visible(kind: str) -> None:
    rejected(
        synthetic_log() + packet(kind, b"private-content"), "unsupported_message_kind"
    )


def test_subscription_reuse_and_removal_fail() -> None:
    data = synthetic_log()
    rejected(
        data + packet("A", struct.pack("<BH", 1, 42) + b"battery_status"),
        "subscription_reuse",
    )
    rejected(
        data + packet("A", struct.pack("<BH", 0, 99) + b"battery_status"),
        "subscription_reuse",
    )
    rejected(
        data + packet("R", struct.pack("<H", 42)), "unsupported_subscription_removal"
    )


def test_unregistered_and_incomplete_data_messages_fail() -> None:
    rejected(header() + packet("D", b"\x01"), "invalid_data_message")
    rejected(header() + packet("D", b"\x01\x00"), "unregistered_data_message")


def test_invalid_and_undefined_subscriptions_fail() -> None:
    rejected(header() + packet("A", b"\x00\x01"), "invalid_subscription")
    rejected(header() + packet("A", b"\x00\x01\x00unknown"), "undefined_subscription")


def test_definition_reuse_and_late_definition_fail() -> None:
    definition = packet("F", b"sensor:uint64_t timestamp;")
    rejected(header() + definition + definition, "definition_reuse")
    rejected(synthetic_log() + definition, "late_definition")
    logging = packet("L", b"6" + bytes(8))
    rejected(header() + logging + definition, "late_definition")


@pytest.mark.parametrize(
    "body,reason",
    [
        (b"sensor:uint64_t timestamp", "invalid_definition"),
        (b"sensor:uint64_t timestamp;float timestamp;", "duplicate_field"),
        (b"sensor:unknown field;", "undefined_nested_definition"),
        (b"sensor:uint8_t[0] field;", "unsupported_field_type"),
        (b"sensor:uint8_t[100000] field;", "unsupported_array_size"),
        (b"sensor:uint64_t[65533] field;", "unsupported_array_size"),
        (
            b"sensor:uint64_t[4096] one;uint64_t[4096] two;",
            "unsupported_definition_size",
        ),
        (b"float:uint8_t value;", "invalid_definition"),
        (b"sensor:uint8_t " + b"x" * 129 + b";", "definition_identifier_limit"),
        (b"sensor:uint8_t x;uint16_t _padding0;", "unsupported_padding"),
        (b"sensor:uint8_t[3] _padding0;", "invalid_definition"),
        (b"sensor:uint8_t x;\xff", "invalid_utf8"),
        (b"sensor:uint8_t x;\x00", "invalid_definition"),
        (b"sensor:uint8_t  x;", "invalid_definition"),
    ],
)
def test_invalid_or_unsupported_definitions_fail(body: bytes, reason: str) -> None:
    rejected(header() + packet("F", body), reason)


def test_huge_array_count_has_a_safe_error_instead_of_integer_conversion_failure() -> (
    None
):
    body = b"sensor:uint8_t[" + b"9" * 5_000 + b"] values;"
    error = rejected(header() + packet("F", body), "unsupported_array_size")
    assert len(str(error)) < 100


def test_invalid_utf8_subscription_and_info_keys_have_safe_errors() -> None:
    rejected(header() + packet("A", b"\x00\x01\x00\xff"), "invalid_utf8")
    rejected(header() + packet("I", b"\x01\xff\x00"), "invalid_utf8")


@pytest.mark.parametrize("padding_bytes", [0, 3])
def test_complete_terminal_padding_can_be_present_or_omitted(
    padding_bytes: int,
) -> None:
    body = b"sensor:uint64_t timestamp;uint8_t[3] _padding0;"
    data = definition_log(body, struct.pack("<Q", 1) + bytes(padding_bytes))
    result = inspect_ulog(data, expectation(data))
    assert result.streams[0].payload_sizes == (8 + padding_bytes,)


def test_partial_terminal_padding_is_explicitly_rejected() -> None:
    data = definition_log(b"sensor:uint64_t timestamp;uint8_t[3] _padding0;", bytes(9))
    rejected(data, "data_size_mismatch")


def test_nonterminal_padding_and_flat_array_have_declared_widths() -> None:
    body = b"sensor:uint64_t timestamp;uint8_t[3] _padding0;float[2] values;"
    data = definition_log(body, bytes(19))
    assert inspect_ulog(data, expectation(data)).streams[0].payload_sizes == (19,)
    rejected(definition_log(body, bytes(16)), "data_size_mismatch")


def test_nested_arrays_keep_embedded_padding_with_forward_references() -> None:
    parent = packet(
        "F", b"sensor:uint64_t timestamp;child[2] samples;uint8_t[2] _padding0;"
    )
    child = packet("F", b"child:float[2] values;uint8_t[3] _padding0;")
    prefix = (
        header() + parent + child + packet("A", struct.pack("<BH", 0, 7) + b"sensor")
    )
    # 8 + 2 * (8 + 3), with only the parent's own 2 padding bytes optional.
    for width in (30, 32):
        data = prefix + packet("D", struct.pack("<H", 7) + bytes(width))
        assert inspect_ulog(data, expectation(data)).streams[0].payload_sizes == (
            width,
        )
    for width in (24, 31):
        rejected(
            prefix + packet("D", struct.pack("<H", 7) + bytes(width)),
            "data_size_mismatch",
        )


def test_unused_circular_definitions_fail_before_any_reader() -> None:
    for definitions in ((b"a:a self;",), (b"a:b next;", b"b:a previous;")):
        rejected(
            header() + b"".join(packet("F", body) for body in definitions),
            "cyclic_definition",
        )


def test_definition_depth_limit_survives_cached_child_layouts() -> None:
    limit = ulog_integrity.MAX_NESTING_DEPTH
    bodies = [f"n{i}:n{i + 1} value;".encode() for i in range(limit)]
    leaf = f"n{limit}:uint8_t value;".encode()
    for order in (bodies + [leaf], [leaf] + list(reversed(bodies))):
        rejected(
            header() + b"".join(packet("F", body) for body in order),
            "definition_depth_limit",
        )
    within = header() + b"".join(packet("F", body) for body in bodies[1:] + [leaf])
    assert inspect_ulog(within, expectation(within)).streams == ()


def test_expanded_fields_bound_a_small_shared_definition_graph() -> None:
    leaf = packet("F", b"leaf:uint8_t[65] values;")
    graph = leaf + packet("F", b"parent:leaf[64] children;")
    rejected(header() + graph, "definition_expansion_limit")
    within = header() + leaf + packet("F", b"parent:leaf[63] children;")
    assert inspect_ulog(within, expectation(within)).streams == ()


def test_empty_subscriptions_still_consume_expansion_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ulog_integrity, "MAX_SUBSCRIBED_FIELDS", 8)
    prefix = header() + packet("F", b"sensor:uint32_t[4] values;")
    for index in range(2):
        prefix += packet("A", struct.pack("<BH", index, index) + b"sensor")
    assert len(inspect_ulog(prefix, expectation(prefix)).streams) == 2
    rejected(
        prefix + packet("A", struct.pack("<BH", 2, 2) + b"sensor"),
        "subscription_expansion_limit",
    )
    monkeypatch.setattr(ulog_integrity, "MAX_SUBSCRIBED_FIELDS", 100_000)
    monkeypatch.setattr(ulog_integrity, "MAX_EXPANDED_NAME_BYTES", 1000)
    prefix = header() + packet("F", b"child:uint8_t[10] values;")
    prefix += packet("F", b"sensor:child[2] a_long_parent_prefix;")
    prefix += packet("A", struct.pack("<BH", 0, 0) + b"sensor")
    assert len(inspect_ulog(prefix, expectation(prefix)).streams) == 1
    rejected(
        prefix + packet("A", struct.pack("<BH", 1, 1) + b"sensor"),
        "subscription_name_expansion_limit",
    )


@pytest.mark.parametrize(
    "kind,payload,reason",
    [
        ("M", b"\x02", "invalid_multi_info"),
        (
            "M",
            b"\x01" + info("char[1]", "note", b"a")[3:],
            "orphan_multi_info_continuation",
        ),
        (
            "M",
            b"\x00" + info("uint32_t", "note", bytes(4))[3:],
            "unsupported_multi_info_type",
        ),
        ("M", b"\x00" + info("char[2]", "note", b"a")[3:], "invalid_info_size"),
        ("L", bytes(8), "invalid_logging_message"),
        ("L", b"8" + bytes(8), "invalid_logging_message"),
        ("L", b"6" + bytes(8) + b"\xff", "invalid_utf8"),
        ("S", bytes(7), "invalid_sync_message"),
        ("S", bytes(8), "invalid_sync_message"),
    ],
)
def test_malformed_service_frames_fail_at_their_original_boundary(
    kind: str, payload: bytes, reason: str
) -> None:
    prefix = synthetic_log()
    assert rejected(prefix + packet(kind, payload), reason).offset == len(prefix)


def test_single_and_multi_metadata_namespaces_must_not_conflict() -> None:
    single = info("char[1]", "note", b"a")
    multiple = packet("M", b"\x00" + single[3:])
    for frames in (single + multiple, multiple + single):
        rejected(header() + frames, "metadata_namespace_conflict")


@pytest.mark.parametrize(
    "payload,reason",
    [
        (b"", "invalid_info"),
        (b"\xffprivate", "invalid_info"),
        (b"\x03bad", "invalid_info"),
        (b"\x0auint32_t x\x00", "invalid_info_size"),
    ],
)
def test_malformed_info_fails_without_exposing_strings(
    payload: bytes, reason: str
) -> None:
    error = rejected(header() + packet("I", payload), reason)
    assert "private" not in str(error)


def test_duplicate_and_wrong_firmware_metadata_fail() -> None:
    rejected(synthetic_log() + info("char[40]", "ver_sw", b"a" * 40), "metadata_reuse")
    rejected(
        header() + info("char[40]", "ver_sw", b"g" * 40),
        "unsupported_firmware_metadata",
    )


def test_scalar_metadata_and_parameter_widths_are_checked() -> None:
    data = header() + info("uint32_t", "scalar", struct.pack("<I", 42))
    parameter = info("float", "PARAM", struct.pack("<f", 1.0))
    data += packet("P", parameter[3:])
    assert inspect_ulog(data, expectation(data)).streams == ()


@pytest.mark.parametrize(
    "kind,value",
    [("int32_t", struct.pack("<i", -42)), ("float", struct.pack("<f", 1.25))],
)
def test_parameter_accepts_only_documented_scalar_types(
    kind: str, value: bytes
) -> None:
    message = info(kind, "PARAM", value)
    data = header() + packet("P", message[3:])
    assert inspect_ulog(data, expectation(data)).streams == ()


@pytest.mark.parametrize(
    "kind,value",
    [("char[3]", b"abc"), ("uint64_t", struct.pack("<Q", 42))],
)
def test_parameter_rejects_other_info_types(kind: str, value: bytes) -> None:
    message = info(kind, "PARAM", value)
    data = header() + packet("P", message[3:])
    error = rejected(data, "unsupported_parameter_type")
    assert error.offset == 16


def test_malformed_dropout_fails() -> None:
    rejected(synthetic_log() + packet("O", b"\x01"), "invalid_dropout_message")
