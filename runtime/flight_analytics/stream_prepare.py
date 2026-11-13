"""Reuse protected F09 preparation as a bounded, deterministic offline stream.

Source payloads keep their original ordinals. Exact duplicate input rows collapse
before ordering checks; conflicting identities and non-increasing per-stream
ordinals/times refuse. GPS/state coverage is contiguous from ordinal zero;
battery holes retain their separate rejection-gap meaning. This verifies retained
artifacts, not independent source admission or physical clock synchronization.
"""

import argparse
import json
import sys
from itertools import pairwise
from pathlib import Path
from typing import Never

from runtime.flight_analytics.stream_contract import (
    _CONTEXT_KEYS,
    _HASH,
    _MANIFEST_KEYS,
    _RUN,
    BUNDLE_PROFILE,
    CONTEXT_PROFILE,
    LIMITATIONS,
    MAX_BYTES,
    MAX_EVENTS,
    SOURCE_BYTES,
    Document,
    _check_reference,
    _documents,
    _gaps,
    _input_names,
    _integer,
    _limitations,
    _ordered_unique,
    _read,
    _reference,
    _rows,
    _safe_path,
    _same,
    _scope,
    _validate_context,
    _validate_inventory,
    timeline,
)
from runtime.flight_analytics.stream_source import _verify_prepared
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    require_keys,
    string_value,
)
from telemetry.local_io import destination, publish_run
from telemetry.recording_stream import (
    STREAMS,
    event_bytes,
    event_order,
    read_event,
    validate_battery_gaps,
)
from ulog_integrity import F09_SOURCE_ID

__all__ = [
    "_CONTEXT_KEYS",
    "_HASH",
    "_MANIFEST_KEYS",
    "_RUN",
    "BUNDLE_PROFILE",
    "CONTEXT_PROFILE",
    "LIMITATIONS",
    "MAX_BYTES",
    "MAX_EVENTS",
    "SOURCE_BYTES",
    "Document",
    "_check_reference",
    "_documents",
    "_gaps",
    "_input_names",
    "_integer",
    "_limitations",
    "_ordered_unique",
    "_read",
    "_reference",
    "_rows",
    "_safe_path",
    "_same",
    "_scope",
    "_validate_context",
    "_validate_inventory",
    "timeline",
    "_verify_prepared",
]


def prepare(
    prepared: Path,
    source: Path,
    output: Path,
    *,
    run_id: str,
    start_us: int,
    end_us: int,
    max_events: int = MAX_EVENTS,
    max_bytes: int = MAX_BYTES,
) -> Document:
    """Write a fresh bundle; manifest.json alone seals a completed attempt."""
    target = destination(output, output.absolute().name)
    _scope(run_id, start_us, end_us)
    _integer(max_events, 1, MAX_EVENTS)
    _integer(max_bytes, 1, MAX_BYTES)
    gps, battery, states, count, gaps, inventory = _verify_prepared(prepared, source)
    events, context = timeline(
        gps,
        battery,
        states,
        run_id=run_id,
        start_us=start_us,
        end_us=end_us,
        battery_source_count=count,
        state_gaps=gaps,
        max_events=max_events,
    )
    lines = []
    size = 0
    for event in events:
        line = event_bytes(event) + b"\n"
        size += len(line)
        if size > max_bytes:
            raise ValueError("stream_output_byte_limit")
        lines.append(line)
    event_body = b"".join(lines)
    context_body = json_line(context)
    manifest: Document = {
        "profile": BUNDLE_PROFILE,
        "source_id": F09_SOURCE_ID,
        "run_id": run_id,
        "start_us": start_us,
        "end_us": end_us,
        "events": len(events),
        "stream_counts": {
            stream: sum(event["stream"] == stream for event in events)
            for stream in STREAMS
        },
        "predecessor_count": len(_documents(context["predecessors"], 3)),
        "files": {
            "events.jsonl": _reference(event_body),
            "context.json": _reference(context_body),
        },
        "input_artifacts": inventory,
        "limitations": list(LIMITATIONS),
    }
    manifest_body = json_line(manifest)
    if len(event_body) + len(context_body) + len(manifest_body) > max_bytes:
        raise ValueError("stream_output_byte_limit")
    target.mkdir()
    for name, body in (("events.jsonl", event_body), ("context.json", context_body)):
        with (target / name).open("xb") as handle:
            handle.write(body)
    pending = target / ".manifest.pending"
    with pending.open("xb") as handle:
        handle.write(manifest_body)
    # Existing atomic no-replace publication also applies to a regular file.
    # Failure retains the pending evidence without a completion manifest.
    publish_run(pending, target / "manifest.json")
    return manifest


