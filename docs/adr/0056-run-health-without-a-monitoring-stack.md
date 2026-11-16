# ADR-0056: Run health and data quality without a monitoring stack

**Status:** Proposed, 2026-11-16. Implemented and checked on the stored
complete runs of step 5 and on short debug runs; the final complete-flight
run waits for the maintainer's criterion.

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
| `kafka_input_end` | broker end offset | equals the declared deliveries at completion, else `fail` |
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

## Consequences

- `ops status`, `collect` and `stop` take about 25 s instead of about 10 s:
  the health probe, `docker stats`, the disk probe and three Kafka tools run
  each time. Readiness polling does not run them.
- The Flink counters restart at zero with every job attempt; after a restore
  they count from the restored checkpoint, so the duplicate expectation is a
  `warn`, not a `fail`.
- Kafka broker metrics stay `unknown` by decision; the status screen says so.
- Signals are computed when `ops` runs; nothing alerts between two runs of it.
- Rollback: the signals are reads. Removing them restores ADR-0055 behaviour;
  the ClickHouse concurrency override and the dashboard changes are
  independent and can be reverted separately.
