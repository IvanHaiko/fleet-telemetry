# Kafka retained-record check after broker SIGKILL

## Scope and result

On 2026-10-20, the authorized synthetic-only M2 experiment killed the existing
Kafka 4.4.0 JVM with SIGKILL and started the same container on its original named
volume. All three acknowledged captured records, keys, offsets, cluster/topic
identity and committed next offset survived this one process failure.
This follows the graceful restart and
retention-gap checks. M1 and full M2 acceptance remain open.

The existing [restart harness](../../scripts/check-kafka-restart.py) now accepts
`--mode sigkill`; its default remains `graceful`. No dependency, service,
broker setting, image, data contract or receipt format changes are introduced.

| Evidence | Before SIGKILL | After startup |
| --- | --- | --- |
| Exact original values and vehicle keys | 3 matches | Same 3 matches |
| Partition / offsets | 0 / 0, 1, 2 | Unchanged |
| Retained interval | `[0, 3)` | `[0, 3)` |
| Committed next offset | 3 | 3 |
| Cluster ID | `MkU3OEVBNTcwNTJENDM2Qk` | Unchanged |
| Topic UUID | `/////6S9TNEAAAAAAZVsdA` | Unchanged |
| Container, image, named volume | Original identities | Unchanged |
| Process `StartedAt` | `2026-10-20T11:47:38.588106609Z` | `2026-10-20T11:47:51.142954226Z` |

