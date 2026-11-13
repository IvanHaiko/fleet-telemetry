"""Two finite loopback inputs coordinated by actual downstream observations."""

import base64
import json
import socket
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import cast

from battery_gate import bounded_input
from paced_source import receipt

IDLE_SECONDS = 30
MAX_INPUTS = 128


class IdleInputs:
    """Keep both sources open until idle/resume and all-silent checks complete."""

    def __init__(self, inputs: dict[str, bytes], control: Path) -> None:
        self.inputs, self.control = inputs, control
        self.listeners: list[socket.socket] = []
        self.connections: list[socket.socket] = []
        self.wires: list[bytes] = []
        self.phases: list[dict[str, object]] = []
        self.stop = threading.Event()
        self.failure: Exception | None = None
        self.completed = False
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def __enter__(self) -> "IdleInputs":
        try:
            for _ in range(2):
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.listeners.append(listener)
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                listener.settimeout(0.25)
            self.thread.start()
            return self
        except BaseException:
            self.stop.set()
            self.close()
            raise

    def close(self) -> None:
        for connection in self.connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        for listener in self.listeners:
            listener.close()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop.set()
        self.close()
        self.thread.join(3)
        if self.thread.is_alive():
            raise RuntimeError("idleness_thread_not_ended")
        if exc_type is None and (self.failure is not None or not self.completed):
            raise RuntimeError("idleness_source_failed") from self.failure

    def state(self) -> dict[str, int]:
        path = self.control / "state.json"
        if not path.exists():
            return {"observation_index": -1, "watermark_ms": -(2**63)}
        return cast(dict[str, int], json.loads(path.read_text()))

    def await_watermark(self, expected: int) -> None:
        deadline = time.monotonic() + 15
        while not self.stop.is_set() and time.monotonic() < deadline:
            current = self.state()["watermark_ms"]
            if current > expected:
                raise ValueError("idleness_watermark_overshoot")
            if current == expected:
                return
            self.stop.wait(0.025)
        raise TimeoutError("idleness_watermark_deadline")

    def send(self, lane: int, name: str) -> None:
        value = self.inputs[name]
        bounded_input([*self.wires, value])
        if len(self.wires) >= MAX_INPUTS:
            raise ValueError("idleness_input_limit")
        index = len(self.wires)
        self.wires.append(value)
        frame = (
            json.dumps(
                {"index": index, "wire": base64.b64encode(value).decode()}
            ).encode()
            + b"\n"
        )
        self.connections[lane].sendall(frame)
        deadline = time.monotonic() + 15
        gate = self.control / f"gate-{index}.json"
        while not self.stop.is_set() and time.monotonic() < deadline:
            if gate.exists():
                admitted = cast(dict[str, bool], json.loads(gate.read_text()))[
                    "admitted"
                ]
                if not admitted or self.state()["observation_index"] == index:
                    return
            self.stop.wait(0.025)
        raise TimeoutError("idleness_observation_deadline")

    def phase(self, name: str, **details: object) -> None:
        self.phases.append({"phase": name, **self.state(), **details})
        receipt(self.control / "phases.json", {"phases": self.phases})

    def exercise(self) -> None:
        self.send(0, "a0")
        self.send(1, "b0")
        self.await_watermark(-2001)
        slow_last = time.monotonic()
        self.send(0, "a12")
        self.await_watermark(-2001)
        # Activity on lane A prevents it becoming idle while B stays silent.
        held = False
        deadline = time.monotonic() + 55
        while time.monotonic() < deadline and not self.stop.is_set():
            current = self.state()["watermark_ms"]
            elapsed = time.monotonic() - slow_last
            if current == 9999:
                if not held or elapsed < IDLE_SECONDS - 1:
                    raise ValueError("idle_input_excluded_too_early")
                self.phase("idle_excluded", silent_seconds=elapsed)
                break
            if current != -2001:
                raise ValueError("unexpected_active_minimum")
            if elapsed >= 2 and not held:
                self.phase("active_minimum_held", silent_seconds=elapsed)
                held = True
            self.send(0, "a12")
            self.stop.wait(0.8)
        else:
            raise TimeoutError("idle_exclusion_deadline")

        self.send(1, "b9")
        self.await_watermark(9999)
        self.phase("resumed_old_event", observation_index=len(self.wires) - 1)
        self.send(1, "b9")
        self.send(1, "invalid")
        self.send(1, "b22")
        self.await_watermark(9999)
        self.phase("resumed_input_holds_minimum")
        self.send(0, "a22")
        self.await_watermark(19999)

        # Observe throughout silence, beyond the configured idle timeout.
        quiet_start = time.monotonic()
        while time.monotonic() - quiet_start < IDLE_SECONDS + 2:
            if self.stop.is_set():
                raise RuntimeError("idleness_cancelled")
            state = self.state()
            if state["watermark_ms"] != 19999 or state.get("windows") != 1:
                raise ValueError("silence_flushed_or_changed_window")
            self.stop.wait(0.1)
        self.phase("all_silent_no_eof", silent_seconds=time.monotonic() - quiet_start)

        self.send(1, "b32")
        self.await_watermark(29999)
        self.phase("resume_after_both_silent")
        self.send(0, "a21")
        self.await_watermark(29999)
        self.phase("second_resumed_old_event", observation_index=len(self.wires) - 1)
        self.send(0, "a42")
        self.await_watermark(29999)
        self.send(1, "b42")
        self.await_watermark(39999)
        self.phase("both_active_advanced")

    def serve(self) -> None:
        try:
            deadline = time.monotonic() + 60
            for listener in self.listeners:
                while not self.stop.is_set() and time.monotonic() < deadline:
                    try:
                        connection, _ = listener.accept()
                        connection.settimeout(2)
                        self.connections.append(connection)
                        break
                    except TimeoutError:
                        continue
                else:
                    raise TimeoutError("idleness_connection_deadline")
            self.exercise()
            self.completed = True
        except Exception as error:
            if not self.stop.is_set():
                self.failure = error
                receipt(self.control / "failure.json", {"reason": str(error)})
        finally:
            self.close()
