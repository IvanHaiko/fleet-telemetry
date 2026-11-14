"""A serving stop between the SQL acknowledgement and the cursor write is safe.

The worker writes a batch to SQL first and only then replaces its cursor file.
If the process dies in between, SQL already holds the batch while the cursor
still points at its first offset. A restart must reread that batch, write it
again without changing the logical result, and finish with the same evidence
as an uninterrupted run. The cursor must never claim an offset SQL has not
acknowledged.
"""

import base64
import json
import time
from collections.abc import Callable
from pathlib import Path

import pytest

pytest.importorskip("fcntl")  # The worker module is Linux-only.

from runtime.continuous import recording_worker  # noqa: E402
from runtime.continuous.recording_batch import MAX_BATCH  # noqa: E402
from telemetry.continuous_archive import durable_cursor  # noqa: E402

TOPIC = "recording-output"
OUTPUTS = 2 * MAX_BATCH + 22


class Clock:
    """Worker time that advances per call, so the test never waits on wall time."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        self.now += 0.05
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def time(self) -> float:
        return time.time()

    def time_ns(self) -> int:
        return time.time_ns()


class Crash(Exception):
    """Stands in for the process dying at one exact point."""


class Partition:
    def __init__(self, partition: int, offset: int) -> None:
        self.partition = partition
        self.offset = offset


class Consumer:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self.messages = messages
        self.position = 0

    def assign(self, partitions: list[Partition]) -> None:
        assert [p.partition for p in partitions] == [0]
        self.position = partitions[0].offset

    def poll(self, timeout: float) -> dict[str, object] | None:
        if self.position >= len(self.messages):
            return None
        message = self.messages[self.position]
        self.position += 1
        return message

    def get_watermark_offsets(
        self, partition: Partition, timeout: float, cached: bool
    ) -> tuple[int, int]:
        return 0, len(self.messages)

    def close(self) -> None:
        pass


class Kafka:
    partitions = 1

    def __init__(self, messages: list[dict[str, object]]) -> None:
        self.messages = messages

    def consumer(self, group: str) -> Consumer:
        return Consumer(self.messages)

    def positions(self, topic: str, offsets: dict[str, int]) -> list[Partition]:
        assert topic == TOPIC
        return [Partition(int(p), offset) for p, offset in offsets.items()]


class Reader:
    def lookup(self, key: str) -> bytes | None:
        return b"{}"

    def close(self) -> None:
        pass


class Gate:
    """Every input is already archived; facts are the expected logical IDs."""

    def __init__(self, config: object, reader: object, root: Path) -> None:
        self.rows = list(range(OUTPUTS))
        self.wires = list(range(OUTPUTS))
        self.facts = {f"fact-{i}": i for i in range(OUTPUTS)}

    def advance(self) -> None:
        pass

    def admit(self, output: dict[str, object]) -> bool:
        return True


class SQL:
    """Keeps every physical write, like the real append-only facts table."""

    def __init__(self) -> None:
        self.physical: list[str] = []
        self.calls: list[list[int]] = []  # offsets of every confirmed write
        self.statuses: list[str] = []

    def write_facts(self, outputs: list[dict[str, object]]) -> None:
        self.physical.extend(str(output["id"]) for output in outputs)
        self.calls.append([int(str(output["offset"])) for output in outputs])

    def acknowledged(self) -> set[int]:
        return {offset for call in self.calls for offset in call}

    def logical_count(self) -> int:
        return len(set(self.physical))

    def logical_ids(self) -> set[str]:
        return set(self.physical)

    def progress(self, status: str, archived: int, logical: int, total: int) -> None:
        self.statuses.append(status)


def messages() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for offset in range(OUTPUTS):
        body = json.dumps({"id": f"fact-{offset}", "offset": offset}).encode()
        result.append(
            {
                "partition": 0,
                "offset": offset,
                "value_b64": base64.b64encode(body).decode(),
            }
        )
    return result


def run(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    kafka: Kafka,
    sql: SQL,
    persist: Callable[[Path, dict[str, object]], None],
) -> None:
    monkeypatch.setattr(recording_worker, "kafka_client", lambda config: kafka)
    monkeypatch.setattr(recording_worker, "storage", lambda config, role: Reader())
    monkeypatch.setattr(recording_worker, "sql_client", lambda config: sql)
    clock = Clock()
    monkeypatch.setattr(recording_worker, "time", clock)
    # A bound on simulated time keeps a regression from looping forever.
    monkeypatch.setattr(
        recording_worker, "lifetime", lambda config: (lambda: False, 10_000.0)
    )
    monkeypatch.setattr(recording_worker, "VerifiedInputs", Gate)
    monkeypatch.setattr(
        recording_worker,
        "observation",
        lambda message, source: {**source, **message},
    )
    monkeypatch.setattr(recording_worker, "read_output", json.loads)
    monkeypatch.setattr(recording_worker, "durable_cursor", persist)
    config: dict[str, object] = {
        "run_id": "gap-test",
        "sources": {"output": {"topic": TOPIC}},
    }
    recording_worker.serve(config, root)


def test_restart_after_sql_ack_before_cursor_keeps_one_logical_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "producer-status.json").write_text('{"status": "completed"}')
    kafka = Kafka(messages())
    sql = SQL()
    cursor = tmp_path / "serving-cursor.json"
    cursor_writes = 0

    def checked(path: Path, value: dict[str, object]) -> None:
        if path == cursor:
            offset = int(value["next"]["0"])  # type: ignore[index]
            missing = set(range(offset)) - sql.acknowledged()
            assert not missing, f"cursor ahead of SQL: {sorted(missing)[:5]}"
        durable_cursor(path, value)

    def dies_on_second_cursor_write(path: Path, value: dict[str, object]) -> None:
        nonlocal cursor_writes
        if path == cursor:
            cursor_writes += 1
            if cursor_writes == 2:
                raise Crash
        checked(path, value)

    with pytest.raises(Crash):
        run(monkeypatch, tmp_path, kafka, sql, dies_on_second_cursor_write)

    # SQL confirmed two exact batches; the cursor only knows about the first.
    first, second = list(range(MAX_BATCH)), list(range(MAX_BATCH, 2 * MAX_BATCH))
    assert sql.calls == [first, second]
    assert json.loads(cursor.read_text()) == {"next": {"0": MAX_BATCH}}
    assert not (tmp_path / "serving-complete.json").exists()
    evidence = {p.name: p.read_bytes() for p in (tmp_path / "outputs").iterdir()}
    assert len(evidence) == 2 * MAX_BATCH

    run(monkeypatch, tmp_path, kafka, sql, checked)

    # Restart replays exactly the unconfirmed-by-cursor batch, then the rest.
    assert sql.calls == [first, second, second, list(range(2 * MAX_BATCH, OUTPUTS))]
    # The second batch was written twice; logically nothing changed.
    assert sql.logical_ids() == set(Gate(None, None, tmp_path).facts)
    assert len(sql.physical) == OUTPUTS + MAX_BATCH
    assert max(sql.physical.count(i) for i in set(sql.physical)) == 2
    assert json.loads(cursor.read_text()) == {"next": {"0": OUTPUTS}}
    complete = json.loads((tmp_path / "serving-complete.json").read_text())
    assert complete["status"] == "completed"
    assert complete["logical_facts"] == OUTPUTS
    assert sql.statuses[-1] == "completed"
    # Replayed outputs matched the evidence files already on disk, which were
    # compared and kept rather than replaced.
    after = {p.name: p.read_bytes() for p in (tmp_path / "outputs").iterdir()}
    assert len(after) == OUTPUTS
    assert all(after[name] == body for name, body in evidence.items())
