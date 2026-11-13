"""Read-only graph acceptance through the documented verifier."""

import copy
import json
import unittest

from archive_fixture import Graph, assert_archive_error, b64, canonical, digest

from telemetry.archive_graph import verify_catalog


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = Graph()

    def verify(self):
        graph = self.graph
        return verify_catalog(
            graph.descriptor_bytes, digest(graph.descriptor_bytes), graph.store
        )

    def reject(self, category=None):
        assert_archive_error(self, self.verify, category)

    def test_exact_graph_repeated_event_and_owned_outputs(self):
        graph = self.graph
        result = self.verify()
        self.assertEqual(result.descriptor, graph.descriptor)
        self.assertEqual(result.blobs, graph.blobs())
        self.assertIsInstance(result.measurements, tuple)
        self.assertEqual(list(result.measurements), graph.events)
        result.descriptor["source"]["topic"] = "changed"
        self.assertEqual(self.verify().descriptor, graph.descriptor)
        for key in graph.blobs():
            self.assertIn(("read", key), graph.store.calls)

    def test_independent_root_trust(self):
        assert_archive_error(
            self,
            lambda: verify_catalog(
                self.graph.descriptor_bytes, "sha256:" + "0" * 64, self.graph.store
            ),
            "untrusted_catalog",
        )
        self.assertEqual(self.graph.store.calls, [])

    def test_missing_and_corrupt_every_object_and_no_cache(self):
        graph = self.graph
        self.verify()
        for key, original in list(graph.store.objects.items()):
            with self.subTest(key=key, fault="corrupt"):
                graph.store.objects[key] = bytes([original[0] ^ 1]) + original[1:]
                self.reject("checksum_mismatch")
            graph.store.objects[key] = original
            with self.subTest(key=key, fault="missing"):
                del graph.store.objects[key]
                self.reject("object_missing")
            graph.store.objects[key] = original
        self.verify()

    def test_hole_and_identical_or_conflicting_overlap(self):
        graph = self.graph
        graph.seal([graph.observations[:4], graph.observations[3:]])
        self.assertEqual(list(self.verify().measurements), graph.events)
        graph.seal([graph.observations[:3], graph.observations[4:]])
        self.reject("coverage_gap")
        for field in ("headers", "timestamp_ms"):
            other = copy.deepcopy(graph.observations[3:])
            if field == "headers":
                other[0][field].reverse()
            else:
                other[0][field] += 1
            graph.seal([graph.observations[:4], other])
            self.reject("observation_conflict")

    def test_event_lineage_and_hidden_admissible_link(self):
        for change in (
            "hidden",
            "id",
            "job",
            "delivery",
            "vehicle",
            "time",
            "semantic",
        ):
            with self.subTest(change=change):
                self.graph = Graph()
                graph = self.graph
                observation = graph.observations[6]
                if change == "hidden":
                    observation["measurement"] = None
                elif change == "id":
                    observation["measurement"]["event_id"] = graph.events[1]["event_id"]
                elif change == "job":
                    observation["measurement"]["source_manifest_sha256"] = (
                        "sha256:" + "0" * 64
                    )
                else:
                    event = copy.deepcopy(graph.events[0])
                    if change == "delivery":
                        event["delivery"]["dataset_run_id"] = "different-run"
                    elif change == "vehicle":
                        event["vehicle_id"] = "other-vehicle"
                    elif change == "time":
                        event["source_time"]["mapping"]["native_anchor_us"] = 1
                    else:
                        event["payload"]["voltage_v"] = 99
                    observation["value_b64"] = b64(canonical(event))
                graph.seal()
                self.reject()

    def test_control_schema_canonical_paths_and_limits(self):
        for mutate in (
            lambda c: c.update(extra=True),
            lambda c: c.update(format_version="future"),
            lambda c: c.update(next_offset=73),
            lambda c: c.update(start_offset=True),
            lambda c: c.update(batches=c["batches"] * 17),
            lambda c: c["lineage"][0]["object"].update(key="../escape"),
            lambda c: c["lineage"][0]["object"].update(key="/absolute"),
            lambda c: c["lineage"][0]["object"].update(version_id="v1"),
            lambda c: c["lineage"][0]["object"].update(
                byte_length=16 * 1024 * 1024 + 1
            ),
        ):
            self.graph = Graph()
            mutate(self.graph.catalog)
            self.graph.root()
            self.reject()
        graph = Graph()
        self.graph = graph
        for body in (
            json.dumps(graph.catalog, indent=2).encode(),
            canonical(graph.catalog).replace(
                b'"format_version":',
                b'"format_version":"archive-catalog-v1","format_version":',
                1,
            ),
        ):
            graph.store.objects["catalog.json"] = body
            graph.descriptor["catalog"].update(
                sha256=digest(body), byte_length=len(body)
            )
            graph.descriptor_bytes = canonical(graph.descriptor)
            self.reject("invalid_format")

    def test_receipt_crosslink_and_calendar(self):
        for fault in ("crosslink", "calendar"):
            self.graph = Graph()
            graph = self.graph
            graph.seal([graph.observations[:3], graph.observations[3:]])
            entries = graph.catalog["batches"]
            receipt = json.loads(graph.store.objects[entries[0]["receipt"]["key"]])
            if fault == "crosslink":
                receipt["manifest"] = entries[1]["manifest"]
            else:
                receipt["verified_at"] = "2026-02-30T00:00:00.000000Z"
            entries[0]["receipt"] = graph.put("receipts", canonical(receipt))
            graph.root()
            self.reject()

    def test_unused_pair_is_read_and_reconciled(self):
        graph = self.graph
        job = copy.deepcopy(graph.job)
        source = b"unused synthetic source"
        job["input"].update(source_log_id=digest(source), size_bytes=len(source))
        job["manifest"].update(
            source_log_id=digest(source), source_manifest_id="unused-manifest"
        )
        job["delivery"]["dataset_run_id"] = "unused-run"
        for role, body in (
            ("original_source", source),
            ("source_manifest", json.dumps(job, indent=2).encode()),
        ):
            entry = copy.deepcopy(next(e for e in graph.lineage if e["role"] == role))
            entry.update(
                object=graph.put("sources", body),
                source_log_id=digest(source),
                source_dataset_run_id="unused-run",
            )
            graph.lineage.append(entry)
        graph.lineage.sort(key=lambda e: (e["role"], e["object"]["key"]))
        graph.seal()
        self.assertEqual(self.verify().blobs, graph.blobs())
        key = next(
            e["object"]["key"]
            for e in graph.lineage
            if e["role"] == "original_source"
            and e["source_dataset_run_id"] == "unused-run"
        )
        self.assertIn(("read", key), graph.store.calls)
        graph.store.objects[key] = b"corrupt"
        self.reject("checksum_mismatch")

    def test_observation_encoding_and_header_limits(self):
        for mutate in (
            lambda o: o.update(value_b64="AP9="),
            lambda o: o.update(headers=o["headers"] * 11),
            lambda o: o["headers"][0].update(name_utf8="x" * 257),
            lambda o: o.update(partition=True),
            lambda o: o.update(timestamp_type="not_available"),
            lambda o: o.update(value_b64="x" * (256 * 1024)),
        ):
            self.graph = Graph()
            mutate(self.graph.observations[1])
            self.graph.seal()
            self.reject()

    def test_conflicting_references_and_manifest_lineage(self):
        graph = self.graph
        graph.seal([graph.observations[:3], graph.observations[3:]])
        entry = graph.catalog["batches"][0]
        manifest = json.loads(graph.store.objects[entry["manifest"]["key"]])
        manifest["lineage"][0]["source_dataset_run_id"] = "other-run"
        entry["manifest"] = graph.put("manifests", canonical(manifest))
        receipt = json.loads(graph.store.objects[entry["receipt"]["key"]])
        receipt["manifest"] = entry["manifest"]
        entry["receipt"] = graph.put("receipts", canonical(receipt))
        graph.catalog["batches"].sort(key=lambda e: e["manifest"]["key"])
        graph.root()
        self.reject("lineage_mismatch")
        self.graph = Graph()
        graph = self.graph
        extra = copy.deepcopy(graph.catalog["lineage"][0])
        extra["object"]["byte_length"] += 1
        graph.catalog["lineage"].append(extra)
        graph.root()
        self.reject()
