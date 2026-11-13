# M6 transport/serving replay baseline

## Declared profile before execution

This first load profile measures synthetic normalization, Kafka admission/readback
and the existing ClickHouse event schema/unique-read semantics. It deliberately
does not run Flink or the archive, change their finite-input limits or claim
complete platform capacity. No new dependency, service or contract is adopted.

Use a fresh Compose project with only the existing pinned Kafka and ClickHouse
services. The shared Docker budget is 16,501,075,968 bytes (about 15.37 GiB),
22 logical CPUs; caps remain Kafka 1,536 MiB / two CPUs and ClickHouse 2 GiB /
one CPU. Other services stay stopped. Require at least 4 GiB free workspace /
Docker storage before launch, stop below 2 GiB free, at 90% container memory for
three consecutive samples, any OOM, sampler failure, reconciliation failure or
the parent deadline. Do not delete data, reset offsets or start historical profiles.

Workload: generator `m6-replay-load-v1`, seed 0, one synthetic vehicle, one Kafka
partition, 128 distinct native records with a fixed January 2026 source clock.
Voltage is always valid; four equal payload classes have both optional values,
missing current, missing remaining fraction, or both missing. Zero invalid/late
inputs; uniform identity frequency and no vehicle skew. Preserve the original
source checksum and normalization recipe. Delivery timestamps do not define IDs.

One 1,024-observation warm-up is excluded. Three measured repetitions each
contain 8,192 observations, 128 unique measurements and 98.4375% duplicate
deliveries. The driver processes serial batches of 128 without an artificial
rate cap: normalize/enqueue, wait for broker ACKs, consume exact bytes, append
typed events and execute conflict-guarded complete unique reads. This is a
bounded replay workload with intentional duplicate pressure, not a diverse
fleet or saturation workload. Parent deadline: 600 seconds after preparation.

Use one parent monotonic clock from immediately before normalization to the
first successful guarded complete unique read. Record one first-visible sample
per distinct event (128 per repetition); batch samples are correlated and
include intrusive query/validation overhead. Report nearest-rank p50/p95/p99
with raw samples, admission/ACK/unique-visible counts and explicit time intervals.
Repeated already-visible deliveries do not create extra unique latency samples.
Historical source age is a separate wall-clock observation. Resource sampling
must disclose interval and distinguish cgroup memory peaks from sampled CPU/disk.

## Observed results, 2026-10-27

The bounded component baseline passes three measured repetitions on fresh
`fleet-m3-final-014`, with isolated run scopes `m6-load-015-001` through `003`.
Warm-up is separate (`000`, 1,024 observations, 0.974 seconds). The measured
intervals total **20.533 seconds**, with 24,576 attempted/acknowledged deliveries
and 25,593,216 serialized value bytes. Every consumed key/value, topic, partition
and offset matches; retained source bounds are `[0,8192)` for each measured topic.
Every batch passes conflict-guarded complete semantic/typed SQL reconciliation
before any query result is accepted. Stable 128-event identity sets agree across
all three scopes. Physical retained event rows include the warm-up and repeated
deliveries; each scope has exactly 128 unique query-visible measurements.

| Repetition | Seconds | Attempted obs/s | ACK obs/s | Unique-visible events/s | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5.826 | 1,406.1 | 1,431.1 | 21.97 | 45.9 | 51.1 | 51.7 |
| 2 | 6.644 | 1,232.9 | 1,253.4 | 19.26 | 61.2 | 66.2 | 66.7 |
| 3 | 8.062 | 1,016.1 | 1,031.9 | 15.88 | 573.4 | 579.1 | 579.7 |

Attempted throughput uses first admission through final verified unique read.
ACK throughput uses first admission through last ACK, including earlier serial
read/write/query work; it is not isolated producer capacity. Unique-visible
throughput divides 128 by the entire measured repetition, not by the number of
duplicate deliveries. Final drain after last ACK is 102 / 109 / 124 ms.

