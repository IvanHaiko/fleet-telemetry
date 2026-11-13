# ADR-0051: One-machine Kafka/Flink default

**Status:** Accepted product/development direction, 2026-11-11. Runtime evidence
applies only to the explicitly checked starter below.

## Problem

The previous onboarding routed readers through a host-specific distributed
experiment. Six brokers, certificate preparation, private source exports and
eighteen-partition job assumptions make a poor fresh-clone starting point.
They are unnecessary for demonstrating the basic streaming responsibilities.

The maintainer selected a simple single-machine default: one broker, about a
dozen partitions and Flink jobs. Historical experiment placement does not define
the product's minimum installation.

## Decision

Use the root `compose.yaml` as the default local development entry point:

- One Kafka 4.4.0 process combines broker and KRaft controller roles.
- Input and output topics each have 12 partitions and replication factor one.
- One Flink 2.2.1 JobManager and one TaskManager run at parallelism two with two
  task slots. Partition count is independent of this execution parallelism.
- A short-lived topic initializer and optional SQL client handle initialization
  and job submission. They are not additional long-running infrastructure.
- Official versioned Kafka/Flink images replace private image prerequisites for
  this starter. The Flink image adds only the already selected SQL Kafka connector
  5.0.0-2.2, verified against its existing recorded SHA-256.
- Only Kafka and the Flink UI publish ports, bound to host loopback. No SSH,
  certificates, private inputs or second computer are required.

The starter's first job consumes existing canonical synthetic battery events,
retains their exact original wire content, IDs and measurement time, projects
values and calculates instantaneous voltage times current in watts. Missing
current yields missing power. This is `local-battery-projection-v1`, a demo result
outside the canonical event contract. It is not the accepted battery window
reference, an energy calculation or a real-source admission gate.

The standard-library CLI reuses the existing converter and reader. A new
delivery-run ID scopes each invocation; it never enters measurement identity.
Readback must match all three current-run measurements, their complete original
content, clock, projected values and power. Earlier runs and matching counts alone
cannot pass. Duplicate deliveries remain logically identifiable; this starter
does not promise duplicate-free physical output.

## Cost, alternatives and limits

The three core containers have combined 4-GiB memory limits. The transient SQL
client adds up to 1 GiB. Recommend allocating at least 6 GiB and four CPUs to
Docker for this profile; these are configuration budgets, not a capacity result.
The first build downloads official images and one connector. There is no host
Java, Maven, PyFlink installation, new Python dependency or custom connector patch.

Keep 12 as a modest explicit starting count rather than copying eighteen-way
partition-specific processing. A single-partition teaching example would hide
partitioned transport; six brokers would reintroduce unnecessary startup cost.
A plain Python consumer would not demonstrate the selected Flink responsibility.

One broker and local volumes provide no broker/host-loss availability. Topic
retention is one hour with 8 MiB per partition plus Kafka segment overhead;
the demo readback refuses beyond its declared 4,096-record scan. Checkpoints and
data survive `stop`; automatic job restoration and production recovery remain
separate work. No archive, SQL or Grafana service is silently started.

This changes the onboarding/default placement, not the original identity,
archival or serving requirements in ADR-0048. Existing research jobs, repairs,
receipts and volumes remain intact. Their fixed topology checks are not relaxed
to make this starter appear compatible. The older proposed topology in ADR-0039
and bounded experiment in ADR-0050 remain historical profile records.

## Rollback and evidence

Stop only the `fleet-telemetry-local` Compose project, without removing volumes.
Reverting this profile does not migrate or delete earlier data. Actual commands,
checks, file scope and remaining limits are recorded in
[the local development guide](../local-development.md).

Upstream references: [Kafka Docker](https://kafka.apache.org/44/getting-started/docker/),
[Flink Docker](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/resource-providers/standalone/docker/)
and [Flink Kafka connector](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/table/kafka/).
