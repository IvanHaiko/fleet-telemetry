# ruff: noqa: I001, B017, B023, E731
# Preserve frozen imports/assertions and synchronous callback helpers.
"""Small real-child protocol suite; no shell, SDK or sandbox substitute."""

import base64
import json
import math
import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == "linux", "owned POSIX groups require Linux")
class ProcessTests(unittest.TestCase):
    def setUp(self):
        from runtime.archive_runtime.processes import run_worker

        self.run_worker = run_worker

    def run_child(self, code, handler=None, duration=5.0):
        startup = "import sys,json,time,os\njson.loads(sys.stdin.readline())\n"
        return self.run_worker(
            [sys.executable, "-c", startup + code],
            {"tiny": True},
            handler,
            expires=time.monotonic() + duration,
        )

    def refuses(self, code, duration=5.0, category=None):
        started = time.monotonic()
        with self.assertRaises(Exception) as caught:
            self.run_child(code, duration=duration)
        self.assertEqual(type(caught.exception).__name__, "ArchiveError")
        if category:
            self.assertEqual(caught.exception.category, category)
        self.assertLess(time.monotonic() - started, duration + 1.0)
        self.assertNotIn("RAW-SECRET", str(caught.exception))

    def test_done_waits_for_exit_and_handler_roundtrip(self):
        packet = {"op": "done", "answer": [1, "ok"]}
        code = f"print({json.dumps(json.dumps(packet))},flush=True)"
        self.assertEqual(self.run_child(code), packet)
        started = time.monotonic()
        self.run_child('print(\'{"op":"done"}\',flush=True)\ntime.sleep(0.12)')
        self.assertGreaterEqual(time.monotonic() - started, 0.1)
        descriptor = base64.b64encode(b"tiny descriptor\n").decode("ascii")
        requests = [
            {
                "op": op,
                "descriptor_b64": descriptor,
                "sha256": "sha256:" + "1" * 64,
            }
            for op in ("verify", "retain")
        ]
        requests.append({"op": "read_retained"})
        observed = []

        def handler(request: dict[str, object]) -> dict[str, object]:
            observed.append(request)
            return {"ack": len(observed)}

        code = f"requests={requests!r}\n"
        code += (
            "for i,request in enumerate(requests,1):\n"
            " print(json.dumps(request),flush=True)\n"
            " assert json.loads(sys.stdin.readline()) == {'ack':i}\n"
        )
        code += 'print(\'{"op":"done"}\',flush=True)'
        self.assertEqual(self.run_child(code, handler), {"op": "done"})
        self.assertEqual(observed, requests)

    def test_protocol_refusals_and_safe_diagnostics(self):
        frames = [
            "{",
            '{"op":"done","op":"done"}',
            '{"op":"done","x":NaN}',
            '{"op":"unknown"}',
            '{"op":"read_retained"}',
            '{"op":"error","category":"RAW-SECRET","field":"RAW-SECRET"}',
        ]
        for frame in frames:
            with self.subTest(frame=frame[:60]):
                self.refuses(f"sys.stdout.write({frame!r}+'\\n');sys.stdout.flush()")
        self.refuses(
            'sys.stdout.write(\'{"op":"done","x":"\''
            " + 'x'*(128*1024) + '\"}\\n');sys.stdout.flush()"
        )
        self.refuses("sys.stderr.write('RAW-SECRET');sys.exit(4)")
        self.refuses("pass")
        self.refuses('print(\'{"op":"done"}\',flush=True)\nsys.exit(4)')
        safe = {"op": "error", "category": "permission_denied", "field": "source"}
        self.refuses(
            f"print({json.dumps(safe)!r},flush=True)", category="permission_denied"
        )

    def test_deadlines_partial_lines_and_descendant_shutdown(self):
        for code in [
            "time.sleep(30)",
            "sys.stdout.write('{');sys.stdout.flush();time.sleep(30)",
            "while True:\n sys.stdout.write(' ');sys.stdout.flush();time.sleep(0.02)",
            'print(\'{"op":"done"}\',flush=True);time.sleep(30)',
        ]:
            self.refuses(code, duration=0.2, category="deadline_exceeded")
        scratch = Path(os.environ["ARCHIVE_TEST_SCRATCH"]).resolve(strict=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            pidfile = Path(directory) / "descendant.pid"
            code = "pid=os.fork()\nif pid==0:\n time.sleep(30)\nelse:\n"
            code += f" open({str(pidfile)!r},'w').write(str(pid))\n"
            code += ' print(\'{"op":"done"}\',flush=True)\n'
            try:
                self.refuses(code, duration=3.0)
                pid = int(pidfile.read_text())
                # A zombie is terminated; group reaping remains the worker's duty.
                proc = Path(f"/proc/{pid}/stat")
                if proc.exists():
                    self.assertEqual(proc.read_text().split(") ", 1)[1].split()[0], "Z")
            finally:
                if pidfile.exists():
                    try:
                        os.kill(int(pidfile.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            marker = Path(directory) / "launched"
            for expires in [
                True,
                0,
                -1,
                math.nan,
                math.inf,
                time.monotonic() - 1,
                time.monotonic() + 121,
            ]:
                with self.subTest(expires=expires):
                    with self.assertRaises(Exception) as caught:
                        self.run_worker(
                            [
                                sys.executable,
                                "-c",
                                f"open({str(marker)!r},'w').write('launched')",
                            ],
                            {},
                            expires=expires,
                        )
                    self.assertEqual(type(caught.exception).__name__, "ArchiveError")
                    self.assertFalse(marker.exists())
