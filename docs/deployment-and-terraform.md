# Local deployment and Terraform plan

## Default development installation, 2026-11-11

Use [the single-machine quickstart](local-development.md) and root `compose.yaml`.
The core is one Kafka broker, 12-partition input/output topics, a Flink JobManager
and one two-slot TaskManager. Short-lived initialization/submission containers
are part of that same Compose project. The three core container memory limits
total 4 GiB; the optional SQL client adds up to 1 GiB. This is a configured budget,
not a throughput or recovery claim.

Only loopback Kafka/REST ports are published. Local plaintext is confined to
development; shared deployment still needs reviewed credentials/TLS boundaries.
Data/checkpoints belong to this new project, and `stop` retains both. Kafka has
one-hour/8-MiB-per-partition retention plus segment overhead; one broker provides
no replication-based availability. Private recordings and existing evidence
must not be placed under its automatically expiring demo topics.

The older multi-host deployment records below remain available for reproducing
their exact experiments. They are not prerequisites for the default installation.
[ADR-0051](adr/0051-single-machine-default.md) owns this updated placement.

## Offline F09 stream commands, 2026-11-10

The [stream preparation/reference commands](guides/f09-stream-replay.md#commands-and-artifacts)
use the existing pinned Python/optional ULog environment and fresh restricted
output directories. They start no services and change no credentials, topics,
offsets, tables or volumes. Originals and prepared inputs remain read-only;
generated measurement artifacts stay in restricted ignored storage. Preserve
failed partial directories and successful manifests rather than overwriting
them. Rollback stops using the commands and retains their inputs/outputs.
This introduces no deployment, infrastructure or dataset migration.

## Run evidence and retention policy, 2026-11-10

The maintainer's [MVP direction](adr/0048-integrated-mvp-and-evidence-preservation.md)
requires collecting reusable evidence while building the current product. This
policy describes the required operating behavior; it does not claim that the
existing demo captures every item or that a new retention controller is installed.
The runtime remains stopped until another explicit startup instruction.

Keep original data and accepted run evidence in restricted, checksummed storage.
Ignored `.local-discovery` directories contain durable research/run artifacts;
their name and Git exclusion do not make them disposable. Do not overwrite an
earlier run or combine its cursors with a new source identity. Store credentials
and private keys separately from portable source/evidence exports. Redacted
configuration references must retain enough non-secret context to reproduce
versions, topology, clocks and resource limits without exposing access material.

| Evidence to preserve | Why it is needed later | Required boundary |
| --- | --- | --- |
| Complete original recordings, acquisition/source manifests, rights/privacy references, firmware and embedded schema definitions | Add reviewed fields or recalculate without repeating acquisition or losing original ordinals | Exact byte hashes and independent readback; unprocessed topics remain original bytes |
| Selected live raw packets/frames and capture configuration | Inspect decoding, gaps, clocks and future adapters | Declare the actual selected set, interval, filters, sampling, capture budget and loss; no claim about unrecorded traffic |
| Exact admitted Kafka input observations and coverage receipts/catalog | Reconstruct transport history after broker retention/replacement | Independent consumer; cluster/topic UUIDs, original key/value/ordered headers/timestamps; storage readback before archive progress |
| Rejections, malformed observations, duplicate/late dispositions and source quality evidence | Reproduce decisions and investigate anomalies without survivor bias | Original references and reason/policy versions; sensitive bytes remain restricted |
| Processing facts and derived analytical results | Compare implementations and reconstruct what the operator saw | Run/source coordinates, measurement references, calculation/association versions, complete content hashes and declared coverage |
| Producer ACKs, archive receipts, serving cursors/readback and final reconciliation | Distinguish acknowledged, archived, processed and query-visible work | Separate stage evidence; partial/unknown progress never becomes complete because counts match |
| Source/code/configuration manifests, dependency locks, image/connector IDs, scenario inputs and lifecycle actions | Reproduce the actual run rather than a later edited workspace | Frozen non-secret inputs; separate private credential references; intended faults and observed outcomes remain distinct |
| Run-scoped metrics, worker/container/host resource samples, errors and checkpoint failure details | Tune capacity, explain failures and establish supported latency/recovery claims | Start capture before traffic; retain the collection interval, units, gaps, clock basis and sampling method |
| Compatible checkpoints and state metadata | Resume the supported processing profile | Separate state lifecycle and source/job binding; checkpoints are not original-data archives |

Preserving processing results does not mean Kafka high-water offsets enumerate
every visible fact. Transactional outputs can contain control/aborted offsets.
Use an explicitly checked coverage profile for their observed data records and
commit visibility; do not apply contiguous non-transactional input assumptions
or certify a complete output archive from a counter. Until such coverage is
admitted, retain available exact result exports and topics with their limitations.

Before a meaningful replay/capture, record a bounded run inventory: selected
source and expected streams/interval, host/device placement, artifact references
and hashes, reader/readback result, actual archive coverage, retention owner,
storage/admission limits and any unavailable evidence. At stop, record the actual
processed interval and pending/unconfirmed boundaries. Original source retention,
verified observation archival, local-only state, and missing coverage must be
distinguishable. Hashing a local file alone does not turn it into a verified S3
archive or an independent backup.

Capture operational history before bounded REST/log/Prometheus retention can
discard it. Preserve checkpoint failures and exception reasons when observed;
a final successful counter cannot reconstruct an expired error history. Export
the relevant metric interval with collection context, or retain an independently
readable equivalent under the run's policy. Retaining a Prometheus volume alone
does not guarantee that old samples survive a later restart/retention cycle.
Never manufacture missing p95/p99, host-memory peaks or end-to-end timing from
snapshots. Component heap/RSS, complete worker memory and host memory/disk are
separate observations.

Keep unique originals, selected benchmark/recovery runs and unreconciled or failed
evidence until a reviewed retention decision and separately authorized cleanup.
No automatic deletion of historical topics, volumes, original logs or run evidence
is introduced. This does not promise infinite retention: assign a finite capture
interval and budget before acquisition. Include all broker replicas, raw sources,
archive copies, SQL projections, metrics, state, exports and free-space reserves
on their actual devices. Preserve the existing 50-GiB retained-Kafka planning
ceiling and stricter host/profile guards; that ceiling is not an enforced quota
or measured capacity for mixed telemetry.

If archive/disk margins cannot support the selected run, reduce its input scope,
pause/refuse new admission, or stop capture with an explicit gap/failure record.
Do not silently delete old evidence or drop unreported observations to keep a
dashboard green. A live source may continue transmitting after admission stops;
those unretained packets remain a declared capture limitation. Expand storage or
add an exporter/service only through the existing documented decision process.

The larger platform should reuse the same originals, identities, lineage and
verified catalogs when adding streams/analytics or changing deployment. Local
SeaweedFS on the PC shares host/device failure risks with other PC data; record
the supported failure domain and verified copies instead of claiming host-loss
durability. AWS/S3 and stronger off-host recovery remain separately authorized.
The existing [production recovery gate](guides/production-recovery-gate.md) still owns
retention margins, preservation response and final recovery admission.

For the stopped 2026-11-10 demo, 7,223 publications are ACK-confirmed and local/PC
artifacts and volumes are retained. The new replay had no independent archive or
SQL consumer and only a checked output prefix. Full per-run metrics export and
three early checkpoint failure details are not established by its snapshots.
Preserve that evidence and those limitations; future runs must connect the
missing collectors/sinks before claiming the full MVP result.

An offline integrity inventory at
`.local-discovery/coach-demo-20261110-001/preservation-inventory.json` now records
57 local F09/demo artifacts (185,880,076 bytes), including the complete registered
original, reviewed definitions, prepared data, source snapshot and run evidence.
The original SHA-256 matches its registered identity. Credentials and private
keys are excluded. PC ACK/topic/volume references are listed as retained but not
rechecked in this inventory; this is not an exhaustive dataset catalog, a new
archive receipt or a proof of independent storage. No runtime was started.

## PC coach dashboards, 2026-11-10

The authorized startup
now serves both coach dashboards from existing PC Grafana through laptop
loopback port 13000 over SSH. Its checked read-only plugin overlay retains the
existing signed ClickHouse plugin and all Grafana data. The owned PC service
helper preserves this overlay and has a saved pre-change copy.
The exact F09 shared projection is loaded/reconciled in fresh PC
`recording_views_v1` tables, using a namespace-scoped writer and a separate
SELECT-only reader. Grafana receives only the reader credential through secure
datasource storage. Existing data and component credentials remain intact.
Stop only the owned services/tunnel for rollback and retain the namespace, users,
plugin, volumes and evidence. No paced Kafka/Flink GPS/state replay or browser
rendering is certified by the successful query checks.

## Live Grafana position connection, 2026-11-04

The [position screen](guides/continuous-position.md#live-grafana-screen) reuses the
existing authenticated Grafana and ClickHouse plugin. Its container reaches
`host.docker.internal:28133` over its existing network; no new attachment,
listener, service, grant or credential rotation was needed. The API-managed
`position-live` datasource uses the current profile's existing SELECT-only
reader and Grafana secure credential storage. The provisioned dashboard has
no secret. Source/store repair exports and all original evidence remain local;
`POSITION_STORE_SOURCE_ROOT` permits a store-only code repair without changing
the collector/Flink source export or resetting persistent state.

## Guarded continuous position runtime, 2026-11-04

The [continuous profile](guides/continuous-position.md) adds two Compose-owned native
workers to the reused pinned position stack in a fresh project. Storage and
workers share Kafka's namespace so existing loopback-only S3/SQL clients remain
unchanged; an access bridge is required for host loopback publishing. Kafka/UDP
are unpublished. The trusted source network can reach namespace listeners, so
this is not shared-deployment isolation. New scoped writer/reader principals
leave old grants untouched. Limits total 8.25 GiB with a one-hour/3,600-delivery
recording guard. Preserve every prior attempt and volume on stop/rollback;
include `--profile worker` when stopping the collector/store services. Broader
recovery and production TLS/ACL gates remain open.

## Bounded live source-to-query profile, 2026-11-04

The [position integration](guides/live-position-source-query.md) uses fresh Compose-owned
Kafka/Flink/S3/ClickHouse storage and existing pinned artifacts. SQL, S3 and Flink
HTTP bind loopback; host Kafka/UDP are unpublished. A temporary PX4 stream enters
the new Kafka namespace through the existing source network and is stopped after
capture. New scoped SQL/S3 credentials do not change historical grants. Configured
limits total 7.75 GiB plus a 256 MiB transient worker. Retain all evidence and
volumes on stop/rollback. This finite local topology has one broker and no host
availability guarantee; continuous recovery and shared-deployment TLS remain open.

## Isolated live PX4 profile, 2026-11-04

The [live MAVLink recipe](guides/live-px4-mavlink.md) uses one new Compose-owned SITL and
receive-only gateway with existing pinned images/dependency artifacts. Only
authenticated HTTP at `127.0.0.1:18771` is published; UDP stays inside the new
checked networks. The gateway access bridge permits egress and is not enforced
full isolation. Old data/services and SQL permissions are untouched. Private
tokens stay in the ignored per-profile config. Stop this profile without volume
or network cleanup on rollback; a restarted simulator needs a new explicit boot
session. Physical devices, shared-deployment security and live archival admission
remain separate gates.

## Two-recording local serving scope, 2026-11-04

The [shared recording view](guides/two-recording-view.md) adds only
`recording_views_v1.observations` and `.recordings` on the existing isolated
research ClickHouse. The maintainer explicitly approved the two-table local load
and SELECT grants to the existing `flight_reader`. No new principal, password,
listener, network, image, service or cloud resource is introduced. Existing
Grafana authentication and loopback HTTP boundaries remain; shared-deployment
TLS/ACL guarantees are not established. Admin secrets stay in the protected
process environment. Local admissions must be serialized, failed/partial scopes
retained, and old/new tables and volumes preserved on rollback. The new registry
is readback admission, not transactional concurrent-writer isolation.

## PC storage and two-host monitoring, 2026-11-03

The actual target admission starts a new
H:-backed PC project for ClickHouse, SeaweedFS, Prometheus and Grafana, and a
separate laptop Flink project. All six native scrape targets work through
authenticated SSH loopback forwarding. Fresh SQL/S3 evidence survives storage
container replacement. Host RAM/disk samples, resource limits, private ACLs,
rollback and remaining startup/runtime gates are recorded there. The subsequent
[PC worker environment](guides/pc-worker-environment.md) admits the native Python,
locked packages and Linux-side storage access; consumers and a complete
Kafka-to-query load remain pending at that boundary. The subsequent
tiny slice actually starts the six-broker candidate,
reconciles 128 measurements through laptop Flink and native PC workers, then
stops the test with state retained. This is not capacity or production adoption.
No historical volume
or checkpoint was migrated and no cloud resource was introduced.

## Live UI follow-up, 2026-10-27

The live interface update keeps the existing loopback
endpoints and separate reader/writer tokens. It adds ephemeral monotonic receipt
ages and a delivery-delay presentation, plus heartbeat recovery labels. Rollback
selects previous source and restarts only the relevant worker; there is no
persistent migration or new service. Actual gateway, cross-host clock bounds and
full graph behavior remain target-deployment checks.

## Bounded monitoring repair, 2026-10-27

The Flink scrape-budget repair changes only existing
monitoring configuration/dashboard/check tooling. It adds no service type or
dependency and preserves current image/container/storage budgets. Short
validation uses the already pinned Prometheus tools and one isolated native
loopback process with a fresh disposable TSDB; historical containers/volumes are
untouched. Load the new files only with the deliberately selected monitoring
profile. Target container memory, cardinality growth and real Grafana queries
remain deployment checks, not evidence supplied by the synthetic replay.

## Deferred two-host laboratory preparation, 2026-10-27

The maintainer authorized offline preparation for a single Kafka cluster split
three brokers on each of the Windows 10 PC and laptop over Wi-Fi. Transfer is
deferred until approximately 2026-10-30. [ADR-0039](adr/0039-two-host-kafka-lab.md)
and the transfer runbook own placement, ports, mutual TLS,
source/image/private-material packaging, resource admission and rollback.
The offline renderer writes Kafka base and host runtime recipes with fresh cluster/volume
names and separate host racks. The client follow-up
implements explicit endpoint/TLS settings with short offline checks; actual
certificate-mounted source/sink admission remains pending. After a read-only
laptop hardware inventory (Core Ultra 7 155H,
31.5 GiB RAM, Windows 11 Home), planned Flink JM/TM and local checkpoints stay
on the laptop; archive, ClickHouse and their workers move to the PC. No measured
throughput comparison is claimed. The [complete setup](guides/two-host-setup.md)
implements host recipes, certificate issuance, restricted role configurations
and source/config ZIP packaging. Only real target admission remains pending;
no network, firewall, service, image, retained data or checkpoint is
changed by preparation. This proposed topology changes none of the historical
single-host evidence below and establishes no host-failure HA.

The initial M6 capture exporter uses the existing Python
environment and one caller-owned loopback listener, default port 19100. It has
no service lifecycle, image/dependency installation, volume or cloud mutation.
Its fixed gauge format is not deployment of Prometheus/Grafana. The subsequent
local monitoring integration implements that separate
increment under ADR-0034 with `compose/m6.yml`, native unpublished scrape ports,
loopback UIs, private credentials and separate retained volumes. A private
monitoring network and a separate UI bridge accommodate Docker Desktop routing.
Measured Grafana pressure causes a stop and documented budget adjustment; no
workload capacity claim follows. All owned services finish stopped and unrelated
projects/retained volumes are preserved.

## Current boundary

The continuous preparation, 2026-10-27, uses a separate
six-broker/eighteen-partition project with the existing pinned services and
trusted host workers. Its authenticated Grafana and runtime remain running for
inspection; earlier finite profiles remain stopped. The authorized shared WSL
limit is now 22 GiB, with 23,084,040,192 bytes reported by Docker after restart.
The guide records ports, memory/PID/disk limits, credentials, corrected Compose
path resolution, retained failures, stop/rollback and current watermark limits.
This adds no cloud resource, dependency installation or shared deployment.

M1 implements bounded local Python commands. Docker Compose now owns an isolated
Kafka 4.4.0 synthetic experiment; the broker was stopped after admission checks,
with its named volume retained. The bounded M3 runtime below is accepted;
the bounded M4 storage/codec foundation below is accepted, while the complete
archive/serving slice and M5-M7 services remain planned.
Terraform belongs to the optional AWS path with separate acceptance criteria.
No cloud bucket, role, backend, network or cluster has been created.

The accepted persistent M3 profile uses
`compose/m3.yml`, fresh per-attempt Kafka/state volumes, standalone JobManager
and TaskManager containers and short-lived submission clients. All owned
services finish stopped. The image reuses pinned installed bytes offline, with
the narrow connector repair in ADR-0023; original images/runtime remain intact.
Loopback ports, non-root/read-only boundaries, exact pins, measured limits and
rollback are documented in ADR-0022 and the acceptance guide. Checkpoint-volume
retention proves tested container/runtime replacement, not host/disk-loss HA.

The M4 storage experiment, under
[ADR-0024](adr/0024-m4-storage-compatibility.md), accepts the bounded
`compose/m4-storage.yml` profile with a verified static SeaweedFS binary and
separately hash-locked local SDK. Only loopback S3 is published; management
endpoints remain unpublished. Its fresh volumes and stopped services are
separate from every historical Kafka profile. Real race, credential-denial and
replacement/readback checks pass. The foundation guide
records adopted adapter/codec/image-preparation commands, reviewed frozen-test
supersessions, read-only review and deterministic acceptance. Raw private
evidence remains ignored. No cloud operation or checkpoint migration occurred.

The following earlier experiment descriptions retain their original scope.
The PyFlink compatibility profile now owns pinned
standalone Python 3.12.13/JDK 17 archives and a separate locked environment in
dedicated native Linux storage under `~/.local/share/fleet-telemetry/pyflink/`.
Downloads and evidence remain in ignored project scratch. Its embedded
MiniCluster uses loopback RPC/REST, one slot, a 1 GiB JVM heap and finite child
deadlines; Python worker memory is additional and no peak is claimed. Jobs
finish after finite collection/offset bounds and their owned process groups
end. This is not a persistent Flink deployment. Compose still owns the existing
Kafka broker lifecycle and any future persistent Flink topology. The Kafka
probe preserves the broker container/image/volume and finishes stopped. No
global interpreter, JDK or workstation configuration was changed.

The finite battery operator reuses that transient
MiniCluster with a bounded synthetic collection and no Kafka startup. Managed
state lasts only for its owned job; no checkpoint path, durable Flink service,
image, package or new deployment resource is introduced. Its finite source
budget is not a measured worker-memory limit or an unbounded-runtime policy.

The paced watermark fixture additionally owns one
transient loopback socket/thread and atomic native-scratch coordination files.
It uses the bundled legacy socket source only to sequence a tiny finite test;
the source is not adopted for application ingestion or checkpoint recovery.
Connection/observation/parent deadlines and listener/thread/process-group
shutdown bound its lifecycle. No Kafka runtime, image or persistent topology is
changed. A checkpoint experiment still needs separately declared Compose
ownership, durable storage and matched source/state recovery evidence.

The two-input idleness check reuses that transient
MiniCluster and bundled source twice, with two random loopback ports and one
owned controller thread. The 30-second idle generator, actual downstream
watermark receipts and explicit EOF coordinate a trace bounded to 128 events
and 1 MiB. A 240-second parent deadline and socket/thread/process-group cleanup
bound each attempt. Native scratch remains under the prepared runtime's owned
`runs/` directory; source exports and reports stay in ignored project evidence.
No broker starts, no historical volume is accessed and no persistent Flink
service is adopted. Memory peaks, Kafka split behavior and recovery remain open.

The checkpoint experiment adds native-filesystem
checkpoints for a transient MiniCluster, not a Compose Flink service. The SDK's
private independent-process selector is pinned to 2.2.1 and checked with actual
client/worker PIDs. Persistent topology, TaskManager/host restore, TLS/shared
deployment and memory peaks remain unvalidated.

The first shared-broker attempt expired old synthetic records under existing
retention; original preservation failed. That broker remains stopped and its
read-only post-expiry archive is not a pre-expiry backup. New work uses
`compose/checkpoint.yml`, project `fleet-m3-checkpoint`, a separate named volume
and cluster ID under [ADR-0019](adr/0019-isolated-checkpoint-broker.md). The same
existing image ID is verified before `create --no-build --pull never`; no new
image/package/cloud provisioning occurred. New topics have explicit seven-day
retention. Both profiles use loopback port 19092 and cannot run concurrently.
Both brokers are stopped with volumes, native checkpoints and receipts retained;
no destructive cleanup or old-topic republication is authorized by this work.

The [retention investigation](case-studies/kafka-retention-incident.md) quarantines the legacy
Desktop matrix and both restart modes before subprocess launch. Direct Docker
and ad hoc scripts are outside this entry-point enforcement. The old volume must
remain stopped. Production requires effective topic retention/size budgets,
independent archive readback, recovery preflight and an exercised alert response.
Stopping a producer does not suspend retention; starting a stopped broker just
to query offsets can already expire evidence. Production durability remains open.

The proposed [production recovery gate](guides/production-recovery-gate.md) now owns
the evidence ledger, bounded local disk budget, final retention/catch-up needs
and response procedure. The [archive contract](reference/archive-recovery-contract.md)
requires readback and an isolated rebuild with expired source offsets and no
source-broker access. These documents introduce no running archive or monitor.
The [v1 format and interface design](reference/archive-format-v1.md) now proposes the
physical format and finite publication boundary. [ADR-0021](adr/0021-bounded-archive-format.md)
proposes SeaweedFS 4.48 and Boto3/botocore 1.43.117. Executable distribution/image
hashes, the complete SDK lock, credentials and live compatibility remain startup
gates. No archive process, dependency or Compose profile is introduced here;
the final S3 target is selected below.

[ADR-0020](adr/0020-bounded-tests-and-s3-archive.md) selects Amazon S3 for the
final archive and keeps local tests within the approximate 10-50 GB scale,
using 50 GiB as a conservative retained-Kafka-data planning ceiling. Original
inputs, local archive copies, checkpoints, restore output and overhead consume
additional disk; inspect actual free space and budget all simultaneous copies.
Tiny fixtures remain the default. The [implemented fixture profile](guides/local-kafka-fixture-profile.md)
now sets non-expiring retention on new ordinary topics, checks actual volume
allocation and broker/workspace free space, and refuses insufficient budgets
before publication. This is a single-publisher three-record guard, not a quota
or a 50 GiB capacity result. Expiry tests remain separate. Source Compose, broker
defaults, existing topic settings and historical data are unchanged. A fresh
validation broker reused the existing image, passed the bounded live matrix and
finished stopped with its separate volume retained.

Use standard restricted administrative access and preserve old evidence. No new
Docker authorization plugin, management service, broker cluster or tiered
storage is needed for the bounded local profile. The Python guard remains an
accidental-use quarantine; it cannot constrain a Docker administrator. Final
S3 placement, credentials/lifecycle and actual readback/restore still need
validation under the separately authorized cloud stage.

The M2 local probe uses one locally built Kafka JVM
container and Windows Python clients, with loopback-only host publication,
separate internal listeners and a named Linux volume. Base digest, actual JRE,
Docker/Compose versions, limits and resource snapshots are recorded. Engine
startup/admission and bounded consumer receipt recovery
work. A graceful retained-record restart also passes
on the original container, image and named volume. A [SIGKILL follow-up](case-studies/kafka-broker-sigkill.md)
also preserves captured data/progress after one confirmed abrupt JVM exit on that
volume. WSL internals, workload peaks, host/disk loss and general failure recovery
remain unvalidated. The image route is owned by
[ADR-0013](adr/0013-local-kafka-release-image.md).

The retention-gap follow-up changes only three retention
settings on its freshly created synthetic topic and verifies an explicit refusal
after expiry. Broker configuration and the inspected settings of all other
existing experiment topics are unchanged; the broker is stopped with its volume retained.

The consolidated local matrix owns one complete check
cycle, including both offline M1 profiles, native producer failure/queue checks,
consumer recovery, retention and both broker restart modes. It requires the
existing stopped owned container and preserves its identity/image/volume through
final cleanup. It adds no runtime setting, service or cloud resource.

The operational evidence inventory and consumer audit add
read-only offline inspection of retained receipts. They require no Kafka client,
service startup, credentials, network access or deployment. Captured progress
and zero captured commit gap are not evidence of current broker health/lag.
Existing owned-runtime procedures still govern any later live operation. The
producer publication audit likewise runs offline
without Kafka clients, executes no captured command and changes no broker
progress. Its manifest is local operational evidence, not runtime coordination.
The M2 acceptance cycle adds runtime stderr metrics and a
manual hosted Linux broker lane. The existing Desktop context remains default
locally. The explicit CI `default` context is allowed only on POSIX with a local
Unix Docker socket and no DOCKER_HOST override; remote endpoints are refused.
The lane prepares the same pinned image, owns its new container/volume and stops
the broker on completion/failure. Hosted execution has not been performed.

The local Version 1 release must remain complete without an AWS account. A cloud stage will demonstrate reproducible infrastructure only after the platform has correctness and recovery evidence worth deploying.

## Local Windows environment

Use Linux containers through Docker Desktop with a suitable WSL2 environment. Verify virtualization, supported host versions, container architecture and available disk before selecting images. The [Docker Windows requirements](https://docs.docker.com/desktop/setup/install/windows-install/) and [WSL backend guidance](https://docs.docker.com/desktop/features/wsl/) are the upstream references; this document does not establish this workstation's readiness.

The current Kafka probe uses Windows PowerShell for Python and Compose commands,
with Docker's Linux engine for the broker. Its preparation script normalizes
shell/config files to LF inside a dedicated build context. A named Linux volume
owns broker data; host clients use `127.0.0.1:19092`, while the internal
`kafka:9092` and controller listener are not published. A later move to WSL
clients must document path, ownership and listener changes. Measure mount
performance before placing write-heavy state on a Windows bind mount.

### Incremental runtime profiles

These are planned groupings, not existing Compose profiles:

| Stage | Services needed | Resource or integration concern |
| --- | --- | --- |
| M1 | None; bounded Python fixture processing | Keep contract logic independent of containers |
| M2 | One Kafka KRaft broker plus bounded clients | Disk retention, advertised listeners and persistence |
| M3 | Kafka plus one Flink JobManager / TaskManager topology | JVM memory, checkpoints, backpressure and version compatibility |
| M4 | Add S3-compatible storage, archive worker and ClickHouse | Shared disk I/O, archive receipts and database merge pressure |
| M5 | Same small topology with controlled failures | Preserve evidence; distinguish process failure from volume loss |
| M6 | Add Prometheus, Grafana and only required exporters | Scrape cardinality, dashboard load and metrics retention |

Instrumentation begins with each component, before the complete monitoring stack exists. Do not run SITL, Kubernetes, Airflow or model serving to satisfy a telemetry milestone.

Flink, Kafka and ClickHouse can all consume substantial memory; checkpoints, archives and merges compete for disk bandwidth. Do not promise a minimum RAM figure without checking actual configurations and idle / peak use. Record host CPU, RAM, free space, WSL limits, storage location, container limits and process peaks during M2-M6. Reduce fixture volume and parallelism before adding machines. Set bounded retention, verify cleanup behavior, and document a stop condition for disk or memory pressure.

Single-node local services are a functional and fault-injection environment. They do not prove replication, host-loss recovery or production availability. Back up irreplaceable source evidence separately before destructive storage experiments.

## Ownership of configuration

| Concern | Planned owner |
| --- | --- |
| Local processes, networks and named volumes | Docker Compose |
| Topic definitions and database DDL | Versioned application / service setup owned by the relevant milestone |
| Event mappings, schemas and window logic | Application code and data contracts |
| Cloud storage, IAM, network and selected compute resources | Terraform after M8 authorization |
| Application release into cloud compute | A separately documented deployment mechanism chosen at M8 |
| Data migration, backfill and reconciliation | Explicit bounded operational procedure |

Terraform must not become a wrapper for local `docker compose`, Kafka message production, database inserts or one-off shell provisioning. Do not give Compose and Terraform competing ownership over the same resources. Create an `infra/terraform/` tree only when real, reviewable configuration exists.

## Terraform scope and entry gate

M8 begins with an ADR comparing the smallest deployable AWS shape, a single-host option and any justified managed services. Amazon S3 is selected for the final archive under ADR-0020; region, other services and availability requirements remain undecided. Avoid defaulting to EKS or managed streaming merely to add technologies.

The cloud proposal must identify a concrete purpose, such as demonstrating an independent archive / restore boundary or a reproducible remote demo. It must include a cost estimate with assumptions, expected runtime, storage and egress growth, budget alerts, who operates it, and an explicit teardown procedure. Budget alerts are notifications, not hard spending limits.

The first Terraform increment should be narrow: a private archival bucket and the least-privilege workload access needed to exercise it, plus any separately approved backend bootstrap. Compute, network expansion and managed Kafka are later choices. Local S3-compatible-to-Amazon S3 behavior must be tested, including endpoints, credentials, encryption, consistency expectations and the selected Flink plugin. An S3-compatible endpoint is not proof of backend or application compatibility.

### State and credentials

- Pin Terraform and provider constraints; commit the dependency lock file when configuration is introduced. Document provider upgrade and state migration steps.
- Use a separately bootstrapped, private remote state backend with encryption, versioning, restricted access and enabled locking. Keep its lifecycle separate from disposable workload resources; do not place state in a bucket that the same teardown destroys.
- For an AWS S3 backend, evaluate the pinned Terraform version's native S3 lockfile support. Do not add DynamoDB only from an old template. Current [S3 backend documentation](https://developer.hashicorp.com/terraform/language/backend/s3) describes `use_lockfile` and deprecates DynamoDB-based locking.
- Treat state and saved plans as potentially secret-bearing. Exclude them, `.terraform/`, credential-bearing variable files and local secrets from Git when adding infrastructure. A `sensitive` display marker is not encryption.
- Prefer short-lived local credentials and, if automated cloud access is later authorized, narrowly scoped federated CI credentials. Do not commit static AWS keys or credentials in backend arguments.
- Separate environment state and permissions. State workspaces alone do not establish a security boundary. Keep application archives, checkpoint storage and Terraform state in distinct access and lifecycle scopes.

### Review, validation and lifecycle

Before applying, run formatting checks, initialize providers with the documented lock file, validate configuration, and inspect a plan for the intended account, region and resource set. Provider initialization may need approved network access; validation is not a substitute for a real plan. Review IAM scope, public access, retention, encryption, deletion protection and cost implications. No plan or apply is run at Stage 0.

With separately authorized cloud execution, apply the reviewed plan, run a tiny upload/read/replay and denial test, then check for an unexpected follow-up diff. Test state locking without unsafe concurrent mutation. Demonstrate recovery of a previous state version in an isolated procedure and document backend bootstrap ownership.

Teardown must list what will be removed, what is retained, and how data and backend state are protected. Do not use broad automatic bucket emptying as a cleanup shortcut. Confirm archive retention and restore evidence before destructive changes. A complete cloud experiment records residual billable resources after cleanup and leaves backend decommissioning as a separate deliberate action.

## Acceptance and deferrals

M8 requires Terraform source, a reproducible plan / apply record, a second-plan drift check, working least-privilege access, data compatibility tests, cost evidence, and a tested teardown / retention runbook. It does not require Kubernetes, multi-region infrastructure, an enterprise module hierarchy, or automated publication.

Before M8, no cloud service selection blocks the local release. Before M4
storage startup, the local candidate must pass maintenance, licensing,
distribution/image provenance and compatibility review. ADR-0021 records the
archived MinIO upstream and proposes SeaweedFS as an alternative; no accepted
runtime choice is rewritten. The proposed single-process topology still needs
measured allocation/idle/peak limits, an exact artifact hash/image digest and a
Compose-owned volume independent of historical Kafka storage. Expose only the
S3 endpoint on loopback, keep administrative interfaces private, disable
unsolicited telemetry/ancillary services, and test distinct writer/read-only
credentials. A failed conditional-create race or persistence check blocks
adoption. This archive design leaves current filesystem checkpoints unchanged.

## Bounded archive graph follow-up, 2026-10-23

The graph/coordination checks reuse the accepted local S3
profile in a new owned prefix; twelve tiny objects survive a backend restart
on the same retained volume. The service ends stopped. No Kafka container is
started or modified, and no new service/image/dependency/cloud resource is
introduced. The callable coordinator still requires concrete source, inventory,
allocation, deadline, fresh-reader and protected-root runtime enforcement.
Windows file reconstruction records unavailable directory fsync; POSIX requires
it. No host/power-loss, off-host durability or actual Kafka-expiry claim follows.

## Bounded Kafka reader experiment, 2026-10-23

Reader checks use fresh `fleet-m4-reader-001` through `005`
projects from `compose/m4-reader.yml`, the existing verified Kafka image and
separate retained data volumes. Only this experiment's topic receives short
retention. The final diagnostic restarts/stops only its owned `005` broker;
historical profiles remain stopped. All five experiment brokers finish stopped.
No new distribution, dependency, cloud resource or storage cleanup is adopted.

The Windows native reader is rejected because its described UUID loses bits;
only the pure read port is implemented. The raw real-client expiry/fetch error
does not complete Kafka/S3 recovery or enforce a 120-second publisher process
deadline. Verify the Linux full-UUID boundary before native runtime admission.

## Linux reader verification follow-up, 2026-10-23

The Linux verification uses a new owned
`fleet-m4-linux-reader-001` project, the same existing Kafka image and Compose
template, and an evidence-local cluster-ID override. Its initial metadata topic
keeps non-expiring policies. Only a new disposable exact-read topic receives
controlled short retention. Full UUID, record bytes, fetch/preflight refusals
and unchanged progress pass; the profile ends stopped on its retained volume.
Historical containers remain stopped with unchanged state/configuration/mounts.
No new executable or dependency is adopted; Linux-only native admission and
the full Kafka/S3 recovery command remain separate implementation work.

## Windows SDK repair, 2026-10-24

[ADR-0025](adr/0025-windows-kafka-uuid-repair.md) and the
[repair report](case-studies/windows-kafka-uuid-repair.md) select an isolated, explicitly
versioned local Windows SDK. The portable pinned compiler is build scratch,
not a new service/system installation. Original Python files and bundled DLLs
stay unchanged. The ordinary lock still selects upstream 2.16.0; use the named
verified environment explicitly, and do not sync the stock lock into it.
Stock Windows now refuses maintained M2/M3 admission before clients.
The final verification profile is Compose-owned, loopback-only and bounded by
the existing Kafka image/resource limits. Only its disposable read topic gets
short retention. All profiles finish stopped with volumes/evidence retained;
historical profile state/configuration/mounts are checked separately. No cloud,
storage cleanup, shared deployment or automatic publication is introduced.

## Historical UUID audit and contribution reproduction, 2026-10-24

The audit reads 20 original Kafka volumes through an
owned helper using the existing image, network disabled, one CPU/128 MiB,
read-only root and read-only volume mounts. It does not start original brokers.
Before/after metadata and original container inspections agree. A separate
fresh `fleet-uuid-upstream-repro-001` Compose profile reuses the existing image
and 2 CPU/1536 MiB/128 MiB temporary mount limits, with loopback Kafka only and
at least 2 GiB free workspace admission. Its single synthetic topic carries no
records; stock/fixed metadata checks finish with that broker stopped and volume
retained. No new production service, dependency, cloud mutation or cleanup.

## Guarded native reader admission, 2026-10-26

The admitted native adapter reuses the selected
SDKs and Kafka image. Successful verification uses fresh projects
`fleet-m4-native-windows-002` and `fleet-m4-native-linux-001` from the existing
reader Compose template, with separate retained volumes and the same loopback
port/resource limits. After an initial default-subnet exhaustion refusal,
evidence-local overrides use checked non-overlapping `/28` ranges; historical
networks and engine configuration are unchanged. At least 2 GiB workspace space
is required for the tiny fixture. Only new read topics receive short retention.
Both profiles finish stopped, with original container state/configuration/mounts
checked separately. No image/dependency install, cloud operation or cleanup.

Use the existing verified Windows environment explicitly; a stock lock sync
does not select that derivative. Stock Windows native-reader construction refuses
before clients. The read-only adapter has no publication/commit/reset API and
does not yet provide a whole-command process deadline or protected recovery-root
retention. These belong to the next finite Kafka/S3 runtime increment.

## Supervised archive runtime, 2026-10-26

[ADR-0027](adr/0027-bounded-archive-runtime.md) and the
runtime guide add host Linux workers around the existing
Compose-owned Kafka/storage services. They require installed bubblewrap 0.11.1,
x86-64 CPython 3.13 and explicitly supplied existing SDK directories outside the
checkout. The verified run copies existing pinned bytes onto private Linux
storage; it installs nothing. Dedicated root/scratch/output directories avoid
exposing original sources or recovery roots to workers. Local HTTP remains
loopback only; shared deployment still needs separate TLS/credential review.

Writer/fetch processes share host networking; reconstruction uses a private
network namespace. Read-only code/runtime mounts, dropped capabilities, bounded
temporary storage and address-space/CPU/file limits are recorded with actual
denial probes. Parent-owned root trust and a complete worker deadline do not
provide malicious-host or host/disk-loss protection.

`compose/m4-storage.yml` now mounts `runtime/s3/archive-master.toml` read-only.
Default master growth exhausted the fresh four-volume fixture; one-volume growth
keeps that cap and 64 MiB volume size. The failed fresh profile stays stopped.
Successful `fleet-m4-runtime-storage-002` and `fleet-m4-runtime-kafka-001` use
separate retained volumes, checked non-overlapping local subnets and the existing
pinned images/resource limits. Actual reader PUT/DELETE and writer DELETE refuse.
At least 3 GiB workspace space precedes the live fixture; runtime copy estimates
reserve another 1 GiB of available space. This is tiny-fixture admission only.

Kafka finishes stopped after expiry. Storage replacement on the retained volume
passes fresh archive reconstruction and then finishes stopped. Historical
container states/configuration/mounts compare unchanged. Preserve roots, objects,
failed profiles and partial directories when rolling back source/configuration;
never reset offsets or delete volumes under the command. No S3 checkpoint
migration, cloud resource, dependency/image download or serving service is added.

## Serving compatibility profile, 2026-10-26

[ADR-0028](adr/0028-serving-compatibility-spike.md) pins the official Linux amd64
ClickHouse 26.8.34.13 manifest. After explicit maintainer launch authorization,
the `compose/m4-serving.yml` experiment runs with loopback HTTP 18123,
a dedicated retained volume, non-root user, read-only root, dropped capabilities,
2 GiB memory, one CPU and bounded temporary/log storage. Docker inspection
confirms the limits, UID/GID 101 and loopback-only host publication. An actual
root-filesystem write refuses. One Docker memory sample is 148 MiB of 2 GiB with
134 PIDs; this is not peak/capacity evidence. Startup initially fails because
automatic network pools are exhausted. The new overridable `10.254.241.48/28`
subnet does not overlap observed allocations; existing networks are preserved.
The required bootstrap password comes from a private environment variable;
Docker administrators can inspect container environment and are trusted. Separate
passwords exercise insert-only writer and read-only reader grants on the fresh
database. Reader INSERT/DDL, writer SELECT/TRUNCATE and incorrect credentials
return HTTP 403. Reader grants and conflict evidence survive replacement.
Shared-deployment TLS, private networking/egress enforcement and production
authentication remain open. The experiment finishes stopped with its volume
retained; no historical service is started or stopped by this experiment.

The event sink gate uses a separate fresh project
`fleet-m4-event-sink-001` with the same pinned image/Compose recipe, loopback 18124
and verified non-overlapping `10.254.241.64/28`. The existing profile file is
unchanged; explicit environment values select this project and private password.
New database/table bootstrap and grants are parent-owned operations. The library
writer has INSERT only; reader has SELECT on the new table and schema metadata.
No package/image download, old-table migration or cloud operation occurs.
Replacement retains the named volume and passes fresh exact readback, then
finishes stopped. A 238.8 MiB sample under the unchanged 2 GiB cap is not capacity
or peak evidence. Existing container stable-state comparison reports no changes.
Local HTTP, trusted administrators, diagnostic raw-table access and socket
inactivity timeouts remain explicit limits; whole-process supervision, shared
TLS and production retention/response are separate admission gates.

## Integrated local slice, 2026-10-26

The source-to-query demonstration combines the
existing M3, archive and serving recipes in fresh project `fleet-m4-slice-001`.
`compose/m4-slice.yml` supplies explicit runtime/archive subnets after observed
Docker automatic address-pool exhaustion; all three selected ranges are checked
against existing allocations. Loopback ports are Kafka 19092, Flink REST 18081,
S3 18334 and ClickHouse 18125. Existing image/resource/security pins remain.
Flink reads a source export without private credentials; parent-only bootstrap
creates the fresh bucket, three tables and distinct reader/writer identities.
The whole scenario runs under a 360-second parent timeout, with existing archive
supervision and a 180-second Flink submission timeout. This is a trusted local
harness, not new shared-deployment or continuous serving runtime admission.

The maintainer explicitly authorized service launch and subsequently deletion
of unnecessary stopped telemetry containers. Stop the new profile, save exact
inspection data/recent logs and remove only owned stopped containers without
`-v`. Preserve all named volumes, roots, failed attempts, images and unrelated
projects. The local cleanup receipt records removed identities and verifies
unchanged volumes and unrelated container state. Historical evidence referring
to now-removed containers remains valid for its original observation time;
recreation requires the retained Compose configuration and original volumes.
No cloud, persistent migration, Git commit or remote publication is involved.

## Bounded M4 recovery/admission completion, 2026-10-26

The M4 acceptance recreates only the existing archive and
serving services on their retained project volumes. Kafka/Flink remain absent
and source TCP 19092 refuses throughout. Both containers are subsequently
replaced on the same named volumes; fresh S3/report reads and another archive-only
reconstruction pass. The approved CLI has one Linux 120-second network-work
budget, with 90 seconds for existing archive supervision and an observed
135-second parent process bound. Other runtime profiles refuse before clients.

Read-only archive configuration and SELECT-only database credentials attest the
original scope; an S3 receipt writer can create only through the existing
conditional byte adapter. Replay database writers target new isolated scopes;
code refuses original archive/source runs before INSERT. Receipt objects use
`archive-v1/m4-completion-seals-001/`, separate from sealed source inventory.
The approved report path enforces complete receipt/archive/fact admission for
closed inputs. Raw SQL and Docker/database administrators remain diagnostic/trusted;
concurrent writer transactions, shared TLS/access enforcement and off-host
retention/recovery are not established. Final cleanup stops/removes only the
two recreated containers after collecting evidence, preserving all volumes and
unrelated projects. No cloud, dependency download or checkpoint migration occurs.

## M5 bounded reliability execution, 2026-10-26

The [M5 ledger](case-studies/m5-reliability.md) uses fresh `fleet-m3-final-011` with existing
M3 Kafka/Flink and M4 ClickHouse image pins. Loopback ports are Kafka 19092,
Flink REST 18081 and new serving 18126; verified free explicit subnets are
`10.254.241.128/28` and `10.254.241.144/28`. Separate private INSERT/SELECT users
own only a new test database. Existing memory/CPU/UID/read-only-root/capability
limits remain unchanged. No package/image download or new service type is added.
Only the retained M4 archive service is separately restarted for read-only outage
recovery. Expiry and permission faults touch only newly created disposable M5
topics and one new checkpoint directory; no retained volume is erased.

ADR-0033 mounts a fresh source-only repair export and adds the already installed
Kafka 4.4.0 offset CLI to finite command admission/completion. Three bounded
fifteen-second metadata subprocess calls add startup/completion overhead, not
new runtime dependencies. Both jobs ship the small helper with existing Python
files. The guard requires the whole declared source interval to remain available;
failed completion does not guarantee source group progress was rolled back.
The existing connector backport/image, Flink graph UIDs and state formats remain;
actual pre-repair checkpoint cold restoration is checked with no-claim mode.
Collect evidence before stopping/removing owned containers, preserve all named
volumes and verify unrelated projects unchanged. Cloud and production admission
remain separate.

## Continuous partition lanes and authorized load, 2026-10-27

The watermark follow-up uses eighteen TaskManager
slots and a 4,096 PID limit in the continuous profile. The existing monitoring
launcher accepts an optional bounded slot override while preserving the image
JVM options. Other profiles keep their existing slot settings. The archive
allows 128 volumes of 64 MiB (about 8 GiB ordinary data), providing headroom for
canonical payload encoding and retained calibration data. This is not a total
disk quota. Existing volumes, checkpoints and original source exports are retained.
The large workload uses fresh topics, bucket, SQL database and protected cursors
on the same local six-broker project. No cloud action or storage deletion occurs.


## Local partition-state candidate, 2026-10-27

The [state-cap repair](case-studies/m6-identity-state-limit.md) is prepared locally and not
deployed. It retains the eighteen source slots and existing 4 GiB TaskManager
container bound, while replacing two mixed battery lanes with eighteen isolated
partition branches. Additional worker/edge cost has not been measured under that
container budget. Existing volumes, checkpoints, topic offsets and SQL rows are
unchanged. New v3 gate/time/battery UIDs are not a compatible v2 checkpoint
migration. Any later startup/replay needs an isolated approved scope; no source
reset or disposal of unmatched state is an implicit migration. Rollback selects
the retained v2 source and its own compatible state. No cloud or infrastructure
resource change is introduced.


## Authorized isolated v3 execution

After explicit maintainer authorization, the v3 preflight and load
use a new `fleet-v3-001` Compose project with fresh cluster identity, credentials,
networks and project-scoped volumes. Automatic approval review refused bringing
up the former shared profile; it remains stopped and none of its volumes is
mounted. Current loopback ports are reused only while those containers are
stopped. The new Prometheus project targets a separate scope exporter on 18767.
The small full graph and checkpoint/expiry check pass within unchanged eighteen
slots, three CPU / 4 GiB TaskManager and 4096 PID bounds. Its pre-restart memory
peak is about 3.22 GiB, without OOM/PID-limit events. This is not the large-load
peak. The large controller refuses unsafe startup and stops publication under
sampled resource/disk pressure, terminal job/worker failure or unexpected facts,
retaining evidence. New `load2gb005` publication is active; final reconciliation
and M6 adoption remain open. No old offset reset, data cleanup, cloud change,
commit or publication occurs.


## User-requested stop and Battery v4 preparation

The maintainer requested stopping the workload and fixing its measured bottleneck.
The stop/performance record retains the final REST
ledger and copied checkpoint 44 before stopping `fleet-v3-001` with Compose stop.
Controller, producer/exporter and scope workers are stopped; three leftover idle
host workers from load2gb004 are stopped after ownership checks. No volumes,
topics, cursors or source offsets were removed or reset. V4 code is local and not
deployed: new battery UIDs/descriptor require fresh isolated state or a separately
tested migration. CPU/PID/memory/identity limits are unchanged. Rollback uses the
retained v3 code and its compatible checkpoint. No service or large run is
restarted automatically, and no Git publication or cloud action occurs.


## Optional local connection monitor

`compose/link-watch.yml` owns a separate optional receiver using the existing
pinned runtime image, loopback port 18768, read-only workspace/private-config
mounts and no persistent measurement volumes. Limits are 128 MiB, 0.5 CPU, 32
PIDs and rotated logs; writer/reader credentials are distinct and remain local.
The runbook defines
startup, shared-clock gateway admission and Compose-stop rollback. The receiver
has no Kafka/Flink/SQL dependency. Public deployment, TLS, durable alarms and a
real device adapter are unimplemented. The separate small check does not restart
historical services or authorize any retained-data cleanup.


## Isolated live Flink profile

The live runtime uses fresh project `fleet-live-001`, new
broker/state volumes and new `liveflink001`/`liveflink002` topics. Original profiles
remain stopped/unmounted. Only Kafka and Flink are started; the latest-value API
is a supervised host worker using the existing Python 3.13 native SDK environment.
`compose/live.yml` explicitly allocates six CPU and single-thread numerical pools
to TaskManager while keeping 4 GiB/4096-PID limits. Java adapter builds use the
existing pinned JDK/Flink libraries and emit hashes. Loopback API 18769 uses
a private reader token. Native checkpoints are restored without offset resets
or dropped state; the runbook defines stop/rollback and deployment limits.

## Local F09 flight research runtime

The separate loopback Grafana/ClickHouse profile uses new named volumes and generated private credentials. Existing data, monitoring stack and offsets are preserved. Its bridge permits egress and is not a shared-deployment security boundary; external map tiles are disabled. The optional network overlay reads the existing Prometheus only when its owning stack is running. No cloud resources or Terraform are involved.
