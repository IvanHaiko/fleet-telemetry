# ADR-0050: Bounded integrated F09 recording runtime

**Status:** Proposed, 2026-11-11. Actual runtime evidence and reviewed code are
required before the selected profile is marked validated.

## Problem and selected boundary

[ADR-0048](0048-integrated-mvp-and-evidence-preservation.md) requires one
source-to-query path. The [offline event/reference preparation](../guides/f09-stream-replay.md)
under [ADR-0049](0049-bounded-f09-stream-events.md) already reproduces a reviewed
60-second F09 interval. It does not make the map a processing-backed result.

Use those separate GPS, battery and state inputs in one ordered Kafka lane,
calculate associations in the existing pinned Flink runtime, independently
archive exact input observations in existing S3-compatible storage, and gate
serving on complete archive readback. Preserve the whole original ULog and the
input/context/software manifests. A new ClickHouse scope and recording-labelled
Grafana dashboard expose the actual processing results. Previous topics,
checkpoints, databases and volumes remain protected.

The two-host six-broker mutual-TLS topology and eighteen-partition topics remain
unchanged. This recording uses input partition zero so native ordering and
equal-time stream precedence remain deterministic. Other input partitions must
stay empty. One checkpointed association lane is sufficient for the declared
interval; this is not a multi-vehicle capacity result or a general late-event
policy. Output may use all eighteen partitions and serving tracks them
separately. Configuration binds cluster/topic UUIDs and retained context hashes.

The runtime caps deliveries/signatures at 4,096 and checkpoint JSON at 16 MiB.
Original measurement IDs, units and native time remain unchanged. No current
aircraft freshness or physical UTC is inferred from replay arrival. The selected
output sink is explicitly at least once; complete readback and logical SQL
deduplication handle retries. Checkpoints do not establish end-to-end exactly
once. Restore, host failure and full-recording operation need their own evidence.

## Alternatives, cost and maintenance

Replaying prejoined snapshots would hide Flink's association responsibility.
A new framework or frontend would add maintenance without closing this path.
Changing broker count/partition policy would mix topology changes with data
integration. Keep existing components, pinned images/clients and repair artifacts.
The new runtime glue owns the explicit F09 envelope, one lane, archive admission,
typed SQL projection and run lifecycle; it does not become a generic adapter
framework. Parser dependencies stay optional for commands that only process
already reviewed events. No package, service or cloud resource is introduced.

## Admission and rollback

Demonstrate advancing SQL before producer completion, actual Grafana datasource
results during the archive pause and after completion, exact archived key/value/header/timestamp/source readback, complete
Flink/reference/SQL identity and content equality, and duplicate-safe SQL retry.
Unavailable archive coverage stalls serving; broker ACKs or matching counts alone
are insufficient. Retain run-scoped progress, errors/checkpoints and resource
observations with explicit gaps. No broad recovery claim follows from a clean run.

Stop only the owned new job/workers and selected Compose services. Retain all
source, evidence, topics, state and data. Do not reset offsets, remove volumes,
replace prior dashboards or publish Git changes as part of this increment.

## Local evidence, 2026-11-11

The selected 60-second interval ran across the existing laptop and PC topology.
The producer acknowledged 1,019 deliveries including two deliberate duplicates;
Flink produced 538 GPS facts. An independent archive reader reconciled all
input observations in 56 segments. With archival stopped, SQL held at 415 facts;
after archival resumed it reached 538. Two repeated SQL inserts raised physical
rows to 540 while the distinct view remained at 538. SQL reached 397 while the
producer was still running. Grafana queries were checked during the pause and
after completion; the browser rendering was checked after completion.

The selected runtime passed 148 tests and focused lint, format, typing and syntax
checks. This is local evidence for this bounded interval, not validation of the
entire architecture. One checkpoint failure was observed. A retained log reports a checkpoint trigger
being aborted because a required source task was not running; its correspondence
to the reported failure count was not independently established. Actual checkpoint
restore and host failure were not demonstrated. The
4,096-delivery limit excludes the complete flight. Original source and run data
remain local; their retention is not an off-host backup.