Each repetition creates new producer/consumer clients and a new topic/scope.
The warm-up therefore warms services/storage, not every later client connection.
Visibility samples cover the first 128 identities in the first batch; all later
deliveries are repeats of already-visible identities. They are **128 correlated
first-burst samples per repetition**, not 8,192 independent steady-stream samples.
No latency polling is used: timestamps bracket a synchronous full query/validation
after each batch. This gives an observed upper bound at that query, with query
and validation overhead included. Raw precision is not an accuracy claim.

The slower third repetition is retained. Client initialization, accumulating
append-only table state and scheduler/IO effects are not isolated by this
experiment; no causal explanation or steady-state capacity claim is made.
Merges remain stopped, as in the existing retry-correctness profile. The benchmark
query's explicit 32,768-row / 256 MiB / five-second limits are local to this
component profile; existing M4 query and Flink finite-input limits are unchanged.

Historical source age is about 25,787,125–25,787,141 seconds from the fixed
2026-01-01 12:00 UTC anchor; source span is 127 ms. It is not processing latency.
Parent `perf_counter` supplies all admission/visibility intervals within the same
Linux process. Windows resource-sampler clocks are not subtracted from that clock.

Environment inventory: VM-visible Intel Core Ultra 7 155H, 22 logical CPUs,
Docker Engine 29.7.2, Ubuntu WSL kernel `6.6.87.2-microsoft-standard-WSL2`,
Docker Desktop virtualized Linux storage. Windows CIM hardware inventory was
unavailable in the restricted session; physical host RAM and the backing drive's
medium/performance are not measured. No cross-machine hardware comparison is made.

### Resource evidence and pressure boundaries

Twelve joined cgroup/disk samples span startup/warm-up/measured work at actual
intervals **2.392–2.470 seconds**, not exactly two seconds. Maximum sampled CPU
uses cgroup usage deltas divided by the host sampler interval (100% = one CPU).

| Container | Cgroup memory peak MiB | Max sampled CPU, one CPU % | Max sampled retained disk MiB | Disk growth MiB |
| --- | ---: | ---: | ---: | ---: |
| Kafka | 440.50 | 93.80 | 26.96 | 26.75 |
| ClickHouse | 184.68 | 84.22 | 18.46 | 16.65 |

Cgroup memory peaks include service startup and warm-up; they are not per-run
peaks. CPU/disk are sparse sampled maxima, not exact instantaneous peaks. Disk
includes retained failed-attempt data in the same fresh project. Python driver,
Windows host and Docker VM overhead/peaks are not measured here; do not add these
container peaks and call the sum total Docker usage.

No sampler error, pressure refusal or OOM occurs in the successful run. Workspace
free-space and container-memory pressure are enforced by the parent. Docker's
filesystem free space is checked again after the run (933,677,364 KiB available);
the earlier monitoring admission had also observed ample Docker space. It was
not separately polled during this run, so continuous Docker-disk pressure
enforcement remains a limitation rather than a claimed checked invariant.
Recovery time is unmeasured: this baseline injects no fault and supplies only
normal final drain, not recovery-versus-catch-up evidence.

### Retained failures and repairs

The first measured attempt refuses a partition EOF notification as a mismatched
record. The benchmark consumer now explicitly disables optional EOF events;
normal records still require exact bytes and coordinates, and offset reset / auto
commit remain disabled. This does not change the maintained recovery consumer.
The next attempt refuses before SQL bootstrap is ready; it is retained with no
successful benchmark claim. The successful parent waits for an actual SQL query
before creating the fresh schema and separate INSERT/SELECT users.

An initial preservation comparison also treated differing Docker mount-list
order as a change. Sorting by destination confirms identical unrelated mounts,
IDs and states. No unrelated project was modified. All unsuccessful evidence
is retained in `.local-discovery/m6-load-20261027-001/` and `002/`.

### Reproduction and checks

