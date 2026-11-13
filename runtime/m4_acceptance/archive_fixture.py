# ruff: noqa: B017
# Preserve the independently frozen broad failure assertions at injected ports.
"""Independent public-format oracle and deterministic ports; no candidate codecs."""

import base64
import copy
import hashlib
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
SOURCE = {
    "cluster_id": "test-cluster",
    "topic_id": "test-topic-uuid",
    "topic": "battery",
    "partition": 0,
}
NOW = "2026-10-23T00:00:00.000000Z"
WRITER = "sha256:" + "1" * 64


def digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def canonical(value):
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def b64(body):
    return None if body is None else base64.b64encode(body).decode("ascii")


class Fault(RuntimeError):
    pass


class Store:
    """Deliberately does not certify checksums for the reader."""

    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.calls = []
        self.fail = None
        self.extra_inventory = []

    def hit(self, operation, key):
        self.calls.append((operation, key))
        if self.fail and self.fail(operation, key):
            raise Fault(operation)

    def read(self, key, sha256, byte_length):
        self.hit("read", key)
        return self.objects[key]

    def create(self, key, body):
        self.hit("create", key)
        if key in self.objects and self.objects[key] != body:
            raise Fault("immutable conflict")
        self.objects[key] = body
        return "created"

    def lookup(self, key):
        self.hit("lookup", key)
        return self.objects.get(key)

    def inventory(self):
        self.hit("inventory", "")
        return [
            (key, len(body)) for key, body in self.objects.items()
        ] + self.extra_inventory


