# ADR-0055: Operations, evidence preservation and restoration of the recording profile

**Status:** Accepted, 2026-11-16, by maintainer decision. Proposed earlier on
the same day. The operations command, the evidence collection and the
publisher continuation are implemented. Three debug runs on short intervals
and one evidence run per source, each under a criterion the maintainer
approved before it, passed ([evidence runs](#evidence-runs-2026-11-16)).

## Problem

Roadmap step 5 asks for one documented start, status and stop flow for the
[single-machine recording profile](0052-single-machine-recording-profile.md)
with both sources, the F09 replay and the
[live PX4 SITL session](0054-live-sitl-recording-profile.md). The flow must
verify the broker, the run's actual Flink job, the archive and serving
workers, the datasource and advancing traffic; save evidence before history
or rotation discards it; and come with an operator runbook and a checked
restoration procedure.

What existed:

- `runtime/recording/profile.py` with start, status and stop helpers, and two
  orchestrators that each ran one declared scenario
  ([ADR-0053](0053-recording-recovery-boundaries.md), ADR-0054);
- readiness meant a healthy broker, a free Flink slot and answering storage;
  nothing confirmed that the job checkpointed or that traffic reached SQL;
- evidence was what each orchestrator chose to write. Flink's job, checkpoint
  and exception history lives in JobManager memory, container logs rotate at
  5 MiB × 2, and neither was saved by a stop;
- the F09 publisher could not continue a run: it created its acknowledgement
  ledger exclusively, so any restart refused. A SIGTERM was recorded as
  `failed`. With an absent ledger it published one record into a non-empty
  topic before its offset check refused;
- the JobManager has no high availability, so a whole-profile stop loses the
  job; ADR-0053 lists host and Docker restarts as not verified.

Two assumptions of the task were checked rather than taken over. The run
topics are created with `retention.ms=-1` and `retention.bytes=-1`
(`runtime/continuous/kafka.py`); they do not expire. What does expire is
Kafka's committed consumer offsets, 7 days after a group becomes empty
(`offsets.retention.minutes=10080`), and the broker default of 168 hours,
which applies to no run topic. The live gateway already opened a new epoch on
every start and continued at the topic's end offset.

## Decision

**One operations command** on top of `Profile`, without a new service or
dependency:

| Module | Lines | Role |
| --- | ---: | --- |
| `runtime/recording/ops.py` | ~400 | `start`, `status`, `collect`, `stop`, `resume`, `complete`, `verify` |
| `runtime/recording/ops_view.py` | ~300 | snapshot, readiness checks, one-screen status |
| `runtime/recording/evidence.py` | ~350 | evidence collection and inventory |
| `runtime/continuous/recording_status.py` | ~270 | read-only probe in a short-lived worker container |
| `runtime/recording/recovery_run.py` | ~300 | the restoration drill with its criterion |

`Profile` gained `submit` (with an optional `--restore` checkpoint) and
`start_observer`, which the two orchestrators and the fault actions now share
instead of three copies.

A snapshot joins what the host sees (container states, the Flink REST API on
loopback, Grafana's unauthenticated `/api/health`) with the probe inside the
archive container's network namespace: the run's progress files reduced to
counts, times and states, SQL counts, the S3 endpoint, Kafka end offsets, the
processing group's committed offset and, for a live session, the `live_state`
connection. Readiness compares two snapshots a declared window apart, because
advancing traffic and completing checkpoints are changes. There are thirteen
checks for F09 and fourteen for a live session (the gateway reports no
refusal), listed in the [runbook](../guides/operations-runbook.md#start). A value
that could not be measured is `unknown` and never passes.

Grafana readiness uses `/api/health` only. A query through the datasource
needs a signed-in user; the runbook makes it a manual maintainer step instead
of reading Grafana credentials.

**Evidence before discard.** `collect`, and `stop` before it stops anything,
writes `<run>/evidence/<UTC stamp>-<label>/` with the Flink job details,
checkpoint statistics and exception history, every container log of the run's
compose profiles and observers with their states, Kafka topic, broker and
group descriptions and end offsets, the progress files, a path/size/SHA-256
inventory of the run's files in the `evidence` and `state` volumes, the
lineage (code revision, working-tree patch, untracked files, image IDs and
repository digests, versions), a manifest and a file inventory of the whole
run directory. Captures, ledgers, outputs, bundles and configurations appear
as path, size and hash only. A run without `serving-complete.json` is
`partial`, with its acknowledged deliveries, archived prefix, serving count
and, for F09, the native-time interval of the acknowledged events. While the
profile is down the collection still saves the volume inventory, progress
files, remaining logs and lineage, and records the unreachable parts.

**Publisher continuation.** A start computes its next index from the ledger
and the broker (`resume_point` in `runtime/continuous/recording_publish.py`):

- without a ledger the topic must be empty;
- every ledger line must equal the acknowledgement of the declared delivery at
  its index, so the ledger is a prefix of the declared sequence;
- the broker's end offset must equal the ledger length, or exceed it by one
  when the process stopped between the broker's acknowledgement and the
  ledger write. That one record is admitted only if its bytes equal the next
  declared delivery, and its line is appended;
- anything else (end offset behind the ledger, a foreign record, a changed or
  torn ledger) refuses with a fixed category and publishes nothing.

Native-time pacing restarts at the first undelivered event, so the outage
lengthens the run rather than compressing it. A SIGTERM records `stopped`.
`tests/test_recording_publish_resume.py` reproduced the refusal against the
unchanged module (seven failures) before the change, and now checks that
every declared delivery lands once at the offset equal to its index across a
stop, including the window between acknowledgement and ledger write, and that
each disagreement refuses.

**Restoration.** `ops resume` starts the services; if no job of the run is
RUNNING, it lists the run's retained checkpoints that have a `_metadata` file
and resubmits from the newest, as ADR-0053's resubmission does (`NO_CLAIM`, the
checkpoint is never taken over). It starts a new observer, the workers, which
continue from their cursors, and the source. Readiness then additionally
requires a SQL fact whose input offset is at or beyond the input end offset
measured just after the restart: such a fact cannot have been visible before
it, which is the strict form of the ADR-0053 recovery measure.

**Live source.** In the drill the PX4 SITL container keeps running through the
outage; it stands for the external vehicle, which does not stop with the
recording host. The gateway opens a new epoch and continues at the topic's
end offset; packets sent while it is down are outside every epoch. A restarted
simulator is a new boot session: its positions' boot time decreases, which the
Flink operator refuses (`live_runtime_position_order`), so the job would fail.
The gateway checks the boot-time order only within an epoch. This is recorded
and the runbook tells the operator to complete the old session and start a
new run; checking it across epochs in the gateway is a possible later change.

## Alternatives, cost and maintenance

- **Prometheus, Alertmanager or an exporter set** would cover the monitoring
  criterion, but they are new services. The task excludes them; the
  unmonitored signals stay explicit gaps in the status screen.
- **Flink high availability** needs ZooKeeper or Kubernetes in open-source
  Flink: a new service family. Resubmission from a retained checkpoint covers
  the selected restoration.
- **Flink's job archive directory and HistoryServer** keep history only for
  jobs that reach a terminal state, so they would miss a JobManager loss, and
  the HistoryServer is another process. Collecting the REST documents at stop
  and on demand covers both cases for the documents it can reach.
- **A larger Docker log rotation** postpones loss instead of preserving the
  run's logs with its evidence, and changes every container's configuration.
- **A transactional F09 producer** could make a restart's repeat invisible to
  read-committed consumers, but it changes the input topic's semantics that
  the archive coverage relies on (contiguous offsets). Checking the ledger
  against the broker keeps offset = index.

The maintenance surface is the five modules above and two `Profile` methods.
No dependency, image, service or compose change.

## Rollback

Stop using `ops.py` and `recovery_run.py`; the orchestrators behave as before.
Without the publisher change a restart refuses again. With it, a fresh run
behaves as before except that it refuses a non-empty input topic before
producing anything, and a SIGTERM records `stopped`. Every run keeps its
topics, checkpoints, archive objects, databases and evidence.

## Debug runs, 2026-11-16

Short runs while developing; not acceptance evidence. Evidence is under
`.local-discovery/<run>/`.

| Run | Scenario | Result |
| --- | --- | --- |
| `f09-ops-dbg-20261116-01` | 60-second F09 interval with `ops start`; whole-profile stop at about 570 acknowledged deliveries; `ops collect` during the outage; `ops resume` first with the unchanged publisher, then with the change | Start readiness passed all 13 checks. The outage collection reported `partial` with 621 acknowledged deliveries and their native-time interval. With the unchanged publisher, resume restored the job from a retained checkpoint but the publisher exited with `FileExistsError` and readiness refused (source, traffic and new-fact checks). With the change it continued at offset 621; resume reached readiness, including a new fact, 30 s later. `verify`: hash set equal to the reference, no logical repeats, rebuild equal, re-emission from the restored position; 590 physical rows, 538 logical. The stop collection reported `completed` with a 710-file inventory |
| `live-ops-dbg-20261116-01` | Drill on a live session: stop 60 s after readiness with the simulator kept running, 20 s outage, completion at 150 s | Resume restored checkpoint 10, the latest completed before the stop, and reached readiness with a new fact 100.5 s after it began. Two gateway epochs, no capture loss, SQL equal to the archive-only recomputation, no logical repeats. One drill check failed: it compared the outage count with a value read just before the stop, while the gateway kept publishing until SIGTERM (571 read, 584 recorded). The check now requires at least the earlier value |
| `f09-ops-dbg-20261116-02` | Drill on the 60-second F09 interval, stop at 500 acknowledged deliveries, 20 s outage | Passed every drill check. Stopped at 507 acknowledged; the outage collection reported `partial`. Resume restored checkpoint 4, the latest completed before the stop, and reached readiness with a new fact 96.9 s after it began. The input topic ended at the declared 1,019 deliveries. `verify`: hashes equal, no logical repeats, rebuild equal; 625 physical rows, 538 logical; 87 facts re-emitted from source offset 387, the restored position. The inventory scope fix below was applied while this run was in its outage |

The state-volume inventory first matched `<run>-*`, which would also have
listed another run whose ID starts with this one; it now matches the
checkpoint directory and job file names exactly, and
`tests/test_recording_ops.py` covers the case.

Observed while stopping: SeaweedFS does not exit within its 20 s grace period
and receives SIGKILL (exit 137); the TaskManager exits with 239. Neither lost
data in these runs. The resubmitted job records one failed checkpoint after
the restore, as in ADR-0053; its cause was not examined.

## Evidence runs, 2026-11-16

Each run declared its criterion in `criterion.json` before it started, and
`--approved-draft` refused any difference from the draft the maintainer
approved. Scenario for both: a whole-profile stop mid-run as at host shutdown
(`docker compose stop` of every service, no job cancellation), a 60 s outage,
then `ops resume`, completion, `ops verify` and `ops stop`; 20 s readiness
window, 300 s resume limit. Visibility and drain timing, the outage itself,
power loss and SIGKILL of every process are not judged. Evidence is under
`.local-discovery/<run>/` (`result.json`, `verify-*.json`, `evidence/`).

| | `f09-s5-full-20261116-01` | `live-s5-full-20261116-01` |
| --- | --- | --- |
| Interval and stop | complete flight, native time 0 to 2,436 s; stop at 20,000 acknowledged deliveries | live PX4 SITL session; stop 240 s after `ops start` returned, simulator kept running; completion 300 s after the resume |
| Start readiness | 13 checks passed | 14 checks passed |
| At the stop | 20,008 acknowledged; latest completed checkpoint 125 | 1,802 published; latest completed checkpoint 28 |
| Outage collection | `partial`, 10,672 files | `partial`, 1,361 files |
| Restore | checkpoint 126 of the same job, completed while the services stopped; processing offset 20,030 | checkpoint 28; processing offset 1,750 |
| Resume to readiness with a new fact | 120.8 s | 98.4 s |
| Input end | 39,760, the declared deliveries | 4,046, equal to the archived and published count, over two gateway epochs |
| SQL | 21,054 logical facts, 21,059 physical rows; hash set equal to the reference; 5 facts re-emitted from the restored position | 2,890 logical facts, 2,936 physical rows; equal to the archive-only recomputation; 1,156 untimed events without time |
| Rebuild | archive-only rebuild equal to the reference and the original | recomputation from the archive is the admission check |
| Stop collection | `completed`, 21,169 files | `completed`, 3,060 files |
| Verdict | **passed**, all seven checks | **passed**, all eight checks |

Both runs removed nothing; the six volumes are kept.

## Not verified

The [runbook](../guides/operations-runbook.md#not-verified) lists what stays
outside the verified profile. In short: power loss and SIGKILL of every
process, Docker Desktop's disk durability, disk exhaustion, memory pressure,
clock changes, broker volume failure, JobManager loss while the rest runs,
checkpoint failures and corruption, a torn publisher ledger, a restarted
simulator in an old session, and every monitoring signal without
instrumentation.
