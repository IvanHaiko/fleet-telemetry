# ruff: noqa: E402
"""Observe one real two-member rebalance with retained backlog and exact bytes."""

import argparse
import hashlib
import json
import re
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from m3_transport import Transport
from m3_transport_types import Error, Message

from scripts.slice_queries import require
from telemetry.archive_documents import canonical


class Position(Protocol):
    topic: str
    partition: int
    offset: int
    error: Error | None


class GroupConsumer(Protocol):
    def subscribe(
        self,
        topics: list[str],
        *,
        on_assign: Callable[["GroupConsumer", list[Position]], None],
    ) -> None: ...
    def assign(self, positions: list[Position]) -> None: ...
    def assignment(self) -> list[Position]: ...
    def pause(self, positions: list[Position]) -> None: ...
    def resume(self, positions: list[Position]) -> None: ...
    def poll(self, timeout: float) -> Message | None: ...
    def committed(
        self, positions: Sequence[Position], *, timeout: float
    ) -> list[Position]: ...
    def commit(
        self, *, offsets: Sequence[Position], asynchronous: bool
    ) -> list[Position]: ...
    def close(self) -> None: ...


def run(source: Path, output: Path, group: str) -> None:
    require(re.fullmatch(r"m5-rebalance-[a-z0-9-]{1,48}", group), "group_scope")
    require(not output.exists(), "output_exists")
    manifest = json.loads((source / "manifest.json").read_bytes())
    topic, ends = manifest["topic"], manifest["ends"]
    expected = {
        (row["partition"], row["offset"]): (row["key_sha256"], row["value_sha256"])
        for row in manifest["records"]
    }
    require(len(expected) == sum(ends) <= 128, "source_bounds")
    operations: list[object] = []
    kafka = Transport(
        lambda kind, data: operations.append({"kind": kind, "data": data})
    )
    identity = kafka.identity(topic, 2)
    original = json.loads((source / "source-identity.json").read_bytes())
    require(
        all(identity[key] == original[key] for key in identity),
        "source_identity_changed",
    )

    def position(partition: int, offset: int) -> Position:
        return cast(Position, kafka.kafka.TopicPartition(topic, partition, offset))

    initializer = cast(GroupConsumer, kafka.consumer(group))
    try:
        initial = initializer.committed([position(p, 0) for p in range(2)], timeout=5)
        require(all(row.offset < 0 for row in initial), "group_already_exists")
        initialized = initializer.commit(
            offsets=[position(p, 0) for p in range(2)], asynchronous=False
        )
        require(
            len(initialized) == 2
            and all(row.offset == 0 and row.error is None for row in initialized),
            "group_init_failed",
        )
    finally:
        initializer.close()
    consumers = [cast(GroupConsumer, kafka.consumer(group)) for _ in range(2)]
    captured: dict[tuple[int, int], tuple[str, str]] = {}
    joining = False
    assignments: list[object] = []

    def assigned(
        index: int, consumer: GroupConsumer, partitions: list[Position]
    ) -> None:
        consumer.assign(partitions)
        assignments.append(
            {
                "member": index,
                "partitions": [p.partition for p in partitions],
                "time": time.monotonic(),
            }
        )
        if joining:
            consumer.pause(partitions)

    def poll(consumer: GroupConsumer) -> None:
        message = consumer.poll(0.2)
        if message is None:
            return
        error = message.error()
        if error is not None:
            require(error.code() == -191, "group_read_error")
            return
        key, value = message.key(), message.value()
        require(type(key) is bytes and type(value) is bytes, "unexpected_null")
        coordinate = (message.partition(), message.offset())
        hashes = (
            hashlib.sha256(cast(bytes, key)).hexdigest(),
            hashlib.sha256(cast(bytes, value)).hexdigest(),
        )
        require(expected.get(coordinate) == hashes, "group_bytes_mismatch")
        captured[coordinate] = hashes
        committed = consumer.commit(
            offsets=[position(coordinate[0], coordinate[1] + 1)], asynchronous=False
        )
        require(len(committed) == 1 and committed[0].error is None, "commit_failed")

    first, second = consumers
    try:
        first.subscribe([topic], on_assign=lambda c, p: assigned(0, c, p))
        deadline = time.monotonic() + 60
        while not captured and time.monotonic() < deadline:
            poll(first)
        require(len(first.assignment()) == 2 and bool(captured), "initial_assignment")
        first.pause(first.assignment())
        joining = True
        second.subscribe([topic], on_assign=lambda c, p: assigned(1, c, p))
        while time.monotonic() < deadline:
            poll(first)
            poll(second)
            a = {p.partition for p in first.assignment()}
            b = {p.partition for p in second.assignment()}
            if len(a) == len(b) == 1 and not a & b:
                break
        require(
            len(a) == len(b) == 1 and a | b == {0, 1} and not a & b, "rebalance_missing"
        )
        committed_at_rebalance = first.committed(
            [position(p, 0) for p in range(2)], timeout=5
        )
        backlog = sum(ends[p.partition] - p.offset for p in committed_at_rebalance)
        require(backlog > 0, "no_backlog_at_rebalance")
        for consumer in consumers:
            consumer.resume(consumer.assignment())
        while len(captured) < len(expected) and time.monotonic() < deadline:
            for consumer in consumers:
                poll(consumer)
        require(captured == expected, "rebalance_lost_observations")
        final = first.committed([position(p, 0) for p in range(2)], timeout=5)
        require(
            {p.partition: p.offset for p in final} == dict(enumerate(ends)),
            "final_progress",
        )
        with output.open("xb") as stream:
            stream.write(
                canonical(
                    {
                        "source_identity": identity,
                        "group": group,
                        "assignments": assignments,
                        "backlog_at_rebalance": backlog,
                        "observation_count": len(captured),
                        "exact_bytes_reconciled": True,
                        "final_offsets": {str(p.partition): p.offset for p in final},
                        "operations": operations,
                    }
                )
            )
    finally:
        for consumer in reversed(consumers):
            consumer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--group", required=True)
    args = parser.parse_args()
    run(args.source_evidence.resolve(), args.output.resolve(), args.group)
