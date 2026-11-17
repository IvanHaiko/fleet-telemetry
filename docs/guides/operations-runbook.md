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

Another registered recording, complete
([ADR-0057](../adr/0057-registered-recordings-in-the-integrated-path.md));
its verified inspection must exist at the path listed in
`runtime/recording/fault_run.py`:

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops start --run-id <run> --source f07 --start-us 0 --end-us 190000000
.venv/Scripts/python.exe -m runtime.recording.ops start --run-id <run> --source f03 --start-us 0 --end-us 410000000
```

Every registered recording uses the same dashboard, titled with its label
(*F07 historical recording* and so on), and the same SQL quality checks. A
file that is not registered is refused before any service starts.

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

**Manual datasource check, signed in.** `grafana_health` does not show that
the datasource can query ClickHouse, and the Grafana API needs a signed-in
user. After `start` (and after `resume`):

1. Sign in at `http://127.0.0.1:13003/` as `recording_admin`. Grafana keeps
   the administrator password of the run that first created the
   `grafana-data` volume; later runs' generated passwords do not change it.
   Five failed sign-ins lock the user for a few minutes.
2. *Connections → Data sources → F09 recording ClickHouse → Save & test.*
   Expected: *Data source is working*. A refusal (`AUTHENTICATION_FAILED`,
   code 516) means the Grafana identity holds another run's password; run
   `ops view --run-id <run>` once the run has stopped, or initialize a new
   run.
3. Open the run's dashboard (*F09 recording → Telemetry — F09 historical
   recording stream* or *Live PX4 SITL session*). Expected: no panel shows a
   red error corner or *No data*; *Run health* lists every check with
   `ok`; the live view's *Connection* shows `observed` while packets arrive.
   Panels showing `TOO_MANY_SIMULTANEOUS_QUERIES` mean the recording
   ClickHouse override is not mounted.
4. Record the result (pass or the failing panel and its message) in the
   run's `events.jsonl` notes or the run report. Never record coordinates.

## Viewing a stored run

```powershell
.venv/Scripts/python.exe -m runtime.recording.ops view --run-id <run>
```

`view` starts only the archive, ClickHouse and Grafana with the stored run's
environment, renders the current dashboard templates for its database into
`.local-discovery/recording-view-<run>/dashboards/`, recreates Grafana so
that it reads them, and makes the datasource able to read the run (it
re-keys the shared Grafana identity only if ClickHouse refuses it). It
prints the dashboard address and the number of SQL points. It refuses while
Kafka, Flink or any worker runs, because recreating ClickHouse with another
run's environment would disturb a running run. One stored run is viewable at
a time; nothing is copied or deleted.

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
could not be measured prints `unknown`. Below it, the *Health* table lists
every monitoring signal with its state and value
([ADR-0056](../adr/0056-run-health-without-a-monitoring-stack.md)); `status`
then takes about 25 s. `collect` and `stop` save the same observations and
signals as `health.json`.

### Health signals

States are `ok`, `warn`, `fail` and `unknown`. `unknown` means not observed
(for example Flink signals while no job runs); it is never a pass and never a
zero.

