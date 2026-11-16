"""Exercise the actual process function with point-access-only managed state."""

import hashlib
import importlib.util
import sys
from copy import deepcopy
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from recording_stream_support import battery, gps
from test_recording_runtime import RUN, SOURCE, events, policy

from telemetry.conversion_contract import json_line, json_object, object_value
from telemetry.recording_processing import process_events
from telemetry.recording_runtime import Document
from telemetry.recording_stream import STREAMS, event_bytes, make_event


def test_operator_state_work_and_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "pyflink.common",
        "pyflink.datastream.functions",
        "pyflink.datastream.state",
    ):
        monkeypatch.setitem(sys.modules, name, MagicMock())
    cast(
        MagicMock, sys.modules["pyflink.datastream.functions"]
    ).KeyedProcessFunction = type("KeyedProcessFunction", (), {"Context": object})
    path = Path(__file__).resolve().parents[1] / "runtime/pyflink/recording_operator.py"
    spec = importlib.util.spec_from_file_location("bounded_operator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = policy()
    context.update(end_us=10_000, battery_source_count=5000)
    stream = events()
    for ordinal in range(4, 1504):
        stamp = 1000 + ordinal
        stream.extend(
            [
                make_event(STREAMS[0], battery(ordinal, stamp), RUN),
                make_event(STREAMS[-1], gps(ordinal + 6, stamp), RUN),
            ]
        )
    stream += [stream[0], stream[2]]
    topic = cast(str, SOURCE["topic"])
    config: Document = {
        "format_version": "f09-recording-job-v1",
        "run_id": RUN,
        "input_topic": topic,
        "output_topic": "output",
        "processing_group": "process",
        "source": {k: v for k, v in SOURCE.items() if k != "partition"},
        "context": context,
        "context_sha256": hashlib.sha256(json_line(context)).hexdigest(),
        "max_age_us": 50,
        "deliveries": len(stream),
        "checkpoint_directory": f"file:///state/{RUN}-checkpoints",
        "job_file": f"/state/{RUN}-job.json",
        "bootstrap": "kafka:9092",
        "kafka_connection": {
            "format_version": "single-host-kafka-v1",
            "endpoint": "kafka:9092",
            "partitions": 12,
        },
    }
    backend = MagicMock()
    signatures: dict[str, str] = {}
    points = backend.get_map_state.return_value
    points.contains.side_effect = signatures.__contains__
    points.get.side_effect = signatures.__getitem__
    points.put.side_effect = signatures.__setitem__
    value = backend.get_state.return_value
    value.value.return_value = None
    operator = module.RecordingOperator(config)
    operator.open(backend)
    facts = []
    head_sizes = []
    for offset, event in enumerate(stream):
        if offset == len(stream) - 2:
            # No Python cache survives; only the most recent head and MapState do.
            value.value.return_value = value.update.call_args.args[0]
            operator = module.RecordingOperator(config)
            operator.open(backend)
            operator._load()
            bad = deepcopy(event)
            object_value(bad["payload"])["ground_speed_m_s"] = 2.0
            with pytest.raises(ValueError, match="refused"):
                list(
                    operator.process_element(
                        [
                            str(bad["measurement_id"]).encode(),
                            event_bytes(bad),
                            topic,
                            0,
                            offset,
                        ],
                        None,
                    )
                )
        points.reset_mock()
        value.update.reset_mock()
        row = [
            str(event["measurement_id"]).encode(),
            event_bytes(event),
            topic,
            0,
            offset,
        ]
        for output in operator.process_element(row, None):
            facts.append(object_value(json_object(output.encode())["fact"]))
        # First input seeds two context predecessors. No other map calls (including
        # iteration), and repeats don't write a signature, even after recreation.
        assert points.contains.call_count == 1
        assert points.get.call_count == int(offset >= len(stream) - 2)
        assert points.put.call_count == (
            3 if offset == 0 else int(offset < len(stream) - 2)
        )
        assert (
            len(points.method_calls)
            == 1 + points.get.call_count + points.put.call_count
        )
        value.update.assert_called_once()
        head_sizes.append(len(value.update.call_args.args[0].encode()))
    assert len(signatures) > 3000
    # Same populated streams, before and after 2900 more unique observations;
    # only numeric field widths and the latest bounded payloads may differ.
    assert max(head_sizes[100:]) <= head_sizes[100] + 128
    assert facts == process_events(stream, context, max_age_us=50)
    value.value.return_value = '{"binding":"old","next_offset":1,"runtime":{}}'
    operator.open(backend)
    with pytest.raises(ValueError, match="legacy_state"):
        operator._load()
