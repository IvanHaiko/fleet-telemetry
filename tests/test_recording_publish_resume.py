"""The F09 publisher continues after a stop without gaps or logical repeats.

A whole-profile stop (as at host shutdown) sends SIGTERM to the publisher
between two deliveries. A later start of the same run must continue at the
next undelivered index: every declared delivery ends up at exactly one Kafka
offset equal to its index, and the acknowledgement ledger lists each offset
once. The broker may hold one record that the ledger does not, when the
process stopped between the acknowledgement and the ledger write; it is
admitted only if its bytes equal the next declared delivery. Any other
disagreement between the ledger and the broker is loss or foreign data and
refuses.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from runtime.continuous import recording_publish

TOPIC = "telemetry.publish-resume.input.v1"


class Message:
    def __init__(self, offset: int, value: bytes) -> None:
        self._offset, self._value = offset, value

    def topic(self) -> str:
        return TOPIC

    def partition(self) -> int:
        return 0

    def offset(self) -> int:
        return self._offset

    def value(self) -> bytes:
        return self._value

    def error(self) -> None:
        return None


class Broker:
    """One partition of the input topic and the clients that reach it."""

    def __init__(self) -> None:
        self.log: list[bytes] = []
        self.position = 0
        self.sdk = self

    # SDK surface used by the publisher.
    def Producer(self, config: dict[str, object]) -> "Broker":  # noqa: N802
        self.pending: list[tuple[bytes, Callable[[object, object], None]]] = []
        return self

    def TopicPartition(  # noqa: N802
        self, topic: str, partition: int, offset: int = 0
    ) -> tuple[str, int, int]:
        return topic, partition, offset

    def client_properties(self) -> dict[str, object]:
        return {}

    def consumer(self, group: str) -> "Broker":
        return self

    # Producer.
    def produce(
        self,
        topic: str,
        partition: int,
        key: bytes,
        value: bytes,
        on_delivery: Callable[[object, object], None],
    ) -> None:
        self.pending.append((value, on_delivery))

    def flush(self, timeout: float) -> int:
        for value, callback in self.pending:
            self.log.append(value)
            callback(None, Message(len(self.log) - 1, value))
        self.pending.clear()
        return 0

    # Consumer.
    def get_watermark_offsets(
        self, position: object, timeout: float, cached: bool
    ) -> tuple[int, int]:
        return 0, len(self.log)

    def assign(self, positions: list[tuple[str, int, int]]) -> None:
        self.position = positions[0][2]

    def poll(self, timeout: float) -> Message | None:
        if self.position >= len(self.log):
            return None
        message = Message(self.position, self.log[self.position])
        self.position += 1
        return message

    def close(self) -> None:
        pass


def inputs(count: int) -> tuple[list[dict[str, object]], list[bytes]]:
    # Equal native times keep the native-time pacing from waiting.
    events: list[dict[str, object]] = [
        {"measurement_id": f"m{i:04d}", "native_timestamp_us": 1000, "i": i}
        for i in range(count)
    ]
    wires = [json.dumps(e, sort_keys=True).encode() for e in events]
    return events, wires + [wires[1], wires[3]]  # the two declared repeats


def publish(
    root: Path,
    broker: Broker,
    wires: list[bytes],
    events: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
    stop_at: int | None = None,
) -> None:
    monkeypatch.setattr(
        recording_publish, "load_inputs", lambda config: (events, {}, wires)
    )
    monkeypatch.setattr(recording_publish, "kafka_client", lambda config: broker)
    monkeypatch.setattr(
        recording_publish,
        "lifetime",
        lambda config: (
            lambda: stop_at is not None and len(broker.log) >= stop_at,
            float("inf"),
        ),
    )
    config: dict[str, object] = {
        "run_id": "publish-resume",
        "sources": {"input": {"topic": TOPIC}},
    }
    recording_publish.publish(config, root)


def ledger(root: Path) -> list[dict[str, object]]:
    lines = (root / "producer-acks.jsonl").read_bytes().splitlines()
    return [json.loads(line) for line in lines]


def status(root: Path) -> object:
    return json.loads((root / "producer-status.json").read_bytes())["status"]


def test_stop_and_restart_delivers_each_index_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events, wires = inputs(12)
    broker = Broker()
    with pytest.raises(ValueError, match="recording_producer_stopped"):
        publish(tmp_path, broker, wires, events, monkeypatch, stop_at=5)
    assert status(tmp_path) == "stopped"
    assert len(broker.log) == 5

    publish(tmp_path, broker, wires, events, monkeypatch)

    assert broker.log == wires  # no gap, no repeat, offset == index
    assert [row["offset"] for row in ledger(tmp_path)] == list(range(len(wires)))
    assert status(tmp_path) == "completed"


def test_record_acknowledged_before_the_ledger_write_is_not_repeated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events, wires = inputs(12)
    broker = Broker()
    with pytest.raises(ValueError):
        publish(tmp_path, broker, wires, events, monkeypatch, stop_at=7)
    # The process stopped after the broker acknowledged offset 6 but before
    # its ledger line was written.
    path = tmp_path / "producer-acks.jsonl"
    path.write_bytes(b"".join(path.read_bytes().splitlines(keepends=True)[:6]))

    publish(tmp_path, broker, wires, events, monkeypatch)

    assert broker.log == wires
    assert [row["offset"] for row in ledger(tmp_path)] == list(range(len(wires)))


@pytest.mark.parametrize(
    "damage",
    ["broker_lost_acknowledged", "foreign_record", "ledger_changed", "ledger_torn"],
)
def test_disagreement_between_ledger_and_broker_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    events, wires = inputs(12)
    broker = Broker()
    with pytest.raises(ValueError):
        publish(tmp_path, broker, wires, events, monkeypatch, stop_at=6)
    path = tmp_path / "producer-acks.jsonl"
    if damage == "broker_lost_acknowledged":
        del broker.log[-1]
    elif damage == "foreign_record":
        broker.log.append(b'{"measurement_id":"foreign"}')
    elif damage == "ledger_changed":
        lines = path.read_bytes().splitlines(keepends=True)
        path.write_bytes(b"".join([lines[1], lines[0], *lines[2:]]))
    else:
        path.write_bytes(path.read_bytes()[:-3])
    before = list(broker.log)

    with pytest.raises(ValueError, match="recording_producer_"):
        publish(tmp_path, broker, wires, events, monkeypatch)

    assert broker.log == before  # nothing was published after the refusal


def test_fresh_run_refuses_a_topic_that_already_holds_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events, wires = inputs(4)
    broker = Broker()
    broker.log.append(wires[0])
    with pytest.raises(ValueError, match="recording_producer_topic_not_empty"):
        publish(tmp_path, broker, wires, events, monkeypatch)
    assert broker.log == [wires[0]]
