"""Historical broker quarantine must precede process launch and artifact writes."""

import importlib.util
import json
import runpy
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("optimized", [False, True])
def test_local_matrix_refuses_without_starting_processes(
    tmp_path: Path, optimized: bool
) -> None:
    code = """
import runpy
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'scripts')
module = runpy.run_path('scripts/check-m2.py')
output = Path(sys.argv[1])
with patch('subprocess.run', side_effect=RuntimeError('external_process_attempted')):
    try:
        module['check'](Path('missing-job'), Path('missing-run'), 'probe', output)
    except ValueError as error:
        if str(error) != 'historical_broker_quarantined':
            raise RuntimeError('wrong_quarantine_reason') from error
    else:
        raise RuntimeError('quarantine_missing')
if output.exists():
    raise RuntimeError('unexpected_artifact_write')
"""
    output = tmp_path / "never-created"
    result = subprocess.run(
        [sys.executable, *(["-O"] if optimized else []), "-B", "-c", code, str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not output.exists()


@pytest.mark.parametrize("mode", ["graceful", "sigkill"])
@pytest.mark.skipif(
    importlib.util.find_spec("confluent_kafka") is None,
    reason="Requires the existing pinned Kafka client, without a broker.",
)
def test_restart_refuses_before_source_and_process_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = runpy.run_path(str(ROOT / "scripts/check-kafka-restart.py"))
    output = tmp_path / "never-created"
    with (
        patch("subprocess.run", side_effect=RuntimeError("external_process_attempted")),
        pytest.raises(ValueError, match="^historical_broker_quarantined$"),
    ):
        module["check"](Path("missing-job"), Path("missing-run"), "probe", output, mode)
    assert not output.exists()


def test_cli_reports_safe_reason(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "scripts/check-m2.py"),
            "--job",
            "missing-job",
            "--run",
            "missing-run",
            "--prefix",
            "probe",
            "--output",
            str(tmp_path / "never-created"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stderr) == {
        "status": "failed",
        "reason": "historical_broker_quarantined",
    }
