"""Authored replay invariants; private F09 reconciliation belongs to integration."""

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import BinaryIO, cast
from unittest.mock import patch

import pytest

pytest.importorskip(
    "pyulog", reason="Install the pinned ulog extra for recording tests."
)
from recording_stream_support import battery, gps, state

from runtime.flight_analytics import stream_reference
from runtime.flight_analytics.recording import combine
from runtime.flight_analytics.state_time import Gap
from telemetry.conversion_contract import json_line, json_object, object_value
from telemetry.models import ULogBatteryEnvelope
from telemetry.recording_processing import FACT_PROFILE, process_events
from telemetry.recording_stream import event_bytes, event_order, make_event
from ulog_integrity import F09_SOURCE_ID

type Document = dict[str, object]

RUN = "authored-replay"
BATTERY = "battery_status:0"
GPS = "vehicle_gps_position:0"
LAND = "vehicle_land_detected:0"
STATUS = "vehicle_status:0"


def context(start: int = 0, end: int = 500) -> Document:
    return {
        "profile": "f09-recording-context-v1",
        "source_id": F09_SOURCE_ID,
        "run_id": RUN,
        "start_us": start,
        "end_us": end,
        "battery_source_count": 3,
        "predecessors": [],
        "battery_gaps": [],
        "state_gaps": [],
    }


def inspection(fact: Document) -> Document:
    return object_value(fact["inspection"])


def section(fact: Document, name: str) -> Document:
    row = inspection(fact)
    if name == "battery":
        return object_value(row[name])
    return object_value(object_value(row["states"])[name])


def test_reference_equals_existing_combine_and_preserves_inputs() -> None:
    positions = [gps(i, stamp) for i, stamp in enumerate((99, 100, 150, 250, 300, 401))]
    batteries = [battery(0, 100), battery(2, 300)]
    states = [
        state(stream, ordinal, stamp)
        for ordinal, stamp in enumerate((100, 300))
        for stream in (LAND, STATUS)
    ]
    events = sorted(
        [make_event(GPS, row, RUN) for row in positions]
        + [make_event(BATTERY, row, RUN) for row in batteries]
        + [make_event(f"{row['stream']}:0", row, RUN) for row in states],
        key=event_order,
    )
    policy = context()
    policy["battery_gaps"] = [{"start_us": 100, "end_us": 300}]
    policy["state_gaps"] = [{"start_us": 250, "end_us": 300}]
    original = deepcopy((events, policy))
    facts = process_events(events, policy, max_age_us=100)
    expected = combine(
        positions,
        states,
        cast(list[ULogBatteryEnvelope], batteries),
        3,
        [Gap(250, 300)],
        100,
    )
    assert [inspection(fact) for fact in facts] == expected
    gps_events = [event for event in events if event["stream"] == GPS]
    for fact, event in zip(facts, gps_events, strict=True):
        assert fact == {
            "profile": FACT_PROFILE,
            "source_id": F09_SOURCE_ID,
            "run_id": RUN,
            "measurement_id": event["measurement_id"],
            "native_timestamp_us": event["native_timestamp_us"],
            "input_event_sha256": hashlib.sha256(event_bytes(event)).hexdigest(),
            "inspection": inspection(fact),
        }
    assert (events, policy) == original
    # Returned nested values must not alias mutable caller payloads.
    object_value(inspection(facts[0])["gps"])["fix_type"] = 0
    assert (events, policy) == original


def test_predecessors_gap_precedence_and_inclusive_age() -> None:
    policy = context(150)
    policy["predecessors"] = [
        make_event(LAND, state(LAND, 0, 100), RUN),
        make_event(BATTERY, battery(0, 100), RUN),
    ]
    policy["battery_gaps"] = [{"start_us": 200, "end_us": None}]
    policy["state_gaps"] = [{"start_us": 150, "end_us": 200}]
    events = sorted(
        [
            make_event(GPS, gps(i, stamp), RUN)
            for i, stamp in enumerate((150, 151, 200, 251))
        ]
        + [
            make_event(BATTERY, battery(1, 200), RUN),
            make_event(LAND, state(LAND, 1, 200), RUN),
            make_event(STATUS, state(STATUS, 0, 200), RUN),
        ],
        key=event_order,
    )
    facts = process_events(events, policy, max_age_us=50)
    assert [section(f, "battery")["status"] for f in facts] == [
        "matched",
        "stale",
        "matched",
        "rejection_gap",
    ]
    assert section(facts[0], "battery")["age_us"] == 50
    assert section(facts[2], "battery")["age_us"] == 0
    assert [section(f, "vehicle_land_detected")["status"] for f in facts] == [
        "recording_gap",
        "recording_gap",
        "matched",
        "stale",
    ]
    assert [section(f, "vehicle_status")["status"] for f in facts] == [
        "before_first",
        "before_first",
        "matched",
        "stale",
    ]
    for fact in facts:
        for name in ("battery", "vehicle_land_detected", "vehicle_status"):
            association = section(fact, name)
            if association["status"] != "matched":
                assert association == {
                    "status": association["status"],
                    "event_id": None,
                    "age_us": None,
                    "values": None,
                }


