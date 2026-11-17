# ADR-0056: Run health and data quality without a monitoring stack

**Status:** Proposed, 2026-11-16. Implemented and checked on the stored
complete runs of step 5, on short debug runs and on one complete F09 run
under a criterion the maintainer approved; that run failed its declared disk
condition and passed every other one ([final run](#final-complete-flight-run-2026-11-17)).
The five-minute live final session failed two conditions on defects of the
signal and the criterion, not of the data ([live session](#final-live-session-2026-11-17));
both are fixed and checked on a short live debug session, without a rerun.

## Problem

Three MVP criteria of the [single-machine recording profile](0052-single-machine-recording-profile.md)
were partial after [ADR-0055](0055-recording-operations-and-restoration.md)
(roadmap, *Criteria status, 2026-11-16*):

- **dashboard:** full-size browser rendering was never checked, and the
  datasource check was a manual signed-in step;
- **monitoring:** `ops status` showed source admission and rejections,
  duplicate and late dispositions, archive coverage and lag as alerting
  signals, broker metrics and resource and disk budgets as `unknown`;
- **limits:** memory and disk under load and the capture-to-browser latency
  were not measured.

The question is how to close them for one run on one computer without adding
services, and without turning signals that were never measured into zeros.

## Decision

Compute every missing signal from what the profile's components already
write or answer, give it a declared threshold and a state, and show it in two
places: `ops status` (and the evidence that `collect` and `stop` save) and
one *Run health* panel on each dashboard.

| Signal | Source that already exists | Threshold → state |
| --- | --- | --- |
| `source_admission` | F09: prepared battery run manifest, bundle manifest and context; live: gateway status | F09: source records = admitted + rejected, every rejection has a reason code → `ok`, else `fail`. Live: refusal → `fail`; lost packets or sequence gaps > 0 → `warn` |
| `processing_dispositions` | the association operator's Flink counters (`accepted`, `duplicate`, `late`, `gps`/`position`, `rejected`) through the REST API | rejected > 0 → `fail`; F09 complete with duplicates ≠ 2 declared repeats → `warn` |
| `sql_repeats` | SQL physical rows and distinct inputs | physical/logical > 2 → `warn`; identity conflicts are a quality check |
| `kafka_input_end` | broker end offset | equals the declared deliveries (F09) or the gateway's final count (live) at completion, else `fail`; while running, F09 end ≤ declared, live end ≥ the count the current gateway epoch acknowledged |
| `archive_coverage`, `serving_coverage` | archive and serving progress files against the broker end | complete: lag 0, else `fail`. Running: lag > 1,000 deliveries or status older than 10 s → `warn`; status older than 60 s → `fail` |
| `checkpoints` | Flink REST | failed > 1 (the submission trigger of ADR-0052) → `warn`; latest completed older than 30 s → `fail` |
| `job_restarts` | Flink REST `numRestarts` | > 0 → `warn`; no running job while Flink answers → `fail` |
| `kafka_broker` | healthcheck, topic IDs, `kafka-topics --unavailable-partitions`, `kafka-log-dirs` | unhealthy, changed IDs or any unavailable partition → `fail` |
| `kafka_group_lag` | `kafka-consumer-groups --describe` for the run's groups | lag > 1,000 → `warn` |
| `kafka_broker_metrics` | none | always `unknown`: request rates and other broker metrics need JMX and an exporter |
| `memory`, `cpu` | `docker stats --no-stream`, `docker inspect` limits | memory ≥ 80 % of the container limit → `warn`, ≥ 95 % → `fail`; CPU ≥ 95 % of the container's CPU budget → `warn` |
| `memory_budget` | `docker inspect`, `docker info` | sum of running limits > engine memory → `fail` |
| `disk_free` | `df` on the Docker disk and free space on the host disk, whichever is smaller | < 2 complete runs (1,024 MiB) → `warn`, < 1 run → `fail` |
| `quality.*` | one SQL scan of the run's `points` view | each check: 0 violations → `ok`, else `fail`; no facts → `unknown` |

The data-quality checks count violations of rules the
[data contracts](../data-contracts.md) and the processing contracts already
declare. No bound is derived from the stored data:

| Check | Rule | F09 | Live |
| --- | --- | --- | --- |
| `identity_conflicts` | equal identity with different content is a conflict | ✓ | ✓ |
| `time_order` | native time does not decrease along input offsets | ✓ | ✓ |
| `latitude_range`, `longitude_range` | WGS 84 bounds | ✓ | ✓ |
| `null_island` | unknown position is NULL, never (0, 0) | ✓ | ✓ |
| `position_pair` | latitude and longitude are both known or both unknown | ✓ | |
| `voltage_positive` / `voltage_nonnegative` | ULog policy: positive volts; canonical: nonnegative | ✓ | ✓ |
| `current_nonnegative` | ULog policy: negative current other than the `-1` sentinel is rejected | ✓ | |
| `remaining_fraction_range` | `[0, 1]`, never a percentage | ✓ | ✓ |
| `battery_values_iff_*`, `state_values_iff_*` | values exist exactly when the association is matched (F09) or receipt-ordered (live); unknown is NULL | ✓ | ✓ |
| `association_age` / `receipt_age` | matched age ≤ 1 s (F09 `max_age_us`); receipt-ordered ≤ 3 s and stale > 3 s (live `max_receipt_age_ms`); unknown ages NULL | ✓ | ✓ |
| `status_domain` | association statuses inside the declared sets | ✓ | ✓ |

The checks are one aggregate over `points`. The panel and `ops` run the same
generated SQL (`runtime/continuous/recording_health.py`; a test compares the
dashboard templates with it), within the Grafana identity's read budget of
50,000 rows. Coordinate checks return counts only.

Resources are sampled into `resources.jsonl` in the run directory every
readiness window and every 15 s while `ops complete` waits: memory (bytes and
percentage of the limit), CPU against the container's budget, the Docker and
host disks, and every profile volume's size.

The final evidence runs use `runtime/recording/mvp_run.py`: `declare` writes
a criterion draft, `run` requires the approved draft, samples resources from
a separate thread every 15 s, saves the signals at a mid-run trigger and after
completion and runs `ops verify`; after the signed-in dashboard check and
`ops stop`, `evaluate` judges each condition into `result.json`.

## Debug evidence, 2026-11-16

| Run | Scenario | Result |
| --- | --- | --- |
| `f09-s6-dbg-20261116-01` | 60 s F09 interval through `ops` | every signal measured; `verify` passed; dispositions `accepted 1017, duplicate 2, late 2, gps 538`; the new run's datasource worked without `ops view` |
| `live-s6-dbg-20261116-01` | live session, 72 s of publishing, simulator paused about 10 s | browser showed *observed*, then *stale* (receipt age 6.2 s) with current values hidden; `verify` passed |
| `f09-s6-dbg-20261116-02` | the orchestrator on the 60 s interval | every condition passed; largest gap between resource samples 27.1 s, too close to the 30 s limit |
| `f09-s6-dbg-20261116-03` | the same after moving sampling to a thread | every condition passed; largest gap 15.0 s; SQL visibility ≤ 2.0 s; computed browser bound 9.2 s |

PyFlink registers an operator counter at its first increment, so
`rejected` (and `duplicate` before the first repeat) is absent rather than
zero. The signal shows it as *not reported* and decides on rejections from
`job_restarts`, because the operator fails the job on any rejection.

## Alternatives

**Prometheus, Alertmanager and exporters.** [ADR-0034](0034-local-observability-stack.md)
accepted a bounded Prometheus collection for the earlier continuous profile,
using Flink's bundled reporter (through an eight-line configuration wrapper)
and ClickHouse's native endpoint. Bringing it to the recording profile would
add a Prometheus container and that wrapper; Kafka broker metrics would still
need a JMX exporter, container memory and disk would need cAdvisor or a
Docker socket, and alerting would need Alertmanager. The profile already sits
at about 10.5 GiB of container limits on a 12 GiB engine, and each service
brings configuration, retention, credentials and a second place where a
signal can disagree with `ops`. These pay off with continuous time series,
alerting while nobody looks, several runs or hosts, and retention beyond one
run; none of those is a requirement of the single-machine MVP, and the
maintainer chose not to add services in this step.

**Great Expectations or Soda.** Both would express the same checks as
configuration, but need a Python environment with many dependencies or a
separate service, and run outside the SQL path that Grafana already reads.
Twelve to thirteen SQL rules held next to their contract references are
smaller than either framework.

**Return to a monitoring stack** when one of these holds: more than one run,
vehicle or host is monitored at once; someone must be alerted while no
operator runs `ops status`; signals must be kept as time series across runs;
or broker internals (request latency, ISR changes, log flush) become an
acceptance criterion. Then Prometheus with the Kafka JMX exporter is the
recognised default, and the thresholds above become its alert rules. Return
to a data-quality framework when checks must be shared with other pipelines
or managed by people who do not edit SQL.

## Found while checking the dashboards (2026-11-16)

Full-size rendering of the stored step 5 runs found three defects that the
sequential SQL checks of ADR-0052 and ADR-0054 could not see:

1. **Datasource refused for every run after the first.** The shared
   `recording_grafana` identity was created with `CREATE USER IF NOT EXISTS`,
   so it kept the first run's password; each later run's datasource carries
   its own. `recording_initialize.grafana_identity` now re-keys it at every
   initialization, and `ops view` re-keys it for a stored run only when
   ClickHouse refuses.
2. **Panels failed on every refresh.** ClickHouse allowed 4 simultaneous
   queries; a refresh sends all panel queries at once (15 on the F09 view), so
   4 to 9 panels showed *No data* with `TOO_MANY_SIMULTANEOUS_QUERIES`. A
   recording-only override (`runtime/recording/clickhouse-concurrency.xml`)
   raises the limit to 24; memory stays bounded by the server limit and each
   reader's 256 MiB.
3. **Live states never showed.** The live view's text stat panels
   (connection, gateway status, association statuses) selected numeric fields
   only, so `observed`, `stale` and `unknown` all displayed as *Unknown*.

`ops view --run-id <run>` serves a stored run's dashboard from storage, SQL
and Grafana alone, with the current templates rendered for that run's
database; nothing is copied. The evidence is in
`.local-discovery/dashboard-check-20261116-01/`.

## Final complete-flight run, 2026-11-17

Run `f09-s6-full-20261116-01` (the ID keeps the date of its approved draft):
the whole flight, 39,760 deliveries, no faults, through
`runtime/recording/mvp_run.py`. Ready 153 s after `start`; serving complete at
2,490 s; verified at 2,587 s; stopped at 2,929 s.

| Condition | Result |
| --- | --- |
| readiness | passed |
| health at 20,045 deliveries and after completion | passed: every signal `ok`, broker metrics `unknown`; dispositions `accepted 39758, duplicate 2, late 2, gps 21054`; checkpoints 241 completed, 1 failed (the submission trigger); 0 restarts; 13 quality checks at 0 violations |
| `ops verify` | passed: hash set equals the reference, 0 logical repeats, archive-only rebuild equal |
| resource samples | passed: 157 samples, largest gap 15.0 s; no container reached 95 % of its limit |
| SQL visibility | passed: 21,054 facts, maximum 2.0 s (the sample interval) |
| disk | **failed**: the profile volumes grew 639.7 MB against the declared 512 MiB |
| dashboard, signed in | passed: datasource working; 5 rounds of 16 simultaneous queries without error, p50 1.09 s, maximum 2.10 s; every panel rendered; *Run health* 13 × `ok`; the map drew 2,350 route points, one per native second, plus the last position |
| stop | passed: completed manifest with `health.json`; every volume kept |

Peak memory against the compose limits: serving worker 442 of 512 MiB
(86.4 %), Kafka 740 of 1,024 MiB (72.3 %), Grafana 501 of 768 MiB (65.3 %),
ClickHouse 1,165 of 2,048 MiB (56.9 %), publisher 230 of 512 MiB (45.1 %),
archive 319 of 768 MiB (41.6 %), archive worker 183 of 512 MiB (35.9 %),
TaskManager 889 of 3,072 MiB (29.0 %), JobManager 414 of 1,536 MiB (27.0 %).
Kafka and ClickHouse reached about one full CPU each at their peak. The serving
worker is the only container above the 80 % warning share and its memory
grows with the archived prefix; a longer source than this flight needs a
larger limit or a serving change.

**Why the disk condition failed.** `serving-data` grew 457.8 MB; Kafka 80 MB,
evidence 61 MB, archive 23 MB and checkpoints 18 MB matched the earlier
footprint. Read afterwards with only storage and ClickHouse started, the
`system` database held 496 MB: `processors_profile_log` 183 MB, `query_log`
162 MB, `trace_log` 78 MB, `part_log` 33 MB and metric logs 39 MB, against
47.9 MB for the run's database and its rebuild. ClickHouse writes these logs
for every query and the profile set no retention, so they grow with time,
about 650 MB per hour of operation, not with the run. The declared budget was
derived from the run's own objects and did not include them. The
run-attributable growth was about 230 MB and the run directory on the host
96.8 MB, both inside the budget. Under the condition as declared the run
failed; it is not relabelled.

**Decision on the system logs (maintainer, 2026-11-17).** Nothing in the
project reads them, so the recording profile now removes every system log that
writes during normal operation (`runtime/recording/clickhouse-system-logs.xml`)
and keeps only `query_log`, bounded to 3 days, and `crash_log`. Checked on
ClickHouse alone: 40 health queries added 0 rows to the removed logs; the new
`query_log` carries the TTL and receives rows. ClickHouse renamed the old table
to `query_log_0`; existing log data, about 496 MB, stays until the maintainer
removes it.

The capture-to-browser time is computed, not measured: SQL visibility 2.0 s,
plus one 2 s sample, plus the 5 s refresh, plus the slowest of 16 simultaneous
panel queries, 2.1 s, about 11.1 s.

## Final live session, 2026-11-17

Run `live-s6-full-20261116-01`: one PX4 SITL session, 300 s after readiness,
no faults, with the system-log override of the same day in place. Publishing
started 81 s after `start`; serving complete 341 s later; 2,310 deliveries,
1,650 positions.

| Condition | Result |
| --- | --- |
| readiness | passed |
| health at 150 s and after completion | **failed**: at mid-run `kafka_input_end` was `unknown`; after completion every signal was within the allowed states (memory `warn`) |
| `ops verify` | passed: every published event captured, no sequence gap, SQL equals the archive-only recomputation, 0 logical repeats, statuses match receipt order |
| resource samples | **failed**: 21 of 22 samples complete; the last one listed the gateway at 0 B while it shut down |
| SQL visibility | passed: maximum 1.0 s (the sample interval) |
| disk | passed: volumes grew 86.3 MB; run directory 20.1 MB |
| dashboard, signed in | passed: *observed* during the session (receipt age 1.1 s); afterwards 5 rounds of 14 simultaneous queries without error, maximum 0.3 s; every panel rendered; *Run health* 11 × `ok` |
| stop | passed |

**Causes.** (1) For a live session `kafka_input_end` compares the broker end
with the gateway's final published count, which exists only after completion,
so the signal is `unknown` while any live session runs. At mid-run the gateway
status reported 1,275 published in its single epoch, without loss or gaps,
against a broker end of 1,277: consistent, but not the declared check. The
orchestrator's live variant had not been exercised on a debug session, which
is how the defect reached the final run. (2) `docker stats` reports 0 B for a
container that is exiting; the condition counted the gateway that `ops
complete` was stopping. Both are recorded as failed and not relabelled.

**Fixes, same day.** (1) While a live session runs, `kafka_input_end` checks
that the broker end is at least the count the gateway's current epoch reports
as acknowledged; that count is per epoch and written every 0.5 s after the
acknowledgement, so equality is required only at completion. (2) `ops complete`
logs `completing` first; after it, a container sampled at 0 B is exiting and
is not counted as a missing value. A live debug session
(`live-s6-dbg-20261117-01`, about 90 s of publishing) showed `kafka_input_end`
`ok` while running (429 at the broker, 427 acknowledged) and at completion
(589 of 589), every other signal `ok` except broker metrics; it also showed
the serving worker, not only the gateway, sampled at 0 B while exiting, which
is why the rule covers any container rather than a named list. Neither final
run was repeated.

**Finding.** Grafana's memory rose from 66 % to 93.9 % of its 768 MiB limit
in these minutes, with the live dashboard refreshing every 5 s and the
signed-in check running; on the complete F09 run it peaked at 65 %. Whether
it levels off was not measured.

## Consequences

- `ops status`, `collect` and `stop` take about 25 s instead of about 10 s:
  the health probe, `docker stats`, the disk probe and three Kafka tools run
  each time. Readiness polling does not run them.
- The Flink counters restart at zero with every job attempt; after a restore
  they count from the restored checkpoint, so the duplicate expectation is a
  `warn`, not a `fail`.
- Kafka broker metrics stay `unknown` by decision; the status screen says so.
- Signals are computed when `ops` runs; nothing alerts between two runs of it.
- ClickHouse keeps no system logs except a 3-day `query_log` and crash
  reports; diagnosing a slow query older than 3 days, or a merge problem, needs
  the logs re-enabled first.
- Rollback: the signals are reads. Removing them restores ADR-0055 behaviour;
  the ClickHouse concurrency and system-log overrides and the dashboard
  changes are independent and can be reverted separately.
