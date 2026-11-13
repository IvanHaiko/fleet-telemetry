# Two-host 100-vehicle, 5 Hz run with an 8 GiB container

## Result, 2026-11-03

A fresh two-host run completed 360,000 ordinary synthetic measurements from
100 vehicles at 5 Hz each, followed by 100 closing tails. All 360,100 deliveries
were acknowledged in 720.25 seconds; the first-to-last admission span is 720.20
seconds, or 500.00 admissions/s. All 360,100 event IDs are unique.

The exact verifier matched **360,100 acknowledgements, 360,100 archived
deliveries and 360,100 SQL event facts** by source coordinate, identity and
content hash. All dispositions were eligible. It checked 7,200 closed windows
against exact rational sums; 100 tail windows remained open. The archive
contained 4,193 verified segments and 636,834,866 encoded bytes. This is one
bounded, synthetic run, not repeated capacity or failure-recovery evidence.

The sampled input end and archive cursor both reached 360,100. The
checkpoint-committed Flink input position also reached 360,100. The SQL cursor
remained 33 offsets below the Kafka output high-water sum; a separate
`read_committed` consumer started at the saved cursor reached EOF on all 18
partitions without reading any further records. Offsets include non-data
positions, so the raw difference is not treated as 33 missing events.

## Queues and SQL visibility

The 246 successful samples were sequential reads, not atomic snapshots. The
largest sampled differences were 2,669 records between input high water and
archive cursor, 13,000 records between input high water and Flink's committed
checkpoint position, and 5,542 output offsets between Kafka high water and the
SQL cursor. The checkpoint difference can include work already processed but
not yet checkpointed; the output offset difference can include non-data
positions. Neither is an instantaneous application queue length.

The observer matched every one of the 360,100 unique IDs to the acknowledgement
ledger. Admission and observation use the same PC monotonic clock. The SQL
query response records an upper-bound observation of first visibility, including
polling and query time; the observer's queries also add load.

| Admission to observed SQL visibility | Seconds |
| --- | ---: |
| p50 | 13.39 |
| p95 | 25.12 |
| p99 | 30.62 |
| Maximum | 44.63 |

These are synthetic processing and polling observations, not real-radio latency
or a production service objective. Physical measurement time is historical
and advances by 200 ms per vehicle; it is separate from admission time.

## Memory and shutdown

The existing TaskManager container was temporarily updated from 4 to 8 GiB
RAM with `docker update --memory 8g --memory-swap 12g`, preserving the previous
4 GiB swap allowance. Its Flink JVM process setting remained 1536 MiB; the
container limit also covers Python workers and other cgroup memory. The sampled
peak was 4,605,603,840 bytes (4.289 GiB), comprising approximately 3.733 GB
anonymous memory, 0.716 GB file memory and 0.152 GB kernel memory. OOM and
OOM-kill counters remained zero. The lowest sampled WSL `MemAvailable` was
14.66 GiB. Samples cannot establish a precise unsampled peak or attribute
anonymous growth between JVM and Python processes.

The first sample after startup measured approximately 3.459 GB anonymous and
0.424 GB file memory. At the sampled peak those categories had increased by
about 274 MB and 292 MB respectively. This distinguishes broad cgroup
categories, not individual allocations or a proven leak. The 8 GiB limit was
left on the existing TaskManager for further local work. It is a Docker
container update; recreating the container from the existing recipe restores
its 4 GiB default. To revert the current idle container explicitly, use
`docker update --memory 4g --memory-swap 8g fleet-cpu-20261103-001-taskmanager-1`.

Before this successful run, a metric read received Kafka `NOT_COORDINATOR` and
the observer stopped the publisher. The publisher handled the actual SIGTERM:
48,371 attempted and acknowledged events, 48,371 ledger rows, zero delivery
errors and zero unconfirmed events. The observer now records that transient
position-read failure as unavailable and continues. The maintained publisher
also checks stop signals while draining callbacks; eight focused setup tests,
Ruff and Linux-profile mypy pass. The final short-interval drain refinement was
unit-tested after the runtime signal drill, and was not separately exercised
against Kafka. A hard kill or host loss can still leave delivery outcome
uncertain; no durability guarantee is inferred from graceful shutdown.

## Procedure and retained evidence

The six existing brokers were restarted with separate empty input, output and
live topics for `split-load500-20261103-003`. Each of the 18 partitions had
two in-sync replicas, one on each host. Archive and SQL data use a separate
prefix and database. The same laptop Flink graph and PC storage/worker placement
as the interrupted 4 GiB run were used. There were no
intentional duplicates or late events, no new package or image, and no failure
injection in this successful run.

The observer was stopped after publication, full ID observation, input/archive
catch-up and a stable serving cursor. Its original exit condition incorrectly
required the SQL cursor to equal the raw Kafka high water; the independent
`read_committed` EOF check above resolves that difference. The observer
therefore exits with `KeyboardInterrupt` after collecting the evidence rather
than reporting a clean exit. The exact verifier is the existing verifier with
its SQL page size increased from 128 to 1,024 rows in an isolated copy; its
checks and 256 MiB query limit are unchanged. It exited zero.

Scripts, source ledger, SQL visibility observations, sample summaries,
container memory breakdown, checkpoint snapshot and reconciliation report
remain under `.local-discovery/load500-20261103-003/`; a PC copy is under
`H:\telemetry\pc-20261103-001\evidence\load500-20261103-003`. The stopped
intermediate attempt remains in the adjacent `-002` evidence scope. The local
summary can be recalculated with:

```powershell
.venv/Scripts/python.exe .local-discovery/load500-20261103-003/summarize.py
```

The test job and the six brokers started for the experiment were stopped after
verification. Volumes, checkpoints, input topics, cursors and evidence remain
intact; existing storage and idle Flink services remain running. No commit,
publication or cloud mutation was performed. Repeated runs, long-duration
steady state, failure recovery and resource attribution remain open.
