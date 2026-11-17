"""Offline inventory and mapping-profile admission on authored ULog bytes."""

import hashlib
import struct
from pathlib import Path

import pytest
from ulog_binary import FIRMWARE_COMMIT, header, info, packet

import telemetry.recordings as recordings
from telemetry import admission, ulog_inventory
from telemetry.ulog_inventory import closure_digest, inventory

CUSTOM = (
    "custom_probe:uint64_t timestamp;float level;uint8_t[3] flags;uint8_t _padding0;"
)
NESTED = "probe_pair:uint64_t timestamp;custom_inner[2] inner;"
INNER = "custom_inner:float a;int16_t b;uint8_t[2] _padding0;"


def _log(*frames: bytes, firmware: str = FIRMWARE_COMMIT) -> bytes:
    prefix = header() + packet("B", bytes(40))
    prefix += info("char[40]", "ver_sw", firmware.encode("ascii"))
    return prefix + b"".join(frames)


def _definition(text: str) -> bytes:
    return packet("F", text.encode("ascii"))


def _subscribe(name: str, instance: int, msg_id: int) -> bytes:
    return packet("A", struct.pack("<BH", instance, msg_id) + name.encode("ascii"))


def _custom(msg_id: int, stamp: int) -> bytes:
    return packet("D", struct.pack("<HQf3BB", msg_id, stamp, 1.5, 1, 2, 3, 0))


def _write(tmp_path: Path, data: bytes, name: str = "probe.ulg") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_unregistered_custom_topic_in_two_instances_needs_no_registry_edit(
    tmp_path: Path,
) -> None:
    data = _log(
        _definition(CUSTOM),
        _subscribe("custom_probe", 0, 1),
        _subscribe("custom_probe", 1, 2),
        _custom(1, 1_000),
        _custom(2, 1_500),
        _custom(1, 2_000),
        _custom(1, 3_000),
        packet("O", struct.pack("<H", 12)),
    )
    report = inventory(_write(tmp_path, data))

    assert report["status"] == "complete" and report["reason"] is None
    rows = report["subscriptions"]
    assert isinstance(rows, list)
    counts = {(r["topic"], r["instance"]): r["samples"] for r in rows}
    assert counts == {("custom_probe", 0): 3, ("custom_probe", 1): 1}
    first = rows[0]
    # Padding is layout, not a field; arrays keep their size.
    assert first["fields"] == [
        ["uint64_t", "timestamp"],
        ["float", "level"],
        ["uint8_t[3]", "flags"],
    ]
    assert (first["first_us"], first["last_us"]) == (1_000, 3_000)
    assert first["mapping"] == "unmapped"
    # Dropout markers stay apart from sample counts.
    assert report["dropouts"] == {"markers": 1, "duration_ms": 12}
    views = report["views"]
    assert isinstance(views, dict)
    assert views["map"]["state"] == "missing_subscription"
    replay = report["replay"]
    assert isinstance(replay, dict) and replay["status"] == "unavailable"
    assert "vehicle_gps_position:missing_subscription" in replay["reasons"]


def test_truncated_tail_keeps_the_prefix_and_states_why(tmp_path: Path) -> None:
    whole = _log(_definition(CUSTOM), _subscribe("custom_probe", 0, 1), _custom(1, 5))
    report = inventory(_write(tmp_path, whole + _custom(1, 6)[:-4]))

    assert report["status"] == "incomplete"
    assert report["reason"] == "truncated_tail" and report["offset"] == len(whole)
    assert report["inventoried_bytes"] == len(whole)
    rows = report["subscriptions"]
    assert isinstance(rows, list) and rows[0]["samples"] == 1


def test_unsupported_features_are_explicit(tmp_path: Path) -> None:
    flags = bytearray(40)
    flags[9] = 1  # an incompatibility bit other than appended data
    data = header() + packet("B", bytes(flags))
    report = inventory(_write(tmp_path, data))
    assert (report["status"], report["reason"]) == (
        "unsupported",
        "unsupported_incompatibility_flags",
    )
    version = bytearray(header())
    version[7] = 2
    report = inventory(_write(tmp_path, bytes(version), "v2.ulg"))
    assert (report["status"], report["reason"]) == (
        "unsupported",
        "unsupported_format_version",
    )


def test_layout_digest_covers_referenced_definitions() -> None:
    texts = {"probe_pair": NESTED, "custom_inner": INNER, "custom_probe": CUSTOM}
    flat = hashlib.sha256(CUSTOM.encode()).hexdigest()
    assert closure_digest("custom_probe", texts) == flat
    nested = closure_digest("probe_pair", texts)
    changed = closure_digest(
        "probe_pair", {**texts, "custom_inner": INNER.replace("int16_t", "int32_t")}
    )
    assert nested != changed  # a changed referenced layout changes the digest


