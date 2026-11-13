# Guarded continuous PX4 position recording

The local position path now continues receiving new PX4 SITL packets, processing
them in Flink, archiving original selected packets and exact Kafka observations,
and updating SQL while acquisition is still running. Source silence and serving
worker interruption are visible through SQL with cleared current values.
[ADR-0047](../adr/0047-continuous-local-position.md) records the local topology and
limits. The earlier [16-position demonstration](live-position-source-query.md)
and its volumes/evidence remain retained separately.

## Actual execution, 2026-11-04

The active project is `fleetpositionstream20261104-003`; its evidence directory
is `.local-discovery/position-stream-20261104-003/`. The original direct monitor
at `http://127.0.0.1:18771/` and historical Grafana remain separate and running.
No arming or flight command was sent. The new source stream alone uses local
port 14622 and UDP destination 14561 inside the source network.

The successful `start` and `check` commands established:

| Observation | Actual result |
| --- | --- |
| Continuing processing | Input and output cursors passed 100 while both workers remained running; later snapshots continue advancing |
| SQL receipt expiry | First silence drill showed stale/NULL values after 1.412 seconds from stream stop; this measures the remaining position receipt deadline |
| Independent heartbeat loss | A further drill held silence until SQL reported `connection=lost`, `status=stale`, all six current values NULL: 3.213 seconds from stream stop |
| Resume | Both drills returned fresh SQL values with a strictly newer native source timestamp |
| Deliberate repeated input | First selected event published again with identical bytes and identity; no freshness renewal for that old measurement |
| Store crash window | SQL accepted two facts through output offset 61 while durable serving cursor remained 60; SIGKILL before cursor publication, then restart |
| Retry result | Recovery snapshot: 93 physical SQL rows, 91 distinct input coordinates, 90 measurements; two retried facts and one deliberately repeated input remain logically duplicate-safe |
| Exact retained prefix | All 78 selected Kafka deliveries, 77 measurements, exact cluster/topic/partition identity, original selected packet bytes, archived input and complete Flink/SQL fact content agree |
| Runtime snapshot | Seven containers running, no OOM; the intentionally killed store was restarted |

These are separate observations at recorded times, not one atomic count snapshot
of the still-running stream. `continuous-check.json`, `heartbeat-loss-check.json`,
`lineage-prefix-check.json`, `runtime-snapshot.json`, the frozen source manifest,
and `checked-controller.py` retain the evidence. Counts continue changing after
the verified prefix. This is not a sealed acceptance of the entire future run.

At the later heartbeat check Flink reported 23 completed checkpoints, one failed,
zero restores. The retained REST history did not identify that earlier failure;
later checkpoints completed and the job continued. No Flink restore, broker/host
failure or end-to-end exactly-once behavior is claimed.

## Live Grafana screen

