# ADR-0048: Integrated local MVP and preservation of reusable evidence

**Status:** Accepted product direction and preservation policy, 2026-11-10.
Implementation, new event profiles and runtime acceptance remain gated by their
own contracts and evidence. No service startup or cloud action is authorized by
this record.

## Context

The maintainer selected the supplied [technology-stack diagram](../mvp-target.png)
as the local MVP target and requested that useful data collected during replays
remain available for the larger platform. The diagram connects Python adapters, Kafka, an
independent archive, Flink, output topics, a serving worker, ClickHouse and two
Grafana views, with separate checkpoints and Prometheus monitoring.

The coach demonstration established useful components but not that complete
multi-stream path. Battery replay used Kafka/Flink; GPS and recorded state used
a separate research loader. Retained topics/volumes and ACKs do not by themselves
establish independently archived transport history or source-to-query coverage.

## Decision

Deliver the existing stack as one integrated, bounded local product. The first
source is the exact reviewed F09 recording, with GPS, battery and recorded state.
Complete this path before adding another benchmark or infrastructure component.
Then connect the reviewed live PX4 SITL profile to the same responsibilities;
synthetic fixtures remain controlled verification inputs. Unsupported fields,
sources and clocks remain explicit rather than receiving fabricated meanings.

For the MVP acceptance path, analytical measurements must reach ClickHouse
through Kafka, Flink and the serving worker, with independently verified input
archive coverage gating serving progress. Direct research loaders remain useful
for exploration, expected-result preparation and comparison. Their preloaded
tables do not certify the streaming path. Flink owns the admitted stateful
calculations and associations; adapters own source interpretation and units.

Preserve complete original ULogs and their provenance, not only the topics
currently displayed. For live capture, declare and retain the selected raw feed,
its capture limits and known gaps. Independently preserve exact admitted Kafka
input observations, rejected/late evidence, processing results and the versions,
configuration references and operational evidence required to explain a run.
Unprocessed bytes can remain uninterpreted until a reviewed adapter needs them.
Retaining bytes does not admit their semantics or prove source completeness.

Every meaningful run needs an inventory of reusable artifacts, retention/storage
ownership, integrity and coverage status, including unavailable evidence. Keep
unique sources and unreconciled evidence protected from automatic cleanup.
Bound acquisition and storage; pause/refuse further admission or expose capture
loss when preservation cannot keep up. This is not unlimited collection or an
unbounded disk-retention promise. The existing local budgets and separate cleanup
authorization remain in force.

## Alternatives and consequences

Keeping the demo as disconnected successful experiments would leave the central
source-to-query behavior unproven. Keeping only ClickHouse aggregates would lose
data needed for new analytics and failure investigation. Parsing every original
topic into a new online schema now would expand the MVP and its workload without
a defined consumer. Instead, retain reusable raw evidence while implementing
only the reviewed streams needed for the current end-to-end result.

Use existing pinned components, clients and validated repairs. This decision
adds no framework, broker, database, lakehouse, AI infrastructure or orchestration
system. It does not require six brokers as an abstract architectural principle;
the current two-host runtime retains that profile until a separately reviewed,
compatible change is justified. Local storage is not off-host durability.
AWS/Terraform and broader source/production admission remain later, separately
authorized work.

No accepted ADR is superseded: existing identity, archive, serving, checkpoint,
research and failure-domain boundaries remain in force. This record sets the
integration priority and evidence policy; it does not rename a research profile
as production or turn a diagram into a correctness guarantee.

## Owners and next increment

[Architecture](../architecture.md#integrated-local-mvp-target-2026-11-10) owns
the component path and current gaps. [Roadmap](../roadmap.md#integrated-mvp-priority-2026-11-10)
owns sequencing and observable acceptance. [Data contracts](../data-contracts.md#preserved-evidence-and-future-reuse-2026-11-10)
own identity, clocks and lineage. [Deployment](../deployment-and-terraform.md#run-evidence-and-retention-policy-2026-11-10)
owns capture/storage inventories and retention. [Testing](../testing-strategy.md#integrated-mvp-evidence-2026-11-10)
owns the required proof.

The next implementation is one bounded F09 interval carrying GPS, battery and
recorded state through the full path, with advancing SQL/Grafana results and
verified archive coverage. Define the necessary versioned stream/fact profiles
before wiring them; preserve all original ordinals, time meanings and uncertainty.
Do not start by building another battery-only replay or a generic adapter layer.