def test_late_exact_duplicates_never_repeat_gps_or_replace_newer_state() -> None:
    first = [
        make_event(BATTERY, battery(0, 100), RUN),
        make_event(LAND, state(LAND, 0, 100), RUN),
        make_event(STATUS, state(STATUS, 0, 100), RUN),
        make_event(GPS, gps(0, 100), RUN),
    ]
    second = [
        make_event(BATTERY, battery(1, 200), RUN),
        make_event(LAND, state(LAND, 1, 200), RUN),
        make_event(STATUS, state(STATUS, 1, 200), RUN),
        make_event(GPS, gps(1, 200), RUN),
    ]
    last = make_event(GPS, gps(2, 250), RUN)
    expected = process_events(first + second + [last], context(), max_age_us=50)
    actual = process_events(first + second + first + [last], context(), max_age_us=50)
    assert actual == expected and len(actual) == 3
    for name in ("battery", "vehicle_land_detected", "vehicle_status"):
        assert section(actual[-1], name)["age_us"] == 50


def test_identity_conflicts_and_malformed_order_refuse() -> None:
    initial = make_event(GPS, gps(0, 100), RUN)
    with pytest.raises(ValueError, match="processing_identity_conflict"):
        process_events([initial, make_event(GPS, gps(0, 101), RUN)], context())
    with pytest.raises(ValueError, match="processing_event_order"):
        process_events([initial, make_event(BATTERY, battery(0, 100), RUN)], context())
    with pytest.raises(ValueError, match="processing_stream_order"):
        process_events([initial, make_event(GPS, gps(1, 99), RUN)], context())
    with pytest.raises(ValueError, match="processing_stream_order"):
        process_events(
            [make_event(GPS, gps(1, 100), RUN), make_event(GPS, gps(0, 200), RUN)],
            context(),
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("extra", None),
        ("run_id", "unsafe/run"),
        ("source_id", "wrong"),
        ("start_us", True),
        ("end_us", 1 << 64),
        ("battery_source_count", False),
        ("battery_gaps", [{"start_us": 100, "end_us": 100}]),
        ("state_gaps", [{"start_us": float("nan"), "end_us": None}]),
    ],
)
def test_strict_context_refuses(key: str, value: object) -> None:
    policy = context()
    policy[key] = value
    with pytest.raises(ValueError):
        process_events([make_event(GPS, gps(), RUN)], policy)


def test_scope_predecessors_and_resource_limits_refuse() -> None:
    event = make_event(GPS, gps(), RUN)
    with pytest.raises(ValueError, match="processing_event_scope"):
        process_events([event], context(101))
    with pytest.raises(ValueError, match="processing_event_scope"):
        process_events([event], context(0, 100))
    with pytest.raises(ValueError, match="processing_event_scope"):
        process_events([make_event(GPS, gps(), "other-run")], context())
    for predecessor in (event, make_event(BATTERY, battery(), RUN)):
        policy = context(100)
        policy["predecessors"] = [predecessor]
        with pytest.raises(ValueError, match="processing_predecessor_scope"):
            process_events([event], policy)
    policy = context(101)
    predecessor = make_event(BATTERY, battery(), RUN)
    policy["predecessors"] = [predecessor, predecessor]
    with pytest.raises(ValueError, match="processing_predecessor_scope"):
        process_events([event], policy)
    for limit in (True, 0, 50_001):
        with pytest.raises(ValueError, match="processing_event_limit"):
            process_events([event], context(), max_events=limit)
    for age in (True, -1, 60_000_001):
        with pytest.raises(ValueError, match="processing_age_limit"):
            process_events([event], context(), max_age_us=age)
    with pytest.raises(ValueError, match="processing_event_limit"):
        process_events([event, event], context(), max_events=1)
    policy = context(150)
    policy["predecessors"] = [make_event(BATTERY, battery(), RUN)]
    with pytest.raises(ValueError, match="processing_identity_limit"):
        process_events([make_event(GPS, gps(0, 150), RUN)], policy, max_events=1)
    assert len(process_events([event], context(), max_events=1, max_age_us=0)) == 1
    with pytest.raises(ValueError, match="processing_empty_gps_interval"):
        process_events([], context())


