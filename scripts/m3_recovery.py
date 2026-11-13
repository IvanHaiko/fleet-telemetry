"""Checkpoint recovery lifecycle and bounded pressure acceptance lane."""

from __future__ import annotations

import json
import time

from m3_reference import check_reference, observed, schedule, scope_fields
from m3_runtime import Runtime, array, digest, integer, obj, require, text
from m3_transport import Transport


def checkpoint(
    runtime: Runtime, kafka: Transport, job: str, topic: str, group: str
) -> tuple[int, str, dict[str, object], str]:
    trigger = obj(runtime.rest("/jobs/" + job + "/checkpoints", {}))
    request = text(trigger["request-id"])
    runtime.wait(
        lambda: (
            obj(runtime.rest("/jobs/" + job + "/checkpoints/" + request)).get("status")
            == {"id": "COMPLETED"}
        ),
        "checkpoint_trigger",
        120,
    )

    def completed() -> object:
        data = obj(runtime.rest("/jobs/" + job + "/checkpoints"))
        latest = obj(data["latest"])
        return latest.get("completed")

    detail = obj(runtime.wait(completed, "checkpoint_completed", 120))
    require(detail.get("status") == "COMPLETED", "checkpoint_status")
    checkpoint_id = integer(detail["id"])
    path = text(detail["external_path"]).rstrip("/") + "/_metadata"
    require(
        path.startswith(("file:/state/checkpoints/", "file:///state/checkpoints/")),
        "checkpoint_path",
    )
    path = "file:///" + path.split("file:", 1)[1].lstrip("/")
    runtime.wait(
        lambda: kafka.committed(topic, group) == 3, "checkpoint_source_progress"
    )
    inventory = runtime.checkpoint_inventory()
    metadata = obj(inventory[path.removeprefix("file://")])
    return checkpoint_id, path, inventory, text(metadata["sha256"])


def find_before(
    runtime: Runtime, control: str, tag: str, minimum_attempt: int
) -> dict[str, object]:
    code = (
        "import pathlib,json,sys; p=pathlib.Path(sys.argv[1]); "
        "rows=[json.loads(f.read_text()) for f in p.glob(sys.argv[2])]; "
        "assert len(rows)<=128; print(json.dumps(rows))"
    )

    def probe() -> object:
        rows = array(
            json.loads(
                runtime.execute(
                    "jobmanager", code, control, "before-" + tag + "-*-3.json"
                )
            )
        )
        matching = [
            obj(r)
            for r in rows
            if obj(r).get("history_ids")
            and len(array(obj(r)["history_ids"])) == 3
            and integer(obj(r)["attempt"]) >= minimum_attempt
        ]
        return matching[-1] if matching else None

    return obj(runtime.wait(probe, "restored_prefix", 120))


