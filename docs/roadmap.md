# Roadmap

What the project is aiming at, where it stands and what comes next. Each item
links to the decision record that holds its design and evidence. Earlier plans,
with every acceptance criterion and status ledger, are kept verbatim in the
[roadmap history](roadmap-history.md).

## Goal

A local fleet telemetry monitor. Recorded flights and live PX4 vehicles enter
through one MAVLink input and flow through Kafka, Flink, an independent
archive, ClickHouse and Grafana, with every value traceable to its source.
Version 1 runs on one computer; an AWS deployment is an optional later stage.

## Where it stands, 2026-11-17

| Capability | State | Decisions |
| --- | --- | --- |
| Replay of a recorded flight file | Complete 39-minute F09 flight, F07, F03 and one further PX4 log on reviewed firmware; SQL equals a prepared reference by content | [0052](adr/0052-single-machine-recording-profile.md), [0057](adr/0057-registered-recordings-in-the-integrated-path.md), [0058](adr/0058-admission-by-mapping-profile.md) |
| Live PX4 over MAVLink | One simulated vehicle (SITL); SQL equals a rebuild from the archive | [0054](adr/0054-live-sitl-recording-profile.md) |
| Failure and restart | Four injected faults and a whole-profile stop and restore without loss or logical repeats; broker, JobManager and host failures not verified | [0053](adr/0053-recording-recovery-boundaries.md), [0055](adr/0055-recording-operations-and-restoration.md) |
| Run health | Every signal with a threshold and `ok`/`warn`/`fail`/`unknown`; SQL quality checks; which stage stopped and why; no unattended alerting | [0056](adr/0056-run-health-without-a-monitoring-stack.md), [0059](adr/0059-explaining-stalled-values.md) |
| Inspecting any ULog | Offline report of topics, fields, samples and supported views for any structurally valid file | [0058](adr/0058-admission-by-mapping-profile.md) |
| Synthetic load | 100 vehicles at 5 Hz on two computers, 360,100 events reconciled | [case study](case-studies/m6-load-500-8g.md) |

**MVP acceptance is open.** The final F09 run passed seven of its eight
declared conditions (disk budget failed: ClickHouse system logs, since
bounded); the final live run passed six of eight (a health signal and a
sampling artifact, both fixed and checked on a debug session, not on a
repeated final run). The maintainer accepts them as recorded or asks for a
repeat ([details](roadmap-history.md#integrated-mvp-priority-2026-11-10)).

## Next

1. **Recorded flights as virtual vehicles.** A player turns each ULog file
   into a virtual PX4 that sends MAVLink to the live gateway; several vehicles
   share one session and join without a restart
   ([ADR-0060](adr/0060-recorded-flights-as-virtual-vehicles.md), proposed).
   *First step done 2026-11-17:* F09 and F03 in one session, F09 paused while
   F03 kept advancing, F03 `ended`, `verify` passed per vehicle.
2. **Demonstration with 3–4 random logs.** Extend the field signatures to the
   most frequent unsupported variants, then replay files chosen at random in
   advance from the local logs with a position.
3. **Logs without GPS.** Show local position (`LOCAL_POSITION_NED`) on a
   local-frame view for the indoor logs that have no geographic position.
4. **A physical PX4 over a radio link.** Needs a vehicle and a telemetry
   radio; checks link loss and the real screen latency.

Only when a need appears: other autopilots such as ArduPilot (their heartbeat
and mode encoding need a review), raw streaming of all recorded topics for a
named consumer, unattended alerting, and the AWS stage (M8).

## Milestones

| Milestone | State |
| --- | --- |
| M0 Foundation | Delivered: contracts, architecture, working agreements |
| M1 Data sources and deterministic replay | Synthetic conversion and reviewed PX4 logs; CI on Windows and Linux |
| M2 Kafka ingestion | Accepted 2026-10-21 for the local synthetic profile ([ADR-0017](adr/0017-synthetic-m2-acceptance.md)) |
| M3 Flink processing | Accepted 2026-10-22 for the bounded local synthetic profile ([ADR-0022](adr/0022-persistent-m3-completion.md)) |
| M4 Storage and analytics | Accepted 2026-10-26 for the bounded synthetic profile ([ADR-0032](adr/0032-bounded-m4-completion.md)) |
| M5 Reliability | Accepted 2026-10-26 for the bounded synthetic profiles ([case study](case-studies/m5-reliability.md)); recording-profile faults in ADR-0053 |
| M6 Observability and benchmarks | Open: run health and the load observation exist, no formal acceptance |
| M7 Portfolio release | Open: follows the MVP and the fleet demonstration |
| M8 AWS with Terraform | Optional; needs its own purpose, budget and authorization ([deployment](deployment-and-terraform.md)) |

## Keeping this file short

A finished item becomes one row or line with its decision link. Designs,
evidence, run IDs and measurements belong in the decision records, guides and
case studies, not here.
