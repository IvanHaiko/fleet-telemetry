# Complete F09 replay on one machine

## Status, 2026-11-13

[ADR-0052](../adr/0052-single-machine-recording-profile.md) defines this profile
and records the first complete run, `f09-full-20261113-002`. Each command below
that builds, starts or stops services needs explicit maintainer authorization.

## Prerequisites

- Docker Desktop with at least 12 GiB and 8 CPUs available to the engine. The
  steady-state limits total about 10.5 GiB.
- Local images: `fleet-telemetry/pyflink-m3:2.2.1-local2`,
  `fleet-telemetry/seaweed-m4:4.48-local1`, `clickhouse/clickhouse-server:26.8.34.13`,
  `grafana/grafana:13.2.4` and `apache/kafka:4.4.0`. All are `pull_policy: never`.
- The Grafana ClickHouse plugin 4.23.2 under
  `.local-discovery/gold-grafana-20261104/plugins/`.
- A complete-flight bundle and reference from the
  [stream preparation guide](f09-stream-replay.md#complete-flight-preparation-2026-11-13).
  The run ID comes from the bundle. A new attempt needs a newly prepared bundle
  with a new run ID, because every scope must be fresh.

## Procedure

Run from the repository root in PowerShell. The private directory must not exist:

```powershell
$private = ".local-discovery/recording-private-f09-full-20261113-001"
.venv/Scripts/python.exe -m runtime.recording.prepare --bundle .local-discovery/f09-full-20261113-001/bundle --reference .local-discovery/f09-full-20261113-001/reference/facts.jsonl --source .local-discovery/real-ulog-20261027-001/log_67_2025-8-21-14-24-48.ulg --private $private
$compose = @("compose", "-f", "compose/recording.yml", "--env-file", "$private/compose.env")
docker @compose --profile run config --quiet
```

The following steps need authorization. Build the worker image (this downloads
the pinned base image and wheels), start the services, initialize and submit:

```powershell
docker @compose --profile run build initialize
docker @compose up -d kafka jobmanager taskmanager archive serving grafana
docker @compose --profile run run --rm initialize
docker @compose --profile run run --rm submit
```

Start resource sampling in a second terminal, then the archive and serving
workers, then the publisher. The publisher paces the 39,760 deliveries by
native time, about 39 minutes:

```powershell
.venv/Scripts/python.exe -m runtime.recording.sample_resources --output .local-discovery/f09-full-20261113-001/resources.jsonl
docker @compose --profile run up -d archive-worker serving-worker
docker @compose --profile run up -d publisher
```

Grafana is at `http://127.0.0.1:13003/`. The admin password is the one in the
`compose.env` of the first preparation that created the `grafana-data` volume;
Grafana ignores later ones. Five failed sign-ins lock the user for a few minutes.
The Flink UI is at `http://127.0.0.1:18082/`.

## Completion and evidence

The serving worker writes `serving-complete.json` only when all of these hold:

- the publisher has completed;
- every delivery is archived and read back byte-for-byte;
- every fact equals the reference;
- SQL holds exactly the reference identities;
- the output topic is fully consumed.

Role status files, ledgers and cursors stay in the `evidence` volume under
`/evidence/<run>/state`. A stopped run keeps everything; record its actual
interval rather than calling it complete.

Stop the profile without removing volumes:

```powershell
docker @compose --profile run stop
```

Never use `down -v`; it would delete the retained evidence.

## Checks to record during the run

Run `f09-full-20261113-002` recorded each of these;
[ADR-0052](../adr/0052-single-machine-recording-profile.md#complete-flight-run-2026-11-13)
has the figures. A later run records the same items:

- SQL advances while the publisher is still running. In the first run it kept up
  only for the first 10,000 facts.
- Stopping `archive-worker` holds SQL at the archived prefix, and SQL catches up
  after `archive-worker` starts again from its durable cursor.
- The two declared duplicate input deliveries reach neither the output topic nor
  SQL: Flink suppresses them. Physical SQL repeats come only from retried SQL
  writes, which [ADR-0050](../adr/0050-integrated-f09-runtime.md#local-evidence-2026-11-11)
  exercised for the 60-second interval and the complete run did not.
- The `points` view and the one-second dashboard buckets stay inside the
  ClickHouse and Grafana budgets at full size, through Grafana's datasource.
  Browser rendering is a separate check, not yet made.
- The multipart reference uploads to SeaweedFS and reads back.
- Peak CPU, memory, PIDs and volume sizes from `resources.jsonl`.

## Fault runs

`runtime/recording/fault_run.py` performs the steps above for one interval and
injects the faults that
[ADR-0053](../adr/0053-recording-recovery-boundaries.md) defines. It writes
`criterion.json` before any service starts, then prepares the inputs, starts the
profile, waits for serving's first status before starting the publisher,
executes the schedule, reconciles, rebuilds from the archive and stops the
profile without removing volumes. Each run needs a new run ID; evidence goes to
`.local-discovery/<run>/`. A 60-second interval with one serving fault:

```powershell
.venv/Scripts/python.exe -m runtime.recording.fault_run --run-id <new-run-id> --start-us 86459069 --end-us 146459069 --fault serving-ack-cursor@200
```

`--fault` takes `taskmanager-kill@N`, `job-resubmit@N`, `serving-ack-cursor@N`
or `archive-pause@N:seconds`. `N` counts acknowledged deliveries, or written
outputs for the serving fault. `--recovery-limit kind=seconds`,
`--visibility-limit` and `--drain-limit` change the declared limits. The
status in `result.json` is `passed`, `failed_criterion` or `failed`.
