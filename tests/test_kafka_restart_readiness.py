"""Coordinator readiness may recover; returned offsets must remain authoritative."""

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCENARIO = """
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

module = runpy.run_path("scripts/check-kafka-restart.py")
lookup = module["committed_offset"]
KafkaError, KafkaException = module["KafkaError"], module["KafkaException"]
case = sys.argv[1]
consumer = Mock()
clock = [0.0]
calls = []

def committed(partitions, timeout):
    calls.append(timeout)
    if case == "offset" or (case not in ("fatal", "deadline") and len(calls) == 2):
        return [SimpleNamespace(topic="retained", partition=0, error=None,
                                offset=0 if case == "offset" else 3)]
    code = (KafkaError.GROUP_AUTHORIZATION_FAILED if case == "fatal" else
            KafkaError.NOT_COORDINATOR if case == "deadline" else
            getattr(KafkaError, case))
    raise KafkaException(KafkaError(code))

def sleep(seconds):
    clock[0] += seconds

consumer.committed.side_effect = committed
with patch.object(module["time"], "monotonic", lambda: clock[0]), \
        patch.object(module["time"], "sleep", sleep):
    try:
        result = lookup(consumer, "retained")
    except KafkaException as error:
        assert case == "fatal" and len(calls) == 1
        assert error.args[0].code() == KafkaError.GROUP_AUTHORIZATION_FAILED
    except ValueError as error:
        assert case == "deadline" and str(error) == "coordinator_recovery_deadline"
        assert clock[0] == 15 and max(calls) <= 10 and len(calls) <= 152
    else:
        assert case not in ("fatal", "deadline")
        assert result == (0 if case == "offset" else 3)
        assert len(calls) == (1 if case == "offset" else 2)
"""


@pytest.mark.skipif(
    importlib.util.find_spec("confluent_kafka") is None,
    reason="Requires the pinned Kafka client; exercised by the M2 runner.",
)
@pytest.mark.parametrize(
    "scenario",
    [
        "NOT_COORDINATOR",
        "COORDINATOR_NOT_AVAILABLE",
        "COORDINATOR_LOAD_IN_PROGRESS",
        "fatal",
        "deadline",
        "offset",
    ],
)
def test_restart_offset_lookup_is_bounded_and_selective(scenario: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(SCENARIO), scenario],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
