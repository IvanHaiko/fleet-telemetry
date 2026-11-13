# Bounded canonical event sink interface

Status: bounded library interface, 2026-10-26. Admission is governed by
the recorded evidence and final acceptance receipt. The v2
formatter clarification replaces the original toString requirement after real
server readback evidence; original frozen v1 remains preserved. This refines
the admitted pure projection without changing it. Scope: event facts, one
versioned table and a
local HTTP library. No window/disposition inference, CLI runtime, offset commit,
shared deployment, continuous run sealing or full M4 acceptance is included.

## Schema and wire

`runtime/clickhouse/events-v1.sql` creates only `serving_events_v1`, without
IF NOT EXISTS, migrations, drops or old-table changes. Ordinary append-only
MergeTree, ORDER BY `(dataset_run_id, pipeline_version, event_id)`, no partition,
TTL, defaults, materialized columns or implicit identity replacement.

Columns, in exact order (standard ClickHouse canonical type spelling):

| Column | Type |
| --- | --- |
| projection_version | String |
| dataset_run_id | String |
| pipeline_version | String |
| event_id | String |
| vehicle_id | String |
| source_timestamp | DateTime64(6, 'UTC') |
| voltage_v | Decimal(18, 6) |
| current_a | Nullable(Decimal(18, 6)) |
| remaining_fraction | Nullable(Decimal(18, 6)) |
| quality_flags | Array(String) |
| semantic_json | String |
| source_dataset_run_id | String |
| source_job_sha256 | String |
| archive_descriptor_sha256 | String |

Every wire row has exactly these 14 fields, preserving the admitted projection.
projection_version is `serving-battery-exact6-v1`; numbers are quoted exact
six-place strings/null, flags a JSON array. source_timestamp remains canonical
six-digit UTC Z. JSONEachRow uses compact sorted object keys, ensure_ascii=False,
UTF-8 and one LF per row. The HTTP writer sets best_effort timestamp parsing;
live readback must prove exact microseconds. The schema has no eligibility field.

An event's logical key is run/pipeline/event_id. Content includes all lineage:
mixing descriptor roots or original jobs under the same key is a conflict.
Rebuilding a differently sealed archive into the same namespace is not an
automatic migration; use a separate explicit target run. Changed sink batch
boundaries with the same trusted descriptor are safe retries.

## Pure coordinator

`telemetry.serving_sink` exports:

- `SCHEMA_VERSION = 'serving-events-v1'`, `MAX_BODY_BYTES = 8388608`.
- `SinkError(category: str, field: str)`: fixed safe diagnostics only.
- Protocol `EventWriter.write(body: bytes) -> None`.
- Protocol `EventReader.check_schema() -> None`,
  `EventReader.read(scope: ServingScope) -> bytes`.
- Frozen `WriteReceipt(schema_version: str, scope: ServingScope,
  archive_descriptor_sha256: str, event_count: int, acknowledged_batches: int)`.
- `publish_archive(descriptor: bytes, expected_sha256: str, store: ReadStore,
  scope: ServingScope, writer: EventWriter, reader: EventReader,
  *, batch_size: int = 16) -> WriteReceipt`.

Validate exact integer batch_size in [1,64] before any port call; boolean invalid
raises `SinkError('invalid_batch_size','batch_size')`. Call the admitted
project_archive afresh, never accept a caller-forged ServingBatch. Existing
ServingError/ArchiveError propagate. Precompute the complete bounded wire before
writes; >8 MiB raises `SinkError('limit_exceeded','body')`. Validate the schema
before the first write. Write deterministic event-ID order in finite batches,
without automatic retries. After every successful write call, increment the
local acknowledgement count. This is not transactional progress.

On ambiguous write, stop immediately, do not call further writes or readback,
and do not return a receipt. The caller may retry the complete fresh projection
with changed batch_size. Propagate SinkError. Map PermissionError from any sink
port to `SinkError('permission_denied','sink')`; OSError/TimeoutError during write
to `SinkError('write_ambiguous','write')`, during schema/read to
`SinkError('sink_unavailable','read')`. Do not swallow programming exceptions.

Read the whole target scope through the reader after all writes. Empty projected
sets make zero writes but still require schema/read verification. Body is <=8 MiB,
at most64 JSONEachRow records, no blank interior lines, duplicate JSON keys,
nonfinite constants, malformed UTF-8 or non-object rows. Unknown/missing fields
or wrong types raise `SinkError('invalid_response','rows')`; oversized bodies or
>64 records raise `SinkError('limit_exceeded','rows')`. Every field is a string
except nullable current/remaining and list[str] flags. Compare entire rows exactly
against the trusted projection, including physical time and all lineage.
Identical repeated rows may collapse. Two contents under one event_id raise
`SinkError('sink_conflict','rows')`. Missing/extra/wrong content raises
`SinkError('reconciliation_failed','rows')`. No equal-count-only success.