def test_reference_cli_seals_hashes_and_refuses_existing_output_before_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle = tmp_path / "authored-bundle"
    bundle.mkdir()
    input_manifest: Document = {"profile": "authored-loader-boundary"}
    raw_manifest = json_line(input_manifest)
    (bundle / "manifest.json").write_bytes(raw_manifest)
    calls: list[Path] = []

    def load(directory: Path) -> tuple[list[Document], Document, Document]:
        calls.append(directory)
        return [make_event(GPS, gps(), RUN)], context(), input_manifest

    # Exercise the reference writer; actual bundle admission is owned by B.
    monkeypatch.setattr(stream_reference, "load_bundle", load)
    output = tmp_path / "reference"
    args = ["--bundle", str(bundle), "--output", str(output), "--max-age-us", "0"]
    assert stream_reference.main(args) == 0
    report = json_object((output / "manifest.json").read_bytes())
    facts = (output / "facts.jsonl").read_bytes()
    assert report["profile"] == "f09-recording-reference-v1"
    assert report["source_id"] == F09_SOURCE_ID and report["run_id"] == RUN
    assert report["facts"] == 1 and report["max_age_us"] == 0
    assert (
        report["input_bundle_manifest_sha256"]
        == hashlib.sha256(raw_manifest).hexdigest()
    )
    assert report["files"] == {
        "facts.jsonl": {
            "bytes": len(facts),
            "sha256": hashlib.sha256(facts).hexdigest(),
        }
    }
    assert json_object(facts)["measurement_id"] == gps()["event_id"]
    assert json.loads(capsys.readouterr().out) == {"status": "completed", "facts": 1}
    assert stream_reference.main(args) == 2
    assert calls == [bundle]
    assert (output / "facts.jsonl").read_bytes() == facts

    def fail(directory: Path) -> tuple[list[Document], Document, Document]:
        raise ValueError("private-source-path-and-payload")

    monkeypatch.setattr(stream_reference, "load_bundle", fail)
    partial = tmp_path / "partial"
    assert (
        stream_reference.main(["--bundle", str(bundle), "--output", str(partial)]) == 2
    )
    assert partial.is_dir() and not (partial / "manifest.json").exists()
    captured = capsys.readouterr()
    assert not captured.out
    assert "private-source" not in captured.err and str(tmp_path) not in captured.err

    monkeypatch.setattr(stream_reference, "load_bundle", load)
    monkeypatch.setattr(stream_reference, "MAX_BYTES", 128)
    bounded = tmp_path / "bounded"
    assert (
        stream_reference.main(["--bundle", str(bundle), "--output", str(bounded)]) == 2
    )
    assert (bounded / "facts.jsonl").is_file()
    assert not (bounded / "manifest.json").exists()

    with pytest.raises(SystemExit) as error:
        stream_reference.main(["--max-age-us", "private-source-path"])
    assert error.value.code == 2
    assert "private-source-path" not in capsys.readouterr().err


@pytest.mark.parametrize("failure", ["write", "close"])
def test_manifest_io_failure_never_publishes_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    input_manifest: Document = {"profile": "authored-loader-boundary"}
    raw_manifest = json_line(input_manifest)
    (bundle / "manifest.json").write_bytes(raw_manifest)

    def load(directory: Path) -> tuple[list[Document], Document, Document]:
        assert directory == bundle
        return [make_event(GPS, gps(), RUN)], context(), input_manifest

    monkeypatch.setattr(stream_reference, "load_bundle", load)
    original_open = Path.open
    output = tmp_path / "failed-reference"

    @contextmanager
    def failing_open(path: Path, mode: str = "r") -> Iterator[BinaryIO]:
        handle = cast(BinaryIO, original_open(path, mode))
        manifest_write = path.parent == output and path.name in {
            "manifest.json",
            ".manifest.pending",
        }
        try:
            if manifest_write and failure == "write":
                original_write = handle.write

                def fail_write(data: bytes) -> int:
                    original_write(data[:8])
                    raise OSError("private-manifest-write-detail")

                with patch.object(handle, "write", side_effect=fail_write):
                    yield handle
            else:
                yield handle
        finally:
            handle.close()
            if manifest_write and failure == "close":
                raise OSError("private-manifest-close-detail")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", failing_open)
        result = stream_reference.main(
            ["--bundle", str(bundle), "--output", str(output)]
        )
    assert result == 2
    assert (output / "facts.jsonl").is_file()
    assert (output / ".manifest.pending").is_file()
    assert not (output / "manifest.json").exists()
    assert (bundle / "manifest.json").read_bytes() == raw_manifest
    captured = capsys.readouterr()
    assert not captured.out
    assert "private-manifest" not in captured.err and str(tmp_path) not in captured.err


def test_direct_processor_reconciles_battery_masks_with_accepted_ordinals() -> None:
    events = sorted(
        [
            make_event(BATTERY, battery(0, 100), RUN),
            make_event(BATTERY, battery(2, 200), RUN),
            make_event(GPS, gps(0, 150), RUN),
            make_event(GPS, gps(1, 200), RUN),
        ],
        key=event_order,
    )
    policy = context()
    policy["battery_gaps"] = [{"start_us": 100, "end_us": 200}]
    original = deepcopy((events, policy))
    assert [
        section(fact, "battery")["status"] for fact in process_events(events, policy)
    ] == ["rejection_gap", "matched"]
    assert (events, policy) == original
    for gaps in ([], [{"start_us": 100, "end_us": None}]):
        bad = deepcopy(policy)
        bad["battery_gaps"] = gaps
        with pytest.raises(ValueError, match="stream_battery_gap_"):
            process_events(events, bad)
