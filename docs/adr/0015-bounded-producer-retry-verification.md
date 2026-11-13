# ADR-0015: Verify producer retry after loss of local publication progress

**Status:** Accepted for the authorized local synthetic M2 verification cycle;
runtime results are recorded in the consolidated report.
This is an experiment protocol, not adoption of a general ingestion service.

**Date:** 2026-10-20

## Problem and decision

[ADR-0012](0012-kafka-ingestion-candidate.md) requires a producer interruption
experiment. Broker acknowledgement and a durable local publication receipt are
separate boundaries. Native idempotence does not deduplicate a fresh application
process that republishes the same source records.

Use one new isolated single-partition topic and the existing verified three-event
synthetic run. The first child requires all three successful callbacks and an
empty queue, flushes diagnostic stdout, then exits immediately with code 88
before writing any local publication receipt. Parent-captured stdout is external
failure-injection evidence, not recovered producer progress. The parent
independently reads the captured `[0, 3)` interval against the external source.

A second process explicitly retries the same original keys/value bytes only
after checking the live cluster/topic UUID and exact original retained coverage.
Require acknowledgement positions 3–5, no pending work and a new fsynced attempt
receipt. Independently read `[0, 6)` and reconcile raw observations separately
from unique event identities and the existing battery semantic projection.
Require six observations, three repeated observations, three source identities,
no missing/extra/conflicting identity and exact original retry keys/value bytes.
Retain raw hashes and offsets. Do not silently reset a consumer or delete records.

Keep raw byte/key mismatch detection separate from semantic conflict detection.
Use authored valid envelopes to check missing, extra and changed-semantic
content, plus a delivery/formatting-only semantic-equivalence control. These are
offline reconciliation checks and are not described as broker fault injection.

Also exercise native timeout and queue-full outcomes against a reserved
non-listening loopback endpoint. Account queued, unqueued, callback-failed,
uncertain and pending positions with finite deadlines. A failed callback is not
proof of absence from a real broker. Refuse publication success for either case;
success of the harness means that the expected failure was detected.

## Alternatives, cost and limits

Resuming from an unchecked local counter could hide a lost receipt. Pretending
idempotence spans new producer sessions could hide duplicates. A transactional
outbox or shared progress database would add services and ownership beyond this
experiment. A generic automatic retry API would require partial-ACK, concurrent
producer, retention and rebalance policies not established here.

This uses existing pinned Python/client dependencies and the existing local
broker. Maintenance cost is one bounded failure harness and a consolidated
runner; synthetic data volume is tiny and no cloud resource or cost is added.
One exclusive local operator and stable source files remain assumptions.
Lost broker ACKs, partial ACKs, production backpressure and host/disk-loss
recovery remain outside the demonstrated protocol.

## Acceptance and rollback

The consolidated cycle runs all existing admission, consumer interruption,
retention, graceful restart and SIGKILL checks alongside these new producer
cases, both existing M1 dependency profiles, quality checks and independent
review. All acceptance conditions must remain active with Python optimization.
Preserve exact commands, outcomes, source hashes and prior evidence; finish with
the original broker stopped and its named volume retained.

Rollback removes this experimental path/runner and its navigation without
changing M1 runs, event/receipt contracts or broker configuration. Preserve
duplicate transport observations and evidence; deleting or downgrading the
volume is not rollback. No accepted ADR is superseded. Hosted CI, real-source
acceptance and full M2 deliverables remain separate gates.
