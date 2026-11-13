# ADR-0028: Append-only analytical serving compatibility candidate

**Status:** Proposed, 2026-10-26. The maintainer explicitly authorized service
launch after the original automatic approval refusal. The bounded local
compatibility experiment now passes, including real retry/conflict/role checks
and container-replacement readback. Independent admission and canonical
integration remain open; this is not production adoption or full M4 acceptance.

## Subsequent bounded adoption, 2026-10-26

[ADR-0032](0032-bounded-m4-completion.md) supersedes this record's candidate-only
local serving status after canonical integration, archive-only replay, immutable
run receipts and exact report admission pass. The original experiment and limits
below remain historical evidence. Production adoption is still open.

## Problem and choice

M4 needs immediate unique event/window reads after ambiguous sink acknowledgement
and retry with changed batching. Physical deduplication windows and background
merges cannot establish that property. Conflicting semantic values must remain
detectable even after compaction.

Experiment with official ClickHouse 26.8.34.13, Linux amd64 manifest
`sha256:ed334fbfae35c4f9fa328534821280b59d1c4677df8f3cf0e950cf7501a25bde`.
Use synchronous HTTP inserts through the Python standard library; introduce no
Python package or Flink connector. Use append-only MergeTree tables and explicit
grouping views. Events have logical key `(dataset_run_id, pipeline_version,
event_id)`. Complete window replacements add vehicle, metric definition, start,
end and logical revision. Equal-revision conflicts invalidate the entire run,
including conflicts in superseded revisions. Select the greatest revision only
after checking every revision. Never select by arrival time.

The query protocol first executes a separate conflict guard, including when the
requested result set is empty, then executes the analytical SQL. An inline guard
alone can be skipped by an optimizer for an empty result set and is insufficient.
Raw physical tables and intermediate views are diagnostic interfaces, not approved
queries. The experiment uses closed, drained inputs; concurrent publication,
atomic run sealing and continuous sink coordination need a separate design.

## Alternatives and maintenance cost

ReplacingMergeTree plus FINAL reduces physical copies, but can discard evidence
of conflicting equal-version contents. Keep conflicts observable with ordinary
MergeTree for this small candidate. Insert deduplication alone depends on blocks
and finite history. Incremental materialized sums can inflate under retries.
Querying the archive directly avoids a serving database but requires another
execution engine and does not answer this candidate's write/read gate.

One isolated Compose service costs a pinned image, retained data volume, up to
2 GiB memory, one CPU and extra query-time grouping. This is deliberately a tiny
fixture experiment, not a capacity claim. Preserve failed evidence and volumes;
stop the profile to roll back. Existing Kafka/S3/Flink profiles are unaffected.
Docker's automatic address pools were exhausted; the profile now uses the
observed free `10.254.241.48/28` subnet, overridable by `M4_SERVING_SUBNET` after
checking local allocations. No existing network was removed or reconfigured.

## Admission still required

Technical results belong in the serving report.
Strict independent tests/review and deterministic acceptance, a canonical
projection/lineage bridge, window/disposition reconciliation with the processing
reference, and a complete archive-to-query run remain required before adoption.
No cloud operation or checkpoint migration is authorized.

## Subsequent pure projection boundary

[ADR-0029](0029-lossless-serving-projection.md) and the
[projection interface](../reference/serving-projection-interface.md) define full canonical
semantics, lossless numeric refusal and independently verified archive lineage.
Its independent gate is scoped to the pure projection. This does not adopt or
silently migrate the earlier experimental tables, writer or query permissions.

Sources: [ReplacingMergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/replacingmergetree),
[insert retry deduplication](https://clickhouse.com/docs/guides/developer/deduplicating-inserts-on-retries).
