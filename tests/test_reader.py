"""Consumer-boundary risks beyond existing producer/golden checks."""

import copy
import json
from pathlib import Path
from typing import cast

import pytest

import telemetry_reader as reader
from telemetry_reader import EnvelopeError, check_event_file, read_battery_event


def example() -> dict[str, object]:
    document = (Path(__file__).parents[1] / "docs/data-contracts.md").read_text(
        encoding="utf-8"
    )
    raw = (
        document.split("### Illustrative event", 1)[1]
        .split("```json", 1)[1]
        .split("```", 1)[0]
    )
    decoded: object = json.loads(raw)
    assert isinstance(decoded, dict)
    return cast(dict[str, object], decoded)


def obj(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def wire(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def test_optional_extensions_and_missing_values_keep_canonical_meanings() -> None:
    original = example()
    extended = copy.deepcopy(original)
    extended["future_optional"] = {"note": "valid extension", "values": [0, 1.25]}
    for key in ("payload", "delivery", "provenance"):
        obj(extended[key])["future_optional"] = ["kept outside recognized projection"]
    source_time = obj(extended["source_time"])
    source_time["future_optional"] = True
    obj(source_time["mapping"])["future_optional"] = "anchor annotation"
    assert read_battery_event(wire(extended)) == original
    payload = obj(extended["payload"])
    payload.pop("current_a")
    payload.pop("remaining_fraction")
    decoded = read_battery_event(wire(extended))
    assert decoded["payload"] == {
        "voltage_v": 15.8,
        "current_a": None,
        "remaining_fraction": None,
    }
    assert decoded["quality_flags"] == original["quality_flags"]
    payload["current_a"] = -4.2
    extended["quality_flags"] = ["synthetic_time_anchor", "future_quality_flag"]
    assert read_battery_event(wire(extended))["payload"]["current_a"] == -4.2
    assert (
        read_battery_event(wire(extended))["quality_flags"] == extended["quality_flags"]
    )


def test_invalid_identity_time_and_measurement_relations_are_rejected() -> None:
    mutations: list[tuple[str, object]] = [
        ("schema_version", "1.0.1"),
        ("event_id", "sha256:" + "0" * 64),
        ("source_record_index", True),
        ("source_timestamp", "2026-01-01T12:00:01.234568Z"),
        ("source_time.timestamp_kind", "publication"),
        ("source_time.mapping.anchor_uncertainty_us", True),
        ("source_time.mapping.utc_anchor", "9999-12-31T23:59:59.999999Z"),
        ("payload.current_a", True),
        ("payload.remaining_fraction", 72),
        ("provenance.privacy_classification", "restricted"),
        ("quality_flags", ["synthetic_time_anchor", "synthetic_time_anchor"]),
    ]
    for path, value in mutations:
        event = example()
        target = event
        fields = path.split(".")
        for field in fields[:-1]:
            target = obj(target[field])
        target[fields[-1]] = value
        with pytest.raises(EnvelopeError):
            read_battery_event(wire(event))
    missing = example()
    missing.pop("source_timestamp")
    with pytest.raises(EnvelopeError, match="missing_required_field"):
        read_battery_event(wire(missing))


def test_ignored_extensions_cannot_hide_invalid_json_or_numbers() -> None:
    valid = wire(example())
    suffix = valid[1:]
    invalid = [
        valid.decode().encode("utf-16"),
        b'{"ignored":{"secret-key":1,"secret-key":2},' + suffix,
        b'{"ignored":NaN,' + suffix,
        b'{"ignored":1e999,' + suffix,
        b'{"ignored":"\\ud800",' + suffix,
        valid + b"{}",
        b" " * reader.MAX_EVENT_BYTES + b"{}",
    ]
    for data in invalid:
        with pytest.raises(EnvelopeError) as caught:
            read_battery_event(data)
        assert "secret-key" not in str(caught.value)
        assert caught.value.field == "json"


def test_jsonl_budgets_and_failure_have_no_partial_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "events.jsonl"
    valid = wire(example()) + b"\n"
    path.write_bytes(valid * 2)
    assert reader.main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "validated", "records": 2}
    invalid = example()
    invalid["source_timestamp"] = "2026-01-01T12:00:01.234568Z"
    path.write_bytes(valid + wire(invalid) + b"\n")
    before = path.read_bytes()
    assert reader.main([str(path)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["record_index"] == 1
    assert path.read_bytes() == before
    path.write_bytes(valid * 2)
    for limit, value in (
        ("MAX_EVENT_FILE_BYTES", len(valid)),
        ("MAX_EVENT_RECORDS", 1),
        ("MAX_EVENT_BYTES", len(valid) - 2),
    ):
        with monkeypatch.context() as budget:
            budget.setattr(reader, limit, value)
            with pytest.raises(EnvelopeError):
                check_event_file(path)
    path.write_bytes(b"")
    assert check_event_file(path) == 0
