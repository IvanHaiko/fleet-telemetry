"""Authored interval, integrity and safe-publication invariants; no real data."""

import copy
import hashlib
from pathlib import Path
from typing import cast

import pytest
from recording_stream_support import battery, gps, state

from runtime.flight_analytics import stream_prepare as subject
from telemetry.conversion_contract import json_line, json_object, object_value
from telemetry.recording_stream import STREAMS, event_bytes, event_order
from ulog_integrity import F09_SOURCE_ID

type Document = dict[str, object]


def inputs() -> tuple[list[Document], list[Document], list[Document]]:
    positions = [gps(i, stamp) for i, stamp in enumerate((99, 100, 150, 200, 299, 300))]
    batteries = [battery(i, stamp) for i, stamp in ((0, 50), (2, 100), (4, 200))]
    states = [
        state(stream, i, stamp)
        for stream in ("vehicle_land_detected", "vehicle_status")
        for i, stamp in enumerate((80, 100, 200))
    ]
    return positions, batteries, states


def selected() -> tuple[list[Document], Document]:
    positions, batteries, states = inputs()
    return subject.timeline(
        positions,
        batteries,
        states,
        run_id="interval-1",
        start_us=100,
        end_us=300,
        battery_source_count=6,
        state_gaps=[{"start_us": 99, "end_us": 101}],
    )


def write_bundle(directory: Path) -> tuple[list[Document], Document, Document]:
    """Author a tiny sealed wire bundle without claiming prepared-source bytes."""
    events, context = selected()
    directory.mkdir()
    bodies = {
        "events.jsonl": b"".join(event_bytes(event) + b"\n" for event in events),
        "context.json": json_line(context),
    }
    prepared_names = {
        "recording.json",
        "inspection.jsonl",
        "gps/manifest.json",
        "gps/gps.jsonl",
        "state/manifest.json",
        "state/state.jsonl",
        "battery/delivery/run-manifest.json",
        "battery/delivery/events.jsonl",
        "battery/delivery/rejections.jsonl",
    }
    inventory: Document = {
        "prepared/" + name: {"bytes": 1, "sha256": "0" * 64} for name in prepared_names
    }
    inventory["source.ulog"] = {
        "bytes": 122_463_132,
        "sha256": F09_SOURCE_ID.removeprefix("sha256:"),
    }
    manifest: Document = {
        "profile": "f09-recording-stream-bundle-v1",
        "source_id": F09_SOURCE_ID,
        "run_id": "interval-1",
        "start_us": 100,
        "end_us": 300,
        "events": len(events),
        "predecessor_count": 3,
        "stream_counts": {
            stream: sum(event["stream"] == stream for event in events)
            for stream in STREAMS
        },
        "files": {
            name: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            for name, body in bodies.items()
        },
        "input_artifacts": inventory,
        "limitations": ["authored protocol fixture; not source admission"],
    }
    for name, body in bodies.items():
        (directory / name).write_bytes(body)
    (directory / "manifest.json").write_bytes(json_line(manifest))
    return events, context, manifest


