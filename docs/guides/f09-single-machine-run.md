# Complete F09 replay on one machine

## Status, 2026-11-13

[ADR-0052](../adr/0052-single-machine-recording-profile.md) defines this profile.
Preparation and `docker compose config` have been checked; no container of the
profile has run. Each command below that builds, starts or stops services needs
explicit maintainer authorization.

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

Grafana is at `http://127.0.0.1:13003/`, and the admin password is in
`compose.env`. The Flink UI is at `http://127.0.0.1:18082/`.

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

These have only static or fake-boundary checks so far:

- SQL advances while the publisher is still running.
- Stopping `archive-worker` holds SQL at the archived prefix, and SQL catches up
  after `archive-worker` starts again from its durable cursor.
- Two duplicate deliveries add physical rows but no logical facts.
- The `points` view and the one-second dashboard buckets stay inside the
  ClickHouse and Grafana budgets at full size.
- The four reference parts upload to SeaweedFS and read back.
- Peak CPU, memory and volume sizes from `resources.jsonl`.