class Graph:
    def __init__(self):
        self.store = Store()
        self.job_bytes = (FIXTURES / "synthetic-conversion-job.json").read_bytes()
        self.source_bytes = (FIXTURES / "synthetic-battery-v1.json").read_bytes()
        self.job = json.loads(self.job_bytes)
        self.golden = json.loads((FIXTURES / "expected-battery-v1.json").read_bytes())
        assert digest(self.source_bytes) == self.golden["source_log_id"]
        assert len(self.source_bytes) == self.job["input"]["size_bytes"]
        self.lineage = []
        for role, body in [
            ("original_source", self.source_bytes),
            ("source_manifest", self.job_bytes),
        ]:
            self.lineage.append(
                {
                    "role": role,
                    "object": self.put("sources", body),
                    "source_log_id": self.golden["source_log_id"],
                    "schema_version": "1.0.0",
                    "normalization_version": "battery-v1",
                    "source_dataset_run_id": self.job["delivery"]["dataset_run_id"],
                    "privacy_classification": "synthetic",
                    "semantic_projection": "battery-semantic-v1",
                }
            )
        self.lineage.sort(key=lambda entry: (entry["role"], entry["object"]["key"]))
        self.events = [self.event(expected) for expected in self.golden["accepted"]]
        values = [
            canonical(self.events[0]),
            b"\x00\xff",
            None,
            b"",
            canonical(self.events[1]),
            canonical(self.events[2]),
            canonical(self.events[0]),
        ]
        self.observations = []
        for index, value in enumerate(values):
            event = {
                0: self.events[0],
                4: self.events[1],
                5: self.events[2],
                6: self.events[0],
            }.get(index)
            self.observations.append(
                {
                    "format_version": "kafka-observation-v1",
                    **SOURCE,
                    "offset": 40 + index,
                    "timestamp_ms": None if index == 2 else 1234 + index,
                    "timestamp_type": "not_available" if index == 2 else "create_time",
                    "key_b64": None if index % 2 == 0 else "",
                    "value_b64": b64(value),
                    "headers": [
                        {"name_utf8": "trace", "value_b64": None},
                        {"name_utf8": "trace", "value_b64": ""},
                        {"name_utf8": "binary", "value_b64": "AP8="},
                    ],
                    "measurement": None
                    if event is None
                    else {
                        "event_id": event["event_id"],
                        "source_manifest_sha256": digest(self.job_bytes),
                    },
                }
            )
        self.seal()

    def event(self, expected):
        manifest = self.job["manifest"]
        return {
            "event_id": expected["event_id"],
            "vehicle_id": manifest["vehicle_id"],
            "event_type": "telemetry.battery",
            "schema_version": "1.0.0",
            "source_timestamp": expected["source_timestamp"],
            "ingest_timestamp": self.job["delivery"]["ingest_timestamp"],
            "source_log_id": self.golden["source_log_id"],
            "source_type": "synthetic",
            "source_stream": manifest["source_stream"],
            "source_record_index": expected["source_record_index"],
            "normalization_version": "battery-v1",
            "source_time": {
                "clock_basis": "boot_relative",
                "native_timestamp_us": expected["native_timestamp_us"],
                "timestamp_kind": "measurement",
                "mapping": {
                    **manifest["clock_anchor"],
                    "anchor_kind": "synthetic_fixed",
                },
            },
            "provenance": {
                "source_manifest_id": manifest["source_manifest_id"],
                "privacy_classification": "synthetic",
            },
            "quality_flags": expected["quality_flags"],
            "payload": expected["payload"],
            "delivery": {
                "dataset_run_id": self.job["delivery"]["dataset_run_id"],
                "replay_mode": "synthetic",
            },
        }

    def put(self, folder, body):
        suffix = {
            "sources": "bin",
            "batches": "jsonl",
            "manifests": "json",
            "receipts": "json",
        }[folder]
        key = f"{folder}/{digest(body)[7:]}.{suffix}"
        self.store.objects[key] = body
        return {
            "key": key,
            "sha256": digest(body),
            "byte_length": len(body),
            "version_id": None,
        }

    def batch(self, observations):
        manifest = {
            "format_version": "archive-batch-manifest-v1",
            "archive_run_id": "test-run",
            "source": SOURCE.copy(),
            "start_offset": observations[0]["offset"],
            "next_offset": observations[-1]["offset"] + 1,
            "record_count": len(observations),
            "observations": self.put("batches", b"".join(map(canonical, observations))),
            "lineage": copy.deepcopy(self.lineage),
        }
        ref = self.put("manifests", canonical(manifest))
        receipt = {
            "format_version": "archive-readback-v1",
            "archive_run_id": "test-run",
            "writer_version": WRITER,
            "manifest": ref,
            "verified_at": NOW,
            "readback_method": "full_get_sha256",
        }
        return {"manifest": ref, "receipt": self.put("receipts", canonical(receipt))}

    def seal(self, groups=None):
        self.catalog = {
            "format_version": "archive-catalog-v1",
            "archive_run_id": "test-run",
            "source": SOURCE.copy(),
            "start_offset": 40,
            "next_offset": 47,
            "lineage": copy.deepcopy(self.lineage),
            "batches": sorted(
                [self.batch(group) for group in (groups or [self.observations])],
                key=lambda item: item["manifest"]["key"],
            ),
        }
        self.root()

    def root(self):
        body = canonical(self.catalog)
        self.store.objects["catalog.json"] = body
        self.descriptor = {
            "format_version": "archive-recovery-descriptor-v1",
            "archive_run_id": "test-run",
            "bucket": "test-archive",
            "prefix": "archive-v1/test-run/",
            "catalog": {
                "key": "catalog.json",
                "sha256": digest(body),
                "byte_length": len(body),
                "version_id": None,
            },
            "source": SOURCE.copy(),
            "start_offset": 40,
            "next_offset": 47,
        }
        self.descriptor_bytes = canonical(self.descriptor)

    def archive_job(self):
        return {
            "archive_run_id": "test-run",
            "bucket": "test-archive",
            "source": SOURCE.copy(),
            "start_offset": 40,
            "next_offset": 47,
            "lineage": copy.deepcopy(self.lineage),
            "writer_version": WRITER,
            "verified_at": NOW,
            "batch_size": 3,
        }

    def blobs(self):
        return {
            entry["object"]["key"]: self.store.objects[entry["object"]["key"]]
            for entry in self.lineage
        }


def assert_archive_error(case, operation, category=None):
    with case.assertRaises(Exception) as caught:
        operation()
    case.assertEqual(type(caught.exception).__name__, "ArchiveError")
    if category is not None:
        case.assertEqual(caught.exception.category, category)
