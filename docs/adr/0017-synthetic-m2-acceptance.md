# ADR-0017: Separate local synthetic M2 acceptance from release/source gates

**Status:** Accepted by the maintainer on 2026-10-21 after independent review of
the acceptance evidence. M2 is accepted only for the local
synthetic ingestion profile; real-source adoption and hosted CI remain open.

**Date:** 2026-10-21

## Problem

The roadmap makes M2 depend on all of M1. M1 combines synthetic normalization
with real-source rights/producer adoption and hosted CI. The bounded M2 protocol
uses only project-authored synthetic input, and its Kafka criteria can be tested
locally without adopting a real source. Git publication is maintainer-owned and
this directory has no Git metadata. More local audit features cannot establish
an unexecuted hosted workflow or real-source rights.

## Decision

Accept M2 specifically as the **local synthetic ingestion profile**. The current
five Kafka criteria, relevant local deliverables, actual runtime metrics,
source-to-publication manifest verification, preserved-runtime cleanup and
independent review passed. Its M1 prerequisite is the validated synthetic source,
file/run integrity and current envelope-reader boundary used by that profile.

Keep real ULog adoption and hosted M1/service CI as explicit release/source
gates, without describing them as passed. M7 release still requires those gates.
M3 may use the accepted synthetic profile; real-source claims require the
separate M1 adoption decision. This selects no Flink API/version and authorizes
no automatic retry, deployment, publication or cloud resource.

This record supersedes only the roadmap's all-of-M1 dependency for
local synthetic M2/M3 sequencing. Existing architecture, data contracts,
ADR-0012 through ADR-0016, failure windows and retention limits remain intact.
The accepted label must always include the local/synthetic scope in README,
roadmap and the acceptance ledger. It does not mean general production ingestion
or a portfolio release has been accepted.

## Alternatives and cost

- Keep the original gate: local M2 results remain verified evidence while full
  milestone acceptance waits for real-source and hosted execution. This is the
  policy retained as a rejected sequencing alternative for this synthetic profile.
- Waive the missing results without recording scope would make acceptance
  misleading and is rejected.
- Adding services or more broker experiments cannot prove provenance/rights or
  hosted CI and is unnecessary for that decision.

There is no dependency, service or cloud cost. Maintenance adds a scoped status
and clear release/source ledger. The operational implementation remains the
existing single-broker/partition synthetic protocol, not a new service.

## Evidence and rollback

The acceptance report must retain exact commands, source hashes, native metrics,
failure probes, manifest verification, independent review and original broker
container/image/volume identity. Prepared CI is distinct from hosted execution.
No earlier failed or incomplete gate may be relabeled as successful.

The maintainer explicitly selected scoped M2 acceptance in this cycle; the local
decision receipt preserves that answer. If the decision is later reversed,
restore the original sequencing/status through a linked decision while retaining every
technical result and decision record. No source/checkpoint/data migration or
storage deletion is involved.

## Partial identity-evidence supersession, 2026-10-24

[ADR-0026](0026-historical-topic-identity-qualification.md) supersedes only the
historical Windows topic-UUID trust portion of this decision and its supporting
evidence. The read-only audit confirms the SDK's
signed-32-bit narrowing against independently retained broker metadata. Preserve
the original measurements, payload hashes, offsets, reference/recovery results
and their bounded limits; they do not certify missing UUID bits. Affected
identity-dependent receipt reuse needs an explicit reviewed attestation/
migration. The earlier record is retained, not silently rewritten.
