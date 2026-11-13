"""Bounded whole-input framing checks before an upstream ULog parser runs.

This deliberately supports a conservative bounded-definition subset. It does not
decode telemetry values or infer completeness before source registration.
"""

import re
import struct
from dataclasses import dataclass, field
from hashlib import sha256

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_RECORDS = 100_000
F09_SOURCE_ID = (
    "sha256:30f1d0f89f6eed0853cdf78a04eced1c5f56afd047541594158a76df74b1a1a0"
)
F01_SOURCE_ID = (
    "sha256:36e54ff7c13619f96c9fb56a74c9fb3efb0650600881412a9363f00a65d7141b"
)
F09_MAX_INPUT_BYTES = 128 * 1024 * 1024
F09_MAX_RECORDS = 2_500_000
MAX_NESTING_DEPTH = 32
MAX_EXPANDED_FIELDS = 4096
MAX_SUBSCRIBED_FIELDS = 100_000
MAX_DEFINITION_NAME_LENGTH = 128
MAX_EXPANDED_NAME_BYTES = 8 * 1024 * 1024
_SYNC_MAGIC = b"\x2f\x73\x13\x20\x25\x0c\xbb\x12"
_MAGIC = b"ULog\x01\x12\x35"
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", re.ASCII)
_TYPE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[([1-9][0-9]*)\])?", re.ASCII)
_CHECKSUM = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)
_WIDTHS = {
    "int8_t": 1,
    "uint8_t": 1,
    "int16_t": 2,
    "uint16_t": 2,
    "int32_t": 4,
    "uint32_t": 4,
    "int64_t": 8,
    "uint64_t": 8,
    "float": 4,
    "double": 8,
    "bool": 1,
    "char": 1,
}


class InputIntegrityError(ValueError):
    """A safe disposition containing no source strings or telemetry values."""

    def __init__(self, reason: str, offset: int | None = None) -> None:
        self.reason = reason
        self.offset = offset
        location = "" if offset is None else f" at byte {offset}"
        super().__init__(f"ULog input rejected: {reason}{location}")


@dataclass(frozen=True)
class ULogExpectation:
    """Trusted external source receipt; never generate it from untrusted input."""

    source_log_id: str
    size_bytes: int


@dataclass(frozen=True)
class StreamFraming:
    name: str
    multi_id: int
    msg_id: int
    record_offsets: tuple[int, ...]
    payload_sizes: tuple[int, ...]


@dataclass(frozen=True)
class ULogInspection:
    source_log_id: str
    size_bytes: int
    streams: tuple[StreamFraming, ...]
    definitions: tuple[tuple[str, str], ...]
    firmware_commit: str | None
    dropout_count: int
    dropout_duration_ms: int


@dataclass
class _Subscription:
    name: str
    multi_id: int
    msg_id: int
    sizes: tuple[int, ...]
    offsets: list[int] = field(default_factory=list)
    payload_sizes: list[int] = field(default_factory=list)


def _text(data: bytes, offset: int) -> str:
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise InputIntegrityError("invalid_utf8", offset) from None


def _type_spec(kind: str, offset: int) -> tuple[str, int]:
    match = _TYPE.fullmatch(kind)
    if match is None:
        raise InputIntegrityError("unsupported_field_type", offset)
    primitive, count_text = match.groups()
    if len(primitive) > MAX_DEFINITION_NAME_LENGTH:
        raise InputIntegrityError("definition_identifier_limit", offset)
    # Bound conversion too: Python limits huge integer strings, but the error
    # must remain our safe, explicit unsupported-input disposition.
    if count_text is not None and len(count_text) > 5:
        raise InputIntegrityError("unsupported_array_size", offset)
    count = 1 if count_text is None else int(count_text)
    if count > 65_533:
        raise InputIntegrityError("unsupported_array_size", offset)
    return primitive, count


def _type_width(kind: str, offset: int) -> tuple[str, int]:
    primitive, count = _type_spec(kind, offset)
    if primitive not in _WIDTHS:
        raise InputIntegrityError("unsupported_nested_definition", offset)
    width = count * _WIDTHS[primitive]
    if width > 65_533:
        raise InputIntegrityError("unsupported_array_size", offset)
    return primitive, width


@dataclass(frozen=True)
class _FormatField:
    kind: str
    count: int
    name: str


@dataclass(frozen=True)
class _Definition:
    text: str
    fields: tuple[_FormatField, ...]
    offset: int