| Signal | `warn` when | `fail` when | Response |
| --- | --- | --- | --- |
| `source_admission` | live: lost packets or sequence gaps > 0 | F09 counts do not reconcile; live gateway refusal | `warn`: the loss is recorded, the run continues. `fail`: collect, stop, keep the run; check the prepared inputs or the gateway refusal category |
| `processing_dispositions` | F09 complete with duplicates ≠ 2 (after a restore the counters restart) | rejected > 0 (the job fails with `recording_operator_refused`) | `fail`: collect; the job's exception history names the refusal |
| `sql_repeats` | physical rows > 2 × facts | — | repeated serving retries; check the serving log for retries; `verify` still decides the logical result |
| `kafka_input_end` | — | end ≠ declared deliveries at completion, or above them while running | collect and stop; compare the publisher ledger with `kafka.json`. While a live session runs, the end must be at least the count the current gateway epoch acknowledged (that count is per epoch and written every 0.5 s); equality with the final count is required at completion |
| `archive_coverage` | lag > 1,000 deliveries or status older than 10 s | status older than 60 s; lag > 0 after completion | `warn`: watch two windows. `fail`: is `archive-worker` running? Start it; it continues from its cursor |
| `serving_coverage` | as archive, against the archived prefix | as archive | start `serving-worker` or `resume` |
| `checkpoints` | more than 1 failed (1 is the submission trigger) | latest completed older than 30 s | `fail`: check the TaskManager; `collect` before restarting anything |
| `job_restarts` | > 0 (Flink recovered) | Flink answers but no job of the run runs | `fail`: `resume` |
| `kafka_broker` | — | unhealthy, topic IDs changed, any unavailable partition | stop the run, collect, do not reuse its topics |
| `kafka_group_lag` | a run group's lag > 1,000 | — | processing is behind by more than about a minute of F09 input |
| `kafka_broker_metrics` | — | — | always `unknown`: no JMX exporter in the profile |
| `memory` | ≥ 80 % of a container's limit | ≥ 95 % | `fail` precedes an OOM kill; collect, then stop the run |
| `cpu` | ≥ 95 % of a container's CPU budget | — | informational; the TaskManager and serving may sit at their budget during catch-up |
| `memory_budget` | — | running limits exceed the engine's memory | raise Docker Desktop's memory before starting |
| `disk_free` | < 2 complete runs (1,024 MiB) on the Docker or host disk | < 1 run (512 MiB) | free space before starting another run; never delete run volumes to do it |
| `quality.*` | — | any violation of the declared rule | collect and keep the run; the check's name says which contract rule failed. The same checks are on the *Run health* panel |

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
  restarts grow with the archived prefix. The `memory_budget` signal compares
  the running limits with Docker's engine memory.
- Disk per complete F09 run, measured on the stored step 5 run: 287 MB on the
  Docker disk (Kafka topics 79.6 MB, archive objects 95.9 MB, evidence volume
  61.3 MB, checkpoints 26.4 MB, SQL 24.0 MB) and 118 MB in the run directory on
  the host; the verification rebuild adds about 24 MB. The declared budget is
  512 MiB per run on each disk; `disk_free` warns below two runs. Docker's
  virtual disk grows on the host disk, so the smaller free space counts.
- ClickHouse system logs: until 2026-11-17 they had no retention and grew by
  about 650 MB per hour of operation (496 MB after the step 6 complete run).
  The profile now keeps only `query_log` for 3 days and crash reports
  (`runtime/recording/clickhouse-system-logs.xml`,
  [ADR-0056](../adr/0056-run-health-without-a-monitoring-stack.md#final-complete-flight-run-2026-11-17)).
  Older log data stays in the `system` database, including the renamed
  `query_log_0`, until the maintainer removes it.
- Resources are sampled into `resources.jsonl` (memory bytes and share of the
  limit, CPU against the container's budget, both disks, every volume's size)
  during readiness and while `complete` waits (`--sample`, default 15 s).
  `complete` logs `completing` before anything stops; after it, a container
  sampled at 0 B is exiting (the gateway, the simulator and the workers end
  on their own), not a missing measurement.
- Peak memory on the complete F09 flight (2026-11-17), against compose limits:
  serving worker 442/512 MiB (86 %), Kafka 740/1,024 MiB (72 %), Grafana
  501/768 MiB (65 %), ClickHouse 1,165/2,048 MiB (57 %), TaskManager
  889/3,072 MiB (29 %); every other container below 46 %. The serving worker
  grows with the archived prefix and is the first to reach its limit on a
  longer source. On the five-minute live session Grafana rose to 721/768 MiB
  (94 %) with the live dashboard open; watch the `memory` signal on longer
  live sessions.
- Capture to browser, computed rather than measured: SQL visibility (2.0 s on
  the complete flight) + one 2 s sample + the 5 s dashboard refresh + the
  slowest simultaneous panel query (2.1 s) ≈ 11 s. On the complete flight a
  refresh's 16 queries take 1.1 s at the median.
- Measured results: SQL visibility within the 2 s sample interval outside
  fault windows on the complete flight (ADR-0052, ADR-0053); live visibility
  within 1 s (ADR-0054). After a whole-profile stop, `resume` reached
  readiness with a new fact in 120.8 s on the complete F09 flight and 98.4 s
  on a live session (ADR-0055 evidence runs).

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
- alerting between two `ops` invocations (signals are computed on demand),
  and Kafka broker metrics beyond health, offsets, partition availability
  and topic sizes.
