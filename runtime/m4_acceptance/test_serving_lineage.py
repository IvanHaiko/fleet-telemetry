"""Parent regression: original source JSON must not be mistaken for a job."""

import copy
import hashlib
import json
import unittest

from archive_fixture import Graph, b64, canonical, digest

from telemetry.archive_graph import verify_catalog
from telemetry.serving_projection import ServingScope, project_archive


class SourceRoleRegression(unittest.TestCase):
    def test_job_shaped_source_uses_catalog_role(self):
        graph = Graph()
        indexes = {event["event_id"]: i for i, event in enumerate(graph.events)}
        native = json.loads(graph.source_bytes)
        native.update(
            job_version="native-extension-decoy",
            mode="not-a-job",
            input={},
            manifest={},
            delivery={},
        )
        graph.source_bytes = canonical(native)
        source_id = digest(graph.source_bytes)
        graph.job["input"].update(
            source_log_id=source_id, size_bytes=len(graph.source_bytes)
        )
        graph.job["manifest"]["source_log_id"] = source_id
        graph.job_bytes = canonical(graph.job)
        graph.golden["source_log_id"] = source_id
        for event in graph.golden["accepted"]:
            identity = [
                "event-id-v1",
                "synthetic",
                source_id,
                "demo-vehicle-001",
                "battery_status:0",
                event["source_record_index"],
                "telemetry.battery",
                "battery-v1",
            ]
            event["event_id"] = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(identity, separators=(",", ":")).encode()
                ).hexdigest()
            )
        graph.events = [graph.event(event) for event in graph.golden["accepted"]]
        for entry in graph.lineage:
            entry["source_log_id"] = source_id
            body = (
                graph.source_bytes
                if entry["role"] == "original_source"
                else graph.job_bytes
            )
            entry["object"] = graph.put("sources", body)
        for row in graph.observations:
            if row["measurement"] is not None:
                event = graph.events[indexes[row["measurement"]["event_id"]]]
                row["value_b64"] = b64(canonical(event))
                row["measurement"] = {
                    "event_id": event["event_id"],
                    "source_manifest_sha256": digest(graph.job_bytes),
                }
        graph.seal()
        trusted = digest(graph.descriptor_bytes)
        self.assertEqual(
            len(
                verify_catalog(
                    graph.descriptor_bytes, trusted, graph.store
                ).measurements
            ),
            3,
        )
        original = copy.deepcopy(graph.store.objects)
        batch = project_archive(
            graph.descriptor_bytes,
            trusted,
            graph.store,
            ServingScope("role-regression", "projection-v1"),
        )
        self.assertEqual(len(batch.rows), 3)
        self.assertTrue(
            all(row.source_job_sha256 == digest(graph.job_bytes) for row in batch.rows)
        )
        self.assertEqual(graph.store.objects, original)


if __name__ == "__main__":
    unittest.main()
