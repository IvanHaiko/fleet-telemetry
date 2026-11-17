"""Evidence inventory completeness and readiness that never passes on unknowns.

The `evidence` and `state` volumes hold every run of the profile. A run's
inventory must list each of its files, nested ones and checkpoints included,
with the hash of its bytes, and nothing of another run. A checkpoint without
`_metadata` is incomplete and must not be offered for a restore.

Readiness compares two snapshots. A value the probe could not measure must
leave its check unknown, never passed, and traffic that did not advance must
fail; otherwise a stopped run could look ready.
"""

import hashlib
import os
from pathlib import Path
from typing import cast

from runtime.continuous.recording_status import checkpoints, inventory
from runtime.recording.ops_view import evaluate

RUN = "f09-ops-test-01"


def write(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def test_inventory_lists_every_run_file_and_nothing_else(tmp_path: Path) -> None:
    evidence, state = tmp_path / "evidence", tmp_path / "state"
    mine = {
        f"volume:evidence/{RUN}/state/producer-acks.jsonl": b"ledger\n",
        f"volume:evidence/{RUN}/state/outputs/p00-0001.json": b"{}\n",
        f"volume:evidence/{RUN}/config/archive.json": b'{"k": 1}',
        f"volume:state/{RUN}-checkpoints/abc/chk-3/_metadata": b"meta",
        f"volume:state/{RUN}-checkpoints/abc/chk-3/state-1": b"s1",
        f"volume:state/{RUN}-job.json": b"{}",
    }
    for name, body in mine.items():
        volume, _, relative = name.partition("/")
        write((evidence if volume.endswith("evidence") else state) / relative, body)
    write(evidence / "other-run" / "state" / "producer-acks.jsonl", b"x")
    write(state / "other-run-checkpoints" / "j" / "chk-1" / "_metadata", b"x")
    # A run whose ID starts with this one shares the volumes.
    write(state / f"{RUN}-2-checkpoints" / "j" / "chk-1" / "_metadata", b"x")
    write(state / f"{RUN}-2-job.json", b"x")
    write(evidence / f"{RUN}-2" / "state" / "producer-acks.jsonl", b"x")
    restore = f"{RUN}-job-restore-{'a' * 32}-chk-3.json"
    write(state / restore, b"{}")
    mine[f"volume:state/{restore}"] = b"{}"
    write(evidence / RUN / "state" / "producer-status.json", b'{"acknowledged":3}')
    mine[f"volume:evidence/{RUN}/state/producer-status.json"] = b'{"acknowledged":3}'

    document = inventory(evidence, state, RUN)

    rows = cast(list[dict[str, object]], document["files"])
    listed = {row["path"]: row for row in rows}
    assert set(listed) == set(mine)
    for name, body in mine.items():
        assert listed[name]["sha256"] == hashlib.sha256(body).hexdigest()
        assert listed[name]["bytes"] == len(body)
    assert document["progress_files"] == {"producer-status.json": {"acknowledged": 3}}


def test_only_complete_checkpoints_are_offered_newest_first(tmp_path: Path) -> None:
    base = tmp_path / f"{RUN}-checkpoints"
    for job, point, when in (("a", 4, 100), ("a", 5, 200), ("b", 2, 300)):
        write(base / job / f"chk-{point}" / "_metadata", b"m")
        os.utime(base / job / f"chk-{point}" / "_metadata", (when, when))
    write(base / "b" / "chk-3" / "state-1", b"incomplete, no _metadata")

    rows = cast(list[dict[str, object]], checkpoints(tmp_path, RUN)["checkpoints"])

    assert [Path(str(r["path"])).parts[-2:] for r in rows] == [
        ("b", "chk-2"),
        ("a", "chk-5"),
        ("a", "chk-4"),
    ]


def snapshot(*, inside: dict[str, object] | None, input_end: int) -> dict[str, object]:
    running = {"state": "running", "health": None}
    return {
        "containers": {
            "kafka": {"state": "running", "health": "healthy"},
            "archive-worker": running,
            "serving-worker": running,
            "publisher": running,
        },
        "flink": {"slots_total": 2, "job": {"jid": "j", "all_running": True}},
        "grafana": {"database": "ok"},
        "inside": inside
        if inside is not None
        else {
            "status": "ok",
            "clock_ms": 10_000,
            "kafka": {"identity_ok": True, "input_end": input_end},
            "progress": {
                name: {"written_ms": 9_000, "input_next": input_end}
                for name in ("archive-status", "serving-status", "producer-status")
            },
            "sql": {"error": None, "distinct_inputs": input_end},
            "s3_answers": True,
        },
    }


def test_unmeasured_values_never_pass_and_stalled_traffic_fails() -> None:
    before = snapshot(inside=None, input_end=10)
    failed_probe = snapshot(inside={"status": "failed"}, input_end=10)
    checks = evaluate(before, failed_probe, "f09")
    for name in ("broker_healthy", "clickhouse", "seaweedfs", "archive_worker"):
        assert checks[name] is None
    for name in ("input_advancing", "archive_advancing", "sql_advancing"):
        assert checks[name] is None

    stalled = evaluate(before, snapshot(inside=None, input_end=10), "f09")
    assert stalled["input_advancing"] is False
    assert stalled["sql_advancing"] is False
    assert stalled["checkpoints_completing"] is False

    moving = evaluate(before, snapshot(inside=None, input_end=20), "f09", 15)
    assert moving["input_advancing"] is True
    assert moving["fact_after_resume_visible"] is None  # no max offset measured
