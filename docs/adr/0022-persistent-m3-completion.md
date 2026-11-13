# ADR-0022: Isolated persistent runtime for bounded M3 completion

**Status:** Accepted for bounded local synthetic M3 on 2026-10-22 after the
actual acceptance checks, retained failure
analysis and restricted final review. The maintainer authorized this scope by
instructing completion of M3. ADR-0023 owns the required narrow local connector
repair. This does not waive the historical preservation failure.

## Problem and scope

The previous independent-worker checkpoint experiment ran inside a transient
MiniCluster. Two loopback inputs subsequently demonstrated idleness, but not
Kafka partition lanes. Neither establishes persistent TaskManager recovery,
cold runtime restart or measured JVM/Python/container resource bounds.

Complete those remaining local synthetic gates using one fresh Compose project:
the existing Kafka 4.4.0 image, separate standalone session JobManager and
TaskManager, and a short-lived submission client. Filesystem checkpoints and
bounded diagnostic evidence survive container replacement on a new shared volume.
Use two slots for the two-partition lane experiment, and one operator lane for
the existing small recovery/reference fixture. No archive or analytical sink is
introduced. AWS, host-loss durability, HA and end-to-end exactly-once remain out
of scope. The original historical preservation attempt remains failed.

## Runtime and image decision

Reuse the installed, separately locked Python 3.12.13, PyFlink 2.2.1, Temurin
17.0.20.1+1 and SQL Kafka connector 5.0.0-2.2. Build a new local image from the
recorded existing Kafka image ID
`sha256:676a930ab90762c2c32ef79642ad2293c18e5cea96381fc72af54e51fb3cd1c3`.
Its checked [base recipe](../../runtime/kafka/Dockerfile) uses digest-pinned
Temurin 25; override Java with the exact copied JDK 17 and verify the actual
version. The inherited Kafka payload/Java 25 are unused in Flink services.

Only allowlisted Python/JDK/venv/connector bytes enter the build context. Record
regular-file hashes, symlink targets, executable modes, installed package graph,
original artifact/lock references, build recipe and resulting image ID. Exclude
caches, runs, credentials and old diagnostics. Preserve the installed absolute
runtime prefix initially to avoid silently breaking venv links. Verify imports,
native libraries, Java, config parsing and CLI before starting a cluster. No
package resolution, network installation or image pull belongs in that build.
An incompatibility requires a retained failure and reviewed alternative.

The [official standalone Docker guide](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/resource-providers/standalone/docker/)
supplies the session-cluster shape; this is a project-owned image, not an official
Flink image. The final runtime pin must identify its measured image digest/ID.

### Launcher prerequisite discovered during preflight

