"""Private run preparation scopes credentials and never overwrites evidence."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from runtime.recording import prepare as module
from telemetry.recordings import F09, RECORDINGS

AUTHORED = "sha256:" + hashlib.sha256(b"ULog").hexdigest()


@pytest.fixture(autouse=True)
def registered(monkeypatch: pytest.MonkeyPatch) -> None:
    # The authored original stands in for a registered recording (ADR-0057).
    monkeypatch.setitem(
        RECORDINGS, AUTHORED, replace(F09, source_id=AUTHORED, source_bytes=4)
    )


def inputs(root: Path) -> tuple[Path, Path, Path, Path]:
    bundle = root / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text(
        json.dumps({"run_id": "f09-authored-001", "events": 3, "source_id": AUTHORED}),
        encoding="utf-8",
    )
    (bundle / "events.jsonl").write_text("{}\n", encoding="utf-8")
    reference = root / "facts.jsonl"
    reference.write_text('{"n":1}\n', encoding="utf-8")
    source = root / "original.ulg"
    source.write_bytes(b"ULog")
    plugin = root / "plugin"
    plugin.mkdir()
    (plugin / "plugin.json").write_text("{}", encoding="utf-8")
    return bundle, reference, source, plugin


def test_prepare_scopes_keys_dashboard_and_refuses_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(
        module, "software", lambda: {"commit": "0" * 40, "worktree_clean": True}
    )
    bundle, reference, source, plugin = inputs(tmp_path)
    private = tmp_path / "private"
    summary = module.prepare(bundle, reference, source, private, plugin)
    assert summary["run_id"] == "f09-authored-001"
    assert summary["database"] == "f09_authored_001"
    secrets = json.loads((private / "secrets.json").read_text(encoding="utf-8"))
    # The printed summary never carries passwords or keys.
    rendered = json.dumps(summary)
    assert secrets["ch_bootstrap"] not in rendered
    identities = json.loads((private / "s3.json").read_text(encoding="utf-8"))
    actions = {row["name"]: row["actions"] for row in identities["identities"]}
    assert actions["reader"] == [
        "Read:fleet-f09-authored-001",
        "List:fleet-f09-authored-001",
    ]
    assert all(":" in action for action in actions["writer"])
    run = json.loads((private / "run.json").read_text(encoding="utf-8"))
    assert run["bundle"] == "/workspace/bundle"
    assert run["reference_bytes"] == len(reference.read_bytes())
    dashboard = (private / "dashboards/recording-stream.json").read_text(
        encoding="utf-8"
    )
    assert module.TEMPLATE_DATABASE not in dashboard
    assert dashboard.count('"f09_authored_001"') == 5
    environment = (private / "compose.env").read_text(encoding="utf-8")
    assert "RECORDING_RUN_ID=f09-authored-001\n" in environment
    with pytest.raises(ValueError, match="recording_private_scope"):
        module.prepare(bundle, reference, source, private, plugin)


def test_prepare_refuses_inputs_outside_the_mounted_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path / "repository")
    monkeypatch.setattr(
        module, "software", lambda: {"commit": "0" * 40, "worktree_clean": True}
    )
    (tmp_path / "repository").mkdir()
    bundle, reference, source, plugin = inputs(tmp_path)
    with pytest.raises(ValueError, match="recording_prepare_outside_repository"):
        module.prepare(bundle, reference, source, tmp_path / "private", plugin)
    assert not (tmp_path / "private" / "compose.env").exists()


def test_prepare_labels_the_registered_recording_and_binds_its_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(
        module, "software", lambda: {"commit": "0" * 40, "worktree_clean": True}
    )
    monkeypatch.setitem(
        RECORDINGS, AUTHORED, replace(RECORDINGS[AUTHORED], label="F07")
    )
    bundle, reference, source, plugin = inputs(tmp_path)
    module.prepare(bundle, reference, source, tmp_path / "private", plugin)
    dashboard = (tmp_path / "private/dashboards/recording-stream.json").read_text(
        encoding="utf-8"
    )
    # One shared template: the same panels, titled for the replayed recording.
    assert "F07 historical recording" in dashboard and "F09" not in dashboard

    source.write_bytes(b"ULoX")
    with pytest.raises(ValueError, match="recording_original_mismatch"):
        module.prepare(bundle, reference, source, tmp_path / "other", plugin)
    assert not (tmp_path / "other").exists()
