# ruff: noqa: I001, E501, B023
# Preserve frozen imports, literal expectations and synchronous callbacks.
"""Frozen independent sink checks; candidate imports occur only at execution."""

import copy
import importlib
import json
from pathlib import Path
import sys
import unittest


def encode(rows):
    return b"".join(
        (
            json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        for row in rows
    )


class Writer:
    def __init__(self, calls: list, error: Exception | None = None):
        self.calls = calls
        self.error = error
        self.bodies: list[bytes] = []

    def write(self, body: bytes) -> None:
        self.calls.append("write")
        self.bodies.append(body)
        if self.error is not None:
            raise self.error


class Reader:
    def __init__(self, calls: list, body: bytes):
        self.calls = calls
        self.body = body
        self.error: Exception | None = None
        self.read_error: Exception | None = None

    def check_schema(self) -> None:
        self.calls.append("schema")
        if self.error is not None:
            raise self.error

    def read(self, scope: object) -> bytes:
        self.calls.append(("read", scope))
        if self.read_error is not None:
            raise self.read_error
        return self.body


class SinkTests(unittest.TestCase):
    def setUp(self):
        self.sink = importlib.import_module("telemetry.serving_sink")
        projection = importlib.import_module("telemetry.serving_projection")
        roots = [Path.cwd()]
        root = getattr(projection, "ROOT", None)
        if root is not None:
            roots.append(Path(root))
        roots.extend(Path(projection.__file__).resolve().parents)
        fixture_dir = next(
            root / "runtime" / "m4_acceptance"
            for root in roots
            if (root / "runtime" / "m4_acceptance" / "archive_fixture.py").is_file()
        )
        sys.path.insert(0, str(fixture_dir))
        fixture = importlib.import_module("archive_fixture")
        self.fixture = fixture
        self.graph = fixture.Graph()
        self.sha = fixture.digest(self.graph.descriptor_bytes)
        self.scope = projection.ServingScope("sink-target", "pipeline-v1")
        self.rows = []
        numbers = [
            ("15.800000", "4.200000", "0.720000"),
            ("16.000000", "-1.250000", None),
            ("0.000000", None, None),
        ]
        # Fixture numbers have independently known canonical spellings. The
        # integer-valued floats below normalize to integers in semantic JSON.
        for golden, event, values in zip(
            self.graph.golden["accepted"], self.graph.events, numbers, strict=True
        ):
            semantic = {
                key: copy.deepcopy(event[key])
                for key in (
                    "vehicle_id",
                    "event_type",
                    "source_timestamp",
                    "source_log_id",
                    "source_type",
                    "source_stream",
                    "source_record_index",
                    "normalization_version",
                    "source_time",
                    "payload",
                    "quality_flags",
                )
            }
            semantic["quality_flags"] = sorted(semantic["quality_flags"])
            for key, value in semantic["payload"].items():
                if isinstance(value, float) and value.is_integer():
                    semantic["payload"][key] = int(value)
            self.rows.append(
                {
                    "projection_version": "serving-battery-exact6-v1",
                    "dataset_run_id": "sink-target",
                    "pipeline_version": "pipeline-v1",
                    "event_id": golden["event_id"],
                    "vehicle_id": self.graph.job["manifest"]["vehicle_id"],
                    "source_timestamp": golden["source_timestamp"],
                    "voltage_v": values[0],
                    "current_a": values[1],
                    "remaining_fraction": values[2],
                    "quality_flags": sorted(golden["quality_flags"]),
                    "semantic_json": json.dumps(
                        semantic,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    "source_dataset_run_id": self.graph.job["delivery"][
                        "dataset_run_id"
                    ],
                    "source_job_sha256": fixture.digest(self.graph.job_bytes),
                    "archive_descriptor_sha256": self.sha,
                }
            )
        self.rows.sort(key=lambda row: row["event_id"])
        self.calls = []
        self.writer = Writer(self.calls)
        self.reader = Reader(self.calls, encode(self.rows))

    def publish(self, batch_size=16):
        return self.sink.publish_archive(
            self.graph.descriptor_bytes,
            self.sha,
            self.graph.store,
            self.scope,
            self.writer,
            self.reader,
            batch_size=batch_size,
        )

    def error(self, category, field, operation):
        with self.assertRaises(self.sink.SinkError) as caught:
            operation()
        self.assertEqual(
            (caught.exception.category, caught.exception.field), (category, field)
        )

    def test_exact_wire_receipt_order_and_changed_batch_retry(self):
        self.assertEqual(self.sink.SCHEMA_VERSION, "serving-events-v1")
        self.assertEqual(self.sink.MAX_BODY_BYTES, 8388608)
        for size, batches in ((2, 2), (1, 3)):
            self.calls.clear()
            self.writer.bodies.clear()
            # Physical duplicate copies may collapse, independent of batch size.
            self.reader.body = encode(self.rows + self.rows)
            receipt = self.publish(size)
            self.assertEqual(
                self.writer.bodies,
                [
                    encode(self.rows[i : i + size])
                    for i in range(0, len(self.rows), size)
                ],
            )
            self.assertEqual(
                self.calls, ["schema"] + ["write"] * batches + [("read", self.scope)]
            )
            self.assertEqual(
                (
                    receipt.schema_version,
                    receipt.scope,
                    receipt.archive_descriptor_sha256,
                    receipt.event_count,
                    receipt.acknowledged_batches,
                ),
                ("serving-events-v1", self.scope, self.sha, 3, batches),
            )

    def test_validation_and_fresh_graph_failure_precede_ports(self):
        for size in (True, False, 0, 65, 1.0, "1", None):
            with self.subTest(size=size):
                self.graph.store.calls.clear()
                self.error(
                    "invalid_batch_size", "batch_size", lambda: self.publish(size)
                )
                self.assertEqual(self.calls, [])
                self.assertEqual(self.graph.store.calls, [])
        self.publish()
        self.calls.clear()
        self.writer.bodies.clear()
        key = self.graph.lineage[0]["object"]["key"]
        self.graph.store.objects[key] = b"corrupt"
        self.fixture.assert_archive_error(self, self.publish)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.writer.bodies, [])

    def test_port_failures_stop_without_retry_or_readback(self):
        for failure, category, field in (
            (TimeoutError(), "write_ambiguous", "write"),
            (OSError(), "write_ambiguous", "write"),
            (PermissionError(), "permission_denied", "sink"),
            (
                self.sink.SinkError("write_ambiguous", "write"),
                "write_ambiguous",
                "write",
            ),
        ):
            self.calls.clear()
            self.writer = Writer(self.calls, failure)
            self.error(category, field, lambda: self.publish(1))
            self.assertEqual(self.calls, ["schema", "write"])
        self.calls.clear()
        self.writer = Writer(self.calls)
        self.reader.body = encode(self.rows + self.rows[:1])
        receipt = self.publish(2)
        self.assertEqual(receipt.acknowledged_batches, 2)
        self.assertEqual(self.calls, ["schema", "write", "write", ("read", self.scope)])
        for failure, category, field in (
            (PermissionError(), "permission_denied", "sink"),
            (OSError(), "sink_unavailable", "read"),
            (
                self.sink.SinkError("schema_mismatch", "schema"),
                "schema_mismatch",
                "schema",
            ),
        ):
            self.calls.clear()
            self.reader.error = failure
            self.error(category, field, self.publish)
            self.assertEqual(self.calls, ["schema"])
        self.reader.error = None
        for failure, category, field in (
            (PermissionError(), "permission_denied", "sink"),
            (TimeoutError(), "sink_unavailable", "read"),
        ):
            self.calls.clear()
            self.reader.read_error = failure
            self.error(category, field, self.publish)
            self.assertEqual(self.calls, ["schema", "write", ("read", self.scope)])
        self.reader.read_error = None
        self.writer.error = RuntimeError("programming defect")
        with self.assertRaises(RuntimeError):
            self.publish()

    def test_full_reconciliation_and_conflicting_copies(self):
        for field in self.rows[0]:
            changed = copy.deepcopy(self.rows)
            value = changed[0][field]
            changed[0][field] = ["different"] if isinstance(value, list) else "wrong"
            with self.subTest(field=field):
                self.reader.body = encode(changed)
                self.error("reconciliation_failed", "rows", self.publish)
        cases = ([], self.rows[:-1], self.rows + [dict(self.rows[0], event_id="extra")])
        for rows in cases:
            self.reader.body = encode(rows)
            self.error("reconciliation_failed", "rows", self.publish)
        for field in ("source_job_sha256", "archive_descriptor_sha256", "voltage_v"):
            conflict = dict(self.rows[0], **{field: "other"})
            self.reader.body = encode(self.rows + [conflict])
            self.error("sink_conflict", "rows", self.publish)

    def test_response_json_types_and_bounds(self):
        row = self.rows[0]
        invalid = [
            b"{",
            b"\xff",
            b"[]\n",
            b"null\n",
            b'{"x":NaN}\n',
            encode([row]) + b"\n" + encode(self.rows[1:]),
            encode([row]).replace(b"{", b'{"event_id":"duplicate",', 1),
            encode([{key: value for key, value in row.items() if key != "vehicle_id"}]),
            encode([dict(row, unknown="x")]),
        ]
        for field in row:
            invalid.append(encode([dict(row, **{field: 1})]))
        invalid.extend(
            [
                encode([dict(row, quality_flags=[None])]),
                encode([dict(row, voltage_v=None)]),
            ]
        )
        for body in invalid:
            with self.subTest(body=body[:60]):
                self.reader.body = body
                self.error("invalid_response", "rows", self.publish)
        for body in (b"x" * 8388609, encode([row] * 65)):
            self.reader.body = body
            self.error("limit_exceeded", "rows", self.publish)

        # A genuinely admitted archive with no measurements still verifies schema
        # and performs readback; empty response means missing data only above.
        for observation in self.graph.observations:
            observation["measurement"] = None
            observation["value_b64"] = None
        self.graph.seal()
        self.sha = self.fixture.digest(self.graph.descriptor_bytes)
        self.calls.clear()
        self.writer.bodies.clear()
        self.reader.body = b""
        receipt = self.publish()
        self.assertEqual((receipt.event_count, receipt.acknowledged_batches), (0, 0))
        self.assertEqual(self.calls, ["schema", ("read", self.scope)])
        self.assertEqual(self.writer.bodies, [])


if __name__ == "__main__":
    unittest.main()
