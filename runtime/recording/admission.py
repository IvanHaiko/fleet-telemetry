"""Prepare an admitted original for the integrated replay (ADR-0058).

`python -m runtime.recording.admission --source X.ulg --output DIR --rights ...`
decides admission (telemetry/admission.py), then writes into a fresh DIR:

- `admission.json`: the decision, the measured counts and the provenance the
  operator supplied (rights, reference); nothing here is inferred from names;
- `battery.job.json`: the bounded battery conversion job, generated from the
  mapping profile instead of written by hand;
- `inspection/`: the same GPS, state and battery inspection a registered
  recording gets (runtime/flight_analytics/recording.py).

A refused file writes nothing and prints one reason per unavailable part; it
stays inspectable with `python -m telemetry.ulog_inventory`. Output holds
counts and states only, never values or coordinates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from runtime.flight_analytics.recording import connect
from telemetry.admission import AdmissionRefused, admit_original
from telemetry.recordings import RECORDINGS, Recording

FORMAT_VERSION = "ulog-admission-v1"
MAX_AGE_US = 1_000_000

type Document = dict[str, object]


def _utc(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def battery_job(
    admitted: Recording,
    report: Document,
    source: Path,
    job_dir: Path,
    *,
    rights: str,
    reference: str,
    retrieved_at: str,
) -> Document:
    """The bounded conversion job a registered recording has, from the profile."""
    rows = {
        (row["topic"], row["instance"]): row
        for row in report["subscriptions"]  # type: ignore[attr-defined]
    }
    battery = rows[("battery_status", 0)]
    digest = admitted.source_id.removeprefix("sha256:")
    return {
        "job_version": "bounded-conversion-v1",
        "mode": "ulog",
        "input": {
            "path": Path(
                os.path.relpath(source.resolve(), job_dir.resolve())
            ).as_posix(),
            "source_log_id": admitted.source_id,
            "size_bytes": admitted.source_bytes,
        },
        "manifest": {
            "source_manifest_id": admitted.battery_manifest_id + "-" + digest[:16],
            "source_log_id": admitted.source_id,
            "vehicle_id": admitted.vehicle_id,
            "source_stream": "battery_status:0",
            "native_timestamp_min_us": battery["first_us"],
            "native_timestamp_max_us": battery["last_us"],
            "clock_anchor": {
                "native_anchor_us": 0,
                "utc_anchor": "2000-01-01T00:00:00.000000Z",
                "anchor_uncertainty_us": None,
            },
            "retrieved_at": retrieved_at,
            "license_evidence": rights,
            "privacy_review": "Restricted; no location or identifiers published.",
            "source_type": "ulog",
            "privacy_classification": "restricted",
            "source_reference": reference,
            "parser_version": "pyulog-1.2.2",
            "vehicle_mapping_version": "ulog-file-pseudonym-v1",
            "producer_evidence": "Unverified physical producer; admitted by "
            f"mapping profile {admitted.key}; restricted research only.",
            "field_definition_reference": admitted.battery_definition,
            "firmware_commit": admitted.firmware,
            "producer_profile": admitted.battery_producer_profile,
            "native_format_version": admitted.battery_native_format,
            "normalization_version": admitted.battery_normalization,
        },
        "delivery": {
            "dataset_run_id": f"ulog-{digest[:16]}-battery",
            # The file's own retrieval time, so a repeated admission of the
            # same bytes reproduces the same battery content.
            "ingest_timestamp": retrieved_at,
            "replay_mode": "historical",
        },
    }


def prepare_admitted(
    source: Path,
    output: Path,
    *,
    rights: str,
    reference: str,
    max_age_us: int = MAX_AGE_US,
) -> Document:
    if not rights.strip() or not reference.strip():
        raise ValueError("admission_provenance_required")
    if output.exists():
        raise ValueError("admission_output_exists")
    admitted, report = admit_original(source)
    if admitted.source_id in RECORDINGS:
        raise ValueError("registered_recording_use_its_key")
    retrieved_at = _utc(source.stat().st_mtime)
    output.mkdir()
    replay = report["replay"]
    selected = [
        row
        for row in report["subscriptions"]  # type: ignore[attr-defined]
        if row["instance"] == 0 and row["topic"] in replay["topics"]  # type: ignore[index]
    ]
    decision: Document = {
        "format_version": FORMAT_VERSION,
        "status": "admitted",
        "source_id": admitted.source_id,
        "source_bytes": admitted.source_bytes,
        "source_name": source.name,
        "firmware": admitted.firmware,
        "mapping_profile": admitted.key,
        "label": admitted.label,
        "vehicle_id": admitted.vehicle_id,
        "records": {
            "vehicle_gps_position": admitted.gps_records,
            "battery_status": admitted.battery_records,
            **admitted.state_counts,
        },
        "dropout_markers": admitted.dropout_markers,
        # One past the last selected sample: the whole file as an interval.
        "native_end_us": max(int(row["last_us"] or 0) for row in selected) + 1,
        "topics": replay["topics"],  # type: ignore[index]
        "rights": rights,
        "reference": reference,
        "retrieved_at": retrieved_at,
        "inventory_format": report["format_version"],
        "decided_utc": _utc(datetime.now(UTC).timestamp()),
    }
    (output / "admission.json").write_text(
        json.dumps(decision, sort_keys=True) + "\n", encoding="utf-8"
    )
    job_path = output / "battery.job.json"
    job = battery_job(
        admitted,
        report,
        source,
        output,
        rights=rights,
        reference=reference,
        retrieved_at=retrieved_at,
    )
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    inspection = connect(job_path, output / "inspection", max_age_us)
    battery = inspection["battery_counts"]
    assert isinstance(battery, dict)
    decision |= {
        "inspection_records": inspection["inspection_records"],
        "battery_admitted": battery["admitted_records"],
        # Values the reviewed battery mapping refuses (ADR-0007), apart from
        # missing and empty subscriptions.
        "battery_rejected_by_mapping": battery["rejected_records"],
        "association_status_counts": inspection["association_status_counts"],
    }
    (output / "admission.json").write_text(
        json.dumps(decision, sort_keys=True) + "\n", encoding="utf-8"
    )
    return decision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rights", default="", help="licence or permission evidence")
    parser.add_argument("--reference", default="", help="where the file came from")
    parser.add_argument(
        "--check", action="store_true", help="decide only; write nothing"
    )
    args = parser.parse_args(argv)
    try:
        if args.check:
            admitted, _ = admit_original(args.source)
            result: Document = {
                "status": "registered"
                if admitted.source_id in RECORDINGS
                else "admitted",
                "mapping_profile": admitted.key,
                "source_id": admitted.source_id,
            }
        else:
            if args.output is None:
                raise ValueError("admission_output_required")
            result = prepare_admitted(
                args.source, args.output, rights=args.rights, reference=args.reference
            )
    except AdmissionRefused as refused:
        print(json.dumps({"status": "refused", "reasons": refused.reasons}))
        return 1
    except (ValueError, OSError) as error:
        reason = str(error) if isinstance(error, ValueError) else "io_failure"
        print(json.dumps({"status": "failed", "reason": reason}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
