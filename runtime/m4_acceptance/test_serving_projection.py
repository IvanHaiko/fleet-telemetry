# ruff: noqa: I001, E501, B023
# Preserve frozen imports, literal checksum and synchronous fixture callbacks.
"""Independent contract gate; import the future candidate only when executed."""

import base64
import copy
import importlib
import json
from decimal import localcontext
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime" / "m4_acceptance"))

from archive_fixture import Graph, b64, canonical, digest  # noqa: E402


IDS = (
    "sha256:69bab69c2d17a4b26fe106cd20feaf128a70f9699a146eb28e36b607d05df760",
    "sha256:d1d0b623e9c088362c8299ead337287d86bc81a2c6bfaa9d612b32b6403ac70d",
    "sha256:b487b5e101415503c758accb6c4aceb1e82f132ef410ccb6bab5a46ae8c4bc4b",
)


def expected_semantic(index):
    """Literal public fixture expectations, independent of candidate output."""
    return {
        "vehicle_id": "demo-vehicle-001",
        "event_type": "telemetry.battery",
        "source_timestamp": (
            "2026-01-01T12:00:01.234567Z",
            "2026-01-01T12:00:01.234569Z",
            "2026-01-01T12:00:01.234570Z",
        )[index],
        "source_log_id": "sha256:a023177a0240f8202effe5ec8fa0f301aea8a09e73c25635311d1af370780ffc",
        "source_type": "synthetic",
        "source_stream": "battery_status:0",
        "source_record_index": (0, 2, 3)[index],
        "normalization_version": "battery-v1",
        "source_time": {
            "clock_basis": "boot_relative",
            "native_timestamp_us": (1234567, 1234569, 1234570)[index],
            "timestamp_kind": "measurement",
            "mapping": {
                "native_anchor_us": 0,
                "utc_anchor": "2026-01-01T12:00:00.000000Z",
                "anchor_kind": "synthetic_fixed",
                "anchor_uncertainty_us": None,
            },
        },
        "payload": (
            {"voltage_v": 15.8, "current_a": 4.2, "remaining_fraction": 0.72},
            {"voltage_v": 16, "current_a": -1.25, "remaining_fraction": None},
            {"voltage_v": 0, "current_a": None, "remaining_fraction": None},
        )[index],
        "quality_flags": ["synthetic_time_anchor"]
        if index == 0
        else ["source_value_missing", "synthetic_time_anchor"],
    }


def semantic_json(value):
    # All expected numbers here are literal short decimals or integers.
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def edit_event(graph, index, change):
    """Change archived bytes for every observation of this identity, then reseal."""
    for observation in graph.observations:
        link = observation["measurement"]
        if link is not None and link["event_id"] == IDS[index]:
            event = json.loads(base64.b64decode(observation["value_b64"]))
            change(event)
            observation["value_b64"] = b64(canonical(event))
    graph.seal()


class ServingProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = importlib.import_module("telemetry.serving_projection")
        cls.verify = staticmethod(
            importlib.import_module("telemetry.archive_graph").verify_catalog
        )

    def scope(self, run="rebuilt-run"):
        return self.api.ServingScope(run, "pipeline-v2")

    def project(self, graph, scope=None):
        return self.api.project_archive(
            graph.descriptor_bytes,
            digest(graph.descriptor_bytes),
            graph.store,
            self.scope() if scope is None else scope,
        )

    def refusal(self, graph, category, field):
        with self.assertRaises(self.api.ServingError) as caught:
            self.project(graph)
        self.assertEqual(
            (caught.exception.category, caught.exception.field), (category, field)
        )
        self.assertNotIn(IDS[0], str(caught.exception))
        self.assertNotIn("demo-vehicle-001", str(caught.exception))

    def test_complete_semantics_and_original_lineage(self):
        graph = Graph()
        before = copy.deepcopy(graph.store.objects)
        batch = self.project(graph)
        self.assertEqual(self.api.PROJECTION_VERSION, "serving-battery-exact6-v1")
        self.assertIsInstance(batch, self.api.ServingBatch)
        self.assertEqual(batch.scope, self.scope())
        self.assertEqual(
            batch.archive_descriptor_sha256, digest(graph.descriptor_bytes)
        )
        self.assertIsInstance(batch.rows, tuple)
        self.assertEqual(tuple(row.event_id for row in batch.rows), tuple(sorted(IDS)))
        numbers = (
            ("15.800000", "4.200000", "0.720000"),
            ("16.000000", "-1.250000", None),
            ("0.000000", None, None),
        )
        for row in batch.rows:
            index = IDS.index(row.event_id)
            expected = expected_semantic(index)
            self.assertIsInstance(row, self.api.ServingRow)
            self.assertEqual(row.semantic_json, semantic_json(expected))
            self.assertEqual(json.loads(row.semantic_json), expected)
            self.assertEqual(len(expected), 11)
            self.assertEqual(
                (row.voltage_v, row.current_a, row.remaining_fraction), numbers[index]
            )
            self.assertEqual(row.quality_flags, tuple(expected["quality_flags"]))
            self.assertEqual(row.vehicle_id, "demo-vehicle-001")
            self.assertEqual(row.source_timestamp, expected["source_timestamp"])
            self.assertEqual(
                (row.dataset_run_id, row.pipeline_version),
                ("rebuilt-run", "pipeline-v2"),
            )
            self.assertEqual(row.source_dataset_run_id, "demo-synthetic-001")
            self.assertEqual(row.source_job_sha256, digest(graph.job_bytes))
            self.assertEqual(
                row.archive_descriptor_sha256, digest(graph.descriptor_bytes)
            )
        self.assertEqual(graph.store.objects, before)
        self.assertTrue(all(operation == "read" for operation, _ in graph.store.calls))
        from dataclasses import FrozenInstanceError

        for obj, field in (
            (batch, "rows"),
            (batch.scope, "dataset_run_id"),
            (batch.rows[0], "voltage_v"),
        ):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, None)
        original = self.project(graph, self.scope("demo-synthetic-001"))
        self.assertEqual(
            [row.semantic_json for row in original.rows],
            [row.semantic_json for row in batch.rows],
        )
        self.assertTrue(
            all(
                row.source_job_sha256 == digest(graph.job_bytes)
                for row in original.rows
            )
        )

    def test_scope_validation_precedes_storage(self):
        class Derived(self.api.ServingScope):
            pass

        invalid = [None, True, {}, ("run", "v"), Derived("run", "v")]
        for value in (
            True,
            1,
            None,
            "",
            "../secret",
            "has space",
            "x/y",
            "é",
            "a" * 129,
        ):
            invalid.extend(
                (self.api.ServingScope(value, "v"), self.api.ServingScope("run", value))
            )
        for scope in invalid:
            with self.subTest(scope=scope):
                graph = Graph()
                with self.assertRaises(self.api.ServingError) as caught:
                    self.api.project_archive(
                        graph.descriptor_bytes,
                        digest(graph.descriptor_bytes),
                        graph.store,
                        scope,
                    )
                self.assertEqual(
                    (caught.exception.category, caught.exception.field),
                    ("invalid_scope", "scope"),
                )
                self.assertNotIn("../secret", str(caught.exception))
                self.assertEqual(graph.store.calls, [])
        self.project(Graph(), self.api.ServingScope("A" + "x" * 127, "v_1.2-3"))

    def test_reader_normalization_and_additive_metadata(self):
        graph = Graph()

        def change(event):
            event["payload"] = {
                "voltage_v": 1.0,
                "current_a": -0.0,
                "remaining_fraction": 1.0,
                "future": "ignored",
            }
            event["quality_flags"] = ["synthetic_time_anchor", "source_value_missing"]
            event["future"] = "ignored"
            event["source_time"]["future"] = "ignored"
            event["source_time"]["mapping"]["future"] = "ignored"
            event["provenance"]["future"] = "ignored"

        edit_event(graph, 0, change)
        # Two wire spellings of the same admitted numbers under the same event ID.
        duplicate = json.loads(base64.b64decode(graph.observations[6]["value_b64"]))
        duplicate["payload"].update(voltage_v=1, current_a=0, remaining_fraction=1)
        # The reader admits this lexical decimal as float 1.0.
        wire = canonical(duplicate).replace(
            b'"voltage_v":1,', b'"voltage_v":1.00000000000000001,'
        )
        graph.observations[6]["value_b64"] = b64(wire)
        graph.seal()
        row = next(row for row in self.project(graph).rows if row.event_id == IDS[0])
        expected = expected_semantic(0)
        expected["payload"] = {"voltage_v": 1, "current_a": 0, "remaining_fraction": 1}
        expected["quality_flags"] = ["source_value_missing", "synthetic_time_anchor"]
        self.assertEqual(row.semantic_json, semantic_json(expected))
        self.assertEqual(
            (row.voltage_v, row.current_a, row.remaining_fraction),
            ("1.000000", "0.000000", "1.000000"),
        )
        self.assertEqual(
            row.quality_flags, ("source_value_missing", "synthetic_time_anchor")
        )
        # Reader admission turns absent recognized optional fields into null.
        edit_event(graph, 0, lambda event: event.update(payload={"voltage_v": 1}))
        expected["payload"] = {
            "voltage_v": 1,
            "current_a": None,
            "remaining_fraction": None,
        }
        row = next(row for row in self.project(graph).rows if row.event_id == IDS[0])
        self.assertEqual(row.semantic_json, semantic_json(expected))
        self.assertEqual((row.current_a, row.remaining_fraction), (None, None))

    def test_exact_precision_range_and_context_independence(self):
        for field in ("voltage_v", "current_a", "remaining_fraction"):
            for value in (1e-7, 0.1234567):
                with self.subTest(field=field, value=value):
                    graph = Graph()
                    edit_event(
                        graph, 0, lambda event: event["payload"].update({field: value})
                    )
                    self.refusal(graph, "precision_loss", field)
        for field in ("voltage_v", "current_a"):
            graph = Graph()
            edit_event(
                graph, 0, lambda event: event["payload"].update({field: 1000000000000})
            )
            self.refusal(graph, "decimal_overflow", field)
        graph = Graph()
        edit_event(
            graph,
            0,
            lambda event: event["payload"].update(
                voltage_v=123456789.123456,
                current_a=-0.000001,
                remaining_fraction=0.123456,
            ),
        )
        with localcontext() as context:
            context.prec = 3
            row = next(
                row for row in self.project(graph).rows if row.event_id == IDS[0]
            )
        self.assertEqual(
            (row.voltage_v, row.current_a, row.remaining_fraction),
            ("123456789.123456", "-0.000001", "0.123456"),
        )
        expected = expected_semantic(0)
        expected["payload"] = {
            "voltage_v": 123456789.123456,
            "current_a": -0.000001,
            "remaining_fraction": 0.123456,
        }
        # Plain notation is required even for the admitted float rendered as 1e-6.
        wanted = semantic_json(expected).replace("-1e-06", "-0.000001")
        self.assertEqual(row.semantic_json, wanted)

    def test_duplicate_and_rebatch_order_determinism(self):
        graph = Graph()
        first = self.project(graph)
        graph.seal([graph.observations[4:], graph.observations[:5]])
        second = self.project(graph)
        self.assertNotEqual(
            first.archive_descriptor_sha256, second.archive_descriptor_sha256
        )
        self.assertEqual(tuple(row.event_id for row in second.rows), tuple(sorted(IDS)))
        self.assertEqual(len(second.rows), 3)
        from dataclasses import replace

        self.assertEqual(
            tuple(
                replace(row, archive_descriptor_sha256=second.archive_descriptor_sha256)
                for row in first.rows
            ),
            second.rows,
        )
        self.assertEqual(self.project(graph), second)

    def test_fresh_graph_failures_propagate(self):
        for failure in ("corrupt", "missing", "untrusted", "hidden_link"):
            with self.subTest(failure=failure):
                graph = Graph()
                self.project(
                    graph
                )  # Warm the same descriptor/store; no cached success allowed.
                trusted = digest(graph.descriptor_bytes)
                key = graph.lineage[0]["object"]["key"]
                if failure == "corrupt":
                    graph.store.objects[key] += b"!"
                elif failure == "missing":
                    del graph.store.objects[key]
                elif failure == "untrusted":
                    trusted = "sha256:" + "0" * 64
                else:
                    graph.observations[0]["measurement"] = None
                    graph.seal()
                    trusted = digest(graph.descriptor_bytes)
                with self.assertRaises(Exception) as verifier_error:
                    self.verify(graph.descriptor_bytes, trusted, graph.store)
                self.assertEqual(
                    type(verifier_error.exception).__name__, "ArchiveError"
                )
                with self.assertRaises(
                    type(verifier_error.exception)
                ) as projection_error:
                    self.api.project_archive(
                        graph.descriptor_bytes, trusted, graph.store, self.scope()
                    )
                self.assertEqual(
                    (
                        projection_error.exception.category,
                        projection_error.exception.field,
                    ),
                    (verifier_error.exception.category, verifier_error.exception.field),
                )

    def test_late_projection_failure_returns_no_batch(self):
        graph = Graph()
        # First unique event (also lexically first) succeeds before a later refusal.
        self.assertEqual(self.project(graph).rows[0].event_id, IDS[0])
        edit_event(graph, 1, lambda event: event["payload"].update(current_a=1e-7))
        verified = self.verify(
            graph.descriptor_bytes, digest(graph.descriptor_bytes), graph.store
        )
        self.assertEqual(len(verified.measurements), 3)
        result = "not returned"
        with self.assertRaises(self.api.ServingError) as caught:
            result = self.project(graph)
        self.assertEqual(result, "not returned")
        self.assertEqual(
            (caught.exception.category, caught.exception.field),
            ("precision_loss", "current_a"),
        )


if __name__ == "__main__":
    unittest.main()
