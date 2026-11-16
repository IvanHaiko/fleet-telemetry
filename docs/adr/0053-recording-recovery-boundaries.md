# ADR-0053: Recovery boundaries of the single-machine recording profile

**Status:** Accepted, 2026-11-16, by maintainer decision on a post-hoc basis
([acceptance](#acceptance-2026-11-16)). Proposed on 2026-11-15. The fault
mechanisms below passed on 60-second and 240-second F09 intervals. Two
complete-flight fault runs on 2026-11-16 passed every correctness and fault
check but failed their declared visibility limit. The first failed because of
serving start-up time ([details](#complete-flight-run-2026-11-16)). In the
second, the recovery measure closed the serving fault's window one sample too
early ([details](#second-complete-flight-run-2026-11-16)). The maintainer
accepted the second run's evaluation under the corrected measure, which passes
every limit.

## Problem

Roadmap step 3 asks for evidence of the selected retry and recovery boundaries
on the [single-machine profile](0052-single-machine-recording-profile.md). Before
this decision the profile had none of it live:

- the Flink job had never been restored from a checkpoint;
- the window between the SQL acknowledgement and the serving cursor write was
  covered only by a worker test with simulated components;
- archive pause and resume had run only on the first complete flight, without a
  predeclared criterion;
- no rebuild from the archive existed for this profile;
- the failures outside the verified profile were not listed.

Killing a container at a random moment does not establish the SQL/cursor window,
because nothing guarantees that the kill lands inside it.

## Decision

Exercise four failures with existing mechanisms, add one isolated rebuild, and
run them from one orchestrator that writes its criterion before any service
starts.

| Failure | Mechanism | Recovery path |
| --- | --- | --- |
| TaskManager loss | `docker kill --signal KILL` once the producer has acknowledged a declared number of deliveries, then `docker start` | The job's fixed-delay restart strategy restores the latest completed checkpoint, as in the M5 checkpoint check |
| Job loss | Cancel through the Flink REST API; the job retains checkpoints on cancellation | `recording_job.py --restore <checkpoint>` submits a new job from the retained checkpoint |
| Serving stop inside the SQL/cursor window | One-shot fault point in the serving worker | Restart from the unchanged cursor rereads the batch |
| Archive outage | `docker stop` and `docker start` of the archive worker, as in ADR-0050 and ADR-0052 | The worker resumes from its durable cursor; serving waits at the archived prefix |

**Checkpoint resubmission.** `--restore` admits only
`/state/<run>-checkpoints/<job>/chk-<n>` of the same run with a `_metadata`
file. It sets `execution.state-recovery.path` with `NO_CLAIM` mode and refuses
unclaimed state, so every operator state must map and the checkpoint is never
taken over or deleted. The new job writes its own receipt and plan files; the
original receipt and all retained checkpoints stay unchanged.

**Serving fault point.** `recording_initialize --serving-fault-after-outputs N`
adds a `serving_fault` entry to the serving configuration only. Without that
entry the worker passes the SQL writer to the batch directly, as before. With it,
the first confirmed batch that brings the first serving process to at least `N`
written outputs triggers the fault: the worker durably writes
`fault-after-sql-ack.json` (the batch's output offsets, input offsets and the
unchanged cursor) and exits with code 70 before the cursor write. The marker
disarms every later process, so a restart with the same configuration rereads
the batch and continues. The worker's existing immutable evidence files compare
every reread output byte for byte; a difference stops the worker.

The maintenance cost is about 70 lines in `runtime/continuous/recording_batch.py`,
a six-line branch in the worker, one initializer option and the adapted restart
test in `tests/test_recording_serving_gap.py`. The entry must stay absent from
ordinary runs; reconciliation reports the fault batch whenever a marker exists.

**Isolated rebuild.** `runtime/continuous/recording_rebuild.py` reads only
archive objects: the stream plan, the archived context, and the chained input
segments, each read back by digest. It does not read Kafka, Flink, the serving
cursor or the original database. The association runtime that the Flink operator
wraps processes the archived deliveries in offset order. The facts go to a new
database `<run database>_rebuild_<id>` with its own writer and reader accounts,
and the evidence to a new `rebuild-<id>` directory beside the run's state. An
existing rebuild scope refuses. Reconciliation compares the rebuilt fact hash
set with the reference and with the original database.

**Orchestration.** `runtime/recording/fault_run.py` runs on the host with the
standard library and the Docker CLI. For one interval and run ID it prepares
fresh inputs, writes `criterion.json`, starts the profile, starts the
publisher only after the serving worker's first status, executes the
schedule, waits for serving completion, reconciles, rebuilds, evaluates and
stops the profile without removing volumes. An observer container
(`runtime/continuous/recording_observe.py`) samples the producer, archive and
serving status files and the SQL-visible GPS input offsets on one clock. Fault
start and resume times are read from the same Docker engine clock. Its start,
status and stop helpers are separate functions for the later operations
command of roadmap step 5. Output holds counts, digests, times and states; no
coordinates, credentials or event identifiers, and no identifiers in metric
labels.

**Recovery measure.** For each fault, recovery ends at the first observer
sample after the resume action at which every fact acknowledged before the
fault is SQL-visible, at least one fact acknowledged after the resume action is
SQL-visible (when one exists), and no pending fact is older than the visibility
limit. Acknowledgement times carry one sample of error, so the middle condition
counts only facts that the first sample at or after the resume action did not
yet cover. The middle condition was added after the first complete-flight run
and made strict after the second; the short-interval runs below were evaluated
without it.
The fault window runs from the fault start to that sample. The visibility
limit applies to facts whose acknowledgement-to-visibility interval lies
outside every window. A deliberate archive pause lasts as long as declared, so
its limit applies to the catch-up after the resume action.

**Correctness checks.** The SQL fact hash set equals the reference set. There
are no logical repeats: distinct identities, DISTINCT view rows and reference
lines are equal, with no conflicting content; physical repeats are allowed. A
restored checkpoint is the latest completed one before the fault. No job's
exception history contains the operator refusal that guards
`offset == runtime.deliveries`. The output topic's repeated facts form a range
that starts at the first GPS fact of the restored source position: an earlier
start would make the operator refuse, a later one would lose facts.

## Alternatives, cost and maintenance

- **Random container kills.** Simple, but they do not guarantee a hit inside
  the SQL/cursor window and cannot be repeated.
- **A chaos or fault-injection framework.** It would add a dependency and a
  service for four failures that Docker and one configuration entry already
  cover.
- **Stop with a savepoint instead of cancelling.** A savepoint is a planned
  operator action; the selected failure is the loss of a running job, which
  leaves only retained checkpoints.
- **Rebuild through a new Flink job.** Replaying the archive into a new topic
  would need new Kafka topics and would not show recovery without Kafka. The
  selected rebuild uses the same association runtime without Kafka or Flink;
  its result is checked against the reference, not trusted.

The new maintenance surface is the fault point above, one job option, three
worker modules (observer, reconciliation, rebuild) and the host orchestrator
with its analysis. No dependency, service or image changes.

## Rollback

Stop using the orchestrator and the `--restore` option. Configurations without a
`serving_fault` entry behave exactly as before. Fault runs keep their topics,
checkpoints, archive objects, databases (including rebuild databases) and
evidence; nothing is reset or removed.

## Short-interval runs, 2026-11-15

Each run used a fresh bundle, reference, topics, database, bucket and checkpoint
scope, and the interval `[86459069,146459069)`: 1,017 events, 1,019 deliveries
with two declared repeats, 538 facts. Evidence is under
`.local-discovery/<run>/`. Times are on the observer clock with 2-second
samples, so each carries up to one sample of error.

| Run | Fault | Outage | Recovery | Result |
| --- | --- | ---: | ---: | --- |
| `f09-s3-tm-20261115-01` | TaskManager SIGKILL at 400 deliveries | 23.9 s | 28.7 s | Restored checkpoint 3, the latest completed; 27 facts re-emitted, 565 physical rows, 538 logical; hashes equal; rebuild equal |
| `f09-s3-resubmit-20261115-01` | Cancel at 400, resubmit from checkpoint 3 | 27.4 s | 30.9 s | New job restored checkpoint 3; 40 facts re-emitted from the first GPS fact at source offset 335; hashes equal; rebuild equal |
| `f09-s3-serving-20261115-01` | Serving fault after 200 outputs | 1.4 s | 2.2 s | Fired after 204 written outputs; the 7-fact batch was reread, 545 physical rows, 538 logical, one content per member; hashes equal |
| `f09-s3-archive-20261115-01` | Archive worker stopped for 15 s at 500 | 16.2 s | 3.1 s catch-up | Serving held at the archived prefix (507 archived, last visible input 505, producer 767); hashes equal |

Outside the fault windows the visibility age never exceeded the 2-second sample
interval, and the terminal drain was 0 s in every run.

The first run's reconciliation step failed because it asked the SQL client for a
60-second timeout, above its 15-second bound. The fix changed only the
reconciliation module; the run's data was reconciled afterwards with the same
module. All later runs completed every step in one invocation.

**Combined rehearsal.** `f09-s3-all-20261115-03` ran all four faults on the
240-second interval `[86459069,326459069)` (4,076 deliveries, 2,159 facts):
TaskManager SIGKILL at 800, serving fault after 900 outputs, resubmission at
2,400 and a 20-second archive pause at 3,300. Recovery took 28.6 s, 2.9 s and
32.3 s, and the archive caught up 5.1 s after resuming; visibility outside the
windows stayed within 2.0 s and the drain was 0 s. Hashes, logical repeats,
restore positions and the rebuild all passed.

**Topic identity defect.** The preceding attempt, `-02`, stopped at job
submission: the input topic ID contained `/`. confluent-kafka renders topic IDs
in standard base64 (`+` and `/`), which [ADR-0025](0025-windows-kafka-uuid-repair.md)
and `runtime/kafka_archive/native.py` already expect, but the Flink operator,
the output validator and the SQL writer accepted only `[A-Za-z0-9._-]`. Roughly
every other fresh topic would have been refused; earlier runs had happened to
receive IDs without those characters. The three validators now accept
`[A-Za-z0-9+/_-]{1,128}` for topic IDs and keep the stricter rule for cluster IDs
and topic names. The test fixtures use IDs with `+` and `/`, which reproduced
the refusal (25 failing tests) before the change.

## Complete-flight run, 2026-11-16

`f09-s3-full-20261116-01` ran the whole flight `[0,2436000000)` at 1x: 39,760
deliveries, 21,054 facts. The maintainer approved its `criterion.json` before
the run. The declared schedule:

| Fault | Trigger | Recovery limit |
| --- | --- | ---: |
| `taskmanager-kill@8000` | producer acknowledged ≥ 8,000 deliveries | 120 s |
| `serving-ack-cursor@6000` | first confirmed SQL batch reaching ≥ 6,000 outputs | 60 s |
| `job-resubmit@16000` | ≥ 16,000 deliveries | 180 s |
| `archive-pause@26000:120` | ≥ 26,000 deliveries, 120 s pause | 60 s catch-up |

**Result: failed the declared criterion** (`status: failed_criterion`). Every
correctness and fault check passed; the visibility limit did not.

Correctness:

- The SQL fact hash set equals the 21,054-line reference
  (set digest `463c0a97…eca760`). 21,161 physical rows, 21,054 distinct
  identities and DISTINCT view rows, at most two rows per identity, no
  conflicting content.
- The 107 physical repeats are exactly the declared re-emissions: 88 facts
  from source offset 7,845 after the TaskManager restore, 11 from 15,982 after
  the resubmission, and the 8-member serving batch. The output topic holds
  21,153 records, 99 more than the reference.
- Both Flink restores used the latest completed checkpoint (49 and 96), and the
  repeated output ranges start at the first GPS fact of each restored source
  position. No exception history contains the operator refusal.
- The serving fault fired after 6,007 written outputs; every member of the
  reread batch has two physical rows and one content.
- During the archive pause serving held at the archived prefix: 26,011
  archived, last visible input 26,010, producer at 28,065.
- Rebuild `001` from archive objects alone read 39,760 deliveries and wrote
  21,054 facts into `f09_s3_full_20261116_01_rebuild_001`; its hash set equals
  the reference and the original database.

Timing on the observer clock (1,199 samples, largest gap 2.0 s, no
observation errors):

| Fault | Outage | Recovery as declared | Limit | Pass |
| --- | ---: | ---: | ---: | --- |
| TaskManager SIGKILL | 20.1 s | 26.6 s | 120 s | yes |
| Serving fault | 1.1 s | 2.6 s | 60 s | yes, but see below |
| Resubmission | 33.9 s | 40.3 s | 180 s | yes |
| Archive pause | 122.3 s | 34.9 s catch-up | 60 s | yes |

The terminal drain was 0 s. Outside the fault windows the median visibility
age was 0 s, but 303 facts exceeded 15 s, with a maximum of 30 s, so the
visibility limit failed. They fall into two groups, and both come from the
serving worker's start-up, not from steady operation:

1. **141 facts in the first 14 s of publication**, at most 28 s old. The
   orchestrator started the publisher immediately after the serving worker.
   Before its first status the worker loads the complete bundle, reads the
   archived reference and builds its indexes, which took about 28 s for the
   whole flight against about 1 s for the 60-second interval. The run guide
   starts the publisher separately, after the workers, which is why the
   earlier complete runs did not show this.
2. **162 facts acknowledged just after the serving fault**, at most 30 s old.
   The restarted worker wrote nothing to SQL for 32 s: start-up again, plus
   re-verification of the whole archived prefix (11,165 deliveries at that
   point). The declared recovery measure closed the fault window after 2.6 s,
   because the batch written before the exit was already visible and the
   pending facts were still younger than the limit. The measure did not
   require the restarted consumer to have written anything.

Two changes follow, both outside the approved criterion's scope and therefore
not applied to this run's verdict:

- The orchestrator now waits for the serving worker's first status (up to
  300 s) before it starts the publisher.
- Recovery additionally requires that at least one fact acknowledged after the
  resume action is SQL-visible. The second complete-flight run showed that this
  version still compared sampled acknowledgement times with the resume time;
  the strict form follows below.

Rehearsal `f09-s3-ready-20261116-01` checked both on the 60-second interval
with a serving fault after 200 outputs. The publisher started after serving
reported ready. Recovery under the revised measure took 4.5 s, and visibility
outside the window stayed within 2.0 s. Hashes, logical repeats and the
rebuild all passed, with 546 physical rows.

A post-hoc re-evaluation of this run's samples with the strict measure, kept as
`reanalysis-strict-measure.json` beside `result.json` and not acceptance
evidence, moves the serving fault's recovery to 36.6 s (within its 60 s limit)
and leaves only the 141 start-up facts above 15 s. The earlier
`reanalysis-revised-measure.json` used the intermediate rule and gives the same
figures for this run.

**Serving restart cost.** A serving restart re-reads the bundle and the
reference and verifies every archived segment from the start, so its duration
grows with the archived prefix: about 1 s on the 60-second interval and 32 s at
11,165 deliveries. Near the end of the flight it would be longer. This bounds
how quickly SQL recovers from any serving restart on the complete flight; it is
recorded here, not changed.

The first job's history shows the expected exceptions of the TaskManager loss
(`CompletionException`, `JobMasterException`) and three failed checkpoints
around it. The resubmitted job recorded one failed checkpoint and no exception;
its cause was not examined.

## Second complete-flight run, 2026-11-16

`f09-s3-full-20261116-02` repeated the same interval and schedule after the
maintainer approved the revised criterion. The publisher started 47 s after
the job, once serving reported ready. **Result: failed the declared criterion**
again on visibility alone; every correctness and fault check passed.

Correctness:

- The SQL hash set equals the reference (set digest `070c171b…c7ee8b`).
  21,222 physical rows, 21,054 identities and DISTINCT view rows, at most two
  rows per identity, no conflicting content.
- The 168 physical repeats are the declared re-emissions: 89 facts from source
  offset 7,840 after the TaskManager restore, 71 from 15,875 after the
  resubmission, and the 8-member serving batch. The output topic holds 21,214
  records.
- Both restores used the latest completed checkpoint (54 and 100), and
  re-emission started at the first GPS fact of each restored position. There
  were no operator refusals. The serving fault fired after 6,002 outputs and
  its batch was reread with one content per member.
- During the pause serving held at 26,015 archived deliveries, with the last
  visible input at 26,014 and the producer at 28,076.
- Rebuild `001` read 39,760 archived deliveries; its 21,054 facts equal the
  reference and the original database.

Timing (1,221 samples, largest gap 2.0 s, no observation errors):

| Fault | Outage | Recovery as declared | Limit | Pass |
| --- | ---: | ---: | ---: | --- |
| TaskManager SIGKILL | 27.9 s | 37.2 s | 120 s | yes |
| Serving fault | 1.3 s | 1.9 s | 60 s | yes, but the window closed too early |
| Resubmission | 38.3 s | 46.5 s | 180 s | yes |
| Archive pause | 122.3 s | 35.3 s catch-up | 60 s | yes |

The start-up group of the first run is gone: the first facts were visible
within the sample interval. The terminal drain was 0 s. 180 facts outside the
windows exceeded 15 s, at most 32 s. All were acknowledged in the 18 s after
the serving fault, while the restarted worker again wrote nothing for about
32 s. The intermediate measure closed the window at the first sample after the
resume. One fact of the batch written before the exit had been acknowledged
just before the fault, but the 2-second samples first showed its
acknowledgement in that sample, after the resume action. The measure took it
for a post-resume fact and treated the consumer as back.

The strict form now counts only facts that the first sample at or after the
resume did not yet cover; such a fact cannot belong to a batch written before
the fault. `tests/test_fault_analysis.py` reproduces this timeline, and both
earlier rules fail it.

A post-hoc evaluation with the strict measure, kept as
`reanalysis-strict-measure.json` beside `result.json` and not acceptance
evidence, passes every declared limit. The serving fault recovers in 37.9 s
against 60 s. Visibility outside the windows is at most 2.0 s, recovery and the
drain pass, and coverage is established. Under the
declared measure the verdict stays `failed_criterion`.

## Acceptance, 2026-11-16

The maintainer accepted step 3 on the evidence of `f09-s3-full-20261116-02`
evaluated with the strict recovery measure
(`reanalysis-strict-measure.json`), instead of a third complete-flight run.
The basis and its limits:

- The run's own `result.json` keeps `failed_criterion`; no run evidence was
  rewritten. The acceptance rests on a measure changed after the run, so the
  run was not blind to it.
- The change touches only where a fault window ends. It does not change the
  observer samples, the 15 s visibility limit, the recovery limits, the drain
  limit or any correctness check, and every correctness and fault check passed
  under the declared criterion as well.
- The strict rule fixes a demonstrated defect: comparing sampled
  acknowledgement times with the resume time. A synthetic regression test
  reproduces that defect.
- Under the strict measure the serving fault's window ends 37.9 s after it
  started, within its 60 s limit. That window holds the 32 s in which the
  restarted worker wrote nothing, so the delayed facts count against the
  fault's recovery limit, not the steady-state visibility limit.

A later fault run uses the strict measure as declared; its `criterion.json`
states it.

## Not verified

These failures stay outside the verified profile:

- **Broker.** The broker process, its volume or its disk failing, and a broker
  restart while producing. One broker has no replica, so any of these is an
  outage of the whole profile, and recovery depends on the local volume alone.
  The publisher cannot resume either: its acknowledgement ledger refuses an
  existing file.
- **Flink.** JobManager loss: the profile has no high availability, so a
  JobManager restart forgets the job, and recovery would be a resubmission from
  a retained checkpoint, which was tested only after a cancellation. Also: a
  failure during a checkpoint, corrupt or missing checkpoint files, exhaustion of
  the three restart attempts, a Python worker crash inside a running
  TaskManager, and restoring a checkpoint into changed operator code or state
  format (the v1 state is refused by design).
- **Workers and storage.** SIGKILL of the archive worker (only a graceful stop
  was tested), serving stopped before the SQL acknowledgement or inside the
  write, ClickHouse or SeaweedFS restarts during writes, and concurrent writers.
- **Host.** Docker engine or host restart, power loss and the durability of
  `fsync` through Docker Desktop's virtual disk, disk exhaustion, memory
  pressure and clock changes. The observer, the profile and its volumes share
  one machine, so these are single points of failure.
