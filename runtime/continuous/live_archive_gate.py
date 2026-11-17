"""Verify live serving facts against the contiguous, read-back archive prefix."""

import base64
import hashlib
from pathlib import Path

from runtime.continuous.recording_config import Document, immutable, require
from runtime.s3.archive_store import ArchiveStore
from telemetry.archive_documents import canonical, digest
from telemetry.continuous_archive import SegmentedArchive, segment_rows
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    object_value,
    string_value,
)
from telemetry.fleet_runtime import make_runtime, runtime_session
from telemetry.live_event import event_key, read_event

SESSION_KEY = "session.json"


class ArchivedFacts:
    """Recompute facts from the archived prefix; local counters grant nothing."""

    def __init__(self, config: Document, reader: ArchiveStore, root: Path) -> None:
        self.config, self.reader = config, reader
        self.session = runtime_session(object_value(config["session"]))
        body = json_line(self.session)
        require(
            reader.read(SESSION_KEY, digest(body), len(body)) == body,
            "live_session_archive",
        )
        self.plan = object_value(config["archive_plan"])
        path = root / "archive-reader-origin.json"
        origin: Document = {
            "format_version": "continuous-archive-cursor-v1",
            "plan_sha256": digest(canonical(self.plan)),
            "partitions": {"0": {"next": 0, "start": 0, "receipt_sha256": None}},
        }
        immutable(path, canonical(origin))
        self.verifier = SegmentedArchive(reader, reader, path, self.plan)
        self.runtime = make_runtime(
            self.session, max_events=integer_value(config["max_deliveries"])
        )
        self.archived = 0
        self.previous: str | None = None
        # Fact hashes by input offset; repeated outputs compare again.
        self.facts: dict[int, str] = {}
        self.identities: set[str] = set()

    def advance(self) -> None:
        while True:
            checked = self.verifier.verify_receipt(0, self.archived)
            if checked is None:
                return
            receipt, body = checked
            require(receipt["previous_sha256"] == self.previous, "live_archive_chain")
            for row in segment_rows(body):
                value = base64.b64decode(string_value(row["value_b64"]), validate=True)
                key = base64.b64decode(string_value(row["key_b64"]), validate=True)
                event = read_event(value)
                require(
                    key == event_key(event).encode() and row["headers"] == [],
                    "live_archive_input_content",
                )
                fact = self.runtime.accept(event)
                if fact is not None:
                    self.facts[self.archived] = hashlib.sha256(
                        json_line(fact)
                    ).hexdigest()
                    self.identities.add(string_value(fact["measurement_id"]))
                self.archived += 1
            self.previous = digest(canonical(receipt))

    def admit(self, output: Document) -> bool:
        """True once archived and recomputed; refuse any differing content."""
        source = {
            **object_value(object_value(self.config["sources"])["input"]),
            "partition": 0,
        }
        require(
            output["input_source"] == source
            and output["session_sha256"] == self.runtime.session_sha256,
            "live_output_scope",
        )
        offset = integer_value(output["input_offset"])
        if offset >= self.archived:
            return False
        require(
            self.facts.get(offset)
            == hashlib.sha256(json_line(output["fact"])).hexdigest(),
            "live_output_content",
        )
        return True
