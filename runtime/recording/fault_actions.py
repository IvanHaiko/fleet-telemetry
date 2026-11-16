"""The declared faults of a recording run and the checks of their recovery.

Each action injects one failure through Docker or the Flink REST API, waits for
the profile's own recovery path, and returns a row of observer-clock times and
Flink states for the run's evidence. The serving fault fires inside the worker
(runtime/continuous/recording_batch.py), so the watcher reacts to it rather
than causing it.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import cast

from runtime.recording.profile import Document, Profile, RunFailure, require

KINDS = ("taskmanager-kill", "job-resubmit", "serving-ack-cursor", "archive-pause")
DEFAULT_RECOVERY_S = {
    "taskmanager-kill": 120.0,
    "job-resubmit": 180.0,
    "serving-ack-cursor": 60.0,
    "archive-pause": 60.0,
}
# Same values as runtime.continuous.recording_batch, which needs the worker
# image's dependencies and is not imported on the host.
FAULT_EXIT_CODE = 70
FAULT_MARKER = "fault-after-sql-ack.json"


@dataclass(frozen=True)
class Fault:
    kind: str
    at: int  # acknowledged deliveries; for serving-ack-cursor, written outputs
    seconds: float = 0.0  # archive-pause length

    @property
    def name(self) -> str:
        return f"{self.kind}@{self.at}"

    @property
    def trigger(self) -> str:
        if self.kind == "serving-ack-cursor":
            return (
                "first confirmed SQL batch that brings the first serving "
                f"process to >= {self.at} written outputs"
            )
        return f"producer acknowledged deliveries >= {self.at}"

    @staticmethod
    def parse(text: str) -> Fault:
        match = re.fullmatch(r"([a-z-]+)@([0-9]+)(?::([0-9]+))?", text)
        require(match is not None and match[1] in KINDS, "fault_syntax")
        assert match is not None
        seconds = float(match[3]) if match[3] else 0.0
        require((match[1] == "archive-pause") == (seconds > 0), "fault_syntax")
        return Fault(match[1], int(match[2]), seconds)


def _restored(run: Profile, job: str) -> Document | None:
    return run.checkpoint(job, "restored") if run.job_running(job) else None


def taskmanager_kill(run: Profile, fault: Fault) -> Document:
    """SIGKILL the TaskManager; the restart strategy restores a checkpoint."""
    job = run.running_job()
    start = run.clock()
    run.docker("kill", "--signal", "KILL", run.container("taskmanager"))
    killed = run.state("taskmanager")
    require(
        killed["ExitCode"] == 137 and not killed["OOMKilled"], "not_injected_sigkill"
    )
    # No checkpoint can complete while the TaskManager is down.
    completed = run.checkpoint(job, "completed")
    require(completed is not None, "no_completed_checkpoint_before_fault")
    assert completed is not None
    run.docker("start", run.container("taskmanager"))
    committed = run.processing_offset()
    point = cast(
        Document,
        run.wait(lambda: _restored(run, job), 240, "taskmanager_restore_timeout"),
    )
    after = run.checkpoint(job, "completed") or {}
    row: Document = {
        "name": fault.name,
        "kind": fault.kind,
        "job": job,
        "start_ms": start,
        "resume_ms": run.clock(),
        "latest_completed_before": completed["id"],
        "restored_checkpoint": point.get("id"),
        "restored_path_matches": point.get("external_path")
        == completed.get("external_path"),
        "committed_offset_at_restore": committed,
        "completed_after_offset_read": after.get("id"),
    }
    run.log("fault_done", **row)
    return row


def job_resubmit(run: Profile, fault: Fault) -> Document:
    """Cancel the job, then submit a new one from its retained checkpoint."""
    job = run.running_job()
    start = run.clock()
    run.rest(f"/jobs/{job}?mode=cancel", "PATCH")
    run.wait(
        lambda: run.rest(f"/jobs/{job}").get("state") == "CANCELED",
        120,
        "cancel_timeout",
    )
    completed = run.checkpoint(job, "completed")
    require(completed is not None, "no_completed_checkpoint_before_fault")
    assert completed is not None
    committed = run.processing_offset()
    path = str(completed["external_path"]).removeprefix("file:")
    output = run.docker(
        *run.compose,
        *"run --rm -T submit submit -py".split(),
        "/workspace/runtime/pyflink/recording_job.py",
        *("--config", f"/evidence/{run.run_id}/config/job.json", "--restore", path),
        timeout=600,
    )
    match = re.search(r"JobID ([0-9a-f]{32})", output)
    require(match is not None, "resubmit_failed")
    assert match is not None
    new = match[1]
    point = cast(
        Document, run.wait(lambda: _restored(run, new), 240, "resubmit_restore_timeout")
    )
    row: Document = {
        "name": fault.name,
        "kind": fault.kind,
        "job": job,
        "new_job": new,
        "start_ms": start,
        "resume_ms": run.clock(),
        "latest_completed_before": completed["id"],
        "restored_checkpoint": point.get("id"),
        "restored_path_matches": str(point.get("external_path")).removeprefix("file:")
        == path,
        "committed_offset_at_restore": committed,
    }
    run.log("fault_done", **row)
    return row


class Watcher:
    """Fail fast on unexpected exits; restart serving after its declared fault."""

    def __init__(
        self, run: Profile, serving: Fault | None, recovery: dict[str, float]
    ) -> None:
        self.run, self.serving, self.recovery = run, serving, recovery
        self.executed: list[Document] = []
        self.serving_handled = False

    def __call__(self) -> None:
        run = self.run
        for service in ("publisher", "archive-worker", "serving-worker"):
            state = run.state(service)
            if service in run.paused or state["Status"] != "exited":
                continue
            code = state["ExitCode"]
            if service == "serving-worker" and code == FAULT_EXIT_CODE:
                self._serving_fault(code)
                continue
            if code == 0 and service == "publisher":
                continue
            if code == 0:
                done = "serving" if service == "serving-worker" else "archive"
                if run.read_state(f"{done}-complete.json")[1] is not None:
                    continue
            raise RunFailure(f"{service}_exited_{code}")
        require(
            not any(j.get("state") == "FAILED" for j in run.jobs()), "flink_job_failed"
        )

    def _serving_fault(self, code: object) -> None:
        fault, run = self.serving, self.run
        require(
            fault is not None and not self.serving_handled, "serving_fault_repeated"
        )
        assert fault is not None
        _, marker = run.read_state(FAULT_MARKER)
        require(marker is not None, "serving_fault_marker_missing")
        assert marker is not None
        run.docker("start", run.container("serving-worker"))
        self.serving_handled = True
        row: Document = {
            "name": fault.name,
            "kind": fault.kind,
            "recovery_limit_s": self.recovery[fault.kind],
            "start_ms": marker["written_ms"],
            "resume_ms": run.clock(),
            "exit_code": code,
            "batch_members": len(cast(list[object], marker["batch"])),
            "written_by_process": marker["written_by_process"],
        }
        self.executed.append(row)
        run.log("fault_done", **row)


def archive_pause(run: Profile, fault: Fault, watch: Watcher) -> Document:
    """Stop the archive worker as ADR-0050 did; serving must hold at its prefix."""
    run.paused.add("archive-worker")
    start = run.clock()
    run.docker("stop", run.container("archive-worker"), timeout=120)
    require(run.state("archive-worker")["ExitCode"] == 0, "archive_unclean_stop")
    end = time.monotonic() + fault.seconds
    while time.monotonic() < end:
        watch()
        time.sleep(1)
    _, archive = run.read_state("archive-status.json")
    _, serving = run.read_state("serving-status.json")
    _, producer = run.read_state("producer-status.json")
    run.docker("start", run.container("archive-worker"))
    run.paused.discard("archive-worker")
    row: Document = {
        "name": fault.name,
        "kind": fault.kind,
        "start_ms": start,
        "resume_ms": run.clock(),
        "pause_s": fault.seconds,
        "archive_next_at_resume": (archive or {}).get("input_next"),
        "serving_archived_at_resume": (serving or {}).get("input_archived"),
        "serving_logical_at_resume": (serving or {}).get("logical_facts"),
        "producer_acknowledged_at_resume": (producer or {}).get("acknowledged"),
    }
    run.log("fault_done", **row)
    return row


def flink_evidence(run: Profile) -> Document:
    """States, checkpoint counts and exception names of this run's jobs."""
    jobs: list[Document] = []
    for overview in run.jobs():
        jid = str(overview["jid"])
        detail = run.rest(f"/jobs/{jid}")
        checkpoints = run.rest(f"/jobs/{jid}/checkpoints")
        history = cast(
            Document, run.rest(f"/jobs/{jid}/exceptions").get("exceptionHistory") or {}
        )
        entries = cast(list[Document], history.get("entries") or [])
        jobs.append(
            {
                "jid": jid,
                "state": detail.get("state"),
                "checkpoint_counts": checkpoints.get("counts"),
                "latest_restored": cast(Document, checkpoints["latest"]).get(
                    "restored"
                ),
                "exceptions": [
                    {"name": e.get("exceptionName"), "timestamp": e.get("timestamp")}
                    for e in entries
                ],
                # Both operators raise fixed text, e.g. when offset != deliveries.
                "operator_refusals": sum(
                    "_operator_refused" in str(e.get("stacktrace", "")) for e in entries
                ),
            }
        )
    return {"jobs": jobs}