The failure mode is explicitly checked. Immediately before the signal,
`/proc/1/comm` reports `java`. The harness runs the
[Compose kill command](https://docs.docker.com/reference/cli/docker/compose/kill/)
with `--signal SIGKILL`, then inspects the stopped container: state `exited`,
exit code 137, `OOMKilled=false`, with the same identity and process start time.
It records that state before running `compose start`. No graceful stop or restart
occurs between those checks.

After startup, a new consumer compares actual received bytes and keys with the
external verified M1 source, validates each envelope, and checks stored progress
before/after read-only inspection. It neither commits nor republishes events.
The complete before/after record snapshots match, including offsets, identities
and hashes. The fixture's fourth native slot remains an M1 rejection.

## Commands and evidence

The existing setup guide owns the pinned local image,
client and runtime. This check requires the existing stopped container in Docker
context `desktop-linux`, verifies Compose ownership and the named data mount,
and refuses a reused output directory. The admission helper refuses an existing
topic and existing group progress. A repeat needs fresh experiment/output names
and an independently verified three-event synthetic run.

The exact successful experiment and graceful-mode regression commands were:

```powershell
.local-discovery/kafka-client-2.16.0/Scripts/python.exe scripts/check-kafka-restart.py --job tests/fixtures/synthetic-conversion-job.json --run .local-discovery/m1-check-4595137880b24811852a885a54f1d9d9/demo-synthetic-001 --experiment sigkill-20261020-001 --output .local-discovery/kafka-sigkill-001 --mode sigkill
.local-discovery/kafka-client-2.16.0/Scripts/python.exe scripts/check-kafka-restart.py --job tests/fixtures/synthetic-conversion-job.json --run .local-discovery/m1-check-4595137880b24811852a885a54f1d9d9/demo-synthetic-001 --experiment sigkill-control-20261020-001 --output .local-discovery/kafka-sigkill-control-001
```

Both exit 0. The first reports `retained_records_sigkill_verified`; the second
reports `retained_records_restart_verified`. Each starts the existing broker,
checks version 4.4.0, admits three events, captures its initial snapshot, injects
the selected failure/restart, compares the final snapshot and stops the broker
in a `finally` block. The SIGKILL path uses:

```powershell
docker compose -p fleet-kafka-440-probe -f compose/kafka.yml exec -T kafka cat /proc/1/comm
docker compose -p fleet-kafka-440-probe -f compose/kafka.yml kill --signal SIGKILL kafka
docker inspect fleet-kafka-440-probe-kafka-1
docker compose -p fleet-kafka-440-probe -f compose/kafka.yml start kafka
```

Ignored evidence is under `.local-discovery/kafka-sigkill-001/` and
`kafka-sigkill-control-001/`: source-bound admission receipts, `before.json`,
`after.json`, completed command logs and `summary.json`. The SIGKILL directory
also contains `crashed.json`. Initial context/ownership checks precede creation
of the fresh output directory and are in `summary.json`; `commands.jsonl`
contains completed commands after that preflight. Summaries include final
container/image/volume identities and process start times.

The final state after both checks is broker stopped and original
`fleet-kafka-440-probe_kafka-data` retained. The M1 source and prior experiment
reports are preserved. No data volume, topic or previous receipt was deleted,
reset or reformatted. Existing retention policies continue to apply.
Both final Compose stop commands exit 0; their JVM/container exit status is 143
after termination, distinct from the injected SIGKILL status 137. Neither final
state reports OOM.

## Validation

The pinned client environment ran:

```powershell
.local-discovery/kafka-client-2.16.0/Scripts/python.exe -m ruff check scripts/prepare-kafka-image.py scripts/kafka-probe.py scripts/check-kafka-recovery.py scripts/check-kafka-restart.py scripts/check-kafka-retention.py
.local-discovery/kafka-client-2.16.0/Scripts/python.exe -m ruff format --check scripts/prepare-kafka-image.py scripts/kafka-probe.py scripts/check-kafka-recovery.py scripts/check-kafka-restart.py scripts/check-kafka-retention.py
.local-discovery/kafka-client-2.16.0/Scripts/python.exe -m mypy scripts/prepare-kafka-image.py scripts/kafka-probe.py scripts/check-kafka-recovery.py scripts/check-kafka-restart.py scripts/check-kafka-retention.py
.venv/Scripts/python.exe .local-discovery/verify_kafka_sigkill.py
```

Ruff formatting/lint and strict mypy passed. The final verifier reconciles both
real broker results with the external source and receipt hashes, confirmed exit
state, commands, local links/anchors, unchanged source/configuration inventory,
prior evidence hashes, frozen lock consistency and current stopped runtime.
Results and hashes are in `.local-discovery/kafka-sigkill-verification.json`;
exact quality commands/results are in `kafka-sigkill-quality.log`.
No pytest cases were added. M1 pure modules are unchanged; the earlier 335-test
M1 result remains historical and that suite was not rerun.

## Limits, rollback and next task

This is one SIGKILL after completed admission, commit and readback on a single
broker/partition with an intact volume and host. It does not inject failure at
the immediate acknowledgement or fsync boundary, flush the OS cache, remove
power, kill the Docker/WSL host, corrupt storage or demonstrate replication.
It establishes no general no-loss, high-availability, benchmark or end-to-end
exactly-once guarantee. Concurrent load, repeated crash loops, retention races,
producer uncertainty, rebalances and hosted service CI remain unvalidated.
The next smallest failure experiment is producer interruption after broker
acknowledgement but before durable local publication progress, with explicit
duplicate/missing-identity reconciliation.

Follow-up on 2026-10-20: the consolidated local cycle
now verifies that producer boundary and reruns this SIGKILL check with the rest
of the synthetic acceptance matrix. The original evidence here is preserved.

Rollback removes the optional SIGKILL mode and navigation additions while
preserving evidence and the stopped volume. Graceful mode keeps its original
interface and success status; new container exit/OOM fields are internal
diagnostics, not canonical contract changes. No data migration or dependency
downgrade is required. Git metadata is absent; no commit or publication was made.

## File inventory

| File | Change |
| --- | --- |
| [check-kafka-restart.py](../../scripts/check-kafka-restart.py) | Optional SIGKILL/start mode, JVM PID 1 check and confirmed exit/OOM evidence |
| [This guide](kafka-broker-sigkill.md) — new | Exact commands, result, evidence and failure-model limits |
| [README](../../README.md), [architecture](../architecture.md), [roadmap](../roadmap.md), [testing strategy](../testing-strategy.md), [deployment guide](../deployment-and-terraform.md), M2 plan, restart guide, retention guide | Current evidence and follow-up navigation |

Canonical contracts, production modules, fixtures, tests, dependency pins,
Compose configuration and image sources are unchanged. Ignored evidence and
verification helpers remain local.
