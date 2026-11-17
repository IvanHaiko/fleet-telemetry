"""Admit a compatible original without a registry entry (ADR-0058).

A file is admitted when its selected topics' layout digests and its reported
firmware match a mapping profile in ``telemetry.recordings`` and the strict
integrity scanner accepts it under the admitted limits. Every count is
measured from the file. A registered checksum keeps its registration.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from telemetry.recordings import (
    ADMITTED_MAX_INPUT_BYTES,
    MAPPING_PROFILES,
    RECORDINGS,
    STATE_STREAMS,
    Recording,
    register_admitted,
    withdraw_admitted,
)
from telemetry.ulog_inventory import inventory
from ulog_integrity import InputIntegrityError, ULogExpectation, inspect_ulog


class AdmissionRefused(ValueError):
    """The file stays inspectable; ``reasons`` name each unavailable part."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("admission_refused")
        self.reasons = reasons


def admit_original(path: Path) -> tuple[Recording, dict[str, object]]:
    """Return the registered or admitted recording and the inventory report."""
    report = inventory(path, max_bytes=ADMITTED_MAX_INPUT_BYTES)
    file = report["file"]
    assert isinstance(file, dict)
    source_id = file["sha256"]
    if isinstance(source_id, str) and source_id in RECORDINGS:
        return RECORDINGS[source_id], report
    replay = report.get("replay")
    if not isinstance(replay, dict):
        raise AdmissionRefused([f"inventory_{report['status']}:{report['reason']}"])
    reasons = list(replay["reasons"])
    rows = {
        (row["topic"], row["instance"]): row
        for row in report["subscriptions"]  # type: ignore[attr-defined]
    }
    selected = {topic: rows.get((topic, 0)) for topic in RECORDING_TOPICS}
    for topic, row in selected.items():
        if row is not None and (row["time_regressions"] or row["removed"]):
            reasons.append(f"{topic}:time_order_or_removal")
    if reasons:
        raise AdmissionRefused(reasons)
    profile = next(p for p in MAPPING_PROFILES if p.key == replay["profile"])
    dropouts = report["dropouts"]
    assert isinstance(dropouts, dict) and isinstance(source_id, str)
    admitted = profile.admit(
        source_id,
        firmware=str(report["firmware"]),
        source_bytes=int(file["bytes"]),
        gps_records=_samples(selected["vehicle_gps_position"]),
        battery_records=_samples(selected["battery_status"]),
        state_records=tuple(
            (topic, _samples(selected[topic])) for topic in STATE_STREAMS
        ),
        dropout_markers=int(dropouts["markers"]),
    )
    data = path.read_bytes()
    if "sha256:" + sha256(data).hexdigest() != source_id:
        raise AdmissionRefused(["source_changed_during_admission"])
    # The strict scanner reads the admitted limits from the registration.
    register_admitted(admitted)
    try:
        inspect_ulog(data, ULogExpectation(source_id, len(data)))
    except InputIntegrityError as error:
        withdraw_admitted(source_id)
        raise AdmissionRefused([f"integrity:{error.reason}"]) from None
    return admitted, report


RECORDING_TOPICS = ("vehicle_gps_position", "battery_status", *STATE_STREAMS)


def _samples(row: object) -> int:
    assert isinstance(row, dict)
    return int(row["samples"])
