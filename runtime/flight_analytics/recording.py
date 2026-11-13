"""Prepare one supported original log and inspect its associated recorded state."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError
from pathlib import Path

from runtime.flight_analytics.battery_time import BatteryPoint, match_publications
from runtime.flight_analytics.gps import prepare as prepare_gps
from runtime.flight_analytics.state import FIELDS, VALUES, prepare, read_prepared
from runtime.flight_analytics.state_time import (
    Gap,
    StatePoint,
    match_states,
    source_gaps,
)
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.jobs import load_job
from telemetry.local_io import destination, read_bounded
from telemetry.models import ULogBatteryEnvelope, ULogSourceManifest
from telemetry.serving_sink import SinkError
from telemetry_convert import convert_job
from telemetry_reader import read_battery_event
from ulog_integrity import F09_SOURCE_ID

PROFILE = "f09-recording-inspection-v1"
MAX_INSPECTION_BYTES = 64 * 1024 * 1024


def combine(
    gps: list[dict[str, object]],
    states: list[dict[str, object]],
    battery: list[ULogBatteryEnvelope],
    source_count: int,
    gaps: list[Gap],
    max_age_us: int,
) -> list[dict[str, object]]:
    """Combine adapter-checked rows, keeping each association's own quality rule.

    GPS rows define the inspection timeline; they are not synchronized physical
    samples. A battery rejection gap is distinct from a state recording mask.
    """
    if type(max_age_us) is not int or not 0 <= max_age_us <= 60_000_000:
        raise ValueError("inspection_age_limit")
    if not 0 < len(gps) <= 25_000 or not 0 < len(battery) <= 100_000:
        raise ValueError("inspection_row_limit")
    if [row.get("source_ordinal") for row in gps] != list(range(len(gps))):
        raise ValueError("inspection_gps_ordinals")
    times = [integer_value(row["native_timestamp_us"]) for row in gps]
    battery_by_id = {event["event_id"]: event for event in battery}
    state_by_id = {string_value(row["event_id"]): row for row in states}
    if len(battery_by_id) != len(battery) or len(state_by_id) != len(states):
        raise ValueError("inspection_duplicate_identity")
    points = []
    for event in battery:
        source_time = event["source_time"]
        if (
            event["source_log_id"] != F09_SOURCE_ID
            or source_time["clock_basis"] != "boot_relative"
            or source_time["timestamp_kind"] != "publication"
        ):
            raise ValueError("inspection_battery_profile")
        points.append(
            BatteryPoint(
                event["source_record_index"],
                source_time["native_timestamp_us"],
                event["event_id"],
            )
        )
    battery_matches = match_publications(times, points, source_count, max_age_us)
    state_matches = {
        stream: match_states(
            times,
            [
                StatePoint(
                    integer_value(row["source_ordinal"]),
                    integer_value(row["native_timestamp_us"]),
                    string_value(row["event_id"]),
                )
                for row in states
                if row["stream"] == stream
            ],
            gaps,
            max_age_us,
        )
        for stream in FIELDS
    }
    result: list[dict[str, object]] = []
    for index, (row, match) in enumerate(zip(gps, battery_matches, strict=True)):
        battery_event = (
            battery_by_id[match.event_id] if match.event_id is not None else None
        )
        associated_states: dict[str, object] = {}
        for stream in FIELDS:
            state_match = state_matches[stream][index]
            state = (
                state_by_id[state_match.event_id]
                if state_match.event_id is not None
                else None
            )
            associated_states[stream] = {
                "status": state_match.status,
                "event_id": state_match.event_id,
                "age_us": state_match.age_us,
                "values": (
                    {name: state[name] for name in VALUES if name in FIELDS[stream]}
                    if state is not None
                    else None
                ),
            }
        result.append(
            {
                "gps": row,
                "battery": {
                    "status": match.status,
                    "event_id": match.event_id,
                    "age_us": match.age_us,
                    "values": (
                        battery_event["payload"] if battery_event is not None else None
                    ),
                },
                "states": associated_states,
            }
        )
    return result


def connect(job_path: Path, output: Path, max_age_us: int) -> dict[str, object]:
    """Prepare a fresh restricted inspection without service or database writes.

    An interrupted attempt is retained. Only recording.json marks completion;
    partial output must not be reused or deleted automatically.
    """
    target = destination(output, output.name)
    if type(max_age_us) is not int or not 0 <= max_age_us <= 60_000_000:
        raise ValueError("inspection_age_limit")
    job = load_job(job_path)
    if (
        job.mode != "ulog"
        or job.expectation.source_log_id != F09_SOURCE_ID
        or not isinstance(job.manifest, ULogSourceManifest)
        or job.manifest.normalization_version != "ulog-battery-f09-research-v1"
        or job.manifest.vehicle_id != "f09-research-vehicle"
    ):
        raise ValueError("unsupported_recording_profile")
    # Each adapter rechecks original bytes; no filtered derivative is admitted.
    # The target is fresh, and a partial result never receives a completion seal.
    target.mkdir()
    gps_manifest = prepare_gps(job.input_path, target / "gps")
    state_manifest = prepare(job.input_path, target / "state")
    (target / "battery").mkdir()
    battery_result = convert_job(
        job_path, target / "battery" / job.delivery.dataset_run_id
    )
    if battery_result.run_manifest["job_sha256"] != job.config_sha256:
        raise ValueError("inspection_job_changed")
    gps = [
        json_object(line)
        for line in read_bounded(target / "gps/gps.jsonl", 32_000_000).splitlines()
    ]
    states = read_prepared(target / "state")
    battery: list[ULogBatteryEnvelope] = []
    for line in read_bounded(
        battery_result.output_directory / "events.jsonl", 32_000_000
    ).splitlines():
        event = read_battery_event(line)
        if event["source_type"] != "ulog":
            raise ValueError("inspection_battery_profile")
        battery.append(event)
    gaps, original_evidence = source_gaps(job.input_path, gps, states)
    counts = object_value(battery_result.run_manifest["counts"])
    rows = combine(
        gps,
        states,
        battery,
        integer_value(counts["source_records"]),
        gaps,
        max_age_us,
    )
    digest = hashlib.sha256()
    size = 0
    statuses: dict[str, Counter[str]] = {
        name: Counter() for name in ("battery", *FIELDS)
    }
    with (target / "inspection.jsonl").open("xb") as handle:
        for row in rows:
            line = json_line(row)
            size += len(line)
            if size > MAX_INSPECTION_BYTES:
                raise ValueError("inspection_byte_limit")
            handle.write(line)
            digest.update(line)
            battery_status = string_value(object_value(row["battery"])["status"])
            statuses["battery"][battery_status] += 1
            selected = object_value(row["states"])
            for stream in FIELDS:
                statuses[stream][
                    string_value(object_value(selected[stream])["status"])
                ] += 1
    report: dict[str, object] = {
        "profile": PROFILE,
        "status": "completed_with_quality_limits",
        "privacy": "restricted",
        "source_id": F09_SOURCE_ID,
        "vehicle_id": job.manifest.vehicle_id,
        "inspection_records": len(rows),
        "inspection_sha256": digest.hexdigest(),
        "max_age_us": max_age_us,
        "association_status_counts": {
            name: dict(sorted(value.items())) for name, value in statuses.items()
        },
        "gps": gps_manifest,
        "state": state_manifest,
        "battery_counts": counts,
        "battery_semantic_sha256": battery_result.run_manifest["semantic_sha256"],
        "battery_rejection_reasons": battery_result.run_manifest["rejection_reasons"],
        "original_evidence": original_evidence,
        "limitations": [
            "exact F09 research source; physical producer unverified",
            "historical recording; no current connection or freshness claim",
            "common native boot clock assumed; no proven physical synchronization",
            "GPS receiver UTC is display time; battery UTC anchor is synthetic",
            "battery rejection gaps and state recording masks have distinct meanings",
            "source loss count unknown; matched does not establish completeness",
            "no state durations, physical flight phases or integrated Kafka replay",
        ],
    }
    with (target / "recording.json").open("xb") as handle:
        handle.write(json_line(report))
    return report


class _Arguments(argparse.Namespace):
    job: Path | None
    source: Path | None
    prepared: Path | None
    output: Path | None
    max_age_us: int | None
    serve: bool
    port: int


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--job", type=Path)
    inputs.add_argument("--source", type=Path, help="Registered F01 original bytes")
    inputs.add_argument("--prepared", type=Path, help="Verify a retained inspection")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-age-us", type=int)
    parser.add_argument(
        "--serve", action="store_true", help="Load shared local SQL view"
    )
    parser.add_argument("--port", type=int, default=28132)
    args = parser.parse_args(argv, namespace=_Arguments())
    try:
        from runtime.flight_analytics.recording_store import load, project

        if args.prepared is not None:
            if args.output is not None or args.max_age_us is not None:
                raise ValueError("prepared_options_conflict")
            directory = args.prepared
            project(directory)
            report = json_object(read_bounded(directory / "recording.json", 32_000))
        else:
            if args.output is None or args.max_age_us is None:
                raise ValueError("output_and_age_required")
            directory = args.output
            if args.source is not None:
                from runtime.flight_analytics.f01 import prepare as prepare_f01

                report = prepare_f01(args.source, directory, args.max_age_us)
            else:
                assert args.job is not None
                report = connect(args.job, directory, args.max_age_us)
        serving = load(directory, args.port) if args.serve else None
    except (ValueError, OSError, KeyError, PackageNotFoundError, SinkError) as error:
        # Do not expose source values, paths, coordinates or credentials in errors.
        reason = str(error) if isinstance(error, ValueError) else "io_or_shape_failure"
        if not reason.isidentifier():
            reason = "validation_failure"
        print(json.dumps({"status": "failed", "reason": reason}), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": report["status"],
                "inspection_records": report["inspection_records"],
                "association_status_counts": report["association_status_counts"],
                "serving": serving,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
