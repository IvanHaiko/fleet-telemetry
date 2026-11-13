"""Immutable publication and exact owned-prefix projected body accounting."""

from collections.abc import Mapping
from typing import cast

from runtime.s3.immutable import StoreError
from telemetry.archive_codec import _fail, _integer, _string
from telemetry.archive_documents import BODY_BUDGET, check_body, ref, store_failure
from telemetry.archive_graph import GraphReader
from telemetry.archive_interfaces import PublishStore


class ProposedStore:
    """Read-only overlay used to verify the full proposed graph before sealing."""

    def __init__(self, objects: Mapping[str, bytes], store: PublishStore) -> None:
        self.objects = objects
        self.store = store

    def read(self, key: str, sha256: str, byte_length: int) -> bytes:
        if key in self.objects:
            return self.objects[key]
        return self.store.read(key, sha256, byte_length)


def inventory(store: PublishStore, proposed: Mapping[str, bytes]) -> dict[str, int]:
    """Count all orphans and proposed new keys without trusting listing as coverage."""
    try:
        entries = store.inventory()
    except StoreError as error:
        store_failure(error, "inventory")
    except PermissionError:
        _fail("permission_denied", "inventory")
    except TimeoutError:
        _fail("deadline_exceeded", "inventory")
    except OSError:
        _fail("source_unavailable", "inventory")
    if len(entries) > 64:
        _fail("limit_exceeded", "inventory")
    sizes: dict[str, int] = {}
    for item in entries:
        if not isinstance(item, tuple) or len(item) != 2:
            _fail("invalid_format", "inventory")
        key, size = item
        _string(key, 512)
        _integer(size, 0, 2**63)
        if size > BODY_BUDGET:
            _fail("limit_exceeded", "inventory")
        if key in sizes:
            _fail("invalid_format", "inventory")
        sizes[key] = size
    projected = dict(sizes)
    for key, body in proposed.items():
        if key in sizes and sizes[key] != len(body):
            _fail("checksum_mismatch", "inventory")
        projected[key] = len(body)
    if len(projected) > 64 or sum(projected.values()) > BODY_BUDGET:
        _fail("limit_exceeded", "inventory")
    return sizes


def lookup(store: PublishStore, key: str) -> bytes | None:
    """Translate known storage failures without hiding arbitrary port errors."""
    try:
        return store.lookup(key)
    except StoreError as error:
        store_failure(error, "object")
    except PermissionError:
        _fail("permission_denied", "object")
    except TimeoutError:
        _fail("deadline_exceeded", "object")
    except OSError:
        _fail("source_unavailable", "object")


def publish(
    store: PublishStore, reference: dict[str, object], body: bytes, role: str
) -> None:
    """Use the immutable port and require full independent readback."""
    reference = ref(reference, role)
    check_body(body, reference)
    key = cast(str, reference["key"])
    try:
        store.create(key, body)
    except StoreError as error:
        store_failure(error, "object")
    except PermissionError:
        _fail("permission_denied", "object")
    except TimeoutError:
        _fail("deadline_exceeded", "object")
    except OSError:
        _fail("source_unavailable", "object")
    GraphReader(store).read(reference, role)
