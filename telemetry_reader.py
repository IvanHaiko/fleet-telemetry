"""Bounded canonical battery admission, independent of native normalization."""

import argparse
import json
import math
import os
import re
import stat
import sys
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import cast

from fleet_telemetry import MAX_NATIVE_INTEGER, BatteryEnvelope, ULogBatteryEnvelope

MAX_EVENT_BYTES = 64 * 1024
READER_VERSION = "battery-envelope-reader-v1"
MAX_EVENT_FILE_BYTES = 64 * 1024 * 1024
MAX_EVENT_RECORDS = 100_000
type BatteryEvent = BatteryEnvelope | ULogBatteryEnvelope
_HASH = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)
_UTC = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z", re.ASCII
)
_ENVELOPE = {
    "event_id",
    "vehicle_id",
    "event_type",
    "schema_version",
    "source_timestamp",
    "ingest_timestamp",
    "source_log_id",
    "source_type",
    "source_stream",
    "source_record_index",
    "normalization_version",
    "source_time",
    "provenance",
    "quality_flags",
    "payload",
    "delivery",
}


class EnvelopeError(ValueError):
    """Fixed reason and field names only; never echo a supplied value or key."""

    def __init__(
        self, reason: str, field: str, record_index: int | None = None
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.field = field
        self.record_index = record_index


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise EnvelopeError("duplicate_json_key", "json")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise EnvelopeError("nonfinite_number", "json")


def _json_values(root: object) -> None:
    pending = [root]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            mapping = cast(dict[str, object], value)
            pending.extend(mapping.keys())
            pending.extend(mapping.values())
        elif isinstance(value, list):
            pending.extend(cast(list[object], value))
        elif isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeError:
                raise EnvelopeError("invalid_utf8", "json") from None
        elif isinstance(value, float) and not math.isfinite(value):
            raise EnvelopeError("nonfinite_number", "json")


def _shape(
    value: object, required: set[str], field: str, optional: set[str] | None = None
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise EnvelopeError("invalid_object", field)
    mapping = cast(dict[str, object], value)
    if not required <= mapping.keys():
        raise EnvelopeError("missing_required_field", field)
    return {
        key: mapping[key] for key in required | (optional or set()) if key in mapping
    }


def _identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[\x20-\x7e]+", value) is None:
        raise EnvelopeError("invalid_identifier", field)
    return value


def _integer(value: object, field: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_NATIVE_INTEGER:
        raise EnvelopeError("invalid_integer", field)
    return value


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise EnvelopeError("invalid_timestamp", field)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise EnvelopeError("invalid_timestamp", field) from None


def _number(value: object, field: str) -> int | float:
    if type(value) not in (int, float):
        raise EnvelopeError("invalid_unit_value", field)
    number = cast(int | float, value)
    try:
        finite = math.isfinite(number)
    except OverflowError:
        finite = False
    if not finite:
        raise EnvelopeError("invalid_unit_value", field)
    return number


def read_battery_event(data: bytes) -> BatteryEvent:
    """Read one supported event into the recognized projection, without I/O.

    Unknown optional object fields are ignored; absent optional payload fields
    become null. A valid positional ID does not authenticate payload values.
    """
    if type(data) is not bytes:
        raise EnvelopeError("invalid_input_type", "json")
    if len(data) > MAX_EVENT_BYTES:
        raise EnvelopeError("event_size_limit", "json")
    try:
        decoded: object = json.loads(
            data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
    except EnvelopeError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise EnvelopeError("invalid_json", "json") from None
    _json_values(decoded)
    event = _shape(decoded, _ENVELOPE, "envelope")
    if event["schema_version"] != "1.0.0" or event["event_type"] != "telemetry.battery":
        raise EnvelopeError("unsupported_schema", "envelope")
    version = event["normalization_version"]
    if version not in ("battery-v1", "ulog-battery-v1", "ulog-battery-f09-research-v1"):
        raise EnvelopeError("unsupported_normalization", "normalization_version")
    if version == "ulog-battery-f09-research-v1":
        from ulog_integrity import F09_SOURCE_ID

        if (
            event["source_log_id"] != F09_SOURCE_ID
            or event["source_type"] != "ulog"
            or event["source_stream"] != "battery_status:0"
        ):
            raise EnvelopeError("profile_mismatch", "source_log_id")
    for field in ("vehicle_id", "source_stream"):
        _identifier(event[field], field)
    for field in ("event_id", "source_log_id"):
        if (
            not isinstance(event[field], str)
            or _HASH.fullmatch(cast(str, event[field])) is None
        ):
            raise EnvelopeError("invalid_checksum", field)
    _integer(event["source_record_index"], "source_record_index")
    source_type = event["source_type"]
    if source_type not in ("synthetic", "ulog") or (
        version == "battery-v1" and source_type != "synthetic"
    ):
        raise EnvelopeError("profile_mismatch", "source_type")

    source_time = _shape(
        event["source_time"],
        {"clock_basis", "native_timestamp_us", "timestamp_kind", "mapping"},
        "source_time",
    )
    if source_time["clock_basis"] != "boot_relative" or source_time[
        "timestamp_kind"
    ] != ("measurement" if version == "battery-v1" else "publication"):
        raise EnvelopeError("profile_mismatch", "source_time")
    native = _integer(source_time["native_timestamp_us"], "native_timestamp_us")
    mapping = _shape(
        source_time["mapping"],
        {"native_anchor_us", "utc_anchor", "anchor_kind", "anchor_uncertainty_us"},
        "mapping",
    )
    anchor_native = _integer(mapping["native_anchor_us"], "native_anchor_us")
    anchor_utc = _utc(mapping["utc_anchor"], "utc_anchor")
    if mapping["anchor_kind"] != "synthetic_fixed":
        raise EnvelopeError("unsupported_anchor", "anchor_kind")
    if mapping["anchor_uncertainty_us"] is not None:
        _integer(mapping["anchor_uncertainty_us"], "anchor_uncertainty_us")
    source_utc = _utc(event["source_timestamp"], "source_timestamp")
    _utc(event["ingest_timestamp"], "ingest_timestamp")
    try:
        expected_utc = anchor_utc + timedelta(microseconds=native - anchor_native)
    except OverflowError:
        raise EnvelopeError("invalid_time_mapping", "source_timestamp") from None
    if source_utc != expected_utc:
        raise EnvelopeError("invalid_time_mapping", "source_timestamp")
    source_time["mapping"] = mapping
    event["source_time"] = source_time

    provenance = _shape(
        event["provenance"],
        {"source_manifest_id", "privacy_classification"},
        "provenance",
    )
    _identifier(provenance["source_manifest_id"], "source_manifest_id")
    delivery = _shape(event["delivery"], {"dataset_run_id", "replay_mode"}, "delivery")
    _identifier(delivery["dataset_run_id"], "dataset_run_id")
    if provenance["privacy_classification"] != (
        "synthetic" if source_type == "synthetic" else "restricted"
    ) or delivery["replay_mode"] != (
        "synthetic" if source_type == "synthetic" else "historical"
    ):
        raise EnvelopeError("profile_mismatch", "provenance_or_delivery")
    event["provenance"], event["delivery"] = provenance, delivery

    payload = _shape(
        event["payload"], {"voltage_v"}, "payload", {"current_a", "remaining_fraction"}
    )
    if _number(payload["voltage_v"], "voltage_v") < 0:
        raise EnvelopeError("invalid_unit_value", "voltage_v")
    for field in ("current_a", "remaining_fraction"):
        value = payload.get(field)
        if value is not None:
            number = _number(value, field)
            if field == "remaining_fraction" and not 0 <= number <= 1:
                raise EnvelopeError("invalid_unit_value", field)
        payload[field] = value
    event["payload"] = payload
    if not isinstance(event["quality_flags"], list):
        raise EnvelopeError("invalid_flags", "quality_flags")
    flags = cast(list[object], event["quality_flags"])
    names = [_identifier(value, "quality_flags") for value in flags]
    if len(set(names)) != len(names) or "synthetic_time_anchor" not in names:
        raise EnvelopeError("invalid_flags", "quality_flags")
    event["quality_flags"] = names
    identity = [
        "event-id-v1",
        source_type,
        event["source_log_id"],
        event["vehicle_id"],
        event["source_stream"],
        event["source_record_index"],
        "telemetry.battery",
        version,
    ]
    expected_id = (
        "sha256:"
        + sha256(
            json.dumps(identity, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    if event["event_id"] != expected_id:
        raise EnvelopeError("identity_mismatch", "event_id")
    return cast(BatteryEvent, event)


def check_event_file(path: Path) -> int:
    """Check bounded JSONL atomically; return count only after complete success."""
    observed = path.stat()
    if not stat.S_ISREG(observed.st_mode):
        raise EnvelopeError("invalid_input_file", "input")
    if observed.st_size > MAX_EVENT_FILE_BYTES:
        raise EnvelopeError("file_size_limit", "input")
    count = total = 0
    with path.open("rb") as handle:
        initial = os.fstat(handle.fileno())
        if not stat.S_ISREG(initial.st_mode):
            raise EnvelopeError("invalid_input_file", "input")
        # The actual read budget also catches a growing input.
        if initial.st_size > MAX_EVENT_FILE_BYTES:
            raise EnvelopeError("file_size_limit", "input")
        while line := handle.readline(MAX_EVENT_BYTES + 2):
            total += len(line)
            if total > MAX_EVENT_FILE_BYTES or count >= MAX_EVENT_RECORDS:
                raise EnvelopeError("file_budget_limit", "input", count)
            record = line[:-1] if line.endswith(b"\n") else line
            if record.endswith(b"\r"):
                record = record[:-1]
            try:
                read_battery_event(record)
            except EnvelopeError as error:
                error.record_index = count
                raise
            count += 1
        if (
            total != initial.st_size
            or os.fstat(handle.fileno()).st_size != initial.st_size
        ):
            raise EnvelopeError("input_changed", "input")
    return count


class _Arguments(argparse.Namespace):
    input: Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check bounded canonical battery JSONL."
    )
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv, namespace=_Arguments())
    try:
        count = check_event_file(args.input)
    except EnvelopeError as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "reason": error.reason,
                    "field": error.field,
                    "record_index": error.record_index,
                }
            ),
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError):
        print(
            json.dumps({"status": "failed", "reason": "input_unavailable"}),
            file=sys.stderr,
        )
        return 2
    print(json.dumps({"status": "validated", "records": count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
