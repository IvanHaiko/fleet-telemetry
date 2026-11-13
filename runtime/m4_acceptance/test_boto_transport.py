# ruff: noqa: B017
# Preserve the independently frozen exception-generality assertions.
"""Public transport boundary tests; no installed SDK or backend required."""

import importlib
import io
import logging
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

SECRET = "private-payload-credential-marker"
KEY = "archive-v1/run-1/objects/a.bin"
BUCKET = "archive"
OPTIONS = dict(
    endpoint="http://127.0.0.1:19000",
    region="local-test",
    access_key="explicit-access",
    secret_key="explicit-secret",
)


class ClientError(Exception):
    def __init__(self, response, operation_name):
        self.response = response
        self.operation_name = operation_name
        super().__init__(SECRET)


class BotoCoreError(Exception):
    pass


class ConnectionError(BotoCoreError):
    pass


class HTTPClientError(BotoCoreError):
    pass


class IncompleteReadError(BotoCoreError):
    pass


class ResponseStreamingError(HTTPClientError):
    pass


class ChecksumError(BotoCoreError):
    pass


class EndpointConnectionError(ConnectionError):
    def __init__(self, **kwargs):
        super().__init__(SECRET)


class ReadTimeoutError(HTTPClientError):
    def __init__(self, **kwargs):
        super().__init__(SECRET)


class Stream:
    def __init__(self, body=b"", error=None):
        self.body = io.BytesIO(body)
        self.error = error
        self.closed = False

    def read(self, amt):
        if self.error is not None:
            raise self.error
        # Short reads force the transport to consume until EOF.
        return self.body.read(min(amt, 3))

    def close(self):
        self.closed = True
        self.body.close()


