"""Immutable archive bytes and bounded, exact-prefix native inventory."""

from collections.abc import Mapping
from typing import Protocol, cast

from runtime.s3.boto_transport import (
    BotoTransport,
    _bucket,
    _sdk_errors,
    _status,
    make_client,
)
from runtime.s3.immutable import (
    ImmutableStore,
    RequestFailure,
    StoreError,
    Transport,
    _category,
)


class Listing(Protocol):
    def list_objects_v2(self, **kwargs: object) -> Mapping[str, object]: ...


class NativeListing:
    def __init__(self, client: Listing) -> None:
        self.client = client
        self.errors = _sdk_errors()

    def list_objects_v2(self, **kwargs: object) -> Mapping[str, object]:
        try:
            return self.client.list_objects_v2(**kwargs)
        except self.errors as error:
            status = _status(error)
            raise StoreError(_category(status)) from None
        except RequestFailure as error:
            raise StoreError(_category(error.status)) from None


class ArchiveStore(ImmutableStore):
    def __init__(
        self, transport: Transport, listing: Listing, *, bucket: str, prefix: str
    ) -> None:
        _bucket(bucket)
        super().__init__(transport, prefix)
        self.bucket = bucket
        self.listing = listing
        self._close: object = None

    def lookup(self, key: str) -> bytes | None:
        full = self._key(key)
        try:
            return self._get(full, [3])
        except StoreError as error:
            if error.category == "object_missing":
                return None
            raise

    def inventory(self) -> tuple[tuple[str, int], ...]:
        result: dict[str, int] = {}
        tokens: set[str] = set()
        token: str | None = None
        for _ in range(65):
            args: dict[str, object] = {
                "Bucket": self.bucket,
                "Prefix": self.prefix,
                "MaxKeys": 65,
            }
            if token is not None:
                args["ContinuationToken"] = token
            response = self.listing.list_objects_v2(**args)
            if (
                not isinstance(response, Mapping)
                or type(response.get("IsTruncated")) is not bool
            ):
                raise StoreError("invalid_format")
            contents = response.get("Contents", [])
            if not isinstance(contents, list) or len(contents) > 65:
                raise StoreError("limit_exceeded")
            for raw in cast(list[object], contents):
                if not isinstance(raw, Mapping):
                    raise StoreError("invalid_format")
                item = cast(Mapping[str, object], raw)
                key, size = item.get("Key"), item.get("Size")
                if not isinstance(key, str) or not key.startswith(self.prefix):
                    raise StoreError("invalid_format")
                relative = key[len(self.prefix) :]
                self._key(relative)
                if type(size) is not int or size < 0 or relative in result:
                    raise StoreError("invalid_format")
                result[relative] = size
                if len(result) > 64:
                    raise StoreError("limit_exceeded")
            if response["IsTruncated"] is False:
                return tuple(result.items())
            next_token = response.get("NextContinuationToken")
            if (
                type(next_token) is not str
                or not next_token
                or len(next_token) > 4096
                or next_token in tokens
            ):
                raise StoreError("invalid_format")
            tokens.add(next_token)
            token = next_token
        raise StoreError("limit_exceeded")

    def close(self) -> None:
        if callable(self._close):
            self._close()


def make_archive_store(
    endpoint: str,
    region: str,
    bucket: str,
    prefix: str,
    access_key: str,
    secret_key: str,
) -> ArchiveStore:
    class Inert:
        def put(self, key: str, body: bytes) -> None:
            raise StoreError("unsupported_profile")

        def get(self, key: str, max_bytes: int) -> bytes:
            raise StoreError("unsupported_profile")

        def list_objects_v2(self, **kwargs: object) -> Mapping[str, object]:
            raise StoreError("unsupported_profile")

    inert = Inert()
    store = ArchiveStore(inert, inert, bucket=bucket, prefix=prefix)
    client = make_client(
        endpoint=endpoint, region=region, access_key=access_key, secret_key=secret_key
    )
    store.transport = BotoTransport(client, bucket)
    store.listing = NativeListing(cast(Listing, client))
    store._close = client.close
    return store
