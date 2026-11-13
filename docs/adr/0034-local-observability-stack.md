# ADR-0034: Bounded local Prometheus and Grafana collection

**Status:** Accepted for bounded local native collection and dashboards,
2026-10-26, following the live M6 checks. Full M6
and production monitoring admission remain open.

## Problem and decision

M6 needs time-series collection and inspectable dashboards against real local
services. M2 file snapshots cannot show live Flink processing or component
availability. Use the maintained upstream Prometheus collector and Grafana OSS,
with Flink's already bundled 2.2.1 Prometheus reporter and ClickHouse's native
Prometheus endpoint. Keep application identities and payloads outside metrics.
Do not introduce a new exporter SDK, JMX agent, Docker socket proxy, monitoring
operator or custom REST bridge for signals already provided upstream.

The existing image's entrypoint does not process stock Docker `FLINK_PROPERTIES`.
Replacing its configuration reproduced a JVM module-access submission failure
because image preparation appends required options. The selected eight-line
wrapper copies the complete original configuration into tmpfs and appends only
the reporter settings. A separate derived image or maintained configuration
fork adds more maintenance. Prefix equality with the image configuration and
actual successful job execution validate this small wrapper; it changes no
connector, graph UID, serializer or checkpoint format.

Candidate official Linux amd64 artifacts, resolved from upstream manifests:

| Component | Version | Immutable manifest digest |
| --- | --- | --- |
| Prometheus | 3.13.5, upstream LTS line | `sha256:dc30314819e04a1a3d18d0b37eaa9c8e4e18f33f026e3e2d81bf127c7cddcd55` |
| Grafana OSS | 13.2.4 | `sha256:7b22f3edf947329d75eba7a62d9f6ea1ac1e786736813ef7a98cfb275a52e49b` |

Use `prom/prometheus` (Apache-2.0) and `grafana/grafana` (AGPL-3.0), not the
Enterprise edition or third-party repackaging. Source and license references:
[Prometheus releases](https://prometheus.io/download/),
[Prometheus source](https://github.com/prometheus/prometheus),
[Grafana release](https://grafana.com/grafana/download?edition=oss),
[Grafana source/license](https://github.com/grafana/grafana),
[official images](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/).
This adds no cloud subscription or hosted service.

## Alternatives and costs

Keeping only JSONL evidence has the lowest runtime cost but cannot validate
dashboard queries and alert transitions. A custom collector/UI duplicates
maintained functionality. A broader observability distribution, log aggregation
service, cAdvisor or node exporter adds services/permissions before a demonstrated
need. Host resource inventory and bounded Docker samples remain parent-owned.

Compose owns two new retained data volumes, configuration mounts, a private
monitoring network, a separate UI bridge and two loopback UI ports. Each service
has one half CPU and 128 PIDs. Prometheus has 512 MiB RAM; Grafana has 768 MiB
and a 384 MiB Go soft memory limit with `GOMAXPROCS=1`. An observed
486.7 MiB Grafana sample approached the initial 512 MiB cap: the container was
stopped before adjusting this budget. Temporary/log storage is bounded. Prometheus
retains two hours or 256 MiB of compacted blocks; WAL/head and filesystem overhead
are additional, so this is not a hard disk cap. Admit at least 4 GiB free workspace
and 4 GiB free Docker storage, record growth and stop on pressure. The fresh
Kafka/Flink/serving profile reuses existing image/resource limits. Do not expand
the declared tiny workload to fit a performance claim.

Maintenance includes two upstream security/update streams, digest refresh with
compatibility checks, provisioned datasource/dashboard schema and PromQL rules.
Keep the first dashboard concise. Drop identity labels before ingestion, cap
samples/labels, and keep native runtime metrics separate from integrity-certified
archive coverage, query visibility and measurement history age.

## Access, validation and rollback

Only loopback UI/REST ports are published. Grafana requires a private bootstrap
password, disables anonymous access, signup, analytics, update checks and plugin
installation. Native scrape endpoints stay unpublished. Monitoring services have
no Docker socket, source bytes, Kafka clients or serving-write credentials.
Local Docker/host administrators remain trusted; this is not shared deployment.

Adoption checks pass: Compose, pinned promtool configuration/rules, provisioned
datasource/dashboard, twelve panel queries through Grafana, label admission,
actual target outage/recovery, firing/resolved alert and safe parent logs.
Memory/disk samples and unchanged SQL content are recorded in the live guide.
All six owned services finish stopped without OOM, with unrelated container
states and every owned volume preserved. For subsequent runs, stop
owned services at completion. Preserve volumes, failure evidence and passwords
outside version control; no automatic `down -v`, offset reset or historical
profile recreation. Rollback stops the new project and removes the overlay
from future invocations. No event schema or persistent application migration.

This decision supplies local monitoring only. Full M6 still needs declared
workload repetitions, latency distributions, archive coverage, actual Kafka
committed lag, recovery/drain times and resource peaks. No SLO or production
monitoring admission follows.

## Collection-budget follow-up, 2026-10-27

The Flink scrape-budget repair raises the finite
per-target sample cap from 4,000 to 20,000 after the documented 10,638-sample
graph no longer fits. It adds an 8 MB body cap, preserves label/split filters,
warns above 16,000 for thirty seconds of healthy collection and exposes sample
counts/health. Pinned-tool syntax/rule checks and a short synthetic Prometheus
process prove admission, bounded refusal and alert recovery. This is a local
collection repair under the accepted stack, not a new service, production
capacity decision or new full-pipeline acceptance. The original evidence below
remains historical; actual graph memory/retention and Grafana checks stay open.
