"""Independent public-contract tests; no candidate is needed to compile this file."""

import copy
import json
import unittest

from telemetry.archive_codec import (
    ArchiveError,
    decode_observations,
    encode_observations,
    reconcile_coverage,
)

SOURCE = dict(cluster_id="cluster", topic_id="uuid", topic="topic", partition=0)
MARKER = "PRIVATE_MARKER_7d96"
LINK = dict(event_id="sha256:" + "a" * 64, source_manifest_sha256="sha256:" + "b" * 64)
LITERAL = (
    b'{"cluster_id":"cluster","format_version":"kafka-observation-v1",'
    b'"headers":[{"name_utf8":"trace","value_b64":null},'
    b'{"name_utf8":"trace","value_b64":""}],"key_b64":null,'
    b'"measurement":null,"offset":40,"partition":0,"timestamp_ms":null,'
    b'"timestamp_type":"not_available","topic":"topic","topic_id":"uuid",'
    b'"value_b64":"AP8="}\n'
)


def row(offset=40, **changes):
    result = dict(
        SOURCE,
        format_version="kafka-observation-v1",
        offset=offset,
        timestamp_ms=None,
        timestamp_type="not_available",
        key_b64=None,
        value_b64="AP8=",
        measurement=None,
        headers=[
            dict(name_utf8="trace", value_b64=None),
            dict(name_utf8="trace", value_b64=""),
        ],
    )
    result.update(changes)
    return result


def wire(value):
    """Construct malformed vectors; LITERAL is the independent positive oracle."""
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


