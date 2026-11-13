# Bounded local M5 reliability evidence

## Scope and outcome, 2026-10-26

This increment exercises the missing reliability boundaries of the accepted
local M4 slice using the existing pinned Kafka, Flink, archive and ClickHouse
components. It adds one tiny authored idle/resume fixture, three targeted live
checks and one source-gap repair. No dependency, image, service type, generic
runner, orchestration system or broad failure matrix is introduced.

The concrete blocker was reproduced first: the selected Flink Table Kafka
connector returned a successful empty bounded result after the required offsets
expired. [ADR-0033](../adr/0033-finite-flink-source-coverage.md) owns the minimal
finite-source guard. The repaired commands refuse a source gap before submission
or after execution and withhold their FINISHED receipt. They require exact source
coverage and preserve the existing connector backport, graph UIDs and state types.

M5 acceptance is limited to the local synthetic profiles and the boundaries in
the ledger below. It does not establish a continuous transactional sink,
end-to-end exactly-once delivery, concurrent run sealing, host-loss recovery,
multi-zone availability or production capacity. M4's archive-to-serving replay
remains terminal bounded reference. The new online test does not pretend that
replaying archive order can reproduce online arrival/watermark decisions.

## Failure and invariant ledger

| Required scenario | Expected observable invariant | Evidence and boundary |
| --- | --- | --- |
| Producer interruption after ACK/before local receipt | Explicit retry preserves stable identities; repeated observations do not inflate logical facts | Reuse the [corrected SDK recovery evidence](windows-kafka-uuid-repair.md#actual-broker-and-recovery-checks): six observations, three unique measurements, three duplicates and complete broker UUID comparison. No old narrowed UUID is recertified |
| Broker restart | Same full topic identity, exact retained bytes and committed group positions | New M5 broker restart preserves all 51 observations, identity and rebalance offsets `[45,6]`; existing SQL reports stay unchanged |
| Consumer rebalance | Pending observations survive partition transfer without unseen loss or content changes | New actual two-member group transitions from `[0,1]` to disjoint single-partition assignments with 50 observations pending; all 51 coordinates/byte hashes and final offsets reconcile |
| Flink termination | Completed checkpoint restores both managed prefix and source position | New TaskManager SIGKILL is not OOM; restored first offset 2 has the exact two saved identity/state entries before processing pending input |
| Checkpoint failure | A failed checkpoint cannot certify or commit its progress; repair must yield a completed checkpoint | Deliberately denied new checkpoint directory causes actual failure and default job restart. Progress stays uninitialized (`-1001`); repaired checkpoint commits 2 before TaskManager loss |
| Archive outage | Unavailable archive produces an explicit failure with no complete reconstruction | Existing read-only rebuild fails against stopped S3; after the same service restarts, exact four-observation/three-measurement reconstruction passes |
| Ambiguous sink response | Explicit changed-batch retries preserve complete logical results before merges | Reuse actual proxy-dropped response evidence from M4 event sink and integrated M4. New online event/window rows also survive changed-batch retry with merges stopped |
| Duplicate within/beyond horizon and late arrival after idleness | Within-horizon repeat is duplicate; expired repeat is late; neither increases closed windows | New 51-observation Kafka/Flink/SQL case has 5 eligible, 43 duplicate and 3 late dispositions, actual identity-expiry callbacks and exact reference windows |
| Missing/conflicting identities or facts | Refuse complete output rather than silently filtering or counting through conflicts | Reuse M3's conflict-after-cleanup invalidation and accepted M4 full canonical/processing admission, missing objects, holes and conflicting overlaps. The new guard also refuses missing/conflicting source receipts |
| Retention loss before/after admission | No successful command certificate for an unavailable declared source interval | Original actual Flink expiry probe falsely succeeded; repaired preflight refuses before job submission, and post-admission loss produces `kafka_source_gap` without FINISHED receipt |
| Missing required recovery state | Explicit failure without an invented restore or offset reset | Required nonexistent checkpoint refuses; no success receipt, and existing committed progress is unchanged. This models missing state without deleting retained volumes |
| Restore versus catch-up | Observe restored prefix before pending input, then reconcile only after drain | Checkpoint 2 is restored with two pending observations; final four-event reference has two windows with voltage sums 7 and 3 |
| Second isolated deterministic rebuild | Stable canonical/observation content survives another rebuild, independent of wall clock | Reuse M4 completion: two distinct replay scopes, exact byte hashes, identical reports, changed-batch retry and fresh rebuild after storage replacement |

This ledger composes explicitly scoped component and integrated evidence; it
does not claim that every fault was injected into one continuous production job.
Historical acceptance remains historical. New tests close identified gaps rather
than rerunning every successful M2-M4 failure cycle.

## Online late/resume and horizon scenario

`m5-idle-battery-v1.json` contains six authored native measurements in monotonic
source-time order. The existing converter registers their exact bytes and emits
six canonical measurements. Delivery order intentionally delays the nine-second
measurement; source clocks and measurement identity are never rewritten to make
the event late.

The existing two-partition job uses two-second out-of-orderness, thirty-second
idleness, ten-second windows and the six-hundred-second deduplication horizon.
Forty repeated deliveries of one twelve-second measurement keep partition 0
active while partition 1 becomes idle. After at least 29 observed seconds of
silence, the operator watermark reaches the first window's closing boundary.
Resumed event-time nine seconds is late; its immediate repeat is duplicate.
Both inputs then advance to 622 seconds. Actual expiry timers release the first
five identities; repeats of the nine-second and zero-second measurements are
late beyond their horizon, without reopening or inflating earlier windows.

All 51 source coordinates, key/value hashes, gate admissions, event dispositions
and rational window values reconcile with the existing independent reference
using the actual observed watermark trace. A separate native reader verifies
every Kafka byte and both final partition positions `[45,6]`. Broker CLI and SDK
topic UUIDs compare as all sixteen bytes. The post-repair normal run repeats
this useful scenario to establish that the safety fix preserves valid behavior.

| Window relative to fixed anchor | Unique eligible measurements | Voltage sum | Voltage mean |
| --- | ---: | ---: | ---: |
| `[0,10)` seconds | 2 | 3 V | 1.5 V |
| `[10,20)` seconds | 1 | 3 V | 3 V |
| `[20,30)` seconds | 1 | 5 V | 5 V |
| `[620,630)` seconds | 1 | 6 V | 6 V |

The nine-second measurement's 4 V remains queryable as late, but does not enter
these windows. All six measurements remain visible in coverage: voltage valid
6/missing 0, current valid 3/missing 3 and remaining fraction valid 2/missing 4.
SQL event quality counts first measurement eligibility: five eligible and one
late measurement. The retained observation trace separately records all three
late deliveries; a later expired repeat does not reclassify an already admitted
measurement's original contribution.

The scenario uses a fresh `m5_online` database and the existing experimental
`events`/`windows` schema and three queries. Complete recognized semantic JSON,
exact typed values, identities and all window fields are read back before SQL
results are accepted. Separate INSERT-only and SELECT-only users and stopped
merges reproduce the existing serving boundary. This is diagnostic online
evidence; no fake archive descriptor or new M4 seal policy is manufactured.

## Checkpoint failure, repair and retained-state recovery

Only a new job's checkpoint directory is temporarily made unwritable. Actual
checkpoint finalization fails and the selected default policy restarts the job
without a completed checkpoint. No group progress is certified. Restoring its
permissions is followed by waiting for running tasks and a newly observed source/
operator prefix, then requesting a completed checkpoint at offset 2.

The TaskManager is killed with SIGKILL only after that checkpoint completes.
Two additional observations are published while it is stopped. Restart shows
the restored two-entry state before processing offset 2, and Kafka checkpoint
progress 2 versus high offset 4 is recorded independently from final catch-up.
After drain, full source identities/bytes and rational windows reconcile.
Checkpoint group progress is a recovery point, not proof that SQL is complete.

A separate compatibility check creates a partial checkpoint with the retained
pre-repair driver, cancels that owned job under RETAIN_ON_CANCELLATION, and
restores it using the guarded driver with `--claimMode no_claim`. Restored prefix
and exact windows 7/3 match. No serializer, operator UID, connector JAR or image
is replaced. A probe that tried to reuse a checkpoint after its original job had
FINISHED fails because Flink had cleaned that checkpoint; this is retained as a
failed probe, not misreported as a source-guard compatibility defect.

## Source-gap defect, repair and recovery rule

The original expired-topic probe advances actual retained bounds past `[0,4)`.
The selected Flink source returns exit 0 and creates a FINISHED receipt with no
observations. The test fails, exposing a correctness defect that the prior
SDK-based archive expiry checks did not establish for the Java source path.

`kafka_bounds.py` uses the already installed Kafka offset CLI with a fifteen-
second per-command timeout. Both maintained jobs require earliest offset zero
for every declared partition before execution and again after completion.
Completion also requires current high offsets covering all reserved ends and
exact source-receipt coordinates, with equal hashes for repeated coordinates.
Producer-paced reserved suffixes may be absent at initial admission. Missing
metadata fails as `kafka_source_bounds_unavailable`; missing retained data or
receipt coverage fails as `kafka_source_gap`.

The supported finite profile conservatively requires the whole interval to
remain retained at admission and completion certification, including an already checkpointed prefix.
It does not claim to admit partial-retention recovery from a checkpoint alone.
After a source-gap failure, preserve the failed run and use an independently
trusted archive for a new isolated rebuild; never reset the original group.

An important limit is observed explicitly: in the post-admission case, Flink
commits source offset 4 before the outer command rejects certification. The
command returns failure and withholds its FINISHED receipt, but does not claim
to roll back Kafka progress. Do not treat command failure as proof that no
source-side effects occurred. Parent run completion and sink publication still
require the complete independent reconciliation, as in M4.

## Evidence, focused checks and preserved failures

Ignored evidence root: `.local-discovery/m5-late-20261026-001/`. Exact arguments,
source hashes, exit codes, stdout/stderr, source/restore receipts, actual traces
and SQL results remain there and in the recorded Linux data directories.
`rebalance-result.json`, `broker-restart.json`, `archive-fail.json`,
`archive-recovered.json`, `missing-state.json`, `source-gap-before.json`,
`source-gap-after.json` and `source-gap-cold-compat.json` name individual outcomes.
The original falsely successful expiry evidence stays in
`expired-flink-source.json`. No failed attempt is relabeled as passing.

Two focused regression tests establish retained-interval and exact receipt
coverage/refusal, including conflicting retries. They reuse normal temporary
fixtures and introduce no test framework. Real checks supply the idle/horizon,
rebalance, checkpoint, outage and expiry behavior; no mirror tests are added for
the scenario scripts. Existing M4 acceptance and its 107-method suite remain
historical evidence rather than a newly repeated unrelated gate.

Ruff check/format and strict typing cover the four scenario/SQL files. The three
changed Flink modules are checked with the existing Python 3.12/PyFlink toolchain;
the pure guard and regression tests also pass the core Python 3.13 checks.
Exact check receipts accompany final source hashes and the local acceptance.
`focused-checks.json` records seven successful commands, including the two-test
pytest run; `runtime-typing.json` records the separate pinned PyFlink typing
check. `final-live-verification.json` records terminal jobs and unchanged SQL
reports before/after the repair. `acceptance.json` ties these results to the
current file hashes and the preserved individual evidence receipts.

Preserved harness failures include the first authored nonmonotonic source
(correctly refused by the converter), the checkpoint retry requested before
tasks were ready, and a post-gap assertion that incorrectly assumed group
progress could not have advanced before command failure. The invalid source
bytes are reconstructed exactly against their originally recorded SHA-256.
Each repair changes the fixture/probe expectation or closes the demonstrated
source defect; no successful invariant is weakened or counted twice.

## Running and preserving the local profiles

Use the existing pinned M3 Compose runtime and M4 serving recipe with a fresh
project, source-only read-only export and private component credentials. The
observed project is `fleet-m3-final-011`, using existing loopback Kafka 19092,
Flink REST 18081 and a fresh ClickHouse port 18126. Explicit free subnets are
`10.254.241.128/28` and `10.254.241.144/28`. Image/resource/security pins remain
the existing M3/M4 values. Bootstrap owns only the new database/tables/users;
the check scripts own no DDL or service startup implicitly.

```bash
/existing/python3.13 -B scripts/check-m5-late.py \
  --project fleet-m3-final-011 --evidence /fresh/m5-late-005 \
  --private-config /private/m5-online.json

/existing/python3.13 -B scripts/check-m5-rebalance.py \
  --source-evidence /existing/m5-late-005 \
  --group m5-rebalance-new-001 --output /fresh/rebalance.json

/existing/python3.13 -B scripts/check-m5-checkpoint.py \
  --project fleet-m3-final-011 --source-evidence /existing/m5-late-005 \
  --evidence /fresh/m5-checkpoint-005
```

The numeric suffixes select fresh topics/control roots and avoid overwriting
prior evidence. Set repository, `scripts/` and the admitted Linux Kafka SDK on
`PYTHONPATH`. The private online JSON contains the existing `HttpConfig` shapes
for distinct writer and reader, both scoped to the fresh database. The parent
enforces bounded process lifetimes and stops owned services on success/failure;
a terminated Docker exec client alone does not cancel a remote Flink job.

Archive outage uses the existing `scripts/archive.py rebuild` and read-only
configuration on the retained M4 archive. Only that archive service is restarted
for recovery; no historical Kafka profile is started. Expiry changes apply only
to new disposable M5 topics whose exact pre-expiry bytes and identities are
retained. Missing-state behavior is exercised without erasing any retained volume.

Finish by collecting source/trace/checkpoint evidence and private logs, stopping
owned services and removing only their stopped containers under the maintainer's
cleanup authorization. Keep every named volume, source export and failed attempt;
verify unrelated projects remain unchanged. There is no cloud mutation,
dependency installation, Git commit or publication.

Final cleanup removes the five stopped containers used by these checks, while
all named volumes and the 17 pre-existing unrelated container states remain
unchanged (`cleanup.json`). A complete `retained-state.tar` preserves Linux
symlinks and checkpoint/control files. Direct extraction to Windows first failed
because symlink creation required a privilege; the partial copy is retained and
the tar archive was validated before any container removal.

## Limits and next task

The proof is finite and single-host, with tiny authored inputs and trusted
administrators. It does not cover real-source adoption, production retention
budgets, physical disk erasure, power/host loss, shared TLS/access enforcement or
all faults in one continuously running checkpoint-to-SQL transaction. Missing
required state/objects are tested as absence, without destructive storage cleanup.
Positive online disposition evidence is retained separately from deterministic
terminal archive replay. Production admission remains open.

The next milestone is M6: collect useful existing counters and latency/lag/state
signals for this demonstrated slice, then measure one declared small workload.
Do not build a monitoring platform or invent throughput/SLO targets first.

## File scope

Created: `scripts/check-m5-late.py`, `scripts/m5_late_sql.py`,
`scripts/check-m5-rebalance.py`, `scripts/check-m5-checkpoint.py`,
`tests/fixtures/m5-idle-battery-v1.json`,
`tests/fixtures/m5-idle-conversion-job.json`, `runtime/pyflink/kafka_bounds.py`,
`tests/test_kafka_bounds.py`, ADR-0033 and this report.
Updated: `runtime/pyflink/persistent_job.py`, `runtime/pyflink/partition_job.py`,
`README.md`, `docs/roadmap.md`, `docs/architecture.md`, `docs/data-contracts.md`,
`docs/testing-strategy.md`, `docs/deployment-and-terraform.md` and
`m3-persistent-acceptance.md`. Private commands, credentials, state copies,
failed attempts and detailed runtime receipts stay in ignored local evidence.
