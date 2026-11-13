# ADR-0003: Keep canonical measurements independent of source protocols

**Status:** Accepted as a design boundary. The proposed `1.0.0` field contract and identity vector require M1 executable validation.

**Date:** 2026-10-19

## Context

ULog messages, future MAVLink packets and simulated sensor outputs have different field names, time bases, units and session semantics. Letting those details leak into every downstream job would couple the whole platform to one flight implementation.

Replay also requires a stable measurement identity independent of transport retries, arrival timestamps and newly created dataset runs.

## Decision

Put source interpretation in explicit versioned adapters. Emit a common JSON envelope with event-specific typed payloads, source position, normalized physical time, provenance and deterministic identity. Keep delivery metadata separate from stable measurement content.

For file sources, derive identity from the source checksum, native stream/ordinal, vehicle mapping, event type and normalization version using the documented recipe. Preserve native timestamps and clock-mapping provenance. Use a fixed declared synthetic anchor when an experiment lacks reliable UTC; do not disguise host arrival time as measurement time.

Begin with one battery event type. Add other measurements only with units, coordinate frame, optional-value and compatibility definitions. A changed interpretation requires a new normalization lineage. Live-device identity needs its own durable session/sequence design before adoption.

## Clarification — 2026-10-19

The original phrase "normalized physical time" above is qualified by the
existing contract's time semantics: use physical sample time when available,
and source publication time only when no sample time exists. Every admitted
event requires `source_timestamp`, with the distinction retained in
`source_time.timestamp_kind`. A fixed synthetic UTC anchor does not turn a
publication timestamp into a physical sample timestamp.

This is a dated clarification of the existing `measurement` / `publication`
contract, recorded as documentation patch `1.0.1`; it does not change the
accepted adapter boundary or identity recipe. The implemented synthetic mapping
continues to emit `1.0.0`. Compatibility of a future ULog producer still needs
executable evidence. The separate `ulog-battery-v1` profile remains proposed
until firmware and field semantics are reviewed.

The original decision text is retained for history. No decision is superseded
by this clarification. If subsequent review changes the accepted time meanings
or identity semantics, create a linked superseding ADR and update the decision
index and affected contracts together before adoption.

## Alternatives

- **Publish only native ULog or MAVLink payloads:** preserves fidelity, but forces every consumer to repeat protocol/time interpretation. Preserve native evidence in the archive instead.
- **One large synchronized vehicle snapshot:** appears convenient, but risks fabricated alignment and hidden carry-forward values across asynchronous sensors.
- **Random identity at publication:** easy to generate, but turns each replay into new measurements and weakens duplicate detection.
- **Timestamp/value identity:** loses legitimate measurements sharing a timestamp or value and ignores source position.
- **Avro or Protobuf plus registry immediately:** may later improve typed compatibility enforcement, but adds tooling before the first contract and consumer exist. Revisit through an ADR when justified.

## Consequences

Downstream components can reuse identity, time, privacy and recovery rules across telemetry domains. Adapters carry more responsibility and need independent fixture tests. JSON requires explicit validation and numeric restrictions; a written contract does not enforce itself.

Schema compatibility and mapping correctness are separate concerns. An additive schema change can preserve identity; a correction to units or time mapping creates a new normalization version and isolated dataset. Reconciliation must detect conflicting content under the same identity rather than silently selecting the latest arrival.

## Related documents

[Data contracts](../data-contracts.md), [architecture](../architecture.md), [testing strategy](../testing-strategy.md).
