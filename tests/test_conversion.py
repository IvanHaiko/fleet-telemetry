"""File-boundary evidence: reconciliation, replay and failure before publication."""

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest
from conversion_support import (
    FIXTURES,
    ULOG_AVAILABLE,
    assert_no_output,
    obj,
    read_json,
    read_lines,
    rewrite_job,
    values,
    write_job,
)
from ulog_binary import synthetic_log

import telemetry_convert as converter
from fleet_telemetry import (
    BatteryEnvelope,
    Rejection,
    SourceManifest,
    normalize_battery,
)
from telemetry import artifacts
from telemetry.validation import InvalidInput as _InvalidInput
from telemetry_convert import ConversionError, convert_job, load_job, verify_job
from ulog_integrity import InputIntegrityError


def test_synthetic_two_runs_match_existing_independent_golden_outputs(
    tmp_path: Path,
) -> None:
    one = write_job(tmp_path)
    two = write_job(tmp_path, run_id="run-002")
    spec = read_json(two)
    obj(spec["delivery"])["ingest_timestamp"] = "2026-10-20T00:00:00.999999Z"
    rewrite_job(two, spec)
    first = convert_job(one, tmp_path / "run-001")
    second = convert_job(two, tmp_path / "run-002")
    assert verify_job(one, tmp_path / "run-001") == first
    assert verify_job(two, tmp_path / "run-002") == second
    golden = read_json(FIXTURES / "expected-battery-v1.json")
    expected = [obj(item) for item in values(golden["accepted"])]
    events = read_lines(tmp_path / "run-001/events.jsonl")
    assert [e["event_id"] for e in events] == [e["event_id"] for e in expected]
    assert [e["payload"] for e in events] == [e["payload"] for e in expected]
    assert [e["source_record_index"] for e in events] == [0, 2, 3]
    rejections = read_lines(tmp_path / "run-001/rejections.jsonl")
    assert rejections == [
        {
            "reason_code": "invalid_unit_value",
            "field": "voltage_mv",
            "source_record_index": 1,
            "source_manifest_id": "authored-file-v1",
            "source_stream": "battery_status:0",
        }
    ]
    assert first.run_manifest["counts"] == {
        "source_records": 4,
        "admitted_records": 3,
        "rejected_records": 1,
        "unique_events": 3,
        "duplicate_events": 0,
    }
    assert (
        first.run_manifest["semantic_sha256"] == second.run_manifest["semantic_sha256"]
    )
    assert first.run_manifest["job_sha256"] != second.run_manifest["job_sha256"]
    assert first.run_manifest["pipeline_version"] == "bounded-converter-v2"
    for name, info in obj(first.run_manifest["artifacts"]).items():
        content = (tmp_path / "run-001" / name).read_bytes()
        assert obj(info)["bytes"] == len(content)
        assert obj(info)["sha256"] == "sha256:" + sha256(content).hexdigest()
    assert read_json(tmp_path / "run-001/run-manifest.json") == first.run_manifest


@pytest.mark.ulog
@pytest.mark.skipif(not ULOG_AVAILABLE, reason="Install the pinned ulog extra.")
def test_binary_to_canonical_keeps_original_ordinals_after_value_rejection(
    tmp_path: Path,
) -> None:
    job = write_job(tmp_path, mode="ulog")
    result = convert_job(job, tmp_path / "run-001")
    events = read_lines(tmp_path / "run-001/events.jsonl")
    assert [e["source_record_index"] for e in events] == [0, 2]
    assert all(e["source_type"] == "synthetic" for e in events)
    assert all(e["normalization_version"] == "ulog-battery-v1" for e in events)
    assert [obj(e["source_time"])["timestamp_kind"] for e in events] == [
        "publication",
        "publication",
    ]
    assert [obj(e["payload"])["current_a"] for e in events] == [4.25, 0.0]
    assert (
        read_lines(tmp_path / "run-001/rejections.jsonl")[0]["source_record_index"] == 1
    )
    assert result.run_manifest["counts"] == {
        "source_records": 3,
        "admitted_records": 2,
        "rejected_records": 1,
        "unique_events": 2,
        "duplicate_events": 0,
    }
    assert obj(result.run_manifest["parser"])["version"] == "1.2.2"
    assert verify_job(job, tmp_path / "run-001") == result


def test_verification_detects_tampering_without_modifying_artifacts(
    tmp_path: Path,
) -> None:
    job = write_job(tmp_path)
    run = tmp_path / "run-001"
    convert_job(job, run)
    originals = {path.name: path.read_bytes() for path in run.iterdir()}
    events = read_lines(run / "events.jsonl")
    obj(events[0]["payload"])["voltage_v"] = 99.0

    def line(value: object) -> bytes:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()

    forged = b"".join(line(event) for event in events)
    manifest = read_json(run / "run-manifest.json")
    obj(manifest["artifacts"])["events.jsonl"] = {
        "bytes": len(forged),
        "sha256": "sha256:" + sha256(forged).hexdigest(),
    }
    semantic = b"".join(
        line(
            {
                "event_id": event["event_id"],
                "measurement": {key: event[key] for key in converter.SEMANTIC_FIELDS},
            }
        )
        for event in events
    )
    manifest["semantic_sha256"] = "sha256:" + sha256(semantic).hexdigest()
    cases = [
        {**originals, "events.jsonl": forged, "run-manifest.json": line(manifest)},
        {**originals, "run-manifest.json": originals["run-manifest.json"] + b" "},
        {**originals, "unexpected.txt": b"authored"},
        {name: data for name, data in originals.items() if name != "rejections.jsonl"},
    ]
    for files in cases:
        for path in run.iterdir():
            path.unlink()
        for name, content in files.items():
            (run / name).write_bytes(content)
        with pytest.raises(ConversionError):
            verify_job(job, run)
        assert {path.name: path.read_bytes() for path in run.iterdir()} == files
        assert not list(tmp_path.glob(".telemetry-stage-*"))


