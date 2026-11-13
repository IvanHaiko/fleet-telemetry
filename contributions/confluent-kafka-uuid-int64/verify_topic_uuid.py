"""Compare actual AdminClient UUIDs with an independently supplied Kafka CLI ID."""

import argparse
import base64
import json
import re
from typing import Protocol, cast

from confluent_kafka import KafkaException, TopicCollection
from confluent_kafka.admin import AdminClient


class _Uuid(Protocol):
    def get_most_significant_bits(self) -> object: ...
    def get_least_significant_bits(self) -> object: ...


class _Description(Protocol):
    topic_id: _Uuid


def decode_cli(value: str) -> bytes:
    """Decode one complete URLsafe Kafka CLI UUID without inventing high bits."""
    if re.fullmatch(r"[A-Za-z0-9_-]{22}", value) is None:
        raise ValueError("expected_cli_uuid")
    raw = base64.b64decode(
        value.translate(str.maketrans("-_", "+/")) + "==", validate=True
    )
    if len(raw) != 16 or not any(raw):
        raise ValueError("expected_nonzero_uuid")
    if base64.urlsafe_b64encode(raw).decode().rstrip("=") != value:
        raise ValueError("expected_canonical_uuid")
    return raw


def main() -> int:
    """Read metadata only; never create topics, publish records or change offsets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-server", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--expected-topic-id", required=True)
    args = parser.parse_args()
    try:
        expected = decode_cli(args.expected_topic_id)
        admin = AdminClient(
            {"bootstrap.servers": args.bootstrap_server, "log_level": 0}
        )
        description = cast(
            _Description,
            admin.describe_topics(TopicCollection([args.topic]), request_timeout=5)[
                args.topic
            ].result(timeout=6),
        )
        value = description.topic_id
        most = value.get_most_significant_bits()
        least = value.get_least_significant_bits()
        if (
            not isinstance(most, int)
            or not isinstance(least, int)
            or isinstance(most, bool)
            or isinstance(least, bool)
        ):
            raise ValueError("integer_halves_required")
        halves = most.to_bytes(8, "big", signed=True) + least.to_bytes(
            8, "big", signed=True
        )
        encoded = base64.b64decode(str(value) + "==", validate=True)
        matched = expected == halves == encoded
        print(
            json.dumps(
                {
                    "status": "matched" if matched else "mismatch",
                    "expected_hex": expected.hex(),
                    "sdk_string_hex": encoded.hex(),
                    "sdk_halves_hex": halves.hex(),
                }
            )
        )
        return 0 if matched else 1
    except (ValueError, KafkaException, TimeoutError):
        print(json.dumps({"status": "failed", "reason": "uuid_verification_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
