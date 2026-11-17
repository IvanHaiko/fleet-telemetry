# Refactoring the local telemetry platform

Maintenance plan, 2026-11-18. Work proceeds in four stages. The first
deliverable is a recording Flink image that can be built on a fresh engine.
The [roadmap](roadmap.md) tracks product milestones and MVP acceptance.

## Starting point

The recording profile adopted the verified image in
[ADR-0061](adr/0061-recording-flink-image.md). F09 checkpoint recovery and
SITL archive reconciliation both passed. The profile inventory and selected
code changes are recorded below. The
[test review](testing-strategy.md#refactoring-checks-18-november-2026)
records execution lanes, timings, skip reasons and the Linux runner repair.

The 17 November audit covered 323 Python files. It found 34 owned modules
of 400–499 lines, including nine test modules and nine scenario scripts.
Reachability from the recording profile alone misses the starter, dynamic
entry points, image builds, recovery probes and documented experiments.
Use that inventory to find candidates and check each one's callers.

Local changes on the audit branch already describe image ownership, retain
the 499-line maximum, remove two unused service lists, and give snapshot
accessors public names. The live worker fell from 410 to 320 lines after the
archive gate used by serving and reconciliation moved into its own module.
Recording and live workers now share SQL connection configuration. This
leaves 33 modules in the 400–499 range. The offline M4 checks are wired into
the Linux synthetic CI job. Local checks ran on Windows; the hosted result
is pending. Carry these changes forward and verify them in their target lanes.

## 1. Replace the recording Flink image and retire obsolete images

1. Inventory exact digests used by Compose profiles, Dockerfile parents and
   retained runs that still require restoration. The recording chain is
   `kafka-probe:4.4.0 → pyflink-m3:2.2.1-local1 → pyflink-m3:2.2.1-local2`.
   The recording broker runs the official Kafka image. SeaweedFS serves the
   archive. The root starter uses its own Flink image. See the
   [current inventory and recipes](guides/f09-single-machine-run.md#which-local-images-to-keep).
2. Build one multi-stage `recording-flink` image for both JobManager and
   TaskManager from pinned upstream inputs. Remove the Kafka broker base.
   Preserve Python, JDK, PyFlink and connector versions, the enumerator fix,
   required launcher utilities, notices, runtime paths and non-root identity.
   Keep compilation and the connector regression probe in the build stage.
   Record the new base, lock inputs, digest and rollback pin in the runtime
   decision and runbook. [Original runtime](adr/0022-persistent-m3-completion.md)
   and [connector repair](adr/0023-bounded-kafka-enumerator-backport.md).
3. Build on a fresh engine without the project-local parent images. Check
   imports, launcher and connector probe. In a fresh recording run, compare
   archived inputs and query-visible identities and content against the
   reference. Restart the TaskManager and reconcile again. Exercise the live
   or fleet path that shares the image. Record commands, results and limits.
4. Switch Compose to the verified digest. Keep the previous digest available
   for rollback and demonstrate how to restore it. For each old image record
   **retire**, **retain for a named consumer**, or **retain for rollback**.
   Remove a specific obsolete local image only after its last dependency
   and rollback obligation have ended and cleanup is authorized. Keep
   SeaweedFS while the archive depends on it. Preserve data volumes,
   checkpoints and failed-run evidence throughout.

**Done when** a fresh build and recovery run pass, the runbook reproduces
them, and every old image has either been retired or has a documented owner
and reason to remain.

## 2. Resolve the audit findings and historical profile ownership

- Classify M2–M6 profiles, position/MAVLink observers and F09 research scripts
  as supported, shared by a supported path, or historical. Check CLI, CI,
  Compose, Docker build contexts, guides and recovery dependencies. Record the
  last reproducible revision and required external artifacts before retiring a
  profile. A source revision alone cannot restore an unpublished image.
- Recheck unused candidates such as `by_profile`, `READER_VERSION`, the
  F09 limit aliases and the S3 deletion protocol method. Remove confirmed
  internal leftovers. Review public imports and test-only recovery helpers
  individually. Preserve historical evidence and update navigation when an
  entry point is retired.
- Trace repeated signatures, file hashes, Kafka/MAVLink protocols and strict
  JSON parsing in supported paths. Consolidate equivalent contracts, preserving
  duplicate-key handling, non-finite number rejection and caller-specific error
  reasons. For shared private names in ClickHouse, archive and stream preparation,
  choose a public owner from the actual callers.

**Done when** each finding has a disposition and rationale, supported entry
points still resolve, and each cleanup passes its existing behavioral checks.

### Profile and code inventory, 18 November

| Consumer | Maintenance disposition |
| --- | --- |
| Root starter and recording, live SITL and fleet operators | Supported. The starter has its own Dockerfile. The three operator paths share the recording Compose definition, archive services and Flink image. |
| M2 broker | Supported synthetic regression profile. The manual M2 workflow builds Kafka and runs the native matrix. |
| Persistent M3 and M4 | Shared runtime and recovery evidence. Keep the M3 scripts, connector recipe, M4 archive/serving checks and historical Compose overlays for the accepted synthetic milestones. |
| M5 and M6 | Historical scenarios for checkpoint, rebalance, late data and measured load. Keep the scripts, configuration, synthetic fixtures and documented run commands alongside the case studies. The M6 benchmark still has an open milestone. |
| Position, link-watch, MAVLink observers and F09 research views | Historical launchers. Shared recording inspection, admission, stream preparation and replay code remains supported through the operator CLI. Keep the experimental entry points with their guides. |

No profile is retired in this review. Source baseline
`78f609f2ab290d7ab7bf7a625c37fc9c7e0c4d00` identifies the pre-refactor
recipes. Reproduction also requires each guide's private inputs, package
directory, pinned images and, for restart runs, retained volumes. The
[image inventory](guides/f09-single-machine-run.md#which-local-images-to-keep)
records image ownership.

Repository-wide reference checks found no caller for `by_profile`,
`READER_VERSION`, the two F09 limit aliases or the S3 protocol's
`delete_object` method. The registry still owns the limits and the
reader still validates its versioned contract. The fleet operator now
uses the preparation module's streaming file digest. Recording and live
content signatures retain different representations for offline comparison
and checkpoint state. MAVLink capture requires raw frame bytes and sequence
numbers, while the observer uses a timed receive; their protocols remain
separate. The archive codec owns the common integer-only JSON decoder.
Document and JSONL callers keep their respective size, schema and canonical
encoding checks. The battery reader and serving parsers have different
numeric or refusal contracts. SQL read settings, serving decimal and JSON
encoding, and prepared-stream verification have public names at their owners.

## 3. Refactor production code by responsibility

Keep the existing maximum of 499 physical lines. Review modules approaching
400 lines when changing them. Prioritize mixed responsibilities, long control
flow and duplicated decisions. Track both module size and function size.

| Priority | First change to investigate | Evidence to preserve |
| --- | --- | --- |
| Prepared recording verification | Separate battery reconciliation from the 264-line `_verify_prepared` in `runtime/flight_analytics/stream_source.py`. Keep the cumulative artifact byte budget with its caller. | Identical accepted rows, hashes, counts and refusal reasons for altered artifacts. |
| Recording and live serving | Explain the different cursor partition and offset checks before sharing any poll, flush or commit logic. | Archive gating, restart at the acknowledged cursor and duplicate-safe SQL results across the write/cursor failure window. |
| ULog and live ingestion | Inspect the framing loop in `ulog_integrity.py` and the live position worker. Extract phases with clear inputs and outputs. | Parser bounds, measurement time, identity, units and rejected-input behavior. |
| Cross-layer imports | Move shared Kafka types out of M3 scripts. Review dependencies from `telemetry` into runtime storage and flight analytics. Trace facade and root CLI callers before moving modules. | Existing public imports, optional-dependency boundaries and documented `python -S` commands work. |
| Maintained scenarios | For surviving profiles, split setup, execution and reconciliation in `run-slice.py` (388-line function) and `check-m5-late.py` (374-line function). | Same failure reporting, scope ownership and independently computed results. |

**Done when** each selected change reduces a concrete reading or maintenance
cost, its normal entry point passes, and the relevant contract and recovery
checks still hold. Review one coherent path at a time.

The selected increments separate battery reconciliation from prepared-stream
verification, bounded frame iteration from ULog interpretation, and Kafka SDK
protocols from the M3 scenario harness. The M3 module re-exports its existing
names. Preparation keeps the cumulative byte budget across every artifact.
Its main verifier now spans 150 lines and its battery check 122. A fresh
preparation of the same F09 interval reproduced all three bundle files
byte-for-byte. Altering the battery semantic digest in a separate inspection
copy gave `stream_battery_reconciliation` in both revisions.

The serving workers already share the SQL-before-cursor ordering through
`ServingBatch.flush`. Recording validates the full partition set on loading
its cursor and bounds each physical output offset against twice the delivery
limit. Live uses its own archive-derived gate and checks the next offset per
partition. Preserve their poll and completion loops. The archive modules
share the storage error type, and recording processing imports the reviewed
state fields and values from flight analytics. Both boundaries still load
in the supported CLI paths. The position-only worker and the M4/M5
case-study runners remain historical; restructuring their scenario control
flow was outside the selected production paths.

## 4. Review the test suite and remove demonstrated redundancy

Use the [testing strategy](testing-strategy.md) to map test groups to a
supported profile, observable invariant, failure mode and execution lane.
Record **keep**, **merge**, **remove with retired profile**, or **repair lane**.
For each removal, name the surviving test that catches the same defect at the
same boundary, or the retired behavior that made the assertion obsolete.

- Start with tests for historical profiles and repeated fixtures or assertions.
  Compare inputs, failure windows and expected outputs before merging. Keep
  independent reference calculations and boundary tests that detect different
  failures. The audit found no clear class of trivial getter tests.
- Review Kafka scenarios embedded in subprocess strings, mock call-count
  assertions and PyFlink imports from root test modules. Preserve subprocess
  isolation where interpreter startup or optional dependencies are under test.
  Check the upstream contribution's checksum manifest before touching its
  duplicate UUID regression fixture.
- Check optional Kafka and ClickHouse skips, Linux-only PyFlink coverage and
  offline M4 discovery. List the command and environment that actually execute
  each retained group. The M4 runner discovered 107 tests locally, with seven
  skipped on Windows. Verify the Linux lane and report actual skip reasons.

**Done when** removals have a traceable rationale, the retained suite exercises
the declared invariants, and before/after results report executed tests,
skips and runtime per lane. Test count is an outcome of the review.

### Files in the maintenance increment

| Area | Files |
| --- | --- |
| Image build and selection | `compose/recording.yml`, `runtime/pyflink/container/Dockerfile.recording`, `connector-image-pin.json` and `recording-inputs.sha256` in that container directory |
| Operator and transport | `runtime/recording/profile.py`, `sample_resources.py`, `fleet.py`; `telemetry/kafka_protocols.py`, `scripts/m3_transport_types.py`, `runtime/continuous/kafka.py` and `generate.py` |
| Archive, registry and reader | `telemetry/archive_codec.py`, `archive_documents.py`, `recordings.py`; `runtime/s3/boto_transport.py`, `telemetry_reader.py` and `ulog_integrity.py` |
| Preparation and projection | `runtime/flight_analytics/stream_source.py` and `stream_prepare.py`; `telemetry/serving_projection.py`; `runtime/continuous/recording_sql.py`, `recording_initialize.py`, `gold.py` and `verify.py`; `runtime/pyflink/continuous_operator.py` |
| Checks and their callers | `scripts/check-m4.py`, `benchmark-transport.py`, `check-m5-late.py`; `tests/test_gold_overview.py`, `test_gold_position.py` and `test_recording_stream_prepare.py` |
| Earlier audit-branch changes | `runtime/continuous/live_worker.py`, `live_archive_gate.py`, `live_reconcile.py` and `recording_config.py`; `runtime/recording/ops.py`, `ops_view.py`, `health_signals.py` and `stall.py`; `tests/test_live_serving_gate.py`; `.github/workflows/m1.yml`, `CONTRIBUTING.md` and `docs/README.md` |
| Evidence and decisions | This plan, `docs/architecture.md`, `docs/testing-strategy.md`, `docs/guides/f09-single-machine-run.md`, `docs/guides/operations-runbook.md` and `docs/adr/0061-recording-flink-image.md` |
