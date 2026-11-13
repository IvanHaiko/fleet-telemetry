# Development roadmap

## Simple local installation priority, 2026-11-11

The default user setup is now one computer, one Kafka broker, 12 partitions per
topic and a small Flink session cluster under [ADR-0051](adr/0051-single-machine-default.md).
The [starter](local-development.md) is the public entry point. The older host
placement below remains experiment history rather than an onboarding requirement.

Deliver the integrated GPS/battery/state, archive and serving responsibilities
within this single-machine profile, with explicit memory/disk budgets and one
start/status/stop flow. Complete a small progressing source-to-query result before
extending it to the full recording. Preserve source identity, native clocks,
independent evidence and query deduplication. Distribution/capacity experiments
are optional follow-up work and do not gate a new user's first run.

## Bounded integration update, 2026-11-11

The first integrated F09 interval described below has now run locally.
[ADR-0050](adr/0050-integrated-f09-runtime.md#local-evidence-2026-11-11) records
advancing SQL, exact independent archival, the serving pause/resume boundary,
538 logical facts and duplicate-safe SQL retry. This is bounded evidence for
the selected interval, not full MVP or full-flight acceptance. Its 4,096-delivery
guard and untested checkpoint restoration remain in force.

The next product increment is full-recording operation under reviewed resource
and evidence bounds, followed by the remaining recovery/lifecycle criteria below.
Repository publication preparation adds no new milestone or runtime acceptance.
The maintenance report records its separate checks.

## Integrated MVP priority, 2026-11-10

The maintainer selected the [integrated architecture](architecture.md#integrated-local-mvp-target-2026-11-10)
as the local MVP target and required preservation of reusable data for the larger
platform. [ADR-0048](adr/0048-integrated-mvp-and-evidence-preservation.md) records
this direction. This section takes priority over the older next-task lists;
earlier accepted milestones and their exact evidence remain historical fact.
The successful coach presentation is not full MVP technical acceptance.

The result is one declared, reproducible operating profile: reviewed source,
adapter, Kafka input, independent archive, Flink, output facts, serving worker,
ClickHouse and two dashboards. GPS, battery and recorded state must traverse
that path. Starting containers or refreshing preloaded research tables alone
does not demonstrate it.

The [bounded stream preparation and reference](guides/f09-stream-replay.md) now provide
the first step's offline event/context profiles and GPS-centred expected result.
Pinned checks and a protected 60-second F09 comparison pass. Actual mixed-stream
Kafka/Flink delivery, independent archival and processing-backed SQL/Grafana
remain the next increment; this does not close step 1.

Work in this order:

1. **One bounded F09 interval through the complete path.** Reuse the registered
   original and reviewed field definitions. Define only the necessary versioned
   GPS/battery/state input and processing-fact profiles, clock/association policy,
   ordinal coverage and reference result. Connect independent input archival and
   a serving worker to one fresh scope. Observe changing SQL position, values
   and state through the actual Grafana datasource. Preserve original native
   timestamps, stable measurement IDs and separate association quality. This is
   the next useful increment; do not introduce a generic adapter framework.
2. **One full F09 native-time replay.** Extend the checked interval to the
   approximately 39-minute recording at 1x, under declared storage/resource
   guards. Account for the 21,054 GPS, 11,730 original battery positions (11,723
   admitted and seven value rejections), and 6,981 original state observations.
   These are different streams, not simultaneous snapshots or interchangeable
   row counts. Any intentional selection must declare its exact interval and
   coverage; retained originals still include unprocessed topics.
3. **Prove the selected retry/recovery boundaries.** Reuse existing mechanisms
   and failure evidence. Demonstrate a serving interruption after SQL ACK but
   before cursor publication, pause/resume, duplicate-safe results and an isolated
   archive-only rebuild without resetting the original run. State which broker,
   Flink and host failures remain outside the verified profile.
4. **Connect the reviewed SITL source to the same responsibilities.** Retain
   original capture, source/session identity and untimed/missing-stream limits.
   Show receipt/collector uncertainty correctly during source silence and gateway
   restart. Synthetic fixtures remain for deterministic faults and edge cases;
   they do not replace the real-recording analytics product.
5. **Close MVP operations and evidence.** One documented start/status/stop flow
   must verify brokers, the actual Flink job, archive/serving workers, datasource
   readiness and advancing traffic. Save evidence before history/retention can
   discard it. Provide an operator runbook and a checked restoration procedure.

The MVP is ready only when the selected profiles meet all of these observable
criteria:

- Source identities, units, native time, interpretation versions, dispositions
  and quality agree from retained input through archive, processing and SQL.
  Exact content/identity reconciliation supports completion; matching totals alone
  and broker ACKs alone do not.
- The telemetry dashboard queries processed ClickHouse results for a progressing
  replay/capture, including GPS/map, speed, altitude, battery and recorded state
  where supported. A retained marker stays labelled historical/paused/stale as
  applicable; unsupported values and expired current state remain unknown.
- System monitoring covers source admission/rejections, duplicate/late results,
  verified archive coverage and lag, serving progress, processing/checkpoint
  failures, Kafka health and both hosts' declared resource/disk budgets. Missing
  instrumentation stays unknown. Any unsupported signal is an explicit remaining
  gate rather than a zero or a green component-health substitute.
- Restart/retry preserves stable identities and duplicate-safe analytical values.
  Isolated reconstruction uses retained evidence; rollback stops the selected
  profile without deleting original data, topics, state or unrelated projects.
- Each run has a checksummed artifact inventory, source/normalization/software
  lineage, coverage/reconciliation status and retained operational evidence.
  A stopped partial run states its actual interval; it is never relabelled as
  full recording completion.
- Operating limits, selected failure consequences, measured latency/resource
  results and untested boundaries are documented. Capture-to-UI refresh, source
  age and publication-to-SQL visibility are separate quantities. No production
  availability or end-to-end exactly-once guarantee follows from this MVP.

The broader platform can later add reviewed sources/fields, multi-vehicle
analytics, longer retention/operation, wider recovery domains and optional AWS
deployment. [Preservation rules](deployment-and-terraform.md#run-evidence-and-retention-policy-2026-11-10)
apply now so those increments can reuse original data and measured run evidence.
This priority does not authorize cloud resources, new services/dependencies,
destructive cleanup, commits, publication or restarting the stopped runtime.

## Active product goal, 2026-11-04

The maintainer's next useful intermediate result is: connect a supported source,
log or civilian drone, see its state, and calculate telemetry correctly. This
product goal takes priority over the older continuation lists below. Historical
acceptance evidence and remaining milestone gates retain their original scope.

"Any source" means a reviewed adapter to shared telemetry meanings and views,
not automatic interpretation of unknown fields, firmware, units or clocks.
Unsupported sources must produce an explicit refusal or missing capability.

Work in this order, completing a visible result before broadening the system:

1. One command prepares the retained F09 original into a combined GPS, battery
   and recorded-state inspection, with identities, source coverage, rejected
   measurements, separate association statuses and explicit native-time ages.
   Show the corresponding combined inspection in the existing Grafana view.
2. Admit a second real log through the same entry point and shared view without
   editing SQL or dashboards per recording. Review its exact firmware, source
   rights, field meanings and time mapping before enabling its adapter. Missing
   streams remain unknown. Preserve distinct recording and vehicle identities.
3. Connect one actual live MAVLink source through a reviewed gateway and show
   latest values, measurement age and independently observed connection state.
   Demonstrate radio/source silence, gateway restart and recovery without
   displaying retained history as fresh or assigning new measurement identities.
4. Join the real-source path to retained source evidence, Kafka, Flink, archive
   and query serving. Reconcile identities and values, then demonstrate one
   retry/failure without inflated results or hidden loss.

Acceptance requires a documented local connection command; position, battery
and recorded state where available; units, timestamp meanings and quality per
value; explicit unknown/stale/gap states; stable identities on replay; and
source-to-result reconciliation. State durations, distance and flight phases
must wait for reviewed definitions and adequate clock/coverage evidence.

Do not divert into another load benchmark, infrastructure expansion, generic
adapter framework or helper acceptance cycle unless a concrete blocker prevents
the next result above. Existing protections remain in force. New dependencies,
cloud work, destructive cleanup, commits and publication need their existing
separate justification or authorization.

**Current increment:** items 1 and 2 are implemented and checked for the exact
F09/F01 historical research profiles: [shared command, SQL admission and
recording-selectable view](guides/two-recording-view.md). F01 contributes 118 original
state records and 77 commander-timeline observations, with empty GPS and missing
battery explicitly preserved. All 21,131 combined observations reconcile through
separate SQL reader readback; identical replays add no rows and competing content
refuses. The native-time UI switches recordings without per-recording SQL edits.
Item 3's live-protocol scenario is now demonstrated using the maintainer-selected
[PX4 SITL live source](guides/live-px4-mavlink.md): position/battery/state receipt ages,
sender silence/resume, and gateway restart with unknown until new packets pass.
This is a running simulator, not a physical drone or RF test. Native identity,
missing time and unsigned-transport limits remain explicit. Item 4 now has a
[bounded live position result](guides/live-position-source-query.md): 16 new native-time
measurements, two repeated deliveries, exact Kafka/Flink receipts, retained raw
packets, independent S3 readback and complete SQL content reconciliation.
Repeated SQL insertion preserves 16 logical measurements. The follow-up
[guarded continuous position session](guides/continuous-position.md) now records new
measurements through archive/SQL, shows source heartbeat loss as stale/NULL and
worker interruption as unknown/NULL, then recovers the SQL-acknowledged-write
window without inflated logical results. Its exact verified prefix is 78
deliveries/77 measurements; recording continues within a one-hour/3,600-delivery
guard. The [live Grafana screen](guides/continuous-position.md#live-grafana-screen) now
shows that SQL-backed state, heartbeat and four position charts, with five-second
refresh and separate native-clock history. A missing status-file race was fixed
and the stopped store recovered its backlog without resetting data. Next extend
the reviewed live view to additional available streams while preserving missing
measurement time and source-specific identity rules.
Unknown firmware, physical producer/clock admission, authenticated device
transport and broader Flink/broker/host recovery remain open; no M6/M7 completion
is implied.

## How to use this plan

M0 is the documentation foundation delivered in this directory. M1-M7 define the
local Version 1 release. M1 includes pure normalization, a bounded integrity
gate, an optional pinned reader and local file conversion. CI is configured;
hosted execution and real-source acceptance remain pending. M2 is accepted for
the local synthetic ingestion profile under ADR-0017; M3 is accepted for the bounded local synthetic profile under
ADR-0022/0023 and its evidence. M4 is accepted for
the closed bounded synthetic profile under ADR-0032. M5 is
accepted for the [bounded local reliability profiles](case-studies/m5-reliability.md); M6-M7 are pending.
M8 is an optional Terraform / AWS
extension. Version 2 Edge AI research requires a separate scope decision.

Each task should deliver one observable result before the next component is introduced. Milestones have dependencies and exit criteria, not fixed dates. Tests, instrumentation and CI start with executable work; later milestones expand their coverage rather than postponing them.

## Active continuation and proportional delivery, 2026-10-26

Prioritize the useful integrated result over more verification infrastructure.
This is the active order for the next local increments; the milestone criteria
below remain unchanged. Completed archive, processing, projection and event-sink
work is reused. Existing evidence is retained rather than rebuilt by default.

1. Connect one tiny authored synthetic fixture through source admission, Kafka,
   the existing Flink processing and ClickHouse, with the existing independent
   archive path. Integrate only the window/disposition behavior needed for that
   scenario. Prefer existing components and runtime controls to another general
   supervisor, protocol layer or separately accepted helper library.
2. Demonstrate three useful queries on that same run: vehicle/window battery
   trends, valid/missing measurement coverage and quality/late dispositions.
   Reconcile exact identities, stable content and aggregate values with the
   existing reference; equal counts alone are insufficient.
3. Exercise one representative integrated retry/failure scenario and show that
   the approved query result remains correct or loss is explicitly reported.
   Reuse existing lost-ACK and archive recovery evidence where applicable.
   Review the completed increment as a coherent change, then assess all remaining
   M4 criteria explicitly. One failure demonstration does not waive other required
   acceptance evidence or establish production durability.

For routine small changes use one session and relevant existing checks. For
medium changes use an explicit scope, implementation and focused validation.
Independent review belongs at a completed meaningful increment when risk
justifies it. Frozen tests and strict isolated roles require a concrete reason
for blindness or enforced read-only review; they are not per-function gates.
The working principle is recorded in [the contributor guide](../CONTRIBUTING.md)
and the [verification policy](testing-strategy.md#verification-effort-proportional-to-risk).

Defer additional generic runners, abstractions, formats and broad test matrices
until an observed blocker or necessary requirement justifies their cost. Retain
existing timeouts, resource limits, data-preservation checks and safe refusals.
Fix a demonstrated correctness or safety blocker when needed; do not remove
protections to make the scenario appear complete. No service launch, cloud
action, storage cleanup, Git commit or publication is authorized by this plan
update. M4 was open at that plan-update boundary; its subsequent bounded
acceptance is recorded below.

The tiny integrated slice now demonstrates the first
three active steps for the existing terminal-reference fixture: real source
admission/Kafka, independent S3 archive, Flink, canonical events and reconciled
window/disposition SQL, including ambiguous-write/rebatch retry. Its criterion
ledger recorded M4 as open at that integration boundary. The next task was
Kafka-inaccessible archive reconstruction into an isolated serving run and sealed
query admission; the subsequent completion below closes those local items. No additional
helper acceptance cycle is needed before that useful scenario.

The bounded M4 acceptance now closes that active M4 work:
Kafka-inaccessible reconstruction, isolated serving replay, immutable seals,
exact approved reports, changed-batch retries and fresh replacement readback pass.
The subsequent [bounded M5 reliability profiles](case-studies/m5-reliability.md) establish
positive online-late behavior and the scoped recovery outcomes below. The next
milestone is M6. The terminal bounded-reference policy remains explicit;
production admission stays separate and no cloud action is authorized.

## Ordered continuation, 2026-10-22

This is the maintainer-authorized ten-step path to the local V1 release.
Each row is an observable work package, not an individual helper or module.
Its evidence demonstrates that result, not a
claim that the entire milestone has passed. M1 provenance/rights review can
advance in parallel; hosted CI still depends on maintainer publication.

| Step | Observable result | Current state |
| --- | --- | --- |
| 1 | Archive format, interfaces, catalog/commit protocol, resource limits and acceptance inputs | Design prepared in [ADR-0021](adr/0021-bounded-archive-format.md) and [archive v1](reference/archive-format-v1.md); proposed, with artifact/live acceptance gates open |
| 2 | Multi-input idle/resume and watermark behavior matches the independent reference | Real two-partition Kafka evidence accepted; earlier loopback evidence retained |
| 3 | Persistent Flink/source-state recovery and measured resource bounds; explicit M3 acceptance | Accepted for bounded local synthetic M3 on 2026-10-22; evidence and limits |
| 4 | Independent source/observation archive with readback before offset commit | Bounded Linux fixture implemented and verified in runtime evidence; production gates remain open |
| 5 | Archive-only isolated rebuild after Kafka expiry; normal recovery refuses gaps | Bounded local evidence passes in archive runtime; production durability remains open |
| 6 | ClickHouse retry/ambiguous-ACK and unique-read proof before adoption | Bounded canonical event library and actual retry/readback evidence pass in event sink; complete serving integration remains open |
| 7 | Reconciled source-to-query slice and three useful SQL queries; M4 acceptance | Accepted for the bounded local profile, including archive-only isolated serving replay and sealed reports |
| 8 | Retained whole-slice failure/recovery evidence and runbooks; M5 acceptance | [Bounded local M5 accepted](case-studies/m5-reliability.md); actual gaps are exercised and the Flink expired-input empty-success defect is guarded |
| 9 | Observability, bounded benchmark and retention-response drill; M6 acceptance | Next: instrument the demonstrated slice and measure one declared small workload |
| 10 | Remaining M1 real-source/hosted-CI gates, fresh setup and failure demo; M7 local release | Pending M1-M6 evidence |

Optional M8 AWS/Terraform execution follows the local release only with its
separate purpose, budget and resource authorization. This continuation does not
authorize Git commits/publication, historical storage cleanup or cloud mutations.

## M0 — Project foundation

**Scope:** mission, architectural boundaries, initial contracts, delivery semantics, development rules, test design and infrastructure direction.

**Deliverables:** README, repository working agreements, architecture, data contracts, roadmap, testing strategy, deployment / Terraform plan, future extension notes and four substantive ADRs.

**Dependencies:** repository inspection and the Stage 0 brief. The starting directory was empty and had no Git metadata.

**Acceptance:** another contributor can identify the first task, distinguish proposed choices from guarantees, explain event identity and time semantics, find reliability gates, and see Terraform's role without assuming deployed infrastructure exists.

**Testing expectations:** check relative links, examples, naming, English-only content, decision consistency and scope boundaries. Documentation review does not validate runtime behavior.

**Out of scope:** pipeline code, executable schema validators, configuration placeholders, dependency installation, datasets, services, cloud resources, commits and publication.

## M1 — Data sources and deterministic replay

The [real-flight and simulator inventory](reference/telemetry-source-inventory.md)
compares eight hardware-labeled logs and three SITL logs, and catalogs their
observed topic/field variations. It does not admit any new canonical source;
firmware, identity, time, rights and real-source replay gates remain open.

**Current evidence:** the first synthetic normalization slice
implements one accepted mapping and local unit/contract checks. A second
bounded pure ULog value slice now asserts the authored
ULog-shaped synthetic cases; actual source adoption remains proposed. The
[bounded conversion slice](guides/bounded-conversion.md) adds strict file jobs,
whole-input integrity, an optional pinned reader, outcome reconciliation and
fresh versioned local runs. These features are implemented and have targeted
tests; final verification evidence belongs to that guide. M1 acceptance still
requires hosted CI execution and reviewed real-source evidence. The
[setup/CI follow-up](guides/m1-checks.md) demonstrates fresh project environments on the
same Windows host and prepares the two dependency lanes without adding tests.
The later Linux publication follow-up closes the initial
platform restriction while retaining the no-overwrite contract. The shared
[M1 command](guides/m1-checks.md) now supports Windows and Linux, with both dependency
profiles configured in CI. Local portability evidence does not replace hosted
CI or actual-source acceptance.

**Scope:** one battery measurement mapping, tiny provenance-reviewed inputs, canonical event identity and bounded file replay. Begin with a synthetic native-record fixture and add one public ULog sample only after rights and timestamp review.

**Deliverables:** a supported Python version and minimal pinned toolchain, pure normalization function, versioned mapping / manifest format, a small bounded file conversion command, fixtures, semantic projection definition, unit and contract tests, and a lightweight CI workflow. Select and justify a ULog parser rather than maintaining a binary parser without a need.

**Dependencies:** M0; accepted fixture rights and privacy review before storing public data; documented native battery fields, current sign and clock anchor before the ULog mapping is accepted.

The separate [`ulog-battery-v1` profile](data-contracts.md#proposed-ulog-mapping-ulog-battery-v1)
remains proposed. Its review needs a local discovery result tied to an exact
source checksum, firmware/message definitions and parser version, with streams,
fields, native counts/time bounds and unresolved semantics. Select an explicit
fixed synthetic anchor if reliable UTC is unavailable. Confirm sample-time
precedence, publication fallback only without sample time, native current sign
conversion to the shared canonical convention, scaling, sentinels and
disconnected-record handling before accepting the mapping. Discovery execution,
dataset acquisition and adapter implementation require separate task scope;
this documentation clarification supplies no such evidence.

The subsequent authorized discovery experiment
parsed two upstream test logs and reviewed exact firmware sources. This adds
local inventory evidence, not mapping acceptance, fixture redistribution rights
or adapter implementation. [ADR-0006](adr/0006-ulog-discovery-tooling.md) records
the isolated parser choice. Remaining M1 delivery criteria still apply.

[ADR-0007](adr/0007-ulog-battery-value-policy.md) proposes the primary firmware's
current/disconnected policy with 22 authored synthetic cases and separate
expected outcomes. The authorized pure mapping now asserts nine admissions and
thirteen rejections, stable identities across delivery runs and failure
boundaries. This pure-slice evidence alone is not binary adapter validation or
M1 acceptance. Producer attribution, rights/privacy and general producer-reader
compatibility remain open. The Python 3.13 parser/embedded-type probe
is complete on two local samples and twelve authored binary experiments. It
exposes silent truncation and shifted row indices after corruption. The
[integrity gate](adr/0008-ulog-input-integrity-gate.md) and
[separately selected reader/converter](adr/0009-bounded-local-conversion.md)
implement the bounded follow-up. The format extension
adds bounded nested layouts and `M`, `L`, `S` to `B`, `F`, `I`, `P`, `A`, `D`,
`O`, at most 16 MiB and 100,000 total frames. The bridge reconciles every
framed stream and preserves selected row ordinals before value filtering.
The optional `ulog` extra pins pyulog `1.2.2` and NumPy `2.3.5`; synthetic file
conversion retains a standard-library runtime. No unrestricted ULog or actual
producer attribution claim follows from these authored-fixture tests.

**Acceptance criteria:**

- The same input, manifest and mapping produce identical ordered event IDs and stable semantic content on two runs with different wall-clock admission times.
- The identity vector in the contract is reproduced exactly. Filtering does not change native ordinals.
- Required fields, missing optional values, source sentinels, invalid timestamps and malformed records have explicit tested dispositions.
- Source and output counts reconcile; unhandled records are visible rather than silently discarded.
- Completed run artifacts can be checked against the external job/source without rewriting output; coordinated manifest/event edits fail exact verification under the recorded runtime.
- Current producer envelopes pass independent consumer admission; optional extensions/missing nullable fields remain compatible while invalid identity/time/unit relations fail visibly.
- A fresh environment can run the documented bounded command and tests without Kafka, Docker or cloud access.

**Testing expectations:** pure-function unit tests, checked contract examples, old/new reader fixtures where relevant, deterministic ordering and golden semantic projections, explicit time-anchor and invalid-value cases. Keep reference expectations independent of the implementation.

**Out of scope:** producers, brokers, Flink, object stores, analytical databases, live simulation and infrastructure provisioning.

The [canonical reader](guides/canonical-reader.md) implements this consumer boundary
under ADR-0011. Current producer/golden scenarios are reused; focused new checks
cover only consumer-boundary risks. Per-envelope validation does not complete
source adoption or transport conflict/deduplication acceptance.

The [read-only verifier](guides/run-verification.md) reuses current golden/binary/CLI
scenarios and adds one focused artifact-tampering regression. The upstream
history review leaves primary-source provenance and usage evidence open.

The 2026-10-27 real ULog review now acquires a separate
unchanged CC BY 4.0 IDF_DS research flight, pins its firmware/embedded definition,
and measures GPS clock variation. Source/license discovery for restricted local
analysis is complete. Actual canonical admission remains pending: this file
exceeds current byte/frame caps, contains unsupported Q messages and needs a
new firmware profile plus a reviewed time mapping. The next real-source increment
is bounded full-input support and two reconciled conversions for this exact
candidate; no real-source M1 completion is claimed.

## M2 — Kafka streaming ingestion

**Status:** accepted on 2026-10-21 for the local synthetic ingestion profile only,
under [ADR-0017](adr/0017-synthetic-m2-acceptance.md). Real-source and hosted gates
remain required for release. The acceptance ledger records the
fresh matrix, metrics, publication verification and independent review.

**Evidence history:** [ADR-0012](adr/0012-kafka-ingestion-candidate.md) and the
compatibility plan select Kafka 4.4.0. The authorized
synthetic-only local probe, using the
[ADR-0013 image route](adr/0013-local-kafka-release-image.md), verifies three
event acknowledgements, exact reads, receipt-before-commit and clean consumer
reopen at offset 3. This scoped experiment does not complete M2, waive full M1
acceptance or authorize actual-source ULog use. Hosted CI and real-source gates
remain open. Consumer receipt recovery now passes
the two before/after-commit process exits and corrupt-receipt checks under
[ADR-0014](adr/0014-bounded-consumer-receipt-recovery.md). The
retained-record broker restart passes for one graceful
restart on the original volume. An isolated retention-gap check
now verifies explicit failure for expired required offsets without resetting
progress. One [abrupt broker JVM exit](case-studies/kafka-broker-sigkill.md) also preserves the
captured records and committed offset on the same volume. The
consolidated local cycle also verifies producer
ACK-before-receipt interruption/retry and duplicate reconciliation, unavailable
endpoint/queue-full failure, and both M1 dependency profiles. Lost broker ACKs,
rebalances, host/disk loss, service CI and full M2 deliverables remain open. The
operational evidence increment inventories those gaps and
adds offline exact-byte consumer receipt inspection with scoped accounting.
The subsequent producer audit adds a versioned
publication accounting manifest for the fixed retry protocol, with read-only
verification from source and original evidence. The later
acceptance cycle now verifies runtime metrics, manifest
integration and a fresh full broker matrix. Broker CI is configured separately
from its unexecuted hosted result. General publication/progress remains outside
the bounded protocol. [ADR-0017](adr/0017-synthetic-m2-acceptance.md) records
scoped local synthetic acceptance and its limited sequencing change.
Offline consistency alone is not present
broker recovery evidence.

**Scope:** admit M1 events to a single local broker, define topic and partition behavior, and demonstrate consumer offset recovery.

**Deliverables:** pinned broker / client matrix, minimal Compose setup, topic definitions, bounded producer and inspection consumer, documented listener addresses, run-level publication manifest and relevant CI integration checks. Add metrics / structured logs for delivery attempts, acknowledgements, errors and consumer progress.

**Dependencies:** the validated M1 synthetic source/file/reader boundary for this
profile, under ADR-0017; a checked Windows / WSL2 execution environment and
persistence directory; a deliberate broker/client version choice. Full M1
real-source acceptance and hosted execution remain release/source gates. M2 has
no permanent event archive, so claims are limited to the retained Kafka interval.

**Acceptance criteria:**

- A fixed event set is acknowledged and consumed with the documented vehicle key and matching semantic content.
- Producer retry and consumer restart experiments expose duplicates without hiding missing identities.
- Acknowledged publication and processing progress are distinguished. Offsets are committed only at the declared consumer boundary.
- Broker restart preserves the tested retained data on its named volume; no high-availability claim follows.
- An offset outside retention produces an explicit failure, never an unnoticed reset to latest.

**Testing expectations:** real broker integration tests for keys, offsets, restart, idempotence settings, duplicate injection and retention gaps. Add a bounded multi-partition probe only when testing ordering or rebalances requires it.

**Out of scope:** production clusters, distributed availability, stream calculations, dashboards and cloud deployment.

## M3 — Flink processing

**Current acceptance:** bounded local synthetic M3 passes under
[ADR-0022](adr/0022-persistent-m3-completion.md) and
[ADR-0023](adr/0023-bounded-kafka-enumerator-backport.md). The
acceptance guide owns exact runtime evidence,
state/memory limits, backport provenance and remaining release/production gates.
Earlier experiments below retain their original scope and failures.

**First slice:** the [bounded window reference](reference/m3-window-reference.md) defines
controlled arrival/watermark expectations independently of a Flink job. It adds
no service and proves no runtime recovery.
[ADR-0018](adr/0018-flink-processing-candidate.md) records the maintainer's PyFlink
direction: candidate 2.2.1 in separate Python 3.12, Java 17 and Kafka connector
5.0.0-2.2 for the spike. The isolated compatibility profile
now pins and installs Python 3.12.13, Temurin 17.0.20.1+1 and the complete
dependency/JAR boundary. Real Python SDK worker execution, timestamp assignment, invalid
side output and finite Kafka reads with source metadata/hashes pass. The
finite battery operator now compares managed identity
state, conflicts, ten-second summaries and terminal cleanup with the reference.
The paced watermark follow-up now verifies observed
single-input window/expiry boundaries, late/duplicate/conflict precedence and
finite state-budget refusal. The checkpoint follow-up
now demonstrates completed-checkpoint state/source restore after independent
Python worker termination and exact finite results on isolated storage. The
initial shared-broker attempt expired historical test records, so original-scope
preservation and original-scope acceptance failed. That transient profile did
not prove Kafka idleness, persistent recovery or measured limits; the new bounded
acceptance above adds those proofs without repairing the lost history.
Host/disk-loss durability remains outside the accepted local profile.
[ADR-0019](adr/0019-isolated-checkpoint-broker.md) defines the new storage boundary.

The subsequent two-input experiment observes the active
minimum, 30-second idle exclusion, late events on resume, no regression and no
EOF from all-input silence. Five windows and ten identities match the unchanged
reference. It reuses bounded loopback sources, not Kafka partitions. The
connector/split-specific idle/resume scenario remains required before claiming
that M3 criterion complete from that experiment alone. The accepted persistent
profile above supplies separate Kafka, recovery and measured-limit evidence.

**Scope:** typed validation, event-time windows, bounded keyed deduplication, late-event handling and checkpoint recovery on a small input.

**Deliverables:** an ADR update selecting the Flink API / JVM / Kafka connector combination, one battery aggregation job, reference calculations, operational side outputs, persistent local checkpoint storage and a documented terminal-window procedure for bounded tests. Pin mapping, pipeline and policy versions per run.

**Dependencies:** M2; successful compatibility spike; explicit timestamp precision conversion and watermark policy. Use a persistent mounted filesystem for the first checkpoint experiment if the S3-compatible store is not introduced until M4.

The accepted local synthetic M2 profile satisfies this sequencing dependency
under ADR-0017. ADR-0018 separately selects the PyFlink experiment; neither
decision accepts real-source use or completes the processing milestone.

**Acceptance criteria:**

- Ten-second battery windows match an independent bounded reference for a controlled arrival / watermark schedule, including counts of non-null values.
- Duplicate identities do not inflate results within the declared horizon; conflicting content invalidates the run.
- On-time, late, invalid and duplicate dispositions match the documented precedence and boundary tests.
- A completed checkpoint restores state and input progress after process termination; final normalized results match the reference.
- Idle partitions, resumed partitions, future timestamps, state cleanup and final-window flushing have visible tested behavior.

**Testing expectations:** operator / integration tests for event-time boundaries and terminal watermarks; real Kafka recovery tests for restored progress and rebalances; state-size checks under a stalled watermark. Keep sink expectations limited to test outputs until M4.

**Out of scope:** a claimed end-to-end exactly-once guarantee, a broad telemetry model, a custom stream-processing framework and live device control.

## M4 — Storage and analytics

**Current acceptance, 2026-10-26:** M4 is accepted for the
closed bounded local synthetic battery profile under ADR-0032. The historical
increments below retain their original scopes. The criterion ledger links all
required local evidence; production admission, capacity, real-source/release and
positive online-late M5 work remain open.

**Scope:** finish the smallest useful vertical slice: source evidence, Kafka observation archive, Flink transformation, analytical facts and SQL reconciliation.

The [retention investigation](case-studies/kafka-retention-incident.md) makes archive readback
and expired-Kafka rebuild evidence an explicit production gate. Local quarantine
is implemented; a durable archive, workload-derived time/size budget and exercised
alert response remain unimplemented. Longer Kafka retention cannot satisfy the
whole gate or reverse historical loss.

The proposed [archive contract](reference/archive-recovery-contract.md) specifies the first
bounded readback/expiry/rebuild scenario. The [production gate](guides/production-recovery-gate.md)
provides the evidence ledger, retention/disk equations and required alert-response
drill. Preparing these contracts does not waive M3 dependencies or authorize
new services; local backend/format selection and executable evidence remain pending.

[ADR-0020](adr/0020-bounded-tests-and-s3-archive.md) selects Amazon S3 as the final
archive target and bounds local testing to the approximate 10-50 GB range
(50 GiB retained Kafka data planning ceiling). The [fixture profile](guides/local-kafka-fixture-profile.md)
now applies non-expiring settings and storage admission to fresh topics in the
two maintained three-record creators. Tiny live recovery/expiry/restart checks
pass; 50 GiB capacity is unvalidated and expiry tests stay isolated. Existing
topics and broker defaults are unchanged. Local backend/client/format review and archive restore evidence remain
pending; no multi-terabyte test workload or Docker policy platform is required.

The next design step is now prepared in [ADR-0021](adr/0021-bounded-archive-format.md)
and [archive v1](reference/archive-format-v1.md): bounded JSONL/base64, immutable references,
whole-interval catalog sealing and public interfaces. SeaweedFS 4.48 and
Boto3/botocore 1.43.117 are proposed local spike candidates; executable artifact
pins, the transitive lock, live compatibility and independent frozen tests remain
pending. This is design preparation, not M4 execution or acceptance. Continue
with the archive compatibility/frozen-test gate now that bounded synthetic M3
is accepted. No archive runtime is adopted by the M3 acceptance.

M4 execution has begun with the storage compatibility experiment
under [ADR-0024](adr/0024-m4-storage-compatibility.md). Exact distribution/SDK
pins and live conditional-create, permission-denial and restart/readback checks
are recorded. The foundation increment is now accepted:
immutable byte adapter, offline image preparation, observation codec and exact
finite coverage, with frozen test supersessions, independent read-only review
and deterministic acceptance. The archive and serving deliverables below remain
open; this increment does not complete M4. The subsequent
graph/coordination increment now checks trusted catalogs,
finite publication/progress ordering and fresh file reconstruction, including
real S3 readback/restart and a separate restricted reconstruction process. The
smallest next task is the concrete Kafka/S3 runtime and actual expiry/fetch-gap
scenario; synthetic progress ports do not establish broker commits.

The Kafka read-boundary increment now implements and checks
the pure finite source port. Its concrete Windows 2.16.0 candidate fails the
broker-owned full topic-UUID comparison and is not adopted. The subsequent
Linux verification passes full identity,
exact reads and real post-preflight fetch-gap refusal with unchanged progress.
The subsequent [Windows UUID repair](case-studies/windows-kafka-uuid-repair.md) provides a
verified local SDK and M2/M3 pre-client guard, with full Windows UUID, read,
expiry and bounded producer/consumer recovery evidence. The next implementation
gate is guarded native archive-reader admission, before publication or complete
expiry/rebuild claims. The historical audit now
confirms 59 narrowed identities and 18 full matches; affected identity reuse
requires a separate attestation/migration under ADR-0026. M4 remains open.

The subsequent guarded native admission now
implements the concrete read-only adapter for the already verified Linux and
corrected Windows profiles. Seven native boundary methods and the existing
suite pass; real full UUID, exact-read and post-preflight expiry checks preserve
committed progress. The next gate is the finite Kafka/S3 publication command,
protected descriptor retention, parent process deadline and complete archive-only
expiry reconstruction. This admission does not migrate historical identities
or complete M4.

The subsequent bounded archive runtime, under
[ADR-0027](adr/0027-bounded-archive-runtime.md), implements finite publication,
fresh reader verification, protected root retention and actual explicit commits.
Four observed interruption gates retry with changed batching; real post-preflight
expiry refuses without reset, and Kafka-off reconstruction matches the frozen
observation/measurement/reference oracle before and after storage replacement.
Linux has 85 offline methods without skips. Windows shared checks pass with
7 explicit skips and do not admit the Linux command on Windows. The smallest
next task is the separate serving compatibility spike and its decision/acceptance
gate; full M4, host-loss durability and production capacity/response remain open.

The serving experiment now passes live append-only
event/window DDL and trend/coverage/quality queries under lost responses, repeated
writes and changed batching before merges. Conflicts, logical revisions, separate
reader/writer grants and container-replacement readback also pass. The maintainer
explicitly authorized startup after the original refusal. ADR-0028 remains
proposed: independent admission, canonical projection/lineage and a complete
archive-to-query run remain required. Full M4 is open.

The subsequent pure canonical projection scopes full
battery semantics, lossless exact6 refusal and original/target archive lineage.
Its independent tests precede candidate exposure; final review/acceptance is a
separate gate from the earlier live spike. No window/sink integration or full
M4 acceptance is supplied by this increment.

The subsequent event sink increment adds a versioned event
table, synchronous HTTP writer and exact readback from separate credentials.
Frozen normal/optimized and combined checks pass; actual lost response,
changed-batch retry, schema/conflict/missing/extra refusal and replacement
readback pass. Final review/acceptance governs the bounded library. This uses
the public Graph fixture as archive input; live S3-to-query, processing windows,
late dispositions, query admission and a supervised runtime remain separate.
Full M4 remains open.

**Deliverables:** a reviewed S3-compatible local distribution/client; separate
raw and checkpoint namespaces; archive worker with offset receipts; ClickHouse
write/read semantics spike; minimal DDL and unique-read queries; a bounded
restore / replay procedure. Select and pin a Flink storage plugin only if moving
checkpoints to object storage, with its own restore test. The archive SDK does
not require that checkpoint migration. Keep ClickHouse proposed until its gate passes.

**Dependencies:** M3; source manifests from M1; selected archive batch format and receipt algorithm; verified store access and sink client compatibility. Introducing object-store checkpoints requires a restore test, not merely an endpoint change.

**Acceptance criteria:**

- Original bytes and observed Kafka values have checksums and complete declared offset coverage for the fixture run.
- Crashes before and after object, receipt and consumer offset commits recover without an undetected archive gap.
- A lost sink acknowledgement, repeated writes and altered batch boundaries leave logically unique queries unchanged before any background merge.
- Event identity sets and semantic content reconcile across admission, archive and serving. Window results match the declared online or bounded-reference policy.
- Three useful SQL queries work: battery trends per vehicle/window, valid / missing measurement coverage, and data-quality / late-event dispositions by run.
- An isolated archive replay produces the expected stable measurements and does not mix with the original dataset run.
- Archive readback and isolated rebuild pass with the required original Kafka
  offsets unavailable and the source broker inaccessible. Corrupt/missing
  objects, coverage holes and conflicting overlaps fail without complete output.
- Normal recovery refuses expired offsets both before and after preflight,
  without resetting progress; verify the actual selected client/connector path.

**Production admission evidence beyond the bounded fixture:** the declared
failure domain has an independent readable archive; measured workload bounds
justify time retention, per-partition size limits, broker/archive capacity and
catch-up; monitoring exposes conservative remaining time or explicit unknown;
the response drill preserves endangered data within its deadline. Runtime and
storage administration must have a tested enforcement boundary; local Python
quarantine alone is insufficient. All of this evidence remains open.

**Testing expectations:** real object-store and ClickHouse integration, pre-merge query checks, checksum and overlap handling, whole-slice bounded test, and restoration from durable data. If a candidate fails, document the alternative and rerun the gate.

**Out of scope:** a warehouse framework, BI frontend, lakehouse table format, automatic schema registry and incremental materialized-view aggregates without retry correctness proof.

## M5 — Reliability engineering

**Status:** Accepted for the [bounded local synthetic reliability profiles](case-studies/m5-reliability.md)
on 2026-10-26. The evidence ledger distinguishes new fault injections from reused
M2-M4 evidence and missing-state fault models from physical storage destruction.
Production and host-loss recovery remain unvalidated.

**Scope:** failure injection across the completed vertical slice and a precise statement of demonstrated recovery boundaries.

**Deliverables:** repeatable failure scenarios, expected-invariant ledger, bounded reconciliation reports, checkpoint recovery and archive rebuild runbooks, documented retention / deduplication limits and honest failure findings.

**Dependencies:** M4 and retained input / evidence for the chosen failure interval.

**Acceptance criteria:**

- Producer interruption, broker restart, consumer rebalance, Flink termination, checkpoint failure, archive outage and ambiguous sink timeout each have an explicit outcome with retained evidence.
- Duplicates within and beyond the state horizon, late arrivals after idleness, missing records and conflicting identities are detected as specified.
- Failures that exceed retention, erase local volumes, or remove required state terminate with a visible unrecoverable / rebuild condition rather than fabricated success.
- Recovery distinguishes state restoration from backlog catch-up, and reconciles final data after the backlog drains.
- A second isolated rebuild verifies the published deterministic-content claim without requiring identical wall-clock observations.

**Testing expectations:** controlled fault injection at acknowledgement and commit boundaries; repeated runs for timing-sensitive failures; independent identity and aggregate comparisons. Record what the single-node environment cannot test.

**Out of scope:** production chaos infrastructure, multi-zone failover, disaster-recovery claims or automatic destructive reset tools.

## M6 — Observability and benchmarks

The separate simulated position map demonstrates
ten PX4 sources through Kafka and Flink under proposed ADR-0040. This does not
complete M6, validate a ten-aircraft shared simulation or admit real positions.

The 100-vehicle 5-Hz load observation, 2026-11-03,
measures approximately 500 admissions/s for 679 seconds before a declared
TaskManager memory guard stops the run. It records sampled queue differences
and SQL visibility for a subset. The incomplete backlog and acknowledgement
evidence remain unreconciled; the run does not complete M6 or prove capacity.
The [8 GiB follow-up](case-studies/m6-load-500-8g.md) completes one fresh 12-minute run at
the same 100-by-5-Hz rate, with 360,100 exactly reconciled deliveries and
full-event SQL visibility observations. Repetitions, longer runs and remaining
M6 criteria remain open.

The live interface follow-up adds stale/unknown/resumed
measurement states, clock-qualified last-delivery delay and separately observed
heartbeat loss/reconnection. Tiny collector, HTTP, browser-script and headless
browser fixtures validate the UI behavior; real gateway and cross-host clock
evidence remain open. This does not complete M6 or measure current Kafka backlog.

The 2026-10-27 Flink collection repair closes the
known 4,000-sample refusal for the documented 10,638-sample graph shape. Local
and continuous policies now allow 20,000 samples/target with an 8 MB body cap;
threshold warnings and sample/health panels make pressure visible. A short
synthetic Prometheus replay verifies admission, overflow refusal and alert
recovery without Kafka/Flink startup. Actual graph/container/retention and
Grafana checks remain required before broad M6 adoption.

The two-host laboratory preparation, 2026-10-27, is a separate
offline increment for the maintainer's planned Windows 10/SSD/Wi-Fi setup around
2026-10-30. [ADR-0039](adr/0039-two-host-kafka-lab.md) proposes one six-broker
cluster split 3+3 and defines its two-host availability limits. Offline rendering
and explicit endpoint/TLS client settings
are implemented and checked offline; actual target runtime remains unvalidated.
The [complete setup](guides/two-host-setup.md) now implements laptop-processing/PC-storage
recipes, certificate issuance and source/config inventories. Before transfer/startup,
check the actual supported runtime inventory, image transfer, paths, permissions
and disk/memory budget. The first network admission uses at most 128 unique
synthetic observations plus duplicates, exact reconciliation and separate
broker/Wi-Fi interruption recovery. No large replay or M6 completion is implied.

The 2026-10-27 continuous preparation implements the
separate six-broker/eighteen-partition runtime beyond the finite 32-record
driver. Source/archive/query reconciliation, checkpoint restore and explicit
identity replay are demonstrated. The partition-watermark correction
now passes all 20,128 backlog measurements with zero late events and exact
window sums. The separate 2.084 GB load failed in Flink at the identity-state
cap after ten restorations; complete publication and archive progress did not
produce full SQL coverage. The [local diagnosis and v3 repair](case-studies/m6-identity-state-limit.md)
now reproduce downstream watermark coupling and preserve partition-local state.
Eight targeted tests pass. A subsequently authorized isolated full-graph
preflight now passes actual Kafka/restore/expiry/resource and
source/archive/query checks. The new `load2gb005` is publishing; its complete
reconciliation is the next observation. The old decoder uncertainty remains
historical; no repeated-run capacity or full M6 acceptance follows. ADR-0035
remains proposed.

**Status, 2026-10-26:** In progress. The capture exporter
exposes bounded M2 snapshots. The subsequent local monitoring integration
adopts pinned Prometheus/Grafana with native Flink/ClickHouse collection,
twelve checked panels and actual serving target failure/alert/recovery.
Missing pipeline signals and repeated declared-workload benchmarks remain open.
Native operator traffic does not establish unique-visible throughput or
end-to-end latency distributions. No production targets are adopted.

The [first component replay benchmark](case-studies/m6-transport-benchmark.md), 2026-10-27,
adds three 8,192-observation Kafka/ClickHouse repetitions with exact readback,
first-visible samples, declared duplicate rates and bounded resource evidence.
It does not measure the full Flink/archive path or sustained fleet capacity.

The subsequent full-path check passes three maximum-
supported 32-observation terminal-reference runs with exact archive/Flink/SQL
reconciliation and same-parent batch timing. The supported finite path is
checked; a sustained-input/per-event latency profile and remaining live signals
are still required for M6 acceptance.

**Scope:** make reliability behavior inspectable and measure a declared local workload.

**Deliverables:** Prometheus collection, concise Grafana dashboards, actionable alert proposals, metric definitions, load profiles, environment inventory and benchmark reports with raw summaries.

**Dependencies:** M5; instrumentation introduced during M1-M5; a stable version/configuration set. Establish a baseline before choosing numerical performance or alert targets.

**Acceptance criteria:**

- Dashboards expose throughput, end-to-end visibility latency distributions, Kafka lag, watermark progress, archive coverage, checkpoint age/duration, retries and resource use.
- A deliberate failure changes the relevant metric and exposes a cause in safe structured logs.
- Each benchmark declares input count/size, vehicles, skew, payload mix, duplicate/late rates, replay speed, warm-up, measurement duration, repetitions and hardware limits.
- Reports include p50/p95/p99 latency, attempted / acknowledged / unique-visible throughput, recovery time and peak CPU/RAM/disk use with clear denominators.
- History age is reported separately from processing latency. Instrumentation failure and clock limitations are disclosed.

**Testing expectations:** metric arithmetic against known fixtures, label-cardinality review, dashboard queries, alert-condition probes and repeated bounded load experiments. Stop on defined disk/memory pressure rather than forcing an overloaded run.

**Out of scope:** invented service-level objectives, a production monitoring deployment, capacity extrapolation without evidence and hardware comparisons using different workloads.

## M7 — Portfolio release

**Scope:** make the local platform reproducible and its engineering evidence easy to inspect.

**Deliverables:** fresh-setup instructions, pinned dependencies/images/connectors, cumulative CI, a short demo procedure, rights-reviewed sample references, architecture and contract updates, failure / benchmark reports and interview notes explaining trade-offs.

**Dependencies:** M1-M6 acceptance evidence and documented unresolved limitations.

ADR-0017 does not waive real-source adoption or hosted M1/service CI execution:
both remain explicit required gates for this release. The exact F09 file has an
isolated battery replay experiment
under proposed ADR-0041. Its two local replays preserve positions and rejection
evidence, but do not establish producer attribution, real UTC, live ingestion
or general real-source acceptance.

**Acceptance criteria:**

- A fresh supported environment runs the small reference scenario using documented commands.
- CI covers pure logic and contract compatibility, plus an appropriately scoped integration lane. Slow reliability / load suites have an explicit execution procedure.
- README accurately separates implemented capabilities from demonstrated guarantees and future plans.
- All evidence identifies code/configuration versions, dataset checksums and workload; no secrets or unapproved location data are released.
- The demo includes one failure and its recovery, plus a source-to-query reconciliation result.

**Testing expectations:** a fresh-environment rehearsal, link and command review, CI execution and a privacy / secret review of release artifacts. Git publication remains a separate user action.

**Out of scope:** unrequested Git commits or pushes, cloud deployment, AI and unrelated portfolio projects.

## M8 — Optional Terraform-managed AWS deployment

**Scope:** reproduce a justified subset of the platform in AWS after the local release, beginning with a private archive boundary and workload access.

**Deliverables:** a cloud-shape ADR, budget and lifecycle plan, Terraform configuration with provider lock file, isolated state backend / bootstrap procedure, least-privilege roles, plan / apply evidence when authorized, compatibility checks and retention / teardown runbook.

**Dependencies:** M7, a concrete cloud objective, selected region/account/services, cost acceptance and separate authorization for resource creation. See [deployment and Terraform](deployment-and-terraform.md).

**Acceptance criteria:**

- Configuration passes formatting and validation; a reviewed plan matches the intended resource set.
- State access, locking, versioning and recovery procedures are demonstrated independently of workload teardown.
- Authorized deployment passes tiny archive upload/read/replay tests and denies unintended access.
- A second plan shows no unexpected drift; measured cost assumptions and any service limits are recorded.
- Authorized teardown removes disposable resources, preserves explicitly retained evidence/state, and records remaining billable resources.

**Testing expectations:** Terraform checks, plan review, IAM positive / negative probes, S3 compatibility and restore tests, drift checks and a controlled teardown rehearsal. Plans and state are restricted artifacts.

**Out of scope:** cloud resources during M0-M7, Kubernetes by default, a multi-account platform, multi-region availability and automatic release publication.

## First slice and the next implementation task

The pure synthetic battery-record normalization slice is implemented and locally
tested. It accepts one native record, a source manifest, a fixed clock anchor
and delivery metadata, and returns the documented envelope or a local rejection.
See the slice evidence and limitations.

The [bounded local conversion follow-up](guides/bounded-conversion.md) now implements
strict `bounded-conversion-v1` jobs and `bounded-run-v1` results for synthetic
JSON and supported ULog bytes. It admits events or explicit value rejections,
reconciles counts/hashes and stable content, and publishes a fresh Windows/Linux output
directory only after whole-input validation. Its directory name matches the
explicit `dataset_run_id`, with a 64 MiB serialized-output budget. Existing
destinations are refused. Network clients and services remain unimplemented.

The [setup/CI follow-up](guides/m1-checks.md) now runs the existing checks and conversion
command in fresh local project environments. The shared Python runner and
four Windows/Linux dependency lanes extend that setup; hosted execution awaits
maintainer publication. The completed
candidate review identified concrete runtime-format
gaps. The ADR-0010 extension now passes the primary
source's structural and all-stream count boundary, with focused failure checks.
The secondary remains unsupported. The next M1 acceptance task is primary
producer/provenance evidence and an explicitly reviewed real-source manifest. Actual
ULog source acceptance still requires reviewed producer evidence, complete
firmware definitions and usage/redistribution rights; the optional reader does
not close those gates.


## M6 stopped-load optimization follow-up, 2026-10-27

The maintainer stopped `load2gb005` during catch-up. Its publication and archive
cursor cover all 2000128 measurements; SQL coverage is partial and final
reconciliation was not reached. The Battery optimization
removes the measured per-entry MapState read hotspot using typed managed vehicle
state. Local RPC, output-equivalence and invariant checks pass under unchanged
identity/horizon/guard rules. [ADR-0036](adr/0036-managed-vehicle-state.md) remains
proposed: v4 uses fresh state and requires a small full-graph/container-budget
check before another large run. Services remain stopped and all prior evidence
is retained. No new 2 GB load is automatically authorized by this closeout.


## M6 live connection-monitoring increment, 2026-10-27

The maintainer authorized a fast connection-monitoring branch after identifying
that analytical checkpoint visibility is too slow for connection loss. The
standalone local receiver/API/page passes bounded state,
silence/replay/pause/restart and a 128-vehicle one-Hz HTTP/container drill.
[ADR-0037](adr/0037-live-link-watch.md) remains proposed for real-device adoption.
Next: connect an actual live gateway and verify radio/gateway dropout; durable
alarm delivery and receiver failover remain open. Analytical v4 whole-graph
capacity and remaining M6 criteria are not satisfied by this fast-path result.


## M6 live Flink delivery, 2026-10-27

The maintainer required actual low-latency output through Flink. The
live measurement increment passes an isolated eighteen-partition
steady-state trace at 128 observations/s, with API p95 186 ms/p99 309 ms. It adds
an immediate output after Battery and a bounded latest view, preserving historical
transactions and identity/state bounds. Native bridges, six-CPU resource cost,
actual restores and eleven SDK regressions are recorded under proposed
[ADR-0038](adr/0038-flink-live-output.md). Next admission work is a sustained
latency/state/budget profile and real-source integration, not another 2 GB replay.
This does not complete remaining M6 or production recovery criteria.

## Fleet Gold foundation

The bounded read-time overview provides a first generic fleet summary for supported event profiles in one continuous run. It supports the existing battery reader and a proposed synthetic position-file reader. It does not yet establish source completeness, a materialized Gold store, actual position processing-to-serving integration or live-device identity. Next, connect the position profile to the existing pipeline and demonstrate source-to-report reconciliation in an isolated scope.

## Real-source Gold priority, 2026-11-04

Build the first useful Gold report against the retained F09 real-flight log;
use synthetic fixtures only to check invariants and failure behavior. First
review exact firmware field definitions, validity and native-time semantics for
the selected GPS, state and battery fields. Implement a bounded versioned
real-source adapter, preserve source identity and privacy, and reconcile its
readout with original evidence. Then materialize and query a per-recording
report in ClickHouse before adding a fleet aggregate or live adapter. The
real-data assessment
records current availability and limits. The previous simulated-position profile
is a testing experiment, not the target data source.

## Local F09 flight view, 2026-11-04

The restricted real-flight view provides one ClickHouse-backed map and detail dashboards on the retained F09 GPS stream. Existing operations dashboards can use their existing Prometheus network in the same Grafana; that service was stopped during the view check. Dashboard battery/state joins, integrated source-to-archive/Kafka/Flink replay, real-device adapters, shared-deployment security and flight-completeness criteria remain open.

The local F09 research view now includes a coverage and replay report
that checks prepared GPS against ClickHouse row by row and compares two battery
replays. It does not establish an atomic SQL snapshot or a GPS/battery join.

The local F09 battery materialization
adds a read-checked battery table and a restricted native-time association to
GPS with explicit age and rejection-gap behavior. Clock validation, actual
physical sample alignment and complete source coverage remain open.

The local dashboard now displays associated battery values and explicit
association-status counts; its verification and resource correction
retain the research-time and source-completeness limits.

The five-item state increment, 2026-11-04, completes exact
firmware field review, bounded original-file state preparation, separate SQL
materialization/readback, a versioned observed-record summary and Grafana state
tables. The 2,337 land-detector and 4,644 commander records reconcile across two
deliveries and SQL. This remains direct file-to-query research.

The authorized state-to-GPS association
now adds 42,108 fully read-checked pairs, an explicit one-second age limit,
file-neighbor masks around all 15 dropout markers, and Grafana state/age/status
panels. Two reconstructions agree byte for byte and a separate SQL ASOF lookup
agrees on predecessor choice. The subsequent [combined inspection](guides/recording-connection.md)
now preserves each association's distinct status and time meaning. Physical phase
and duration definitions, integrated archive/Kafka/Flink replay, real
clock/producer admission and M6 acceptance remain open.