@pytest.mark.ulog
@pytest.mark.skipif(not ULOG_AVAILABLE, reason="Install the pinned ulog extra.")
@pytest.mark.parametrize(
    "data",
    [
        synthetic_log()[:-1],
        synthetic_log(invalid_bool=True),
        synthetic_log(decreasing_time=True),
    ],
    ids=["truncated-payload", "invalid-bool", "clock-reset"],
)
def test_binary_whole_source_failure_publishes_nothing(
    tmp_path: Path, data: bytes
) -> None:
    job = write_job(tmp_path, mode="ulog", payload=data)
    with pytest.raises(InputIntegrityError):
        convert_job(job, tmp_path / "run-001")
    assert_no_output(tmp_path)


def test_source_alteration_against_trusted_receipt_publishes_nothing(
    tmp_path: Path,
) -> None:
    job = write_job(tmp_path)
    with (tmp_path / "input.json").open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(ConversionError, match="source_bytes_mismatch"):
        convert_job(job, tmp_path / "run-001")
    assert_no_output(tmp_path)


def test_output_budget_fails_before_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = write_job(tmp_path)
    monkeypatch.setattr(artifacts, "MAX_OUTPUT_BYTES", 1000)
    with pytest.raises(ConversionError, match="output_budget_exceeded"):
        convert_job(job, tmp_path / "run-001")
    assert_no_output(tmp_path)


def test_all_rejected_source_has_explicit_reconciled_result(tmp_path: Path) -> None:
    data = read_json(FIXTURES / "synthetic-battery-v1.json")
    for value in values(data["records"]):
        obj(value)["voltage_mv"] = -1
    job = write_job(tmp_path, payload=json.dumps(data).encode())
    result = convert_job(job, tmp_path / "run-001")
    assert result.run_manifest["status"] == "completed_with_rejections"
    assert obj(result.run_manifest["counts"])["source_records"] == 4
    assert obj(result.run_manifest["counts"])["admitted_records"] == 0
    assert (tmp_path / "run-001/events.jsonl").read_bytes() == b""
    assert len(read_lines(tmp_path / "run-001/rejections.jsonl")) == 4


@pytest.mark.parametrize("conflict", [False, True])
def test_identity_fault_is_detected_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conflict: bool
) -> None:
    job = write_job(tmp_path)
    original = normalize_battery
    first: BatteryEnvelope | None = None

    def faulty_normalizer(*args: object) -> BatteryEnvelope:
        nonlocal first
        if first is None:
            record = load_job(job)
            manifest = record.manifest
            anchor = manifest.clock_anchor
            delivery = record.delivery
            assert isinstance(manifest, SourceManifest)
            native = obj(values(read_json(record.input_path)["records"])[0])
            valid = original(native, manifest, anchor, delivery)
            assert not isinstance(valid, Rejection)
            first = valid
        result = copy.deepcopy(first)
        if conflict and len(args) > 0 and obj(args[0]).get("source_record_index") != 0:
            result["payload"]["voltage_v"] = 99.0
        return result

    monkeypatch.setattr(artifacts, "normalize_battery", faulty_normalizer)
    with pytest.raises(
        ConversionError, match="identity_conflict" if conflict else "duplicate_identity"
    ):
        convert_job(job, tmp_path / "run-001")
    assert_no_output(tmp_path)


@pytest.mark.parametrize(
    "change",
    [
        "unknown_key",
        "wrong_version",
        "wrong_generator",
        "oversize_identifier",
        "invalid_run",
        "missing_anchor",
    ],
)
def test_strict_job_context_fails_before_output(tmp_path: Path, change: str) -> None:
    job = write_job(tmp_path)
    spec = read_json(job)
    if change == "unknown_key":
        spec["unexpected"] = True
    elif change == "wrong_version":
        spec["job_version"] = "other"
    elif change == "wrong_generator":
        obj(spec["manifest"])["parser_version"] = "made-up-v99"
    elif change == "oversize_identifier":
        obj(spec["manifest"])["vehicle_id"] = "x" * 257
    elif change == "invalid_run":
        obj(spec["delivery"])["dataset_run_id"] = "../run"
    else:
        del obj(spec["manifest"])["clock_anchor"]
    rewrite_job(job, spec)
    with pytest.raises((ConversionError, _InvalidInput)):
        convert_job(job, tmp_path / "run-001")
    assert_no_output(tmp_path)


@pytest.mark.parametrize(
    "raw", [b'{"job_version":"a","job_version":"b"}', b'{"job_version":NaN}']
)
def test_duplicate_keys_and_nonfinite_json_are_not_coerced(
    tmp_path: Path, raw: bytes
) -> None:
    job = tmp_path / "job.json"
    job.write_bytes(raw)
    with pytest.raises(ConversionError):
        load_job(job)


def test_invalid_source_positions_fail_without_renumbering(tmp_path: Path) -> None:
    data = read_json(FIXTURES / "synthetic-battery-v1.json")
    obj(values(data["records"])[2])["source_record_index"] = 1
    job = write_job(tmp_path, payload=json.dumps(data).encode())
    with pytest.raises(ConversionError, match="invalid_source_positions"):
        convert_job(job, tmp_path / "run-001")
    assert_no_output(tmp_path)