Open [Live PX4 - source to SQL](http://127.0.0.1:13002/d/live-position-stream).
It refreshes every five seconds and queries this running stream through the
existing Grafana ClickHouse plugin and SELECT-only `position_reader`. The screen
shows SQL pipeline state, source heartbeat, unique positions, current altitude
and speed, four actual position-history charts and the current SQL row. The
historical F09/F01 screen remains separate. Native numeric boot seconds are the
chart X axis; no synthetic measurement UTC is introduced. History covers the
latest ten native-clock minutes even when current values expire. The position
offset plot is an approximate local change of the estimate, not flight distance.
Numeric panels have no unreviewed alarm thresholds.

The existing Grafana network can reach the published SQL loopback port through
`host.docker.internal:28133`, which was verified from the Grafana container. No
network attachment, new service, SQL grant or existing credential changed.
The datasource password is stored by Grafana's secure credential mechanism,
outside the dashboard JSON. The datasource is local profile-specific; a fresh
profile's reader credential must be connected again with:

```powershell
.venv/Scripts/python.exe scripts/connect-position-grafana.py --evidence .local-discovery/position-stream-20261104-003 --grafana-env .local-discovery/gold-grafana-20261104/runtime.env
```

All ten data queries passed through Grafana's actual datasource with populated
typed frames; each of the four charts returned 600 samples at the check. Browser
verification observed LIVE, CONNECTED, advancing counts, current values and all
four rendered charts. A five-second refresh can delay visible expiry by up to
five seconds beyond the SQL receipt policy; it is not a flight-control display.
Grafana 13.2.4's XY panels require a matching `pluginVersion` to prevent the old
pre-11.1 migration from clearing the new series configuration. String state
panels explicitly include string fields in their reduction.

During this UI connection the store was found stopped at input/output 667,
while collection continued. A FileNotFoundError occurred between probing and
opening the atomically replaced collector-status file on the Docker bind mount.
The new bounded snapshot reader treats only missing files as no health update;
it never renews freshness from cached data and does not hide malformed or denied
reads. A focused regression reproduces disappearance after stat. The store alone
was restarted from retained archive/serving cursors using the new immutable
`source-store-v2` export and its separate manifest; it caught up beyond 1,400
deliveries without resetting Kafka or replacing old evidence. The original
collector/Flink export is unchanged. `POSITION_STORE_SOURCE_ROOT` selects a
store-only repair export and otherwise defaults to the normal source export.

This follow-up creates `scripts/connect-position-grafana.py` and
`runtime/flight_analytics/dashboards/position-live.json`, and modifies
`runtime/continuous/position_sql.py`, `runtime/continuous/position_stream.py`,
`compose/position-continuous.yml`, `tests/test_mavlink_position.py`, `README.md`,
`docs/roadmap.md`, `docs/architecture.md`, `docs/data-contracts.md`,
`docs/deployment-and-terraform.md`, `docs/testing-strategy.md`, and this guide.
The focused live suite now passes 17 tests; lint/type checks pass for the changed
Python scope. Rollback may remove only the `position-live` datasource/new
dashboard connection; stop the new stream using the existing recipe below and
retain volumes and both source exports. Historical datasources and dashboards
are not part of that rollback.

## Current SQL state and time meaning

SQL/S3 remain on authenticated host loopback ports 28133/28333; Flink REST uses
28081. The new `position_reader` credential is in this profile's ignored local
`credentials.json`. Never include it in a URL or paste it into shell history.
The user from the previous short-run SQL instance is a separate principal.

```sql
SELECT * FROM position_stream.live_state;

SELECT count() AS physical_rows, uniqExact(input_offset) AS deliveries,
       uniqExact(event_id) AS measurements
FROM position_stream.facts;

SELECT boot_ms, latitude_deg, longitude_deg, altitude_msl_m,
       relative_altitude_m, ground_speed_m_s, down_speed_m_s
FROM position_stream.positions ORDER BY boot_ms;
```

`live_state` returns current values only when both collector and SQL bridge
receipt heartbeats are younger than three seconds, the selected source receipt
is younger than three seconds, fix qualification is fresh, and SQL has the
collector's selected event. It returns:

- `fresh`: current values come from SQL, with the selected event identity.
- `stale`: source/position receipt deadline expired; current values are NULL.
- `unknown`: collector or store stopped reporting, or a receipt clock is in the
  future; current values are NULL.
- `catching_up`: SQL has not reached the collector's selected event; current
  values are NULL.

`connection` is separately observed heartbeat presence. It becomes unknown when
the health bridge expires. Historical `positions` remain queryable throughout;
history does not establish live state. Native boot milliseconds remain native
source time. The health timestamps are local receipt/processing clocks, not
measurement UTC or physical sample age. Host/container wall-clock jumps can
invalidate freshness; this profile does not establish physical synchronization.

The source contract and calculation remain those of ADR-0046. The helper's
original 32-offset default is preserved; this explicit profile admits at most
3,600 source offsets. The Flink source is unbounded while running, the sink is
at least once, and normalized facts retain exact source-coordinate/byte hashes.
The collector selects approximately one fix-qualified position per second, not
all MAVLink traffic. Selected raw position/GPS packets are fsynced locally before
publication; exact independent Kafka input and raw evidence are then published
immutably to S3 before corresponding output can enter SQL.

## Recovery and resource bounds

The store resumes from the existing archive receipt/cursor and a separately
durable output cursor. It reconstructs expected facts from retained archive and
raw evidence, validates every output, writes SQL, checks complete typed/JSON
readback, then advances output progress. A crash in that window can insert
physical duplicates; measurement and source-coordinate queries remain stable.
Competing content, changed source identity, retention loss or an unconfirmed
publication refuses success. Collector restart with existing publication state
requires explicit review; it does not invent a safe resolution of ambiguous ACKs.

Manual reassignment before each newly inspected retained Kafka interval clears
a queued EOF from the previous high watermark. The existing native reader and
its EOF/gap refusal are unchanged. Reads still require exact offsets and source
identity. This repair was necessary after attempt 002 visibly stopped at input
41/output 40; SQL expired to unknown rather than retaining false freshness.

The recording guard is **one hour or 3,600 deliveries**, whichever occurs first.
This is a bounded local operating session, not a 24/7 service. Collector and
store stop admitting data after the guard and catch-up respectively; Flink and
storage services remain allocated until explicitly stopped. The added PX4 stream
also needs the stop command below. The final completion file is operational
progress, not certification of every possible later output from an unbounded job.

Container limits total 8.25 GiB. One retained snapshot used Kafka 428.4 MiB,
JobManager 445.2 MiB, TaskManager 640.6 MiB, SeaweedFS 159.2 MiB, ClickHouse
201.4 MiB, collector 32.34 MiB and store 65.08 MiB. These are snapshots, not
peaks or capacity evidence. Diagnostic JSON exposes received delivery count,
archive/output progress and unique measurements; complete Prometheus pipeline
signals and latency distributions are still outside this increment.

Kafka/SeaweedFS/ClickHouse/workers share one network namespace to reuse the
existing loopback-only clients. The access bridge permits egress and the source
network can reach namespace listeners. Authentication and host loopback binds
are preserved, but this trusted local topology is unsuitable for an untrusted
device network. There is one broker/partition and no host availability guarantee.
New scoped SQL writer/reader and S3 writer/reader credentials leave old grants
unchanged. No new dependency, image download or cloud mutation was required.

## Run, pause and rollback

The current session remains running after validation. Before a fresh run with
the same ports/subnets, stop the previous integration project while retaining
its data. Example 004 has not been run:

```powershell
.venv/Scripts/python.exe scripts/run-position-stream.py prepare --evidence .local-discovery/position-stream-20261104-004
.venv/Scripts/python.exe scripts/run-position-stream.py start --evidence .local-discovery/position-stream-20261104-004
.venv/Scripts/python.exe scripts/run-position-stream.py check --evidence .local-discovery/position-stream-20261104-004
```

`check` deliberately stops/resumes only port 14622 and kills/restarts only this
profile's store. Run it once per evidence scope; it retains the failure marker
and report. The original 14620 direct-monitor stream stays untouched.

For graceful capture completion, create the collector stop request and wait for
`collector-finished.json` followed by `stream-finished.json`. Then stop this new
runtime and its added source stream:

```powershell
New-Item .local-discovery/position-stream-20261104-003/stop-collector -ItemType File
Get-Content .local-discovery/position-stream-20261104-003/stream-finished.json
docker exec fleetmavlink20261104-sitl-1 /opt/px4/bin/px4-mavlink stop -u 14622
docker compose --env-file .local-discovery/position-stream-20261104-003/runtime.env -f compose/live-position-path.yml -f compose/position-continuous.yml -p fleetpositionstream20261104-003 --profile worker stop
```

The file read is an observation, not a blocking wait; if the completion file is
absent, acquisition/serving has not completed or has refused. Immediate rollback
uses the final two commands, preserving all volumes and evidence. Never use
volume deletion, prune, old offset resets or source `stop-all` for this scenario.

Attempt 001 refused host S3 access before capture because the shared namespace
had only internal bridges; adding the access bridge repaired loopback publishing.
Attempt 002 captured real data but stopped on a queued Kafka EOF. Both attempts
are retained with their volumes and stopped workers. The older short-run project
was stopped to release the ports; its stored data and original reports remain.

## Verification and files

Ruff lint/formatting and strict mypy passed for the six changed Python files
(the Linux worker is checked with `--platform linux`). Strict SDK-aware mypy
passed on the actual frozen Flink job in its pinned Python 3.12 runtime.
The focused suite passed **16 tests**, including preservation of the original
32-offset guard, explicit continuous budget, units, identity/conflict handling
and existing loopback HTTP/freshness behavior. Actual `start`/`check`, stronger
heartbeat loss and full prefix readback establish the observations above.

Implementation files: `compose/position-continuous.yml`,
`runtime/continuous/position_sql.py`, `runtime/continuous/position_stream.py`,
`scripts/run-position-stream.py`, `runtime/pyflink/mavlink_position_job.py`,
`telemetry/mavlink_position.py`, `tests/test_mavlink_position.py`.
Documentation files: this guide, `docs/adr/0047-continuous-local-position.md`,
`README.md`, `docs/roadmap.md`, `docs/architecture.md`, `docs/data-contracts.md`,
`docs/testing-strategy.md`, `docs/deployment-and-terraform.md`, and the historical
guide's handoff note in `docs/guides/live-position-source-query.md`.

The next useful product change is to expose this SQL-backed state in the shared
source inspection screen. Physical devices, authenticated MAVLink, real clocks,
collector ambiguous-publication recovery, full Flink/broker/host recovery and
production operation remain open. No general source-admission or M6/M7 completion
follows from this local position result.
