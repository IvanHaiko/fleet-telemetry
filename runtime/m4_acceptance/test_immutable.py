# ruff: noqa: B023
# Contract callbacks are consumed synchronously in their current loop iteration.
"""Contract tests; run from the candidate root, with no backend or SDK."""

import hashlib
import unittest
from collections import deque

from runtime.s3.immutable import ImmutableStore, RequestFailure, StoreError

PREFIX = "archive-v1/run-1/"
KEY = "objects/a.bin"
BODY = b"\x00archive\xff\n"


def digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def failure(status):
    return RequestFailure(status, "safe simulated failure")


class FakeTransport:
    """Strict queued outcomes: no storage semantics or implicit retry behavior."""

    def __init__(self, *, puts=(), gets=()):
        self.puts = deque(puts)
        self.gets = deque(gets)
        self.operations = []

    def _take(self, queue):
        if not queue:
            raise AssertionError("Unexpected transport call")
        outcome = queue.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def put(self, key, body):
        self.operations.append(("put", key, body))
        return self._take(self.puts)

    def get(self, key, max_bytes):
        self.operations.append(("get", key, max_bytes))
        return self._take(self.gets)


class ImmutableTests(unittest.TestCase):
    def store(self, *, puts=(), gets=(), limit=1024):
        transport = FakeTransport(puts=puts, gets=gets)
        return ImmutableStore(transport, PREFIX, max_bytes=limit), transport

    def assert_error(self, category, call):
        with self.assertRaises(StoreError) as caught:
            call()
        if category is not None:
            self.assertEqual(caught.exception.category, category)
        return caught.exception

    def assert_calls(self, transport, kinds, body=BODY, limit=1024):
        expected = [
            (kind, PREFIX + KEY, body if kind == "put" else limit) for kind in kinds
        ]
        self.assertEqual(transport.operations, expected)

    def test_create_acknowledged_requires_full_fresh_readback(self):
        for body in (b"", BODY, bytes(range(256))):
            with self.subTest(body_length=len(body)):
                store, transport = self.store(puts=[None], gets=[body])
                self.assertEqual(store.create(KEY, body), "created")
                self.assert_calls(transport, ["put", "get"], body)

    def test_acknowledgment_does_not_override_readback(self):
        for outcome, category in (
            (BODY[:-1], "observation_conflict"),
            (BODY + b"extra", "observation_conflict"),
            (failure(404), "object_missing"),
        ):
            with self.subTest(category=category):
                store, transport = self.store(puts=[None], gets=[outcome])
                self.assert_error(category, lambda: store.create(KEY, BODY))
                self.assert_calls(transport, ["put", "get"])

    def test_failed_put_resolves_identical_or_different_bytes(self):
        for status in (None, 409, 500, 503, 412):
            for observed in (BODY, b"different"):
                with self.subTest(status=status, observed=observed):
                    store, transport = self.store(
                        puts=[failure(status)], gets=[observed]
                    )
                    if observed == BODY:
                        self.assertEqual(store.create(KEY, BODY), "existing")
                    else:
                        self.assert_error(
                            "observation_conflict", lambda: store.create(KEY, BODY)
                        )
                    self.assert_calls(transport, ["put", "get"])

    def test_missing_after_retryable_put_allows_conditional_retry(self):
        for status in (None, 409, 500, 599):
            with self.subTest(status=status):
                store, transport = self.store(
                    puts=[failure(status), None], gets=[failure(404), BODY]
                )
                self.assertEqual(store.create(KEY, BODY), "created")
                self.assert_calls(transport, ["put", "get", "put", "get"])

    def test_missing_after_412_refuses_backend(self):
        store, transport = self.store(puts=[failure(412)], gets=[failure(404)])
        self.assert_error(
            "conditional_create_unsupported", lambda: store.create(KEY, BODY)
        )
        self.assert_calls(transport, ["put", "get"])

    def test_put_exhaustion_is_three_attempts_with_observation_each_time(self):
        store, transport = self.store(
            puts=[failure(None), failure(409), failure(503)],
            gets=[failure(404)] * 3,
        )
        self.assert_error("deadline_exceeded", lambda: store.create(KEY, BODY))
        self.assert_calls(transport, ["put", "get"] * 3)

    def test_get_budget_is_shared_across_put_resolution_cycles(self):
        store, transport = self.store(
            puts=[failure(None), None],
            gets=[failure(503), failure(404), failure(None)],
        )
        self.assert_error("deadline_exceeded", lambda: store.create(KEY, BODY))
        self.assert_calls(transport, ["put", "get", "get", "put", "get"])

    def test_create_readback_get_retries_without_repeating_put(self):
        store, transport = self.store(
            puts=[None], gets=[failure(None), failure(409), BODY]
        )
        self.assertEqual(store.create(KEY, BODY), "created")
        self.assert_calls(transport, ["put", "get", "get", "get"])

    def test_nonretryable_statuses_stop_immediately(self):
        for status, category in (
            (401, "permission_denied"),
            (403, "permission_denied"),
            (400, "unsupported_profile"),
            (404, "unsupported_profile"),
            (429, "unsupported_profile"),
        ):
            with self.subTest(status=status, phase="put"):
                store, transport = self.store(puts=[failure(status)])
                self.assert_error(category, lambda: store.create(KEY, BODY))
                self.assert_calls(transport, ["put"])
        for status, category in (
            (401, "permission_denied"),
            (403, "permission_denied"),
            (404, "object_missing"),
            (412, "unsupported_profile"),
            (429, "unsupported_profile"),
        ):
            for phase in ("read", "readback", "resolve"):
                if status == 404 and phase == "resolve":
                    continue
                with self.subTest(status=status, phase=phase):
                    puts = [] if phase == "read" else [None]
                    if phase == "resolve":
                        puts = [failure(None)]
                    store, transport = self.store(puts=puts, gets=[failure(status)])
                    call = (
                        (lambda: store.read(KEY, digest(BODY), len(BODY)))
                        if phase == "read"
                        else (lambda: store.create(KEY, BODY))
                    )
                    self.assert_error(category, call)
                    kinds = ["get"] if phase == "read" else ["put", "get"]
                    self.assert_calls(transport, kinds)

    def test_read_full_bytes_and_no_cache(self):
        store, transport = self.store(gets=[BODY, BODY, b""])
        for body in (BODY, BODY, b""):
            self.assertEqual(store.read(KEY, digest(body), len(body)), body)
        self.assert_calls(transport, ["get"] * 3)

    def test_create_does_not_seed_read_cache(self):
        store, transport = self.store(puts=[None], gets=[BODY, failure(404)])
        self.assertEqual(store.create(KEY, BODY), "created")
        self.assert_error(
            "object_missing", lambda: store.read(KEY, digest(BODY), len(BODY))
        )
        self.assert_calls(transport, ["put", "get", "get"])

    def test_read_retries_and_exhaustion(self):
        for status in (None, 409, 500, 503, 599):
            for succeeds in (True, False):
                with self.subTest(status=status, succeeds=succeeds):
                    tail = BODY if succeeds else failure(status)
                    store, transport = self.store(
                        gets=[failure(status), failure(status), tail]
                    )
                    call = lambda: store.read(KEY, digest(BODY), len(BODY))  # noqa: E731
                    if succeeds:
                        self.assertEqual(call(), BODY)
                    else:
                        self.assert_error("deadline_exceeded", call)
                    self.assert_calls(transport, ["get"] * 3)

    def test_read_checks_digest_and_length_independently(self):
        for checksum, length in (
            (digest(b"other"), len(BODY)),
            (digest(BODY), len(BODY) - 1),
            (digest(BODY), len(BODY) + 1),
        ):
            with self.subTest(checksum=checksum, length=length):
                store, transport = self.store(gets=[BODY])
                self.assert_error(
                    "checksum_mismatch", lambda: store.read(KEY, checksum, length)
                )
                self.assert_calls(transport, ["get"])

    def test_invalid_prefixes_and_limits_never_call_transport(self):
        prefixes = (
            "",
            "archive-v1/a",
            "archive-v1//",
            "archive-v1/A/",
            "archive-v1/-a/",
            "archive-v1/a_b/",
            "archive-v1/../",
            "archive-v1/" + "a" * 65 + "/",
            "archive-v1/a/extra/",
            "/archive-v1/a/",
            "archive-v1/é/",
            "archive-v1/a/\n",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                transport = FakeTransport()
                self.assert_error(
                    "invalid_format", lambda: ImmutableStore(transport, prefix)
                )
                self.assertEqual(transport.operations, [])
        for limit in (True, False, 0, -1, 16777217, 1.0, "1", None):
            with self.subTest(limit=limit):
                transport = FakeTransport()
                self.assert_error(
                    None, lambda: ImmutableStore(transport, PREFIX, max_bytes=limit)
                )
                self.assertEqual(transport.operations, [])

    def test_malicious_keys_rejected_before_io(self):
        keys = (
            "",
            ".",
            "..",
            "/a",
            "a/",
            "a//b",
            "a/../b",
            "a/./b",
            "https://host/a",
            "a\\b",
            "a%2fb",
            "a?x",
            "a#x",
            "é",
            "a\x00b",
            "a\nb",
            "a/ b",
            "_a",
            "-a",
            ".hidden",
            "a" * 129,
            "a" * 128 + "/" + "b" * 128,
            "../other/key",
            "archive-v1/../other/key",
        )
        for key in keys:
            for operation in ("create", "read"):
                with self.subTest(key=key, operation=operation):
                    store, transport = self.store()
                    call = (
                        (lambda: store.create(key, BODY))
                        if operation == "create"
                        else (lambda: store.read(key, digest(BODY), len(BODY)))
                    )
                    self.assert_error(None, call)
                    self.assertEqual(transport.operations, [])

    def test_valid_boundaries_are_accepted(self):
        key = "A" * 128 + "/" + "b" * 127
        prefix = "archive-v1/" + "a" * 64 + "/"
        transport = FakeTransport(puts=[None], gets=[b"x", b"x"])
        store = ImmutableStore(transport, prefix, max_bytes=1)
        self.assertEqual(store.create(key, b"x"), "created")
        self.assertEqual(store.read(key, digest(b"x"), 1), b"x")
        self.assertEqual(
            transport.operations,
            [
                ("put", prefix + key, b"x"),
                ("get", prefix + key, 1),
                ("get", prefix + key, 1),
            ],
        )
        ImmutableStore(FakeTransport(), PREFIX, max_bytes=16777216)

    def test_bad_read_metadata_and_body_rejected_before_io(self):
        for checksum in (
            "",
            "0" * 64,
            "sha256:" + "A" * 64,
            "sha256:" + "g" * 64,
            digest(BODY) + "\n",
            None,
        ):
            store, transport = self.store()
            self.assert_error(None, lambda: store.read(KEY, checksum, len(BODY)))
            self.assertEqual(transport.operations, [])
        for length in (True, False, -1, 1.0, "1", None):
            store, transport = self.store()
            self.assert_error(None, lambda: store.read(KEY, digest(BODY), length))
            self.assertEqual(transport.operations, [])
        store, transport = self.store()
        self.assert_error("limit_exceeded", lambda: store.read(KEY, digest(BODY), 1025))
        self.assertEqual(transport.operations, [])
        for body in (bytearray(BODY), memoryview(BODY), "secret-payload", None):
            store, transport = self.store()
            self.assert_error(None, lambda: store.create(KEY, body))
            self.assertEqual(transport.operations, [])
        store, transport = self.store(limit=1)
        error = self.assert_error(
            "limit_exceeded", lambda: store.create(KEY, b"secret-payload")
        )
        self.assertNotIn("secret-payload", str(error))
        self.assertEqual(transport.operations, [])


if __name__ == "__main__":
    unittest.main()
