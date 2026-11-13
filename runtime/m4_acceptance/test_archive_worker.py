# ruff: noqa: B023
# Each injected callback is consumed synchronously in its loop iteration.
# ruff: noqa: B017
# Preserve the independently frozen broad failure assertions at injected ports.
"""Finite coordination checks; deterministic hooks are not isolation evidence."""

import copy
import unittest

from archive_fixture import SOURCE, Fault, Graph, Store, digest

from telemetry.archive_graph import verify_catalog
from telemetry.archive_worker import CommitAmbiguous, SourceState, archive_interval


class Source:
    def __init__(self, graph, trace):
        self.graph = graph
        self.trace = trace
        self.committed = 40
        self.commits = []
        self.overrides = {}
        self.ambiguity = None
        self.snapshot_count = 0
        self.change_after = None

    def snapshot(self):
        self.trace.append("snapshot")
        self.snapshot_count += 1
        fields = dict(
            source=SOURCE.copy(),
            low=40,
            high=47,
            committed=self.committed,
            delete_only=True,
            non_transactional=True,
            assigned=True,
        )
        fields.update(self.overrides)
        if self.change_after and self.snapshot_count > 1:
            fields.update(self.change_after)
        return SourceState(**fields)

    def observations(self, start, next_offset):
        self.trace.append("observations")
        return copy.deepcopy(self.graph.observations)

    def commit(self, next_offset):
        self.trace.append("commit")
        self.commits.append(next_offset)
        if self.ambiguity != "unchanged":
            self.committed = next_offset
        if self.ambiguity:
            raise CommitAmbiguous()


class Hooks:
    def __init__(self, case, store, trace):
        self.case = case
        self.store = store
        self.trace = trace
        self.retained = None
        self.fail = None

    def step(self, name):
        self.trace.append(name)
        if name == self.fail:
            raise Fault(name)

    def verify_fresh(self, descriptor, expected_sha256):
        self.step("fresh")
        # Deliberately a deterministic port, not a process-isolation claim.
        verify_catalog(descriptor, expected_sha256, self.store)

    def retain(self, descriptor, expected_sha256):
        self.step("retain")
        self.case.assertEqual(digest(descriptor), expected_sha256)
        self.retained = descriptor

    def read_retained(self):
        self.step("read_retained")
        return (
            b"wrong retained root" if self.fail == "wrong_retained" else self.retained
        )


class WorkerTests(unittest.TestCase):
    def setup_ports(self):
        self.graph = Graph()
        self.trace = []
        self.store = Store()
        self.source = Source(self.graph, self.trace)
        self.hooks = Hooks(self, self.store, self.trace)
        self.job = self.graph.archive_job()

    def setUp(self):
        self.setup_ports()

    def run_worker(self):
        return archive_interval(
            self.job, self.graph.blobs(), self.source, self.store, self.hooks
        )

    def test_publish_readback_retain_and_observe_before_success(self):
        descriptor = self.run_worker()
        self.assertEqual(self.source.commits, [47])
        self.assertEqual(self.hooks.retained, descriptor)
        self.assertLess(self.trace.index("fresh"), self.trace.index("retain"))
        self.assertLess(self.trace.index("retain"), self.trace.index("read_retained"))
        self.assertLess(self.trace.index("read_retained"), self.trace.index("commit"))
        commit = self.trace.index("commit")
        self.assertEqual(self.trace[commit - 1], "snapshot")
        self.assertIn("snapshot", self.trace[commit + 1 :])
        verify_catalog(descriptor, digest(descriptor), self.store)
        for index, (operation, key) in enumerate(self.store.calls):
            if operation == "create":
                self.assertIn(("read", key), self.store.calls[index + 1 :])

    def test_every_publication_readback_fault_prevents_partial_commit(self):
        self.run_worker()
        points = list(
            dict.fromkeys(
                (op, key.split("/")[0])
                for op, key in self.store.calls
                if op in ("create", "read")
            )
        )
        for operation, folder in points:
            with self.subTest(operation=operation, folder=folder):
                self.setup_ports()
                self.store.fail = lambda op, key: (
                    op == operation and key.split("/")[0] == folder
                )
                with self.assertRaises(Exception):
                    self.run_worker()
                self.assertEqual(self.source.commits, [])
        for name in ("fresh", "retain", "read_retained", "wrong_retained"):
            self.setup_ports()
            self.hooks.fail = name
            with self.assertRaises(Exception):
                self.run_worker()
            self.assertEqual(self.source.commits, [])

    def test_lost_commit_ack_uses_actual_progress(self):
        self.source.ambiguity = "advanced"
        self.run_worker()
        self.assertEqual(self.source.commits, [47])
        self.assertEqual(self.trace[-1], "snapshot")
        self.setup_ports()
        self.source.ambiguity = "unchanged"
        with self.assertRaises(Exception):
            self.run_worker()
        self.assertTrue(all(offset == 47 for offset in self.source.commits))

    def test_existing_catalog_retry_with_changed_batching(self):
        first = self.run_worker()
        originals = self.store.objects.copy()
        self.job["batch_size"] = 1
        second = self.run_worker()
        self.assertEqual(second, first)
        for key, body in originals.items():
            self.assertEqual(self.store.objects[key], body)
        self.graph.observations[0]["headers"].reverse()
        with self.assertRaises(Exception):
            self.run_worker()

    def test_source_progress_identity_profile_and_late_change(self):
        for changes in (
            {"committed": None},
            {"committed": 41},
            {"committed": 48},
            {"low": 41},
            {"high": 46},
            {"assigned": False},
            {"delete_only": False},
            {"non_transactional": False},
            {"source": {**SOURCE, "topic_id": "recreated"}},
        ):
            for late in (False, True):
                with self.subTest(changes=changes, late=late):
                    self.setup_ports()
                    if late:
                        self.source.change_after = changes
                    else:
                        self.source.overrides = changes
                    with self.assertRaises(Exception):
                        self.run_worker()
                    self.assertEqual(self.source.commits, [])
        self.setup_ports()
        del self.graph.observations[2]
        with self.assertRaises(Exception):
            self.run_worker()
        self.assertEqual(self.source.commits, [])

    def test_orphan_limits_before_new_writes(self):
        for inventory in (
            [("orphans/" + str(i), 1) for i in range(64)],
            [("orphans/large", 96 * 1024 * 1024)],
            [("orphans/overflow", 96 * 1024 * 1024 + 1)],
        ):
            self.setup_ports()
            self.store.extra_inventory = inventory
            with self.assertRaises(Exception):
                self.run_worker()
            self.assertFalse(any(op == "create" for op, key in self.store.calls))
            self.assertEqual(self.source.commits, [])
