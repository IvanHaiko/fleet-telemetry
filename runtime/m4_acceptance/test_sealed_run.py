"""Archive-derived receipt integrity and canonical report admission."""

import copy
import unittest
from fractions import Fraction
from unittest.mock import patch

from archive_fixture import Graph, canonical, digest

from runtime.clickhouse.transport import HttpConfig
from scripts.slice_run import (
    admitted_report,
    exact6,
    expected_run,
    publish_run,
    verify_events,
)
from telemetry.serving_projection import ServingScope


def terminal_graph():
    graph = Graph()
    graph.observations = [copy.deepcopy(graph.observations[i]) for i in (0, 4, 5, 6)]
    for offset, observation in enumerate(graph.observations):
        observation["offset"] = offset
    graph.seal()
    graph.catalog.update(start_offset=0, next_offset=4)
    graph.root()
    graph.descriptor.update(start_offset=0, next_offset=4)
    graph.descriptor_bytes = canonical(graph.descriptor)
    return graph


class SealedRunTests(unittest.TestCase):
    def setUp(self):
        self.graph = terminal_graph()
        self.scope = ServingScope("isolated-rebuild", "source-query-v1")
        self.seal = expected_run(
            self.graph.descriptor_bytes,
            digest(self.graph.descriptor_bytes),
            self.graph.store,
            self.scope,
        )

    def test_archive_reference_retains_lineage_and_exact_missing_counts(self):
        self.assertEqual(len(self.seal["events"]), 3)
        self.assertEqual(
            [row["disposition"] for row in self.seal["dispositions"]],
            ["eligible", "eligible", "eligible", "duplicate"],
        )
        self.assertEqual(
            [
                (row["metric"], row["valid_count"], row["value_sum"])
                for row in self.seal["windows"]
            ],
            [
                ("voltage_v", 3, "31.800000"),
                ("current_a", 2, "2.950000"),
                ("remaining_fraction", 1, "0.720000"),
            ],
        )
        self.assertTrue(
            all(
                row["source_dataset_run_id"] == "demo-synthetic-001"
                and row["dataset_run_id"] == self.scope.dataset_run_id
                for row in self.seal["events"]
            )
        )
        self.assertEqual(exact6(Fraction(-5, 4)), "-1.250000")
        with self.assertRaisesRegex(ValueError, "window_precision_loss"):
            exact6(Fraction(1, 3))

    def test_forged_or_incomplete_seal_never_reaches_query(self):
        incomplete = {**self.seal, "events": self.seal["events"][:2]}
        boolean_index = copy.deepcopy(self.seal)
        boolean_index["dispositions"][1]["observation_index"] = True
        for body, sha in (
            (canonical(self.seal), "sha256:" + "0" * 64),
            (canonical(incomplete), digest(canonical(incomplete))),
            (canonical(boolean_index), digest(canonical(boolean_index))),
        ):
            with self.subTest(sha=sha), patch("scripts.slice_run.reports") as reports:
                with self.assertRaises(ValueError):
                    admitted_report(
                        body,
                        sha,
                        self.graph.descriptor_bytes,
                        digest(self.graph.descriptor_bytes),
                        self.graph.store,
                        HttpConfig(18125, "slice", "reader", "test-only"),
                    )
                reports.assert_not_called()

    def test_canonical_omission_refuses_even_if_processing_facts_match(self):
        body = b"".join(canonical(row) for row in self.seal["events"][:2])
        with patch("scripts.slice_run.HttpReader") as native:
            native.return_value.read.return_value = body
            with self.assertRaisesRegex(ValueError, "canonical_fact_mismatch"):
                verify_events(
                    HttpConfig(18125, "slice", "reader", "test-only"),
                    self.scope,
                    self.seal,
                )

    def test_replay_refuses_original_scope_before_database_write(self):
        config = HttpConfig(18125, "slice", "test", "test-only")
        for original in ("test-run", "demo-synthetic-001"):
            with (
                self.subTest(original=original),
                patch("scripts.slice_run.publish_archive") as publish,
            ):
                with self.assertRaisesRegex(
                    ValueError, "replay_scope_must_be_isolated"
                ):
                    publish_run(
                        self.graph.descriptor_bytes,
                        digest(self.graph.descriptor_bytes),
                        self.graph.store,
                        ServingScope(original, "source-query-v1"),
                        config,
                        config,
                        self.graph.store,
                    )
                publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
