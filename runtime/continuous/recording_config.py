"""Bounded F09 publication, independent input archival and archive-gated serving."""

import hashlib
import os
import signal
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig
from runtime.continuous.kafka import Kafka
from runtime.continuous.recording_sql import RecordingSQL
from runtime.flight_analytics.stream_prepare import load_bundle
from runtime.s3.archive_store import ArchiveStore, make_archive_store
from telemetry.conversion_contract import (
    integer_value,
    json_line,
    object_value,
    string_value,
)
from telemetry.local_io import read_bounded
from telemetry.recording_output import MAX_EVENTS
from telemetry.recording_stream import event_bytes

type Document = dict[str, object]
MAX_DELIVERIES = MAX_EVENTS
# Matches the reference/bundle output bound; complete F09 facts are 29.6 MB.
MAX_BODY = 64 * 1024 * 1024
# A 1x native-time replay of the complete F09 flight lasts about 39 minutes.
MAX_LIFETIME_SECONDS = 3600


def require(value: object, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def immutable(path: Path, body: bytes) -> None:
    if path.exists():
        require(read_bounded(path, MAX_BODY) == body, "recording_local_conflict")
        return
    with path.open("xb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())


def load_inputs(config: Document) -> tuple[list[Document], Document, list[bytes]]:
    events, context, manifest = load_bundle(Path(string_value(config["bundle"])))
    require(
        context["run_id"] == config["run_id"]
        and hashlib.sha256(json_line(context)).hexdigest() == config["context_sha256"]
        and hashlib.sha256(json_line(manifest)).hexdigest() == config["bundle_sha256"],
        "recording_bundle_binding",
    )
    raw = config["duplicate_indices"]
    require(isinstance(raw, list) and len(raw) == 2, "recording_duplicate_selection")
    indices = [integer_value(i) for i in cast(list[object], raw)]
    require(all(0 <= i < len(events) for i in indices), "recording_duplicate_selection")
    wires = [event_bytes(event) for event in events]
    wires += [wires[i] for i in indices]
    require(
        len(wires) == integer_value(config["deliveries"])
        and 1 <= len(wires) <= MAX_DELIVERIES,
        "recording_delivery_bound",
    )
    return events, context, wires


def kafka_client(config: Document) -> Kafka:
    source = object_value(object_value(config["sources"])["input"])
    kafka = Kafka(
        string_value(config["bootstrap"]),
        string_value(source["cluster_id"]),
        config["kafka_connection"],
    )
    for expected in object_value(config["sources"]).values():
        selected = object_value(expected)
        require(
            kafka.describe(string_value(selected["topic"])) == selected,
            "recording_topic_identity",
        )
    return kafka


def storage(config: Document, role: str) -> ArchiveStore:
    settings = object_value(config["storage"])
    keys = object_value(settings[role])
    return make_archive_store(
        string_value(settings["endpoint"]),
        "us-east-1",
        string_value(settings["bucket"]),
        string_value(settings["prefix"]),
        string_value(keys["access_key"]),
        string_value(keys["secret_key"]),
    )


def sql_client(config: Document) -> RecordingSQL:
    def connection(role: str) -> HttpConfig:
        row = object_value(config[role])
        return HttpConfig(
            integer_value(row["port"]),
            string_value(row["database"]),
            string_value(row["user"]),
            string_value(row["password"]),
            15,
        )

    return RecordingSQL(connection("sql_admin"), connection("sql_reader"))


def lifetime(config: Document) -> tuple[Callable[[], bool], float]:
    seconds = integer_value(config["duration_seconds"])
    require(1 <= seconds <= MAX_LIFETIME_SECONDS, "recording_lifetime_bound")
    stopped = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return lambda: stopped, time.monotonic() + seconds
