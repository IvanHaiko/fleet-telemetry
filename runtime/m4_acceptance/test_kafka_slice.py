"""Independent public-port tests; no Kafka SDK or candidate-generated fixtures."""

import copy
import dataclasses
import math
import unittest
from unittest import mock

from runtime.kafka_archive.reader import read_slice
from runtime.kafka_archive.types import SourceInfo

SOURCE = {
    "cluster_id": "fixture-cluster",
    "topic_id": "12345678-1234-4234-8234-123456789abc",
    "topic": "slice-fixture",
    "partition": 0,
}
# Literal base64 expectations: AP8= is bytes 00 ff; /wA= is ff 00.
ROWS = (
    {
        "format_version": "kafka-observation-v1",
        **SOURCE,
        "offset": 40,
        "timestamp_ms": -1,
        "timestamp_type": "create_time",
        "key_b64": None,
        "value_b64": "AP8=",
        "headers": [
            {"name_utf8": "trace", "value_b64": None},
            {"name_utf8": "trace", "value_b64": ""},
            {"name_utf8": "é", "value_b64": "/wA="},
        ],
        "measurement": None,
    },
    {
        "format_version": "kafka-observation-v1",
        **SOURCE,
        "offset": 41,
        "timestamp_ms": 9223372036854775807,
        "timestamp_type": "log_append_time",
        "key_b64": "",
        "value_b64": None,
        "headers": [],
        "measurement": None,
    },
    {
        "format_version": "kafka-observation-v1",
        **SOURCE,
        "offset": 42,
        "timestamp_ms": None,
        "timestamp_type": "not_available",
        "key_b64": "/wA=",
        "value_b64": "",
        "headers": [],
        "measurement": None,
    },
    {
        "format_version": "kafka-observation-v1",
        **SOURCE,
        "offset": 43,
        "timestamp_ms": 0,
        "timestamp_type": "create_time",
        "key_b64": None,
        "value_b64": "AP8=",
        "headers": [],
        "measurement": None,
    },
)


def info(**changes):
    fields = dict(
        source=copy.deepcopy(SOURCE), low=40, high=44, committed=40, delete_only=True
    )
    fields.update(changes)
    return SourceInfo(**fields)


class Client:
    """Only the documented port; effects/errors are scripted at call boundaries."""

    def __init__(self, rows=None, inspections=None, assignments=None, hook=None):
        self.rows = iter(copy.deepcopy(ROWS) if rows is None else rows)
        self.inspections = iter(inspections or [info(), info()])
        self.assignments = iter(assignments or [True, True, True, True, True, True])
        self.calls = []
        self.hook = hook

    def call(self, name, argument=None):
        self.calls.append((name, argument))
        if self.hook:
            self.hook(name)

    @staticmethod
    def resolve(value):
        if isinstance(value, Exception):
            raise value
        return value

    def inspect(self, timeout):
        self.call("inspect", timeout)
        return self.resolve(next(self.inspections))

    def assign(self, start):
        self.call("assign", start)

    def poll(self, timeout):
        self.call("poll", timeout)
        return self.resolve(next(self.rows, None))

    def assigned(self):
        self.call("assigned")
        return self.resolve(next(self.assignments, True))


