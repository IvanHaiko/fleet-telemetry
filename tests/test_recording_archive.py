"""Reference archival must fit the 16-MiB immutable object cap without loss."""

import pytest

from runtime.continuous import recording_archive
from runtime.continuous.recording_archive import (
    REFERENCE_INDEX,
    read_reference,
    reference_parts,
)
from runtime.s3.archive_store import ArchiveStore
from runtime.s3.immutable import MAX_BYTES
from telemetry.archive_documents import digest


class Reader:
    """Stores exact objects and verifies reads like the immutable store."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = dict(objects)

    def lookup(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def read(self, key: str, sha256: str, byte_length: int) -> bytes:
        body = self.objects[key]
        assert len(body) == byte_length and digest(body) == sha256
        return body


def stored(body: bytes, part_bytes: int) -> tuple[Reader, ArchiveStore]:
    index, parts = reference_parts(body, part_bytes)
    reader = Reader({**parts, REFERENCE_INDEX: index})
    return reader, reader  # type: ignore[return-value]


def test_parts_respect_the_object_cap_and_rebuild_exact_bytes() -> None:
    lines = [b'{"n":%d}\n' % i for i in range(1000)]
    body = b"".join(lines)
    index, parts = reference_parts(body, 512)
    assert len(parts) > 1
    assert all(0 < len(part) <= 512 for part in parts.values())
    assert all(part.endswith(b"\n") for part in parts.values())
    assert b"".join(parts.values()) == body
    reader, store = stored(body, 512)
    sha = digest(body).removeprefix("sha256:")
    assert read_reference(store, sha, len(body), 512) == body
    # The production part size stays well inside the immutable object cap.
    assert recording_archive.REFERENCE_PART_BYTES < MAX_BYTES
    assert index == reader.objects[REFERENCE_INDEX]


def test_changed_part_layout_or_total_refuses() -> None:
    body = b"".join(b'{"n":%d}\n' % i for i in range(200))
    sha = digest(body).removeprefix("sha256:")
    reader, store = stored(body, 256)
    with pytest.raises(ValueError, match="recording_reference_index"):
        read_reference(store, "0" * 64, len(body), 256)
    with pytest.raises(ValueError, match="recording_reference_index"):
        read_reference(store, sha, len(body) + 1, 256)
    # A different but internally consistent split must not be accepted.
    other_index, other_parts = reference_parts(body, 128)
    other = Reader({**other_parts, REFERENCE_INDEX: other_index})
    with pytest.raises(ValueError, match="recording_reference_content"):
        read_reference(other, sha, len(body), 256)  # type: ignore[arg-type]
    del reader.objects[REFERENCE_INDEX]
    with pytest.raises(ValueError, match="recording_reference_index"):
        read_reference(store, sha, len(body), 256)


def test_incomplete_or_oversized_lines_refuse_before_upload() -> None:
    with pytest.raises(ValueError, match="recording_reference_body"):
        reference_parts(b'{"n":1}')
    with pytest.raises(ValueError, match="recording_reference_line"):
        reference_parts(b"x" * 300 + b"\n", 256)
