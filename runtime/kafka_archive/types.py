"""Read-only source port and immutable inspection result."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SourceInfo:
    source: Mapping[str, object]
    low: int
    high: int
    committed: int | None
    delete_only: bool


class SliceClient(Protocol):
    def inspect(self, timeout: float) -> SourceInfo: ...
    def assign(self, start: int) -> None: ...
    def poll(self, timeout: float) -> Mapping[str, object] | None: ...
    def assigned(self) -> bool: ...
