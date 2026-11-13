# ADR-0035: Continuous local processing, segmented archival and serving

**Status:** Proposed, 2026-10-27. The maintainer authorized a 22 GiB Docker/WSL
budget and preparation of continuous processing/archival for the six-broker,
18-partition local profile. Adoption requires actual running/checkpoint/recovery
and source/archive/query reconciliation, not removal of finite test guards.

The actual calibration now passes 20,128 unique
measurements plus an explicit replay, segmented source-byte/SQL reconciliation,
checkpoint-12 restoration and retained worker-cursor restart. Adoption remains
pending: source-subtask watermark placement causes excessive late classification
under backlog; per-partition behavior, active broker outage and large-load
admission remain open. The preparation does not certify a 1–2 GiB benchmark.

## Problem and decision

The accepted finite demonstration admits at most 32 observations and repeatedly
submits a terminating job. It cannot establish a 1–2 GiB continuous workload.
Keep that profile and its recovery proofs unchanged. Add a separate continuous
runtime using the same pinned Kafka 4.4.0, Flink 2.2.1/connector repair, local
S3 backend/SDK and ClickHouse. No new service type, package or connector.

Use six brokers, with three also acting as KRaft controllers, an 18-partition
canonical input and an 18-partition processing-fact output. RF=2 is one leader
and one follower per partition. `acks=all` and min ISR=2 intentionally stop
affected writes when only one replica remains. Internal transaction/offset topics
use RF=3/min ISR=2. Each broker has its own volume/node/listener. Controllers
bootstrap one shared dynamic voter set; never independently format six standalone
quorums. Existing broker volumes and standalone startup are not modified.

An unbounded Flink Table Kafka source preserves input key/value and observation
coordinates. A new keyed operator validates canonical inputs and maintains
event-time deduplication and ten-second windows. Identity signatures expire with
the declared 600-second horizon; per-vehicle state and the admitted vehicle set
are bounded explicitly. Late copies do not reopen closed windows. Long-horizon
identity/content conflicts remain detectable in serving reconciliation; bounded
state does not promise permanent conflict detection. Existing finite state UIDs,
serializers and checkpoint directories are not reused.

The maintained Kafka sink publishes processing facts with checkpoint-coordinated
transactions and stable UIDs. Use read-committed output consumers. This is a
Kafka/Flink boundary claim only; ClickHouse and archive writes still require
their own retry/content/readback/commit ordering. Fixed 10-second checkpoints,
30-second idleness and two-second out-of-orderness are initial local settings,
not workload-derived objectives.

An independent input consumer archives bounded segments continuously across all
18 partitions. Retain exact observation bytes and full cluster/topic/partition
identities. Reuse v1 observation validation in chunks of at most sixteen lines;
new segment/receipt/cursor documents are a separate versioned continuous format,
not v1 closed catalogs or trusted M4 seals. No whole-run list/inventory/count cap
applies to the new stream. Each buffer/object/HTTP operation remains bounded.

Immutable segment and receipt readback with separate S3 reader credentials
precedes a durable local cursor, which precedes Kafka progress commit. The
protected cursor binds every partition's next offset and verified receipt hash.
Refuse source identity changes, retention gaps, competing bytes, missing required
cursor state or broker progress ahead of retained state. Retry already published
segments by content; never reset offsets or overwrite retained evidence. A single
locked host worker owns the fixed assignment; archive-worker horizontal scaling
and dynamic partition expansion are separate scope.

A separate output consumer materializes processing facts into append-only tables.
Batch retries preserve semantic content; guarded logical reads detect competing
versions before deduplication. Commit output progress only after synchronous
INSERT and exact readback. Emit resource/accepted/rejected/retry/lag progress
without event/vehicle IDs in metric labels. Raw Kafka offsets remain lineage,
never measurement identity. Historical source time remains separate from latency.

## Alternatives, costs and limits

Raising finite constants or concatenating thousands of 32-record jobs preserves
startup overhead and finite history growth. A new orchestration platform or sink
connector adds maintenance before the declared scenario works. Native Kafka
source/sink, existing SDK byte operations and HTTP SQL retain one toolchain.
Maintenance adds a continuous operator, segmented cursor/recovery protocol,
worker commands and six-node local configuration; these need focused invariant
tests and real failure probes. Archive workers are administrator-trusted host
processes; the prior finite bubblewrap isolation claim does not transfer.

Docker/WSL's configured maximum is 22 GiB; actual engine-available bytes must be
recorded. Six broker caps plus Flink/storage/serving need a measured aggregate
budget with pressure stops. All endpoints remain loopback/private Docker links;
distinct credentials and retained volumes remain mandatory. Shared deployment,
off-host durability, host-loss recovery and saturation capacity remain unvalidated.

## Verification and rollback

Demonstrate more than 32 genuinely unique inputs over multiple checkpoints while
the same job stays RUNNING; exact per-partition archive intervals, complete
logical serving content/windows and visible late/duplicate outcomes must agree.
Stop/restart workers and terminate/recover the TaskManager, then reconcile after
backlog drains. Check an actual broker outage/return with ISR recovery. A later
1–2 GiB run remains a declared load experiment, not implied by successful startup.