@dataclass(frozen=True)
class _Layout:
    size: int
    padding: int
    expanded_fields: int
    depth: int
    name_bytes: int

    @property
    def sizes(self) -> tuple[int, ...]:
        return (self.size - self.padding, self.size) if self.padding else (self.size,)


def _definition(data: bytes, offset: int) -> tuple[str, _Definition]:
    text = _text(data, offset)
    name, separator, fields_text = text.partition(":")
    if not separator or _IDENTIFIER.fullmatch(name) is None or name in _WIDTHS:
        raise InputIntegrityError("invalid_definition", offset)
    if len(name) > MAX_DEFINITION_NAME_LENGTH:
        raise InputIntegrityError("definition_identifier_limit", offset)
    if not fields_text.endswith(";"):
        raise InputIntegrityError("invalid_definition", offset)
    fields = fields_text[:-1].split(";")
    seen: set[str] = set()
    parsed: list[_FormatField] = []
    for value in fields:
        parts = value.split(" ")
        if len(parts) != 2 or _IDENTIFIER.fullmatch(parts[1]) is None:
            raise InputIntegrityError("invalid_definition", offset)
        kind, field_name = parts
        if len(field_name) > MAX_DEFINITION_NAME_LENGTH:
            raise InputIntegrityError("definition_identifier_limit", offset)
        if field_name in seen:
            raise InputIntegrityError("duplicate_field", offset)
        seen.add(field_name)
        primitive, count = _type_spec(kind, offset)
        if primitive in _WIDTHS:
            _type_width(kind, offset)
        if field_name.startswith("_padding"):
            if primitive != "uint8_t":
                raise InputIntegrityError("unsupported_padding", offset)
        parsed.append(_FormatField(primitive, count, field_name))
    return name, _Definition(text, tuple(parsed), offset)


def _resolve_layouts(definitions: dict[str, _Definition]) -> dict[str, _Layout]:
    layouts: dict[str, _Layout] = {}
    active: set[str] = set()

    def resolve(name: str, reference_offset: int) -> _Layout:
        if name in active:
            raise InputIntegrityError("cyclic_definition", reference_offset)
        if name in layouts:
            return layouts[name]
        if name not in definitions:
            raise InputIntegrityError("undefined_nested_definition", reference_offset)
        definition = definitions[name]
        offset = definition.offset
        if len(active) >= MAX_NESTING_DEPTH:
            raise InputIntegrityError("definition_depth_limit", offset)
        active.add(name)
        total = padding = expanded = name_bytes = 0
        depth = 1
        for item in definition.fields:
            if item.kind in _WIDTHS:
                width, fields = _WIDTHS[item.kind], 1
                # Five-digit indices plus brackets bound every supported array.
                field_name_bytes = len(item.name) + 7
            else:
                child = resolve(item.kind, offset)
                width, fields = child.size, child.expanded_fields
                depth = max(depth, child.depth + 1)
                field_name_bytes = child.name_bytes + fields * (len(item.name) + 8)
            total += width * item.count
            expanded += fields * item.count
            name_bytes += field_name_bytes * item.count
            if total > 65_533:
                raise InputIntegrityError("unsupported_definition_size", offset)
            if expanded > MAX_EXPANDED_FIELDS:
                raise InputIntegrityError("definition_expansion_limit", offset)
            if depth > MAX_NESTING_DEPTH:
                raise InputIntegrityError("definition_depth_limit", offset)
            if name_bytes > MAX_EXPANDED_NAME_BYTES:
                raise InputIntegrityError("definition_name_expansion_limit", offset)
            padding = (
                padding + width * item.count if item.name.startswith("_padding") else 0
            )
        if total == padding:
            raise InputIntegrityError("invalid_definition", offset)
        active.remove(name)
        layouts[name] = _Layout(total, padding, expanded, depth, name_bytes)
        return layouts[name]

    for name, definition in definitions.items():
        resolve(name, definition.offset)
    return layouts


def _info(
    data: bytes, offset: int, *, allow_empty_char: bool = False
) -> tuple[str, str, bytes]:
    if not data or not 0 < data[0] < len(data):
        raise InputIntegrityError("invalid_info", offset)
    key_size = data[0]
    parts = _text(data[1 : 1 + key_size], offset).split(" ")
    if len(parts) != 2 or _IDENTIFIER.fullmatch(parts[1]) is None:
        raise InputIntegrityError("invalid_info", offset)
    kind, key = parts
    _, width = (
        ("char", 0)
        if allow_empty_char and kind == "char[0]"
        else _type_width(kind, offset)
    )
    value = data[1 + key_size :]
    if len(value) != width:
        raise InputIntegrityError("invalid_info_size", offset)
    if kind.startswith("char["):
        _text(value, offset)
    return kind, key, value


