"""Direct loopback HTTP ports for the bounded versioned event table."""

import base64
import http.client
import re
from dataclasses import dataclass, field
from urllib.parse import urlencode

from telemetry.serving_projection import ServingError, ServingScope
from telemetry.serving_sink import COLUMNS, MAX_BODY_BYTES, SinkError, _json_object

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}", re.ASCII)
_SCOPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", re.ASCII)
_TYPES = (
    "String",
    "String",
    "String",
    "String",
    "String",
    "DateTime64(6, 'UTC')",
    "Decimal(18, 6)",
    "Nullable(Decimal(18, 6))",
    "Nullable(Decimal(18, 6))",
    "Array(String)",
    "String",
    "String",
    "String",
    "String",
)
_BOUNDS = (
    " SETTINGS max_execution_time=10, max_threads=1,"
    " max_memory_usage=268435456, max_rows_to_read=4096,"
    " read_overflow_mode='throw', max_bytes_to_read=16777216"
)


@dataclass(frozen=True)
class HttpConfig:
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    timeout_seconds: int = 5

    def __post_init__(self) -> None:
        valid = (
            type(self.port) is int
            and 1 <= self.port <= 65535
            and type(self.timeout_seconds) is int
            and 1 <= self.timeout_seconds <= 15
            and type(self.database) is str
            and _IDENTIFIER.fullmatch(self.database) is not None
            and type(self.user) is str
            and _IDENTIFIER.fullmatch(self.user) is not None
            and type(self.password) is str
            and bool(self.password)
            and not any(char in self.password for char in "\r\n\0")
        )
        try:
            valid = valid and len(self.password.encode("utf-8")) <= 256
        except UnicodeError:
            valid = False
        if not valid:
            raise SinkError("invalid_config", "config")


def _request(
    config: HttpConfig,
    sql: str,
    body: bytes,
    *,
    write: bool = False,
    parameters: dict[str, str] | None = None,
) -> bytes:
    query = {
        "query": sql,
        "wait_end_of_query": "1",
        "output_format_json_quote_64bit_integers": "0",
    }
    if parameters:
        query.update(parameters)
    category, location = (
        ("write_ambiguous", "write") if write else ("sink_unavailable", "read")
    )
    connection: http.client.HTTPConnection | None = None
    response: http.client.HTTPResponse | None = None
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", config.port, timeout=config.timeout_seconds
        )
        connection.request(
            "POST",
            "/?" + urlencode(query),
            body=body,
            headers={
                "Authorization": "Basic "
                + base64.b64encode(f"{config.user}:{config.password}".encode()).decode(
                    "ascii"
                ),
                "Content-Type": "application/octet-stream",
            },
        )
        response = connection.getresponse()
        if response.status in (401, 403):
            raise SinkError("permission_denied", "sink")
        if response.status != 200:
            raise SinkError(category, location)
        result = response.read(MAX_BODY_BYTES + 1)
        if len(result) > MAX_BODY_BYTES:
            if write:
                raise SinkError(category, location)
            raise SinkError("limit_exceeded", "rows")
        return result
    except PermissionError:
        raise SinkError("permission_denied", "sink") from None
    except (OSError, http.client.HTTPException, UnicodeError):
        raise SinkError(category, location) from None
    finally:
        try:
            if response is not None:
                response.close()
        finally:
            if connection is not None:
                connection.close()


class HttpWriter:
    def __init__(self, config: HttpConfig) -> None:
        self.config = config

    def write(self, body: bytes) -> None:
        if type(body) is not bytes:
            raise SinkError("invalid_response", "rows")
        if len(body) > MAX_BODY_BYTES:
            raise SinkError("limit_exceeded", "body")
        sql = (
            f"INSERT INTO {self.config.database}.serving_events_v1 "
            f"({', '.join(COLUMNS)}) SETTINGS async_insert=0, insert_deduplicate=0, "
            "date_time_input_format='best_effort', input_format_skip_unknown_fields=0 "
            "FORMAT JSONEachRow"
        )
        _request(self.config, sql, body, write=True)


def _metadata(body: bytes) -> list[dict[str, object]]:
    try:
        lines = body.decode("utf-8").split("\n")
        if lines[-1] == "":
            lines.pop()
        return [_json_object(line) for line in lines]
    except (ValueError, UnicodeError, RecursionError):
        raise SinkError("schema_mismatch", "schema") from None


