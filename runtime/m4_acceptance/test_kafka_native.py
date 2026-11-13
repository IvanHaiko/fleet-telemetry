# ruff: noqa: E731
# Preserve the independently frozen literal encoder lambda.
"""Independent native port tests; no broker or confluent-kafka installation."""

import base64
import importlib
import math
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

SOURCE = dict(
    cluster_id="local", topic_id="/////////////////////w", topic="fixture", partition=0
)
SECRET = "native detail: credential=DO-NOT-LEAK"


class TP:
    def __init__(self, topic, partition, offset=-1001, error=None):
        self.topic, self.partition = topic, partition
        self.offset, self.error = offset, error


class Resource:
    def __init__(self, restype, name, **kwargs):
        self.restype, self.name = restype, name


class NativeError:
    _PARTITION_EOF = -191
    OFFSET_OUT_OF_RANGE = 1
    _AUTO_OFFSET_RESET = -140
    TOPIC_AUTHORIZATION_FAILED = 29
    GROUP_AUTHORIZATION_FAILED = 30
    CLUSTER_AUTHORIZATION_FAILED = 31
    _TIMED_OUT = -185
    _TRANSPORT = -195

    def __init__(self, code):
        self.number = code

    def code(self):
        return self.number

    def __str__(self):
        return SECRET


class NativeException(Exception):
    pass


def message(
    key=b"\x00\xff", value=b"\xff\x00", headers=None, timestamp=(1, 123), error=None
):
    return NS(
        topic=lambda: "fixture",
        partition=lambda: 0,
        offset=lambda: 40,
        key=lambda: key,
        value=lambda: value,
        headers=lambda: headers,
        timestamp=lambda: timestamp,
        error=lambda: error,
    )


class Boundary:
    """SDK-shaped data and futures; all forbidden methods remain observable."""

    def __init__(self):
        self.calls = []
        self.cluster = NS(
            cluster_id="local", nodes=[NS(id=1, host="127.0.0.1", port=19092)]
        )
        self.topic = NS(
            name="fixture",
            topic_id=SOURCE["topic_id"],
            partitions=[NS(id=0, leader=None, replicas=[], isr=[])],
        )
        self.config = {"cleanup.policy": NS(name="cleanup.policy", value="delete")}
        self.consumer = Mock()
        self.consumer.committed.return_value = [TP("fixture", 0, 40)]
        self.consumer.get_watermark_offsets.return_value = (0, 50)
        self.consumer.assignment.return_value = [TP("fixture", 0, 40)]
        self.consumer.poll.return_value = None
        for name in ("committed", "get_watermark_offsets", "poll"):
            method = getattr(self.consumer, name)

            def timed(*args, _name=name, _method=method, **kwargs):
                timeout = kwargs.get("timeout")
                if timeout is None and args and _name == "poll":
                    timeout = args[0]
                self.calls.append((_name, timeout))
                return _method.return_value

            method.side_effect = timed
        self.admin = Mock()
        self.admin.describe_cluster.side_effect = self.describe_cluster
        self.admin.describe_topics.side_effect = self.describe_topics
        self.admin.describe_configs.side_effect = self.describe_configs
        self.sdk = NS(
            TopicCollection=lambda names: NS(topic_names=names),
            Consumer=Mock(return_value=self.consumer),
            TopicPartition=TP,
            KafkaError=NativeError,
            KafkaException=NativeException,
            OFFSET_INVALID=-1001,
            TIMESTAMP_NOT_AVAILABLE=0,
            TIMESTAMP_CREATE_TIME=1,
            TIMESTAMP_LOG_APPEND_TIME=2,
            version=lambda: "2.16.0",
            libversion=lambda: ("2.16.0", 0x021000FF),
        )
        self.admin_sdk = NS(
            AdminClient=Mock(return_value=self.admin),
            ConfigResource=Resource,
            ResourceType=NS(TOPIC=2),
        )

    def future(self, value):
        def result(timeout=None):
            self.calls.append(("future", timeout))
            return value

        return NS(result=Mock(side_effect=result))

    def describe_cluster(self, **kwargs):
        self.calls.append(("cluster", kwargs.get("request_timeout")))
        return self.future(self.cluster)

    def describe_topics(self, topics, **kwargs):
        self.calls.append(("topics", kwargs.get("request_timeout")))
        return {"fixture": self.future(self.topic)}

    def describe_configs(self, resources, **kwargs):
        self.calls.append(("configs", kwargs.get("request_timeout")))
        return {r: self.future(self.config) for r in resources}


