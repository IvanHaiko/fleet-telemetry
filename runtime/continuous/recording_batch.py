"""Group archive-admitted serving outputs into one SQL write per batch.

The serving cursor is the only durable record of which output offsets reached
SQL. A batch therefore plans offsets in memory and publishes them only after the
SQL writer confirms the whole batch is reader-visible. A crash or a failed write
leaves the cursor at the last confirmed batch, so restart rereads every member.
"""

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

from runtime.continuous.recording_config import (
    MAX_DELIVERIES,
    Document,
    immutable,
    require,
)
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    object_value,
    string_value,
)

# The SQL writer admits 1..64 outputs per call (recording_sql.write_facts).
MAX_BATCH = 64
FAULT_POINT = "after_sql_ack_before_cursor"
FAULT_MARKER = "fault-after-sql-ack.json"
FAULT_EXIT_CODE = 70


class ServingBatch:
    """Outputs awaiting one write; `committed` changes only after it succeeds."""

    def __init__(self, committed: Document) -> None:
        self.committed = committed
        self.planned = dict(committed)
        self.outputs: list[Document] = []

    def expected(self, partition: int) -> int:
        return integer_value(self.planned[str(partition)])

    def full(self) -> bool:
        return len(self.outputs) >= MAX_BATCH

    def add(self, partition: int, offset: int, output: Document) -> None:
        require(
            not self.full() and offset == self.expected(partition),
            "recording_output_offset",
        )
        self.outputs.append(output)
        self.planned[str(partition)] = offset + 1

    def flush(
        self, write: Callable[[list[Document]], None], persist: Callable[[], None]
    ) -> None:
        """Write, then advance and persist the cursor; a raised write moves nothing."""
        if not self.outputs:
            return
        write(self.outputs)
        self.committed.update(self.planned)
        persist()
        self.outputs = []


def _exit(code: int) -> NoReturn:
    # No cleanup handlers run, as for a killed process.
    os._exit(code)


class AckCursorFault:
    """One-shot test fault between a confirmed SQL write and the cursor write.

    Only an explicit `serving_fault` configuration entry creates it; without one
    the worker calls the SQL writer directly. After the first confirmed batch
    that brings this process to `after_outputs` written outputs, it durably
    records the batch and exits without moving the cursor. The marker disarms
    every later process, so a restart with the same configuration rereads the
    batch instead of failing again.
    """

    def __init__(
        self,
        setting: object,
        root: Path,
        exit: Callable[[int], NoReturn] | None = None,
    ) -> None:
        row = object_value(setting)
        require(
            set(row) == {"point", "after_outputs"}
            and string_value(row["point"]) == FAULT_POINT,
            "recording_serving_fault",
        )
        self.after = integer_value(row["after_outputs"])
        require(1 <= self.after <= 2 * MAX_DELIVERIES, "recording_serving_fault")
        self.marker = root / FAULT_MARKER
        self.armed = not self.marker.exists()
        self.written = 0
        self.exit = _exit if exit is None else exit

    def wrap(
        self, write: Callable[[list[Document]], None], batch: ServingBatch
    ) -> Callable[[list[Document]], None]:
        def confirmed(outputs: list[Document]) -> None:
            write(outputs)
            self.written += len(outputs)
            if not self.armed or self.written < self.after:
                return
            members = [
                {"partition": int(partition), "offset": offset}
                for partition, start in batch.committed.items()
                for offset in range(
                    integer_value(start), batch.expected(int(partition))
                )
            ]
            immutable(
                self.marker,
                json_line(
                    {
                        "point": FAULT_POINT,
                        "after_outputs": self.after,
                        "written_by_process": self.written,
                        "cursor": dict(batch.committed),
                        "batch": members,
                        "input_offsets": sorted(
                            integer_value(output["input_offset"]) for output in outputs
                        ),
                        "written_ms": time.time_ns() // 1_000_000,
                    }
                ),
            )
            self.armed = False
            self.exit(FAULT_EXIT_CODE)

        return confirmed
