"""Bounded decoding of selected scalar fields from a ULog file (ADR-0060).

Only top-level scalar fields of the selected topics, instance 0, are read;
samples whose ULog timestamp does not increase are dropped and counted.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator
from dataclasses import dataclass, field

from ulog_integrity import _WIDTHS, _Definition, _definition, _Layout, _resolve_layouts

type Value = float | int | bool
type Samples = list[tuple[int, dict[str, Value]]]

_STRUCT = {
    "int8_t": "b",
    "uint8_t": "B",
    "int16_t": "h",
    "uint16_t": "H",
    "int32_t": "i",
    "uint32_t": "I",
    "int64_t": "q",
    "uint64_t": "Q",
    "float": "f",
    "double": "d",
    "bool": "?",
}


_GPS_FIELDS = ("lat", "lon", "alt", "latitude_deg", "longitude_deg", "altitude_msl_m")
_SELECTED = {
    "vehicle_global_position": ("lat", "lon", "alt"),
    "vehicle_gps_position": _GPS_FIELDS,
    "sensor_gps": _GPS_FIELDS,
    "home_position": ("alt",),
    "vehicle_local_position": ("vx", "vy", "vz"),
    "battery_status": ("voltage_v", "current_a", "remaining"),
    "vehicle_status": ("arming_state",),
}


@dataclass
class Topic:
    kinds: dict[str, str]
    offsets: dict[str, int]
    samples: Samples = field(default_factory=list)
    regressions: int = 0


def _offsets(
    definition: _Definition, layouts: dict[str, _Layout]
) -> tuple[dict[str, str], dict[str, int]]:
    """Top-level scalar fields: type and byte offset within a sample."""
    kinds: dict[str, str] = {}
    offsets: dict[str, int] = {}
    offset = 0
    for item in definition.fields:
        width = _WIDTHS.get(item.kind)
        if width is not None and item.count == 1:
            kinds[item.name] = item.kind
            offsets[item.name] = offset
        offset += item.count * (width if width else layouts[item.kind].size)
    return kinds, offsets


def _frames(data: bytes) -> Iterator[tuple[int, bytes]]:
    offset = 16
    while offset + 3 <= len(data):
        size, kind = struct.unpack_from("<HB", data, offset)
        end = offset + 3 + size
        if end > len(data):
            return
        yield kind, data[offset + 3 : end]
        offset = end


def decode(data: bytes) -> dict[str, Topic]:
    """Samples of the selected fields of the selected topics, instance 0."""
    definitions: dict[str, _Definition] = {}
    layouts: dict[str, _Layout] | None = None
    topics: dict[int, tuple[str, Topic]] = {}
    found: dict[str, Topic] = {}
    for kind, payload in _frames(data):
        if kind == 0x46:  # F
            name, definition = _definition(payload, 0)
            definitions[name] = definition
            layouts = None
        elif kind == 0x41:  # A
            multi_id, msg_id = struct.unpack_from("<BH", payload)
            name = payload[3:].rstrip(b"\0").decode("ascii", "replace")
            if multi_id != 0 or name not in _SELECTED or name in found:
                continue
            if layouts is None:
                layouts = _resolve_layouts(definitions)
            kinds, offsets = _offsets(definitions[name], layouts)
            if kinds.get("timestamp") != "uint64_t":
                continue
            topic = Topic(kinds, offsets)
            topics[msg_id] = (name, topic)
            found[name] = topic
        elif kind == 0x44:  # D
            entry = topics.get(struct.unpack_from("<H", payload)[0])
            if entry is None:
                continue
            name, topic = entry
            body = payload[2:]
            stamp = struct.unpack_from("<Q", body, topic.offsets["timestamp"])[0]
            if topic.samples and stamp <= topic.samples[-1][0]:
                topic.regressions += 1  # dropped: native order is the contract
                continue
            values: dict[str, Value] = {}
            for wanted in _SELECTED[name]:
                if wanted in topic.offsets:
                    code = "<" + _STRUCT[topic.kinds[wanted]]
                    values[wanted] = struct.unpack_from(
                        code, body, topic.offsets[wanted]
                    )[0]
            topic.samples.append((stamp, values))
    return found
