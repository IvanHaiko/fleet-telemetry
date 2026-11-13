# ADR-0023: Candidate bounded Kafka enumerator backport

**Status:** Accepted only for the bounded local synthetic M3 profile on
2026-10-22 after real cold completion, full runtime/resource checks and restricted
final review. The acceptance guide owns scope
and retained evidence. This is a local maintained derivative, not an Apache release.

## Problem and evidence

The stock SQL Kafka connector 5.0.0-2.2 restores source offset 3 and managed
prefix state after cold session-cluster restart, consumes through stopping
offset 9, but never completes. The retained `targeted-007` attempt hits its
completion deadline and stops owned services. TaskManager-only recovery passes.
This matches [FLINK-31006](https://issues.apache.org/jira/browse/FLINK-31006)
and the open [upstream PR 318](https://github.com/apache/flink-connector-kafka/pull/318):
the recreated bounded enumerator skips an empty discovery change and fails to
signal no more splits. It is not missing application data or a proven runtime
capacity problem. The unmodified failure remains retained.

## Candidate and alternatives

Investigate a narrow backport to the exact existing 5.0.0-2.2 artifact. Retain
its hash, released source provenance, exact source patch, compiler/classpath
inputs and resulting class/JAR hashes. Reuse the installed pinned JDK and SDK
libraries offline; install no compiler, Maven or new dependency. Preserve the
installed original runtime and JAR. Never synthesize EOF, append control records,
change finite bounds, enable discovery as a workaround, discard restore state,
or weaken the FINISHED/reference criterion.

The candidate may change only the enumerator's empty-change guard for bounded
one-time discovery. Periodic discovery/unbounded behavior, per-record logic and
state serializers must remain unchanged. A locally rebuilt connector is a
project-maintained artifact, not an official Apache release. Adoption requires
an explicit new image/JAR pin, full byte-change inventory, offline class-level
checks and real repeated failure/restore observations. Compilation or provenance
mismatch fails closed; a partial or unexplained binary rewrite is insufficient.

Alternatives are waiting for a released compatible fix, rebuilding the complete
upstream module with its larger dependency/toolchain boundary, or choosing a
separately reviewed connector/API matrix. None has been adopted. Manual source
completion or relabeling a running job as success does not satisfy M3.

## Cost, migration and rollback

The repair adds one pinned patch/build recipe and its maintenance obligation,
plus a new local image layer. Existing source payloads, package locks and
historical images/volumes stay unchanged. No cloud or archive service is added.
Recheck the release/source/license and ABI boundary on every upgrade; replace
this backport with a tested upstream release when available. No serializer
format migration is intended; actual checkpoint restore must prove compatibility.
Rollback stops only the fresh candidate project and selects the original image,
retaining all source, failed runs and checkpoint bytes. Do not deploy this
candidate to shared infrastructure or remove persistent storage under this task.

## Adopted artifact and demonstrated boundary

The pinned released source is commit
`2960af0eb26dfac3e224f5edf1db6f867888c62f`, file SHA-256
`0b27ea0d45614eeda375148d56da13c8c13137eb353bc490866768e6eff57cce`.
The exact offline guard and 469 compiler/classpath input hashes are recorded in
[connector-backport.json](../../runtime/pyflink/connector-backport.json).
JDK 17 compiles to the original class major 55. Two builds reproduce JAR SHA-256
`01d49d99e184229f80da2cf674d3843ca9419ec7542f36f57205a8bf43885497`,
including an independent parent execution in a read-only sandbox. Five
enumerator-family class entries change; all other records/metadata/licenses
and state serializer bytes remain unchanged, with identical private/public ABI.

The actual class callback regression fails on the stock JAR and passes after
the repair while preserving six periodic/unbounded negative combinations.
This is not broker or restore evidence. Real cold runs `cold-009` and the full
`live-010` cycle both restore original checkpoint/source/managed prefix state
and reach actual FINISHED with exact reference results. The full cycle also
repeats TaskManager failure, two partition lanes and measured state refusal.
The new image is pinned in Compose; the old image/JAR and failed stock run remain
retained. Do not broaden this result to dynamic subscriptions, production
capacity, arbitrary upgrades or disaster recovery.

The accepted cycles create and restore checkpoints with the pinned repaired
image. An in-place stock-to-repaired checkpoint upgrade was not executed;
historical state was not migrated. Unchanged serializer bytes do not replace
a dedicated upgrade test.
