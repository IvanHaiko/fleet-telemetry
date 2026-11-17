"""Offline inventory of any structurally valid ULog file (roadmap step 1).

One row per subscription: topic, instance, field names and types, sample
count, native time range and mapping status, plus the views the file supports
(map, battery, recorded state) and whether the integrated replay admits it.
No service runs and no telemetry value is interpreted: the only decoded field
is each sample's ULog ``timestamp``, which the format itself defines.

The structural admission policy is separate from the strict checksum-bound
scanner in ``ulog_integrity.py`` and is published in ``POLICY``. It reuses that
scanner's bounded definition and layout decoding. A file it cannot read to the
end gets an explicit ``incomplete`` (truncated or corrupt after a valid
prefix; the prefix is inventoried) or ``unsupported`` (format version,
incompatible feature, limit) status with a reason and a byte offset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

from telemetry.recordings import (
    MAPPING_PROFILES,
    RECORDINGS,
    SELECTED_TOPICS,
    MappingProfile,
    Recording,
)
from ulog_integrity import (
    _MAGIC,
    _WIDTHS,
    InputIntegrityError,
    _Definition,
    _definition,
    _Layout,
    _resolve_layouts,
)

FORMAT_VERSION = "ulog-inventory-v1"
MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_FRAMES = 20_000_000
_FLAG_APPENDED = 1
POLICY: dict[str, object] = {
    "format_versions": [0, 1],
    "message_kinds": "B F I M P Q A R D L C S O; other ASCII letters are "
    "skipped and counted (the format allows readers to skip unknown kinds)",
    "incompatible_flags": "bit 0 (appended data) is read through; any other "
    "bit is unsupported",
    "definitions": "ulog_integrity bounds: nesting depth, expanded fields, "
    "array sizes and name lengths",
    "max_input_bytes": MAX_INPUT_BYTES,
    "max_frames": MAX_FRAMES,
    "timestamps": "a top-level uint64_t field named timestamp, as the format "
    "defines it; no other field value is decoded",
}
# Which selected topics each view needs (ADR-0057 meanings).
VIEWS = {
    "map": ("vehicle_gps_position",),
    "battery": ("battery_status",),
    "state": ("vehicle_land_detected", "vehicle_status"),
}


@dataclass
class _Row:
    topic: str
    instance: int
    msg_id: int
    sizes: tuple[int, ...]
    stamp_offset: int | None
    samples: int = 0
    first_us: int | None = None
    last_us: int | None = None
    regressions: int = 0
    removed: bool = False


@dataclass
class _Scan:
    ulog_version: int | None = None
    features: list[str] = field(default_factory=list)
    firmware: str | None = None
    hardware: str | None = None
    frames: int = 0
    dropouts: int = 0
    dropout_ms: int = 0
    logged: int = 0
    parameters: int = 0
    metadata_errors: int = 0
    unknown_kinds: dict[str, int] = field(default_factory=dict)
    definitions: dict[str, _Definition] = field(default_factory=dict)
    rows: list[_Row] = field(default_factory=list)
    status: str = "complete"
    reason: str | None = None
    offset: int | None = None
    inventoried: int = 0


class _Stop(Exception):
    def __init__(self, status: str, reason: str, offset: int | None) -> None:
        super().__init__(reason)
        self.status, self.reason, self.offset = status, reason, offset


def closure_digest(topic: str, definitions: dict[str, str]) -> str:
    """SHA-256 of a topic's definition and every definition it references.

    Texts are joined by newlines in first-reference order, each once. For a
    topic without nested types this equals the SHA-256 of its own definition,
    the digest ADR-0057 registrations already pin.
    """
    order: list[str] = []
    pending = [topic]
    while pending:
        name = pending.pop(0)
        if name in order or name not in definitions:
            continue
        order.append(name)
        for item in definitions[name].partition(":")[2].split(";"):
            kind = item.split(" ")[0].split("[")[0]
            if item and kind not in _WIDTHS:
                pending.append(kind)
    body = "\n".join(definitions[name] for name in order)
    return hashlib.sha256(body.encode()).hexdigest()


def _stamp_offset(definition: _Definition, layouts: dict[str, _Layout]) -> int | None:
    offset = 0
    for item in definition.fields:
        if item.name == "timestamp" and item.kind == "uint64_t" and item.count == 1:
            return offset
        width = _WIDTHS.get(item.kind)
        offset += item.count * (width if width else layouts[item.kind].size)
    return None


def _text(value: bytes) -> str | None:
    try:
        return value.rstrip(b"\0").decode("ascii")
    except UnicodeDecodeError:
        return None


def _info(scan: _Scan, payload: bytes) -> None:
    """Lenient metadata: only firmware and hardware names are kept."""
    if not payload or payload[0] >= len(payload):
        scan.metadata_errors += 1
        return
    key = _text(payload[1 : 1 + payload[0]])
    if key is None or " " not in key:
        scan.metadata_errors += 1
        return
    kind, name = key.split(" ", 1)
    value = payload[1 + payload[0] :]
    if name == "ver_sw" and kind.startswith("char["):
        scan.firmware = _text(value)
    elif name == "ver_hw" and kind.startswith("char["):
        scan.hardware = _text(value)


def _scan(data: bytes, max_frames: int, scan: _Scan) -> None:
    if len(data) < 16 or data[:7] != _MAGIC:
        raise _Stop("unsupported", "not_a_ulog_file", 0)
    scan.ulog_version = data[7]
    if data[7] not in (0, 1):
        raise _Stop("unsupported", "unsupported_format_version", 7)
    layouts: dict[str, _Layout] | None = None
    rows: dict[int, _Row] = {}
    keys: set[tuple[str, int]] = set()
    offset = 16
    scan.inventoried = offset
    while offset < len(data):
        if scan.frames >= max_frames:
            raise _Stop("incomplete", "frame_limit", offset)
        if len(data) - offset < 3:
            raise _Stop("incomplete", "truncated_tail", offset)
        size, kind = struct.unpack_from("<HB", data, offset)
        end = offset + 3 + size
        if end > len(data):
            raise _Stop("incomplete", "truncated_tail", offset)
        payload = data[offset + 3 : end]
        scan.frames += 1
        if kind == 0x44:  # D
            if size < 2:
                raise _Stop("incomplete", "invalid_data_message", offset)
            row = rows.get(struct.unpack_from("<H", payload)[0])
            if row is None or row.removed:
                raise _Stop("incomplete", "unregistered_data_message", offset)
            if size - 2 not in row.sizes:
                raise _Stop("incomplete", "data_size_mismatch", offset)
            row.samples += 1
            if row.stamp_offset is not None:
                stamp = struct.unpack_from("<Q", payload, 2 + row.stamp_offset)[0]
                if row.first_us is None:
                    row.first_us = stamp
                elif row.last_us is not None and stamp < row.last_us:
                    row.regressions += 1
                row.last_us = stamp
        elif kind == 0x41:  # A
            if size < 4:
                raise _Stop("incomplete", "invalid_subscription", offset)
            multi_id, msg_id = struct.unpack_from("<BH", payload)
            name = _text(payload[3:])
            if name is None or name not in scan.definitions:
                raise _Stop("unsupported", "undefined_subscription", offset)
            known = rows.get(msg_id)
            if (known is not None and not known.removed) or (name, multi_id) in keys:
                raise _Stop("incomplete", "subscription_reuse", offset)
            if layouts is None:
                layouts = _resolve_layouts(scan.definitions)
            definition = scan.definitions[name]
            row = _Row(
                name,
                multi_id,
                msg_id,
                layouts[name].sizes,
                _stamp_offset(definition, layouts),
            )
            rows[msg_id] = row
            keys.add((name, multi_id))
            scan.rows.append(row)
        elif kind == 0x46:  # F
            name, definition = _definition(payload, offset)
            if name in scan.definitions:
                raise _Stop("unsupported", "definition_reuse", offset)
            scan.definitions[name] = definition
            layouts = None
        elif kind == 0x52:  # R
            if size < 3:
                raise _Stop("incomplete", "invalid_subscription_removal", offset)
            row = rows.get(struct.unpack_from("<H", payload, 1)[0])
            if row is not None:
                row.removed = True
                keys.discard((row.topic, row.instance))
        elif kind == 0x4F:  # O
            if size != 2:
                raise _Stop("incomplete", "invalid_dropout_message", offset)
            scan.dropouts += 1
            scan.dropout_ms += struct.unpack_from("<H", payload)[0]
        elif kind == 0x42:  # B
            if offset != 16 or size < 40:
                raise _Stop("unsupported", "invalid_flags_message", offset)
            incompatible = int.from_bytes(payload[8:16], "little")
            if incompatible & ~_FLAG_APPENDED:
                raise _Stop("unsupported", "unsupported_incompatibility_flags", offset)
            if incompatible & _FLAG_APPENDED:
                scan.features.append("appended_data")
            if payload[0] & 1:
                scan.features.append("default_parameters")
        elif kind == 0x49:  # I
            _info(scan, payload)
        elif kind in (0x50, 0x51):  # P, Q
            scan.parameters += 1
        elif kind in (0x4C, 0x43):  # L, C
            scan.logged += 1
        elif kind in (0x4D, 0x53):  # M, S
            pass
        elif 0x41 <= kind <= 0x5A or 0x61 <= kind <= 0x7A:
            letter = chr(kind)
            scan.unknown_kinds[letter] = scan.unknown_kinds.get(letter, 0) + 1
        else:
            raise _Stop("incomplete", "invalid_message_kind", offset)
        offset = end
        scan.inventoried = offset


def _mapping(
    scan: _Scan, registered: Recording | None
) -> tuple[dict[str, str], dict[str, object]]:
    """Mapping status per selected topic and the file's replay admission."""
    texts = {name: d.text for name, d in scan.definitions.items()}
    present = {(r.topic, r.instance): r for r in scan.rows}
    digests = {
        topic: closure_digest(topic, texts)
        for topic in SELECTED_TOPICS
        if topic in texts
    }
    matching = [
        profile
        for profile in MAPPING_PROFILES
        if all(digests.get(t) == d for t, d in profile.layouts.items() if t in digests)
    ]
    reviewed = [p for p in matching if scan.firmware in p.firmware]
    candidates = reviewed or matching
    profile: MappingProfile | None = candidates[0] if candidates else None
    topics: dict[str, str] = {}
    for topic in SELECTED_TOPICS:
        if registered is not None:
            topics[topic] = "registered" if (topic, 0) in present else "missing"
        elif (topic, 0) not in present:
            topics[topic] = "missing_subscription"
        elif profile is None or digests.get(topic) != profile.layouts[topic]:
            topics[topic] = "unknown_definition"
        elif scan.firmware not in profile.firmware:
            topics[topic] = "candidate_unreviewed_firmware"
        else:
            topics[topic] = "mapped"
    reasons: list[str] = []
    if scan.status != "complete":
        reasons.append(f"inventory_{scan.status}")
    for topic in SELECTED_TOPICS:
        row = present.get((topic, 0))
        if row is None:
            reasons.append(f"{topic}:missing_subscription")
        elif row.samples == 0 and topic in VIEWS["map"] + VIEWS["battery"]:
            reasons.append(f"{topic}:empty_subscription")
        elif registered is None and topics[topic] != "mapped":
            reasons.append(f"{topic}:{topics[topic]}")
    if registered is not None:
        status = "registered"
    elif reasons:
        status = "unavailable"
    else:
        status = "admitted"
    return topics, {
        "status": status,
        "registration": None if registered is None else registered.key,
        "profile": None if profile is None else profile.key,
        "profile_firmware_reviewed": profile is not None
        and scan.firmware in profile.firmware,
        "topics": topics,
        "reasons": reasons,
    }