Successful evidence is ignored `.local-discovery/m6-load-20261027-003/`:
`command.json`, `resources.jsonl`, `resource-status.json`, `summary.json`,
`before.json`, `after.json`, logs and `stop.json`. `raw-run/` contains the exact
native fixture, manifest, SDK/topic identities, warm-up/measured summaries and
all raw first-visible samples copied from `~/m6-transport-load-003`
in Ubuntu WSL. Native fixture: 11,040 bytes, SHA-256
`3a9b43a576fb14c326da6f9559c32d0d15267f01128e2f11116a6129d659e972`.
Each measured run serializes 8,531,072 event-value bytes. The generator and
benchmark source hash are recorded; Linux uses existing CPython 3.13.1 and the
admitted pinned Kafka 2.16.0 SDK without installation.

The exact successful launch is retained privately in `command.json`. The portable
form below uses `KAFKA_SITE` for the pinned client package directory and
`PYTHON313` for the pinned interpreter. This parameterized form was not rerun
during documentation cleanup:

```bash
PYTHONPATH=<repo>:<repo>/scripts:${KAFKA_SITE} \
  "${PYTHON313}" -B \
  <repo>/scripts/benchmark-transport.py \
  --private-config <repo>/.local-discovery/m6-load-20261027-003/config.json \
  --evidence ~/m6-transport-load-003 \
  --stop-file <repo>/.local-discovery/m6-load-20261027-003/STOP \
  --run-prefix m6-load-015
```

Use new topic/run/evidence identities on reproduction. The private JSON contains
the existing `HttpConfig` shapes for `writer` and `reader`. The observed SQL port
is loopback 18128, Kafka 19092; project runtime/serving subnets are
`10.254.242.0/28` and `10.254.242.16/28`. Parent-owned Compose startup combines
the existing M3 and M4 serving files with an explicit fresh runtime subnet.
Only `kafka` and `serving` start; no Flink/archive/monitoring service is started.

The retained parent `control.py` samples resources, creates `STOP` on pressure
or sampler error, enforces 600 seconds and stops the two owned services in
cleanup. The command itself also checks `STOP`/deadline each bounded batch.
Its fixed SQL timeout and five/six-second transport timeouts bound refusal
latency. Parent subprocess termination is not a transactional rollback guarantee.

Ruff lint/format, strict mypy and the existing <500-line module guard pass for
the new command. Separate raw-result recalculation verifies nearest-rank p50 /
p95 / p99 at literal sample indexes 63 / 121 / 126 and recomputes all measured
attempt rates; actual identity sets are compared across scopes. No mirrored
unit-test suite or unrelated acceptance cycle is added. Checks:

```powershell
.venv/Scripts/python.exe -m ruff check scripts/benchmark-transport.py
.venv/Scripts/python.exe -m ruff format --check scripts/benchmark-transport.py
.venv/Scripts/python.exe -m mypy scripts/benchmark-transport.py
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('scripts/check-m1.py')['check_module_sizes'](); print('Module-size check passed')"
git diff --check
```

Both owned containers finish stopped without OOM; all named volumes, fixtures
and failure evidence remain. Unrelated states/mounts compare unchanged. Rollback
stops this fresh project and omits the benchmark command; there is no persistent
migration, offset reset, data cleanup, dependency install, commit or publication.

Created files: `scripts/benchmark-transport.py` and this report. Updated files:
`scripts/check-m1.py`, `README.md`, `docs/roadmap.md`, `m6-local-monitoring.md`
and `docs/testing-strategy.md` for discovery/status/evidence navigation.

The subsequent full-path timing check now verifies
three 32-observation runs through the existing Flink/archive path with exact
source/archive/window/SQL reconciliation. Full M6 remains open for a supported
sustained-input and per-event visibility profile, completed checkpoint/committed-
lag/live archive-coverage signals and representative cardinality/late-rate load.
Neither this component baseline nor the finite full-path check establishes
sustained fleet capacity.