Receipt returns only after successful exact reconciliation. It attests this
bounded observed write/read sequence, not future durability, atomic run sealing,
an end-to-end exactly-once effect or a persisted completion marker. The caller
must not concurrently mutate the namespace during this finite operation.

## Concrete local transport

`runtime.clickhouse.transport` exports frozen
`HttpConfig(port: int, database: str, user: str, password: str,
timeout_seconds: int = 5)` and classes `HttpWriter(config)`, `HttpReader(config)`
implementing the ports. Config construction validates before sockets: exact int
port1..65535 and timeout1..15; database/user plain strings matching
`[A-Za-z_][A-Za-z0-9_]{0,63}`; nonempty password plain string <=256 UTF-8 bytes,
no CR/LF/NUL. Invalid raises `SinkError('invalid_config','config')`. Password must
not appear in repr, errors, URL or returned data.

HTTP only at literal 127.0.0.1; no environment credentials, proxy discovery, DNS,
redirect following, TLS claims or package dependency. Use stdlib http.client
with explicit socket inactivity timeout. A trickling peer can outlive that
timeout: an enforced whole-command supervisor deadline is a later runtime gate.
Close owned connections on success/failure. Bound all full response bodies to
8 MiB with an extra-byte overflow check. No body, SQL values or credentials in
error messages. HTTP 401/403 maps to permission_denied/sink. Other non-200 read
responses and network/protocol failures map to sink_unavailable/read; write
responses/failures map to write_ambiguous/write. Never follow 3xx or retry.
An oversized HTTP response is write_ambiguous/write for writer and
limit_exceeded/rows for reader; malformed schema JSON is schema_mismatch/schema.

Writer POSTs exactly one synchronous INSERT into the fixed versioned table,
with explicit 14-column list, async_insert=0, insert_deduplicate=0,
date_time_input_format=best_effort and input_format_skip_unknown_fields=0.
SQL identifier database comes only from validated config; row values stay in
the body. Writer credentials need INSERT only, never SELECT/DDL/merge control.
Validate bytes type/size before sockets, invalid raises invalid_response/rows
or limit_exceeded/body. Direct write is a trusted low-level port; normal callers
must enter through publish_archive for fresh projection/admission.

Reader check_schema uses system.columns and system.tables read-only queries:
all exact names/types/order/default_kind/default_expression as above, engine
MergeTree, sorting key the three stated fields, empty partition key, no TTL.
Unknown/missing/extra columns or incompatible metadata raises
`SinkError('schema_mismatch','schema')`. Malformed metadata must fail safely.
Equivalent whitespace in sorting/type strings may normalize; semantic changes
must not be normalized away. No schema repair or DDL is performed.

Reader.read issues one scoped SELECT DISTINCT of all14 fields, including
toDecimalString(decimal columns, 6) and UTC formatDateTime with six microsecond digits.
Run/pipeline are typed query parameters, never SQL interpolation. LIMIT65 exposes
overflow to the coordinator; do not truncate to64. Set wait_end_of_query=1,
max_execution_time=10, max_threads=1, max_memory_usage=268435456,
max_rows_to_read=4096, read_overflow_mode=throw and max_bytes_to_read=16777216.
No FINAL/background-merge or finite insert-deduplication reliance. Credentials
need SELECT on the new table plus relevant system metadata, not INSERT/DDL.
Raw table access remains diagnostic; approved-query enforcement is a later gate.

## Required evidence and rollback

Independent restricted tests freeze before candidate exposure; reuse public Graph
fixtures, the admitted projection and existing tests. Cover original lineage,
exact wire/readback, schema-before-write, ambiguity/no retry, changed batching,
equal-count substitutions, conflicts, malformed/oversized responses, safe config
and bounded HTTP behavior using public http.client mocks (no private attributes).
Few combined methods, no duplicate archive/projection test matrices.

Real pinned ClickHouse checks must run separate writer/reader credentials,
schema mismatch before write, lost response after actual insert, changed batch
retry before merges, exact full row/lineage/microsecond readback, conflict/missing
or extra refusal and fresh-process readback after container replacement. Preserve
earlier experimental tables/volumes, offsets, failures and private credentials.
No migrations/deletes; rollback stops calling the new library/table. Window and
full archive-to-query reconciliation, production supervisor and M4 stay open.