def _views(scan: _Scan, topics: dict[str, str]) -> dict[str, object]:
    present = {(r.topic, r.instance): r for r in scan.rows}
    result: dict[str, object] = {}
    for view, needed in VIEWS.items():
        parts = []
        for topic in needed:
            row = present.get((topic, 0))
            if row is None:
                state = "missing_subscription"
            elif row.samples == 0:
                state = "empty_subscription"
            elif topics[topic] in ("mapped", "registered"):
                state = "available"
            else:
                state = "unknown_mapping"
            parts.append(
                {
                    "topic": topic,
                    "state": state,
                    "samples": None if row is None else row.samples,
                    # Values a reviewed mapping refuses are counted only when
                    # that mapping runs (admission or a registered adapter).
                    "rejected_by_mapping": None,
                }
            )
        states = {str(p["state"]) for p in parts}
        result[view] = {
            "state": "available" if states == {"available"} else sorted(states)[0],
            "topics": parts,
        }
    return result


def inventory(
    path: Path, max_bytes: int = MAX_INPUT_BYTES, max_frames: int = MAX_FRAMES
) -> dict[str, object]:
    """Inventory one file; an unreadable structure is a status, not an error."""
    size = path.stat().st_size
    if size > max_bytes:
        return {
            "format_version": FORMAT_VERSION,
            "file": {"name": path.name, "bytes": size, "sha256": None},
            "status": "unsupported",
            "reason": "input_size_limit",
            "policy": POLICY,
        }
    data = path.read_bytes()
    source_id = "sha256:" + hashlib.sha256(data).hexdigest()
    scan = _Scan()
    try:
        _scan(data, max_frames, scan)
    except (_Stop, InputIntegrityError) as stop:
        scan.status = stop.status if isinstance(stop, _Stop) else "unsupported"
        scan.reason = stop.reason
        scan.offset = stop.offset
    registered = RECORDINGS.get(source_id)
    topics, replay = _mapping(scan, registered)
    texts = {name: d.text for name, d in scan.definitions.items()}
    subscribed = {row.topic for row in scan.rows}
    return {
        "format_version": FORMAT_VERSION,
        "file": {"name": path.name, "bytes": size, "sha256": source_id},
        "status": scan.status,
        "reason": scan.reason,
        "offset": scan.offset,
        "inventoried_bytes": scan.inventoried,
        "ulog_version": scan.ulog_version,
        "features": scan.features,
        "firmware": scan.firmware,
        "hardware": scan.hardware,
        "frames": scan.frames,
        "dropouts": {"markers": scan.dropouts, "duration_ms": scan.dropout_ms},
        "logged_messages": scan.logged,
        "parameters": scan.parameters,
        "metadata_errors": scan.metadata_errors,
        "unknown_message_kinds": scan.unknown_kinds,
        "definitions": len(scan.definitions),
        "definitions_without_subscription": len(set(scan.definitions) - subscribed),
        "subscriptions": [
            {
                "topic": row.topic,
                "instance": row.instance,
                "msg_id": row.msg_id,
                "definition_sha256": closure_digest(row.topic, texts),
                "fields": [
                    [
                        f.kind if f.count == 1 else f"{f.kind}[{f.count}]",
                        f.name,
                    ]
                    for f in scan.definitions[row.topic].fields
                    if not f.name.startswith("_padding")
                ],
                "samples": row.samples,
                "first_us": row.first_us,
                "last_us": row.last_us,
                "time_regressions": row.regressions,
                "removed": row.removed,
                "mapping": topics.get(row.topic, "unmapped")
                if row.instance == 0
                else "unmapped",
            }
            for row in scan.rows
        ],
        "views": _views(scan, topics),
        "replay": replay,
        "policy": POLICY,
    }


