# ruff: noqa: B017
# Preserve the independently frozen broad failure assertions at injected ports.
"""Archive-only reconstruction with exact independently authored byte oracles."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from archive_fixture import Graph, canonical, digest

from telemetry.archive_rebuild import rebuild_archive


class RebuildTests(unittest.TestCase):
    def setUp(self):
        self.graph = Graph()
        self.temporary = tempfile.TemporaryDirectory(dir="scratch")
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.destination = self.parent / "rebuilt"

    def rebuild(self):
        graph = self.graph
        return rebuild_archive(
            graph.descriptor_bytes,
            digest(graph.descriptor_bytes),
            graph.store,
            self.destination,
        )

    def test_exact_observations_unique_measurements_blobs_and_originals(self):
        graph = self.graph
        objects = graph.store.objects.copy()
        originals = {
            path: path.read_bytes()
            for path in (Path("tests/fixtures")).iterdir()
            if path.is_file()
        }
        result = self.rebuild()
        self.assertEqual(
            (self.destination / "observations.jsonl").read_bytes(),
            b"".join(map(canonical, graph.observations)),
        )
        measurements = [
            json.loads(line)
            for line in (self.destination / "measurements.jsonl")
            .read_bytes()
            .splitlines()
        ]
        self.assertEqual(measurements, graph.events)
        self.assertEqual(len({event["event_id"] for event in measurements}), 3)
        self.assertEqual(list(result.measurements), graph.events)
        for key, body in graph.blobs().items():
            self.assertEqual((self.destination / key).read_bytes(), body)
        self.assertEqual(
            (self.destination / "descriptor.json").read_bytes(), graph.descriptor_bytes
        )
        # Completion field names are intentionally not specified by this contract.
        self.assertIsInstance(
            json.loads((self.destination / "complete.json").read_bytes()), dict
        )
        self.assertEqual(graph.store.objects, objects)
        for path, body in originals.items():
            self.assertEqual(path.read_bytes(), body)

    def test_any_missing_or_corrupt_object_prevents_complete_output(self):
        graph = self.graph
        for index, (key, body) in enumerate(list(graph.store.objects.items())):
            for fault in ("missing", "corrupt"):
                with self.subTest(key=key, fault=fault):
                    self.destination = self.parent / f"failure-{index}-{fault}"
                    if fault == "missing":
                        del graph.store.objects[key]
                    else:
                        graph.store.objects[key] = body + b"x"
                    with self.assertRaises(Exception):
                        self.rebuild()
                    self.assertFalse((self.destination / "complete.json").exists())
                    graph.store.objects[key] = body

    def test_untrusted_root_hole_and_conflict_have_no_marker(self):
        graph = self.graph
        with self.assertRaises(Exception):
            rebuild_archive(
                graph.descriptor_bytes,
                "sha256:" + "0" * 64,
                graph.store,
                self.destination,
            )
        self.assertFalse((self.destination / "complete.json").exists())
        graph.seal([graph.observations[:2], graph.observations[3:]])
        with self.assertRaises(Exception):
            self.rebuild()
        self.assertFalse((self.destination / "complete.json").exists())

    def test_existing_target_and_symlinks_refused_without_replacement(self):
        self.destination.mkdir()
        sentinel = self.destination / "original"
        sentinel.write_bytes(b"preserve me")
        with self.assertRaises(Exception):
            self.rebuild()
        self.assertEqual(sentinel.read_bytes(), b"preserve me")
        self.assertFalse((self.destination / "complete.json").exists())
        real = self.parent / "real"
        real.mkdir()
        link = self.parent / "link"
        try:
            link.symlink_to(real.resolve(), target_is_directory=True)
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                self.skipTest(
                    "Windows symlink fixture requires an unavailable privilege"
                )
            raise
        for target in (link, link / "new"):
            self.destination = target
            with self.assertRaises(Exception):
                self.rebuild()
            self.assertFalse((target / "complete.json").exists())
        self.assertEqual(list(real.iterdir()), [])

    def test_fsync_failure_never_publishes_completion(self):
        with patch("os.fsync", side_effect=OSError("injected disk failure")):
            with self.assertRaises(Exception):
                self.rebuild()
        self.assertFalse((self.destination / "complete.json").exists())
