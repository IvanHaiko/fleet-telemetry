"""Bounded nonblocking worker IPC with owned POSIX process-group shutdown."""

import ctypes
import json
import math
import os
import selectors
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from types import FrameType

from runtime.archive_runtime.config import strict_json
from telemetry.archive_codec import _fail

FRAME = 128 * 1024
STARTUP = 96 * 1024 * 1024
CATEGORIES = frozenset(
    {
        "invalid_format",
        "unsupported_profile",
        "limit_exceeded",
        "object_missing",
        "checksum_mismatch",
        "observation_conflict",
        "coverage_gap",
        "lineage_mismatch",
        "untrusted_catalog",
        "permission_denied",
        "deadline_exceeded",
        "source_unavailable",
        "progress_mismatch",
        "conditional_create_unsupported",
        "source_gap",
        "source_identity",
    }
)
FIELDS = frozenset(
    {
        "source",
        "commit",
        "retention",
        "offset",
        "committed",
        "assignment",
        "cleanup_policy",
        "observation",
        "catalog",
        "manifest",
        "receipt",
        "batch",
        "blob",
        "lineage",
        "measurement",
        "event_id",
        "registration",
        "pairs",
        "hidden_link",
        "destination",
        "destination_parent",
        "output",
        "retained",
        "hooks",
        "storage",
        "protocol",
        "worker",
        "timeout",
        "config",
        "path",
        "json",
        "credentials",
        "interval",
        "verified_at",
        "missing_catalog",
        "blobs",
    }
)


def encode(value: Mapping[str, object], maximum: int = FRAME) -> bytes:
    try:
        body = (
            json.dumps(
                dict(value), ensure_ascii=True, allow_nan=False, separators=(",", ":")
            )
            + "\n"
        ).encode()
    except (ValueError, TypeError, RecursionError):
        _fail("invalid_format", "protocol")
    if len(body) > maximum:
        _fail("limit_exceeded", "protocol")
    return body


def check_frame(frame: dict[str, object]) -> str:
    op = frame.get("op")
    if op in ("verify", "retain"):
        if set(frame) != {"op", "descriptor_b64", "sha256"} or not all(
            type(frame[key]) is str for key in ("descriptor_b64", "sha256")
        ):
            _fail("invalid_format", "protocol")
    elif op == "read_retained":
        if set(frame) != {"op"}:
            _fail("invalid_format", "protocol")
    elif op == "error":
        if set(frame) != {"op", "category", "field"}:
            _fail("invalid_format", "protocol")
        category, field = frame["category"], frame["field"]
        if (
            not isinstance(category, str)
            or category not in CATEGORIES
            or not isinstance(field, str)
            or field not in FIELDS
        ):
            _fail("invalid_format", "protocol")
        _fail(category, field)
    elif op != "done":
        _fail("invalid_format", "protocol")
    return str(op)


def _left(expires: float) -> float:
    remaining = expires - time.monotonic()
    if remaining <= 0:
        _fail("deadline_exceeded", "worker")
    return remaining


