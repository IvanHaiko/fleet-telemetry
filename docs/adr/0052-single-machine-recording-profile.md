# ADR-0052: Single-machine F09 recording profile

**Status:** Proposed, 2026-11-13. The complete flight ran locally on this profile;
see [the run evidence](#complete-flight-run-2026-11-13). The run needed one fix
during execution and leaves SQL write throughput open, so the profile is not
marked validated.

## Problem

Roadmap step 2 needs the complete F09 flight through the integrated path:
Kafka, Flink, an independent archive, archive-gated SQL and Grafana. The maintainer
selected the single-machine placement from
[ADR-0051](0051-single-machine-default.md) for that run. The starter in ADR-0051
deliberately has no archive, SQL or dashboard service. The
[ADR-0050](0050-integrated-f09-runtime.md) runtime was bound to the two-host
six-broker mutual-TLS lab:

- the connection parser accepted only six endpoints;
- the Kafka client checked six brokers and eighteen partitions;
- the Flink job and serving worker hard-coded eighteen partitions.

The 60-second run's configuration was assembled by private scripts on the Linux
hosts and is not in the repository.

## Decision

Add an opt-in profile, `compose/recording.yml` (project `fleet-recording-local`).
It reuses the pinned images already used by earlier milestones:

| Service | Image | Memory | CPUs |
| --- | --- | ---: | ---: |
| Kafka, one KRaft broker/controller | `apache/kafka:4.4.0` (starter digest) | 1 GiB | 1 |
| Flink JobManager | `fleet-telemetry/pyflink-m3:2.2.1-local2` | 1.5 GiB | 1 |
| Flink TaskManager | same | 3 GiB | 2 |
| SeaweedFS archive | `fleet-telemetry/seaweed-m4:4.48-local1` | 768 MiB | 1 |
| ClickHouse serving | `clickhouse/clickhouse-server:26.8.34.13` | 2 GiB | 1 |
| Grafana | `grafana/grafana:13.2.4` | 768 MiB | 1 |
| Archive, serving and publisher workers | new `fleet-telemetry/recording-worker:0.1.0` | 512 MiB each | 1 each |

Steady-state limits total about 10.5 GiB. ClickHouse has `pids_limit: 1024`;
the original 256 failed during the run (see below). The one-shot initializer and job submit
add up to 2 GiB more while they run. The development host's Docker engine reports
22 CPUs and 21.5 GiB. These are configured limits, not measured use; the run
must record actual CPU, memory and volume sizes.

**Topology.** A new connection format, `single-host-kafka-v1`, names one broker
endpoint and a partition count of 1 to 64. The profile uses `kafka:9092` and
12 partitions. With this format, the Kafka client requires exactly one broker
and that partition count. Topics are created with replication factor one and
`min.insync.replicas=1`, with retention disabled so the run cannot expire its
input. The two-host format and the implicit legacy route keep their six-broker,
eighteen-partition checks unchanged. The Flink job and serving worker take the
partition count from the connection.

**Plaintext boundary.** Kafka uses plaintext only on the profile's private
Compose network and publishes no host port. TLS stays required for the two-host
format.

**Loopback storage.** The S3 and ClickHouse clients accept only `127.0.0.1`
endpoints, and this profile keeps that rule. ClickHouse and every worker join the
archive container's network namespace (`network_mode: service:archive`), so S3
and SQL are reached on genuine loopback. SeaweedFS binds S3 to loopback inside
that namespace. Grafana reaches ClickHouse through the `storage` network alias.
Only Grafana (`127.0.0.1:13003`) and the Flink UI (`127.0.0.1:18082`) publish
host ports. Restarting the archive container also detaches the services that
share its namespace, so the profile treats the archive as their lifetime owner.

**Worker image.** The workers need Linux, CPython 3.13 with `confluent-kafka`
2.16.0, and the reviewed S3 lock. The build starts from
`python:3.13.18-slim-trixie` at the digest that `3.13-slim` resolved to on
2026-11-08. It installs only hash-pinned binary wheels from
`runtime/recording/worker-requirements.txt`, without resolving dependencies. It
runs as UID 10001 with a read-only root filesystem. A container keeps the profile
to one start/stop flow on a fresh machine, where a hand-built WSL environment
would not.

**Preparation and initialization.** Two steps replace the private scripts:

1. `runtime/recording/prepare.py` runs on the host, uses only the standard
   library and writes one new private directory. It contains:
   - generated passwords and bucket-scoped S3 identities;
   - the Compose environment file;
   - a dashboard rendered for the run's database;
   - a source manifest with the original, bundle-manifest and reference digests
     and the code revision.

   It derives the run ID from the bundle, because the runtime requires the
   configured run to equal the bundle context.
2. `runtime/continuous/recording_initialize.py` runs once in the worker
   container. It creates:
   - fresh input and output topics;
   - a fresh database, with an INSERT-only writer and a readonly reader whose
     defaults equal the client's query limits;
   - grants for one Grafana identity, whose defaults equal the dashboard's
     limits;
   - a bucket that denies deletion.

   It then writes the publish, archive, serve and job configurations into the
   evidence volume. Any existing topic, database, run user, bucket or evidence
   directory refuses the run instead of being reused. The query defaults matter:
   under `readonly=1`, ClickHouse rejects per-query settings that differ from the
   user's defaults (Code 164). The 60-second run found this.

**Observation.** `runtime/recording/sample_resources.py` samples `docker stats`
and the profile's volume sizes through the Docker CLI only.

## Alternatives, cost and maintenance

- **Reuse the two-host lab.** It needs no code change but keeps the run on a
  topology that ADR-0051 no longer treats as the default.
- **Run workers in WSL.** No worker environment exists on this machine, and
  Windows-to-WSL loopback reachability would need its own check.
- **Allow service names in the storage clients.** This would weaken a deliberate
  loopback-only boundary. A shared network namespace keeps that boundary intact.

The new maintenance surface is one Compose file, one small Dockerfile with a
pinned base digest and hash-pinned wheels, two scripts and one connection
format. The local images, and the Grafana ClickHouse plugin 4.23.2 under
`.local-discovery/gold-grafana-20261104/plugins`, are prerequisites. A fresh
clone does not have them, so this profile is not yet a fresh-clone onboarding
path.

## Rollback and limits

Stop the `fleet-recording-local` project without removing volumes. Topics,
checkpoints, archive objects, SQL tables and evidence remain. Reverting the code
restores the two-host-only behavior; existing two-host configurations are
unaffected because their format and checks did not change.

One broker and local volumes provide no broker or host-loss availability. The
plaintext route is not admitted for any shared or multi-host deployment. Checkpoint
restore, serving interruption and archive-only rebuild remain roadmap step 3.
Building the worker image downloads the base image and seven wheels. Building,
starting the profile and running the replay each need explicit authorization.
The procedure is in [the single-machine run guide](../guides/f09-single-machine-run.md).

## Complete-flight run, 2026-11-13

Run `f09-full-20261113-002` used the preparation at commit `c86d473`. Two fixes
made during the run were uncommitted at the time, and their diffs are retained
with the restricted evidence. The worker image is
`sha256:9d5d95ab70115cf034edf9055deb1c447dfdd8bc5d52f3cd392ffa9d714193e3`.
Inside it, CPython 3.13.18 and `confluent-kafka` 2.16.0 pass the full UUID
boundary check.

**Result.** The publisher paced 39,760 deliveries by native time from 17:41:46
to 18:21:10 UTC. The archive worker read back all 39,760 byte for byte, and
serving completed at 18:39:50. Kafka holds 39,760 input records in partition 0
only, and 21,054 output records across all 12 partitions. Flink suppressed both
declared duplicates and emitted no repeated fact. The independent reconciliation
afterwards gives:

| Check | Result |
| --- | --- |
| Distinct SHA-256 of SQL `fact_json` vs reference lines | 21,054 = 21,054, sets equal |
| Physical rows, distinct identities, DISTINCT view rows | 21,054 each |
| Identities with conflicting content | 0 |
| Battery associations | 21,028 matched, 25 rejection gaps, 1 before first |
| Land-detector associations | 20,883 matched, 122 stale, 49 recording gaps |
| Commander associations | 21,005 matched, 49 recording gaps |
| Last progress row | `completed`, 39,760 input, 21,054 of 21,054 facts |

The association counts equal the retained inspection. Flink completed 359 of 360
checkpoints, and its final state was 6,408,582 bytes. The one failure was the
first trigger at submission, before the source task ran ("Not all required tasks
are currently running"), as in the 60-second run. All 15 dashboard queries ran
through Grafana's ClickHouse datasource at full size: 2,350 one-second buckets,
with NULLs preserved. They also ran as `recording_grafana` with its own
read-only defaults, with no Code 164. The browser rendering was not checked in
this run.

**Archive pause.** `archive-worker` was stopped for about 130 seconds. The
producer advanced from 1,125 to 2,677 deliveries while the archive stayed at
1,104 and SQL stayed at 583 facts. After restart from the durable cursor, the
archive caught up within 30 seconds.

**Failures found and fixed.**

1. The first initialization (`-001`) failed: describing a newly created topic
   raised `KafkaException` before metadata was visible. `Kafka.create` now
   retries only the readback after a successful create, so an existing topic
   still refuses. The empty-topic check retries watermark reads. The `-001`
   input topic stays empty and retained.
2. At 18:08:59 the serving reader got ClickHouse Code 439, "thread constructor
   failed". ClickHouse had reached `pids_limit: 256` at about 17:51, with 239
   global pool threads. Its tracked memory was 526 MB, so memory was not the
   cause. The limit is now 1024, and the peak observed after the change was 292.
   Only ClickHouse was recreated, with its data volume kept. The serving worker
   resumed from its cursor at 18:12:56. The failed read preceded any insert, so
   no physical repeat resulted. This run therefore does not exercise SQL retry
   duplicates.
3. Grafana applies its admin password only when its data volume is first
   created. A later preparation's password does not apply to an existing
   `grafana-data` volume.

**SQL keeps up only for part of the flight.** The lag of SQL behind published GPS
was at most 25 facts up to about 10,000 facts (18:00). It grew to 484 before the
failure, 3,074 after the restart and 3,857 when publishing ended. SQL completed
18 minutes 40 seconds after the last delivery. Serving writes one fact per insert
with two readback queries. Its rate fell from about 18 to about 5 facts per
second as the table grew, below the GPS rate of about 9 per second. Batching
serving writes (the SQL client already admits up to 64) is the next small task.

**Peak resources** from 364 samples at 10-second intervals, with no sample gaps:

| Container | Memory | CPU | PIDs |
| --- | ---: | ---: | ---: |
| ClickHouse | 1,736 MiB of 2 GiB | 103% | 292 |
| TaskManager | 1,122 MiB of 3 GiB | 163% | 128 |
| Kafka | 775 MiB of 1 GiB | 105% | 137 |
| Serving worker | 425 MiB of 512 MiB | 100% | 15 |
| JobManager | 410 MiB | 14% | 65 |
| SeaweedFS | 349 MiB | 40% | 9 |
| Archive worker | 319 MiB | 100% | 9 |
| Publisher | 303 MiB | 100% | 8 |
| Grafana | 237 MiB | 15% | 111 |

Docker's memory figure includes page cache. The workers' 100% CPU is their
polling loops at the one-CPU limit. The volume sizes Docker reported at the end
were 2.3 GB for ClickHouse, 1.95 GB for Kafka, 148 MB for Flink state, 61 MB for
evidence and 27 MB for the archive. These are Docker's reported sizes; this run
did not separate the ClickHouse system-log tables or Kafka's preallocated index
files from the data itself.

**Not established.** Checkpoint restore, broker or host failure, SQL retry
duplicates, browser rendering of the dashboard, and 1x SQL throughput for the
whole flight.
