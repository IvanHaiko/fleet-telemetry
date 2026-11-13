"""Explicit local-only SDK boundary for the pinned low-level S3 client."""

import importlib
import os
import re
from collections.abc import Callable, Mapping
from typing import Protocol, cast
from urllib.parse import urlsplit

from .immutable import MAX_BYTES, ImmutableStore, RequestFailure, StoreError


class StreamingBody(Protocol):
    def read(self, amt: int) -> bytes: ...

    def close(self) -> None: ...


class Events(Protocol):
    def register_first(
        self, event_name: str, handler: Callable[..., object]
    ) -> None: ...


class ClientMeta(Protocol):
    @property
    def events(self) -> Events: ...


class S3Client(Protocol):
    """Low-level client surface, including parent credential/permission probes."""

    @property
    def meta(self) -> ClientMeta: ...

    def put_object(
        self, *, Bucket: str, Key: str, Body: bytes, IfNoneMatch: str
    ) -> Mapping[str, object]: ...

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]: ...

    def delete_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]: ...

    def create_bucket(self, *, Bucket: str) -> Mapping[str, object]: ...

    def close(self) -> None: ...


class _Session(Protocol):
    def client(self, service_name: str, **kwargs: object) -> S3Client: ...


class _Boto(Protocol):
    __version__: str

    def Session(
        self, *, aws_access_key_id: str, aws_secret_access_key: str, region_name: str
    ) -> _Session: ...


class _ConfigModule(Protocol):
    def Config(self, **kwargs: object) -> object: ...


class _Exceptions(Protocol):
    ClientError: type[Exception]
    ConnectionError: type[Exception]
    HTTPClientError: type[Exception]
    IncompleteReadError: type[Exception]
    ResponseStreamingError: type[Exception]
    ChecksumError: type[Exception]


def _endpoint(endpoint: str) -> None:
    if (
        not isinstance(endpoint, str)
        or re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", endpoint) is None
    ):
        raise StoreError("invalid_format")
    if not 1 <= int(endpoint.rsplit(":", 1)[1]) <= 65535:
        raise StoreError("invalid_format")


def _bucket(bucket: str) -> None:
    if (
        not isinstance(bucket, str)
        or re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket) is None
    ):
        raise StoreError("invalid_format")


def _status(error: Exception) -> int | None:
    response: object = getattr(error, "response", None)
    if isinstance(response, dict):
        metadata = cast(Mapping[str, object], response).get("ResponseMetadata")
        if isinstance(metadata, dict):
            status = cast(Mapping[str, object], metadata).get("HTTPStatusCode")
            if type(status) is int and 100 <= status <= 599:
                return status
    return None


def _sdk_errors() -> tuple[type[Exception], ...]:
    errors = cast(_Exceptions, importlib.import_module("botocore.exceptions"))
    return (
        errors.ClientError,
        errors.ConnectionError,
        errors.HTTPClientError,
        errors.IncompleteReadError,
        errors.ResponseStreamingError,
        errors.ChecksumError,
    )


def _refuse_ambient_aws() -> None:
    """Refuse conflicting discovery inputs before importing or invoking the SDK."""
    forbidden = {
        "AWS_ACCESS_KEY_ID",
        "AWS_ACCESS_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SECRET_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_SECURITY_TOKEN",
        "AWS_PROFILE",
        "AWS_DEFAULT_PROFILE",
        "AWS_SHARED_CREDENTIALS_FILE",
        "AWS_CREDENTIAL_FILE",
        "AWS_CONFIG_FILE",
        "BOTO_CONFIG",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
        "AWS_ROLE_ARN",
        "AWS_ROLE_SESSION_NAME",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_CONTAINER_AUTHORIZATION_TOKEN",
        "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE",
        "AWS_EC2_METADATA_SERVICE_ENDPOINT",
        "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE",
        "AWS_ENDPOINT_URL",
        "AWS_USE_FIPS_ENDPOINT",
        "AWS_USE_DUALSTACK_ENDPOINT",
    }
    if any(
        # The pinned SDK treats even an empty profile selector as a profile.
        name in {"AWS_PROFILE", "AWS_DEFAULT_PROFILE"}
        or (value and (name in forbidden or name.startswith("AWS_ENDPOINT_URL_")))
        for name, value in os.environ.items()
    ):
        raise StoreError("unsupported_profile")


