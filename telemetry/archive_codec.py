"""Pure bounded observation encoding; measurement links are syntax only."""

import base64
import binascii
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import NoReturn, TypedDict, cast

_LINE = 256 * 1024
_BATCH = 1024 * 1024
_SOURCE = frozenset(("cluster_id", "topic_id", "topic", "partition"))
_FIELDS = _SOURCE | {
    "format_version",
    "offset",
    "timestamp_ms",
    "timestamp_type",
    "key_b64",
    "value_b64",
    "headers",
    "measurement",
}
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


class Header(TypedDict):
    """Ordered header entry, retaining null and empty byte distinctions."""

    name_utf8: str
    value_b64: str | None


class MeasurementLink(TypedDict):
    """Syntactic references, without event or manifest admission."""

    event_id: str
    source_manifest_sha256: str


class ArchiveError(ValueError):
    """Safe fixed diagnostics without supplied metadata or payload values."""

    def __init__(self, category: str, field: str) -> None:
        self.category = category
        self.field = field
        super().__init__(f"{category}: {field}")


@dataclass(frozen=True)
class Coverage:
    """Owned observations and distinct overlap/measurement accounting."""

    observations: tuple[dict[str, object], ...]
    overlap_count: int
    repeated_measurement_count: int


def _fail(category: str = "invalid_format", field: str = "observation") -> NoReturn:
    raise ArchiveError(category, field) from None