def inspect_ulog(data: bytes, expectation: ULogExpectation) -> ULogInspection:
    """Validate registered bytes and all frames before exposing stream ordinals.

    Supported messages: B, F, I, M, P, A, D, L, S and O. Flags must be zero;
    definitions must precede the data section, and subscription changes
    and duplicate metadata keys are unsupported. MAX_RECORDS bounds all frames,
    including metadata, so no unbounded indexing state can be accumulated.
    Terminal padding may be wholly omitted or wholly present, never partial.
    The exact registered F09 checksum has separate limits and admits the
    default-parameter flag and Q and byte-array M records under ADR-0041.
    Registered F01 admits those service frames under ADR-0044 with default limits.
    """
    if type(data) is not bytes:
        raise InputIntegrityError("invalid_input_type")
    f09 = expectation.source_log_id == F09_SOURCE_ID
    extended_service_frames = expectation.source_log_id in (
        F09_SOURCE_ID,
        F01_SOURCE_ID,
    )
    byte_limit = F09_MAX_INPUT_BYTES if f09 else MAX_INPUT_BYTES
    frame_limit = F09_MAX_RECORDS if f09 else MAX_RECORDS
    if len(data) > byte_limit:
        raise InputIntegrityError("input_size_limit")
    if (
        type(expectation.size_bytes) is not int
        or not 0 <= expectation.size_bytes <= byte_limit
        or not isinstance(expectation.source_log_id, str)
        or _CHECKSUM.fullmatch(expectation.source_log_id) is None
    ):
        raise InputIntegrityError("invalid_expectation")
    if len(data) != expectation.size_bytes:
        raise InputIntegrityError("source_size_mismatch")
    if "sha256:" + sha256(data).hexdigest() != expectation.source_log_id:
        raise InputIntegrityError("source_checksum_mismatch")
    if len(data) < 16:
        raise InputIntegrityError("truncated_file_header", 0)
    if data[:7] != _MAGIC:
        raise InputIntegrityError("invalid_magic", 0)
    if data[7] != 1:
        raise InputIntegrityError("unsupported_file_version", 7)

    definitions: dict[str, _Definition] = {}
    layouts: dict[str, _Layout] | None = None
    subscribed_fields = 0
    subscribed_name_bytes = 0
    subscriptions: dict[int, _Subscription] = {}
    stream_keys: set[tuple[str, int]] = set()
    metadata_keys: set[str] = set()
    multi_keys: set[str] = set()
    firmware: str | None = None
    dropout_count = 0
    dropout_duration = 0
    flags_seen = False
    frame_count = 0
    offset = 16
    while offset < len(data):
        frame_count += 1
        if frame_count > frame_limit:
            raise InputIntegrityError("record_count_limit", offset)
        if len(data) - offset < 3:
            raise InputIntegrityError("truncated_message_header", offset)
        size, kind = struct.unpack_from("<HB", data, offset)
        end = offset + 3 + size
        if end > len(data):
            raise InputIntegrityError("truncated_message_payload", offset)
        payload = data[offset + 3 : end]
        if kind == ord("B"):
            if offset != 16 or flags_seen:
                raise InputIntegrityError("invalid_flags_position", offset)
            if size != 40:
                raise InputIntegrityError("unsupported_flags_size", offset)
            if any(payload[8:16]):
                raise InputIntegrityError("unsupported_incompatibility_flags", offset)
            if any(payload[16:]):
                raise InputIntegrityError("unsupported_appended_sections", offset)
            unsupported_compat = (
                bool(payload[0] & ~1 or any(payload[1:8]))
                if extended_service_frames
                else any(payload[:8])
            )
            if unsupported_compat:
                raise InputIntegrityError("unsupported_compatibility_flags", offset)
            flags_seen = True
        elif kind == ord("F"):
            if layouts is not None:
                raise InputIntegrityError("late_definition", offset)
            name, definition = _definition(payload, offset)
            if name in definitions:
                raise InputIntegrityError("definition_reuse", offset)
            definitions[name] = definition
        elif kind in (ord("I"), ord("P")):
            info_kind, key, value = _info(payload, offset)
            if kind == ord("P") and info_kind not in ("int32_t", "float"):
                raise InputIntegrityError("unsupported_parameter_type", offset)
            if kind == ord("I"):
                if key in multi_keys:
                    raise InputIntegrityError("metadata_namespace_conflict", offset)
                if key in metadata_keys:
                    raise InputIntegrityError("metadata_reuse", offset)
                metadata_keys.add(key)
                if key == "ver_sw":
                    decoded = _text(value, offset)
                    if (
                        info_kind != "char[40]"
                        or re.fullmatch(r"[0-9a-f]{40}", decoded, flags=re.ASCII)
                        is None
                    ):
                        raise InputIntegrityError(
                            "unsupported_firmware_metadata", offset
                        )
                    firmware = decoded
        elif kind == ord("Q") and extended_service_frames:
            if not payload or not 0 < payload[0] <= 3:
                raise InputIntegrityError("invalid_default_parameter", offset)
            info_kind, _, _ = _info(payload[1:], offset)
            if info_kind not in ("int32_t", "float"):
                raise InputIntegrityError("unsupported_parameter_type", offset)
        elif kind == ord("M"):
            if not payload or payload[0] not in (0, 1):
                raise InputIntegrityError("invalid_multi_info", offset)
            info_kind, key, _ = _info(payload[1:], offset, allow_empty_char=True)
            if not info_kind.startswith("char[") and not (
                extended_service_frames and info_kind.startswith("uint8_t[")
            ):
                raise InputIntegrityError("unsupported_multi_info_type", offset)
            if key in metadata_keys:
                raise InputIntegrityError("metadata_namespace_conflict", offset)
            if payload[0] and key not in multi_keys:
                raise InputIntegrityError("orphan_multi_info_continuation", offset)
            multi_keys.add(key)
        elif kind == ord("A"):
            if size < 4:
                raise InputIntegrityError("invalid_subscription", offset)
            multi_id, msg_id = struct.unpack_from("<BH", payload)
            name = _text(payload[3:], offset)
            if _IDENTIFIER.fullmatch(name) is None or name not in definitions:
                raise InputIntegrityError("undefined_subscription", offset)
            if msg_id in subscriptions or (name, multi_id) in stream_keys:
                raise InputIntegrityError("subscription_reuse", offset)
            if layouts is None:
                layouts = _resolve_layouts(definitions)
            layout = layouts[name]
            subscribed_fields += layout.expanded_fields
            subscribed_name_bytes += layout.name_bytes
            if subscribed_fields > MAX_SUBSCRIBED_FIELDS:
                raise InputIntegrityError("subscription_expansion_limit", offset)
            if subscribed_name_bytes > MAX_EXPANDED_NAME_BYTES:
                raise InputIntegrityError("subscription_name_expansion_limit", offset)
            subscriptions[msg_id] = _Subscription(name, multi_id, msg_id, layout.sizes)
            stream_keys.add((name, multi_id))
        elif kind == ord("L"):
            if size < 9 or not ord("0") <= payload[0] <= ord("7"):
                raise InputIntegrityError("invalid_logging_message", offset)
            _text(payload[9:], offset)
            if layouts is None:
                layouts = _resolve_layouts(definitions)
        elif kind == ord("S"):
            if payload != _SYNC_MAGIC:
                raise InputIntegrityError("invalid_sync_message", offset)
        elif kind == ord("D"):
            if size < 2:
                raise InputIntegrityError("invalid_data_message", offset)
            msg_id = struct.unpack_from("<H", payload)[0]
            if msg_id not in subscriptions:
                raise InputIntegrityError("unregistered_data_message", offset)
            subscription = subscriptions[msg_id]
            payload_size = size - 2
            if payload_size not in subscription.sizes:
                raise InputIntegrityError("data_size_mismatch", offset)
            subscription.offsets.append(offset)
            subscription.payload_sizes.append(payload_size)
        elif kind == ord("O"):
            if size != 2:
                raise InputIntegrityError("invalid_dropout_message", offset)
            dropout_count += 1
            dropout_duration += struct.unpack_from("<H", payload)[0]
        elif kind == ord("R"):
            raise InputIntegrityError("unsupported_subscription_removal", offset)
        else:
            raise InputIntegrityError("unsupported_message_kind", offset)
        offset = end

    if layouts is None:
        _resolve_layouts(definitions)
    return ULogInspection(
        source_log_id=expectation.source_log_id,
        size_bytes=len(data),
        streams=tuple(
            StreamFraming(
                s.name, s.multi_id, s.msg_id, tuple(s.offsets), tuple(s.payload_sizes)
            )
            for s in subscriptions.values()
        ),
        definitions=tuple(
            (name, definition.text) for name, definition in definitions.items()
        ),
        firmware_commit=firmware,
        dropout_count=dropout_count,
        dropout_duration_ms=dropout_duration,
    )