The initial image verifies all 14,625 reused runtime files/native imports, but
the bundled launcher also requires `rev`, absent from the minimal base. Its
Java-version check emits command-not-found errors even when CLI help exits zero.
Do not accept that exit alone. Include only the existing Ubuntu `bsdextrautils`
2.41.3-3ubuntu2.2 `rev` binary, SHA-256
`f393e3705cefcd00121f71c58c587c6bb431c0737dac526007594da3754225aa`, and its
copyright/GPL-2 notices as separately hashed build inputs. Verify its ABI and
clean launcher execution in the image; install no package on the host and patch
no Flink script. The [Ubuntu package inventory](https://packages.ubuntu.com/resolute/all/bsdextrautils/filelist)
confirms ownership. This adds one small pinned OS utility and its maintenance
obligation. Alternatives are a larger base/package installation or maintaining
a custom replacement utility; neither is needed for the local offline route.

## Storage, security and limits

Use a new Kafka cluster ID, named volume and topic/group namespace; never start
the historical profiles or adopt their seven-day storage. New ordinary topics
must read back `cleanup.policy=delete`, `retention.ms=-1`, `retention.bytes=-1`
before publication. Admit only tiny predeclared input and explicit disk/copy
budgets. Retain all volumes and failed attempts; no destructive cleanup.

Expose host Kafka 19092 and REST 18081 only on loopback. Containers use Kafka's
existing `kafka:9092` internal listener and private service names. Run non-root,
drop capabilities, use read-only source mounts and separate new state storage.
Plaintext/no-auth is limited to this trusted local private-network profile;
no shared deployment or credential/TLS guarantee follows. Docker remains an
administrative trust boundary. Compose owns all service start/stop/replacement.

Initial container ceilings are Kafka 1536 MiB, JobManager 1536 MiB and
TaskManager 3072 MiB. Use at most two TaskManager slots and bounded CPU, logs and
temporary storage. Measure actual cgroup current/peak/limit/OOM counters and
Python/JVM RSS over startup, processing, failure and restore. A healthy run must
stay below 90% of its configured cgroup cap without OOM. Input/history guards,
not event-time TTL alone, bound this finite experiment. Larger workloads require
their own admission and capacity evidence.

## Acceptance and independent work

1. Preserve original source, staged state and index bytes; use a disposable index
   for Git inspection. Follow the current external workflow with restricted
   Tester, frozen public tests, restricted implementation and read-only review.
   Observe native permission denials; shared sessions are not blind verification.
2. Run a real two-partition Kafka source with raw metadata/bytes, validation
   before timestamp assignment, source/admission/generator parallelism two and
   observed one-partition-per-generator mapping. Prove the active minimum,
   30-second idle exclusion, late/duplicate resumes, invalid-future isolation,
   no EOF from silence and exact finite reference results. Planned future end
   offsets are not previously captured offsets; independently capture/read back
   the completed finite ranges and verify actual connector EOF afterward.
3. Complete and retain a filesystem checkpoint; independently observe source
   progress and managed prefix state. SIGKILL only the owned TaskManager,
   replace it, and require actual checkpoint/source/state restoration before
   applying the first resumed record. Compare final results with the reference.
4. Stop the owned full runtime, retain/check checkpoint bytes, restart it and
   explicitly resubmit from that checkpoint. Prove restoration through REST and
   managed prefix state even when the new execution attempt counter starts at
   zero. Automatic JobManager failover is not required or claimed.
5. Refuse the next distinct identity at a declared small history limit under a
   stalled watermark. Measure container/Python/JVM memory; distinguish injected
   SIGKILL from OOM. Validate resource headroom and safe shutdown.
6. Reconcile original source bytes/identities, dispositions, windows, expiry and
   all physical replay traces without claiming a transactional diagnostic sink.
   Pass relevant toolchains/tests and the restricted final review. End owned
   services stopped with source, checkpoints and evidence preserved.

Externalized checkpoints require explicit retention and restore configuration;
their mere presence is insufficient. See the pinned
[checkpoint guide](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/ops/state/checkpoints/)
and [TaskManager memory model](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/memory/mem_setup_tm/).

## Alternatives, cost and rollback

- Continue with only MiniCluster/socket tests: insufficient for the remaining
  transport and persistent-process gates.
- Download a new official Flink image/distribution: viable fallback, but duplicates
  installed bytes and adds a Python/dependency packaging task without a need yet.
- Introduce HA coordination, orchestration or object-store checkpoints: additional
  scope with no requirement for this single-host M3 experiment.

Reusing the roughly 1.2 GB installed payload adds a local build context and image
layers, plus small volumes/logs/checkpoints. Account for simultaneous copies and
measured allocation before startup; there is no cloud spend or 50 GiB capacity
claim. Maintenance owns one extra image and a pinned packaging recipe.

Rollback stops only the new Compose project, restores scoped source/configuration
files and leaves old/new volumes and evidence retained. There is no canonical
schema or existing-state migration. Checkpoint UID/serializer changes after
adoption require an explicit state-compatibility/migration procedure. Do not
delete persistent data or publish Git changes as part of rollback.

## Partial identity-evidence supersession, 2026-10-24

[ADR-0026](0026-historical-topic-identity-qualification.md) supersedes only the
historical Windows topic-UUID trust portion of this decision and its supporting
evidence. The read-only audit confirms the SDK's
signed-32-bit narrowing against independently retained broker metadata. Preserve
the original measurements, payload hashes, offsets, reference/recovery results
and their bounded limits; they do not certify missing UUID bits. Affected
identity-dependent receipt reuse needs an explicit reviewed attestation/
migration. The earlier record is retained, not silently rewritten.
