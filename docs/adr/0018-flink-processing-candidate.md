# ADR-0018: PyFlink direction for the bounded M3 compatibility experiment

**Status:** Accepted for the API direction of a local compatibility spike by the
maintainer on 2026-10-21. The candidate version matrix, installation and runtime
adoption remain gated by the evidence below. This is not M3 acceptance.

**Date:** 2026-10-21

## Problem and maintainer decision

M2 is accepted for the local synthetic profile under ADR-0017. M3 needs typed
admission, keyed identity state, event-time timers, explicit late/conflict
dispositions and checkpoint/source recovery. The maintainer prefers Python
because it is familiar and Java application development would add a substantial
learning burden. Use **PyFlink** for the compatibility experiment. Keep ingestion
and the independent reference on the existing Python 3.13 toolchain.

The initial Java DataStream proposal was not accepted. Its API advantage does
not outweigh that maintenance/learning constraint for this project. No Java job
or Maven build is introduced. PyFlink still requires a JVM and Python workers;
selecting Python does not remove that operational boundary.

## Candidate matrix and isolation

Target PyFlink (`apache-flink`) **2.2.1**, a separate **Python 3.12** environment,
Java **17**, and the matching Kafka connector **5.0.0-2.2**, against the existing
Kafka **4.4.0** broker. Keep the connector's Kafka client **4.2.0** dependency
initially. Do not replace it with the Python producer's librdkafka version.
This matrix is supported by documentation, not yet validated locally.

