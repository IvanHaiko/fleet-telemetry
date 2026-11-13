# ADR-0014: Recover the bounded consumer from a verified observation receipt

**Status:** Implemented and locally validated for the authorized synthetic-only
M2 before/after-commit process interruption experiment. The
evidence guide records the exact limits; full M2
and general consumer recovery remain unvalidated.

**Date:** 2026-10-20

## Problem and decision

The first Kafka probe proves clean consumer reopen,
but not a process exit between receipt persistence and offset commit. Extending
that three-event experiment requires an explicit checkpoint format and recovery
rule. This does not add a service, dependency, source mapping or wire version.

Introduce `kafka-probe-receipt-v1` for new probe receipts. Bind a receipt to the
external verified M1 job/source, exact event bytes and vehicle keys, expected
offsets 0–2, fixed experiment group/topic, live cluster ID and topic UUID. Use the
client's documented describe-topics API to obtain the UUID. A topic name alone
cannot distinguish recreation. Legacy unversioned probe receipts remain evidence
and are not eligible for automatic recovery.

Validate bounded receipt bytes against the deterministic complete report expected
from these independent inputs. Require the authored canonical JSON serialization,
including its trailing newline; truncated, reformatted, extra/duplicate-field,
different-context or future-version receipts fail rather than being repaired.
This is an internal exact-byte checkpoint contract, separate from the canonical
event reader's tolerant optional-field behavior. Do not trust a stored next offset
or hash without regenerating its expected contents. Trusted local files and one
exclusive operator remain assumptions; this is not authenticated provenance.

For each new isolated experiment, require absent broker group progress and then
explicitly commit start offset 0 before reading; never reset existing progress.
After three verified observations, write/fsync/reread a new precommit receipt.
Real process failpoints use immediate exit without Python cleanup immediately
before commit and immediately after its broker acknowledgement. They are explicit
test-only options, never implicit production behavior.

On resume, publish no new events and create no topic. Require the same live topic
UUID and captured retained interval `[0, 3)`, with broker committed offset 0 or 3.
At 0, replay all three retained observations and compare their exact bytes/keys
against the source and verified original receipt; count three repeated
observations and three unique measurements. Persist a separate recovery receipt
before committing 3. At 3, do not rewind: verify original coverage and broker
progress, and record zero replayed observations. Other/missing committed offsets,
retention changes and corrupt receipts fail without advancing offsets. Separate
new output paths preserve every original receipt and avoid overwrite.

## Alternatives and limits

Committing 3 directly from an unchecked receipt can hide loss. Always rewinding
to earliest hides retention gaps and adds unnecessary observations after an
acknowledged commit. A database/WAL framework would add maintenance beyond this
fixed three-record, manually assigned partition. General receipt parsing,
partial-batch recovery, concurrent consumer fencing and rebalances remain future
work. No cross-process exactly-once or host/power-loss claim follows from fsync.

Reuse the existing source fixture and admission assertions. Exercise both real
process exit windows plus incomplete/altered receipt rejection against the broker;
do not add another native normalization or golden-vector unit suite. Recovery
receipts retain counts and safe position/hash evidence, not raw event payloads.

## Migration and rollback

Create fresh experiment topics/groups for the new format. Do not rewrite or
auto-upgrade old receipts. Existing canonical events and Kafka image/volume
configuration are unchanged. Rollback stops the same isolated Compose project
and retains its named volume and all receipts. This supplements ADR-0012 and
ADR-0013 without superseding an accepted measurement or image decision.
