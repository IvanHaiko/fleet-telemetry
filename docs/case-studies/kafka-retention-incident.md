# Kafka retention incident: cause and production gate

## Finding and authorized repair

The 2026-10-21 checkpoint experiment reused historical local Kafka storage whose
records had exceeded its one-hour retention policy. Kafka rolled and deleted
eligible segments as configured. The procedural defect was starting shared
storage before proving required historical bytes were safe independently of it.
A post-start readback detects a gap; it cannot prevent background deletion.
The logs establish time retention, not a Kafka/Flink checkpoint defect.

Original preservation remains failed. Neither isolated recovery nor this repair
recovers expired bytes or accepts M3. There is no production deployment. The
authorized repair quarantines the two legacy local lifecycle entry points and
defines the remaining production gate. No broker starts, topic/offset/retention
settings change, dependency is added or storage is removed.

## Evidence chain

`runtime/kafka/kafka-probe.properties` declares one-hour retention, 64 MiB per
partition, 1 MiB segments and a 10-second retention-check interval. Topic creators
also explicitly set `cleanup.policy=delete`, `retention.ms=3600000` and
`retention.bytes=67108864`. A broker-default increase alone would not replace
those topic overrides. These are bounded-probe settings, not a production budget.

Each of the four observed deleted segments was 3,259 bytes. The deletion message
explicitly cites the 3,600,000 ms time limit, not the 64 MiB size ceiling.
All table times are UTC; Berlin local time was UTC+02:00.

| Topic suffix before `.telemetry.canonical.v1` | Largest record timestamp, 2026-10-21 | Deletion time | Age |
| --- | --- | --- | --- |
| `m2.refactor-1021-003-graceful` | 12:02:19.121 | 21:39:28.974 | 9h 37m 09.853s |
| `m2.m3-pyflink-1021-001` | 12:38:05.806 | 21:39:28.976 | 9h 01m 23.170s |
| `m2.refactor-1021-003-sigkill` | 12:02:37.893 | 21:39:28.977 | 9h 36m 51.084s |
| `m2.m3-pyflink-1021-002` | 12:46:08.230 | 21:39:28.978 | 8h 53m 20.748s |

For the last topic, three lines at 21:39:28.978 record segment rollover at offset
3, log start advancing to 3 and base-offset-zero deletion for time retention.
The earlier successful `[0,3)` read did not reserve these records. The later
interval guard observed start 3 and refused the missing interval. Ten seconds
is a scheduler interval, not a client/restart preservation grace period.

These Kafka record timestamps are contemporary transport timestamps, not the
historical measurement times in event payloads; producer calls supplied no
explicit Kafka timestamp. Logs do not support blaming replayed 1970 measurement
times, clock skew, disk failure, missing commits or offset reset for this incident.

Original evidence remains in ignored `.local-discovery/m3-checkpoint-001/`:
`broker-full-log-inspection.json`, `retention-incident.json`, cycle 003/004 receipts
and `checkpoint-evidence.zip`. Derived timestamps and exact relevant lines are
in `.local-discovery/retention-rca-001/cause-evidence.json`. Four is the observed
deletion count here, not an exhaustive cluster-wide loss audit.

## Why previous controls did not prevent loss

- A named volume preserves storage identity; Kafka can still delete its contents.
  Stopping the broker stops the retention task, not wall-clock record ageing.
- A new topic name isolates publication, not cleanup of old topics on the broker.
- Before/after checks neither backed up all required old intervals nor gated
  startup. Successful pre-read and later background expiry can both occur.
- Commits and checkpoints preserve progress/state; they do not pin Kafka segments
  or recreate deleted source records. Replicas also apply retention.
- No permanent observation archive, verified pre-start copy, workload retention
  budget or oldest-unarchived-record alert had been implemented.
- Container/image/mount identity and final stopped state can remain unchanged
  after Kafka's own deletion. They are insufficient preservation evidence.

The initiating action was starting old shared storage without a pre-start
preservation gate. Retention was the deletion mechanism. The separate Python
worker failure explains the failed recovery job, not the retention deletion.

## Immediate executable protection and its limits

`scripts/kafka_evidence.py` now quarantines project `fleet-kafka-440-probe` in
context `desktop-linux`, returning the safe reason `historical_broker_quarantined`.
`scripts/check-m2.py` refuses that path before output/source/process access.
`scripts/check-kafka-restart.py`, whose existing supported context is Desktop,
refuses both graceful and SIGKILL paths before source or runtime access.

Five focused cases in `tests/test_kafka_quarantine.py` use a process-launch
tripwire, absent inputs and an output that must remain absent; they check normal
and optimized Python, both restart modes and CLI code 2 with the safe reason.
The installed pinned Kafka client is reused without a broker or installation.

