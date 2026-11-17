"""Verify a completed recording run and retain its reconciliation report."""

import json
import time
from typing import cast

from runtime.recording.evidence import probe, write
from runtime.recording.profile import Document, Profile


def verify_run(run: Profile, plan: Document) -> Document:
    """Exact reconciliation after completion; F09 adds an archive-only rebuild."""
    events = [
        json.loads(line)
        for line in (run.out / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    if plan["source"] == "live":
        reconcile = run.worker("live_reconcile", timeout=900)
        capture = cast(Document, reconcile["capture"])
        inside = probe(run, "snapshot", network=True)
        final = inside.get("gateway_final_published")
        checks: Document = {
            "archive_equals_published": isinstance(final, int)
            and reconcile["archived_deliveries"]
            == final
            == cast(Document, inside.get("kafka") or {}).get("input_end"),
            "capture_covered": capture["covered"],
            "no_capture_loss": capture["lost_packets"] == 0,
            "fact_hash_sets_equal": reconcile["fact_hash_sets_equal"],
            "zero_logical_repeats": reconcile["zero_logical_repeats"],
            "untimed_without_time": reconcile["untimed_without_time"],
            "statuses_match_receipt_order": cast(Document, reconcile["restart"])[
                "statuses_match_receipt_order"
            ],
        }
        documents = {"reconcile": reconcile}
        info: Document = {"capture_epochs": len(cast(list[object], capture["epochs"]))}
    else:
        positions = [
            str(e["committed_offset_at_restore"])
            for e in events
            if e.get("event") == "job_restored"
            and isinstance(e.get("committed_offset_at_restore"), int)
        ]
        reconcile = run.worker(
            "recording_reconcile",
            *(["--restore-positions", ",".join(positions)] if positions else []),
        )
        rebuild_id = f"{len(list(run.out.glob('verify-*.json'))) + 1:03d}"
        rebuilt = run.worker("recording_rebuild", "--rebuild", rebuild_id, timeout=1800)
        again = run.worker(
            "recording_reconcile", "--database", str(rebuilt.get("database"))
        )
        starts = [
            r[0]
            for r in cast(list[list[int]], reconcile.get("repeated_output_ranges", []))
        ]
        mapped = cast(Document, reconcile.get("restore_positions") or {})
        checks = {
            "fact_hash_sets_equal": reconcile.get("fact_hash_sets_equal"),
            "zero_logical_repeats": reconcile.get("zero_logical_repeats"),
            "rebuild_fact_hash_sets_equal": again.get("fact_hash_sets_equal"),
            "rebuild_matches_original_hash_set": again.get("fact_hash_set_sha256")
            == reconcile.get("fact_hash_set_sha256"),
            "re_emission_starts_at_restored_positions": all(
                mapped.get(p) in starts for p in positions
            ),
        }
        documents = {"reconcile": reconcile, "rebuild": rebuilt, "rebuild_check": again}
        info = {"restores": len(positions)}
    result: Document = {
        "run_id": run.run_id,
        "status": "passed" if all(v is True for v in checks.values()) else "failed",
        "checks": checks,
        **documents,
    }
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    write(run.out / f"verify-{stamp}.json", result)
    run.log("verified", status=result["status"])
    return {
        "run_id": run.run_id,
        "status": result["status"],
        "checks": checks,
        **info,
    }
