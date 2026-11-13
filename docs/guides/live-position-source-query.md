# Live PX4 position from source to SQL

The 2026-11-04 local demonstration takes **new packets from the running PX4
SITL** through Kafka and Flink, independently archives the Kafka input and
original selected MAVLink packets to S3, and reconciles the output in SQL.
[ADR-0046](../adr/0046-live-position-source-query-slice.md) owns this bounded profile.
The existing [direct live monitor](live-px4-mavlink.md) stays running separately.

**Subsequent handoff:** the [continuous position session](continuous-position.md)
now owns the same SQL/S3/Flink loopback ports. This short-run project's services
were stopped to release those ports, with its volumes, frozen source and all
reports retained. The availability statements below describe this run's original
completion, before that handoff. Do not start both integration projects on the
same ports simultaneously.

## Demonstrated result

Evidence is retained under `.local-discovery/live-position-path-20261104-003/`;
`verified-report.json` is the completed reconciliation, with `sources.json`,
producer acknowledgements, raw packets, input/output observations, archive plan,
receipt/cursor, Flink result, frozen source manifest and verification source.
Credentials and precise source data stay local and ignored by Git.

| Boundary | Observed result |
| --- | --- |
| Original source | 16 distinct fix-qualified GLOBAL_POSITION_INT packets; complete selected position and GPS_RAW_INT packet bytes retained before Kafka publication |
| Kafka input | 18 acknowledged deliveries, exact offsets `[0,18)`; the final two repeat the first two byte for byte |
| Flink | First output observed while capture was incomplete; job FINISHED in 16,304 ms; all 18 source coordinates and complete facts reconciled |
| S3 archive | Four immutable objects: original selected packet evidence, stream plan, 18-observation segment and receipt; separate reader verifies every byte |
| Initial SQL | 18 physical rows, 18 source deliveries, 16 unique measurements; complete typed columns and original event/fact JSON match |
| Repeated SQL batch | 36 physical rows, still 18 source deliveries and 16 measurements in the deduplicated position view |

Selected native boot timestamps run from 2,409,132 to 2,418,132 ms. They describe
a nine-second source-clock interval, not proven UTC or physical sample age.
The job duration includes startup and finite processing; it is not a per-event
latency distribution. The simulator remained disarmed; no flight command ran.

## Contract and calculation

`px4-live-position-input-v1` is separate from canonical Battery. It contains
`event_id`, `source_kind=px4-sitl`, declared `source_boot_session`, `system_id`,
`component_id`, `source_time_kind=boot_timestamp_clock_unverified`, and `native`:
`time_boot_ms`, `lat`, `lon`, `alt`, `relative_alt`, `vx`, `vy`, `vz`.
Integers have their MAVLink bounds; booleans and changed profile/identity refuse.
Only position packets with a recently received GPS fix >= 3 enter this slice;
the existing three-second receipt policy qualifies the fix, not physical clock
synchronization. Full original packet bytes retain other fields such as heading,
but this version normalizes only the selected quantities.

Identity preserves the direct monitor's recipe:

```text
sha256("px4-mavlink-position-v1:<boot-session>:<system>:<component>:GLOBAL_POSITION_INT:<native-boot-ms>")
```

The result is prefixed `sha256:`. Receiver epoch, arrival time, Kafka coordinate
and replay/batch identity are absent from measurement identity. Equal identity
with changed native content refuses; repeated identical events count once.
The boot session is an operator assertion and must change after a simulator boot.

Flink validates the exact input profile/key and converts latitude/longitude from
1e-7 degrees, altitudes from millimetres, and velocities from centimetres/second.
Ground speed is `hypot(vx,vy)/100`; down speed is `vz/100` (positive down).
`px4-live-position-fact-v1` retains the full event, normalized Float64 payload,
input topic/partition/offset, and SHA-256 of exact input key and value bytes.
There is no invented measurement UTC or timestamp-less battery identity.

The bounded streaming Kafka source waits for future offsets through 18. The
Kafka sink is at least once. FINISHED alone is insufficient: the native reader
independently reads input/output and every source-coordinate fact must match.
S3 uses the existing `kafka-observation-v1` codec and SegmentedArchive protocol;
its Battery-specific measurement link remains NULL. The archive plan binds the
original selected packet evidence and processing-source manifest by hash.

## Run and inspect

Prerequisites are the running source from `live-px4-mavlink.md`, its unchanged
declared boot session, existing pinned images and retained dependency artifacts.
The script intentionally names this local profile and refuses an existing
evidence directory. It installs nothing. Free loopback ports 28081, 28133 and
28333 and unused subnets `10.254.248.0/28`, `.16/28`, `.32/28` are required.
Stop an earlier integration project before starting another with these ports.

For a fresh attempt (004 is an example, not already-run evidence):

```powershell
.venv/Scripts/python.exe scripts/run-live-position-path.py prepare --evidence .local-discovery/live-position-path-20261104-004
.venv/Scripts/python.exe scripts/run-live-position-path.py capture --evidence .local-discovery/live-position-path-20261104-004
.venv/Scripts/python.exe scripts/run-live-position-path.py verify --evidence .local-discovery/live-position-path-20261104-004
```