The [versioned installation requirements](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/dev/python/installation/)
list Python 3.9-3.12; Python 3.13 is not a supported PyFlink 2.2 runtime. The
[official PyPI release](https://pypi.org/project/apache-flink/2.2.1/) provides a
Linux x86-64 CPython 3.12 wheel. Use a separate environment and lockfile so its
Beam/NumPy/PyArrow/worker dependencies cannot replace M1's optional reader or
tools. Begin on Linux/WSL, keeping the host environment and root `uv.lock` intact.

The [Apache compatibility matrix](https://flink.apache.org/downloads/) lists
connector 5.0.0 for Flink 2.1.x/2.2.x. The
[versioned connector guide](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/datastream/kafka/)
gives the `5.0.0-2.2` coordinate, and the
[release POM](https://github.com/apache/flink-connector-kafka/blob/v5.0.0/pom.xml)
pins Kafka client 4.2.0. The
[2.2.1 announcement](https://flink.apache.org/2026/05/15/apache-flink-2.2.1-release-announcement/)
identifies the bug-fix release. Do not infer broker/runtime compatibility from
these version numbers without an actual run.

[Versioned Java guidance](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/java_compatibility/)
recommends Java 17. Do not reuse the Kafka image's Java 25 by inference. Before
installation, pin the exact maintained Python 3.12 patch/distribution/checksum,
JDK 17 patch/vendor/checksum, complete resolved PyFlink dependencies and connector
JAR checksum. Pin any eventual image digest. The Python 3.12 line alone is not
a reproducible installation recipe. No runtime package is installed by this ADR.

## Alternatives and cost

- **Java DataStream:** direct typed timers, state and record deserialization,
  but adds a language/build unfamiliar to the maintainer. Not selected.
- **SQL/Table API through PyFlink:** retain as an option inside the Python
  experiment if it materially simplifies input metadata or aggregation. It
  must still preserve conflict, expiry, late evidence and invalidation semantics.
- **PyFlink in the root Python environment:** rejected because Python 3.13 is
  unsupported by the chosen line and its dependency graph differs from M1.
- **Flink 2.3.0:** newer runtime, but its
  [connector guide](https://nightlies.apache.org/flink/flink-docs-release-2.3/docs/connectors/datastream/kafka/)
  currently has no matching released connector. Recheck compatibility before
  changing the candidate rather than assuming a newer minor works.

Python workers, their serialization boundary and the JVM add memory and restart
cost; measure these before choosing resource limits. Dependency maintenance now
includes a second isolated Python environment and JVM. No cloud cost or new
orchestrator is required. The existing Python reference remains a bounded
calculation oracle, not an alternate stream-processing engine.

## Required evidence and rollback

The [reference slice](../reference/m3-window-reference.md) defines controlled expectations
before a processing candidate exists. It cannot prove connector loading,
periodic watermarks, idleness, Python worker recovery or checkpoint semantics.

First prove package resolution, JVM/worker startup, connector loading, exact
timestamp conversion and finite completion in a tiny Linux experiment. Use
classic PyFlink DataStream where it covers the required operators. Check Python
timestamp-assigner/side-output behavior before choosing a job structure. Invalid
timestamps must be isolated before watermark generation.

The Python Kafka API's value-only deserialization does not expose every native
record field. If the experiment needs key/offset metadata unavailable there,
evaluate a supported Table source/metadata bridge first. Do not silently add a
custom Java helper or discard required evidence to conceal an API limitation.

Then compare actual dispositions and ten-second summaries with the frozen
reference. Capture downstream global watermarks, not only arrival order. A
source must stop at explicit captured offsets; silence is not EOF. Checkpoint
tests must run in streaming execution mode, with stable operator UIDs, explicit
state types, persistent local checkpoint storage, matching source offsets and
actual Python worker/TaskManager failure. Add Compose only with that experiment's
owned runtime, limits and cleanup defined. M3 stays open until the roadmap's
full compatibility, idleness, bounded-state and recovery criteria pass.

If this direction proves unsuitable, record a linked decision with actual
failure evidence before selecting another API. Stop only owned test runtime;
retain evidence/checkpoints and preserve all existing M2 data and receipts.
No source identity, canonical schema or M2 migration is introduced here.

## Bounded compatibility follow-up, 2026-10-21

The maintainer authorized environment preparation and the next bounded checks.
The compatibility guide records exact archive
and dependency pins, source/JAR/native-binary hashes, failed attempts, actual
runtime results and rollback. CPython 3.12.13, Temurin 17.0.20.1+1, PyFlink
2.2.1 and the shaded SQL connector 5.0.0-2.2 now pass process-worker startup,
literal timestamp assignment, invalid side output and finite Kafka reads with
topic/partition/offset and original key/value hash reconciliation.

The supported Table-to-DataStream bridge preserves needed record metadata
without Java application code. The embedded MiniCluster is transient and uses
one slot, loopback endpoints and a bounded JVM heap; persistent recovery
topology remains deferred. Native Linux runtime storage is required because
the initial Python archive extraction on the Windows mount hit a case-related
symbolic-link cycle. Bootstrap retained the failure and its safe extraction
filter; it installs neither interpreter nor JVM globally. Maintenance now owns
the separate 61-distribution environment and its pinned source-build tools.

This qualifies the declared compatibility experiment only. It changes no
accepted contract or sequencing decision. Full envelope/source admission,
managed deduplication, windows, observed watermark/idleness decisions and
checkpoint/source recovery remain necessary before M3 acceptance. The earlier
documentation-only matrix statement records the evidence at the initial API
decision; it is not the current runtime result.

## Finite operator follow-up, 2026-10-21

The maintainer requested the next five steps after compatibility preparation.
The finite battery operator now exercises canonical
admission, managed keyed identity/history/window state, event-time callbacks,
exact ten-second summaries and independent-reference comparison. It uses the
same runtime and dependencies. Periodic watermarks are deliberately disabled;
source EOF drives final windows and active-state cleanup. Whole-run release is
rejected on conflicts, including windows from other vehicles.

This is a bounded experiment under the existing API decision, not adoption of
an unbounded processor or M3 acceptance. Intermediate watermarks, late/idle
behavior, measured state-pressure limits and persistent checkpoint/source
recovery remain required. It introduces no Kafka publication, storage migration,
new service or alternate orchestration system.

## Intermediate-watermark follow-up, 2026-10-21

The maintainer authorized the next ten steps. The paced watermark experiment
extends the same operator with late/window diagnostics, fixed-name counters,
explicit state limits and actual intermediate-time boundary checks. A bundled
legacy loopback socket source supplies a finite controlled test; it introduces
no Java helper, new JAR or dependency and is not adopted as a checkpointable
application input. The guide records alternatives, lifecycle cost and rollback.

The independent reference remains unchanged. Capture actual watermarks and
require full comparison and deliberate state-limit failure; requested progress
or a sleep is not evidence. This does not supersede the API decision or accept
M3. Checkpoint/source recovery, multi-source idleness and measured memory limits
still require their own real runtime experiments.

## Checkpoint and independent-worker follow-up, 2026-10-22

The authorized ten-step continuation produced a bounded checkpoint recovery
candidate. The final isolated Kafka run observes
completed checkpoint 1 at next 3, managed-state/source restoration at 3 after
independent Python worker exit and successful finite completion at 9. Eight unique
identities and two windows match the unchanged reference. It is a transient
MiniCluster, not the persistent topology anticipated above. TaskManager/host
recovery, multi-input idleness, memory limits and M3 acceptance remain open.

Clarification of the earlier worker claim: local `python.execution-mode=process`
did not establish an independent OS worker; the SDK can select loopback execution.
This experiment pins 2.2.1, selects its private process-launch setting and guards
fault injection using distinct client/worker PIDs. This version-sensitive boundary
requires fresh review on upgrade; earlier SDK checks remain historical evidence.

The initial shared-broker attempt expired four old synthetic topic segments under
existing one-hour retention. It violated the preservation requirement above;
later technical success cannot relabel that failure. [ADR-0019](0019-isolated-checkpoint-broker.md)
records separate storage, alternatives, cost and rollback for subsequent bounded
experiments. Original-scope acceptance remains failed, with no M3 acceptance.

## Two-input idleness follow-up, 2026-10-22

The maintainer authorized the next idle/resume checks. The bounded
two-input experiment reuses the installed matrix,
bundled loopback source, canonical gate, managed operator and unchanged reference.
Two independent generators before union demonstrate active-input minima,
30-second idle exclusion, late/duplicate dispositions on resume, monotonic
progress and no EOF during all-input silence. Five exact windows and ten
identities match the reference; terminal timers clear all active identities.

This adds test modules, two loopback listeners and one bounded controller thread,
not a framework, service, dependency or durable-state migration. Existing
admission/operator/reference logic is unchanged. Retain separate source/check
snapshots and timing-sensitive repeated runtime observations. These author
checks do not claim restricted independent review. Kafka partition/connector
idleness, rebalances, persistent recovery, measured resource limits and M3
acceptance remain open. The earlier historical preservation failure stays failed.

## Persistent bounded acceptance, 2026-10-22

M3 is now accepted for the bounded local synthetic profile.
[ADR-0022](0022-persistent-m3-completion.md) adds separate Compose-owned session
services and original filesystem checkpoint restore.
[ADR-0023](0023-bounded-kafka-enumerator-backport.md) records the stock 5.0.0-2.2
cold-completion defect and exact locally maintained enumerator repair. The
PyFlink API/runtime matrix stays pinned; stock compatibility success is not
reclassified as successful cold recovery. Source contracts/reference behavior
remain unchanged. Real-source adoption, hosted CI, external sinks, production
capacity and host/disk-loss durability remain separate gates. The original
historical retention/preservation failure stays failed.
