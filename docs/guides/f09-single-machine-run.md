# Complete F09 replay on one machine

## Status, 2026-11-13

[ADR-0052](../adr/0052-single-machine-recording-profile.md) defines this profile
and records the first complete run, `f09-full-20261113-002`. Each command below
that builds, starts or stops services needs explicit maintainer authorization.

For routine operation (start, status, evidence, stop and restoration) use the
[operator runbook](operations-runbook.md); this guide keeps the manual steps
and the orchestrated scenario.

## Prerequisites

- Docker Desktop with at least 12 GiB and 8 CPUs available to the engine. The
  steady-state limits total about 10.5 GiB.
- Local images: the `fleet-telemetry/recording-flink` digest in Compose,
  `fleet-telemetry/seaweed-m4:4.48-local1`, `clickhouse/clickhouse-server:26.8.34.13`,
  `grafana/grafana:13.2.4` and `apache/kafka:4.4.0`. All are `pull_policy: never`.
- The Grafana ClickHouse plugin 4.23.2 under
  `.local-discovery/gold-grafana-20261104/plugins/`.
- A complete-flight bundle and reference from the
  [stream preparation guide](f09-stream-replay.md#complete-flight-preparation-2026-11-13).
  The run ID comes from the bundle. A new attempt needs a newly prepared bundle
  with a new run ID, because every scope must be fresh.

### Which local images to keep

Use the digest references in [recording.yml](../../compose/recording.yml) for
inventory. From a prepared run, `docker compose -f compose/recording.yml
--env-file <private>/compose.env --profile "*" config --images` lists the
references. Use `docker image inspect <reference>` to check each one locally.

| Image | Role and rebuild inputs |
| --- | --- |
| `pyflink-m3:2.2.1-local2` | Retained for M3, link-watch, the generated six-broker and two-host lab profiles, and rollback. Keep the [connector backport builder](../../runtime/pyflink/prepare_connector_backport.py), [final Dockerfile](../../runtime/pyflink/container/Dockerfile.backport) and [repair evidence](../adr/0023-bounded-kafka-enumerator-backport.md). |
| `pyflink-m3:2.2.1-local1` | Pinned parent of `local2`. Its [Dockerfile](../../runtime/pyflink/container/Dockerfile) needs the exact Linux runtime prefix and payload from [bootstrap](../../runtime/pyflink/bootstrap.py) and [context preparation](../../runtime/pyflink/prepare_runtime_image.py). |
| `kafka-probe:4.4.0` | Pinned parent of `local1`. Keep the [Kafka context preparer](../../scripts/prepare-kafka-image.py) and [base recipe](../../runtime/kafka/Dockerfile). The recording broker itself runs the official `apache/kafka` image. |
| `seaweed-m4:4.48-local1` | Runs the archive service. The [context preparer](../../runtime/s3/prepare_image.py) takes `--archive`, `--license` and a fresh `--output` directory. It checks the [artifact pins](../../runtime/s3/artifacts.json) before staging the binary and Dockerfile. |

These four names use the `fleet-telemetry/` repository prefix. Keep the
images while this profile or its offline rebuild depends on them. A Git tag
preserves recipes only. Before retiring a local image, check all Compose
files, Dockerfile parents and the image constants in
`runtime/continuous/prepare.py` and `split_runtime.py`, which generate the
six-broker and two-host lab profiles. Then verify that its exact pinned
reference can be restored on a fresh engine. For a replacement digest,
validate replay, archive readback and restart in a fresh run before updating
the pin. Retain the previous image for rollback.

### Building the recording Flink candidate

Use Linux/amd64 and a new BuildKit container with its own content store. The
two input directories below hold the original allowlisted runtime payload from
ADR-0022 and the released Java source from ADR-0023. Copy these directories
to a fresh host to repeat the build. Their contents are external build inputs.
The recipe checks the payload, configuration, utility and notices against
`runtime/pyflink/container/recording-inputs.sha256` before extraction.
The connector builder checks the source, compiler inputs, archive changes
and stock/patched probe outcomes. The final stage checks native imports,
the installed JAR and the launcher under UID/GID 10001.

```powershell
$inputs = ".local-discovery/m3-completion-20261022-001"
docker buildx create --name telemetry-recording-20261118 --driver docker-container
docker buildx build --builder telemetry-recording-20261118 --platform linux/amd64 `
  --build-context "payload=$inputs/build" --build-context "upstream=$inputs/connector-source" `
  --file runtime/pyflink/container/Dockerfile.recording `
  --tag fleet-telemetry/recording-flink:2.2.1-candidate --load runtime/pyflink
docker image inspect fleet-telemetry/recording-flink:2.2.1-candidate --format '{{json .RepoDigests}}'
```

On 18 November 2026 the local image inventory matched the recording pins.
Retain `local2` for M3, link-watch, the six-broker and two-host labs and
previous recording runs, including `f09-s3-full-20261116-02`. Its rollback
reference is
`fleet-telemetry/pyflink-m3:2.2.1-local2@sha256:9cd317885a161473064ad7628d807f87c688bff0d3d7335bf8e2c7b5cfd77956`.
Retain `local1` for rebuilding that image. Retain `kafka-probe` for the
Kafka, checkpoint, M3, M4 reader, six-broker and two-host profiles.
Retain `seaweed-m4` for M4 storage, the two-host archive and recording
archival. The starter uses `fleet-telemetry/local-flink:2.2.1`.
The recording worker and PX4 SITL have separate runtime consumers.

To check a candidate while preserving a previous project's storage, set
the following in a fresh PowerShell session. Choose unused Docker subnets,
a fresh project name and a new run ID. The profile still needs exclusive use
of its published loopback ports. The operator commands use the same project
name for Compose, observer mounts and resource samples. The digest below is
the tested local manifest. For a new build, use the repository digest returned
by inspection above. The connector builder checks the JAR for byte equality;
the build does not assert equality of image metadata across builds.

```powershell
$env:COMPOSE_PROJECT_NAME = 'fleet-recording-check-20261118'
$env:RECORDING_SUBNET = '10.253.241.16/28'
$env:RECORDING_LIVE_SUBNET = '10.253.241.32/28'
$env:RECORDING_FLINK_IMAGE = 'fleet-telemetry/recording-flink@sha256:48b7eb2aa98e49b2c50099e7e04d74c61f34acb4a174bb4180ad7ec30c17d2a1'
.venv/Scripts/python.exe -m runtime.recording.fault_run --run-id flink-image-f09-20261118-01 --start-us 86459069 --end-us 266459069 --fault taskmanager-kill@1200
.venv/Scripts/python.exe -m runtime.recording.live_run --run-id flink-image-live-20261118-01 --silence-at 60 --silence-s 25 --restart-at 115 --restart-down-s 15 --end-at 200
```

For rollback, stop the candidate run with its own project settings. In the
session for the previous project, set the old image reference and verify its
runtime before following the [restore procedure](operations-runbook.md).
The image preflight can run without mounting any checkpoint or data volume.

```powershell
$env:RECORDING_FLINK_IMAGE = 'fleet-telemetry/pyflink-m3:2.2.1-local2@sha256:9cd317885a161473064ad7628d807f87c688bff0d3d7335bf8e2c7b5cfd77956'
docker run --pull=never --rm --network none --read-only $env:RECORDING_FLINK_IMAGE preflight
```

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
