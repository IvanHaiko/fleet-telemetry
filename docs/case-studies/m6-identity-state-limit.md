# Continuous identity-state refusal: diagnosis and local repair

## Scope and result

The maintainer authorized diagnosis and a minimal local M6 repair of
`load2gb004`, without another 2 GB run, source resets, data removal or Git
publication. Existing staged, unstaged and untracked work was preserved.
The failed job, its topics, originals, checkpoints and earlier evidence were
not restarted or rewritten. All production containers were already stopped
when inspected. The repair is prepared locally, not deployed.

**Cause:** the corrected v2 source assigned watermarks in eighteen partition
lanes, but then `key_by(vehicle_id)` connected all eighteen lanes to each of
two battery subtasks. Each subtask's watermark was constrained by the slowest
active input. A faster partition could accumulate thousands of seconds of
future measurements relative to that minimum. A 600-second event-time horizon
therefore did not imply 600 retained identities at the workload's one Hz per
vehicle. The 4096 refusal was a correct guard on excessive retained state.

Unequal partition sizes and unequal source durations are normal. In this
fixture, hashing 128 vehicles produced 3--11 vehicles per partition. Reading
similar record counts from those partitions advanced measurement time at very
different rates. CPU throttling could affect scheduling, but is not required
for the reproduced failure. Active backlog is not an idle partition.

## Retained evidence

New private diagnostic evidence is in
`.local-discovery/identity-limit-20261027-001`; the original
`.local-discovery/watermark-20261027-002` remains untouched. Read-only inspection
used stopped-container logs and copied checkpoints 40, 43 and 45. The decoder
records input SHA-256 hashes and checks all 128 keys: stored count equals map
cardinality, expiry-bucket membership equals the retained identity set, and
retained expiry ranges are contiguous at one Hz. It decodes this pinned,
uncompressed heap snapshot only; it is not a general checkpoint reader.

| Checkpoint | Retained IDs | Processed measurements inferred from source ordinals | Already expired IDs | Largest vehicle state | Earliest retained expiry, seconds since 12:00 UTC |
| --- | ---: | ---: | ---: | ---: | ---: |
| 40 | 162177 | 310401 | 148224 | 4080 | 1758 |
| 43 | 163338 | 313610 | 150272 | 4065 | 1774 |
| 45 | 163072 | 323584 | 160512 | 4081 | 1854 |

The checkpoint-45 processed total equals the preserved SQL distinct count,
323584. Every vehicle has already released its first 1254 identities; cleanup
advanced by 96 measurement seconds between checkpoints 40 and 45. This is
neither a monotonically leaking count nor a complete failure to run expiry.

Checkpoint-45 per-partition progress:

| Partition | Vehicles | Source next offset | Latest retained measurement, seconds since 12:00 UTC | Largest vehicle state |
| --- | ---: | ---: | ---: | ---: |
| 0 | 6 | 14331 | 2388 | 1135 |
| 1 | 9 | 18314 | 2034 | 781 |
| 2 | 4 | 18244 | 4560 | 3307 |
| 3 | 6 | 14416 | 2402 | 1149 |
| 4 | 8 | 14852 | 1856 | 603 |
| 5 | 8 | 14989 | 1873 | 620 |
| 6 | 7 | 21820 | 3117 | 1864 |
| 7 | 4 | 18475 | 4618 | 3365 |
| 8 | 8 | 22857 | 2857 | 1604 |
| 9 | 9 | 18506 | 2056 | 803 |
| 10 | 4 | 21340 | 5334 | 4081 |
| 11 | 11 | 24205 | 2200 | 947 |
| 12 | 3 | 14970 | 4989 | 3736 |
| 13 | 7 | 18570 | 2652 | 1399 |
| 14 | 8 | 15381 | 1922 | 669 |
| 15 | 9 | 18565 | 2062 | 809 |
| 16 | 8 | 15222 | 1902 | 649 |
| 17 | 9 | 18527 | 2058 | 805 |

For partition 10's four vehicles, retained timestamps run from second 1254
through 5334 inclusive: `5334 - 1254 + 1 = 4081`. The slowest partition, 4,
reached second 1856. Its configured two-second allowance is consistent with
a downstream watermark near second 1853.999. The first remaining expiry is
1854, still in the future. After fifteen more distinct fast measurements the
count is 4096; the following distinct measurement refuses if the slow frontier
has not advanced. Increasing the cap would only postpone this failure.

