# ADR-0026: Qualify historical Windows Kafka identity evidence

**Status:** Accepted finding for the maintainer-requested bounded read-only
audit on 2026-10-24. Evidence and limits define the
inventory. This adds no runtime, schema or automatically accepted migration.

## Problem

ADR-0017 accepts local synthetic M2 and ADR-0022 accepts bounded persistent M3.
Their earlier Windows client metadata observations were made before the
confluent-kafka 2.16.0 UUID narrowing defect was diagnosed. Repeated equal SDK
strings can therefore preserve the same wrong identity. ADR-0025 repaired new
conversions but explicitly left historical identity evidence untrusted pending
audit. The maintainer requested that audit and an upstream contribution package.

## Finding and partial supersession

Independent persisted Kafka metadata from 20 read-only mounted volumes gives
136 partition identities. The bounded 1,398-file JSON/JSONL inventory contains
77 distinct recorded topic identities: 59 exactly match the Windows int32
narrowing of the authoritative halves; 18 match all original 128 bits. The 59
bad identities occur in 171 evidence files. Eleven intentionally truncated
negative fixtures remain explicit rejected inputs, not extra accepted records.

This record **partially supersedes the historical topic-UUID trust portion**
of ADR-0017 and ADR-0022 and their supporting Windows observations. It does not
silently rewrite either decision or erase separately observed payload hashes,
offsets, operator/reference outputs and bounded recovery measurements. Those
observations retain their original limits and cannot substitute for full source
identity. ADR-0025's corrected-runtime acceptance remains unchanged.

Apply the existing full-identity contract: affected receipts are unsuitable for
identity-dependent reuse until an explicit reviewed attestation/migration binds
their original hashes to independent broker evidence. The diagnostic full-UUID
mapping is not a new accepted receipt schema. Preserve old bytes and failed
claims. No in-place replacement, inferred high bits, group reset, broker restart
or historical data deletion is authorized by this record.

The audit compares retained metadata at observation time; it does not establish
complete historical continuity, record availability or archive durability. The
original retention/preservation incident stays failed. Exact UUID matches do
not complete M4 or close production recovery gates.

## Contribution, alternatives and cost

Reuse the existing tested UUID-only repair and independent native regression.
An open upstream PR #2325 addresses the same cause more broadly. Prepare a
tests-only contribution for that PR and a narrowly scoped alternative patch;
do not publish either automatically or bundle project data/build machinery.

Rejected alternatives are trusting equal corrupted strings, widening an already
narrowed number, rewriting old receipts or restarting quarantined brokers just
to make old assertions pass. Reading retained metadata read-only supplies an
independent value without those changes. A helper uses the existing image,
network disabled, one CPU/128 MiB and read-only mounts. No new dependency,
service platform, cloud spend or compiled SDK is introduced by this increment.

## Verification and rollback

Keep exact input hashes/pointers, cluster/topic/volume bindings and both metadata
passes; independently check the signed narrowing calculation. Preserve original
container state/mounts and source/index bytes. Reuse the frozen native regression,
exercise stock/fixed Windows and stock Linux, and apply/reverse-check both
contribution patches against pinned official commit preimages. Separate
read-only review assesses findings, contribution scope and publication limits.

Rollback affects only the contribution/documentation increment. It cannot turn
invalid identities into valid ones. Retain the audit and original records; any
later revision of this finding needs new independently supported evidence.