Rollback stops the new project/workers and preserves all cursors, objects,
checkpoints, partial attempts and volumes. Existing finite commands remain
available. No existing persistent migration, deletion, Git commit, remote
publication or cloud operation is authorized.

Sources: [Kafka KRaft bootstrap](https://kafka.apache.org/40/operations/kraft/),
[Flink Kafka connector](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/datastream/kafka/),
[WSL resource settings](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).

## Partition-watermark follow-up, 2026-10-27

The maintainer authorized correction and a 2 GB local run. Reuse the pinned
connector assignment and the previously tested partition-lane approach: a single
18-partition topic has eighteen source/Calc/TableToDataStream/admission/timestamp
lanes, connected FORWARD until watermarks are assigned. Only then shuffle by
vehicle into two processing lanes. The canonical gate still precedes timestamp
assignment, refuses mixed partitions in a lane and requires eighteen subtasks.
A pre-submit graph check refuses lane merges or shuffles. Native per-split
watermarks with a JVM-side canonical deserializer would remove the one-slot-per-
partition cost, but add a maintained JVM admission implementation. SQL timestamp
extraction before full admission would weaken the existing bad-clock gate.
Neither alternative is required for this fixed local topology.

The cost is eighteen slots and more Python workers; a measured 1,024 PID
startup failure required 4,096. Preserve the image JVM options when overriding
slots. The actual backlog oracle passes all 20,128
eligible events, zero late and exact reference windows. This supersedes only
the current-placement limitation, not the recorded failed calibration.
Partition expansion/rescaling requires a separately checked topology. Use fresh
processing state for this correction; old checkpoints retain their old watermark
history and cannot repair already closed windows. Preserve old runs for audit.
The separate load published 2.084 decimal GB and reached 2,000,128 archive
cursor records, but Flink failed after ten restorations with
`continuous_identity_state_limit`; SQL retained 323,584 measurements. The
4,096-ID per-vehicle guard remained intact. This failure requires state-retention
and watermark-progress diagnosis; raising the guard without evidence is not
an adopted repair. Full-path reconciliation and adoption gates remain open.


## Partition-state follow-up, 2026-10-27

The maintainer authorized diagnosis and a minimal local repair, excluding another
2 GB run or changes to retained data. The [checkpoint investigation](../case-studies/m6-identity-state-limit.md)
shows that v2's downstream key shuffle made both battery subtasks use the minimum
of eighteen active partition watermarks. Real count and expiry state agree;
partition skew, not a need to raise 4096, explains the observed guard.

The v3 candidate routes validated records through eighteen typed side outputs,
checks the existing fixed vehicle-partition recipe, gathers each selected
partition before assigning time, and keeps keyed state in one lane per branch.
Only processing facts merge. This replaces the proposed two-lane battery part
of the earlier topology; previous calibration/load evidence remains unchanged.
It changes no event identity or persistent fact format. It uses new v3 UIDs and
requires fresh isolated processing state; no silent v2 state discard or offset
reset is a migration. The guard remains 4096 and the horizon 600 seconds.

Raising the guard does not bound skew. Wall-clock expiry weakens replay and
identity retention semantics. Native source watermark alignment would require
moving canonical timestamp admission to a compatible source implementation;
adding an option to the current downstream timestamp operator cannot provide
source pause/resume. The side-output candidate reuses existing components without
adding a coordinator/client, at the cost of sixteen more battery lanes and
branch edges. Its container worker/memory and v3 restore checks remain open.
Within-partition disorder, partition expansion and rescaling remain separate
constraints. Eight targeted checks pass; no Kafka deployment or large load was
run. ADR-0035 remains proposed, including the documented unmatched-future-timer
snapshot uncertainty and the unchanged full-path reconciliation/adoption gates.


## Isolated v3 verification and load authorization

The maintainer subsequently authorized verification and a new load. The
actual v3 preflight now passes the complete eighteen-partition
Kafka graph, existing archive/serving workers, exact source-byte/window oracle,
TaskManager checkpoint restore, deduplication across restore and expiry without
EOF. The small case stays within the existing 4 GiB / 4096 PID limits. This
narrows the v3 deployment/restore/resource uncertainties above for that declared
scenario; it does not retroactively repair v2 evidence or establish large-load
capacity. The final verifier uses the owning partition frontier, preserving
independent branch closure semantics. A new separately authorized `load2gb005`
is publishing in a fresh cluster and volumes, leaving the shared old project
stopped. Full large-run reconciliation, repeated runs and remaining reliability
and adoption gates are still required. ADR-0035 remains proposed.


## Stopped workload and state-access follow-up

The maintainer stopped the running load to remove its demonstrated Battery RPC
bottleneck. [ADR-0036](0036-managed-vehicle-state.md) proposes a v4 managed vehicle
value instead of per-entry state maps, preserving all canonical and event-time
semantics and the 4096 refusal. This supersedes only the proposed state layout
for the local candidate; historical v3 processing/recovery evidence remains.
The performance record distinguishes local checks
from full graph/container admission. The old state/data are retained and all
services remain stopped. ADR-0035 and broad M6 adoption remain pending.
