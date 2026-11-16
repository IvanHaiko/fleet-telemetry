"""Read-only snapshot and file inventory of one recording-profile run.

Runs in a short-lived container on the recording worker image, started by the
host operations command (runtime/recording/ops.py). Nothing here writes to the
run, the topics, SQL or the archive.

- `snapshot` (in the archive container's network namespace): the container
  clock, the run's progress files reduced to scalar counts, times and states,
  SQL availability and counts, the S3 endpoint's reachability, Kafka offsets
  and, for a live session, the `live_state` connection and ages. A failed
  observation is reported as an error with a null value, never as a zero.
- `inventory` (no network): path, size and SHA-256 of every file of the run in
  the evidence volume and of its checkpoints and job files in the state volume,
  plus the content of the small progress files. Captures, ledgers, outputs and
  configurations appear only as path, size and hash.
- `checkpoints` (no network): the retained checkpoints of the run that have a
  `_metadata` file, newest first.
- `health` (in the archive namespace): the data-quality checks and the run's
  storage footprint (runtime/continuous/recording_health.py).

Output never carries coordinates, credentials, keys or event identifiers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.recording_config import kafka_client
from runtime.continuous.recording_health import measure
from telemetry.conversion_contract import json_object, object_value, string_value
from telemetry.local_io import read_bounded

type Document = dict[str, object]

PROGRESS = (
    "producer-status.json",
    "gateway-status.json",
    "archive-status.json",
    "serving-status.json",
)
MARKERS = (
    "archive-complete.json",
    "serving-complete.json",
    "gateway-complete.json",
    "fault-after-sql-ack.json",
)
# Small progress files whose full content is kept in the evidence inventory.
CONTENT = (*PROGRESS, *MARKERS, "serving-cursor.json", "archive-cursor.json")
MAX_FILE = 1024 * 1024
MAX_FILES = 200_000


def reduced(document: Document) -> Document:
    """Scalars as they are; an offset map becomes its sum and its size."""
    out: Document = {}
    for key, value in document.items():
        if isinstance(value, dict):
            numbers = [v for v in value.values() if isinstance(v, int)]
            out[key + "_total"] = sum(numbers) if len(numbers) == len(value) else None
        elif value is None or isinstance(value, (str, int, float, bool)):
            out[key] = value
    return out


def _read(path: Path) -> Document | None:
    try:
        return json_object(read_bounded(path, MAX_FILE))
    except (OSError, ValueError):
        return None


def _plan(private: Path) -> tuple[bool, Document]:
    live = (private / "live-run.json").exists()
    name = "live-run.json" if live else "run.json"
    return live, json_object(read_bounded(private / name, 65536))


def _sql(private: Path, database: str, live: bool) -> Document:
    secrets = json_object(read_bounded(private / "secrets.json", 65536))
    config = HttpConfig(
        8123, database, "bootstrap", string_value(secrets["ch_bootstrap"]), 15
    )
    out: Document = {"error": None}
    try:
        out["version"] = _request(config, "SELECT version()", b"").decode().strip()
        row = _request(
            config,
            "SELECT count(), uniqExact(input_offset), max(input_offset) "
            f"FROM {database}.facts FORMAT JSONCompactEachRow",
            b"",
        )
        physical, distinct, highest = json.loads(row)
        out.update(
            physical_rows=physical,
            distinct_inputs=distinct,
            max_input_offset=highest if physical else None,
        )
        if live:
            body = _request(
                config,
                "SELECT connection, collector_age_ms, serving_age_ms, "
                "source_receipt_age_ms, position_receipt_age_ms "
                f"FROM {database}.live_state FORMAT JSONEachRow",
                b"",
            )
            lines = body.splitlines()
            out["live_state"] = json_object(lines[0]) if lines else None
    except Exception as failure:  # recorded, never hidden
        out["error"] = type(failure).__name__
    return out


def _kafka(evidence: Path, run_id: str) -> Document:
    out: Document = {"error": None}
    try:
        config = json_object(
            read_bounded(evidence / run_id / "config" / "archive.json", 262144)
        )
        kafka = kafka_client(config)  # refuses a changed cluster or topic identity
        out["identity_ok"] = True
        sources = object_value(config["sources"])
        names = {k: string_value(object_value(v)["topic"]) for k, v in sources.items()}
        consumer = kafka.consumer(run_id + "-status")
        try:
            ends = {}
            for which, topic in names.items():
                ends[which] = [
                    consumer.get_watermark_offsets(
                        kafka.sdk.TopicPartition(topic, p, 0), timeout=5, cached=False
                    )[1]
                    for p in range(kafka.partitions)
                ]
            out["input_end"] = ends["input"][0]
            out["output_end_total"] = sum(ends["output"])
        finally:
            consumer.close()
        group = kafka.consumer(run_id + "-processing")
        try:
            committed = group.committed(
                [kafka.sdk.TopicPartition(names["input"], 0, 0)], timeout=5
            )[0].offset
            out["processing_committed"] = committed if committed >= 0 else None
        finally:
            group.close()
    except Exception as failure:  # recorded, never hidden
        out["error"] = type(failure).__name__
    return out


def _s3() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:8333/", timeout=3)
    except urllib.error.HTTPError:
        return True  # an S3 refusal still proves the endpoint answers
    except OSError:
        return False
    return True


def snapshot(private: Path, evidence: Path) -> Document:
    live, plan = _plan(private)
    run_id = string_value(plan["run_id"])
    state = evidence / run_id / "state"
    progress = {
        name.removesuffix(".json"): (
            None if (document := _read(state / name)) is None else reduced(document)
        )
        for name in PROGRESS
    }
    return {
        "status": "ok",
        "run_id": run_id,
        "source": "live" if live else "f09",
        "clock_ms": time.time_ns() // 1_000_000,
        "progress": progress,
        "markers": {m.removesuffix(".json"): (state / m).exists() for m in MARKERS},
        "gateway_final_published": (_read(state / "gateway-complete.json") or {}).get(
            "published"
        ),
        "sql": _sql(private, string_value(plan["database"]), live),
        "s3_answers": _s3(),
        "kafka": _kafka(evidence, run_id),
    }


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _files(base: Path, label: str, root: Path) -> list[Document]:
    rows: list[Document] = []
    if not root.exists():
        return rows
    paths = [root] if root.is_file() else sorted(root.rglob("*"))
    for path in paths:
        if path.is_file() and not path.is_symlink():
            rows.append(
                {
                    "path": f"{label}/{path.relative_to(base).as_posix()}",
                    "bytes": path.stat().st_size,
                    "sha256": _digest(path),
                }
            )
    return rows


def inventory(evidence: Path, state: Path, run_id: str) -> Document:
    files = _files(evidence, "volume:evidence", evidence / run_id)
    # Exact names: another run's ID may start with this one.
    files += _files(state, "volume:state", state / f"{run_id}-checkpoints")
    pattern = re.compile(
        re.escape(run_id)
        + r"-(job|execution-plan)(-restore-[0-9a-f]{32}-chk-\d+)?\.json"
    )
    for path in sorted(state.iterdir()) if state.is_dir() else []:
        if pattern.fullmatch(path.name):
            files += _files(state, "volume:state", path)
    if len(files) > MAX_FILES:
        raise ValueError("inventory_limit")
    progress = evidence / run_id / "state"
    content = {
        name: document
        for name in CONTENT
        if (document := _read(progress / name)) is not None
    }
    return {"status": "ok", "files": files, "progress_files": content}


def checkpoints(state: Path, run_id: str) -> Document:
    rows = [
        {
            "path": metadata.parent.as_posix(),
            "metadata_mtime_ms": metadata.stat().st_mtime_ns // 1_000_000,
        }
        for metadata in (state / f"{run_id}-checkpoints").glob("*/chk-*/_metadata")
        if metadata.is_file() and not metadata.parent.is_symlink()
    ]
    rows.sort(key=lambda row: cast(int, row["metadata_mtime_ms"]), reverse=True)
    return {"status": "ok", "checkpoints": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("snapshot", "inventory", "checkpoints", "health")
    )
    parser.add_argument("--private", type=Path, default=Path("/private"))
    parser.add_argument("--evidence", type=Path, default=Path("/evidence"))
    parser.add_argument("--state", type=Path, default=Path("/state"))
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    try:
        if args.mode == "snapshot":
            document = snapshot(args.private, args.evidence)
        elif args.mode == "health":
            document = measure(args.private, args.evidence, args.state)
        else:
            if args.run_id is None or "/" in args.run_id or ".." in args.run_id:
                raise ValueError("run_id")
            document = (
                inventory(args.evidence, args.state, args.run_id)
                if args.mode == "inventory"
                else checkpoints(args.state, args.run_id)
            )
    except Exception as error:
        # Trust boundary: client exceptions may embed credentials or paths.
        print(json.dumps({"status": "failed", "category": type(error).__name__}))
        return 2
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
