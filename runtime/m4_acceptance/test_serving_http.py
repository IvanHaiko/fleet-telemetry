# ruff: noqa: I001, E501, B023
# Preserve frozen imports, literal expectations and synchronous callbacks.
"""Public stdlib HTTP mocks; no candidate helpers or live service."""

import base64
import copy
import importlib
import json
import re
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit


COLUMNS = [
    ("projection_version", "String"),
    ("dataset_run_id", "String"),
    ("pipeline_version", "String"),
    ("event_id", "String"),
    ("vehicle_id", "String"),
    ("source_timestamp", "DateTime64(6, 'UTC')"),
    ("voltage_v", "Decimal(18, 6)"),
    ("current_a", "Nullable(Decimal(18, 6))"),
    ("remaining_fraction", "Nullable(Decimal(18, 6))"),
    ("quality_flags", "Array(String)"),
    ("semantic_json", "String"),
    ("source_dataset_run_id", "String"),
    ("source_job_sha256", "String"),
    ("archive_descriptor_sha256", "String"),
]


def metadata(rows, sql):
    if re.search(r"\bFORMAT\s+JSONEachRow\b", sql, re.I):
        return b"".join((json.dumps(row) + "\n").encode() for row in rows)
    return json.dumps({"data": rows}).encode()


class Response:
    def __init__(self, body=b"", status=200, failure=None):
        self.status = status
        self.body = body
        self.failure = failure
        self.closed = False
        self.sizes = []

    def read(self, size):
        if not isinstance(size, int) or size <= 0:
            raise AssertionError("response read must be positively bounded")
        self.sizes.append(size)
        if self.failure is not None:
            raise self.failure
        result, self.body = self.body[:size], self.body[size:]
        return result

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, harness):
        self.harness = harness
        self.closed = False
        self.record = None

    def request(self, method, url, body=None, headers=None, **kwargs):
        self.record = (method, url, body, headers or {})
        self.harness.requests.append(self.record)
        if self.harness.request_failure is not None:
            raise self.harness.request_failure

    def getresponse(self):
        sql = self.harness.sql(self.record)
        if "system.columns" in sql:
            body = metadata(self.harness.columns, sql)
        elif "system.tables" in sql:
            body = metadata(self.harness.tables, sql)
        else:
            body = self.harness.body
        response = Response(body, self.harness.status, self.harness.read_failure)
        self.harness.responses.append(response)
        return response

    def close(self):
        self.closed = True


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.connections = []
        self.responses = []
        self.body = b""
        self.status = 200
        self.request_failure = None
        self.read_failure = None
        self.columns = [
            {
                "name": name,
                "type": kind,
                "position": position,
                "default_kind": "",
                "default_expression": "",
            }
            for position, (name, kind) in enumerate(COLUMNS, 1)
        ]
        self.tables = [
            {
                "engine": "MergeTree",
                "sorting_key": "dataset_run_id, pipeline_version, event_id",
                "partition_key": "",
                "create_table_query": (
                    "CREATE TABLE facts.serving_events_v1 ("
                    + ", ".join(name + " " + kind for name, kind in COLUMNS)
                    + ") ENGINE = MergeTree ORDER BY "
                    "(dataset_run_id, pipeline_version, event_id)"
                ),
            }
        ]
        # Patch before import also supports a public imported HTTPConnection alias.
        self.patch = mock.patch("http.client.HTTPConnection", side_effect=self.connect)
        self.factory = self.patch.start()
        self.addCleanup(self.patch.stop)
        self.transport = importlib.import_module("runtime.clickhouse.transport")
        self.sink = importlib.import_module("telemetry.serving_sink")
        self.config = self.transport.HttpConfig(8123, "facts", "reader", "sëcret")
        self.writer = self.transport.HttpWriter(self.config)
        self.reader = self.transport.HttpReader(self.config)

    def connect(self, *args, **kwargs):
        host = args[0] if args else kwargs.get("host")
        port = args[1] if len(args) > 1 else kwargs.get("port")
        timeout = args[2] if len(args) > 2 else kwargs.get("timeout")
        self.assertEqual((host, port, timeout), ("127.0.0.1", 8123, 5))
        connection = Connection(self)
        self.connections.append(connection)
        return connection

    @staticmethod
    def params(record):
        return parse_qs(urlsplit(record[1]).query, keep_blank_values=True)

    @classmethod
    def sql(cls, record):
        query = cls.params(record).get("query")
        if query:
            return query[0]
        body = record[2] or b""
        return body.decode() if isinstance(body, bytes) else body

    def error(self, category, field, operation):
        with self.assertRaises(self.sink.SinkError) as caught:
            operation()
        self.assertEqual(
            (caught.exception.category, caught.exception.field), (category, field)
        )
        self.assertNotIn("sëcret", str(caught.exception))

    def closed(self):
        self.assertTrue(all(connection.closed for connection in self.connections))

    def test_config_validation_and_pre_socket_body_validation(self):
        self.assertNotIn("sëcret", repr(self.config))
        valid = dict(
            port=8123,
            database="facts",
            user="reader",
            password="sëcret",
            timeout_seconds=5,
        )
        for field, values in {
            "port": [True, 0, 65536, 8123.0],
            "timeout_seconds": [True, 0, 16, 5.0],
            "database": ["bad.name", "x;DROP", "", "a" * 65, None],
            "user": ["a:b", "a\n", "1user", None],
            "password": ["", "x\r", "x\n", "x\x00", "é" * 129, None],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.error(
                        "invalid_config",
                        "config",
                        lambda: self.transport.HttpConfig(
                            **dict(valid, **{field: value})
                        ),
                    )
        for body in ("{}\n", bytearray(b"{}\n"), None):
            self.error("invalid_response", "rows", lambda: self.writer.write(body))
        self.error("limit_exceeded", "body", lambda: self.writer.write(b"x" * 8388609))
        self.factory.assert_not_called()

    def test_direct_insert_auth_settings_and_no_retry(self):
        body = b'{"vehicle_id":"value-stays-in-body"}\n'
        with mock.patch.dict(
            "os.environ",
            {
                "HTTP_PROXY": "http://invalid-proxy:1",
                "http_proxy": "http://invalid:1",
            },
        ):
            self.writer.write(body)
        self.assertEqual(len(self.requests), 1)
        method, url, sent, headers = self.requests[0]
        self.assertEqual(method, "POST")
        self.assertEqual(sent, body)
        self.assertFalse(urlsplit(url).netloc)
        self.assertNotIn("sëcret", url)
        self.assertNotIn("value-stays-in-body", self.sql(self.requests[0]))
        auth = {key.lower(): value for key, value in headers.items()}["authorization"]
        self.assertEqual(
            auth, "Basic " + base64.b64encode("reader:sëcret".encode()).decode()
        )
        sql = self.sql(self.requests[0])
        self.assertRegex(sql, r"(?i)INSERT\s+INTO\s+`?facts`?\.`?serving_events_v1`?")
        match = re.search(r"\(([^)]+)\)", sql)
        self.assertIsNotNone(match)
        self.assertEqual(
            [part.strip().strip("`") for part in match[1].split(",")],
            [name for name, _ in COLUMNS],
        )
        self.assertRegex(sql, r"(?i)FORMAT\s+JSONEachRow")
        parameters = self.params(self.requests[0])
        for key, value in {
            "async_insert": "0",
            "insert_deduplicate": "0",
            "date_time_input_format": "best_effort",
            "input_format_skip_unknown_fields": "0",
        }.items():
            in_sql = re.search(r"\b" + key + r"\s*=\s*'?" + value + r"'?", sql)
            self.assertTrue(parameters.get(key) == [value] or in_sql, key)
        self.closed()
        for status, category, field in (
            (302, "write_ambiguous", "write"),
            (500, "write_ambiguous", "write"),
            (401, "permission_denied", "sink"),
            (403, "permission_denied", "sink"),
        ):
            before = len(self.requests)
            self.status = status
            self.error(category, field, lambda: self.writer.write(body))
            self.assertEqual(len(self.requests), before + 1)
            self.closed()

    def test_metadata_semantics_and_scoped_bounded_select(self):
        self.reader.check_schema()
        sqls = [self.sql(record) for record in self.requests]
        self.assertTrue(any("system.columns" in sql for sql in sqls))
        self.assertTrue(any("system.tables" in sql for sql in sqls))
        for sql in sqls:
            self.assertNotRegex(sql, r"(?i)\b(ALTER|CREATE|DROP|INSERT)\b")
        original_columns = copy.deepcopy(self.columns)
        original_tables = copy.deepcopy(self.tables)
        mutations = [
            ("column", "type", "Float64"),
            ("column", "position", 99),
            ("column", "name", "wrong"),
            ("column", "default_kind", "DEFAULT"),
            ("column", "default_expression", "'invented'"),
            ("table", "engine", "ReplacingMergeTree"),
            ("table", "sorting_key", "dataset_run_id, event_id, pipeline_version"),
            ("table", "partition_key", "dataset_run_id"),
            (
                "table",
                "create_table_query",
                original_tables[0]["create_table_query"]
                + " TTL source_timestamp + INTERVAL 1 DAY",
            ),
        ]
        for target, key, value in mutations:
            self.columns = copy.deepcopy(original_columns)
            self.tables = copy.deepcopy(original_tables)
            (self.columns if target == "column" else self.tables)[0][key] = value
            with self.subTest(target=target, key=key):
                self.error("schema_mismatch", "schema", self.reader.check_schema)
        self.columns, self.tables = original_columns, original_tables
        from telemetry.serving_projection import ServingScope

        self.body = b'{"opaque":"response passed to coordinator"}\n'
        start = len(self.requests)
        result = self.reader.read(ServingScope("target-run", "pipe-v2"))
        self.assertEqual(result, self.body)
        self.assertEqual(len(self.requests), start + 1)
        record = self.requests[-1]
        sql, parameters = self.sql(record), self.params(record)
        self.assertRegex(sql, r"(?i)SELECT\s+DISTINCT\b")
        self.assertRegex(sql, r"(?i)\bLIMIT\s+65\b")
        self.assertNotRegex(sql, r"(?i)\bFINAL\b")
        for name, _ in COLUMNS:
            self.assertRegex(sql, r"\b" + name + r"\b")
        for name in ("voltage_v", "current_a", "remaining_fraction"):
            self.assertRegex(
                sql, r"(?i)toDecimalString\s*\(\s*`?" + name + r"`?\s*,\s*6\s*\)"
            )
        self.assertIn("formatDateTime", sql)
        self.assertIn("%f", sql)
        self.assertIn("UTC", sql)
        for field, value in (
            ("dataset_run_id", "target-run"),
            ("pipeline_version", "pipe-v2"),
        ):
            self.assertNotIn(value, sql)
            match = re.search(
                r"\{(\w+)\s*:\s*String\}",
                sql[sql.index(field, sql.upper().index("WHERE")) :],
            )
            self.assertIsNotNone(match)
            self.assertEqual(parameters.get("param_" + match[1]), [value])
        for key, value in {
            "wait_end_of_query": "1",
            "max_execution_time": "10",
            "max_threads": "1",
            "max_memory_usage": "268435456",
            "max_rows_to_read": "4096",
            "read_overflow_mode": "throw",
            "max_bytes_to_read": "16777216",
        }.items():
            in_sql = re.search(r"\b" + key + r"\s*=\s*'?" + value + r"'?", sql)
            self.assertTrue(parameters.get(key) == [value] or in_sql, key)
        self.closed()

    def test_bounded_bodies_network_errors_and_malformed_metadata(self):
        from telemetry.serving_projection import ServingScope

        scope = ServingScope("target", "pipeline")
        for port, operation, category, field in (
            ("write", lambda: self.writer.write(b"{}\n"), "write_ambiguous", "write"),
            ("read", lambda: self.reader.read(scope), "limit_exceeded", "rows"),
        ):
            self.body = b"x" * 8388609
            with self.subTest(port=port):
                self.error(category, field, operation)
                self.closed()
        self.body = b""
        for failure in (TimeoutError(), OSError()):
            for attribute in ("request_failure", "read_failure"):
                setattr(self, attribute, failure)
                before = len(self.requests)
                self.error(
                    "write_ambiguous", "write", lambda: self.writer.write(b"{}\n")
                )
                self.assertEqual(len(self.requests), before + 1)
                self.error("sink_unavailable", "read", lambda: self.reader.read(scope))
                self.closed()
                setattr(self, attribute, None)
        for status, category, field in (
            (302, "sink_unavailable", "read"),
            (500, "sink_unavailable", "read"),
            (401, "permission_denied", "sink"),
            (403, "permission_denied", "sink"),
        ):
            self.status = status
            before = len(self.requests)
            self.error(category, field, lambda: self.reader.read(scope))
            self.assertEqual(len(self.requests), before + 1)
            self.closed()
        self.status = 200
        for columns in (
            [],
            self.columns[:-1],
            self.columns + [self.columns[0]],
            [{"name": "projection_version"}],
        ):
            self.columns = columns
            self.error("schema_mismatch", "schema", self.reader.check_schema)
        # Malformed JSON rather than malformed-but-decodable metadata.
        for body in (b"{", b"{}", b"", b'{"data":null}'):
            with mock.patch.object(
                Connection, "getresponse", return_value=Response(body)
            ):
                self.error("schema_mismatch", "schema", self.reader.check_schema)
        self.closed()


if __name__ == "__main__":
    unittest.main()