class Config:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeSDK:
    """Only the documented low-level SDK construction boundary is provided."""

    def __init__(self):
        self.calls = []
        self.sessions = []
        self.client = mock.Mock()
        self.modules = {}
        for name in ("boto3", "botocore", "botocore.config", "botocore.exceptions"):
            module = types.ModuleType(name)
            module.__version__ = "1.43.117"
            self.modules[name] = module
        self.modules["botocore.config"].Config = Config
        exceptions = self.modules["botocore.exceptions"]
        for cls in (
            ClientError,
            BotoCoreError,
            ConnectionError,
            HTTPClientError,
            IncompleteReadError,
            ResponseStreamingError,
            ChecksumError,
            EndpointConnectionError,
            ReadTimeoutError,
        ):
            setattr(exceptions, cls.__name__, cls)
        self.modules["botocore"].config = self.modules["botocore.config"]
        self.modules["botocore"].exceptions = exceptions
        self.modules["boto3"].client = self.new_client
        self.modules["boto3"].Session = self.session
        session_module = types.ModuleType("boto3.session")
        session_module.Session = self.session
        self.modules["boto3.session"] = session_module
        self.modules["boto3"].session = session_module

    def session(self, **kwargs):
        self.sessions.append(kwargs)
        return types.SimpleNamespace(client=self.new_client)

    def new_client(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.client

    def load(self):
        real_import = importlib.import_module

        def import_module(name, package=None):
            if name in self.modules:
                return self.modules[name]
            return real_import(name, package)

        # Covers both direct SDK imports and lazy importlib factories.
        self.module_patch = mock.patch.dict("sys.modules", self.modules)
        self.import_patch = mock.patch("importlib.import_module", import_module)
        self.module_patch.start()
        self.import_patch.start()
        return real_import("runtime.s3.boto_transport")

    def stop(self):
        self.import_patch.stop()
        self.module_patch.stop()


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.sdk = FakeSDK()
        self.addCleanup(self.sdk.stop)
        self.api = self.sdk.load()
        self.failure = importlib.import_module("runtime.s3.immutable").RequestFailure
        self.transport = self.api.BotoTransport(self.sdk.client, BUCKET)

    def safe_failure(self, call, status):
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        logger = logging.getLogger()
        logger.addHandler(handler)
        try:
            with redirect_stdout(output), redirect_stderr(output):
                with self.assertRaises(self.failure) as caught:
                    call()
        finally:
            logger.removeHandler(handler)
        self.assertEqual(caught.exception.status, status)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertNotIn(SECRET, output.getvalue())
        return caught.exception

    def test_one_conditional_low_level_put(self):
        body = b"\x00archive\xff"
        self.transport.put(KEY, body)
        self.sdk.client.put_object.assert_called_once_with(
            Bucket=BUCKET, Key=KEY, Body=body, IfNoneMatch="*"
        )
        self.sdk.client.get_object.assert_not_called()
        self.sdk.client.head_object.assert_not_called()
        self.sdk.client.upload_fileobj.assert_not_called()

    def test_known_client_and_network_failures_are_safe_and_not_retried(self):
        errors = [
            (
                ClientError(
                    {
                        "ResponseMetadata": {"HTTPStatusCode": status},
                        "Error": {"Code": "Denied", "Message": SECRET},
                    },
                    "PutObject",
                ),
                status,
            )
            for status in (403, 409, 412, 503)
        ]
        errors.append((EndpointConnectionError(endpoint_url=SECRET), None))
        for method in ("put_object", "get_object"):
            for error, status in errors:
                with self.subTest(method=method, status=status):
                    self.sdk.client.reset_mock()
                    getattr(self.sdk.client, method).side_effect = error
                    call = (
                        (lambda: self.transport.put(KEY, b"x"))
                        if method == ("put_object")
                        else (lambda: self.transport.get(KEY, 32))
                    )
                    self.safe_failure(call, status)
                    getattr(self.sdk.client, method).assert_called_once()
                    getattr(self.sdk.client, method).side_effect = None

    def test_unknown_programming_errors_are_not_translated(self):
        for method, call in (
            ("put_object", lambda: self.transport.put(KEY, b"x")),
            ("get_object", lambda: self.transport.get(KEY, 32)),
        ):
            error = RuntimeError("local programming error")
            getattr(self.sdk.client, method).side_effect = error
            with self.assertRaises(RuntimeError) as caught:
                call()
            self.assertIs(caught.exception, error)

    def test_empty_and_binary_short_streams_are_fully_read_and_closed(self):
        for body in (b"", bytes(range(256))):
            for length in (None, len(body)):
                with self.subTest(size=len(body), length=length):
                    stream = Stream(body)
                    response = {"Body": stream}
                    if length is not None:
                        response["ContentLength"] = length
                    self.sdk.client.get_object.return_value = response
                    self.assertEqual(self.transport.get(KEY, 256), body)
                    self.assertTrue(stream.closed)
        self.sdk.client.get_object.assert_called_with(Bucket=BUCKET, Key=KEY)

    def test_oversize_is_rejected_even_without_truthful_length(self):
        for length in (None, 0, 2, 9):
            with self.subTest(length=length):
                stream = Stream(b"123456789")
                response = {"Body": stream}
                if length is not None:
                    response["ContentLength"] = length
                self.sdk.client.get_object.return_value = response
                error_type = importlib.import_module("runtime.s3.immutable").StoreError
                with self.assertRaises(error_type) as caught:
                    self.transport.get(KEY, 8)
                self.assertEqual(caught.exception.category, "limit_exceeded")
                self.assertTrue(stream.closed)

    def test_stream_failure_is_translated_and_closed(self):
        stream = Stream(error=ReadTimeoutError(endpoint_url=SECRET))
        self.sdk.client.get_object.return_value = {"Body": stream}
        self.safe_failure(lambda: self.transport.get(KEY, 32), None)
        self.assertTrue(stream.closed)

    def test_factory_uses_explicit_safe_configuration(self):
        ambient = {
            "HTTP_PROXY": "http://invalid:1",
            "HTTPS_PROXY": "http://invalid:2",
            "ALL_PROXY": "http://invalid:3",
            "AWS_DEFAULT_REGION": "ambient",
        }
        with mock.patch.dict("os.environ", ambient):
            self.assertIs(self.api.make_client(**OPTIONS), self.sdk.client)
        self.assertEqual(len(self.sdk.calls), 1)
        args, kwargs = self.sdk.calls[0]
        self.assertEqual(args or (kwargs.get("service_name"),), ("s3",))
        self.assertEqual(kwargs["endpoint_url"], OPTIONS["endpoint"])
        effective = {}
        for session in self.sdk.sessions:
            effective.update(session)
        effective.update(kwargs)
        self.assertEqual(effective["region_name"], OPTIONS["region"])
        self.assertEqual(effective["aws_access_key_id"], OPTIONS["access_key"])
        self.assertEqual(effective["aws_secret_access_key"], OPTIONS["secret_key"])
        self.assertFalse(effective.get("profile_name"))
        config = kwargs["config"]
        self.assertEqual(config.retries["total_max_attempts"], 1)
        self.assertEqual(config.connect_timeout, 2)
        self.assertEqual(config.read_timeout, 5)
        self.assertEqual(config.signature_version, "s3v4")
        self.assertEqual(config.s3["addressing_style"], "path")
        self.assertEqual(config.proxies, {})

    def test_factory_rejects_ambient_aws_credentials_and_routing(self):
        error_type = importlib.import_module("runtime.s3.immutable").StoreError
        for name in (
            "AWS_PROFILE",
            "AWS_ENDPOINT_URL",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
        ):
            with (
                self.subTest(variable=name),
                mock.patch.dict("os.environ", {name: SECRET}),
            ):
                with self.assertRaises(error_type) as caught:
                    self.api.make_client(**OPTIONS)
                self.assertIn(
                    caught.exception.category, ("invalid_format", "unsupported_profile")
                )
                self.assertNotIn(SECRET, str(caught.exception))
                self.assertEqual(self.sdk.calls, [])
                self.assertEqual(self.sdk.sessions, [])

    def test_factory_refuses_unsafe_or_missing_explicit_settings(self):
        changes = [
            {"endpoint": value}
            for value in (
                "",
                "https://127.0.0.1:9000",
                "http://localhost:9000",
                "http://example.com:9000",
                "http://169.254.169.254:80",
                "http://127.0.0.1:9000/path",
                "http://user@127.0.0.1:9000",
            )
        ]
        changes.extend({name: ""} for name in ("region", "access_key", "secret_key"))
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(Exception):
                    self.api.make_client(**(OPTIONS | change))
                self.assertEqual(self.sdk.calls, [])
        for name in OPTIONS:
            options = OPTIONS.copy()
            del options[name]
            with self.subTest(missing=name):
                with self.assertRaises(Exception):
                    self.api.make_client(**options)
                self.assertEqual(self.sdk.calls, [])

    def test_factory_refuses_unpinned_sdk_versions(self):
        for name in ("boto3", "botocore"):
            with self.subTest(module=name):
                self.sdk.modules[name].__version__ = "1.43.116"
                try:
                    with self.assertRaises(Exception):
                        self.api.make_client(**OPTIONS)
                    self.assertEqual(self.sdk.calls, [])
                finally:
                    self.sdk.modules[name].__version__ = "1.43.117"

    def test_factory_client_failure_does_not_try_defaults(self):
        error = EndpointConnectionError(endpoint_url=SECRET)
        with mock.patch.object(self.sdk, "new_client", side_effect=error) as factory:
            # Replace the public fake entry points, not candidate internals.
            self.sdk.modules["boto3"].client = factory
            with self.assertRaises(Exception):
                self.api.make_client(**OPTIONS)
            self.assertEqual(factory.call_count, 1)

    def test_store_factory_wires_public_transport_and_core(self):
        store = self.api.make_store(
            **OPTIONS, bucket=BUCKET, prefix="archive-v1/run-1/", max_bytes=8
        )
        stream = Stream(b"\x00\xff")
        self.sdk.client.get_object.return_value = {"Body": stream}
        self.assertEqual(store.create("objects/a.bin", b"\x00\xff"), "created")
        self.sdk.client.put_object.assert_called_once_with(
            Bucket=BUCKET, Key=KEY, Body=b"\x00\xff", IfNoneMatch="*"
        )
        self.assertTrue(stream.closed)


if __name__ == "__main__":
    unittest.main()