def make_client(
    *, endpoint: str, region: str, access_key: str, secret_key: str
) -> S3Client:
    """Create a pinned client without credential discovery or cloud fallback."""
    _endpoint(endpoint)
    for value in (region, access_key, secret_key):
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or any(ord(char) < 33 or ord(char) > 126 for char in value)
        ):
            raise StoreError("invalid_format")
    _refuse_ambient_aws()
    boto = cast(_Boto, importlib.import_module("boto3"))
    core = importlib.import_module("botocore")
    if (
        boto.__version__ != "1.43.117"
        or getattr(core, "__version__", None) != "1.43.117"
    ):
        raise StoreError("unsupported_profile")
    config_module = cast(_ConfigModule, importlib.import_module("botocore.config"))
    config = config_module.Config(
        retries={"total_max_attempts": 1, "mode": "standard"},
        connect_timeout=2,
        read_timeout=5,
        signature_version="s3v4",
        s3={"addressing_style": "path", "use_accelerate_endpoint": False},
        proxies={},
        use_fips_endpoint=False,
        use_dualstack_endpoint=False,
        ignore_configured_endpoint_urls=True,
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )
    session = boto.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    client = session.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        config=config,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        use_ssl=False,
    )

    def guard_send(request: object, **kwargs: object) -> None:
        url: object = getattr(request, "url", None)
        if not isinstance(url, str):
            raise RequestFailure(400, "invalid request endpoint")
        parsed = urlsplit(url)
        if (
            parsed.scheme != "http"
            or parsed.netloc != endpoint.removeprefix("http://")
            or parsed.fragment
        ):
            raise RequestFailure(400, "endpoint change refused")

    def guard_redirect(response: object = None, **kwargs: object) -> None:
        if isinstance(response, tuple) and response:
            status: object = getattr(
                cast(tuple[object, ...], response)[0], "status_code", None
            )
            if type(status) is int and 300 <= status <= 399:
                raise RequestFailure(status, "redirect refused")
        # Botocore's S3 region redirector can retry 400 responses too.
        if isinstance(response, tuple) and len(response) > 1:
            data: object = cast(tuple[object, ...], response)[1]
            if isinstance(data, dict):
                error = cast(Mapping[str, object], data).get("Error")
                if isinstance(error, dict) and cast(Mapping[str, object], error).get(
                    "Code"
                ) in (
                    "AuthorizationHeaderMalformed",
                    "PermanentRedirect",
                    "IllegalLocationConstraintException",
                ):
                    raise RequestFailure(400, "region redirect refused")

    client.meta.events.register_first("before-send.s3", guard_send)
    client.meta.events.register_first("needs-retry.s3", guard_redirect)
    return client


class BotoTransport:
    """One signed request per method; stream size is checked independently."""

    def __init__(self, client: S3Client, bucket: str) -> None:
        _bucket(bucket)
        self.client = client
        self.bucket = bucket
        self._errors = _sdk_errors()

    def put(self, key: str, body: bytes) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=key, Body=body, IfNoneMatch="*"
            )
        except self._errors as error:
            raise RequestFailure(_status(error), "S3 PUT failed") from None

    def get(self, key: str, max_bytes: int) -> bytes:
        if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES:
            raise StoreError("limit_exceeded")
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            raw_body = response.get("Body")
            if not callable(getattr(raw_body, "close", None)):
                raise RequestFailure(400, "invalid S3 response stream")
            # Reviewed cast: botocore GetObject returns StreamingBody; validate
            # every read result instead of trusting the untyped SDK response.
            body = cast(StreamingBody, raw_body)
            try:
                if not callable(getattr(raw_body, "read", None)):
                    raise RequestFailure(400, "invalid S3 response stream")
                length = response.get("ContentLength")
                if type(length) is int and length > max_bytes:
                    raise StoreError("limit_exceeded")
                result = bytearray()
                while True:
                    chunk = body.read(min(65_536, max_bytes - len(result) + 1))
                    if not isinstance(chunk, bytes):
                        raise RequestFailure(400, "invalid S3 stream bytes")
                    if len(chunk) > max_bytes - len(result):
                        raise StoreError("limit_exceeded")
                    if not chunk:
                        return bytes(result)
                    result.extend(chunk)
            finally:
                body.close()
        except self._errors as error:
            raise RequestFailure(_status(error), "S3 GET failed") from None


def make_store(
    *,
    endpoint: str,
    region: str,
    bucket: str,
    prefix: str,
    access_key: str,
    secret_key: str,
    max_bytes: int = MAX_BYTES,
) -> ImmutableStore:
    """Validate all storage configuration before creating any SDK client."""
    _bucket(bucket)

    # Construct with a typed inert transport first to validate prefix and bound.
    class Unconfigured:
        def put(self, key: str, body: bytes) -> None:
            raise StoreError("unsupported_profile")

        def get(self, key: str, max_bytes: int) -> bytes:
            raise StoreError("unsupported_profile")

    store = ImmutableStore(Unconfigured(), prefix, max_bytes=max_bytes)
    client = make_client(
        endpoint=endpoint, region=region, access_key=access_key, secret_key=secret_key
    )
    store.transport = BotoTransport(client, bucket)
    return store
