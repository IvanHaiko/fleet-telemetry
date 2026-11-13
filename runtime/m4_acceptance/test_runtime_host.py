# ruff: noqa: I001, B017, B023, E731
# Preserve frozen imports/assertions and synchronous callback helpers.
"""Retained-root checks using only public descriptors and host operations."""

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.m4_acceptance.archive_fixture import Graph


@unittest.skipUnless(sys.platform == "linux", "native publication requires Linux")
class RetainedRootTests(unittest.TestCase):
    def setUp(self):
        from runtime.archive_runtime.retention import RetainedRoot

        self.factory = RetainedRoot
        scratch = Path(os.environ["ARCHIVE_TEST_SCRATCH"]).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.body = Graph().descriptor_bytes
        self.sha = "sha256:" + hashlib.sha256(self.body).hexdigest()

    def refuses(self, call):
        with self.assertRaises(Exception) as caught:
            call()
        self.assertEqual(type(caught.exception).__name__, "ArchiveError")

    def contents(self, root):
        return {p.name: p.read_bytes() for p in root.iterdir()}

    def test_exact_durable_publication_retry_and_fresh_read(self):
        retained = self.factory(self.parent, "test-run")
        # Observe actual fsyncs while preserving the native syscall behavior.
        synced = []
        native_fsync = os.fsync

        def fsync(fd):
            synced.append(os.fstat(fd).st_mode)
            return native_fsync(fd)

        with patch("os.fsync", side_effect=fsync):
            retained.retain(self.body, self.sha)
        import stat

        self.assertGreaterEqual(sum(stat.S_ISREG(mode) for mode in synced), 2)
        self.assertGreaterEqual(sum(stat.S_ISDIR(mode) for mode in synced), 1)
        root = self.parent / "test-run"
        expected = {
            "descriptor.json": self.body,
            "descriptor.sha256": (self.sha + "\n").encode("ascii"),
        }
        self.assertEqual(self.contents(root), expected)
        identities = {p.name: p.stat().st_ino for p in root.iterdir()}
        retained.retain(self.body, self.sha)
        self.assertEqual(self.contents(root), expected)
        self.assertEqual({p.name: p.stat().st_ino for p in root.iterdir()}, identities)
        self.assertEqual(self.factory(self.parent, "test-run").read(), self.body)
        (root / "descriptor.json").write_bytes(self.body + b" ")
        self.refuses(retained.read)

    def test_conflicting_incomplete_extra_and_linked_roots_unchanged(self):
        for mode in ("conflict", "incomplete", "extra", "linked-file", "linked-root"):
            with self.subTest(mode=mode):
                parent = self.parent / mode
                parent.mkdir()
                root = parent / "test-run"
                root.mkdir()
                (root / "descriptor.json").write_bytes(self.body)
                (root / "descriptor.sha256").write_text(self.sha + "\n")
                if mode == "conflict":
                    (root / "descriptor.json").write_bytes(b"conflicting original")
                elif mode == "incomplete":
                    (root / "descriptor.sha256").unlink()
                elif mode == "extra":
                    (root / "extra").write_bytes(b"keep")
                elif mode == "linked-file":
                    target = parent / "outside"
                    target.write_bytes(self.body)
                    (root / "descriptor.json").unlink()
                    (root / "descriptor.json").symlink_to(target)
                else:
                    moved = parent / "original"
                    root.rename(moved)
                    root.symlink_to(moved, target_is_directory=True)
                before = self.contents(root)
                links = {p.name: p.is_symlink() for p in root.iterdir()}
                self.refuses(
                    lambda: self.factory(parent, "test-run").retain(self.body, self.sha)
                )
                self.assertEqual(self.contents(root), before)
                self.assertEqual(
                    {p.name: p.is_symlink() for p in root.iterdir()}, links
                )
                self.assertEqual(root.is_symlink(), mode == "linked-root")

    def test_parent_run_path_descriptor_and_hash_admission(self):
        missing = self.parent / "missing"
        plain = self.parent / "file"
        plain.write_bytes(b"keep")
        alias = self.parent / "alias"
        alias.symlink_to(self.parent, target_is_directory=True)
        for parent, run in [
            (missing, "test-run"),
            (plain, "test-run"),
            (alias, "test-run"),
            (self.parent, "../escape"),
            (self.parent, "/absolute"),
            (self.parent, "UPPER"),
            (self.parent, ""),
        ]:
            with self.subTest(parent=parent, run=run):
                self.refuses(lambda: self.factory(parent, run))
        retained = self.factory(self.parent, "test-run")
        for body, sha in [
            (self.body, "sha256:" + "0" * 64),
            (self.body, self.sha.upper()),
            (self.body + b" ", self.sha),
            (b"{}\n", "sha256:" + hashlib.sha256(b"{}\n").hexdigest()),
        ]:
            self.refuses(lambda: retained.retain(body, sha))
            self.assertFalse((self.parent / "test-run").exists())
        other = self.factory(self.parent, "other-run")
        self.refuses(lambda: other.retain(self.body, self.sha))
        self.assertFalse((self.parent / "other-run").exists())
