"""Actual native constructor gate; requires an installed confluent_kafka SDK."""

import base64
import importlib
import unittest

# Literal signed64 inputs, including collisions in the low 32 bits of BOTH halves.
HALVES = (
    (0, 0),
    (-1, -1),
    (9223372036854775807, -9223372036854775808),
    (-9223372036854775808, 9223372036854775807),
    (1, 2),
    (4294967297, 8589934594),
    (-4294967295, -8589934590),
    (81985529216486895, -81985529216486896),
    (-1, 0),
    (0, -1),
)


def expected_bytes(a, b):
    """Independent two's-complement oracle; no SDK-derived expectations."""
    return a.to_bytes(8, "big", signed=True) + b.to_bytes(8, "big", signed=True)


class ActualSDK(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # ImportError is a failing gate, never a skip or a fake substitute.
        cls.sdk = importlib.import_module("confluent_kafka")

    def test_native_constructor_getters_and_complete_string(self):
        for a, b in HALVES:
            with self.subTest(a=a, b=b):
                value = self.sdk.Uuid(a, b)
                self.assertEqual(value.get_most_significant_bits(), a)
                self.assertEqual(value.get_least_significant_bits(), b)
                raw = expected_bytes(a, b)
                encoded = base64.b64encode(raw).decode("ascii").rstrip("=")
                self.assertEqual(str(value), encoded)
                self.assertEqual(
                    base64.b64decode(str(value) + "==", validate=True), raw
                )


if __name__ == "__main__":
    unittest.main()
