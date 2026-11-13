"""Owned loopback test input paced by observed downstream watermark receipts."""

import base64
import json
import socket
import threading
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import cast

from pyflink.datastream import OutputTag
from pyflink.datastream.functions import ProcessFunction

from battery_gate import Admitted, BatteryGate, BatteryScope


@dataclass(frozen=True)
class Scheduled:
    wire: bytes
    watermark_after: int


def receipt(path: Path, value: dict[str, object]) -> None:
    """Atomic local test coordination; not a durable processing receipt."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


def decode_frame(text: str) -> tuple[int, bytes]:
    """Only parent-authored transport framing reaches the canonical gate."""
    row = cast(dict[str, object], json.loads(text))
    index, value = row["index"], row["wire"]
    if type(index) is not int or not isinstance(value, str):
        raise ValueError("invalid_paced_frame")
    return index, base64.b64decode(value, validate=True)


class PacedGate(BatteryGate):
    def __init__(self, scope: BatteryScope, control: Path) -> None:
        super().__init__(scope)
        self.control = control

    def process_element(
        self, value: tuple[int, bytes], ctx: ProcessFunction.Context
    ) -> Iterator[Admitted | tuple[OutputTag, str]]:
        admitted = False
        for row in super().process_element(value, ctx):
            admitted = isinstance(row[0], int)
            yield row
        receipt(self.control / f"gate-{value[0]}.json", {"admitted": admitted})


class PacedSource:
    """Close the socket only after every scheduled observation is acknowledged."""

    def __init__(self, samples: Sequence[Scheduled], control: Path) -> None:
        self.samples, self.control = samples, control
        self.stop = threading.Event()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(0.25)
        self.port = cast(int, self.listener.getsockname()[1])
        self.failure: Exception | None = None
        self.completed = False
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def serve(self) -> None:
        try:
            deadline = time.monotonic() + 60
            while not self.stop.is_set() and time.monotonic() < deadline:
                try:
                    connection, _ = self.listener.accept()
                    break
                except TimeoutError:
                    continue
            else:
                raise TimeoutError("paced_connection_deadline")
            with connection:
                for index, sample in enumerate(self.samples):
                    frame = (
                        json.dumps(
                            {
                                "index": index,
                                "wire": base64.b64encode(sample.wire).decode(),
                            }
                        ).encode()
                        + b"\n"
                    )
                    connection.sendall(frame)
                    self.await_observation(index, sample.watermark_after)
            self.completed = True
        except Exception as error:
            if not self.stop.is_set():
                self.failure = error

    def await_observation(self, index: int, expected: int) -> None:
        deadline = time.monotonic() + 30
        gate, state = self.control / f"gate-{index}.json", self.control / "state.json"
        while not self.stop.is_set() and time.monotonic() < deadline:
            if gate.exists() and state.exists():
                admitted = cast(dict[str, object], json.loads(gate.read_text()))[
                    "admitted"
                ]
                status = cast(dict[str, int], json.loads(state.read_text()))
                if not admitted or status["observation_index"] == index:
                    if status["watermark_ms"] > expected:
                        raise ValueError("watermark_overshot_schedule")
                    if status["watermark_ms"] == expected:
                        return
            self.stop.wait(0.025)
        raise TimeoutError("paced_observation_deadline")

    def __enter__(self) -> "PacedSource":
        self.thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop.set()
        self.listener.close()
        self.thread.join(3)
        if self.thread.is_alive():
            raise RuntimeError("paced_source_thread_not_ended")
        if exc_type is None and (self.failure is not None or not self.completed):
            raise RuntimeError("paced_source_failed") from self.failure