class ArchiveCodecTests(unittest.TestCase):
    def refused(self, category, function, *args):
        before = copy.deepcopy(args)
        with self.assertRaises(ArchiveError) as caught:
            function(*args)
        error = caught.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.category, category)
        self.assertIsInstance(error.field, str)
        self.assertTrue(error.field)
        for diagnostic in (str(error), repr(error), error.category, error.field):
            self.assertNotIn(MARKER, diagnostic)
        self.assertEqual(args, before)

    def invalid_row(self, value, category="invalid_format"):
        self.refused(category, encode_observations, [value])
        self.refused(category, decode_observations, wire(value))

    def test_literal_complete_observation_and_owned_results(self):
        original = [row()]
        snapshot = copy.deepcopy(original)
        self.assertEqual(encode_observations(original), LITERAL)
        decoded = decode_observations(LITERAL)
        self.assertIsInstance(decoded, tuple)
        self.assertEqual(decoded, (row(),))
        self.assertIsInstance(decoded[0], dict)
        decoded[0]["headers"][0]["name_utf8"] = "changed"
        self.assertEqual(decode_observations(LITERAL), (row(),))
        self.assertEqual(original, snapshot)
        for key, value in (("", None), (None, None), ("AP8=", "")):
            item = row(key_b64=key, value_b64=value)
            self.assertEqual(decode_observations(encode_observations([item])), (item,))

    def test_schema_and_link_syntax_only(self):
        # Binary AP8= is not event JSON; no event/manifest admission is required.
        item = row(measurement=LINK)
        self.assertEqual(decode_observations(encode_observations([item])), (item,))
        malformed = [
            dict(row(), extra=MARKER),
            row(headers={}),
            row(headers=[dict(name_utf8="x", value_b64=None, x=MARKER)]),
            row(measurement=dict(LINK, extra=MARKER)),
            row(measurement={"event_id": LINK["event_id"]}),
            row(measurement=dict(LINK, event_id="sha256:" + "A" * 64)),
            row(measurement=dict(LINK, source_manifest_sha256=MARKER)),
        ]
        for field in row():
            item = row()
            del item[field]
            malformed.append(item)
        for item in malformed:
            with self.subTest(item=item):
                self.invalid_row(item)
        self.invalid_row(row(format_version="future"), "unsupported_profile")

    def test_base64(self):
        for value in ("AP9=", "AP8", "AP8==", "AP8=\n", "-_8=", "====", 1):
            for field in ("key_b64", "value_b64"):
                with self.subTest(value=value, field=field):
                    self.invalid_row(row(**{field: value}))
            self.invalid_row(row(headers=[dict(name_utf8="", value_b64=value)]))

    def test_integer_timestamp_and_identity_rules(self):
        for changes in (
            dict(partition=-1),
            dict(partition=2**31),
            dict(offset=-1),
            dict(offset=2**63),
            dict(timestamp_ms=2**63, timestamp_type="create_time"),
            dict(timestamp_ms=-(2**63) - 1, timestamp_type="create_time"),
            dict(timestamp_ms=0),
            dict(timestamp_type="create_time"),
            dict(timestamp_type="other"),
        ):
            self.invalid_row(row(**changes))
        for field in ("partition", "offset", "timestamp_ms"):
            for value in (True, False, 1.0, "1"):
                changes = {field: value}
                if field == "timestamp_ms":
                    changes["timestamp_type"] = "create_time"
                self.invalid_row(row(**changes))
        for field in ("cluster_id", "topic_id", "topic"):
            for value in ("", None, "\ud800"):
                self.invalid_row(row(**{field: value}))
        for timestamp in (-(2**63), 2**63 - 1):
            for kind in ("create_time", "log_append_time"):
                item = row(
                    partition=2**31 - 1,
                    offset=2**63 - 1,
                    timestamp_ms=timestamp,
                    timestamp_type=kind,
                )
                self.assertEqual(
                    decode_observations(encode_observations([item])), (item,)
                )

    def test_canonical_decode_refusals(self):
        vectors = [
            b"",
            bytearray(LITERAL),
            b"\xef\xbb\xbf" + LITERAL,
            LITERAL + b"\n",
            LITERAL[:-1],
            LITERAL.replace(b"\n", b"\r\n"),
            LITERAL.replace(b'":', b'": ', 1),
            LITERAL.replace(b'"offset":40', b'"offset":4e1'),
            LITERAL.replace(b'"offset":40', b'"offset":NaN'),
            LITERAL.replace(b'"offset":40', b'"offset":Infinity'),
            LITERAL.replace(b'"offset":40', b'"offset":40,"offset":40'),
            LITERAL.replace(b'"cluster_id":"cluster",', b"").replace(
                b'"headers":', b'"cluster_id":"cluster","headers":'
            ),
            LITERAL.replace(b'"cluster"', b'"clu\\u0073ter"'),
        ]
        for data in vectors:
            with self.subTest(data=data):
                self.refused("invalid_format", decode_observations, data)
        # Modest allocations probe recursion and integer digit admission.
        deep = b"[" * 17 + b"0" + b"]" * 17 + b"\n"
        self.refused("limit_exceeded", decode_observations, deep)
        self.refused(
            "invalid_format",
            decode_observations,
            LITERAL.replace(b'"offset":40', b'"offset":' + b"9" * 1000),
        )

    def test_string_and_header_bounds(self):
        for field in ("cluster_id", "topic_id", "topic"):
            item = row(**{field: "é" * 256})
            self.assertEqual(decode_observations(encode_observations([item])), (item,))
            self.invalid_row(row(**{field: "é" * 256 + "x"}), "limit_exceeded")
        headers = [dict(name_utf8="é" * 128, value_b64="")] * 32
        item = row(headers=headers)
        self.assertEqual(decode_observations(encode_observations([item])), (item,))
        self.invalid_row(row(headers=headers + headers[:1]), "limit_exceeded")
        self.invalid_row(
            row(headers=[dict(name_utf8="é" * 128 + "x", value_b64=None)]),
            "limit_exceeded",
        )
        self.invalid_row(row(headers=[dict(name_utf8="\ud800", value_b64=None)]))
        item = row(
            headers=[
                dict(name_utf8="", value_b64=None),
                dict(name_utf8="e\u0301", value_b64=""),
                dict(name_utf8="é", value_b64="AP8="),
            ]
        )
        self.assertEqual(decode_observations(encode_observations([item])), (item,))

    def test_batch_order_duplicates_and_sources(self):
        items = [row(42), row(40), row(41)]
        before = copy.deepcopy(items)
        encoded = encode_observations(items)
        self.assertEqual(
            [x["offset"] for x in decode_observations(encoded)], [40, 41, 42]
        )
        self.assertEqual(items, before)
        self.refused("invalid_format", encode_observations, [])
        self.refused("invalid_format", decode_observations, wire(row(41)) + LITERAL)
        self.refused("observation_conflict", encode_observations, [row(), row()])
        self.refused("observation_conflict", decode_observations, LITERAL * 2)
        for field in SOURCE:
            other = row(41, **{field: 1 if field == "partition" else MARKER})
            self.refused("lineage_mismatch", encode_observations, [row(), other])
            self.refused("lineage_mismatch", decode_observations, LITERAL + wire(other))

    def test_encoded_line_and_batch_limits(self):
        # Canonical base64 lengths are multiples of four; adjust an identity
        # by <=3 ASCII bytes to reach an exact encoded-byte boundary.
        def sized(offset, size):
            item = row(offset, value_b64="")
            remaining = size - len(wire(item))
            item["value_b64"] = "AAAA" * (remaining // 4)
            item["topic"] += "x" * (remaining % 4)
            self.assertEqual(len(wire(item)), size)
            return item

        exact = sized(40, 256 * 1024)
        self.assertEqual(encode_observations([exact]), wire(exact))
        self.assertEqual(decode_observations(wire(exact)), (exact,))
        too_big = sized(40, 256 * 1024 + 1)
        self.invalid_row(too_big, "limit_exceeded")
        batch = [dict(exact, offset=n) for n in range(40, 44)]
        data = b"".join(wire(x) for x in batch)
        self.assertEqual(len(data), 1024 * 1024)
        self.assertEqual(encode_observations(batch), data)
        self.assertEqual(decode_observations(data), tuple(batch))
        extra = row(44, topic=exact["topic"])
        self.refused("limit_exceeded", encode_observations, batch + [extra])
        self.refused("limit_exceeded", decode_observations, data + wire(extra))
        sixteen = [row(n) for n in range(16)]
        self.assertEqual(len(decode_observations(encode_observations(sixteen))), 16)
        self.refused("limit_exceeded", encode_observations, sixteen + [row(16)])
        self.refused(
            "limit_exceeded",
            decode_observations,
            b"".join(wire(row(n)) for n in range(17)),
        )

    def test_enumerated_union_overlap_and_repeated_measurements(self):
        a, b, c = (row(n, measurement=copy.deepcopy(LINK)) for n in (40, 41, 42))
        batches = [wire(b) + wire(c), wire(a) + wire(b), wire(b)]
        before = copy.deepcopy((batches, SOURCE))
        result = reconcile_coverage(batches, SOURCE, 40, 43)
        self.assertEqual(result.observations, (a, b, c))
        self.assertIsInstance(result.observations, tuple)
        self.assertEqual(result.overlap_count, 2)
        self.assertEqual(result.repeated_measurement_count, 2)
        self.assertEqual((batches, SOURCE), before)
        result.observations[0]["headers"][0]["name_utf8"] = "changed"
        again = reconcile_coverage(batches, SOURCE, 40, 43)
        self.assertEqual(again.observations, (a, b, c))
        plain = reconcile_coverage([LITERAL, LITERAL], SOURCE, 40, 41)
        self.assertEqual(
            (plain.overlap_count, plain.repeated_measurement_count), (1, 0)
        )
        self.assertEqual(plain.observations, (row(),))

    def test_union_gap_conflicts_and_lineage(self):
        self.refused(
            "coverage_gap", reconcile_coverage, [LITERAL, wire(row(42))], SOURCE, 40, 43
        )
        self.refused("coverage_gap", reconcile_coverage, [], SOURCE, 40, 41)
        for changed in (
            row(headers=list(reversed(row()["headers"]))),
            row(timestamp_ms=0, timestamp_type="create_time"),
        ):
            left = row(measurement=LINK)
            changed["measurement"] = copy.deepcopy(LINK)
            self.refused(
                "observation_conflict",
                reconcile_coverage,
                [wire(left), wire(changed)],
                SOURCE,
                40,
                41,
            )
        for field in SOURCE:
            source = dict(SOURCE, **{field: 1 if field == "partition" else MARKER})
            self.refused(
                "lineage_mismatch", reconcile_coverage, [LITERAL], source, 40, 41
            )
        self.refused(
            "lineage_mismatch",
            reconcile_coverage,
            [LITERAL, wire(row(41))],
            SOURCE,
            40,
            41,
        )
        self.refused(
            "invalid_format", reconcile_coverage, [LITERAL[:-1]], SOURCE, 40, 41
        )
        self.refused(
            "invalid_format",
            reconcile_coverage,
            [LITERAL],
            dict(SOURCE, extra=MARKER),
            40,
            41,
        )

    def test_coverage_limits_and_interval_types(self):
        batches = [b"".join(wire(row(n)) for n in range(s, s + 16)) for s in (0, 16)]
        result = reconcile_coverage(batches * 2, SOURCE, 0, 32)
        self.assertEqual([x["offset"] for x in result.observations], list(range(32)))
        self.assertEqual(result.overlap_count, 32)
        self.refused(
            "limit_exceeded",
            reconcile_coverage,
            batches * 2 + [wire(row(0))],
            SOURCE,
            0,
            32,
        )
        self.assertEqual(
            reconcile_coverage([LITERAL] * 16, SOURCE, 40, 41).overlap_count, 15
        )
        self.refused(
            "limit_exceeded", reconcile_coverage, [LITERAL] * 17, SOURCE, 40, 41
        )
        for start, end in ((0, 33), (0, 2**63)):
            self.refused("limit_exceeded", reconcile_coverage, [], SOURCE, start, end)
        for start, end in (
            (True, 41),
            (40, True),
            (40.0, 41),
            (40, 41.0),
            (-1, 1),
            (40, 40),
            (41, 40),
            (0, 2**63 + 1),
        ):
            self.refused("invalid_format", reconcile_coverage, [], SOURCE, start, end)
        last = row(2**63 - 1)
        self.assertEqual(
            reconcile_coverage([wire(last)], SOURCE, 2**63 - 1, 2**63).observations,
            (last,),
        )


if __name__ == "__main__":
    unittest.main()
