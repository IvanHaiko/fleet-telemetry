# Documentation guide

Start with the [project overview and runnable synthetic example](../README.md).
The project has accumulated separate experiments; a dated success applies to
the profile described in its report, not every runtime in this repository.

## Layout

| Folder | Contents |
| --- | --- |
| `docs/` | Core design: architecture, contracts, roadmap, testing, deployment |
| [`adr/`](adr/) | Architecture decision records, numbered in order |
| [`guides/`](guides/) | How to run a specific profile, check or environment |
| [`reference/`](reference/) | Interfaces, archive format, field catalogs, datasets and reference calculations |
| [`case-studies/`](case-studies/) | Selected experiments with measured results and their limits |

## Understand the system

| Document | What it owns |
| --- | --- |
| [Architecture](architecture.md) | Component responsibilities, delivery semantics and open decisions |
| [Data contracts](data-contracts.md) | Identity, units, clocks, missing values and compatibility |
| [Roadmap](roadmap.md) | Acceptance criteria, sequencing and remaining work |
| [Testing strategy](testing-strategy.md) | Invariants and required evidence |
| [Deployment](deployment-and-terraform.md) | Local runtime, resource/security boundaries and the cloud gate |
| [Architecture decisions](adr/) | Accepted and proposed choices with their consequences |

## Run a declared profile

- **Start here:** [one-machine Kafka/Flink quickstart](local-development.md).

- [Synthetic and ULog conversion](guides/bounded-conversion.md), [canonical reader](guides/canonical-reader.md) and [run verification](guides/run-verification.md).
- [M1 development checks](guides/m1-checks.md) and [contributor guide](../CONTRIBUTING.md).
- [F09 stream preparation](guides/f09-stream-replay.md) and [bounded integrated F09 evidence](adr/0050-integrated-f09-runtime.md).
- [Recording inspection](guides/recording-connection.md) and [two-recording view](guides/two-recording-view.md).
- [Live MAVLink observer](guides/live-px4-mavlink.md), [source-to-query position slice](guides/live-position-source-query.md) and [continuous position](guides/continuous-position.md).

The synthetic conversion example needs no private inputs. Recorded-source and
service guides describe additional prerequisites; retained local paths do not
exist in a fresh clone. Start only the selected Compose profile; the root
`compose.yaml` is the default starter and the other profiles live in `compose/`.

## Case studies

Selected experiments, each with its setup, result and limits:

| Case study | What it shows |
| --- | --- |
| [100 vehicles at 5 Hz](case-studies/m6-load-500-8g.md) | Two-host load run; 360,100 events reconciled across Kafka, archive and SQL |
| [Transport and serving baseline](case-studies/m6-transport-benchmark.md) | Replay throughput and first-visible latency on a recorded environment |
| [Kafka retention incident](case-studies/kafka-retention-incident.md) | Cause analysis of lost retained records and the resulting production gate |
| [Broker SIGKILL](case-studies/kafka-broker-sigkill.md) | Retained records after an abrupt broker kill |
| [Identity-state limit](case-studies/m6-identity-state-limit.md) | Diagnosis and repair of a continuous-job state refusal |
| [Reliability profile](case-studies/m5-reliability.md) | Checkpoint, late-event and rebalance checks on synthetic data |
| [Windows Kafka UUID repair](case-studies/windows-kafka-uuid-repair.md) | Client bug reproduction, local repair and upstream regression |

The [production recovery gate](guides/production-recovery-gate.md) lists what
must hold before any of this runs beyond a local machine.

Raw logs, private measurements, credentials, checkpoints and generated run
artifacts stay outside distributable source. Earlier step-by-step experiment
logs are kept outside the repository; the ADRs record the decisions they led to.
