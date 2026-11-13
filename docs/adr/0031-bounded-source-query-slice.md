# ADR-0031: Integrate the existing components in a finite source-to-query slice

**Status:** Accepted for the tiny local synthetic demonstration, 2026-10-26.
Full M4 acceptance and production admission remain open.

## Problem and decision

The separate archive, processing and event-sink results do not demonstrate a
single source-to-query run. The active roadmap prioritizes that useful result.
Reuse the authored M1 source/job, M2 transport, independent supervised archive,
M3 persistent job, canonical event projection and admitted event HTTP sink.
Keep their existing pins, refusal behavior and historical evidence.

Use the existing terminal-watermark bounded-reference policy for four Kafka
observations: three admitted measurements followed by one repeat. A finite parent
checks actual Flink source-byte receipts, dispositions and rational window sums
against the independent reference before writing processing facts. Store these
in two new append-only demonstration tables, separate from canonical events.
Read back full distinct rows before reporting trends, coverage or quality.
Check exact means for this fixture and refuse missing or competing facts.

An acknowledged upstream event write followed by a caller-side connection-loss
injection establishes ambiguous completion. Explicit changed-batch retries must
leave all three reports unchanged while merges remain stopped. This is a trusted
parent demonstration, not another isolated component-acceptance workflow.

## Alternatives and cost

Another Flink sink connector, continuous supervisor, protocol or generic runner
would add dependencies and maintenance before a complete finite scenario exists.
Reusing the experimental partial event table would discard admitted canonical
semantics and lineage. Reuse the current event table and add only the finite
scenario script, its SQL/report companion and two small processing tables.
There are no new packages, images or services. Explicit Compose network ranges
address the observed exhaustion of Docker Desktop's automatic address pools.

## Boundaries and rollback

Provisional Flink diagnostics become demonstration facts only after successful
job completion, exact byte receipts and reference reconciliation. This is not a
transactional continuous Flink sink or checkpoint-to-ClickHouse guarantee.
The local receipt is not a durable concurrent run seal. Query admission is
trusted parent code with separate reader/writer credentials; concurrent writers
or administrators remain outside the guarantee. SQL division is checked exactly
for this fixture, not adopted as a general arbitrary-precision mean policy.

No canonical identity, timestamp, unit, archive encoding or historical receipt
changes. Positive online-late behavior, archive-only replay into a new serving
run and full M4 assessment remain required. Stop invoking the new script/tables
to roll back; preserve volumes, roots and evidence. Container cleanup is a
separate explicitly authorized action; it does not authorize deleting storage.

## Subsequent milestone completion

[ADR-0032](0032-bounded-m4-completion.md) and M4 acceptance
complete the subsequent archive-only serving replay and sealed report boundary.
The original demonstration decision and its time-specific open items above remain
historical evidence; production and concurrent-writer admission remain separate.
