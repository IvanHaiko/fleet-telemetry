# ruff: noqa: I001, B017, B023, E731
# Preserve frozen imports/assertions and synchronous callback helpers.
"""Independent finite-source port checks; production imports occur at runtime."""

import base64
import copy
import time
import unittest
from collections.abc import Mapping

from runtime.m4_acceptance.archive_fixture import Graph, SOURCE, canonical


class Reader:
    def __init__(self, rows):
        self.rows = iter(copy.deepcopy(rows))
        self.source = SOURCE.copy()
        self.low, self.high, self.committed = 40, 47, 40
        self.delete_only = True
        self.active = False
        self.calls = []

    def inspect(self, timeout: float):
        from runtime.kafka_archive.types import SourceInfo

        assert 0 < timeout <= 120
        self.calls.append("inspect")
        return SourceInfo(
            self.source.copy(), self.low, self.high, self.committed, self.delete_only
        )

    def assign(self, start: int) -> None:
        self.calls.append(("assign", start))
        self.active = True

    def assigned(self) -> bool:
        self.calls.append("assigned")
        return self.active

    def poll(self, timeout: float) -> Mapping[str, object] | None:
        assert 0 < timeout <= 120
        self.calls.append("poll")
        return next(self.rows, None)

    def close(self) -> None:
        self.calls.append("close")


class Committer:
    def __init__(self):
        self.calls = []
        self.error = None

    def commit(self, next_offset: int, timeout: float) -> None:
        self.calls.append((next_offset, timeout))
        if self.error is not None:
            raise self.error

    def close(self) -> None:
        self.calls.append("close")


class SourceTests(unittest.TestCase):
    def setUp(self):
        from runtime.kafka_archive.source import ArchiveKafkaSource
        from telemetry.archive_lineage import registrations

        self.factory = ArchiveKafkaSource
        self.graph = Graph()
        self.registrations = registrations(
            self.graph.archive_job()["lineage"], self.graph.blobs()
        )

    def make(self, **kwargs):
        rows = copy.deepcopy(self.graph.observations)
        for row in rows:
            row["measurement"] = None
        reader, committer = Reader(rows), Committer()
        source = self.factory(
            reader,
            committer,
            SOURCE.copy(),
            40,
            47,
            self.registrations,
            non_transactional=True,
            **kwargs,
        )
        self.assertEqual(reader.calls, [])
        self.assertEqual(committer.calls, [])
        return source, reader, committer

    def refuses(self, call, category=None):
        with self.assertRaises(Exception) as caught:
            call()
        self.assertEqual(type(caught.exception).__name__, "ArchiveError")
        if category:
            self.assertEqual(caught.exception.category, category)

    def test_constructor_and_fresh_snapshot_assignment(self):
        for start, end, duration, non_tx in [
            (True, 47, 1, True),
            (40, False, 1, True),
            (40, 40, 1, True),
            (40, 73, 1, True),
            (40, 47, True, True),
            (40, 47, float("nan"), True),
            (40, 47, 0, True),
            (40, 47, 121, True),
            (40, 47, 1, False),
            (40, 47, 1, 1),
        ]:
            with self.subTest(args=(start, end, duration, non_tx)):
                reader, committer = Reader([]), Committer()
                self.refuses(
                    lambda: self.factory(
                        reader,
                        committer,
                        SOURCE.copy(),
                        start,
                        end,
                        self.registrations,
                        non_transactional=non_tx,
                        timeout_seconds=duration,
                    )
                )
                self.assertEqual((reader.calls, committer.calls), ([], []))
        for identity in [{**SOURCE, "partition": True}, {**SOURCE, "partition": 1}]:
            reader, committer = Reader([]), Committer()
            self.refuses(
                lambda: self.factory(
                    reader,
                    committer,
                    identity,
                    40,
                    47,
                    self.registrations,
                    non_transactional=True,
                )
            )
            self.assertEqual((reader.calls, committer.calls), ([], []))
        source, reader, committer = self.make()
        state = source.snapshot()
        self.assertEqual(
            (state.source, state.low, state.high, state.committed),
            (SOURCE, 40, 47, 40),
        )
        self.assertTrue(
            state.delete_only and state.non_transactional and state.assigned
        )
        reader.high, reader.committed = 50, 47
        fresh = source.snapshot()
        self.assertEqual((fresh.high, fresh.committed), (50, 47))
        reader.active = False
        self.refuses(source.snapshot, "unsupported_profile")
        self.assertEqual(reader.calls.count(("assign", 40)), 1)
        self.assertEqual(committer.calls, [])
        source.close()
        self.assertEqual((reader.calls[-1], committer.calls[-1]), ("close", "close"))
        source, reader, _ = self.make()
        reader.active = True
        source.snapshot()
        self.assertNotIn(("assign", 40), reader.calls)

    def test_original_rows_links_and_captured_interval(self):
        source, reader, committer = self.make()
        # Deliberately noncanonical whitespace in original event bytes is retained.
        expected = copy.deepcopy(self.graph.observations)
        original = b" \n" + canonical(self.graph.events[0]) + b" "
        expected[0]["value_b64"] = base64.b64encode(original).decode("ascii")
        unmatched = copy.deepcopy(self.graph.events[1])
        unmatched["delivery"]["dataset_run_id"] = "other-original-delivery"
        expected[4]["value_b64"] = base64.b64encode(canonical(unmatched)).decode(
            "ascii"
        )
        expected[4]["measurement"] = None
        rows = copy.deepcopy(expected)
        for row in rows:
            row["measurement"] = None
        reader.rows = iter(rows)
        source.snapshot()
        reader.high = 60
        self.refuses(lambda: source.observations(40, 48))
        self.assertEqual(tuple(source.observations(40, 47)), tuple(expected))
        self.assertEqual(committer.calls, [])

    def test_commit_budget_ambiguity_and_changed_source_refuse(self):
        from telemetry.archive_worker import CommitAmbiguous

        source, reader, committer = self.make()
        source.snapshot()
        self.refuses(lambda: source.commit(46))
        self.assertEqual(committer.calls, [])
        ambiguous = CommitAmbiguous()
        committer.error = ambiguous
        with self.assertRaises(CommitAmbiguous) as caught:
            source.commit(47)
        self.assertIs(caught.exception, ambiguous)
        self.assertEqual(len(committer.calls), 1)
        self.assertEqual(committer.calls[0][0], 47)
        self.assertTrue(0 < committer.calls[0][1] <= 5)
        for attribute, value, category in [
            ("low", 41, "source_gap"),
            ("committed", 43, "progress_mismatch"),
            ("delete_only", False, "unsupported_profile"),
            ("source", {**SOURCE, "topic_id": "different"}, "source_identity"),
        ]:
            with self.subTest(attribute=attribute):
                source, reader, committer = self.make()
                source.snapshot()
                setattr(reader, attribute, value)
                self.refuses(source.snapshot, category)
                self.assertEqual(committer.calls, [])
        source, reader, committer = self.make(timeout_seconds=0.01)
        time.sleep(0.025)
        self.refuses(source.snapshot, "deadline_exceeded")
        self.refuses(lambda: source.commit(47), "deadline_exceeded")
        self.assertEqual(committer.calls, [])