def load_bundle(directory: Path) -> tuple[list[Document], Document, Document]:
    """Verify content, ordering and scope even when modified bytes were rehashed."""
    root = _safe_path(directory)
    if not root.is_dir() or {path.name for path in root.iterdir()} != {
        "events.jsonl",
        "context.json",
        "manifest.json",
    }:
        raise ValueError("stream_bundle_files")
    manifest_body = _read(root / "manifest.json", 32_000)
    manifest = json_object(manifest_body)
    require_keys(manifest, _MANIFEST_KEYS)
    run, start, end = _scope(
        manifest["run_id"], manifest["start_us"], manifest["end_us"]
    )
    if manifest["profile"] != BUNDLE_PROFILE or manifest["source_id"] != F09_SOURCE_ID:
        raise ValueError("stream_bundle_profile")
    count = _integer(manifest["events"], 1, MAX_EVENTS)
    _integer(manifest["predecessor_count"], 0, 3)
    _limitations(manifest["limitations"])
    _validate_inventory(manifest["input_artifacts"])
    files = object_value(manifest["files"])
    require_keys(files, {"events.jsonl", "context.json"})
    event_body = _read(root / "events.jsonl", MAX_BYTES - len(manifest_body))
    remaining = MAX_BYTES - len(event_body) - len(manifest_body)
    if remaining <= 0:
        raise ValueError("stream_bundle_byte_limit")
    context_body = _read(root / "context.json", remaining)
    if len(event_body) + len(context_body) + len(manifest_body) > MAX_BYTES:
        raise ValueError("stream_bundle_byte_limit")
    _check_reference(files["events.jsonl"], event_body)
    _check_reference(files["context.json"], context_body)
    context = json_object(context_body)
    predecessors = _validate_context(context)
    if any(
        context[key] != manifest[key]
        for key in ("source_id", "run_id", "start_us", "end_us")
    ) or manifest["predecessor_count"] != len(predecessors):
        raise ValueError("stream_bundle_context_scope")
    events: list[Document] = []
    seen: set[str] = {string_value(event["measurement_id"]) for event in predecessors}
    previous: tuple[int, int, int] | None = None
    for line in event_body.splitlines():
        if len(events) >= count:
            raise ValueError("stream_bundle_count")
        event = read_event(line)
        identity = string_value(event["measurement_id"])
        order = event_order(event)
        if (
            event["run_id"] != run
            or not start <= integer_value(event["native_timestamp_us"]) < end
            or identity in seen
            or (previous is not None and order <= previous)
        ):
            raise ValueError("stream_bundle_event_scope")
        if event["stream"] == STREAMS[0] and integer_value(event["source_ordinal"]) >= (
            integer_value(context["battery_source_count"])
        ):
            raise ValueError("stream_battery_source_count")
        seen.add(identity)
        events.append(event)
        previous = order
    if len(events) != count or not any(
        event["stream"] == STREAMS[3] for event in events
    ):
        raise ValueError("stream_bundle_count")
    counts = object_value(manifest["stream_counts"])
    require_keys(counts, set(STREAMS))
    for stream in STREAMS:
        if _integer(counts[stream], 0, MAX_EVENTS) != sum(
            event["stream"] == stream for event in events
        ):
            raise ValueError("stream_bundle_stream_counts")
    ordered = _ordered_unique(predecessors + events)
    prior_streams = {event["stream"] for event in predecessors}
    for stream in STREAMS[1:]:
        ordinals = [
            integer_value(event["source_ordinal"])
            for event in ordered
            if event["stream"] == stream
        ]
        if any(b != a + 1 for a, b in pairwise(ordinals)):
            raise ValueError("stream_bundle_source_coverage")
        if (
            stream in STREAMS[1:3]
            and ordinals
            and stream not in prior_streams
            and ordinals[0] != 0
        ):
            raise ValueError("stream_bundle_source_coverage")
    validate_battery_gaps(ordered, context)
    return events, context, manifest


class _Arguments(argparse.Namespace):
    prepared: Path
    source: Path
    output: Path
    run_id: str
    start_us: int
    end_us: int
    max_events: int
    max_bytes: int


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # argparse's default error echoes supplied paths/values.
        self.exit(2, '{"status":"failed","reason":"stream_arguments"}\n')


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    for name in ("prepared", "source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start-us", type=int, required=True)
    parser.add_argument("--end-us", type=int, required=True)
    parser.add_argument("--max-events", type=int, default=MAX_EVENTS)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args(argv, namespace=_Arguments())
    try:
        report = prepare(
            args.prepared,
            args.source,
            args.output,
            run_id=args.run_id,
            start_us=args.start_us,
            end_us=args.end_us,
            max_events=args.max_events,
            max_bytes=args.max_bytes,
        )
    except (ValueError, OSError, KeyError, TypeError, ImportError, RecursionError):
        print(
            '{"status":"failed","reason":"stream_preparation_failed"}',
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps({"status": "completed", "events": report["events"]}, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
