# ADR-0010: Extend bounded ULog framing to nested layouts and M/L/S

**Status:** Implemented and locally validated for the authorized M1 format-support
increment. Real-source mapping adoption remains proposed.

**Date:** 2026-10-19

**Supersedes:** only the flat-definition and supported-message subset clauses
of [ADR-0008](0008-ulog-input-integrity-gate.md). Its whole-input validation,
external receipt, count/ordinal and no-recovery requirements remain in force.
Actual-source adoption in ADR-0007 remains proposed.

## Problem and decision

The candidate review demonstrates that the primary
retained input needs three nested definitions and `M`, `L`, `S` messages.
Skipping unsupported bytes or trusting parser recovery would weaken identity
correctness. Extend the structural gate; keep upstream value decoding separate.

Resolve definition references after the definition section, allowing forward
references. Reject undefined or cyclic references even in unused definitions.
Memoize width, expanded scalar-field count and depth without materializing
expanded arrays. Nested fields always include their complete padding; only a
top-level definition's own terminal padding may be omitted. Cap depth at 32,
expanded fields at 4096 per definition, and summed subscribed expanded fields
at 100,000, including subscriptions that have no data. Existing byte/frame and
packet-width limits remain unchanged.

Definition, field and referenced-type identifiers are capped at 128 ASCII
characters. Also memoize a conservative qualified-field-name byte bound and cap
it at 8 MiB per layout and across all subscriptions, including empty streams;
scalar/leaf counts alone do not bound name allocation in the upstream reader.

Support `M` only for UTF-8 `char[N]` chunks with exact declared byte lengths,
including `char[0]`. Chunk lengths may vary for a key; continuation must be 0/1
and a continued chunk must follow a started value for that key. Reject shared
`I`/`M` keys to avoid ambiguous metadata. Do not assemble or expose these values.
Validate `L` minimum header width, ASCII severity 0 through 7 and UTF-8 text.
Validate exact `S` magic/width at the current frame boundary; never resynchronize
by scanning forward. Unsupported messages, flags, appends and subscription
changes still fail the whole source.

The converter records `pipeline_version: bounded-converter-v2` because its
supported input boundary changes. Event schema, mappings and measurement IDs
are unchanged. No framework, package, service or cloud resource is added.
The new work budgets may reject large flat layouts that fit the earlier byte
limit; older completed runs retain their existing meaning and provenance.

## Alternatives, cost and rollback

Discarding unrelated streams prevents whole-input count reconciliation. A
replacement semantic parser duplicates upstream ownership. Unbounded recursive
expansion risks stack or allocation failure before upstream validation. Small
memoized structural summaries and explicit limits keep this change local; the
maintenance cost is the resolver, three frame validators and focused fault cases.

Verify nested arrays/padding, unresolved/cyclic/oversized/deep layouts,
continuation/metadata ambiguity, corrupt service frames and original ordinals
through the existing reader tests. Inspect the registered primary file without
normalizing or exporting real measurements. Record actual supported limits and
remaining failures rather than assuming candidate acceptance.

Rollback restores the earlier gate and converter pipeline version, restricting
new input admission. Retain completed run metadata; no measurement migration
or persisted-state deletion is required. Changes to accepted value semantics
would need a separate normalization-lineage decision.