class NativePortTests(unittest.TestCase):
    def setUp(self):
        # Import the real public guard, never manufacture a native-local seam.
        self.compat = importlib.import_module("telemetry.kafka_compat")
        self.native = importlib.import_module("runtime.kafka_archive.native")
        self.boundary = Boundary()
        self.guard = self.enterContext(
            patch.object(self.compat, "require_uuid_boundary", return_value=None)
        )
        real_import = importlib.import_module

        def sdk_import(name, package=None):
            if name == "confluent_kafka":
                return self.boundary.sdk
            if name == "confluent_kafka.admin":
                return self.boundary.admin_sdk
            return real_import(name, package)

        self.imports = self.enterContext(
            patch("importlib.import_module", side_effect=sdk_import)
        )

    def client(self, source=None, endpoint="127.0.0.1:19092", group="m4-reader-test"):
        return self.native.NativeSliceClient(
            endpoint, group, SOURCE.copy() if source is None else source
        )

    def refusal(self, operation, category=None, field=None):
        with self.assertRaises(Exception) as caught:
            operation()
        exc = caught.exception
        self.assertEqual(type(exc).__name__, "ArchiveError")
        if category is not None:
            self.assertEqual(exc.category, category)
        if field is not None:
            self.assertEqual(exc.field, field)
        self.assertNotIn(SECRET, str(exc))
        return exc

    def assert_no_clients(self):
        self.boundary.sdk.Consumer.assert_not_called()
        self.boundary.admin_sdk.AdminClient.assert_not_called()

    def test_admission_order_and_repeated_guard(self):
        from telemetry.kafka_compat import KafkaCompatibilityError

        self.guard.side_effect = KafkaCompatibilityError(SECRET)
        self.refusal(self.client, "unsupported_profile", "source")
        self.assert_no_clients()
        self.assertFalse(
            any(
                c.args[0].startswith("confluent_kafka")
                for c in self.imports.call_args_list
            )
        )
        self.guard.side_effect = None
        a, b = self.client(), self.client()
        self.assertEqual(self.guard.call_count, 3)
        a.close()
        b.close()

    def test_invalid_inputs_and_platform_refuse_before_clients(self):
        cases = [
            dict(endpoint="localhost:19092"),
            dict(endpoint="127.0.0.1:9092"),
            dict(group="other"),
            dict(group="m4-reader-"),
            dict(group="m4-reader-" + "a" * 65),
            dict(source={**SOURCE, "partition": 1}),
            dict(source={**SOURCE, "partition": True}),
            dict(source={**SOURCE, "topic": ""}),
            dict(source={k: v for k, v in SOURCE.items() if k != "cluster_id"}),
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                self.refusal(lambda: self.client(**kwargs))  # noqa: B023 - invoked synchronously in this subtest
                self.assert_no_clients()
        for target, value in [
            ("platform.system", "Darwin"),
            ("platform.machine", "aarch64"),
            ("platform.python_implementation", "PyPy"),
        ]:
            with self.subTest(target=target), patch(target, return_value=value):
                self.refusal(self.client, "unsupported_profile", "source")
                self.assert_no_clients()

    def test_configuration_inspection_assignment_and_read_only_surface(self):
        client = self.client()
        cfg = self.boundary.sdk.Consumer.call_args.args[0]
        expected = {
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "auto.offset.reset": "error",
            "isolation.level": "read_committed",
            "enable.partition.eof": True,
            "allow.auto.create.topics": False,
        }
        for key, value in expected.items():
            self.assertEqual(cfg[key], value)
        self.assertGreater(cfg["queued.max.messages.kbytes"], 0)
        fetch_limits = [
            cfg[k] for k in ("fetch.message.max.bytes", "fetch.max.bytes") if k in cfg
        ]
        self.assertTrue(fetch_limits)
        self.assertTrue(all(isinstance(n, int) and n > 0 for n in fetch_limits))
        info = client.inspect(3)
        self.assertEqual(dict(info.source), SOURCE)
        self.assertEqual(
            (info.low, info.high, info.committed, info.delete_only), (0, 50, 40, True)
        )
        client.assign(40)
        parts = self.boundary.consumer.assign.call_args.args[0]
        self.assertEqual(
            [(p.topic, p.partition, p.offset) for p in parts], [("fixture", 0, 40)]
        )
        self.assertTrue(client.assigned())
        for assignment in (
            [],
            [TP("other", 0)],
            [TP("fixture", 1)],
            [TP("fixture", 0), TP("fixture", 1)],
        ):
            self.boundary.consumer.assignment.return_value = assignment
            self.assertFalse(client.assigned())
        client.close()
        forbidden = (
            "commit",
            "seek",
            "subscribe",
            "produce",
            "create_topics",
            "delete_topics",
            "alter_configs",
            "reset",
        )
        for name in forbidden:
            self.assertFalse(callable(getattr(client, name, None)), name)
            getattr(self.boundary.consumer, name).assert_not_called()
            getattr(self.boundary.admin, name).assert_not_called()

    def test_identity_uuid_profile_and_native_metadata_errors(self):
        # Standard base64 UUIDs retain all high bits, including '+' and '/'.
        for uuid in (SOURCE["topic_id"], "+////////////////////w"):
            with self.subTest(uuid=uuid):
                self.boundary.topic.topic_id = uuid
                client = self.client({**SOURCE, "topic_id": uuid})
                self.assertEqual(client.inspect(3).source["topic_id"], uuid)
                client.close()
        mutations = [
            lambda: setattr(self.boundary.topic, "topic_id", "A" * 22),
            lambda: setattr(self.boundary.topic, "topic_id", "bad!"),
            lambda: setattr(self.boundary.cluster, "cluster_id", "wrong"),
            lambda: setattr(self.boundary.cluster, "nodes", []),
            lambda: setattr(
                self.boundary.cluster, "nodes", [NS(host="remote", port=19092)]
            ),
            lambda: setattr(
                self.boundary.cluster, "nodes", [NS(host="127.0.0.1", port=9092)]
            ),
            lambda: setattr(self.boundary.topic, "partitions", [NS(id=1)]),
            lambda: setattr(self.boundary.topic, "partitions", [NS(id=0), NS(id=1)]),
            lambda: self.boundary.config.update(
                {"cleanup.policy": NS(value="compact,delete")}
            ),
            lambda: setattr(
                self.boundary.consumer.committed,
                "return_value",
                [TP("fixture", 0, 40, NativeError(29))],
            ),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.boundary = Boundary()
                client = self.client()
                mutate()
                self.refusal(lambda: client.inspect(3))  # noqa: B023 - invoked synchronously in this subtest
                client.close()

    def test_lossless_records_timestamps_and_invalid_headers(self):
        client = self.client()
        headers = [("tracé", None), ("tracé", b""), ("二", b"\x00\xff")]
        for key, value, stamp, kind, millis in [
            (b"\x00\xff", b"\xff\x00", (1, 123), "create_time", 123),
            (None, b"", (2, -123), "log_append_time", -123),
            (b"", None, (0, -1), "not_available", None),
        ]:
            with self.subTest(key=key, value=value):
                self.boundary.consumer.poll.return_value = message(
                    key, value, headers, stamp
                )
                row = client.poll(2)
                enc = lambda b: (
                    None if b is None else base64.b64encode(b).decode("ascii")
                )
                self.assertEqual(
                    dict(row),
                    dict(
                        SOURCE,
                        format_version="kafka-observation-v1",
                        offset=40,
                        timestamp_type=kind,
                        timestamp_ms=millis,
                        key_b64=enc(key),
                        value_b64=enc(value),
                        measurement=None,
                        headers=[
                            dict(name_utf8=n, value_b64=enc(v)) for n, v in headers
                        ],
                    ),
                )
        self.boundary.consumer.poll.return_value = None
        self.assertIsNone(client.poll(2))
        for headers in [[("\ud800", b"x")], [("bad\x00name", None)]]:
            self.boundary.consumer.poll.return_value = message(headers=headers)
            self.refusal(lambda: client.poll(2))
        client.close()

    def test_safe_errors_and_programming_errors(self):
        client = self.client()
        for code, category in [
            (NativeError._PARTITION_EOF, "source_gap"),
            (NativeError.OFFSET_OUT_OF_RANGE, "source_gap"),
            (NativeError._AUTO_OFFSET_RESET, "source_gap"),
            (29, "permission_denied"),
            (30, "permission_denied"),
            (31, "permission_denied"),
            (-195, "source_unavailable"),
        ]:
            with self.subTest(code=code):
                self.boundary.consumer.poll.return_value = message(
                    error=NativeError(code)
                )
                self.refusal(lambda: client.poll(2), category)
                self.boundary.consumer.poll.side_effect = NativeException(
                    NativeError(code)
                )
                self.refusal(lambda: client.poll(2), category)
                self.boundary.consumer.poll.side_effect = None
        for exc, category in [
            (PermissionError(SECRET), "permission_denied"),
            (TimeoutError(SECRET), "deadline_exceeded"),
            (OSError(SECRET), "source_unavailable"),
        ]:
            self.boundary.admin.describe_cluster.side_effect = exc
            self.refusal(lambda: client.inspect(2), category, "source")
        for operation, mock in [
            (lambda: client.inspect(2), self.boundary.admin.describe_cluster),
            (lambda: client.poll(2), self.boundary.consumer.poll),
        ]:
            mock.side_effect = TypeError("programming bug")
            with self.assertRaisesRegex(TypeError, "programming bug"):
                operation()
        client.close()

    def test_deadline_caps_sequential_budget_and_invalid_durations(self):
        client = self.client()
        for method in (client.inspect, client.poll):
            for duration in (0, -1, math.inf, -math.inf, math.nan):
                with self.subTest(method=method.__name__, duration=duration):
                    self.refusal(lambda: method(duration))  # noqa: B023 - invoked synchronously in this subtest
        self.boundary.calls.clear()
        # Each boundary consumes time; later calls must use what remains.
        ticks = iter(100 + i * 0.03 for i in range(1000))
        with patch("time.monotonic", side_effect=lambda: next(ticks)):
            client.inspect(2)
        timeouts = [timeout for _, timeout in self.boundary.calls]
        self.assertGreater(len(timeouts), 2)
        self.assertTrue(all(0 < t <= 2 for t in timeouts), timeouts)
        self.assertLess(timeouts[-1], timeouts[0])
        self.boundary.calls.clear()
        client.inspect(30)
        client.poll(30)
        self.assertTrue(all(0 < t <= 5 for _, t in self.boundary.calls))
        ticks = iter([100, 200] + [200] * 100)
        self.boundary.calls.clear()
        with patch("time.monotonic", side_effect=lambda: next(ticks)):
            self.refusal(lambda: client.inspect(1), "deadline_exceeded", "source")
        self.assertTrue(all(0 < t <= 1 for _, t in self.boundary.calls))
        client.close()


if __name__ == "__main__":
    unittest.main()
