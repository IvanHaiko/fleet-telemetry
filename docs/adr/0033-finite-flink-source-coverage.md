# ADR-0033: Refuse incomplete finite Flink source intervals

**Status:** Accepted for the bounded local finite-source commands, 2026-10-26,
following the [M5 evidence](../case-studies/m5-reliability.md). Production admission remains open.

## Observed problem and narrow repair

The pinned Table Kafka source can finish a bounded job successfully when the
requested `[0,4)` interval has expired. Actual retained bounds advance beyond
the stopping offset; the command returns exit 0 and a FINISHED receipt despite
reading none of the declared observations. `properties.auto.offset.reset=none`
does not establish the promised refusal on this connector path. The failed
M5 probe is retained; a low-level FINISHED result is insufficient evidence.

Keep the pinned runtime and the validated ADR-0023 enumerator repair. Add a
finite admission/completion guard using Kafka's already installed offset CLI.
Require earliest offset zero on every declared partition before submission and
again after completion. At completion require high offsets cover every reserved
end and require exact source-receipt coordinates for the entire declared range,
with identical content hashes on repeated coordinates. Only then publish the
existing FINISHED command receipt. Both maintained persistent and two-partition
jobs use the same small guard; operators and graph/state UIDs stay unchanged.

This deliberately conservative local profile requires the whole finite interval
to be available at admission and completion certification, including checkpoint-restored prefixes.
It does not admit partial-retention recovery merely because a checkpoint exists.
Use the separately verified isolated archive rebuild path for unavailable input.
The guard reports source gap separately from unavailable bounds and preserves
all existing source, checkpoint and diagnostic files. A completion-stage refusal
may occur after Flink has already committed source progress; it does not promise
offset rollback or authorize resetting a consumer group.

## Alternatives, cost and validation

Trusting job status repeats the observed silent-loss defect. Changing connector
offset initializers or replacing the Table source could alter serialized source
state/UIDs and invalidate established cold restoration. A new SDK or another
connector patch is unnecessary for this finite profile. Existing Kafka 4.4.0
Java CLI tools add bounded startup/process cost but no image/package dependency.
This is one scenario-required guard, not a general source framework.

Require a focused pure regression for expired bounds/incomplete or conflicting
receipts, actual preflight and post-admission retention refusals, ordinary finite
completion and a cold restore of the already retained checkpoint. Preserve the
original falsely successful probe and the checkpoint readiness-race history.
No blind-test or enforced independent-review claim is needed for these observable
inputs; the demonstrated loss consequence justifies the targeted escalation.

Rollback stops affected source commands; do not restore an unsafe successful
completion path. No schema, measurement identity, image, checkpoint format,
operator serializer, cloud resource or historical receipt is migrated.