def _group_exists(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _kill(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _subreaper(enabled: int | None = None) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.restype = ctypes.c_int
    previous = ctypes.c_int()
    if prctl(37, ctypes.byref(previous), 0, 0, 0) != 0:
        _fail("unsupported_profile", "worker")
    if enabled is not None and prctl(36, enabled, 0, 0, 0) != 0:
        _fail("unsupported_profile", "worker")
    return previous.value


def _timeout(signum: int, frame: FrameType | None) -> None:
    _fail("deadline_exceeded", "worker")


@contextmanager
def _alarm(expires: float) -> Iterator[None]:
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    entered = time.monotonic()
    signal.signal(signal.SIGALRM, _timeout)
    delay = _left(expires)
    if previous_timer[0] > 0:
        delay = min(delay, previous_timer[0])
    signal.setitimer(signal.ITIMER_REAL, delay)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(
                signal.ITIMER_REAL,
                max(0.000001, previous_timer[0] - (time.monotonic() - entered)),
                previous_timer[1],
            )


def run_worker(
    argv: Sequence[str],
    request: Mapping[str, object],
    handler: Callable[[dict[str, object]], dict[str, object]] | None = None,
    *,
    expires: float,
) -> dict[str, object]:
    if (
        type(expires) not in (int, float)
        or not math.isfinite(expires)
        or not 0 < expires - time.monotonic() <= 120
    ):
        _fail("invalid_format", "timeout")
    if threading.current_thread() is not threading.main_thread():
        _fail("unsupported_profile", "worker")
    reserve = min(0.1, (expires - time.monotonic()) / 4)
    previous = _subreaper(1)
    try:
        with _alarm(expires - reserve):
            return _run(argv, request, handler, expires=expires)
    finally:
        _subreaper(previous)


def _run(
    argv: Sequence[str],
    request: Mapping[str, object],
    handler: Callable[[dict[str, object]], dict[str, object]] | None = None,
    *,
    expires: float,
) -> dict[str, object]:
    if (
        type(expires) not in (int, float)
        or not math.isfinite(expires)
        or not 0 < expires - time.monotonic() <= 120
    ):
        _fail("invalid_format", "timeout")
    if not argv or any(
        type(arg) is not str or not arg or "\x00" in arg for arg in argv
    ):
        _fail("invalid_format", "worker")
    pending = bytearray(encode(request, STARTUP))
    _left(expires)
    try:
        process = subprocess.Popen(
            list(argv),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env={},
            bufsize=0,
        )
    except OSError:
        _fail("source_unavailable", "worker")
    selector = selectors.DefaultSelector()
    done: dict[str, object] | None = None
    output = bytearray()
    stderr = bytearray()
    try:
        if process.stdin is None or process.stdout is None or process.stderr is None:
            _fail("source_unavailable", "worker")
        for pipe, kind in (
            (process.stdin, "input"),
            (process.stdout, "output"),
            (process.stderr, "error"),
        ):
            os.set_blocking(pipe.fileno(), False)
            selector.register(
                pipe,
                selectors.EVENT_WRITE if kind == "input" else selectors.EVENT_READ,
                kind,
            )
        while True:
            remaining = _left(expires)
            status = process.poll()
            if status is not None and not any(
                key.data == "output" for key in selector.get_map().values()
            ):
                if status == 0 and done is not None and not output:
                    # Collect exited adopted children only in our owned group.
                    # Live descendants remain present and must still fail below.
                    while True:
                        _left(expires)
                        try:
                            child, _ = os.waitpid(-process.pid, os.WNOHANG)
                        except ChildProcessError:
                            break
                        if child == 0:
                            break
                if status != 0 or done is None or output or _group_exists(process.pid):
                    _fail("source_unavailable", "worker")
                return done
            for key, _ in selector.select(min(remaining, 0.05)):
                _left(expires)
                fd = key.fd
                if key.data == "input":
                    try:
                        count = os.write(fd, pending[:65536])
                    except BrokenPipeError:
                        _fail("source_unavailable", "protocol")
                    del pending[:count]
                    if not pending:
                        selector.unregister(key.fileobj)
                    continue
                chunk = os.read(fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "error":
                    stderr.extend(chunk[: max(0, FRAME - len(stderr))])
                    continue
                output.extend(chunk)
                while b"\n" in output:
                    line, _, rest = output.partition(b"\n")
                    if len(line) + 1 > FRAME or done is not None:
                        _fail("limit_exceeded", "protocol")
                    output = bytearray(rest)
                    frame = strict_json(bytes(line), FRAME)
                    op = check_frame(frame)
                    if op == "done":
                        done = frame
                    else:
                        if handler is None or pending:
                            _fail("invalid_format", "protocol")
                        reply = handler(frame)
                        _left(expires)
                        pending.extend(encode(reply))
                        selector.register(process.stdin, selectors.EVENT_WRITE, "input")
                if len(output) >= FRAME:
                    _fail("limit_exceeded", "protocol")
    finally:
        _kill(process.pid)
        # Disable the active timer during the reserved shutdown window. Nested
        # invocations restore their caller's absolute timer through _alarm.
        signal.setitimer(signal.ITIMER_REAL, 0)
        shutdown = min(expires, time.monotonic() + 0.1)
        try:
            process.wait(timeout=max(0.001, shutdown - time.monotonic()))
        except subprocess.TimeoutExpired:
            _kill(process.pid)
        while _group_exists(process.pid) and time.monotonic() < shutdown:
            try:
                child, _ = os.waitpid(-process.pid, os.WNOHANG)
            except ChildProcessError:
                child = 0
            if child == 0:
                time.sleep(min(0.002, max(0, shutdown - time.monotonic())))
        selector.close()
        for owned_pipe in (process.stdin, process.stdout, process.stderr):
            if owned_pipe is not None:
                owned_pipe.close()