def rehash(directory: Path, name: str, body: bytes) -> None:
    (directory / name).write_bytes(body)
    manifest = json_object((directory / "manifest.json").read_bytes())
    object_value(manifest["files"])[name] = {
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    (directory / "manifest.json").write_bytes(json_line(manifest))


def test_timeline_keeps_original_ids_predecessors_and_distinct_masks() -> None:
    positions, batteries, states = inputs()
    original = copy.deepcopy((positions, batteries, states))
    events, context = selected()
    assert [event_order(event) for event in events] == sorted(map(event_order, events))
    assert [event["stream"] for event in events[:4]] == list(STREAMS)
    gps_events = [event for event in events if event["stream"] == STREAMS[3]]
    assert [event["source_ordinal"] for event in gps_events] == [1, 2, 3, 4]
    assert [event["payload"] for event in gps_events] == positions[1:5]
    assert [event["measurement_id"] for event in gps_events] == [
        row["event_id"] for row in positions[1:5]
    ]
    assert context["battery_gaps"] == [
        {"start_us": 50, "end_us": 100},
        {"start_us": 100, "end_us": 200},
        {"start_us": 200, "end_us": None},
    ]
    assert context["state_gaps"] == [{"start_us": 99, "end_us": 101}]
    predecessors = cast(list[Document], context["predecessors"])
    assert [event["stream"] for event in predecessors] == list(STREAMS[:3])
    assert [event["source_ordinal"] for event in predecessors] == [0, 0, 0]
    assert subject.timeline(
        positions,
        batteries,
        states,
        run_id="interval-1",
        start_us=100,
        end_us=300,
        battery_source_count=6,
        state_gaps=[{"start_us": 99, "end_us": 101}],
    ) == (events, context)
    assert (positions, batteries, states) == original


def test_duplicates_collapse_but_conflicts_reorder_and_lost_ordinals_refuse() -> None:
    positions, batteries, states = inputs()

    def run(rows: list[Document]) -> tuple[list[Document], Document]:
        return subject.timeline(
            rows,
            batteries,
            states,
            run_id="interval-1",
            start_us=100,
            end_us=300,
            battery_source_count=6,
            state_gaps=[],
        )

    assert run(positions + [positions[0]]) == run(positions)
    conflicting = {**positions[0], "ground_speed_m_s": 2.0}
    if conflicting["ground_speed_m_s"] == positions[0]["ground_speed_m_s"]:
        conflicting["ground_speed_m_s"] = 3.0
    with pytest.raises(ValueError, match="stream_identity_conflict"):
        run(positions + [conflicting])
    with pytest.raises(ValueError, match="stream_source_order"):
        run([positions[0], gps(1, 98), *positions[2:]])
    with pytest.raises(ValueError, match="stream_source_coverage"):
        run(positions[1:])


def test_interval_count_and_mask_limits_refuse_without_fabricating_times() -> None:
    positions, batteries, states = inputs()
    # Explicit calls retain typed public boundaries and reject bool-as-int inputs.
    with pytest.raises(ValueError):
        subject.timeline(
            positions,
            batteries,
            states,
            run_id="bounded",
            start_us=True,
            end_us=300,
            battery_source_count=6,
            state_gaps=[],
        )
    with pytest.raises(ValueError, match="stream_empty_gps_interval"):
        subject.timeline(
            positions,
            batteries,
            states,
            run_id="bounded",
            start_us=301,
            end_us=302,
            battery_source_count=6,
            state_gaps=[],
        )
    with pytest.raises(ValueError, match="stream_event_limit"):
        subject.timeline(
            positions,
            batteries,
            states,
            run_id="bounded",
            start_us=100,
            end_us=300,
            battery_source_count=6,
            state_gaps=[],
            max_events=1,
        )
    with pytest.raises(ValueError):
        subject.timeline(
            positions,
            batteries,
            states,
            run_id="bounded",
            start_us=100,
            end_us=300,
            battery_source_count=6,
            state_gaps=[],
            max_events=50001,
        )
    with pytest.raises(ValueError):
        subject.timeline(
            positions,
            batteries,
            states,
            run_id="bounded",
            start_us=100,
            end_us=300,
            battery_source_count=6,
            state_gaps=[{"start_us": 100, "end_us": 100}],
        )


def test_bundle_roundtrip_then_changed_bytes_and_rehashed_invalid_values_refuse(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "bundle"
    expected = write_bundle(directory)
    assert subject.load_bundle(directory) == expected
    context_path = directory / "context.json"
    original = context_path.read_bytes()
    context_path.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="stream_artifact_digest"):
        subject.load_bundle(directory)
    context = json_object(original)
    context["start_us"] = 101
    rehash(directory, "context.json", json_line(context))
    with pytest.raises(ValueError):
        subject.load_bundle(directory)
    rehash(directory, "context.json", original)
    event_body = (directory / "events.jsonl").read_bytes()
    records = [json_object(line) for line in event_body.splitlines()]
    records[0]["native_timestamp_us"] = 101
    rehash(directory, "events.jsonl", b"".join(json_line(row) for row in records))
    with pytest.raises(ValueError):
        subject.load_bundle(directory)


def test_missing_gap_duplicate_and_unsafe_inventory_refuse(tmp_path: Path) -> None:
    directory = tmp_path / "bundle"
    events, context, _ = write_bundle(directory)
    context["battery_gaps"] = []
    rehash(directory, "context.json", json_line(context))
    with pytest.raises(ValueError, match="stream_battery_gap_coverage"):
        subject.load_bundle(directory)
    _, context = selected()
    rehash(directory, "context.json", json_line(context))
    body = b"".join(event_bytes(event) + b"\n" for event in [*events[:-1], events[0]])
    rehash(directory, "events.jsonl", body)
    with pytest.raises(ValueError):
        subject.load_bundle(directory)
    manifest = json_object((directory / "manifest.json").read_bytes())
    object_value(manifest["input_artifacts"])["../outside"] = {
        "bytes": 1,
        "sha256": "0" * 64,
    }
    (directory / "manifest.json").write_bytes(json_line(manifest))
    with pytest.raises(ValueError, match="stream_input_inventory"):
        subject.load_bundle(directory)


def test_existing_output_limits_and_symlinks_refuse_before_source_reads(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "retained.txt"
    marker.write_text("retain", encoding="utf-8")
    with pytest.raises(ValueError, match="output_exists"):
        subject.prepare(
            tmp_path / "missing",
            tmp_path / "absent.ulg",
            tmp_path,
            run_id="safe",
            start_us=1,
            end_us=2,
        )
    with pytest.raises(ValueError, match="stream_integer_range"):
        subject.prepare(
            tmp_path / "missing",
            tmp_path / "absent.ulg",
            tmp_path / "fresh",
            run_id="safe",
            start_us=1,
            end_us=2,
            max_bytes=67108865,
        )
    directory = tmp_path / "bundle"
    write_bundle(directory)
    (directory / "unexpected").write_bytes(b"extra")
    with pytest.raises(ValueError, match="stream_bundle_files"):
        subject.load_bundle(directory)
    assert marker.read_text(encoding="utf-8") == "retain"
    assert not (tmp_path / "fresh").exists()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(directory, target_is_directory=True)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink creation privilege unavailable")
        raise
    with pytest.raises(ValueError, match="output_symlink_unsupported"):
        subject.load_bundle(alias)


def test_cli_errors_never_echo_sensitive_arguments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        subject.main(
            [
                "--prepared",
                str(tmp_path / "sensitive-prepared"),
                "--source",
                str(tmp_path / "private-source"),
                "--output",
                str(tmp_path),
                "--run-id",
                "safe",
                "--start-us",
                "1",
                "--end-us",
                "2",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "stream_preparation_failed" in captured.err
    assert str(tmp_path) not in captured.err
    with pytest.raises(SystemExit) as error:
        subject.main(["--start-us", "private-coordinate"])
    assert error.value.code == 2
    assert "private-coordinate" not in capsys.readouterr().err


def test_interrupted_seal_retains_partial_evidence_without_completion_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, fixture_manifest = write_bundle(tmp_path / "authored-wire")

    def retained(
        prepared: Path,
        source: Path,
    ) -> tuple[
        list[Document], list[Document], list[Document], int, list[Document], Document
    ]:
        # Isolate publication failure; this does not test original-byte admission.
        positions, batteries, states = inputs()
        return (
            positions,
            batteries,
            states,
            6,
            [],
            object_value(fixture_manifest["input_artifacts"]),
        )

    def interrupted(stage: Path, target: Path) -> None:
        raise OSError("authored publication interruption")

    monkeypatch.setattr(subject, "_verify_prepared", retained)
    monkeypatch.setattr(subject, "publish_run", interrupted)
    bounded = tmp_path / "too-small"
    with pytest.raises(ValueError, match="stream_output_byte_limit"):
        subject.prepare(
            tmp_path / "unused-prepared",
            tmp_path / "unused-source",
            bounded,
            run_id="interval-1",
            start_us=100,
            end_us=300,
            max_bytes=1,
        )
    assert not bounded.exists()
    target = tmp_path / "interrupted"
    with pytest.raises(OSError):
        subject.prepare(
            tmp_path / "unused-prepared",
            tmp_path / "unused-source",
            target,
            run_id="interval-1",
            start_us=100,
            end_us=300,
        )
    assert (target / "events.jsonl").is_file()
    assert (target / "context.json").is_file()
    assert (target / ".manifest.pending").is_file()
    assert not (target / "manifest.json").exists()
    with pytest.raises(ValueError, match="stream_bundle_files"):
        subject.load_bundle(target)
