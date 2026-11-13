"""Offline reconciliation of synthetic observations without a Kafka client."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from kafka_evidence import obj, require

from fleet_telemetry import Rejection, SourceManifest, normalize_battery
from telemetry_convert import SEMANTIC_FIELDS, load_job
from telemetry_reader import read_battery_event


@dataclass(frozen=True)
class Record:
    """One independently received transport observation."""

    offset: int
    key: bytes
    value: bytes


def reconcile(values: tuple[bytes, ...], rows: list[Record]) -> dict[str, int]:
    """Distinguish missing, extra, conflicting and repeated observations."""

    def semantic(value: bytes) -> dict[str, object]:
        event = read_battery_event(value)
        fields = cast(Mapping[str, object], event)
        return {
            **{name: fields[name] for name in SEMANTIC_FIELDS},
            "quality_flags": sorted(event["quality_flags"]),
        }

    expected = {read_battery_event(v)["event_id"]: v for v in values}
    semantics = {event_id: semantic(value) for event_id, value in expected.items()}
    seen: set[str] = set()
    conflicts: set[str] = set()
    byte_mismatches, key_mismatches = 0, 0
    for row in rows:
        event = read_battery_event(row.value)
        event_id = event["event_id"]
        seen.add(event_id)
        content = semantic(row.value)
        if event_id in semantics and content != semantics[event_id]:
            conflicts.add(event_id)
        else:
            semantics[event_id] = content
        if event_id in expected:
            byte_mismatches += int(row.value != expected[event_id])
            key_mismatches += int(
                row.key != read_battery_event(expected[event_id])["vehicle_id"].encode()
            )
    return {
        "observations": len(rows),
        "unique_expected": len(seen & expected.keys()),
        "duplicate_observations": len(rows) - len(seen),
        "missing_identities": len(expected.keys() - seen),
        "extra_identities": len(seen - expected.keys()),
        "conflicting_identities": len(conflicts),
        "byte_mismatches": byte_mismatches,
        "key_mismatches": key_mismatches,
    }


def negative_reconciliation(
    job: Path, values: tuple[bytes, ...], rows: list[Record]
) -> dict[str, object]:
    """Use valid authored envelopes to establish three distinct mismatch detectors."""
    spec = load_job(job)
    if not isinstance(spec.manifest, SourceManifest):
        raise ValueError("synthetic_manifest_required")
    manifest = spec.manifest

    def authored(index: int, voltage: int) -> Record:
        value = normalize_battery(
            {
                "source_record_index": index,
                "timestamp_us": 1234567,
                "voltage_mv": voltage,
                "current_ma": 4200,
                "remaining_pct": 72,
            },
            manifest,
            manifest.clock_anchor,
            spec.delivery,
        )
        if isinstance(value, Rejection):
            raise ValueError("negative_fixture_rejected")
        raw = json.dumps(value, separators=(",", ":")).encode()
        read_battery_event(raw)
        return Record(0, value["vehicle_id"].encode(), raw)

    missing = reconcile(values, rows[:2])
    extra = reconcile(values, [*rows[:3], authored(99, 15800)])
    conflict = reconcile(values, [authored(0, 15900), *rows[1:3]])
    equivalent = obj(json.loads(values[0]))
    equivalent["ingest_timestamp"] = "2026-10-20T00:00:00.000000Z"
    equivalent["delivery"] = {
        **obj(equivalent["delivery"]),
        "dataset_run_id": "equivalent-check",
    }
    equivalent_result = reconcile(
        values,
        [Record(0, rows[0].key, json.dumps(equivalent, indent=2).encode()), *rows[1:3]],
    )
    require(
        missing["missing_identities"] == 1
        and extra["extra_identities"] == 1
        and conflict["conflicting_identities"] == 1,
        "reconciliation_negative_missed",
    )
    require(
        equivalent_result["conflicting_identities"] == 0
        and equivalent_result["byte_mismatches"] == 1,
        "delivery_or_formatting_changed_semantics",
    )
    return {
        "missing": missing,
        "extra": extra,
        "conflict": conflict,
        "semantic_equivalence_control": equivalent_result,
        "scope": "offline reconciliation of valid authored envelopes",
    }