def _mapping(value: object, keys: frozenset[str] | set[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or len(value) != len(keys):
        _fail()
    if any(type(key) is not str or key not in keys for key in value):
        _fail()
    return cast(Mapping[str, object], value)


def _string(value: object, maximum: int, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty):
        _fail()
    if len(value) > maximum:
        _fail("limit_exceeded", "string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        _fail()
    if size > maximum:
        _fail("limit_exceeded", "string")
    return value


def _integer(value: object, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        _fail()
    return value


def _binary(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _fail()
    if len(value) > _LINE:
        _fail("limit_exceeded", "line")
    try:
        decoded = base64.b64decode(value, validate=True)
        canonical = base64.b64encode(decoded).decode("ascii")
    except (ValueError, binascii.Error):
        _fail()
    if canonical != value:
        _fail()
    return value


def _source(value: object) -> dict[str, object]:
    source = _mapping(value, _SOURCE)
    return {
        "cluster_id": _string(source["cluster_id"], 512),
        "topic_id": _string(source["topic_id"], 512),
        "topic": _string(source["topic"], 512),
        "partition": _integer(source["partition"], 0, 2**31 - 1),
    }


def _row(value: object) -> dict[str, object]:
    row = _mapping(value, _FIELDS)
    if row["format_version"] != "kafka-observation-v1":
        _fail("unsupported_profile", "format_version")
    result = _source({key: row[key] for key in _SOURCE})
    result["format_version"] = "kafka-observation-v1"
    result["offset"] = _integer(row["offset"], 0, 2**63 - 1)
    kind = row["timestamp_type"]
    timestamp = row["timestamp_ms"]
    if timestamp is None:
        if kind != "not_available":
            _fail()
    else:
        _integer(timestamp, -(2**63), 2**63 - 1)
        if kind not in ("create_time", "log_append_time"):
            _fail()
    result["timestamp_type"] = kind
    result["timestamp_ms"] = timestamp
    headers = row["headers"]
    if not isinstance(headers, list):
        _fail()
    if len(headers) > 32:
        _fail("limit_exceeded", "headers")
    # Reject aggregate string bodies before base64 decoding or JSON escaping.
    # Every supplied string contributes at least its character count on wire.
    string_size = 0
    for key in ("key_b64", "value_b64"):
        value = row[key]
        if isinstance(value, str):
            string_size += len(value)
    for entry in headers:
        header = _mapping(entry, {"name_utf8", "value_b64"})
        for key in ("name_utf8", "value_b64"):
            value = header[key]
            if isinstance(value, str):
                string_size += len(value)
    if string_size > _LINE:
        _fail("limit_exceeded", "line")
    result["key_b64"] = _binary(row["key_b64"])
    result["value_b64"] = _binary(row["value_b64"])
    owned: list[Header] = []
    # Fixed-schema validation never recursively walks supplied containers.
    for entry in headers:
        header = _mapping(entry, {"name_utf8", "value_b64"})
        owned.append(
            Header(
                name_utf8=_string(header["name_utf8"], 256, True),
                value_b64=_binary(header["value_b64"]),
            )
        )
    result["headers"] = owned
    link = row["measurement"]
    if link is not None:
        measurement = _mapping(link, {"event_id", "source_manifest_sha256"})
        fresh: dict[str, object] = {}
        for key in ("event_id", "source_manifest_sha256"):
            digest = _string(measurement[key], 512)
            if _DIGEST.fullmatch(digest) is None:
                _fail()
            fresh[key] = digest
        result["measurement"] = fresh
    else:
        result["measurement"] = None
    return result


def _line(row: Mapping[str, object]) -> bytes:
    encoder = json.JSONEncoder(
        ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    chunks: list[bytes] = []
    size = 1
    for chunk in encoder.iterencode(row):
        encoded = chunk.encode("utf-8")
        size += len(encoded)
        if size > _LINE:
            _fail("limit_exceeded", "line")
        chunks.append(encoded)
    return b"".join(chunks) + b"\n"


def _sequence(value: object, maximum: int) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail()
    if len(value) > maximum:
        _fail("limit_exceeded", "count")
    return value


def encode_observations(rows: Sequence[Mapping[str, object]]) -> bytes:
    """Validate and sort a bounded batch without changing caller data."""
    supplied = _sequence(rows, 16)
    if not supplied:
        _fail()
    validated: list[tuple[int, bytes]] = []
    source: dict[str, object] | None = None
    seen: set[int] = set()
    total = 0
    for value in supplied:
        row = _row(value)
        current = {key: row[key] for key in _SOURCE}
        if source is not None and source != current:
            _fail("lineage_mismatch", "source")
        source = current
        offset = cast(int, row["offset"])
        if offset in seen:
            _fail("observation_conflict", "offset")
        seen.add(offset)
        line = _line(row)
        total += len(line)
        if total > _BATCH:
            _fail("limit_exceeded", "batch")
        validated.append((offset, line))
    validated.sort(key=lambda pair: pair[0])
    return b"".join(line for _, line in validated)


def _nesting(line: bytes) -> None:
    depth = 0
    quoted = False
    escaped = False
    for char in line:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > 16:
                _fail("limit_exceeded", "nesting")
        elif char in (93, 125):
            depth -= 1


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _reject_number(value: str) -> NoReturn:
    _fail()


def _parse_integer(value: str) -> int:
    if len(value) > 20:
        _fail()
    return int(value)


def decode_observations(data: bytes) -> tuple[dict[str, object], ...]:
    """Require canonical JSONL, returning fresh nested observation structures."""
    if type(data) is not bytes or not data or not data.endswith(b"\n"):
        _fail()
    if len(data) > _BATCH:
        _fail("limit_exceeded", "batch")
    if data.count(b"\n") > 16:
        _fail("limit_exceeded", "count")
    rows: list[dict[str, object]] = []
    for line in data.split(b"\n")[:-1]:
        if len(line) + 1 > _LINE:
            _fail("limit_exceeded", "line")
        _nesting(line)
        try:
            parsed: object = json.loads(
                line,
                object_pairs_hook=_pairs,
                parse_float=_reject_number,
                parse_constant=_reject_number,
                parse_int=_parse_integer,
            )
        except (ValueError, UnicodeError, RecursionError):
            # Preserve our fixed categories, including bounds from hooks.
            _fail()
        rows.append(_row(parsed))
    canonical = encode_observations(rows)
    if canonical != data:
        _fail()
    return tuple(rows)


def reconcile_coverage(
    batches: Sequence[bytes],
    source: Mapping[str, object],
    start_offset: int,
    next_offset: int,
) -> Coverage:
    """Enumerate exact offset union; compare overlaps using full canonical bytes."""
    expected = _source(source)
    start = _integer(start_offset, 0, 2**63 - 1)
    end = _integer(next_offset, 0, 2**63)
    if start >= end:
        _fail()
    if end - start > 32:
        _fail("limit_exceeded", "interval")
    supplied = _sequence(batches, 16)
    observations: dict[int, dict[str, object]] = {}
    lines: dict[int, bytes] = {}
    overlaps = 0
    count = 0
    for batch in supplied:
        if type(batch) is not bytes:
            _fail()
        if len(batch) > _BATCH:
            _fail("limit_exceeded", "batch")
        # Count before parsing a batch that would exceed the aggregate bound.
        count += batch.count(b"\n")
        if count > 64:
            _fail("limit_exceeded", "count")
        for row in decode_observations(batch):
            offset = cast(int, row["offset"])
            if {key: row[key] for key in _SOURCE} != expected:
                _fail("lineage_mismatch", "source")
            if not start <= offset < end:
                _fail("lineage_mismatch", "interval")
            line = _line(row)
            if offset in lines:
                if lines[offset] != line:
                    _fail("observation_conflict", "offset")
                overlaps += 1
            else:
                lines[offset] = line
                observations[offset] = row
    if any(offset not in observations for offset in range(start, end)):
        _fail("coverage_gap", "interval")
    ordered = tuple(observations[offset] for offset in range(start, end))
    identities: set[str] = set()
    repeated = 0
    for row in ordered:
        link = row["measurement"]
        if link is not None:
            event_id = cast(MeasurementLink, link)["event_id"]
            if event_id in identities:
                repeated += 1
            identities.add(event_id)
    return Coverage(ordered, overlaps, repeated)
