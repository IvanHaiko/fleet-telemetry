"""Bounded immutable byte storage; transport owns atomic conditional creation."""

import hashlib
import re
from typing import Protocol

MAX_BYTES = 16_777_216


class RequestFailure(Exception):
    """Safe transport failure, with no remote response or request payload."""

    def __init__(self, status: int | None, reason: str) -> None:
        self.status = status
        self.reason = reason
        super().__init__(reason)


class StoreError(Exception):
    """Stable application failure category."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class Transport(Protocol):
    """Each invocation performs one request, without hidden retries."""

    def put(self, key: str, body: bytes) -> None: ...

    def get(self, key: str, max_bytes: int) -> bytes: ...


def _retryable(status: int | None) -> bool:
    return status is None or status == 409 or 500 <= status <= 599


def _category(status: int | None) -> str:
    if status in (401, 403):
        return "permission_denied"
    if status == 404:
        return "object_missing"
    return "unsupported_profile"


class ImmutableStore:
    """No cache; each logical operation has three PUT and three GET slots."""

    def __init__(
        self, transport: Transport, prefix: str, *, max_bytes: int = MAX_BYTES
    ) -> None:
        if not isinstance(prefix, str) or not re.fullmatch(
            r"archive-v1/[a-z0-9][a-z0-9-]{0,63}/", prefix
        ):
            raise StoreError("invalid_format")
        if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES:
            raise StoreError("limit_exceeded")
        self.transport = transport
        self.prefix = prefix
        self.max_bytes = max_bytes

    def _key(self, key: str) -> str:
        if (
            not isinstance(key, str)
            or not 1 <= len(key) <= 256
            or any(
                re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", part) is None
                for part in key.split("/")
            )
        ):
            raise StoreError("invalid_format")
        return self.prefix + key

    def _get(self, key: str, budget: list[int]) -> bytes:
        while budget[0] > 0:
            budget[0] -= 1
            try:
                body = self.transport.get(key, self.max_bytes)
            except RequestFailure as error:
                if _retryable(error.status):
                    continue
                raise StoreError(_category(error.status)) from None
            if not isinstance(body, bytes):
                raise StoreError("unsupported_profile")
            if len(body) > self.max_bytes:
                raise StoreError("limit_exceeded")
            return body
        raise StoreError("deadline_exceeded")

    def create(self, key: str, body: bytes) -> str:
        full_key = self._key(key)
        if not isinstance(body, bytes):
            raise StoreError("invalid_format")
        if len(body) > self.max_bytes:
            raise StoreError("limit_exceeded")
        budget = [3]
        for _ in range(3):
            if budget[0] == 0:
                raise StoreError("deadline_exceeded")
            status: int | None = None
            acknowledged = False
            try:
                self.transport.put(full_key, body)
                acknowledged = True
            except RequestFailure as error:
                status = error.status
                if status != 412 and not _retryable(status):
                    category = (
                        "permission_denied"
                        if status in (401, 403)
                        else "unsupported_profile"
                    )
                    raise StoreError(category) from None
            try:
                observed = self._get(full_key, budget)
            except StoreError as error:
                if error.category != "object_missing" or acknowledged:
                    raise
                if status == 412:
                    raise StoreError("conditional_create_unsupported") from None
                continue
            if observed != body:
                raise StoreError("observation_conflict")
            return "created" if acknowledged else "existing"
        raise StoreError("deadline_exceeded")

    def read(self, key: str, sha256: str, byte_length: int) -> bytes:
        full_key = self._key(key)
        if not isinstance(sha256, str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", sha256
        ):
            raise StoreError("invalid_format")
        if type(byte_length) is not int or byte_length < 0:
            raise StoreError("invalid_format")
        if byte_length > self.max_bytes:
            raise StoreError("limit_exceeded")
        body = self._get(full_key, [3])
        if (
            len(body) != byte_length
            or "sha256:" + hashlib.sha256(body).hexdigest() != sha256
        ):
            raise StoreError("checksum_mismatch")
        return body
