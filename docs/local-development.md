# Run locally

The default setup fits on one computer: one Kafka broker and a Flink session
cluster with one JobManager and one TaskManager. Each battery topic has 12
partitions; Flink starts with two task slots and parallelism two.

## Prerequisites and commands

Use Docker Desktop with Linux containers, or Docker Engine with Compose v2 on
Linux. Allocate at least 6 GiB of Docker memory and four CPUs for the configured
budgets. Python 3.13 runs the helper/demo using only its standard library and
this repository's existing code. No `pip install`, uv environment, host Java,
Maven, flight log or private lab configuration is needed for this example.
The first start needs internet access to pull images and the pinned connector.

From the repository root:

```sh
python scripts/local.py start
python scripts/local.py demo
python scripts/local.py status
python scripts/local.py stop
```

`start` builds the small connector layer, creates the two topics and waits for
the broker, JobManager and registered TaskManager. `demo` submits or reuses the
running battery SQL job, converts the checked-in synthetic source and publishes
its three accepted measurements. It reads results back from Kafka and verifies
the current delivery run's original content, IDs, source time, values and power.
Successful output includes `"status": "verified", "measurements": 3`.

Open the [Flink UI](http://127.0.0.1:8081) to inspect
`local-battery-projection-v1`. Kafka is available to local clients at
`localhost:9092`; containers use `kafka:9092`. Running a second copy on these
ports is not supported. Select a local Docker context; the helper refuses remote
endpoints. The Compose project is always `fleet-telemetry-local`.
Its private bridge uses `10.253.240.0/28`; set `FLEET_LOCAL_SUBNET` to an unused
private subnet if that range overlaps a VPN or another local Docker network.

The equivalent core startup command is `docker compose up -d --build --wait`.
Job submission uses `docker compose --profile jobs run --rm submit`; the Python
helper additionally avoids submitting a second running copy and checks output.
`stop` stops only this project and retains its Kafka/checkpoint volumes.
Job submission after a full stop is explicit; automatic checkpoint restoration
has not been added to this starter.

## What this example establishes

The path is synthetic source → canonical converter → Kafka → Flink SQL → Kafka
readback. IDs and measurement time survive unchanged. Negative current remains
negative, missing values remain unknown, and power is `voltage_v * current_a` in
watts. This is an instantaneous demo projection, not a battery-window or energy
result. The exact original event is retained as `raw_event`.

The source topics are dedicated to the checked fixture. This SQL example is not
a validator for arbitrary JSON, flight logs or physical devices. It does not
provide the full archival/ClickHouse/Grafana acceptance path. Those components
can be added on the same machine when their existing contracts are integrated;
they are not required to try the streaming core.

Delivery is at least once. Repeated runs retain the same measurement IDs with
different delivery-run IDs; physical output may contain repeats. Readback checks
the current run and does not count historical results as new progress. The
4,096-record/16-MiB readback guard can refuse a busy retained demo topic. Stop
instead of automatically deleting data or silently ignoring the guard.

Kafka retains one hour of topic history with an 8-MiB per-partition byte budget
plus segment/maintenance overhead. Kafka data and Flink checkpoints are local
named volumes. One broker has no replica-based availability, and same-machine
storage does not survive host/disk loss. These settings are for development.
No source-to-archive durability or end-to-end exactly-once claim follows.

## Implementation and checks

[ADR-0051](adr/0051-single-machine-default.md) records the topology choice,
versions, resource budgets and scope. `compose.yaml` owns the local services;
`runtime/local/` contains the topic initializer, connector image and SQL job.
`scripts/local.py` handles lifecycle and complete synthetic readback.

Focused checks:

```sh
python -m pytest tests/test_local.py tests/test_split_setup.py -q
python -m ruff check scripts/local.py tests/test_local.py
python -m mypy scripts/local.py tests/test_local.py
docker compose config --quiet
```

The Python check commands need the existing development environment; the runtime
helper itself does not. [Full-stack architecture](architecture.md),
[contracts](data-contracts.md) and [roadmap](roadmap.md) retain broader product
requirements. Dated distributed runs in historical reports are not installation
prerequisites for the default setup.

## Local verification, 2026-11-11

The exact default commands were exercised on Windows with Docker Desktop Linux
containers and Python 3.13.1. Two `demo` invocations both verified three complete
measurements with different delivery runs and the same measurement IDs. The
second invocation reused the existing job; REST confirmed one running job, one
TaskManager and two total slots. Kafka readback confirmed 12 partitions and
replication factor one for both data topics. The final checkpoint snapshot
reported 76 completed, zero failed and zero restored checkpoints; no restore or
failure injection was tested. `python -S scripts/local.py status` also passed.

After verification, `stop` stopped only this new project. Both named volumes
remain present and the three previously running historical broker containers
remain running. No old network, volume, topic, job or retained source was changed.

One small-workload Docker snapshot reported approximately 361 MiB for Kafka,
281 MiB for JobManager and 451 MiB for TaskManager (about 1.07 GiB combined).
This is one observation after six input deliveries, not a peak, load benchmark,
minimum-memory guarantee or whole-Docker memory measurement. The configured
limits and transient SQL client budget above remain the planning boundary.
The stock connector logged metric-name collision warnings for
`pendingCommittables`; output reconciled, but metric completeness was not certified.

The first start built successfully but could not allocate a Docker network
because the host's default address pools were exhausted by retained projects.
The final profile uses a checked free `/28` subnet with an optional override;
no existing networks were removed. The subsequent startup and both demos passed.

The two verifier tests and eight existing source-export cases pass (10 total).
Ruff lint/format checks pass for 261 Python files; strict root mypy passes for
93 files, and explicit strict mypy passes for the new runner and test. The module
size guard, offline lock check and Compose configuration check pass. No Python
packages were installed or synchronized. A full historical service/failure
matrix or hosted CI was not repeated for this independent starter.

The changed files for this increment are `.gitattributes`, `README.md`,
`CONTRIBUTING.md`, `docs/README.md`, `docs/architecture.md`,
`docs/data-contracts.md`, `docs/deployment-and-terraform.md`, `docs/roadmap.md`,
`docs/testing-strategy.md`, `github-preparation.md`,
`runtime/continuous/split_transfer.py` and `tests/test_split_setup.py`.
Created files are `compose.yaml`, `runtime/local/Dockerfile`,
`runtime/local/init-topics.sh`, `runtime/local/battery.sql`, `scripts/local.py`,
`tests/test_local.py`, `docs/adr/0051-single-machine-default.md` and this guide.
The source exporter includes the root Compose file; its existing regression
checks that the default setup survives a source handoff.

Original source/index bytes and detailed command logs are retained under ignored
`.local-discovery/single-host-20261111/`; generated synthetic runs stay in their
own `local-demo-*` directories. No staging, commit or publication was performed.
Rollback stops this Compose project, retains its volumes, restores the listed
modified files from the saved baseline and removes this increment's new source
files together. No existing persistent format requires migration.
