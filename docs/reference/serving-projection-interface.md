# Bounded archive-to-serving projection interface

Status: bounded pure interface, 2026-10-26. Admission is governed by the
independent evidence and final acceptance receipt.
This is not a ClickHouse sink, window calculator or M4 acceptance. The frozen
v1 contract retains its earlier proposed status; normative behavior is unchanged.

## Public API

`telemetry.serving_projection` exports frozen dataclasses:

- `ServingScope(dataset_run_id: str, pipeline_version: str)`.
- `ServingRow(dataset_run_id: str, pipeline_version: str, event_id: str,
  vehicle_id: str, source_timestamp: str, voltage_v: str,
  current_a: str | None, remaining_fraction: str | None,
  quality_flags: tuple[str, ...], semantic_json: str,
  source_dataset_run_id: str, source_job_sha256: str,
  archive_descriptor_sha256: str)`.
- `ServingBatch(scope: ServingScope, archive_descriptor_sha256: str,
  rows: tuple[ServingRow, ...])`.
- `ServingError(category: str, field: str)`: safe fixed diagnostic attributes;
  messages contain no supplied payload, path, identifier or credential.
- `project_archive(descriptor: bytes, expected_sha256: str,
  store: telemetry.archive_interfaces.ReadStore,
  scope: ServingScope) -> ServingBatch`.

Only this one public projection function is required. No dependency, filesystem
or network client is added. The caller supplies the already supported storage
port; the function does not write/commit, resolve paths, read ambient configuration
or modify supplied objects. Every invocation performs fresh whole-graph validation
through the existing `verify_catalog`, never a cache or a caller-forged
`VerifiedArchive`. Existing graph failures propagate as `ArchiveError` unchanged.

Validate the scope before any storage call: exact ServingScope instance, both
fields plain strings matching `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`. Invalid scope
raises `ServingError('invalid_scope', 'scope')`. A target namespace may equal or
differ from the original dataset run; original delivery context is never rewritten.

## Lineage and event semantics

The graph's current supported profile remains bounded synthetic battery 1.0.0,
`battery-v1`, `battery-semantic-v1`. Do not broaden archive or canonical admission.
Use the graph's verified unique measurements, with at most 64 observations and
the existing graph byte/object limits. Rows sort lexically by event_id; no output
escapes on any failure. No online eligibility or late disposition is invented.
No quarantine or window rows are produced.

Each row preserves its validated physical source_timestamp as the original UTC
string with six fractional digits and Z, independent of arrival/processing time.
It records target scope, original delivery.dataset_run_id, exact original job
SHA-256 and independently supplied descriptor SHA-256. Derive the original job
link using the verified descriptor/catalog lineage and archived registrations;
do not trust a link passed separately by the caller or copied from target scope.
An event must match exactly one admitted original registration. Otherwise raise
`ServingError('lineage_mismatch', 'registration')`.

semantic_json is a deterministic JSON object containing exactly the documented
battery-semantic-v1 fields: vehicle_id, event_type, source_timestamp, source_log_id,
source_type, source_stream, source_record_index, normalization_version,
source_time, payload and quality_flags. event_id is preserved separately.
Keep complete recognized nested source_time and all three recognized payload
fields, including null optional values. Flags are sorted lexically. Exclude
schema/provenance/retrieval metadata, ingest time, delivery and unknown additive
optional fields; reuse the canonical reader's recognized projection.

JSON object keys sort lexically at every depth, arrays retain order except flags,
strings use JSON escaping with ensure_ascii=False, no spaces or trailing newline.
Finite numbers use their reader-admitted base-10 value (`Decimal(str(value))`),
plain non-exponent notation, no insignificant fractional trailing zeros or
decimal point, and signed zero becomes 0. Thus 1 and 1.0 have identical encoding.
Never hash raw event JSON as measurement identity. This normalized encoding is a
serving representation of typed semantic equality, not a canonical wire change.

## Lossless local precision profile

The profile is `serving-battery-exact6-v1`; expose it as `PROJECTION_VERSION`.
For each recognized non-null payload number, convert its reader-admitted decimal
value exactly to a signed integer scaled by 1,000,000. Do not use binary float
multiplication, context-dependent Decimal rounding, quantize rounding or truncation.
Values with any nonzero digit beyond six places raise
`ServingError('precision_loss', FIELD)`; exactly representable values must also
have absolute scaled integer <= 999999999999999999, otherwise raise
`ServingError('decimal_overflow', FIELD)`. FIELD is the fixed payload field name.
Check precision before range when both fail. Preserve valid zero, negative current
and null optional fields; voltage remains required/non-null under the reader.

Output numeric strings use exactly six digits after the decimal point, no exponent,
and no negative zero, e.g. 15.800000, -1.250000 and 0.000000. Do not reinterpret
units or round accepted canonical measurements to make this limited serving
profile accept them. A profile refusal does not invalidate the canonical event.

## Acceptance and limits

Reuse the existing public Graph fixture and three small authored source/job/golden
fixtures. Independent tests must precede candidate exposure and check full semantic
projection, null/zero/signed values, exact precision/refusal, original lineage versus
target run, duplicate/changed-batch determinism, fresh graph rejection and no partial
return, without duplicating the whole archive suite. Normal and optimized Python,
strict types, Ruff and existing relevant archive/canonical regressions are required.

No ClickHouse DDL change is authorized by this interface. The earlier experimental
DDL has no lineage columns and stores a fixture semantic projection; do not label
these rows directly insertable or claim full serving integration. A versioned sink
schema/transport and approved-query enforcement need a later gate. Existing stored
ClickHouse experiments, Kafka offsets, archive objects and M3 checkpoints are
unchanged; removing this pure projection requires no persistent migration.