def recovery(
    runtime: Runtime, kafka: Transport, topic: str, kind: str
) -> dict[str, object]:
    runtime.begin_lane(kind)
    records = schedule("tm" if kind == "taskmanager_sigkill" else "cold")
    identity = kafka.create(topic, 1)
    group, control = topic + "-group", "/state/" + kind
    manifest = runtime.manifest(
        kind,
        {
            "profile": "m3-persistent-input-v1",
            "topic": topic,
            "bootstrap": "kafka:9092",
            "group": group,
            "end": 9,
            "scope": scope_fields(),
        },
    )
    for record in records[:3]:
        kafka.send(topic, record)
    args = [
        "--manifest",
        manifest,
        "--control",
        control,
        "--checkpoints",
        "/state/checkpoints",
        "--identity-limit",
        "128",
    ]
    kafka.readback(topic, records[:3], [3])
    runtime.submit(kind, "persistent_job.py", [*args, "--run-tag", "initial"])
    job = runtime.finished(control, "initial")
    prefix = observed(runtime, control + "/observation-initial-0-2.json")
    ids = array(prefix["history_ids"])
    require(len(ids) == 3 and prefix.get("window_unique_events") == 3, "initial_prefix")
    checkpoint_id, uri, inventory, sha = checkpoint(runtime, kafka, job, topic, group)
    require(
        runtime.checkpoint_inventory(kind, retain=True) == inventory,
        "retained_copy_differs",
    )
    old_runtime = runtime.container(
        "taskmanager" if kind == "taskmanager_sigkill" else "jobmanager"
    )
    if kind == "taskmanager_sigkill":
        for record in records[3:5]:
            kafka.send(topic, record)
        observed(runtime, control + "/observation-initial-0-4.json")
        kafka.readback(topic, records[:5], [5])
        runtime.sample()
        runtime.pause_sampling()
        runtime.dc("kill", "-s", "SIGKILL", "taskmanager")
        killed = array(runtime.json_command(["docker", "inspect", old_runtime]))
        runtime.log("injected_sigkill", killed)
        require(
            obj(obj(killed[0])["State"])["OOMKilled"] is False, "injected_kill_was_oom"
        )
        runtime.dc(
            "up",
            "-d",
            "--force-recreate",
            "--no-build",
            "--pull",
            "never",
            "taskmanager",
        )
        tag = "initial"
    else:
        runtime.sample()
        runtime.pause_sampling()
        runtime.stop_services()
        runtime.client_exit(kind, interrupted=True)
        runtime.dc(
            "up",
            "-d",
            "--force-recreate",
            "--no-build",
            "--pull",
            "never",
            "kafka",
            "jobmanager",
            "taskmanager",
        )
        runtime.wait(runtime.ready, "cold_rest", 120)
        require(
            not array(obj(runtime.rest("/jobs/overview"))["jobs"]), "cold_session_jobs"
        )
        require(runtime.checkpoint_inventory() == inventory, "checkpoint_bytes_changed")
        require(kafka.identity(topic, 1) == identity, "cold_source_changed")
        kafka.readback(topic, records[:3], [3])
        runtime.submit(
            "cold-restored", "persistent_job.py", [*args, "--run-tag", "cold"], uri
        )
        tag = "cold"
        job = runtime.finished(control, tag)
        for record in records[3:5]:
            kafka.send(topic, record)
    runtime.sampling()
    new_runtime = runtime.container(
        "taskmanager" if kind == "taskmanager_sigkill" else "jobmanager"
    )
    require(new_runtime != old_runtime, "runtime_not_replaced")
    runtime.wait(
        lambda: (
            obj(obj(runtime.rest("/jobs/" + job + "/checkpoints"))["latest"]).get(
                "restored"
            )
            is not None
        ),
        "restored_checkpoint_rest",
        120,
    )
    restored = obj(
        obj(obj(runtime.rest("/jobs/" + job + "/checkpoints"))["latest"])["restored"]
    )
    require(restored.get("id") == checkpoint_id, "restored_checkpoint_id")
    before = find_before(
        runtime, control, tag, 1 if kind == "taskmanager_sigkill" else 0
    )
    require(
        set(map(text, array(before["history_ids"]))) == set(map(text, ids))
        and before.get("window_unique_events") == 3
        and before.get("first_offset") == 3,
        "managed_prefix_restore",
    )
    successful_attempt = integer(before["attempt"])
    if kind == "taskmanager_sigkill":
        require(successful_attempt > 0, "missing_recovery_attempt")
    restored_inventory = runtime.checkpoint_inventory()
    require(
        all(restored_inventory.get(k) == v for k, v in inventory.items()),
        "post_restore_original_checkpoint_changed",
    )
    sha_after = text(obj(restored_inventory[uri.removeprefix("file://")])["sha256"])
    metadata_hex = runtime.execute(
        "jobmanager",
        "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
        "assert p.stat().st_size<=1048576; print(p.read_bytes().hex())",
        uri.removeprefix("file://"),
    ).strip()
    require(
        digest(bytes.fromhex(metadata_hex)) == sha_after,
        "metadata_changed_during_capture",
    )
    runtime.log("post_restore_metadata_bytes", {"uri": uri, "hex": metadata_hex})
    runtime.log(
        "post_restore_pre_eof_metadata_hash",
        {"sha256": sha_after, "measured_monotonic": time.monotonic(), "uri": uri},
    )
    for record in records[5:]:
        kafka.send(topic, record)
    runtime.await_finished(control, job, tag)
    runtime.client_exit(kind if tag == "initial" else "cold-restored")
    all_rows = runtime.lines(control + "/trace-initial.jsonl")
    if tag == "cold":
        all_rows += runtime.lines(control + "/trace-cold.jsonl")
    rows = [
        r
        for r in all_rows
        if (
            obj(r).get("run_tag") == tag and obj(r).get("attempt") == successful_attempt
        )
        or (
            obj(r).get("run_tag") == "initial"
            and obj(r).get("attempt") == 0
            and obj(r).get("kind") == "disposition"
            and integer(obj(r)["observation_index"]) < 3
        )
    ]
    runtime.log(
        "recovery_reference", check_reference(runtime, records, rows, terminal=True)
    )
    kafka.readback(topic, records, [9])
    after = kafka.identity(topic, 1)
    require(after == identity, "recovery_source_changed")
    retained = runtime.checkpoint_inventory(kind)
    require(
        all(retained.get(k) == v for k, v in inventory.items()),
        "checkpoint_graph_changed",
    )
    return {
        "kind": kind,
        "source_before": identity,
        "source_after": after,
        "checkpoint_id": checkpoint_id,
        "checkpoint_status": text(restored.get("status", "COMPLETED")),
        "checkpoint_sha256_before": sha,
        "checkpoint_sha256_after": sha_after,
        "next_offset": 3,
        "first_restored_offset": integer(before["first_offset"]),
        "prefix_ids": ids,
        "restored_ids": array(before["history_ids"]),
        "restored_window_unique_events": integer(before["window_unique_events"]),
        "runtime_id_before": old_runtime,
        "runtime_id_after": new_runtime,
        "source_progress_from_checkpoint": restored["id"] == checkpoint_id,
        "status": text(obj(runtime.rest("/jobs/" + job))["state"]),
        "reference_match": True,
    }


