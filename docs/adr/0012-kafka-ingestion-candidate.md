# ADR-0012: Propose a bounded Kafka ingestion compatibility experiment

**Status:** Kafka `4.4.0` selected by the maintainer for the M2 experiment.
The first scoped local admission/clean-consumer-reopen experiment is implemented
and validated. Full M2 runtime adoption remains proposed pending recovery,
retention and broader acceptance evidence.

**Date:** 2026-10-20

**Image-route follow-up:** [ADR-0013](0013-local-kafka-release-image.md) partially
supersedes the proposed ready-made image route after registry inspection returned
`not found`. It authorizes a local image of the same 4.4.0 release for the scoped
synthetic experiment. Runtime validation results are recorded separately.

## Problem

The independent M1 reader establishes envelope admission, but cannot demonstrate
broker acknowledgements, retained records or consumer offset recovery. M2 needs
one concrete broker/client pair and a small experiment that distinguishes these
boundaries before adding processing or storage services. M1 hosted CI and actual
ULog source acceptance remain open; this proposal does not waive that dependency.

## Proposed decision

Target the official JVM image `apache/kafka:4.4.0` with one combined KRaft
broker/controller, and synchronous `confluent-kafka==2.16.0` on the existing
CPython 3.13 Windows x86-64 toolchain. The client release is based on librdkafka
2.16.0, and a matching CPython 3.13 Windows wheel is published. These are upstream
compatibility grounds, not a locally validated matrix. The
experiment plan records sources and remaining pins.

Keep the client in the optional `kafka` extra, independently of `ulog`.
Continue using the standard-library converter and reader for offline work.
Use the existing synthetic conversion fixture, one partition, explicit topic
creation and a named Linux volume under Docker Compose. Preserve canonical value
bytes and the UTF-8 `vehicle_id` key. Native mapping, measurement identity and
wire schema remain unchanged.

Require producer idempotence, delivery callbacks and bounded shutdown; report
uncertain outcomes rather than assuming a timeout proves absence. Consumer
auto-commit and automatic offset storage must be disabled. Commit the next
offset only after the declared local observation receipt is verified. Missing
or out-of-retention progress must fail rather than silently reset. Replaying an
application after a crash can still create observations with repeated event IDs.

## Alternatives and cost

- [kafka-python](https://github.com/dpkp/kafka-python) offers a Python client
  implementation without making librdkafka the selected boundary. It remains a
  viable fallback if native-wheel or typing integration is disproportionate;
  it needs the same real-broker recovery evidence. No performance comparison has
  been performed here.
- [aiokafka](https://github.com/aio-libs/aiokafka) fits an asyncio application.
  The current bounded commands do not need an event loop, so that programming
  model supplies no required behavior for the first experiment.
- A JVM producer or bundled CLI can diagnose the broker, but adds a second
  application language if used as the maintained Python ingestion path.
- A managed broker adds account, credential and ongoing-cost responsibilities;
  the accepted local-first boundary defers cloud work to M8.

The proposal adds one native Python package and one JVM service at implementation
time. Wheel/library provenance, image digest/JRE patches, security updates,
Compose behavior, retained disk space and failure probes become maintenance
obligations. It creates no cloud bill; Docker Desktop licensing eligibility and
workstation resource capacity still require review. No capacity or throughput
claim is supported yet. The maintainer selected Kafka 4.4.0 on 2026-10-20 for
this new runtime. Use that exact release rather than a floating `latest` tag.
Release artifacts are published by Apache; the image tag/digest and bundled JRE
must be verified before executable configuration is added. An older broker
requires a documented incompatibility or regression and a revised decision;
there is no established need for one in this project.

## Acceptance, consequences and rollback

Adopt only after the plan's exact-byte/key reconciliation, unavailable-broker,
producer/consumer interruption, preserved-volume restart and retention-gap
experiments pass with recorded versions and resource limits. A single broker
with `acks=all` still has one data replica; it proves neither replication nor
host-loss recovery. Kafka and Flink remain proposed under ADR-0001.

This documentation increment changes no persistent state. A future rollback
stops the isolated Compose project, preserves its named volume and evidence,
and removes the optional ingestion path without altering M1 runs. Broker
downgrades against existing data and volume deletion need separate procedures.
No accepted ADR is superseded.
