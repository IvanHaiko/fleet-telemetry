"""Finite archive source over the admitted immutable slice reader."""

import base64
import re
from collections.abc import Mapping
from typing import Protocol, cast

from runtime.kafka_archive.native import NativeSliceClient
from runtime.kafka_archive.reader import _snapshot, deadline, read_slice, remaining
from runtime.kafka_archive.types import SliceClient
from telemetry.archive_codec import _fail, _integer, _source
from telemetry.archive_interfaces import SourceState
from telemetry.archive_lineage import Registration, matches
from telemetry_reader import EnvelopeError, read_battery_event


class Reader(SliceClient, Protocol):
    def close(self) -> None: ...


class Committer(Protocol):
    def commit(self, next_offset: int, timeout: float) -> None: ...
    def close(self) -> None: ...


def validate(
    source: Mapping[str, object],
    start: int,
    end: int,
    registrations: tuple[Registration, ...],
    non_transactional: bool,
    timeout: float,
) -> tuple[dict[str, object], float]:
    owned = _source(source)
    start = _integer(start, 0, 2**63 - 1)
    end = _integer(end, 0, 2**63 - 1)
    if owned["partition"] != 0:
        _fail("unsupported_profile", "assignment")
    if start >= end or end - start > 32:
        _fail("limit_exceeded", "interval")
    if non_transactional is not True:
        _fail("unsupported_profile", "source")
    if type(registrations) is not tuple or not 1 <= len(registrations) <= 2:
        _fail("lineage_mismatch", "registration")
    if any(not isinstance(item, Registration) for item in registrations):
        _fail("lineage_mismatch", "registration")
    return owned, deadline(timeout)


class ArchiveKafkaSource:
    def __init__(
        self,
        reader: Reader,
        committer: Committer,
        source: Mapping[str, object],
        start_offset: int,
        next_offset: int,
        registrations: tuple[Registration, ...],
        *,
        non_transactional: bool,
        timeout_seconds: float = 120,
    ) -> None:
        self.source, self.expires = validate(
            source,
            start_offset,
            next_offset,
            registrations,
            non_transactional,
            timeout_seconds,
        )
        self.reader, self.committer = reader, committer
        self.start, self.end = start_offset, next_offset
        self.registrations = registrations
        self.started = False
        self.attempted_commit = False

    def snapshot(self) -> SourceState:
        try:
            info = self.reader.inspect(remaining(self.expires))
            if info.source != self.source:
                _fail("source_identity", "source")
            _snapshot(info, self.source, self.start, self.end)
            remaining(self.expires)
            if not self.started:
                if self.reader.assigned() is not True:
                    self.reader.assign(self.start)
                self.started = True
            if self.reader.assigned() is not True:
                _fail("unsupported_profile", "assignment")
            remaining(self.expires)
            return SourceState(
                dict(info.source),
                info.low,
                info.high,
                info.committed,
                info.delete_only,
                True,
                True,
            )
        except PermissionError:
            _fail("permission_denied", "source")
        except TimeoutError:
            _fail("deadline_exceeded", "source")
        except OSError:
            _fail("source_unavailable", "source")

    def observations(
        self, start: int, next_offset: int
    ) -> tuple[dict[str, object], ...]:
        if (
            type(start) is not int
            or type(next_offset) is not int
            or (start, next_offset) != (self.start, self.end)
        ):
            _fail("invalid_format", "interval")
        self.snapshot()
        rows = read_slice(
            self.reader,
            self.source,
            start,
            next_offset,
            timeout_seconds=remaining(self.expires),
        )
        for row in rows:
            value = row["value_b64"]
            if value is None:
                continue
            try:
                event = dict(
                    read_battery_event(
                        base64.b64decode(cast(str, value), validate=True)
                    )
                )
            except EnvelopeError:
                continue
            admitted = [job for job in self.registrations if matches(event, job)]
            if len(admitted) > 1:
                _fail("lineage_mismatch", "registration")
            if admitted:
                row["measurement"] = {
                    "event_id": event["event_id"],
                    "source_manifest_sha256": admitted[0].job_hash,
                }
        remaining(self.expires)
        return rows

    def commit(self, next_offset: int) -> None:
        timeout = min(5.0, remaining(self.expires))
        if (
            type(next_offset) is not int
            or next_offset != self.end
            or self.attempted_commit
        ):
            _fail("progress_mismatch", "commit")
        self.attempted_commit = True
        try:
            self.committer.commit(next_offset, timeout)
            remaining(self.expires)
        except PermissionError:
            _fail("permission_denied", "commit")
        except TimeoutError:
            _fail("deadline_exceeded", "commit")
        except OSError:
            _fail("source_unavailable", "commit")

    def close(self) -> None:
        try:
            self.reader.close()
        finally:
            self.committer.close()


def open_source(
    endpoint: str,
    group: str,
    source: Mapping[str, object],
    start_offset: int,
    next_offset: int,
    registrations: tuple[Registration, ...],
    *,
    non_transactional: bool,
    timeout_seconds: float = 120,
) -> ArchiveKafkaSource:
    from runtime.kafka_archive.commit import NativeCommitter

    _, expires = validate(
        source,
        start_offset,
        next_offset,
        registrations,
        non_transactional,
        timeout_seconds,
    )
    if (
        endpoint != "127.0.0.1:19092"
        or type(group) is not str
        or re.fullmatch(r"m4-reader-[a-z0-9-]{1,64}", group) is None
    ):
        _fail("unsupported_profile", "source")
    reader = NativeSliceClient(endpoint, group, source)
    try:
        committer = NativeCommitter(endpoint, group, source)
    except BaseException:
        reader.close()
        raise
    return ArchiveKafkaSource(
        reader,
        committer,
        source,
        start_offset,
        next_offset,
        registrations,
        non_transactional=non_transactional,
        timeout_seconds=remaining(expires),
    )
