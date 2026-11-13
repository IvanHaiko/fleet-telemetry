# ADR-0029: Lossless bounded serving projection from a trusted archive

**Status:** Bounded pure profile decision, 2026-10-26. Admission is governed by
the independent checks, final restricted review
and deterministic acceptance receipt. Only an accepted receipt admits the boundary.
ClickHouse adoption and complete M4 acceptance remain separate.

## Problem and bounded decision

The ClickHouse compatibility experiment stores a partial golden-fixture record
as semantic_json and has no proven canonical projection or archive lineage bridge.
Its Decimal(18,6) columns cannot represent every valid canonical numeric value.
Silently rounding would let the serving result disagree with immutable evidence.

Add a pure, finite `serving-battery-exact6-v1` projection under the
[public interface](../reference/serving-projection-interface.md). Reuse fresh whole-graph
verification and current original-job registration checks. Preserve stable
event identity, physical measurement time, recognized battery-semantic-v1
content, exact job/descriptor hashes and original versus target dataset runs.
Normalize semantic JSON numeric representations so equivalent 1/1.0 and signed
zero do not create artificial conflicts. Never manufacture measurement identity
or window/late dispositions from transport or arrival metadata.

Represent payload values losslessly at six decimal places, refusing excess
precision or range instead of rounding or clipping. Use exact integer arithmetic
over reader-admitted decimal values, independent of Decimal context precision.
A serving-profile refusal does not reject or rewrite a valid canonical event.
This is a profile-specific capability limit, not a canonical contract revision.

## Alternatives and impact

Float64 columns would admit more values but still require explicit reproducible
comparison and aggregation semantics. Larger Decimal scales/ranges shift rather
than remove the compatibility boundary. Rounding requires a distinct derived
measurement policy and reconciliation tolerances. Preserve raw canonical evidence
and fail closed in the existing small Decimal candidate instead.

No SDK, framework, service, storage format, cloud resource or runtime dependency
is introduced. One small typed standard-library module adds review/maintenance
cost. Existing archive limits bound input size. Reuse existing independent Graph
fixtures and canonical-reader regression checks instead of duplicating their
test matrices.

## Adoption limits and rollback

The module returns immutable values; it does not write a sink, commit offsets,
open paths, migrate existing tables or alter archive evidence. Existing spike DDL
does not carry these lineage fields and is not the admitted target schema.
A versioned sink schema/transport, approved-query access, window/disposition
reconciliation and the complete archive-to-query run need later gates.
Rollback stops using the pure projection; no persistent migration is required.