This is entry-point quarantine, not Docker permission enforcement or a production
preflight. Direct Docker, ignored ad hoc scripts and recreated/remounted volumes
bypass it; none is authorized for historical storage without a reviewed preservation
procedure. A different context does not authorize old storage: existing endpoint,
context and ownership checks still apply. The Desktop-specific gate does not
change the fresh Linux CI path; hosted execution and its existing compatibility
gaps remain unvalidated. No new context support is introduced.

Both brokers remain stopped, with both volumes, inputs, receipts and checkpoint
retained. The old broker copy is post-expiry and cannot restore the lost history.
[ADR-0019](../adr/0019-isolated-checkpoint-broker.md) isolates subsequent bounded
work. Seven-day experiment retention is still finite, not permanent archival.

## Required production controls

Production admission remains blocked until these controls have executable evidence:

1. **Time and size budget.** Retention must exceed the oldest required record's
   age at the last healthy point plus supported outage, detection/repair,
   catch-up and margin. Include bounded Kafka timestamp skew, peak partition
   rates/bursts and disk headroom. Time and size limits independently threaten
   required data; this fixture cannot establish production capacity.
2. **Verified independent archive.** Preserve original source and observed event
   bytes outside Kafka, with checksums, partition/offset coverage and durable
   receipts. Demonstrate readback and an isolated rebuild after required Kafka
   offsets are unavailable. A receipt without a read/restore check is insufficient.
   M4 owns this boundary; it is not implemented by the quarantine.
3. **Recovery preflight.** Match cluster/topic identity, checkpointed source
   progress, retained interval and archive coverage. Refuse gaps without resetting
   to latest. Starting stopped storage to query offsets is already a mutation
   risk: first preserve it offline or use a fresh broker for archive rebuild.
4. **Remaining-margin alert and response.** Observe effective retention/size
   limits, archive coverage, oldest unarchived age, recovery needs and disk pressure.
   Exercise intervention before the budget is exhausted. Stopping a producer/job
   does not stop retention. The response must preserve bytes or perform an
   explicitly authorized capacity/retention action; an alert alone is not durability.
5. **Configuration and failure tests.** Review effective topic overrides and
   destructive-operation permissions. Prohibit shared experimental storage.
   Exercise long downtime, slow archive, size pressure, drift and expired-offset
   recovery with independently preserved inputs.

Kafka documents time/size retention independently of consumption. Disabling only
time retention leaves the byte limit; disabling both without capacity controls
trades expiry for disk exhaustion. Longer retention is a budget, not a complete
durability solution. See official [time retention](https://kafka.apache.org/40/configuration/topic-level-configs/#retention.ms)
and [size retention](https://kafka.apache.org/40/configuration/topic-level-configs/#retention.bytes).
These explain the model; actual 4.4.0 incident facts above come from local logs
and configuration, not an assumption that this older reference pins the runtime.

## Validation, file scope and rollback

Modified code: `scripts/kafka_evidence.py`, `scripts/check-m2.py`,
`scripts/check-kafka-restart.py`. New test: `tests/test_kafka_quarantine.py`.
Documentation: this new report, `README.md`, `docs/deployment-and-terraform.md`,
`docs/testing-strategy.md`, `docs/roadmap.md` and a dated addition to
`docs/adr/0019-isolated-checkpoint-broker.md`. The increment is ten files.

The full root suite with the existing optional Kafka client passed all 424 cases,
including the five new refusals. Ruff/format passed on all 12 scripts and the new
test; strict mypy passed on 36 root/test and 12 script files. The module-size guard
passed. Commands/output are in ignored `.local-discovery/retention-rca-001/`.
No live expiry experiment is repeated. Read-only independent investigation/repair
review is not a blind test cycle or evidence of production fault tolerance.

No runtime configuration, contract, lock, CI workflow, image or broker bytes change.
Rollback restores only this source increment from its preserved baseline; that
does not authorize historical storage startup. No storage migration/deletion is
needed. Re-enabling the lifecycle requires a reviewed preservation/storage
migration procedure, not a skip flag. Next: a bounded archive coverage/readback
contract and expiry-rebuild acceptance scenario before production claims.

The separate restricted read-only Reviewer accepted this investigation/quarantine
increment with no blockers. It independently recomputed segment ages from raw
logs, checked the ten-file diff and early guard ordering, observed denied
source/test write-open attempts (`EROFS`), and ran the permitted Python 3.13
checks: three passed, two skipped without the optional Kafka client. All 424
Windows cases, including those restart cases, are recorded separately. Review
inputs stayed unchanged; the process ended with code zero and no timeout.
`completion.json`, `review-final.txt` and `retention-investigation.zip` retain the
final scope/checks/review and preservation evidence. Acceptance applies only to
this repair: original preservation is still failed and production remains open.
