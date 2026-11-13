# ADR-0036: Packed managed vehicle state for continuous Battery

**Status:** Proposed, 2026-10-27. Implemented and locally checked after the
maintainer requested stopping the slow load and removing its bottleneck.
Production throughput/container admission remains pending.

## Problem

Actual Flink REST observations show Battery busy and its upstream backpressured,
with idle Kafka output and no serving lag. A frozen local SDK workload performs
10240 synchronous MapState reads for 2048 observations, spending most of the
operator interval in state access. Waiting for the two-million-record backlog
would not diagnose or remove this per-entry overhead.

## Decision

Replace three entry-addressed MapStates and a separate count ValueState with one
managed typed tuple ValueState per vehicle: identity map, expiry-bucket map,
window map and count. Preserve every event-time/identity/window rule and guard.
Use the maintained SDK's existing value cache and bundle/checkpoint flushing;
there is no private authoritative cache or SDK patch. Empty completed state is
cleared. Battery state descriptors/UIDs and the job name advance to v4.

The performance record binds frozen v3 and v4
inputs, RPC counts, semantic-output hashes, correctness tests and savepoint
checks. Local operator timing improves about five times; startup-inclusive and
full-runtime throughput claims are distinguished.

## Alternatives and cost

Increasing CPU quota would not remove synchronous per-entry requests and was
not selected. Warming the SDK's complete-map cache was smaller and initially
fast, but the longer probe exposed a growing known-key index despite cache
entry eviction; it was rejected. A custom Python cache would require its own
boundedness, invalidation and checkpoint behavior. A JVM implementation or new
backend/connector would add a separate maintained code/runtime boundary.

Whole-value serialization sends a larger value on commit and can become costly
under cache eviction or high state density. The existing managed-key cache and
per-vehicle/source bounds remain; the one-entry-cache regression checks safe
fallback. No framework, service, dependency, identity cap or memory quota is
introduced or increased. Maintenance is a new internal serializer and an
explicit state-compatibility boundary, rather than an additional cache protocol.

## Migration and rollback

This is an internal state-format change, not a canonical identity or wire-format
change. V3 checkpoints remain retained and are not migrated. Do not allow
unmatched state to be silently discarded. A v4 deployment starts in a fresh
isolated processing scope unless an explicit migration is independently checked.
Rollback selects frozen v3 code and a compatible v3 checkpoint. The stopped
load's data/offsets/evidence remain unchanged. A full graph/budget check precedes
any subsequent large-run adoption; no large run is automatically restarted.