def fault_checks(
    executed: list[Document], flink: Document, reconcile: Document, timing: Document
) -> Document:
    """One pass/fail entry per correctness condition of each executed fault."""
    jobs = cast(list[Document], flink["jobs"])
    checks: Document = {
        "no_operator_refusal": all(j["operator_refusals"] == 0 for j in jobs)
    }
    measured = {cast(str, m["name"]): m for m in cast(list[Document], timing["faults"])}
    starts = [
        r[0] for r in cast(list[list[int]], reconcile.get("repeated_output_ranges", []))
    ]
    positions = cast(Document, reconcile.get("restore_positions") or {})
    for row in executed:
        name, kind = row["name"], row["kind"]
        if kind in ("taskmanager-kill", "job-resubmit"):
            checks[f"{name}: restored latest completed checkpoint"] = (
                row["restored_checkpoint"] == row["latest_completed_before"]
                and row["restored_path_matches"] is True
            )
            # Re-emission must start at the first GPS fact of the restored source
            # position: earlier would refuse in the operator, later loses facts.
            first = positions.get(str(row.get("committed_offset_at_restore")))
            checks[f"{name}: re-emission starts at the restored position"] = (
                first is not None and first in starts
            )
        elif kind == "archive-pause":
            held = cast(Document, measured[cast(str, name)].get("held_at_resume") or {})
            archived = held.get("archive_next")
            shown = held.get("max_visible_input_offset")
            checks[f"{name}: serving held at the archive boundary"] = (
                isinstance(archived, int)
                and isinstance(shown, int)
                and shown < archived
                and held.get("serving_archived") == archived
                and cast(int, held.get("producer_acknowledged") or 0) > archived
            )
        elif kind == "serving-ack-cursor":
            batch = cast(Document, reconcile.get("fault_batch") or {})
            checks[f"{name}: batch reread without logical change"] = (
                row["exit_code"] == FAULT_EXIT_CODE
                and batch.get("members")
                == batch.get("members_in_sql")
                == row["batch_members"]
                and cast(int, batch.get("min_physical_rows_per_member", 0)) >= 2
                and batch.get("max_distinct_content_per_member") == 1
            )
    return checks