def pressure(runtime: Runtime, kafka: Transport, topic: str) -> dict[str, object]:
    runtime.begin_lane("pressure")
    records = schedule("pressure")
    kafka.create(topic, 1)
    control = "/state/pressure"
    manifest = runtime.manifest(
        "pressure",
        {
            "profile": "m3-persistent-input-v1",
            "topic": topic,
            "bootstrap": "kafka:9092",
            "group": topic + "-group",
            "end": 4,
            "scope": scope_fields(),
        },
    )
    for record in records[:3]:
        kafka.send(topic, record)
    runtime.submit(
        "pressure",
        "persistent_job.py",
        [
            "--manifest",
            manifest,
            "--control",
            control,
            "--checkpoints",
            "/state/checkpoints",
            "--run-tag",
            "initial",
            "--identity-limit",
            "3",
        ],
    )
    job = runtime.finished(control, "initial")
    prefix = observed(runtime, control + "/observation-initial-0-2.json")
    require(len(array(prefix["history_ids"])) == 3, "pressure_prefix_history")
    kafka.send(topic, records[3])
    runtime.wait(
        lambda: obj(runtime.rest("/jobs/" + job)).get("state") == "FAILED",
        "pressure_refusal",
        120,
    )
    runtime.client_exit("pressure", interrupted=True)
    exceptions = runtime.rest("/jobs/" + job + "/exceptions")
    require(
        "battery_history_limit" in json.dumps(exceptions), "pressure_failure_reason"
    )
    before = observed(runtime, control + "/before-initial-0-3.json")
    require(
        len(array(before["history_ids"])) == 3
        and before.get("watermark_ms") == prefix.get("watermark_ms") == -(2**63),
        "pressure_state_changed",
    )
    runtime.sample()
    runtime.pause_sampling()
    require(runtime.sampler_error is None, "memory_sampler_failed")
    tm = [r for r in runtime.samples if r["service"] == "taskmanager"]
    require(bool(tm), "missing_taskmanager_memory")
    python_peak = 0
    for row in runtime.samples:
        peak, limit = int(text(row["memory.peak"])), int(text(row["memory.max"]))
        require(0 < peak < limit * 0.9, "memory_headroom")
        events = dict(line.split() for line in text(row["memory.events"]).splitlines())
        require(int(events["oom"]) == int(events["oom_kill"]) == 0, "observed_oom")
        for process in array(row["processes"]):
            p = obj(process)
            if row["service"] == "taskmanager" and p.get("kind") == "python":
                for field in ("rss", "hwm"):
                    value = p[field]
                    if isinstance(value, str):
                        python_peak = max(python_peak, int(value.split()[0]) * 1024)
    peak = max(int(text(r["memory.peak"])) for r in tm)
    require(
        all(int(text(r["memory.max"])) == 3 * 1024**3 for r in tm)
        and 0 < python_peak <= peak,
        "memory_measurement_bounds",
    )
    kafka.readback(topic, records, [4])
    return {
        "limit_bytes": 3 * 1024**3,
        "peak_bytes": peak,
        "python_rss_peak_bytes": python_peak,
        "oom_killed": False,
        "state_limit": 3,
        "history_at_limit": len(array(before["history_ids"])),
        "refused_reason": "battery_history_limit",
        "watermark_before": prefix["watermark_ms"],
        "watermark_after": before["watermark_ms"],
    }
