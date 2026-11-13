"""Bounded, provisional diagnostics from actual source and keyed operator state."""

import fcntl
import hashlib
import json
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from pyflink.common import Row
from pyflink.datastream.functions import (
    KeyedProcessFunction,
    MapFunction,
    RuntimeContext,
)

from battery_gate import Admitted, BatteryScope
from battery_operator import BatteryOperator

MAX_ROW_BYTES = 65536
MAX_TRACE_BYTES = 1_048_576
MAX_FILES = 1024


def _encode(row: dict[str, object]) -> bytes:
    data = json.dumps(row, sort_keys=True, allow_nan=False).encode() + b"\n"
    if len(data) > MAX_ROW_BYTES:
        raise ValueError("persistent_diagnostic_row_limit")
    return data


def publish(control: Path, name: str, row: dict[str, object]) -> None:
    """Atomically retain a bounded receipt, accepting only identical retries."""
    if re.fullmatch(r"[a-z0-9-]+\.json", name) is None:
        raise ValueError("persistent_diagnostic_name")
    data = _encode(row)
    with (control / ".diagnostics.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = control / name
        if target.exists():
            if target.stat().st_size > MAX_ROW_BYTES or target.read_bytes() != data:
                raise ValueError("persistent_diagnostic_collision")
            return
        if sum(1 for _ in control.iterdir()) >= MAX_FILES:
            raise ValueError("persistent_diagnostic_file_limit")
        temporary = control / f".{name}.{os.getpid()}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def append_trace(control: Path, run_tag: str, row: dict[str, object]) -> str:
    """Append diagnostics under a lock; these are not transactional sink rows."""
    _validate_tag(run_tag)
    data = _encode(row)
    with (control / ".diagnostics.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = control / f"trace-{run_tag}.jsonl"
        with path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() + len(data) > MAX_TRACE_BYTES:
                raise ValueError("persistent_trace_limit")
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    return data.decode().rstrip("\n")


def _validate_tag(run_tag: str) -> None:
    if run_tag not in ("initial", "cold"):
        raise ValueError("persistent_run_tag")


class KafkaObservation(MapFunction):
    """Record exact Kafka bytes before admission, without changing the payload."""

    def __init__(self, control: Path, run_tag: str, topic: str, end: int) -> None:
        _validate_tag(run_tag)
        self.control, self.run_tag, self.topic, self.end = control, run_tag, topic, end

    def open(self, runtime_context: RuntimeContext) -> None:
        self.attempt = runtime_context.get_attempt_number()
        self.count = 0
        self.input_bytes = 0

    def map(self, value: Row) -> tuple[int, bytes]:
        key, wire, topic, partition, offset = tuple(value)
        if (
            not isinstance(key, (bytes, bytearray))
            or not isinstance(wire, (bytes, bytearray))
            or len(key) > MAX_ROW_BYTES
            or len(wire) > MAX_ROW_BYTES
            or topic != self.topic
            or type(partition) is not int
            or partition != 0
            or type(offset) is not int
            or not 0 <= offset < self.end
        ):
            raise ValueError("persistent_kafka_row")
        self.count += 1
        self.input_bytes += len(wire)
        if self.count > self.end or self.input_bytes > 1_048_576:
            raise ValueError("persistent_input_limit")
        publish(
            self.control,
            f"source-{self.run_tag}-{self.attempt}-{offset}.json",
            {
                "topic": topic,
                "partition": partition,
                "offset": offset,
                "key_sha256": hashlib.sha256(key).hexdigest(),
                "value_sha256": hashlib.sha256(wire).hexdigest(),
                "worker_pid": os.getpid(),
                "attempt": self.attempt,
                "run_tag": self.run_tag,
            },
        )
        return offset, bytes(wire)


class InvalidObservation(MapFunction):
    """Retain safe gate dispositions once per attempt and source position."""

    def __init__(self, control: Path, run_tag: str) -> None:
        _validate_tag(run_tag)
        self.control, self.run_tag = control, run_tag

    def open(self, runtime_context: RuntimeContext) -> None:
        self.attempt = runtime_context.get_attempt_number()

    def map(self, value: str) -> str:
        row = cast(dict[str, object], json.loads(value))
        offset = row.get("observation_index")
        if type(offset) is not int or not 0 <= offset < 32:
            raise ValueError("persistent_invalid_position")
        row.update(run_tag=self.run_tag, attempt=self.attempt)
        # The receipt is the once-per-attempt invalid diagnostic. The print sink
        # and trace are provisional and may repeat across checkpoint recovery.
        publish(
            self.control,
            f"invalid-{self.run_tag}-{self.attempt}-{offset}.json",
            row,
        )
        return json.dumps(row, allow_nan=False, sort_keys=True)


class ObservedBattery(BatteryOperator):
    """Preserve BatteryOperator descriptors, serializers, timers and semantics."""

    def __init__(
        self, scope: BatteryScope, control: Path, run_tag: str, identity_limit: int
    ) -> None:
        super().__init__(scope, identity_limit)
        _validate_tag(run_tag)
        self.control, self.run_tag = control, run_tag

    def open(self, runtime_context: RuntimeContext) -> None:
        super().open(runtime_context)
        self.attempt = runtime_context.get_attempt_number()
        self.first_offset: int | None = None

    def observation(self, offset: int, watermark: int) -> dict[str, object]:
        """Read the managed maps only while Flink has selected the current key."""
        unique = 0
        for stored in self.windows.values():
            row = cast(dict[str, object], json.loads(stored))
            count = row["unique_events"]
            if type(count) is not int:
                raise ValueError("persistent_window_count")
            unique += count
        return {
            "worker_pid": os.getpid(),
            "attempt": self.attempt,
            "run_tag": self.run_tag,
            "first_offset": self.first_offset,
            "offset": offset,
            "history_ids": sorted(self.history.keys()),
            "active_ids": sorted(self.active.keys()),
            "window_unique_events": unique,
            "watermark_ms": watermark,
        }

    def process_element(
        self, value: Admitted, ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        offset = value[0]
        if self.first_offset is None:
            self.first_offset = offset
        watermark = cast(int, ctx.timer_service().current_watermark())  # type: ignore[no-untyped-call]
        stem = f"{self.run_tag}-{self.attempt}-{offset}.json"
        publish(self.control, f"before-{stem}", self.observation(offset, watermark))
        try:
            for output in super().process_element(value, ctx):
                yield self.tag(output)
        except ValueError as error:
            if str(error) == "battery_history_limit":
                after_watermark = cast(int, ctx.timer_service().current_watermark())  # type: ignore[no-untyped-call]
                row = self.observation(offset, after_watermark)
                row.update(
                    refused_reason="battery_history_limit",
                    watermark_before=watermark,
                    watermark_after=after_watermark,
                )
                publish(self.control, f"refused-{stem}", row)
            raise
        watermark = cast(int, ctx.timer_service().current_watermark())  # type: ignore[no-untyped-call]
        publish(
            self.control, f"observation-{stem}", self.observation(offset, watermark)
        )

    def tag(self, output: str) -> str:
        row = cast(dict[str, object], json.loads(output))
        row.update(run_tag=self.run_tag, attempt=self.attempt)
        return append_trace(self.control, self.run_tag, row)

    def on_timer(
        self, timestamp: int, ctx: KeyedProcessFunction.OnTimerContext
    ) -> Iterator[str]:
        for output in super().on_timer(timestamp, ctx):
            yield self.tag(output)