`prepare` exports source without old data/secrets and creates fresh credentials.
`capture` initializes two one-partition topics, submits Flink, captures 16 new
measurements and publishes two repeats. A temporary custom MAVLink instance uses
local source port 14621 and UDP target 14561 inside the existing source network;
it is stopped afterwards. The original 14620 direct-monitor stream is untouched.
The native worker shares Kafka's network namespace, preserving the existing
reader's exact `127.0.0.1:19092` admission boundary. Host Kafka/UDP are unpublished.

`verify` reconciles complete content, archives it, and creates the scoped SQL
table/view and a fresh SELECT-only reader on the new ClickHouse instance.
Verification can resume the completed archive and SQL batches without deleting
or overwriting evidence. Partial/unknown SQL batches or conflicting contents
refuse; it is not a general automatic recovery procedure for partial captures.
Existing `flight_reader` and historical tables receive no grants or changes.

At `127.0.0.1:28133`, use the new `position_reader` credential from the local
`credentials.json`; do not paste it into a URL, shell history or documentation.
Useful queries are:

```sql
SELECT count(), uniqExact(input_offset), uniqExact(event_id)
FROM live_positions.facts;

SELECT source_time_ms, latitude_deg, longitude_deg, altitude_msl_m,
       relative_altitude_m, ground_speed_m_s, down_speed_m_s
FROM live_positions.positions ORDER BY source_time_ms;
```

The position view is correct for this reconciled, serialized finite scope. An
arbitrary competing writer is not admitted or hidden by a last-write-wins rule.
This table is a retained interval; the separate direct monitor is the current
live state. No SQL freshness/heartbeat state is inferred from retained rows.

## Checks and operational boundaries

Focused verification passed:

- Ruff lint and formatting on the six changed Python files.
- Strict root mypy on the helper, live model, native worker, driver and tests.
- Strict SDK-aware mypy on the actual frozen job in the existing Flink runtime
  (Python 3.12, `--follow-untyped-imports`, explicit package bases).
- `pytest tests/test_mavlink_position.py tests/test_mavlink_live.py tests/test_link_watch.py tests/test_live_state.py tests/test_position_live.py -q -p no:cacheprovider`:
  **16 passed**, including loopback HTTP regressions.
- Actual `prepare`, `capture`, `verify` for attempt 003, complete raw-packet,
  Kafka, Flink, independent S3 reader and SQL reader reconciliation. Re-running
  `verify` rechecks retained data without adding SQL rows.

Attempt 001 refused Compose interpolation before starting services. Attempt 002
created empty topics but hit Kafka's asynchronous topic-metadata visibility;
the worker now retries only UNKNOWN_TOPIC_OR_PARTITION within 15 seconds.
Its new services were stopped/removed with volumes retained. Attempt 003's
first SQL read refused unqualified table names; explicit database-qualified
queries and non-destructive verification resumed the same retained evidence.
No failed attempt is claimed successful and no old storage/offset was reset.

The retained post-run sample was Kafka 406.6 MiB, JobManager 569.4 MiB,
TaskManager 513 MiB, SeaweedFS 31.55 MiB and ClickHouse 212.6 MiB. These are
snapshots, not peaks or capacity measurements. The five service containers
reported zero restarts and no OOM. Two checkpoints completed; no restore was
tested in this position run. Configured limits total 7.75 GiB plus the transient 256 MiB
worker; existing live/history services have their own limits. Access bridges
permit egress, so internal networks are not a full isolation guarantee.

The completed run's Kafka/JobManager/TaskManager are stopped, with their
containers, checkpoints and volumes retained. SQL/archive remain available for
inspection. A post-stop SQL reader check still returns 36 physical rows, 18
source deliveries and 16 measurements; the existing direct monitor reports a
healthy gateway and the same boot session. Rollback stops the complete
new project, retaining its volumes, source export, raw packets and reports:

```powershell
docker compose --env-file .local-discovery/live-position-path-20261104-003/runtime.env -f compose/live-position-path.yml -p fleetliveposition20261104-003 stop
```

Do not use volume deletion, prune or offset resets. This is one unsigned SITL,
one partition and 16 selected positions. Physical source/clock admission,
continuous archive/SQL updates, integrated recovery after an interruption,
archive-only rematerialization, authenticated device transport and production
capacity remain open. The next useful change is a bounded continuous position
worker with source silence/recovery visible through the same SQL result.

## Changed files

Implementation: `compose/live-position-path.yml`,
`telemetry/mavlink_position.py`, `telemetry/mavlink_live.py`,
`runtime/continuous/live_position_worker.py`,
`runtime/pyflink/mavlink_position_job.py`, `scripts/run-live-position-path.py`,
`tests/test_mavlink_position.py`.
Documentation: this guide, `docs/adr/0046-live-position-source-query-slice.md`,
`README.md`, `docs/roadmap.md`, `docs/architecture.md`, `docs/data-contracts.md`,
`docs/testing-strategy.md`, `docs/deployment-and-terraform.md`.