class SliceTests(unittest.TestCase):
    def reject(self, client, diagnostic=None, **kwargs):
        # A failed call must raise, never return a prefix of the observations.
        with self.assertRaises(Exception) as caught:
            read_slice(
                client,
                kwargs.pop("source", copy.deepcopy(SOURCE)),
                kwargs.pop("start", 40),
                kwargs.pop("next_offset", 44),
                **kwargs,
            )
        error = caught.exception
        self.assertEqual(type(error).__name__, "ArchiveError")
        if diagnostic:
            self.assertEqual((error.category, error.field), diagnostic)
        return error

    def test_lossless_complete_result_progress_endpoints_and_frozen_source(self):
        positional = SourceInfo(copy.deepcopy(SOURCE), 40, 44, 40, True)
        self.assertEqual(positional, info())
        self.assertTrue(dataclasses.is_dataclass(positional))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            positional.low = 39
        for committed in (40, 44):
            with self.subTest(committed=committed):
                source = copy.deepcopy(SOURCE)

                def change_caller_source(name):
                    if name == "assign":
                        source["topic"] = "changed-after-preflight"  # noqa: B023

                client = Client(
                    inspections=[
                        info(committed=committed),
                        info(committed=committed, high=99),
                    ],
                    hook=change_caller_source,
                )
                result = read_slice(client, source, 40, 44, timeout_seconds=3)
                self.assertIsInstance(result, tuple)
                self.assertEqual(result, ROWS)
                names = [name for name, _ in client.calls]
                self.assertEqual(names.count("inspect"), 2)
                self.assertEqual(names.count("poll"), 4)
                self.assertEqual(
                    [arg for name, arg in client.calls if name == "assign"], [40]
                )
                self.assertLess(names.index("inspect"), names.index("assign"))
                self.assertGreater(names.index("assigned"), names.index("assign"))
                for name, timeout in client.calls:
                    if name in ("inspect", "poll"):
                        self.assertGreater(timeout, 0)
                        self.assertLessEqual(timeout, 3)

    def test_input_refused_before_any_port_operation(self):
        cases = [dict(start=x) for x in (True, -1, 40.0, "40")]
        cases += [dict(next_offset=x) for x in (False, 40, 39, 73, 2**63)]
        cases += [
            dict(timeout_seconds=x)
            for x in (True, False, 0, -1, 120.001, math.inf, -math.inf, math.nan)
        ]
        for source in (
            {},
            {**SOURCE, "extra": 0},
            {**SOURCE, "partition": True},
            {**SOURCE, "partition": 1},
            {**SOURCE, "topic": ""},
            {k: v for k, v in SOURCE.items() if k != "topic_id"},
        ):
            cases.append(dict(source=source))
        for arguments in cases:
            with self.subTest(arguments=arguments):
                client = Client()
                self.reject(client, **arguments)
                self.assertEqual(client.calls, [])
        # Inclusive admission boundaries and a second codec group (>16 rows).
        for start, end in ((40, 72), (2**63 - 2, 2**63 - 1)):
            rows = [dict(copy.deepcopy(ROWS[0]), offset=n) for n in range(start, end)]
            client = Client(
                rows,
                [
                    info(low=start, high=end, committed=start),
                    info(low=start, high=end, committed=start),
                ],
            )
            self.assertEqual(
                read_slice(client, SOURCE, start, end, timeout_seconds=120), tuple(rows)
            )

    def test_preflight_and_final_snapshot_invariants(self):
        scenarios = [
            (dict(committed=None), ("progress_mismatch", "committed")),
            (dict(committed=41), ("progress_mismatch", "committed")),
            (dict(committed=45), ("progress_mismatch", "committed")),
            (dict(committed=39), ("progress_mismatch", "committed")),
            (dict(low=41), ("source_gap", "retention")),
            (dict(high=43), ("source_gap", "retention")),
            (dict(delete_only=False), ("unsupported_profile", "cleanup_policy")),
        ]
        for field, value in (
            ("cluster_id", "other"),
            ("topic_id", "other"),
            ("topic", "other"),
            ("partition", 1),
        ):
            scenarios.append(
                (dict(source={**SOURCE, field: value}), ("source_identity", "source"))
            )
        for changes, diagnostic in scenarios:
            for final in (False, True):
                with self.subTest(changes=changes, final=final):
                    inspections = (
                        [info(), info(**changes)] if final else [info(**changes)]
                    )
                    client = Client(inspections=inspections)
                    self.reject(client, diagnostic)
                    if not final:
                        self.assertEqual([n for n, _ in client.calls], ["inspect"])
        # Even an otherwise admissible S -> U progress change is forbidden.
        self.reject(
            Client(inspections=[info(), info(committed=44)]),
            ("progress_mismatch", "committed"),
        )
        for assignments in ([False], [True, False]):
            self.reject(
                Client(assignments=assignments), ("unsupported_profile", "assignment")
            )

    def test_exact_offsets_and_full_observation_schema(self):
        for offset in (39, 40, 42, 44):
            rows = [copy.deepcopy(ROWS[0]), dict(ROWS[1], offset=offset)]
            with self.subTest(offset=offset):
                self.reject(Client(rows), ("source_gap", "offset"))
        for field in SOURCE:
            row = dict(ROWS[1], **{field: "other" if field != "partition" else 1})
            self.reject(Client([ROWS[0], row]), ("source_identity", "source"))
        invalid = [
            dict(value_b64="AP9="),
            dict(key_b64="?"),
            dict(timestamp_ms=None),
            dict(timestamp_type="unknown"),
            dict(timestamp_ms=True),
            dict(timestamp_ms=2**63),
            dict(measurement={"event_id": "unlinked"}),
            dict(format_version="future"),
            dict(extra="unknown"),
            dict(headers=[{"name_utf8": "x", "value_b64": None}] * 33),
            dict(headers=[{"name_utf8": "é" * 129, "value_b64": ""}]),
            dict(headers=[{"name_utf8": "\ud800", "value_b64": ""}]),
            dict(value_b64="AAAA" * 90000),
        ]
        for changes in invalid:
            with self.subTest(fields=list(changes)):
                self.reject(Client([ROWS[0], dict(ROWS[1], **changes)]))

    def test_deadline_none_polls_and_safe_failure_translation(self):
        client = Client(rows=[None, ROWS[0], None, *ROWS[1:]])
        self.assertEqual(read_slice(client, SOURCE, 40, 44), ROWS)
        ticks = iter(n / 10 for n in range(1000))
        with mock.patch("time.monotonic", side_effect=lambda: next(ticks)):
            client = Client(rows=[])
            self.reject(client, ("deadline_exceeded", "source"), timeout_seconds=1)
        self.assertLessEqual(sum(n == "poll" for n, _ in client.calls), 10)
        for name, timeout in client.calls:
            if name in ("inspect", "poll"):
                self.assertGreater(timeout, 0)
                self.assertLessEqual(timeout, 1)
        secret = "SECRET-payload-credential-header"
        for exception, category in (
            (PermissionError, "permission_denied"),
            (TimeoutError, "deadline_exceeded"),
            (OSError, "source_unavailable"),
        ):
            for stage in ("inspect", "assign", "assigned", "poll", "final"):
                with self.subTest(exception=exception, stage=stage):

                    def fail(name):
                        if name == stage:  # noqa: B023
                            raise exception(secret)  # noqa: B023

                    client = Client(
                        hook=fail if stage != "final" else None,
                        inspections=[info(), exception(secret)],
                    )
                    if stage == "poll":
                        client.hook = None
                        client.rows = iter([ROWS[0], exception(secret)])
                    error = self.reject(client, (category, "source"))
                    self.assertNotIn(secret, str(error))
                    self.assertNotIn(secret, repr(error))
        # Programming errors are not disguised as availability failures.
        bug = RuntimeError("programming bug")
        with self.assertRaises(RuntimeError) as caught:
            read_slice(Client(rows=[ROWS[0], bug]), SOURCE, 40, 44)
        self.assertIs(caught.exception, bug)


if __name__ == "__main__":
    unittest.main()
