"""Independent reconciliation of one live session: SITL or a fleet.

ADR-0054 for one SITL source; ADR-0060 for a fleet of replay players, where
every check runs per vehicle and the players' ledgers are compared with the
archive.

Reads, and never changes, the run's SQL scope, archive objects and local
capture evidence. It reports:

- capture coverage: every acknowledged event matches a captured packet marked
  published, in the same epoch and sequence;
- archive-only rebuild: the facts recomputed from archive objects alone with
  `LiveRuntime` have the same hash set as SQL, with no logical repeats;
- untimed streams: no battery or state event carries measurement time;
- restart behaviour: after a gateway restart, positions show
  `unknown_after_restart` until new battery and state receipts pass;
- fleet only: each player's ledger of sent positions equals the archived
  position events of its vehicle by identity and content hash.

Output holds counts, digests and statuses only, never coordinates.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from collections import Counter
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.live_worker import ArchivedFacts
from runtime.continuous.recording_config import require, storage
from telemetry.archive_documents import canonical, digest
from telemetry.continuous_archive import segment_rows
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    json_object,
    object_value,
    string_value,
)
from telemetry.live_event import read_event, replay_scope
from telemetry.live_runtime import Document
from telemetry.local_io import read_bounded

_MAX_CAPTURE = 256 * 1024 * 1024


def capture_coverage(state: Path, sources: set[tuple[int, int]]) -> Document:
    """Match acknowledgement ledgers with the epochs' raw captures."""
    epochs: list[Document] = []
    for capture in sorted(state.glob("capture-*.jsonl")):
        epoch = capture.stem.removeprefix("capture-")
        records = [
            json_object(line)
            for line in read_bounded(capture, _MAX_CAPTURE).splitlines()
        ]
        ledger = state / f"gateway-acks-{epoch}.jsonl"
        acks = [
            json_object(line)
            for line in read_bounded(ledger, _MAX_CAPTURE).splitlines()
        ]
        published = [r for r in records if r["published"] is True]
        sequences = [integer_value(r["sequence"]) for r in records]
        # Each declared sender's own packet sequence; other IDs are counted.
        lost = 0
        for address in sources:
            seqs = [
                integer_value(r["mavlink_seq"])
                for r in records
                if (r["system"], r["component"]) == address
            ]
            lost += sum((b - a - 1) % 256 for a, b in zip(seqs, seqs[1:], strict=False))
        epochs.append(
            {
                "captured": len(records),
                "published_in_capture": len(published),
                "acknowledged": len(acks),
                "sequences_contiguous": sequences == list(range(len(records))),
                "packets_decoded": all(
                    base64.b64decode(string_value(r["packet_b64"]), validate=True)
                    for r in records
                ),
                "messages": dict(Counter(string_value(r["message"]) for r in records)),
                "mavlink_lost_packets": lost,
                "sources": dict(
                    Counter(f"{r['system']}/{r['component']}" for r in records)
                ),
            }
        )
    return {
        "epochs": epochs,
        "lost_packets": sum(int(str(e["mavlink_lost_packets"])) for e in epochs),
        "covered": bool(epochs)
        and all(
            e["sequences_contiguous"]
            and e["packets_decoded"]
            and e["published_in_capture"] == e["acknowledged"]
            for e in epochs
        ),
    }


def reconcile(private: Path, evidence: Path) -> Document:
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    plan = json_object(read_bounded(private / "live-run.json", 65536))
    run = string_value(plan["run_id"])
    database = string_value(plan["database"])
    state = evidence / run / "state"
    config = json_object(read_bounded(evidence / run / "config/serve.json", 262144))
    sql = HttpConfig(
        8123, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
    )

    def rows(query: str) -> list[list[object]]:
        body = _request(sql, query + " FORMAT JSONCompactEachRow", b"")
        return [json.loads(line) for line in body.splitlines()]

    def one(query: str) -> object:
        return rows(query)[0][0]

    # Rebuild from archive objects alone, with its own origin file.
    rebuild = state.parent / "rebuild-001"
    rebuild.mkdir()
    reader = storage(config, "reader")
    try:
        archived = ArchivedFacts(config, reader, rebuild)
        archived.advance()
        # Untimed-stream checks run over the archived events themselves.
        archived_events = _archived_events(archived)
    finally:
        reader.close()
    rebuilt = set(archived.facts.values())
    sql_hashes = {
        str(r[0])
        for r in rows(
            "SELECT DISTINCT lower(hex(SHA256(concat(fact_json, '\\n')))) "
            f"FROM {database}.facts"
        )
    }
    untimed = [e for e in archived_events if e["measurement_id"] is None]
    declared = (
        [
            replay_scope(json_object(read_bounded(path, 8192)))
            for path in sorted((state / "players").glob("*.declaration.json"))
        ]
        if "fleet" in plan
        else []
    )
    statuses = rows(
        "SELECT capture_epoch, input_offset, battery_status, state_status "
        f"FROM {database}.points ORDER BY input_offset"
    )
    result: Document = {
        "database": database,
        "archived_deliveries": archived.archived,
        "rebuilt_facts": len(rebuilt),
        "sql_distinct_fact_hashes": len(sql_hashes),
        "fact_hash_sets_equal": sql_hashes == rebuilt,
        "physical_rows": one(f"SELECT count() FROM {database}.facts"),
        "distinct_event_ids": one(f"SELECT uniqExact(event_id) FROM {database}.facts"),
        "distinct_full_rows_view": one(f"SELECT count() FROM {database}.measurements"),
        "conflicting_events": one(
            f"SELECT count() FROM (SELECT event_id FROM {database}.facts "
            "GROUP BY event_id HAVING uniqExact(fact_json) > 1)"
        ),
        "untimed_events": len(untimed),
        "untimed_without_time": all(e["native_time_boot_ms"] is None for e in untimed),
        "association_counts": {
            name: dict(Counter(str(r[index]) for r in statuses))
            for index, name in ((2, "battery"), (3, "state"))
        },
        "restart": restart_behaviour(statuses, archived_events),
        "capture": capture_coverage(state, senders(plan, declared)),
    }
    if "fleet" in plan:
        result["players"] = ledger_check(state / "players", archived_events)
    result["zero_logical_repeats"] = (
        result["distinct_event_ids"]
        == result["distinct_full_rows_view"]
        == len(rebuilt)
        and result["conflicting_events"] == 0
    )
    return result


