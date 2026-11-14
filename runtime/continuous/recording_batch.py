"""Group archive-admitted serving outputs into one SQL write per batch.

The serving cursor is the only durable record of which output offsets reached
SQL. A batch therefore plans offsets in memory and publishes them only after the
SQL writer confirms the whole batch is reader-visible. A crash or a failed write
leaves the cursor at the last confirmed batch, so restart rereads every member.
"""

from collections.abc import Callable

from runtime.continuous.recording_config import Document, require
from telemetry.conversion_contract import integer_value

# The SQL writer admits 1..64 outputs per call (recording_sql.write_facts).
MAX_BATCH = 64


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
