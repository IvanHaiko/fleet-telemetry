# Live PX4 SITL session on the recording profile

[ADR-0054](../adr/0054-live-sitl-recording-profile.md) connects one PX4 SITL
simulator to the single-machine recording profile: a gateway with durable raw
capture, Kafka, the Flink association lane, the independent archive,
archive-gated SQL and Grafana. This is a simulated source, not a physical
vehicle or RF link. No arming, takeoff, mission or other flight command is sent.

Building, starting or stopping services needs the maintainer's authorization,
as for the F09 runs in the [single-machine guide](f09-single-machine-run.md).

For routine operation (start, status, evidence, stop and restoration) use the
[operator runbook](operations-runbook.md); this guide keeps the manual steps
and the orchestrated scenario.

## What it needs

Everything is already local; nothing is downloaded:

- the recording profile's images;
- the PX4 SITL image pinned by digest
  `39d5a950208a5a45fccbbb0670bd8716663ed0b350ef738447581395e0c92d97`;
- the retained Linux package directory with pymavlink 2.4.50 and
  confluent-kafka 2.16.0 (`.local-discovery/sim-map-20261103/linux-packages`),
  mounted read-only into the gateway;
- the Grafana ClickHouse plugin directory the F09 preparation uses.

The simulator joins only the internal `live-source` network
(`RECORDING_LIVE_SUBNET`, default `10.253.240.32/28`). The archive container
also joins it, and the gateway, like every worker, runs in that container's
network namespace. Neither the simulator's ports nor the gateway's UDP port is
published to the host.

## One orchestrated session

```powershell
.venv/Scripts/python.exe -m runtime.recording.live_run --run-id <new-run-id>
```

The orchestrator runs these steps in order:

1. prepares a new private directory
   (`.local-discovery/recording-private-<run>`) with `live_prepare.py`;
2. writes `criterion.json` before any service starts;
3. starts the profile with the `live` services and initializes fresh topics, a
   database, a bucket and role configs (`live_initialize.py`);
4. submits the Flink job, starts the observer, the live archive and serving
   workers, then the gateway, then the simulator;
5. starts a PX4 MAVLink instance in `minimal` mode at 4,000 B/s towards the
   gateway, with `GLOBAL_POSITION_INT` at 5 Hz and `SYS_STATUS` at 1 Hz;
6. pauses the simulator for a source silence, then stops and restarts the
   gateway;
7. completes the session with `SIGUSR1` to the gateway, then stops the
   simulator;
8. waits for serving completion, runs the reconciliation (`live_reconcile.py`)
   and evaluates the samples;
9. writes `result.json` and stops the profile without removing a volume.

The default schedule counts from the first publication:

| Step | Default | Option |
| --- | --- | --- |
| Source silence starts | 180 s | `--silence-at` |
| Silence lasts | 30 s | `--silence-s` |
| Gateway stops | 360 s | `--restart-at` |
| Gateway is down | 15 s | `--restart-down-s` |
| Session completes | 600 s | `--end-at` |

`--visibility-limit`, `--recovery-limit`, `--drain-limit`, `--observed-fraction`
and `--interval` set the declared limits and the sampling interval. Evidence goes
to `.local-discovery/<run>/`, the console log to
`.local-discovery/<run>.console.log`.

## Reading the result

`result.json` reports `passed`, `failed_criterion` or `failed`, with:

- `correctness`: capture coverage and loss, archive count, SQL hash set
  against the archive-only rebuild, logical repeats, untimed streams,
  association statuses against input order, and operator refusals;
- `live_state`: what the view showed during the silence, during the gateway
  outage and in steady state;
- `timing`: visibility outside the drills, recovery after each drill and the
  terminal drain, from the observer's single clock.

Grafana at `http://127.0.0.1:13003/` has a *Live PX4 SITL session* dashboard per
run. Its connection panel follows `live_state`: *observed* only while a source
heartbeat arrived in the last 3 s and the gateway and serving reports are
current; *stale* while the gateway is current but the source is silent;
*unknown* otherwise. Current values show only while observed.

The gateway's raw capture (`capture-<epoch>.jsonl`), its acknowledgement
ledgers and its status stay in the `evidence` volume under
`/evidence/<run>/state`. The capture holds simulated coordinates; keep it out of
reports.
