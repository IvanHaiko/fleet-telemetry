"""Public admission contract, independent of candidate internals and broker."""

import base64
import importlib
import importlib.metadata
import socket
import sys
import types
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import Mock, patch

SAFE_ERROR = "kafka_uuid_boundary_unavailable"
SDK_NAME = "confluent_kafka"
GUARD_NAME = "telemetry.kafka_compat"


def signed32(value):
    return ((value + 2147483648) % 4294967296) - 2147483648


def sdk_module(defect=None):
    """Only public SDK surface. Deliberately no implementation helper hooks."""
    sdk = types.ModuleType(SDK_NAME)

    class Uuid:
        def __init__(self, a, b):
            self.a, self.b = a, b
            if defect == "constructor_high_bits":
                self.a, self.b = signed32(a), signed32(b)
            if defect == "constructor_error":
                raise ValueError("sensitive native detail")

        def get_most_significant_bits(self):
            if defect in ("getters", "most_getter"):
                return signed32(self.a)
            if defect == "unsigned":
                return self.a % (1 << 64)
            if defect == "getter_type":
                return str(self.a)
            return self.a

        def get_least_significant_bits(self):
            if defect in ("getters", "least_getter"):
                return signed32(self.b)
            if defect == "unsigned":
                return self.b % (1 << 64)
            return self.b

        def __str__(self):
            a, b = self.a, self.b
            if defect == "string_high_bits":
                a, b = signed32(a), signed32(b)
            raw = a.to_bytes(8, "big", signed=True) + b.to_bytes(8, "big", signed=True)
            encoded = base64.b64encode(raw).decode("ascii").rstrip("=")
            if defect == "string_tail":
                return encoded[:-1] + ("A" if encoded[-1] != "A" else "B")
            return encoded

    sdk.Uuid = Uuid
    sdk.version = lambda: ("2.16.0", 0x02100000)
    sdk.libversion = lambda: ("2.16.0", 0x021000FF)
    return sdk


@contextmanager
def environment(
    sdk, distribution="2.16.0", python=(3, 13, 9, "final", 0), implementation="cpython"
):
    """All public patches are scoped and restored, even on failed assertions."""
    real_version = importlib.metadata.version

    def version(name):
        if name.replace("_", "-").lower() == "confluent-kafka":
            if isinstance(distribution, Exception):
                raise distribution
            return distribution
        return real_version(name)

    with ExitStack() as stack:
        stack.enter_context(patch.dict(sys.modules, {SDK_NAME: sdk}))
        stack.enter_context(patch.object(importlib.metadata, "version", version))
        stack.enter_context(patch.object(sys, "version_info", python))
        stack.enter_context(patch.object(sys.implementation, "name", implementation))
        yield


class UUIDGuard(unittest.TestCase):
    def load_guard(self):
        # Force a fresh import with SDK unavailable. Restores module cache and
        # parent package binding so these tests cannot leave import state behind.
        parent = importlib.import_module("telemetry")
        old_binding = vars(parent).get("kafka_compat")
        had_binding = "kafka_compat" in vars(parent)
        try:
            with patch.dict(sys.modules, {SDK_NAME: None}):
                sys.modules.pop(GUARD_NAME, None)
                module = importlib.import_module(GUARD_NAME)
                self.assertIsNone(sys.modules[SDK_NAME])
                return module
        finally:
            if had_binding:
                parent.kafka_compat = old_binding
            else:
                vars(parent).pop("kafka_compat", None)

    def setUp(self):
        self.guard = self.load_guard()
        self.assertTrue(issubclass(self.guard.KafkaCompatibilityError, ValueError))

    def invoke(
        self,
        sdk,
        distribution="2.16.0",
        python=(3, 13, 9, "final", 0),
        implementation="cpython",
        accepted=False,
    ):
        before = dict(vars(sdk)) if sdk is not None else None
        # Client construction, network and file writes are outside this guard.
        forbidden = Mock(side_effect=AssertionError("guard performed I/O"))
        admin = types.ModuleType("confluent_kafka.admin")
        admin.AdminClient = forbidden
        if sdk is not None:
            sdk.AdminClient = forbidden
            sdk.Producer = forbidden
            sdk.Consumer = forbidden
            before = dict(vars(sdk))
        uuid_type = getattr(sdk, "Uuid", None)
        uuid_before = dict(vars(uuid_type)) if isinstance(uuid_type, type) else None
        with environment(sdk, distribution, python, implementation):
            with patch.dict(sys.modules, {"confluent_kafka.admin": admin}):
                with ExitStack() as stack:
                    stack.enter_context(patch.object(socket, "socket", forbidden))
                    stack.enter_context(
                        patch.object(socket, "create_connection", forbidden)
                    )
                    stack.enter_context(patch("builtins.open", forbidden))
                    if accepted:
                        self.assertIsNone(self.guard.require_uuid_boundary())
                    else:
                        with self.assertRaises(
                            self.guard.KafkaCompatibilityError
                        ) as caught:
                            self.guard.require_uuid_boundary()
                        self.assertEqual(str(caught.exception), SAFE_ERROR)
                    self.assertIs(sys.modules[SDK_NAME], sdk)
                    if sdk is not None:
                        self.assertEqual(vars(sdk), before)
                    if uuid_before is not None:
                        self.assertEqual(vars(uuid_type), uuid_before)
        forbidden.assert_not_called()

    def test_lazy_import_and_missing_sdk_refusal(self):
        # setUp already proved module import works with SDK absent.
        self.invoke(None)

    def test_supported_versions_require_full_width_conversion(self):
        for distribution in ("2.16.0", "2.16.0+fleet.uuid1"):
            with self.subTest(distribution=distribution):
                self.invoke(sdk_module(), distribution, accepted=True)
        # Calling again must still inspect the current boundary, not cache success.
        self.invoke(sdk_module("getters"))

    def test_unsupported_versions_and_runtime_profiles(self):
        cases = (
            {"distribution": "2.15.0"},
            {"distribution": "2.16.1"},
            {"distribution": "2.16.0+other"},
            {"distribution": importlib.metadata.PackageNotFoundError("secret")},
            {"python": (3, 12, 10, "final", 0)},
            {"python": (3, 14, 0, "final", 0)},
            {"implementation": "pypy"},
        )
        for case in cases:
            with self.subTest(case=case):
                self.invoke(sdk_module(), **case)
        sdk = sdk_module()
        sdk.version = lambda: ("2.15.0", 0x020F0000)
        self.invoke(sdk)

    def test_corrupted_or_malformed_public_sdk_is_refused_safely(self):
        for defect in (
            "constructor_high_bits",
            "getters",
            "most_getter",
            "least_getter",
            "unsigned",
            "getter_type",
            "string_high_bits",
            "string_tail",
            "constructor_error",
        ):
            with self.subTest(defect=defect):
                self.invoke(sdk_module(defect))
        for attribute, value in (
            ("Uuid", None),
            ("version", None),
            ("version", lambda: None),
            ("version", lambda: ()),
        ):
            with self.subTest(attribute=attribute, value=value):
                sdk = sdk_module()
                setattr(sdk, attribute, value)
                self.invoke(sdk)
        sdk = sdk_module()
        del sdk.Uuid
        self.invoke(sdk)
        sdk = sdk_module()
        sdk.Uuid = lambda a, b: object()
        self.invoke(sdk)


if __name__ == "__main__":
    unittest.main()