This watermark is inferred from checkpoint progress, expiry and the configured
generator; the exact rejected record's watermark and vehicle were not logged
by v2. The retained exceptions establish eleven refusals across ten restores,
not the identity of the first rejected vehicle. New guard-only diagnostics
log run, vehicle, measurement time, watermark, stored and observed counts,
due-ID count and earliest expiry. The scan is bounded to limit + 1 entries;
no event IDs, payloads or vehicle metric labels are added.

### Timer inspection limits

The binary decoder matches expiry buckets to JVM event-time timer records.
At checkpoint 45, 729 future bucket timestamps have no matched timer in this
decoder. The earliest unmatched timestamp is 1767271147000, later than the
first retained expiry by 493 seconds. None was due at the inferred watermark;
these observations cannot explain reaching the current guard. They also do
not prove complete timer registration or checkpoint restoration correctness.
This remains a separate checkpoint-reader/registration uncertainty.

The targeted actual-runtime bundle-128 probe below checks that all 512 IDs
are removed and counts reach zero after timer delivery. It does not resolve
the historical snapshot discrepancy or certify v3 restore. No old checkpoint
was restored into a running job. The copied Prometheus TSDB had no samples in
the failed job interval (its retained block begins after failure), so it cannot
supply a missing historical per-subtask watermark trace.

## Minimal repair and operational implications

Gate now sends validated records to eighteen typed side outputs and checks the
existing publisher recipe `sha256(vehicle_id) % 18` against the Kafka partition.
A mismatched partition produces an invalid fact, rather than creating duplicate
vehicle state in another branch. Each selected partition output is gathered
before timestamp assignment and has a single-lane watermark and keyed battery
operator. Processing results are unioned only after state/timer processing.
An unrelated partition can no longer hold back this branch's identity expiry
or window closure. Identity signatures, 600-second horizon, rounded expiry
buckets, two-second allowance, ten-second windows and the cap 4096 are unchanged.

The plan guard checks eighteen isolated timestamp-to-battery paths and refuses
a merge before state processing. No new service, client or dependency is adopted.
This adds sixteen battery lanes relative to v2 and branch-routing edges; the
production worker/PID/RSS cost under the existing eighteen slots and 4 GiB
TaskManager cap is not measured here. Smaller retained state does not itself
certify a container memory budget. The guard remains necessary for higher
per-vehicle rates, large event-time jumps or watermark stalls within a partition.

The new v3 gate/time/battery UIDs intentionally require fresh processing state;
there is no automatic migration from the mixed-watermark v2 state. Restoring
v2 into v3 with unmatched state discarded would lose dedup/window state and is
not an allowed migration. Input topics, offsets and serving facts were untouched.
Any subsequent replay/deployment requires a separately approved isolated scope,
including output/query isolation. Rollback selects retained v2 source/settings
and its own compatible checkpoint; it does not attach v3 state to v2.

This fixed topology requires stable vehicle partition ownership. It does not
solve arbitrary disorder between multiple vehicles sharing one partition,
partition expansion, reassignment or rescaling. A finished short flight does
not terminally advance an unbounded stream's watermark. It may retain an open
tail until that partition receives later measurement time; the existing idle
policy does not synthesize terminal event time. Native split alignment was
considered but is not available merely by adding an alignment option to the
current post-admission DataStream timestamp operator. Replacing this source or
adding a coordinator is a larger change than keeping partition-local state.

## Targeted checks

All executable tests use the existing pinned Linux Python 3.12.13 / PyFlink
2.2.1 environment. No Kafka, SQL, archive, old checkpoint or cloud service is
connected by the probes. Exact launcher and logs are retained in the new
private scope.

```text
wsl -d Ubuntu -- bash <repo>/.local-discovery/identity-limit-20261027-001/test.sh --disable-warnings
# pytest-006.log: 8 passed, 27 upstream warnings, 76.61 seconds
# The retained launcher now selects the fresh pytest-007 directory.
wsl -d Ubuntu -- bash <repo>/.local-discovery/identity-limit-20261027-001/test.sh --disable-warnings -k 'not real'
# pytest-007.log: 5 passed, 3 deselected, 24.17 seconds after type cleanup
# and the added injected downstream state-merge refusal.
wsl -d Ubuntu -- bash <repo>/.local-discovery/identity-limit-20261027-001/types.sh
# mypy-sdk-passed.log: Success: no issues found in 3 source files
.venv/Scripts/python.exe -m ruff check runtime/pyflink/continuous_job.py runtime/pyflink/continuous_operator.py runtime/pyflink/test_continuous.py
.venv/Scripts/python.exe -m ruff format --check runtime/pyflink/continuous_job.py runtime/pyflink/continuous_operator.py runtime/pyflink/test_continuous.py
```

