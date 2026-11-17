# ADR-0059: Explaining why a value stopped updating

**Status:** Proposed, 2026-11-17. Extends
[ADR-0056](0056-run-health-without-a-monitoring-stack.md); no monitoring
service is added.

## Problem

ADR-0056 states whether each stage is healthy, but an operator who sees a
value stop changing still has to work out which stage stopped: the source,
the replay publisher, the archive or serving. Step 2 of the
[roadmap](../roadmap-history.md#next-steps-after-the-mvp-evidence-runs-2026-11-17)
asks for source mode, last source progress, archive progress and last
query-visible progress side by side, each on a clock ADR-0054 qualifies, and
for distinct explanations of a silent source, a paused or ended replay and
serving that is behind. The F09 publisher had no explicit paused or ended
state with a position, and the fault orchestrator had no serving pause.

## Decision

`runtime/recording/stall.py` is a pure function of two status snapshots a
declared window apart (10 s in `collect` and `stop`, `--window` in `status`).
It reports:

| Stage | Progress | Clock |
| --- | --- | --- |
| Source | replay: publisher state, acknowledged of declared deliveries, native time of the last acknowledged event; live: gateway state and published count, source receipt age | native time; status-file age on the observer clock; receipt age on the SQL clock (ADR-0054) |
| Input | broker end offset, advancing | broker offsets |
| Archive | archived prefix, advancing | status-file age on the observer clock |
| Query | visible facts, advancing, what serving has taken, newest visible native time, age of the last SQL progress write | native time; SQL clock |
| Browser | `unknown` (not measured) | — |

and one explanation, in this order: `completed` (serving's completion
marker, written only when SQL holds every reference fact), `advancing`,
`serving_behind` (serving holds more than 100 archived deliveries back, or its
status is older than 10 s while the archive advances or holds input it has
not taken; growth over a zero window is not measured),
`archive_behind`, `replay_paused`, `replay_ended`, `replay_waiting` (a native
time gap), `source_silent` (live: gateway running and current, connection
stale), else `unknown` (for example missing gateway health).

- **Publisher state.** `producer-status.json` now carries `declared`
  deliveries and `position_native_us` and is rewritten at least every second
  while waiting or paused, so its age measures the publisher. `paused`
  (operator file `pause-publisher`) and `completed` (end of the declared
  deliveries) are explicit states.
- **Where it is shown.** `ops status --window N` prints a *Why* block;
  `ops collect` and `ops stop` store it as `why` in `health.json`. The
  serving worker writes its own view with every progress write to a new
  `source_progress` table, and the dashboard shows the newest row in a
  *Run health — why values stopped updating* panel. A stopped serving worker
  writes nothing: the panel's `written` time then ages, and `ops status`
  explains from outside the profile. Runs created before this decision have
  no `source_progress` table, so that one panel reports an error when they are
  viewed with `ops view`; their other panels are unaffected.
- **Drill.** `runtime/recording/stall_drill.py` declares the detection
  interval and the phases in `criterion.json` before any service starts,
  then runs `ops start`, samples the explanation every 5 s over a 10 s window
  into `why.jsonl`, pauses the publisher and stops serving at declared
  acknowledged-delivery triggers, waits for completion and runs `ops verify`.
  For a live session it pauses the simulator instead.

Unattended alerting stays deferred under ADR-0056: nothing evaluates between
`ops` invocations, and a decision against the ADR-0034 Prometheus path waits
until someone must respond while nobody watches.

## Alternatives

- **Infer pause or end from silence.** Rejected: a gap in the recording and a
  paused publisher look the same from the broker; the state must be explicit.
- **Compute the explanation in Grafana.** The dashboard rules allow no wall
  clock, subqueries or joins in panel SQL, and Grafana sees only ClickHouse,
  which a stopped serving worker no longer updates. The panel shows the
  worker's own view with its write time instead.
- **A continuously running checker.** Deferred with unattended alerting.

## Consequences

The operator sees which stage stopped and the last position of each. The
explanation is as good as its inputs: two snapshots, a 10 s status age limit
and a 100-delivery lag threshold; a stage that writes no status stays
`unknown`. Browser render delay remains unmeasured.

## Drill, 2026-11-17

One run combined this drill with the integrated replay of an admitted file
(ADR-0058), on the maintainer's instruction to use one live run for several
steps and a log not run before: Flight Review `695ad7af…` (firmware
`54f0455f`, 1,223 events, 467 facts), not F09 as the roadmap names.

- `x695-s2-drill-20261117-01` stopped before readiness: the serving worker
  exited with `SinkError` because the run's SQL writer had INSERT on `facts`
  and `progress` only, not on the new `source_progress` table. The grant was
  added (`runtime/continuous/recording_initialize.py`); `ops stop` collected
  the partial run.

- `x695-s2-drill-20261117-02` **passed** its declared criterion (detection
  interval 30 s, 5 s samples over a 10 s window, 45 s pauses):

  | Phase | Trigger | Expected | First seen after | While held | Advancing again after |
  | --- | --- | --- | --- | --- | --- |
  | publisher pause | acknowledged ≥ 250 (paused at 366) | `replay_paused` | 2.4 s | only `replay_paused` (9 samples) | 2.3 s |
  | serving stop | acknowledged ≥ 600 | `serving_behind` | 12.6 s | only `serving_behind`; before detection 2 samples `advancing` (the window still held SQL growth) | 7.4 s |
  | end of file | — | `completed` | 5.0 s after the end-of-file phase began | — | — |

  `ops start` reached readiness with all 13 checks; `ops verify` passed: the
  SQL fact hash set equals the reference (467 facts), zero logical repeats,
  and an archive-only rebuild into a separate database has the same set.
  The publisher reached the end of the file while serving was stopped, so
  `replay_ended` was not sampled from outside; the serving worker's own
  `source_progress` rows show every state in order: `unknown` (6 rows, before
  the publisher's first status), `advancing` (96), `replay_paused` (81, at
  acknowledged 366), `replay_ended` (3), `completed` (1), and no row while it
  was stopped. Through the Grafana datasource (HTTP API, not a rendered
  browser view) the dashboard is titled *ULog 19d3c604*, the new panel returns
  the `completed` row with position 902,310,811 µs, and *Run health* lists 13
  checks at 0 violations. `health.json` of the stop stores `why: completed`;
  every signal is `ok` except `kafka_broker_metrics` (`unknown` by decision).
- The first `ops stop` of that run failed while writing lineage: Git output
  was decoded with the Windows locale codec, which cannot decode every UTF-8
  byte of the working diff, so `git diff` returned nothing. Git output is now
  decoded as UTF-8 in `evidence.py`, `fault_run.py` and `prepare.py`; the
  second `stop` collected a `completed` manifest of 607 files. The failed
  attempt left one incomplete evidence directory beside it.

- `live-s2-silent-20261117-01` (PX4 SITL, a separate run because the live
  source is a separate profile) **passed**: ready with all 14 live checks;
  30 s after readiness the simulator was paused for 45 s while the gateway
  ran. `source_silent` appeared 12.4 s after the pause, every sample while
  held was `source_silent`, and the run was `advancing` again 1.9 s after the
  resume. `ops complete` reached `completed`; `ops verify` passed (capture
  covered without loss, archive equals published, SQL equal to the
  archive-only recomputation, zero logical repeats, statuses in receipt
  order).
- One defect, found in that run and fixed afterwards without a repeat run: the
  drill's first sample compares a snapshot with itself, and with serving 6
  deliveries behind the archive it read `serving_behind`. Growth over a zero
  window is now unmeasured, and serving counts as behind only when it holds
  more than 100 archived deliveries back or its status is older than 10 s
  while the archive holds input it has not taken. Recomputed from the stored
  samples, the new rule keeps all 7 `serving_behind` detections of the replay
  drill (each had a serving status older than 10 s) and removes the live
  false positive; `tests/test_recording_stall.py` covers it.