# Four tiny selected topics stand in for a reviewed mapping profile.
SELECTED = {
    "vehicle_gps_position": "vehicle_gps_position:uint64_t timestamp;float x;",
    "battery_status": "battery_status:uint64_t timestamp;float voltage_v;",
    "vehicle_land_detected": "vehicle_land_detected:uint64_t timestamp;bool landed;",
    "vehicle_status": "vehicle_status:uint64_t timestamp;uint8_t arming_state;",
}


def _selected_log(firmware: str, samples: int = 2) -> bytes:
    # The strict scanner admits definitions only before the first subscription.
    frames = [_definition(text) for text in SELECTED.values()]
    for index, text in enumerate(SELECTED.values(), start=1):
        frames.append(_subscribe(text.split(":")[0], 0, index))
    for stamp in range(samples):
        for index, text in enumerate(SELECTED.values(), start=1):
            width = 4 if "float" in text else 1
            frames.append(
                packet("D", struct.pack("<HQ", index, 1_000 + stamp) + bytes(width))
            )
    return _log(*frames, firmware=firmware)


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> recordings.MappingProfile:
    digest = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in SELECTED.items()}
    reference = recordings.Recording(
        key="t01",
        label="T01",
        source_id="sha256:" + "0" * 64,
        source_bytes=1,
        firmware=FIRMWARE_COMMIT,
        vehicle_id="t01-research-vehicle",
        battery_definition="sha256:" + digest["battery_status"],
        gps_definition=digest["vehicle_gps_position"],
        state_definitions=tuple(
            (k, digest[k]) for k in ("vehicle_land_detected", "vehicle_status")
        ),
        gps_records=1,
        battery_records=1,
        state_records=(),
        gps_layout="degrees",
        dropout_markers=0,
    )
    item = recordings.MappingProfile("px4-t01-v1", reference, (FIRMWARE_COMMIT,))
    monkeypatch.setattr(recordings, "MAPPING_PROFILES", (item,))
    monkeypatch.setattr(ulog_inventory, "MAPPING_PROFILES", (item,))
    monkeypatch.setattr(admission, "MAPPING_PROFILES", (item,))
    monkeypatch.setattr(recordings, "_MAPPING_KEYS", {item.key: item})
    monkeypatch.setattr(recordings, "_ADMITTED", {})
    return item


def test_matching_layouts_on_reviewed_firmware_are_admitted_per_file(
    tmp_path: Path, profile: recordings.MappingProfile
) -> None:
    from telemetry.admission import AdmissionRefused, admit_original

    first = _write(tmp_path, _selected_log(FIRMWARE_COMMIT, 2), "a.ulg")
    second = _write(tmp_path, _selected_log(FIRMWARE_COMMIT, 3), "b.ulg")
    one, report = admit_original(first)
    two, _ = admit_original(second)

    assert report["replay"]["status"] == "admitted"  # type: ignore[index]
    assert one.key == two.key == profile.key
    assert one.source_id != two.source_id and one.vehicle_id != two.vehicle_id
    assert (one.gps_records, two.gps_records) == (2, 3)  # measured per file
    assert one.name("recording-event-v1") == "px4-t01-v1-recording-event-v1"
    assert recordings.recording(one.source_id) == one

    # A validator that never reads the original resolves the identity only;
    # its per-file counts and firmware are not measured and fail closed.
    other = "sha256:" + "1" * 64
    resolved = recordings.resolve(
        other, "px4-t01-v1-recording-fact-v1", "recording-fact-v1"
    )
    assert resolved.vehicle_id == "ulog-" + "1" * 16
    assert resolved.gps_records == recordings.UNMEASURED and resolved.firmware == ""
    with pytest.raises(ValueError, match="unregistered_recording"):
        recordings.resolve(
            "sha256:" + "2" * 64, "f09-recording-fact-v1", "recording-fact-v1"
        )

    unreviewed = _write(tmp_path, _selected_log("1" * 40, 2), "c.ulg")
    with pytest.raises(AdmissionRefused) as refused:
        admit_original(unreviewed)
    assert "vehicle_gps_position:candidate_unreviewed_firmware" in refused.value.reasons
    assert (
        recordings.lookup(
            "sha256:" + hashlib.sha256(unreviewed.read_bytes()).hexdigest()
        )
        is None
    )
