# ADR-0030: Bounded canonical event writes with exact readback

**Status:** Bounded event-library decision, 2026-10-26. The
recorded checks, final restricted review and deterministic
acceptance receipt govern admission. Only an accepted receipt admits the library.
Full M4 and production runtime admission remain separate.

## Problem and bounded decision

The accepted pure projection has complete semantic content and archive lineage;
the earlier SQL experiment stores a partial fixture projection without those
fields. Adapting rows to the old table would lose evidence. Create a separately
versioned append-only `serving_events_v1` table and use the existing pinned
ClickHouse image with a standard-library HTTP transport. Preserve old tables.

Publish only a freshly verified archive projection, check actual schema before
writing, use synchronous bounded batches and reconcile every distinct stored
row through separate reader credentials. Ambiguous writes stop without local
completion; full explicit retry with changed batching remains duplicate-safe.
No physical insert uniqueness or background merge is required.

The pinned server's toString(Decimal) removes insignificant zeros. Use
toDecimalString(column,6) on verified Decimal(18,6) columns to preserve the exact
wire scale without rounding. The failed real readback, native settings probe
and narrow frozen formatter-matcher supersession are retained for review.

All lineage is content under the scoped event key. A different descriptor under
the same event key is a conflict, not an implicit archive migration. Use explicit
isolated target runs for changed archive roots. Return a verified observation
receipt only after full identity/content reconciliation, never equal counts alone.

## Alternatives, cost and maintenance

Changing the existing experiment in place would erase the distinction between
partial fixtures and admitted canonical semantics. ReplacingMergeTree may discard
conflict evidence; bounded block deduplication cannot handle all retry batching.
Adding an SDK or Flink sink connector requires another dependency/compatibility
gate without improving this finite event boundary. Reuse the pinned service and
stdlib HTTP; two small typed modules and a SQL table add maintenance cost but no
new service/image/package. Scan/result limits bound this tiny profile, not capacity.

## Limits and rollback

[The interface](../reference/serving-sink-interface.md) defines exact APIs, schema and
failure behavior. No windows, late routing, source offset commits, S3 checkpoint
migration, persisted completion marker or concurrency/sealing guarantee is added.
Socket inactivity timeouts are not a whole-command deadline; a supervised runtime
gate remains required. Reader raw-table access is diagnostic, not enforced query
admission. Local HTTP and trusted Docker/database administrators remain explicit.

Stop using the new library/table to roll back. Preserve rows, old experiments,
archive evidence and offsets; do not drop tables or delete volumes. Cloud,
production durability and complete archive-to-query acceptance remain open.
