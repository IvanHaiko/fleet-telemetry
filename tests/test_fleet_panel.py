"""Operator requests must remain within the active session and library."""

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from runtime.recording import panel
from runtime.recording import panel_services as services
from runtime.recording.panel_history import list_runs


def test_only_one_operation_and_only_member_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(panel, "DATA", tmp_path)
    console = panel.Console()
    console.sources["chosen"] = "a.ulg"
    console.state["phase"] = "Running"
    with pytest.raises(ValueError, match="not in this session"):
        console.submit("pause", "chosen")
    with pytest.raises(ValueError, match="Select a recording"):
        console.submit("add", "another.ulg")
    console.busy = "complete"
    with pytest.raises(ValueError, match="already running"):
        console.submit("stop", "")


def test_partial_evidence_does_not_hide_other_runs_or_last_sample(
    tmp_path: Path,
) -> None:
    for name, content in (
        ("first", '{"source":"f09","compose_project":"one"}'),
        ("second", '{"source":'),
    ):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "ops.json").write_text(content, encoding="utf-8")
    assert {r["run"]: r["project"] for r in list_runs(tmp_path)} == {
        "first": "one",
        "second": None,
    }
    sample = tmp_path / "observe.jsonl"
    sample.write_bytes(b'{"visible":7}\n{"visible":')
    assert panel.last_sample(sample) == {"visible": 7}


def test_healthy_flink_can_have_zero_jobs_and_s3_probe_can_be_unknown() -> None:
    response = CompletedProcess([], 0, '{"jobs-running":0,"taskmanagers":1}', "")
    with patch.object(services, "docker", return_value=response):
        flink = services.probe("jobmanager", "job-id", "Up", None)
    assert (flink["state"], flink["jobs"]) == ("Live", 0)
    assert services.probe("archive", "archive-id", "Up", None)["state"] == "Unknown"


def test_embedded_session_requires_verified_viewer_role() -> None:
    outputs = [
        "123456789abc",
        "127.0.0.1:13003",
        '{"login":"fleet_panel_viewer","isGrafanaAdmin":false}',
        '[{"role":"Editor"}]',
    ]
    with (
        patch.object(
            services,
            "docker",
            side_effect=[CompletedProcess([], 0, output, "") for output in outputs],
        ) as requests,
        pytest.raises(ValueError, match="Viewer role"),
    ):
        services.viewer_cookie("fleet-panel-local")
    assert all(
        "http://127.0.0.1:3000/login" not in call.args
        for call in requests.call_args_list
    )
