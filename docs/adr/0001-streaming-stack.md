# ADR-0001: Propose Kafka and Flink for the streaming core

**Status:** Proposed; adoption requires M2 broker/client and M3 processing compatibility evidence.

**Date:** 2026-10-19

## Context

The project needs partitioned event transport, event-time windows, recoverable keyed state and inspectable failure behavior. It should demonstrate transferable streaming engineering without operating two processing engines for the same workload. Initial inputs are bounded historical logs, with continuous simulated sources possible later.

## Decision

Use Kafka as the proposed event log and Flink as the proposed stateful processing engine. Begin with one local broker and a small job topology. Python remains the ingestion / replay language; choose SQL, Java or PyFlink for processing only after verifying the required validation, side-output, Kafka and storage integrations.

Document a compatibility matrix before installing dependencies or writing the job: runtime, JVM, API, Kafka client/connector, storage plugin and eventual ClickHouse write path. Use a single battery aggregation as the validation workload. Do not claim connector compatibility from product names alone.

Acceptance of the proposal requires a bounded ingestion/restart experiment, controlled watermark tests and checkpoint restore with reference output. Connector choices may be revised without changing the canonical measurement contract.

## Alternatives

- **Kafka plus Spark Structured Streaming:** credible for teams prioritizing Spark and batch integration; would still require careful event-time, checkpoint and external sink tests. Defer it because the initial learning objective centers on explicit stateful streaming behavior.
- **Kafka Streams:** fewer runtime services for JVM-only processing and worth considering if Flink's operational cost outweighs the needed operators. It changes the development model and still requires external sink correctness work.
- **Python consumer with database calculations:** suitable for the smallest transport prototype, but custom window/state recovery would obscure the intended streaming-engine exercise.
- **Flink and Spark together:** adds duplicate processing ownership without an initial requirement; excluded.

## Consequences

The stack supports explicit partitioning, watermarks and state experiments, but introduces JVM, container and connector complexity on a single Windows workstation. Incremental service startup and a measured resource budget are required. Flink checkpoints alone do not establish exactly-once effects in external storage; M4/M5 must prove the selected sink behavior separately.

If a supported integration cannot meet the small slice without disproportionate custom code, amend this proposal or supersede it with an evidence-based decision. Do not add a second engine to hide an unresolved connector problem.

## Related documents

[Architecture](../architecture.md), [roadmap](../roadmap.md), [testing strategy](../testing-strategy.md).
