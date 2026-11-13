# ADR-0047: Guarded continuous local position updates

**Status:** Proposed; guarded local continuation demonstrated, 2026-11-04.

The [execution record](../guides/continuous-position.md) demonstrates continuing SQL
updates, actual source silence/resume, acknowledged-write/cursor-window store
recovery and an exact independently read 78-delivery prefix. Recording remains
active within its one-hour/3,600-delivery guard. Other failure boundaries remain open.

## Problem and scope

The maintainer authorized the next live increment after ADR-0046: continuously
update archive/SQL, expose source silence as stale and worker interruption as
unknown, and recover a serving worker without inflated logical measurements.
Keep the 16-position evidence and existing direct monitor intact. Use the same
position versions, identity, unit conversions and pinned runtime/dependencies.
One local run is capped at one hour and 3,600 selected positions, sampled at
approximately 1 Hz. This is an operating guard, not a throughput benchmark.

## Selected design and alternatives

Use a fresh Compose project and separate topics/storage, with independent
collector and archive/serving workers. Keep the existing bounded native Kafka
reader unchanged. Its manual assignment/poll API supports the continuous
worker; inspect source identity and retained bounds at startup and periodically.
Persist raw selected packets before publication, independently archive exact
input observations, validate Flink facts against archived inputs, then write SQL
and verify complete readback before durable output progress advances.

The local Kafka, SeaweedFS, ClickHouse and native workers share Kafka's network
namespace. This lets the existing strictly loopback S3/SQL clients remain
unchanged. Publish only authenticated SQL/S3 and Flink HTTP on host loopback;
Kafka/UDP stay unpublished. The tradeoff is less network separation inside this
already trusted local experiment. Device-network participants can reach the
namespace listeners; this is not suitable for a shared/untrusted deployment.
No new proxy, framework, dependency or cloud service is introduced. A host-only
serving daemon would bypass Compose lifecycle ownership; weakening existing
transport guards for general remote endpoints is unnecessary for this result.
Fresh volumes require roughly the same configured 8 GiB as ADR-0046 plus two
256 MiB workers. Stop the previous integration services without deleting data.

Flink runs an unbounded Kafka source with a fixed maximum admitted source offset.
Checkpointing remains enabled and output at least once. SQL deduplicates complete
source coordinates and measurement identities only after conflict validation.
Receiver status and SQL bridge heartbeats use explicit local receipt clocks,
separate from native boot measurement time. Expired/future receipt clocks clear
current values; retained historical rows never establish freshness. Collector
sequence reuse cannot renew receipt age. Source silence and processing backlog
have separate statuses.

## Evidence and rollback

Demonstrate continuing SQL increments, source stream stop/resume, and SIGKILL of
the archive/serving worker after SQL acknowledgement but before output progress.
Resume from retained archive receipts/cursors, reread outputs and verify exact
content and unique counts. Preserve every failed attempt and all selected packet
evidence. Recovery while the source continues may expose a gap or backlog; never
claim exactly once, complete acquisition, physical clock admission or production
availability. Collector ambiguous-publication recovery and Flink/broker/host
failure remain separate unless actually tested. Rollback stops this new project
and only its added MAVLink stream, retaining volumes and local evidence.
