# ADR-0002: Separate immutable evidence from analytical serving

**Status:** Accepted as an architectural boundary. MinIO distribution, archive format and ClickHouse adoption remain proposed until M4 validation.

**Date:** 2026-10-19

## Context

Kafka retains only a bounded input history. Analytical tables are optimized for queries and may transform, replace or aggregate records. Neither can independently preserve all original evidence needed to investigate mapping defects and rebuild derived datasets.

Recovery also needs application state, which has a different lifecycle from source evidence. Treating raw data, checkpoints and analytical rows as interchangeable makes deletion, recovery and correctness claims ambiguous.

## Decision

Preserve original source bytes and provenance manifests separately from observed Kafka events. Archive observed values with topic/partition/offset coverage and checksums through an independent consumer. Store checkpoints in a separate access and lifecycle namespace, even when the local object-store process is shared.

Use S3-compatible object storage as the archive boundary, with MinIO as the initial candidate. Use ClickHouse as the serving candidate. Serving datasets are reproducible projections identified by dataset run and pipeline version; source and observed-event evidence must remain available for the declared retention period.

The archive writer must verify durable bytes and receipts before committing Kafka progress. Serving writes may repeat physically; logical identity, unique-read queries and reconciliation establish the intended analytical result. Adopt ClickHouse only after ambiguous acknowledgement and pre-merge query tests pass.

## Alternatives

- **Keep everything in Kafka:** simplifies early replay, but makes long-term recovery depend on broker storage and retention cost; use only for the M2 prototype.
- **Keep only analytical rows:** reduces storage but loses exact source evidence, rejected inputs and transport history.
- **Query the raw archive directly:** useful for occasional audits, but requires another query execution choice and does not by itself solve serving latency or event identity.
- **Introduce a lakehouse format immediately:** could support future table evolution and query engines; its catalog and maintenance work are unnecessary for the first small slice.

## Consequences

Independent archival and serving allow rebuilding tables and investigating failures, at the cost of another worker, duplicated storage and explicit progress reconciliation. No atomic transaction spans Kafka, the archive and ClickHouse. A run is not complete merely because one consumer has caught up.

Immutability is a write policy until storage protection and restoration are tested. A single local object-store volume is not an off-host backup. Privacy review, derivative lineage and deletion / retention ownership remain necessary even for public-source data.

## Related documents

### Final archive target follow-up, 2026-10-22

[ADR-0020](0020-bounded-tests-and-s3-archive.md) selects Amazon S3 for the final
deployment's archive. It supersedes only the unresolved final provider choice;
local backend/format/client validation, the independent evidence boundary and
ClickHouse adoption gates remain unchanged. No cloud resources are authorized.

[Architecture](../architecture.md), [data contracts](../data-contracts.md), [deployment and Terraform](../deployment-and-terraform.md).

### Proposed local format/backend follow-up, 2026-10-22

[ADR-0021](0021-bounded-archive-format.md) proposes bounded JSONL/base64,
immutable manifests/receipts and a finite sealed catalog. It proposes SeaweedFS
as the local compatibility candidate after observing the archived MinIO upstream.
This is not runtime adoption or a change to this accepted responsibility boundary;
the final S3 target and ClickHouse gate remain unchanged.