def senders(plan: Document, declared: list[Document]) -> set[tuple[int, int]]:
    sources = declared if "fleet" in plan else [object_value(plan["source"])]
    return {
        (integer_value(s["system"]), integer_value(s["component"])) for s in sources
    }


def ledger_check(players: Path, events: list[Document]) -> Document:
    """Per vehicle: positions the player sent equal the archived positions."""
    archived: dict[str, set[tuple[str, str]]] = {}
    for event in events:
        if event["measurement_id"] is None:
            continue
        vehicle = string_value(object_value(event["source"])["vehicle"])
        archived.setdefault(vehicle, set()).add(
            (
                string_value(event["measurement_id"]),
                hashlib.sha256(json_line(event["native"])).hexdigest(),
            )
        )
    result: Document = {}
    for path in sorted(players.glob("*.ledger.jsonl")):
        vehicle = path.name.removesuffix(".ledger.jsonl")
        sent = {
            (string_value(row["measurement_id"]), string_value(row["native_sha256"]))
            for row in (
                json_object(line)
                for line in read_bounded(path, _MAX_CAPTURE).splitlines()
            )
        }
        got = archived.get(vehicle, set())
        result[vehicle] = {
            "sent_positions": len(sent),
            "archived_positions": len(got),
            "missing_in_archive": len(sent - got),
            "not_sent_by_player": len(got - sent),
            "equal": sent == got,
        }
    return result


def _archived_events(archived: ArchivedFacts) -> list[Document]:
    """Re-read the verified segments for content checks; counts only leave."""
    events: list[Document] = []
    offset = 0
    previous: str | None = None
    while True:
        checked = archived.verifier.verify_receipt(0, offset)
        if checked is None:
            return events
        receipt, body = checked
        require(receipt["previous_sha256"] == previous, "live_reconcile_chain")
        for row in segment_rows(body):
            value = base64.b64decode(string_value(row["value_b64"]), validate=True)
            events.append(read_event(value))
            offset += 1
        previous = digest(canonical(receipt))


def _expected(last: str | None, epoch: str) -> str:
    if last is None:
        return "none"
    return "unknown_after_restart" if last != epoch else "fresh"


def restart_behaviour(statuses: list[list[object]], events: list[Document]) -> Document:
    """Compare each position's statuses with what receipt order implies.

    Within the first epoch a stream is `none` until its first receipt. In a
    later epoch it is `unknown_after_restart` until its first receipt in that
    epoch, if anything was received before. Afterwards it is fresh or stale.
    """
    expected: dict[int, tuple[str, str]] = {}
    # Receipt order is per vehicle: one vehicle's receipts never count for
    # another's positions.
    seen: dict[tuple[str, str], str] = {}
    for offset, event in enumerate(events):
        epoch = string_value(object_value(event["capture"])["epoch"])
        stream = string_value(event["stream"])
        vehicle = string_value(object_value(event["source"])["vehicle"])
        if stream != "position":
            seen[(vehicle, stream)] = epoch
            continue
        expected[offset] = (
            _expected(seen.get((vehicle, "battery")), epoch),
            _expected(seen.get((vehicle, "state")), epoch),
        )
    exact = True
    shown = {"battery": 0, "state": 0}
    for row in statuses:
        battery, state = row[2], row[3]
        want = expected.get(integer_value(row[1]))
        if want is None:
            exact = False
            continue
        for index, (name, value) in enumerate((("battery", battery), ("state", state))):
            target = want[index]
            if target == "fresh":
                exact &= value in ("receipt_ordered", "stale")
            else:
                exact &= value == target
            shown[name] += value == "unknown_after_restart"
    epochs = len({string_value(object_value(e["capture"])["epoch"]) for e in events})
    return {
        "epochs": epochs,
        "positions_checked": len(statuses),
        "statuses_match_receipt_order": exact and len(statuses) == len(expected),
        "battery_unknown_after_restart": shown["battery"],
        "state_unknown_after_restart": shown["state"],
        "restart_exercised": epochs > 1 and shown["battery"] + shown["state"] > 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.private, args.evidence)
    except Exception as error:
        print(json.dumps({"status": "failed", "category": type(error).__name__}))
        return 2
    print(json.dumps({"status": "reconciled", **result}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
