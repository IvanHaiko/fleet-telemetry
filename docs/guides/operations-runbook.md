# Operator runbook: single-machine recording profile

This runbook covers one run of the [recording profile](../adr/0052-single-machine-recording-profile.md)
on one computer, with either source: the F09 replay or a live PX4 SITL session
([ADR-0054](../adr/0054-live-sitl-recording-profile.md)). One command,
`runtime/recording/ops.py`, starts, inspects, stops, preserves and restores a
run ([ADR-0055](../adr/0055-recording-operations-and-restoration.md)). Starting
or stopping services needs the maintainer's authorization, as for the earlier
guides.

Run every command from the repository root. Each run has a new run ID
(`[a-z0-9][a-z0-9-]{2,39}`), its own directory `.local-discovery/<run>/` and its
own private directory `.local-discovery/recording-private-<run>/`.

## Before a start

- Docker Desktop with at least 12 GiB and 8 CPUs for the engine; the local
  images listed in the [F09 guide](f09-single-machine-run.md#prerequisites).
  The live source also needs the items in the
  [live guide](live-sitl-recording-run.md#what-it-needs).
- No worker of an earlier run may be running; `start` refuses otherwise.
- Never run `docker compose down -v`, `docker volume rm` or `docker system
  prune`. The `evidence`, `state`, `kafka-data`, `archive-data` and
  `serving-data` volumes hold every earlier run.

## Start

F09 replay of one interval (native time, 1x):

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops start --run-id <run> --source f09 --start-us 86459069 --end-us 146459069
```

Live SITL session:

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops start --run-id <run> --source live
```

`start` prepares the scope, starts Kafka, Flink, SeaweedFS, ClickHouse and
Grafana, initializes fresh topics, database and bucket, submits the job,
starts an observer, the archive and serving workers and the source, and then
returns only when every readiness check below passes between two snapshots
taken `--window` seconds apart (default 20 s; `--timeout` default 300 s). On a
timeout it prints the status screen and exits with `not_ready`.

| Check | Passes when |
| --- | --- |
| `broker_healthy` | the Kafka container is healthy and the run's topics keep their cluster and topic IDs |
| `flink_slots_registered` | at least one TaskManager slot is registered; `start` and `resume` also wait for a free slot before submitting |
| `job_running` | exactly one job of the run is RUNNING with every vertex RUNNING |
| `checkpoints_completing` | the completed-checkpoint count grew over the window and the latest is at most 30 s old |
| `archive_worker`, `serving_worker`, `source_worker` | the container runs and its progress file is at most 10 s old |
| `clickhouse`, `seaweedfs` | SQL answers queries; the S3 endpoint answers |
| `grafana_health` | `/api/health` reports `database: ok`, without signing in |
| `input_advancing`, `archive_advancing`, `sql_advancing` | the input end offset, the archived prefix and the SQL-visible inputs all grew over the window |
| `source_not_refused` (live) | the gateway reports no refusal |
| `fact_after_resume_visible` (resume only) | SQL holds a fact whose input offset is at or beyond the input end offset measured just after the workers restarted |

**Manual step, maintainer only.** `grafana_health` does not show that the
datasource can query ClickHouse. Sign in at `http://127.0.0.1:13003/`, open the
run's dashboard (*F09 recording* or *Live PX4 SITL session*) and confirm the
panels show data; or use *Connections → Data sources → ClickHouse → Save &
test*. Record the result with the run. Five failed sign-ins lock the user for
a few minutes.

## Status

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops status --run-id <run>
```

One screen with the broker, Flink (version, slots, jobs, checkpoint counts and
the latest checkpoint's age), the committed processing offset and its lag, the
source, archive and serving progress with the age of each progress file, SQL
rows, distinct inputs and the highest visible input offset, SeaweedFS,
Grafana's health, the live view's connection for a live session, the
completion markers, and the readiness checks over `--window` seconds
(`--window 0` takes one snapshot and shows readiness as unknown). A value that
could not be measured prints `unknown`. The last line lists what the profile
does not instrument; those signals stay unknown, never zero.

Read the lags as counts, not times: archive lag is input end minus archived
prefix; processing lag is input end minus the offset Flink committed at its
last checkpoint, so it is up to one checkpoint interval (10 s) of input even
when processing is current. The output end offset includes transaction
markers. Visibility age and capture-to-UI refresh are not shown; the observer
samples in `observe*.jsonl` and the ADR-0053 analysis measure them.

## Completion and verification

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops complete --run-id <run> --timeout 3600
.venv/Scripts/python.exe -m runtime.recording.ops verify --run-id <run>
```

For F09, `complete` waits for `serving-complete.json`. For a live session it
sends `SIGUSR1` to the gateway (which records the final published count),
stops the simulator and then waits. `verify` writes `verify-<stamp>.json`:

- F09: the SQL fact hash set equals the reference, no logical repeats, a
  rebuild from archive objects alone into a separate database equals the
  reference and the original, and after each checkpoint restore the
  re-emitted facts start at the restored source position;
- live: every published event is in the capture, no sequence gap inside a
  gateway epoch, SQL equals the archive-only recomputation, no logical
  repeats, battery and state without measurement time, and association
  statuses equal what input order implies.

## Stop and evidence

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops collect --run-id <run> --label <label>
.venv/Scripts/python.exe -m runtime.recording.ops stop --run-id <run>
```

`collect` writes `.local-discovery/<run>/evidence/<UTC stamp>-<label>/`; `stop`
collects with the label `stop`, stops the run's observers, cancels the run's
job (its checkpoints are retained on cancellation) and stops the containers.
Nothing is deleted.

| File | Content |
| --- | --- |
| `snapshot.json` | the status snapshot at collection time |
| `flink.json` | per job of the run: details, checkpoint statistics and history, exception history |
| `logs/`, `containers.json` | every container log of the run's profiles and observers; state, exit code, image and log configuration |
| `kafka.txt`, `kafka.json` | topic descriptions and configuration, broker configuration, end offsets, the run's consumer groups |
| `progress-files.json` | the run's progress files, cursors and completion markers |
| `volume-inventory.json` | path, size and SHA-256 of every run file in the `evidence` and `state` volumes, checkpoints included |
| `lineage.json`, `working.patch` | code revision, working-tree patch and untracked files with hashes, image references, IDs and repository digests, Docker and Python versions |
| `manifest.json` | declared scope, actual progress, `completed` or `partial` |
| `inventory.json` | path, size and SHA-256 of every file in the run directory, plus the volume entries |

A run is `completed` only when `serving-complete.json` exists. Otherwise the
manifest says `partial` and records the acknowledged deliveries, the archived
prefix, the serving count and, for F09, the native-time interval of the
acknowledged events. Never relabel a partial run.

Collect **before** anything that discards history:

- the JobManager keeps job, checkpoint and exception history in memory only;
  a JobManager restart, `resume` after a host stop or a later run's start
  loses it;
- container logs rotate at 5 MiB × 2 files (2 MiB × 2 for the simulator); a
  container recreated by a changed configuration starts an empty log;
- Kafka keeps committed consumer offsets for 7 days after a group becomes
  empty (`offsets.retention.minutes=10080`). The run topics themselves are
  created with `retention.ms=-1` and `retention.bytes=-1` and do not expire.

While the profile is down, `collect` still saves the volume inventory, the
progress files, the remaining container logs and the lineage; Flink and Kafka
sections then record that they were unreachable.

Captures, ledgers, outputs, bundles and configurations appear in the
inventories as path, size and hash only. Do not paste their contents, or any
coordinate, into reports.

## Restoration after a stop or a host shutdown

The same commands restore a run after `ops stop` or after the host, Docker or
the whole profile stopped without warning:

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops collect --run-id <run> --label outage
.venv/Scripts/python.exe -m runtime.recording.ops resume --run-id <run>
.venv/Scripts/python.exe -m runtime.recording.ops status --run-id <run>
```

`resume` performs these steps and logs each one to `events.jsonl`:

1. starts the services and waits for a healthy broker, a free Flink slot and
   answering storage, then starts Grafana;
2. if no job of the run is RUNNING, lists the run's retained checkpoints that
   have `_metadata` and resubmits the job from the newest with
   `recording_job.py --restore` (NO_CLAIM: the checkpoint is never taken over
   or deleted). The JobManager has no high availability, so after its restart
   this resubmission is the only way back;
3. starts a new observer, then the archive and serving workers, which continue
   from their cursors; serving re-verifies the archived prefix first, which
   takes about 1 s for a 60-second interval and about 30 s at 11,000 archived
   deliveries;
4. starts the source. The F09 publisher continues at the first undelivered
   index after checking its ledger against the broker. The live gateway opens
   a new epoch at the topic's end offset;
5. requires readiness, plus a fact acknowledged after the restart in SQL.

Then `complete`, `verify` and `stop` as usual. The restored job re-emits the
facts after the checkpoint; SQL holds them as physical repeats of the same
content, and `verify` shows the logical result unchanged.

**F09 publisher refusals.** The publisher refuses instead of guessing when the
ledger and the broker disagree:

| Category | Meaning | Action |
| --- | --- | --- |
| `recording_producer_resume_offset` | the broker's end offset is behind the ledger (acknowledged data lost) or more than one ahead | keep the run as partial; preserve the evidence; start a new run |
| `recording_producer_ledger_mismatch` | a ledger line does not match the declared delivery at its index | as above; the ledger or bundle changed |
| `recording_producer_ledger_torn` | the ledger ends inside a line (power loss during the write) | as above; this case was not exercised |
| `recording_producer_topic_not_empty` | a fresh publisher found records in the topic | as above |

**Live source after a restart.** The gateway continues the session only if the
simulator kept running and the archive container kept its `live-source`
address; `resume` refuses with `live_source_not_running` or `live_address`
otherwise. A restarted simulator is a new PX4 boot session. Its boot time
starts again, and the Flink operator refuses positions whose boot time
decreases (`live_runtime_position_order`), so the job would fail after three
restarts. Do not point a restarted simulator at the old session: complete the
old session (`ops complete`), verify and stop it, and start a new run.

## Failure responses

| Failure | Verified in | What happens | Response |
| --- | --- | --- | --- |
| TaskManager killed | ADR-0053 | the restart strategy restores the latest checkpoint within about 30 s | none; confirm with `status`; `verify` after completion |
| Job cancelled or lost | ADR-0053 | no job runs; checkpoints are retained | `resume` (it resubmits from the newest checkpoint) |
| Serving stopped between SQL acknowledgement and cursor | ADR-0053 | restart rereads the batch; physical repeats only | `docker compose ... up -d --no-deps serving-worker` or `resume` |
| Archive worker stopped | ADR-0053 | serving holds at the archived prefix | start `archive-worker`; it continues from its cursor |
| Source silence (live) | ADR-0054 | the view shows *stale* | none; packets not sent are not data |
| Gateway restart (live) | ADR-0054 | the view shows *unknown*; positions show `unknown_after_restart` until new receipts | start `live-gateway` or `resume`; packets sent while it was down are outside every epoch |
| Whole profile stopped (host shutdown) | ADR-0055 | the JobManager forgets the job; every worker and the source stop | `collect --label outage`, then `resume` |
| Any failure under *Not verified* | — | unknown | `collect`, `stop`; keep the evidence; do not reuse the run |

## Operating limits

- One run at a time on one Docker engine; its scope (topics, database, bucket,
  checkpoints) is fresh and never reused.
- F09: at most 50,000 deliveries; the complete flight is 39,760 deliveries and
  about 39 minutes at 1x. Live: at most 50,000 deliveries and 30 minutes per
  gateway process.
- Steady-state container limits total about 10.5 GiB of memory; serving
  restarts grow with the archived prefix.
- Measured results: SQL visibility within the 2 s sample interval outside
  fault windows on the complete flight (ADR-0052, ADR-0053); live visibility
  within 1 s (ADR-0054); restoration times in ADR-0055.

## Not verified

These remain outside the verified profile. ADR-0053 and ADR-0054 have the
detail:

- power loss, SIGKILL of every process at once, Docker Desktop's virtual-disk
  durability, disk exhaustion, memory pressure and clock changes;
- broker volume or disk failure; a broker failure while the rest keeps running;
- JobManager loss while the rest keeps running, a failure during a checkpoint,
  corrupt or missing checkpoint files, exhaustion of the restart attempts;
- SIGKILL of the archive worker; serving stopped before the SQL acknowledgement
  or inside the write; ClickHouse or SeaweedFS restarts during writes;
- a torn publisher ledger; a restarted simulator joined to an old session;
- monitoring of source admission and rejections, duplicate and late
  dispositions, archive coverage and lag as alerts, Kafka health beyond the
  healthcheck, and resource and disk budgets.
