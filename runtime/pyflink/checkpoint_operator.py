"""Real managed-state recovery observation and once-only worker termination."""

import json
import os
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
from checkpoint_control import append_trace, publish


class KafkaObservation(MapFunction):
    def map(self, value: Row) -> tuple[int, bytes]:
        """Keep the broker position paired with its unchanged canonical bytes."""
        key, wire, partition, offset = value[0], value[1], value[3], value[4]
        if (
            not isinstance(key, (bytes, bytearray))
            or not isinstance(wire, (bytes, bytearray))
            or len(wire) > 65536
            or type(partition) is not int
            or partition != 0
            or type(offset) is not int
            or not 0 <= offset < 32
        ):
            raise ValueError("unexpected_checkpoint_kafka_row")
        return offset, bytes(wire)


class RecoveryBattery(BatteryOperator):
    def __init__(
        self, scope: BatteryScope, control: Path, fault_offset: int, client_pid: int
    ) -> None:
        super().__init__(scope)
        self.control = control
        self.fault_offset = fault_offset
        if type(client_pid) is not int or client_pid <= 0:
            raise ValueError("invalid_checkpoint_client_pid")
        self.client_pid = client_pid

    def open(self, runtime_context: RuntimeContext) -> None:
        super().open(runtime_context)
        self.attempt = runtime_context.get_attempt_number()
        self.first = True

    def observation(self, offset: int) -> dict[str, object]:
        """Read actual managed state while the keyed context is active."""
        unique = 0
        for stored in self.windows.values():
            row = cast(dict[str, object], json.loads(stored))
            unique += cast(int, row["unique_events"])
        return {
            "worker_pid": os.getpid(),
            "attempt": self.attempt,
            "offset": offset,
            "history_ids": sorted(self.history.keys()),
            "active_ids": sorted(self.active.keys()),
            "window_unique_events": unique,
        }

    def process_element(
        self, value: Admitted, ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        offset = value[0]
        if self.first:
            if self.attempt > 0:
                restored = self.observation(offset)
                restored["first_offset"] = offset
                publish(self.control, "restored.json", restored)
            self.first = False
        if offset == self.fault_offset and self.attempt == 0:
            marker = self.control / "fault.json"
            if not marker.exists():
                if os.getpid() == self.client_pid:
                    raise RuntimeError("independent_worker_required")
                publish(
                    self.control,
                    "fault.json",
                    {
                        "worker_pid": os.getpid(),
                        "client_pid": self.client_pid,
                        "requested_exit_code": 87,
                        "offset": offset,
                        "attempt": self.attempt,
                    },
                )
                os._exit(87)
        for output in super().process_element(value, ctx):
            yield self.tag(output)
        publish(
            self.control,
            f"observation-{self.attempt}-{offset}.json",
            self.observation(offset),
        )

    def tag(self, output: str) -> str:
        row = cast(dict[str, object], json.loads(output))
        row["attempt"] = self.attempt
        append_trace(self.control, row)
        return json.dumps(row, allow_nan=False)

    def on_timer(
        self, timestamp: int, ctx: KeyedProcessFunction.OnTimerContext
    ) -> Iterator[str]:
        for output in super().on_timer(timestamp, ctx):
            yield self.tag(output)
