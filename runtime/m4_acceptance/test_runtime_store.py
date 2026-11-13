# ruff: noqa: I001, B017, B023, E731
# Preserve frozen imports/assertions and synchronous callback helpers.
"""Owned-prefix inventory and public raw-byte transport adapter checks."""

import copy
import hashlib
import unittest
from collections.abc import Mapping


PREFIX = "archive-v1/test-run/"
ORPHAN = "batches/" + "a" * 64 + ".jsonl"


class UnusedTransport:
    """Inventory must use listing alone, never transport byte operations."""

    def put(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("inventory performed a PUT")

    def get(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("inventory performed a GET")


class Listing:
    def __init__(self, pages):
        self.pages = iter(copy.deepcopy(pages))
        self.calls = []

    def list_objects_v2(self, **kwargs: object) -> Mapping[str, object]:
        self.calls.append(kwargs)
        return next(self.pages)


def page(entries=(), *, truncated=False, token=None):
    result = {
        "Contents": [{"Key": PREFIX + key, "Size": size} for key, size in entries],
        "IsTruncated": truncated,
    }
    if token is not None:
        result["NextContinuationToken"] = token
    return result


class StoreTests(unittest.TestCase):
    def make(self, pages):
        from runtime.s3.archive_store import ArchiveStore

        listing = Listing(pages)
        store = ArchiveStore(
            UnusedTransport(), listing, bucket="test-archive", prefix=PREFIX
        )
        self.assertEqual(listing.calls, [])
        return store, listing

    def refuses(self, pages):
        store, listing = self.make(pages)
        with self.assertRaises(Exception) as caught:
            store.inventory()
        self.assertIn(type(caught.exception).__name__, ("StoreError", "ArchiveError"))
        self.assertLessEqual(len(listing.calls), 65)

    def test_exact_prefix_pagination_orphans_and_fresh_inventory(self):
        store, listing = self.make(
            [
                page([("catalog.json", 10)], truncated=True, token="page-two"),
                page([(ORPHAN, 0)]),
                page([]),
            ]
        )
        self.assertEqual(set(store.inventory()), {("catalog.json", 10), (ORPHAN, 0)})
        self.assertEqual(list(store.inventory()), [])
        self.assertEqual(len(listing.calls), 3)
        for index, call in enumerate(listing.calls):
            self.assertEqual(call["Bucket"], "test-archive")
            self.assertEqual(call["Prefix"], PREFIX)
            self.assertIs(type(call["MaxKeys"]), int)
            self.assertTrue(1 <= call["MaxKeys"] <= 65)
            expected = {"Bucket", "Prefix", "MaxKeys"}
            if index == 1:
                expected.add("ContinuationToken")
                self.assertEqual(call["ContinuationToken"], "page-two")
            self.assertEqual(set(call), expected)

    def test_malformed_entries_tokens_and_overflow_refuse(self):
        malformed = [
            {"Contents": [], "IsTruncated": 1},
            {"Contents": "not a list", "IsTruncated": False},
            {"Contents": [None], "IsTruncated": False},
            {"Contents": [{"Key": PREFIX + "catalog.json"}], "IsTruncated": False},
        ]
        for key, size in [
            ("archive-v1/test-run-other/catalog.json", 1),
            (PREFIX + "../catalog.json", 1),
            (PREFIX + "catalog.json", True),
            (PREFIX + "catalog.json", -1),
            (PREFIX + "catalog.json", "1"),
            (42, 1),
        ]:
            malformed.append(
                {"Contents": [{"Key": key, "Size": size}], "IsTruncated": False}
            )
        for response in malformed:
            with self.subTest(response=response):
                self.refuses([response])
        for pages in [
            [page([("catalog.json", 1), ("catalog.json", 1)])],
            [
                page([("catalog.json", 1)], truncated=True, token="a"),
                page([("catalog.json", 1)]),
            ],
            [page([], truncated=True)],
            [page([], truncated=True, token="")],
            [page([], truncated=True, token=42)],
            [page([], truncated=True, token="a"), page([], truncated=True, token="a")],
            [page([(f"sources/{i:064x}.bin", 0) for i in range(65)])],
            [page([], truncated=True, token=f"page-{i}") for i in range(66)],
        ]:
            with self.subTest(pages=len(pages)):
                self.refuses(pages)

    def test_public_transport_reuse_and_fresh_bounded_lookup(self):
        from runtime.s3.archive_store import ArchiveStore
        from runtime.s3.immutable import RequestFailure, StoreError

        class RawTransport:
            def __init__(self):
                self.objects, self.calls, self.failures = {}, [], []

            def put(self, key: str, body: bytes) -> None:
                self.calls.append(("put", key, body))
                test.assertIs(type(body), bytes)
                if key in self.objects:
                    raise RequestFailure(412, "precondition failed")
                self.objects[key] = body

            def get(self, key: str, max_bytes: int) -> bytes:
                self.calls.append(("get", key, max_bytes))
                test.assertIs(type(max_bytes), int)
                test.assertGreater(max_bytes, 0)
                if self.failures:
                    raise RequestFailure(self.failures.pop(0), "fixture failure")
                if key not in self.objects:
                    raise RequestFailure(404, "missing")
                return self.objects[key]

        test = self
        transport, listing = RawTransport(), Listing([])
        store = ArchiveStore(transport, listing, bucket="test-archive", prefix=PREFIX)
        body = b"\x00original\xff\r\n"
        digest = hashlib.sha256(body).hexdigest()
        key = "sources/" + digest + ".bin"
        full_key = PREFIX + key
        self.assertEqual(store.create(key, body), "created")
        self.assertEqual(transport.objects, {full_key: body})
        self.assertEqual(store.create(key, body), "existing")
        self.assertEqual(store.read(key, "sha256:" + digest, len(body)), body)
        transport.calls.clear()
        self.assertEqual(store.lookup(key), body)
        transport.objects[full_key] = b"changed"
        self.assertEqual(store.lookup(key), b"changed")
        self.assertEqual([call[0] for call in transport.calls], ["get", "get"])
        del transport.objects[full_key]
        self.assertIsNone(store.lookup(key))
        transport.calls.clear()
        transport.failures = [403]
        with self.assertRaises(StoreError):
            store.lookup(key)
        self.assertEqual(len(transport.calls), 1)

        transport.objects[full_key] = body
        for status in (None, 409, 503):
            with self.subTest(status=status):
                transport.calls.clear()
                transport.failures = [status, status]
                self.assertEqual(store.lookup(key), body)
                self.assertEqual(len(transport.calls), 3)
                transport.calls.clear()
                transport.failures = [status] * 3
                with self.assertRaises(StoreError):
                    store.lookup(key)
                self.assertEqual(len(transport.calls), 3)
                self.assertTrue(all(call[0] == "get" for call in transport.calls))

        transport.calls.clear()
        oversized = b"x" * (16 * 1024 * 1024 + 1)
        with self.assertRaises(StoreError):
            store.create(key, oversized)
        self.assertEqual(transport.calls, [])
        transport.objects[full_key] = oversized
        with self.assertRaises(StoreError):
            store.lookup(key)
        self.assertTrue(1 <= len(transport.calls) <= 3)
        for malformed in ("../catalog.json", "/catalog.json"):
            with self.subTest(key=malformed):
                transport.calls.clear()
                for operation in (
                    lambda: store.create(malformed, body),
                    lambda: store.read(malformed, "sha256:" + digest, len(body)),
                    lambda: store.lookup(malformed),
                ):
                    with self.assertRaises(StoreError):
                        operation()
                self.assertEqual(transport.calls, [])
        self.assertEqual(listing.calls, [])
