# ADR-0038: Immediate live output from the continuous Flink job

**Status:** Proposed, 2026-10-27. Implemented and checked in a small isolated
eighteen-partition runtime. Production adoption and sustained capacity remain open.

## Problem

The sole transactional Kafka sink makes eligible measurements invisible until
checkpoint completion. Its ten-second cadence is inappropriate for a live view.
The independently tested heartbeat receiver does not establish live measurement
processing through Flink. Small full-graph checks additionally expose Python
execution overhead that the previous local Battery microbenchmark did not cover.

## Decision

Keep canonical admission, keyed Battery state, partition-local watermarks,
4096 identity refusal and the historical exactly-once Kafka sink. Add an optional
second Kafka sink after Battery with at-least-once delivery, all-replica ACKs and
idempotent production. It emits the same processing facts without checkpoint
transaction visibility delay. Its latest-value consumer admits eligible facts,
ignores repeated/older measurements, refuses competing equal-time measurements,
and bounds memory to the registered fleet. This is an operational projection,
not an exactly-once durable result or a replacement for analytical reconciliation.

For the live profile, eliminate PyFlink's identity-map insertion in
`get_side_output()` and its Python timestamp/key-selector bridges. A small JVM
adapter uses the already admitted tuple timestamp and creates exactly the key
envelope expected by the pinned Python keyed operator. Each partition still
gathers to one lane before assigning watermarks. No invalid canonical record
may advance time. The execution-plan guard checks this native path separately.
The keyed Battery stage may optionally use two to four subtasks inside each
partition branch, after the one-lane watermark assignment. This adds Python
workers and resource cost; the default remains one. State compatibility and
the partition-local watermark boundary remain required when rescaling.

Build against the existing Flink 2.2.1 libraries/JDK 17, with no new dependency,
SDK patch or downloaded artifact. Source, build script and targeted actual-SDK
tests belong to the repository; build outputs/hashes stay local. This adapter
is justified by a demonstrated full-graph latency blocker, not speculation.

## Alternatives and cost

Shorter checkpoints alone do not remove Python graph overhead and couple live
visibility to snapshot/commit duration. Reading uncommitted historical
transactions would expose aborted records without an explicit live contract.
Replacing Flink or bypassing it for measurements would not establish the
requested source-to-live processing behavior. The separate heartbeat monitor
remains useful for observing loss of the processing system itself.

Maintenance adds one small Java class, its reproducible local build, a second
output topic/sink, a bounded Python latest-value projection and API/page using
the existing HTTP infrastructure. Backpressure/failure of either sink still
affects the shared job. No process-isolation or independent-availability claim
is made for these two outputs.

The optional `compose/live.yml` assigns six CPU rather than three to TaskManager
and limits unused BLAS/OpenMP pools to one thread. Memory remains 4 GiB, PIDs
4096 and retained IDs 4096 per vehicle. This is a declared resource cost, not a
claim that code changes alone deliver the final measured latency. The final
profile combines graph changes and resource configuration; their individual
performance contributions were not isolated.
The ongoing 1 GB experiment uses a separate ten-CPU, 6 GiB TaskManager limit
and two Battery subtasks per partition. It does not establish a capacity or
latency guarantee; its interim evidence and incomplete verification are recorded
in the execution record.

## Compatibility and validation

The historical default without live configuration retains the Python bridge
path. Live configuration requires a built `partition_time_jar` file URI and
a distinct `live_output_topic`. Native gather/time UIDs are new; Battery's v4
serializer/UIDs are unchanged. A compatible native checkpoint was restored
twice without allowing unmatched state to be dropped. No v3-to-v4 migration
or historical offset reset is performed. A new deployment should start in an
isolated scope unless its exact restore path is checked.

The execution record binds the small latency trace,
actual restored duplicates, native timer/topology regressions and resource
limits. Rollback selects retained code/configuration plus its compatible
checkpoint, stopping only the new scope. Existing historical evidence remains.

## UI and freshness follow-up, 2026-10-27

The live interface follow-up adds optional monotonic
receipt age and clock-qualified admission-to-collector delay to the existing API.
Only records at or beyond each partition's captured startup frontier can acquire
the new freshness signal; reconstruction and unhealthy collection are unknown.
Existing wire identity, Kafka delivery, state UIDs and checkpoints are unchanged.
Small mocked/HTTP/browser checks do not extend the recorded production capacity
or actual-device evidence. This decision remains proposed.
