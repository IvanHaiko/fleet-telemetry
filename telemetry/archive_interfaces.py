"""Trusted injectable ports; concrete isolation and deadlines belong to the host."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SourceState:
    """Fresh identity, retention, effective profile and group progress."""

    source: Mapping[str, object]
    low: int
    high: int
    committed: int | None
    delete_only: bool
    non_transactional: bool
    assigned: bool


class CommitAmbiguous(Exception):
    """Commit acknowledgement was lost; only fresh observed U resolves it."""


class ReadStore(Protocol):
    """Fresh full-body reads; the graph independently checks integrity."""

    def read(self, key: str, sha256: str, byte_length: int) -> bytes: ...


class PublishStore(ReadStore, Protocol):
    """Owned-prefix immutable storage; inventory includes all retained orphans."""

    def create(self, key: str, body: bytes) -> str: ...
    def lookup(self, key: str) -> bytes | None: ...
    def inventory(self) -> Sequence[tuple[str, int]]: ...


class ArchiveSource(Protocol):
    """Finite lossless source with synchronous explicit commit and no reset."""

    def snapshot(self) -> SourceState: ...
    def observations(
        self, start: int, next_offset: int
    ) -> Sequence[Mapping[str, object]]: ...
    def commit(self, next_offset: int) -> None: ...


class ArchiveHooks(Protocol):
    """Host-enforced fresh reader process and independently retained root.

    Injected calls alone prove neither process isolation nor durable retention.
    The host must enforce separate credentials, 120-second process deadline and
    process-group shutdown. The engine checks exact retained bytes before commit.
    """

    def verify_fresh(self, descriptor: bytes, expected_sha256: str) -> None: ...
    def retain(self, descriptor: bytes, expected_sha256: str) -> None: ...
    def read_retained(self) -> bytes: ...