def _type_text(value: str) -> str:
    # Only insignificant spaces outside quoted timezone literals normalize.
    return re.sub(r"\s*([(),])\s*", r"\1", value.strip())


class HttpReader:
    def __init__(self, config: HttpConfig) -> None:
        self.config = config

    def check_schema(self) -> None:
        parameters = {
            "param_database": self.config.database,
            "param_table": "serving_events_v1",
        }
        where = " WHERE database={database:String} AND "
        columns = _metadata(
            _request(
                self.config,
                "SELECT name, type, position, default_kind, default_expression "
                "FROM system.columns" + where + "table={table:String} "
                "ORDER BY position LIMIT 15" + _BOUNDS + " FORMAT JSONEachRow",
                b"",
                parameters=parameters,
            )
        )
        if len(columns) != len(COLUMNS):
            raise SinkError("schema_mismatch", "schema")
        for position, (column, name, kind) in enumerate(
            zip(columns, COLUMNS, _TYPES, strict=True), 1
        ):
            if (
                set(column)
                != {"name", "type", "position", "default_kind", "default_expression"}
                or column["name"] != name
                or type(column["position"]) is not int
                or column["position"] != position
                or column["default_kind"] != ""
                or column["default_expression"] != ""
                or not isinstance(column["type"], str)
            ):
                raise SinkError("schema_mismatch", "schema")
            if _type_text(column["type"]) != _type_text(kind):
                raise SinkError("schema_mismatch", "schema")
        tables = _metadata(
            _request(
                self.config,
                "SELECT engine, sorting_key, partition_key, create_table_query "
                "FROM system.tables"
                + where
                + "name={table:String} LIMIT 2"
                + _BOUNDS
                + " FORMAT JSONEachRow",
                b"",
                parameters=parameters,
            )
        )
        if len(tables) != 1:
            raise SinkError("schema_mismatch", "schema")
        table = tables[0]
        if (
            set(table)
            != {"engine", "sorting_key", "partition_key", "create_table_query"}
            or any(type(value) is not str for value in table.values())
            or table["engine"] != "MergeTree"
            or table["partition_key"] != ""
        ):
            raise SinkError("schema_mismatch", "schema")
        sorting = table["sorting_key"]
        create = table["create_table_query"]
        assert isinstance(sorting, str) and isinstance(create, str)
        # Ignore quoted identifiers/string literals before detecting TTL syntax.
        unquoted = re.sub(
            r"'(?:\\.|''|[^'])*'|`(?:``|[^`])*`|\"(?:\"\"|[^\"])*\"", "", create
        )
        if (
            _type_text(sorting) != "dataset_run_id,pipeline_version,event_id"
            or not create.strip()
            or re.search(r"\bTTL\b", unquoted, re.IGNORECASE)
        ):
            raise SinkError("schema_mismatch", "schema")

    def read(self, scope: ServingScope) -> bytes:
        if type(scope) is not ServingScope or any(
            type(value) is not str or _SCOPE.fullmatch(value) is None
            for value in (scope.dataset_run_id, scope.pipeline_version)
        ):
            raise ServingError("invalid_scope", "scope")
        expressions = []
        for name in COLUMNS:
            if name in ("voltage_v", "current_a", "remaining_fraction"):
                expressions.append(f"toDecimalString({name},6) AS {name}")
            elif name == "source_timestamp":
                expressions.append(
                    "formatDateTime(source_timestamp, '%Y-%m-%dT%H:%i:%S.%fZ', "
                    "'UTC') AS source_timestamp"
                )
            else:
                expressions.append(name)
        sql = (
            f"SELECT DISTINCT {', '.join(expressions)} "
            f"FROM {self.config.database}.serving_events_v1 "
            "WHERE dataset_run_id={run:String} AND pipeline_version={pipeline:String} "
            "LIMIT 65" + _BOUNDS + " FORMAT JSONEachRow"
        )
        return _request(
            self.config,
            sql,
            b"",
            parameters={
                "param_run": scope.dataset_run_id,
                "param_pipeline": scope.pipeline_version,
            },
        )
