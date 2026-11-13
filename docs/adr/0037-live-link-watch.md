# ADR-0037: Independent local live connection monitor

**Status:** Proposed, 2026-10-27. Authorized local implementation and synthetic
HTTP/container checks; real device adoption remains open.

## Problem

The historical analytical path exposes Kafka transactional output after Flink
checkpoints. Its ten-second checkpoint schedule, possible backlog and event-time
watermarks cannot provide prompt loss-of-connection indication. Extra host RAM
does not remove these waiting conditions. Replayed historical data must not make
a drone appear connected.

## Decision

Add an optional, independently scheduled loopback heartbeat receiver using the
existing Python standard library and existing pinned runtime image. A trusted
local live gateway submits actual receive observations directly, before any
historical publication/processing backlog. The receiver uses monotonic deadlines,
a fixed registered fleet and a three-second default timeout, checked every
100 ms. A small authenticated API/page shows connected/lost/unknown status;
the page polls every 250 ms. This is observational monitoring, not flight control.

The new operational `live-heartbeat-v1` contract is separate from canonical
measurement identity. Freshness validation, strictly increasing gateway sequence
and receive timestamp, and a receiver-start epoch refuse stale/repeated input.
Restart and monitor scheduling gaps produce unknown until new input arrives.
Vehicle IDs appear only in protected API data and rotated transition logs.
Prometheus output has four aggregate gauges with no identifier labels.

## Alternatives, cost and boundaries

Shortening analytical windows/checkpoints still couples connection detection to
backlog and transaction completion. A Flink processing-time side output in the
same job shares its failure/backpressure domain. Kafka-only heartbeats introduce
broker availability and consumer catch-up into the indication. Replacing the
analytical sink's exactly-once policy would weaken its existing contract.

The cost is one small optional service, a bounded fleet map, HTTP endpoints and
an explicit live gateway contract. No framework, dependency, broker, database,
image download or extra orchestration system is introduced. Reusing the existing
image avoids another pin, although the image is larger than this service needs.
Compose limits it to 0.5 CPU, 128 MiB, 32 PIDs, sixteen simultaneous requests,
1024-byte bodies and two rotated 2 MiB logs. The default profile is 128 vehicles;
configuration refuses more than 1024. Public exposure, TLS, distributed failover,
durable alarm delivery and an actual MAVLink adapter are outside this increment.

Only a trusted gateway sharing the host clock may publish receive times; it must
not emit heartbeat from a timer independently of actual vehicle input, restamp
buffered observations, or connect historical replay. Credentials authenticate the
gateway, not the physical radio origin. A lost status means no fresh heartbeat
was observed, not proof of a crash or attribution to a specific network hop.

## Validation and rollback

The implementation record binds deterministic deadline,
replay/pause/restart checks and an actual 128-vehicle, one-Hz container trace.
The receiver has no persistent measurement state or dependency on stopped
Kafka/Flink/SQL. Stop its separate Compose project to roll back. No existing
checkpoint, volume, offset, identity cap or measurement contract is migrated.

## UI follow-up, 2026-10-27

The live interface follow-up exposes observed loss and
same-epoch recovery in the heartbeat page. An unavailable or delayed monitor
clears UI transition history rather than claiming a recovery that was not
observed. This does not alter the underlying deadline, gateway trust boundary,
API or proposed decision status.