def _field(value: object) -> str:
    return "-" if value is None else str(value)


def render(report: dict[str, object]) -> str:
    """One screen: file status, one row per subscription, then the views."""
    file = report["file"]
    assert isinstance(file, dict)
    head = f"{file['name']}  {file['bytes']} B  status {report['status']}"
    if report.get("reason"):
        head += f" ({report['reason']} at byte {_field(report.get('offset'))})"
    lines = [head]
    if "subscriptions" not in report:
        return "\n".join(lines)
    dropouts = report["dropouts"]
    assert isinstance(dropouts, dict)
    lines.append(
        f"ULog v{_field(report['ulog_version'])}  firmware "
        f"{_field(report['firmware'])}  hardware {_field(report['hardware'])}  "
        f"frames {report['frames']}  dropout markers {dropouts['markers']} "
        f"({dropouts['duration_ms']} ms)  features "
        f"{','.join(report['features']) or '-'}"  # type: ignore[arg-type]
    )
    lines.append("")
    lines.append(
        f"{'topic':<40} {'inst':>4} {'samples':>9} {'span_s':>9} {'fields':>6}  mapping"
    )
    rows = report["subscriptions"]
    assert isinstance(rows, list)
    for row in rows:
        first, last = row["first_us"], row["last_us"]
        span = "-" if first is None or last is None else f"{(last - first) / 1e6:.1f}"
        lines.append(
            f"{row['topic']:<40} {row['instance']:>4} {row['samples']:>9} "
            f"{span:>9} {len(row['fields']):>6}  {row['mapping']}"
        )
    lines.append("")
    views = report["views"]
    assert isinstance(views, dict)
    for name, view in views.items():
        parts = ", ".join(
            f"{t['topic']} {t['state']} ({_field(t['samples'])} samples)"
            for t in view["topics"]
        )
        lines.append(f"view {name:<8} {view['state']:<22} {parts}")
    replay = report["replay"]
    assert isinstance(replay, dict)
    lines.append(
        f"replay   {replay['status']}  profile {_field(replay['profile'])}"
        + (f"  reasons {', '.join(replay['reasons'])}" if replay["reasons"] else "")
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("source", type=Path, help="a .ulg file")
    parser.add_argument("--json", action="store_true", help="the full report")
    parser.add_argument("--fields", action="store_true", help="list fields")
    parser.add_argument("--max-bytes", type=int, default=MAX_INPUT_BYTES)
    parser.add_argument("--max-frames", type=int, default=MAX_FRAMES)
    args = parser.parse_args(argv)
    try:
        report = inventory(args.source, args.max_bytes, args.max_frames)
    except OSError:
        print(json.dumps({"status": "failed", "reason": "unreadable_input"}))
        return 2
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(render(report))
        if args.fields:
            for row in report.get("subscriptions", []):  # type: ignore[attr-defined]
                fields = " ".join(f"{k} {n};" for k, n in row["fields"])
                print(f"{row['topic']}:{row['instance']}  {fields}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
