# Production recovery admission and response

## Status and scope

Production reliability is **open**, 2026-10-26. The bounded local M4 profile
now implements and verifies archive/readback/rebuild and isolated serving recovery.
This is single-host synthetic evidence, not production durability or workload admission. [ADR-0020](../adr/0020-bounded-tests-and-s3-archive.md)
selects Amazon S3 for the final archive and a small, bounded local test profile.
The [archive contract](../reference/archive-recovery-contract.md) owns exact observation
coverage and recovery refusal. These planning decisions change no live setting,
start no service and create no cloud resources.

| Required condition | Current evidence | Remaining acceptance evidence |
| --- | --- | --- |
| Independent readable archive and rebuild after Kafka loss | Bounded local S3 archive, Kafka-inaccessible isolated reconstruction and serving replay pass; no independent host-loss failure domain | Independent failure-domain archive and final AWS S3 compatibility/readback/rebuild before deployment acceptance |
| Sufficient retention and disk | Historical one-hour profile expired data; no capacity measurement | Bounded local data/disk admission; final workload-based retention, archive lag and catch-up allowance |
| Remaining time and response | No live archive-margin monitor or response drill | Observe archive progress, retention exposure and disk; repair/preserve before loss in a small timed drill |
| Fail-closed recovery | Accepted native/archive runtime refuses actual expiry before and after preflight without resetting progress | Preserve these selected-client guarantees under the final production topology and workload; do not infer host-loss durability |

The original historical preservation failure remains failed. A selected S3
target or successful document check cannot close these rows.

## Bounded local tests

Use tiny synthetic fixtures by default. The maintainer's expected upper scale
is approximately 10-50 GB; use **50 GiB of retained Kafka test log data across
all test topics/partitions in one profile** as a conservative planning ceiling.
This is not an enforced quota or a claim that the workstation supports it.
Record actual bytes and units. Do not generate tens of gigabytes without a
specific test question.

The [implemented three-record profile](local-kafka-fixture-profile.md) uses these
settings for new ordinary finite fixture topics:

```properties
cleanup.policy=delete
retention.ms=-1
retention.bytes=-1
```

These remove automatic time/size expiry from those topics. They do not bound
disk use. The current helper checks allocated volume bytes and actual broker/
workspace free space before mutation, and verifies effective topic settings
before publication. It bounds the three-record/two-attempt fixture and refuses
insufficient budgets. This is a single-publisher guard, not a quota or a 50 GiB
capacity result. Larger profiles need their own admission/footprint bounds. Keep
short-retention experiments on separate disposable topics. Existing historical
profiles remain stopped and unchanged. Group offsets and checkpoints have their
own lifecycle and still need explicit recovery validation.

The local disk budget is the sum of retained Kafka logs, original/canonical
inputs, local archive copies when present, checkpoints, restore outputs,
internal topics/logs and measured overhead, plus a declared free-space reserve.
The 50 GiB planning ceiling applies only to Kafka test data, not that whole sum.
Count simultaneous copies on the same device; use measured expansion and exact
placement rather than assuming archive encoding or compression is free. Reduce
the fixture if the host cannot accommodate it. No fixed multi-terabyte disk,
extra broker cluster, tiered storage or Docker authorization service is required
for these bounded tests.

Retain independent input/evidence for the chosen test. Review any cleanup after
readback/reconciliation; disabling Kafka expiry does not authorize deleting old
volumes or evidence. Automatic storage cleanup is not introduced here.

## Final S3 archive and Kafka retention

Archive original sources and observed Kafka records to Amazon S3 with checksums,
source lineage and partition/offset coverage. The proposed [v1 design](../reference/archive-format-v1.md)
and [ADR-0021](../adr/0021-bounded-archive-format.md) define physical format, finite
catalog/commit rules and a local client/backend candidate. Review the design,
lock executable artifacts and prove compatibility before implementing the
smallest bounded archive/readback/replay path. A local S3-compatible backend can
exercise that path before cloud work;
actual S3 permissions, lifecycle, independent readback and recovery must be
verified during separately authorized cloud execution.

For the final runtime, choose Kafka time retention longer than the supported
outage, detection/repair, archive catch-up and existing unarchived age, with a
margin and a bounded Kafka timestamp/clock error. Size limits must fit that
window at the measured partition rates and bursts. If recovery throughput does
not exceed continued incoming throughput, throttle admission or increase tested
capacity before claiming bounded catch-up. Record effective topic overrides,
all local replicas and shared-device consumers. No arbitrary production rates,
retention duration or capacity figure is selected by this document.

S3 capacity/lifecycle and cost cover original data, observation copies,
versioning if enabled, requests and recovery transfer. Checkpoints and Terraform
state retain separate ownership/lifecycle. A bucket name alone proves neither
archive completeness nor recoverability. Asynchronous archival can leave an
unarchived acknowledged tail; state the supported recovery point/time rather
than claiming zero loss from the presence of S3.

## Monitoring and response

Observe verified contiguous archive coverage and its oldest hole, archive
failures, oldest unarchived record age, effective Kafka time/size limits and
actual shared-disk free space. With finite limits, remaining safe time is bounded
by the earliest time expiry, size pressure or disk exhaustion under measured
growth bounds. Consumer lag alone does not supply all these quantities. Missing
or stale measurements are unknown, not healthy. With ordinary local data expiry
disabled, disk budget and finite admission remain the relevant local controls.

Set alert thresholds before the supported repair/preservation and catch-up time
is exhausted, with allowance for observation/delivery delay and a reserve.
Use a small disposable workload to rehearse this response:

1. Record affected intervals, actual settings, archive state and available disk.
2. Pause or throttle new admission when required; existing data still ages under
   finite retention. Repair the archive path or perform an explicitly authorized
   capacity/retention action before its budget expires.
3. Read back endangered objects and verify coverage. If required offsets are
   missing, refuse normal restore without resetting to earliest/latest.
4. Rebuild from verified archive into a fresh run when needed; reconcile bytes,
   identities and stable content before publishing complete results.
5. Resume only after archive catch-up and fresh margins are established. Retain
   actual timings and any loss/failure instead of reporting an alert as survival.

## Historical quarantine and next task

Keep the existing Python quarantine as an accidental-use guard. It does not
restrict direct Docker administration. Historical storage stays protected and
stopped; use ordinary least-privilege administration and deliberate preservation.
A new Docker policy platform is outside this bounded local plan. Unrestricted
administrators remain a trust boundary; quarantine is not archive durability.

The finite fixture admission/settings change now passes its bounded live checks.
The archive format/client interfaces now have a proposed specification, not
executable acceptance. Next in the authorized plan, close M3 multi-input idleness
and persistent recovery/resource checks. Then prove archive compatibility,
readback and expired-offset rebuild with tiny inputs and frozen independent
acceptance. M3 sequencing and
separate cloud authorization remain intact. This documentation change requires
no persistent migration; reverting it does not authorize historical startup.
