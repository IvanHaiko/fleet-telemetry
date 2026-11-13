"""Reports must not hide missing or conflicting processing facts."""

import unittest
from unittest.mock import patch

from runtime.clickhouse.transport import HttpConfig
from scripts.slice_queries import reconcile
from telemetry.serving_projection import ServingScope


class SliceQueryTests(unittest.TestCase):
    def test_missing_or_competing_fact_refuses_report(self):
        expected = {"observation_index": 0, "disposition": "eligible"}
        conflict = {**expected, "disposition": "late"}
        for actual in ([], [expected, conflict]):
            with (
                self.subTest(actual=actual),
                patch("scripts.slice_queries.query", return_value=actual),
            ):
                with self.assertRaisesRegex(
                    ValueError, "processing_fact_reconciliation_failed"
                ):
                    reconcile(
                        HttpConfig(18125, "slice", "reader", "test-only"),
                        ServingScope("test", "v1"),
                        [expected],
                        [],
                    )


if __name__ == "__main__":
    unittest.main()