The new test module establishes:

- Actual cap 4096 refusal with a checkpoint-shaped minimum watermark, no missing
  timer needed, followed by release at exact expiry and renewed admission.
- A 6000-measurement one-Hz trace with duplicates retains at most 603 IDs,
  expires 5397 during the trace and drains identities, buckets and windows.
- Subsecond semantic expiry, rounded bucket delivery, stale timer safety,
  duplicate-before-late classification and conflicting content.
- The same small two-partition actual Flink scenario fails under the old merge
  with test cap 8 and passes with separate branches: peak 8, final count zero,
  24 unique window contributions plus duplicate, conflict and late observations.
- Actual Flink with production bundle size 128 processes 512 unique measurements
  spaced ten seconds apart: peak 189 under test cap 256, final count zero,
  exactly 512 window contributions. EOF flushes this finite probe; continuous
  silence is not claimed to do so.
- Correct/misplaced-partition Gate routing and a real eighteen-branch generated
  execution plan, including an injected parallelism violation. The full Kafka
  graph is not executed.

The first root-config mypy attempt was unsuitable for the untyped SDK; the
repository's existing PyFlink config is used for the successful final SDK-aware
check. Ruff lint/format checks pass. `git diff --check`, local Markdown links,
Python module sizes and checkpoint per-partition offset/ordinal/count checks
also pass. The three real Flink scenarios were not repeated for type-only casts;
the five affected state/gate/plan tests passed again after final cleanup.
No full repository suite, production RSS/cgroup limit test, new checkpoint
restore, broker test, whole-run source/archive/SQL reconciliation, 2 GB rerun,
commit or publication is claimed. Docker inspection accidentally resolved the
unpinned Prometheus tag once while requesting CLI help; subsequent TSDB reading
used the retained exact image digest with `--pull never`, without network or a
running Prometheus service. No project version pin changed.

## Changed files and next task

Executable changes: `runtime/pyflink/continuous_job.py`,
`runtime/pyflink/continuous_operator.py`; new purposeful regression module:
`runtime/pyflink/test_continuous.py`.
Documentation: this record, `m6-watermark-and-2gb.md`, README,
`docs/architecture.md`, `docs/data-contracts.md`, `docs/roadmap.md`,
`docs/testing-strategy.md`, `docs/deployment-and-terraform.md`,
`m6-continuous-runtime.md` and the proposed ADR-0035 follow-up.
Private new artifacts are confined to the new ignored diagnostic directory.

The smallest next task is a separately authorized small eighteen-partition
Kafka/checkpoint-restore run under the existing container budget, with deliberate
unequal partition durations and inspection of the unmatched future timer
records. Large-load, full-path reconciliation and M6 adoption remain open.


## Authorized full-graph follow-up

The maintainer subsequently authorized checking and starting a new run. The
isolated v3 record now establishes actual eighteen-branch
Kafka/source/archive/query reconciliation, TaskManager checkpoint restoration,
duplicates after restore and expiry without EOF. Copied state shrinks from
5172 retained old IDs to exactly 128 new IDs after partition-frontier advances,
with count/map/bucket agreement and matching remaining timers. The small run
fits the unchanged 4 GiB / 4096 PID bounds without OOM/PID-limit events.
The new large `load2gb005` has started in a separate cluster with new volumes;
full large-run reconciliation is still pending. This follow-up does not resolve
the old v2 snapshot decoder discrepancy or change the failed load's ledger.


## User-requested stop and optimization

The maintainer subsequently stopped `load2gb005` and requested removal of the
Battery bottleneck. The stop and managed-state optimization record
supersedes the active-run observations above: the job is canceled, all telemetry
services/workers are stopped, and data/checkpoints/cursors remain retained.
No final full-path reconciliation is claimed. V4 prepares one managed value per
vehicle under the same identity/time/4096 rules; its new state layout is covered
by [ADR-0036](../adr/0036-managed-vehicle-state.md). It is not deployed or attached
to the old v3 checkpoint, and no new large run has started.
