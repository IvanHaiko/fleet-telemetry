"""New-topic visibility can lag creation ACK; recovery must still fail closed."""

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCENARIO = """
import sys
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, "scripts")
import kafka_producer_transport as transport

case = sys.argv[1]
topic = "fresh"
admin = Mock()
admin.list_topics.return_value = SimpleNamespace(
    cluster_id="cluster", brokers={1: SimpleNamespace(host="127.0.0.1", port=19092)})
description = Mock(spec=transport.TopicDescription)
description.name = topic
description.partitions = [SimpleNamespace(id=0)]
description.topic_id = "topic-id"
clock = [0.0]
calls = []

def describe(collection, request_timeout):
    calls.append(request_timeout)
    future = Future()
    if case == "visible" and len(calls) == 2:
        future.set_result(description)
    else:
        code = (transport.KafkaError.TOPIC_AUTHORIZATION_FAILED if case == "fatal"
                else transport.KafkaError.UNKNOWN_TOPIC_OR_PART)
        future.set_exception(transport.KafkaException(transport.KafkaError(code)))
    return {topic: future}

def sleep(seconds):
    clock[0] += seconds

admin.describe_topics.side_effect = describe
with patch.object(transport.time, "monotonic", lambda: clock[0]), \
        patch.object(transport.time, "sleep", sleep):
    try:
        result = transport.identity(admin, topic, wait_for_creation=case != "existing")
    except transport.KafkaException as error:
        assert case in ("existing", "fatal") and len(calls) == 1
        expected = (transport.KafkaError.TOPIC_AUTHORIZATION_FAILED if case == "fatal"
                    else transport.KafkaError.UNKNOWN_TOPIC_OR_PART)
        assert error.args[0].code() == expected
    except ValueError as error:
        assert case == "deadline" and str(error) == "topic_creation_visibility_deadline"
        assert clock[0] == 15 and max(calls) <= 10 and len(calls) <= 152
    else:
        assert case == "visible" and result == ("cluster", "topic-id")
        assert len(calls) == 2
"""


@pytest.mark.skipif(
    importlib.util.find_spec("confluent_kafka") is None,
    reason="Requires the pinned Kafka client; exercised by the M2 runner.",
)
@pytest.mark.parametrize("scenario", ["visible", "existing", "fatal", "deadline"])
def test_topic_creation_visibility_is_bounded_and_selective(scenario: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(SCENARIO), scenario],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
