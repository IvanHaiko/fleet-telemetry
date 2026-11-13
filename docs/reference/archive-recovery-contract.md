# Archive coverage and expired-offset rebuild contract

## Status and scope

Proposed M4 acceptance contract, 2026-10-22. This defines the next archive
implementation boundary under [ADR-0002](../adr/0002-archive-and-serving.md).
The graph/coordination increment now implements callable
graph verification, finite coordination and fresh file reconstruction. No
concrete Kafka archive command or actual expiry scenario is established by it.
The M4 foundations now accept the bounded local byte-storage
adapter and observation codec; those do not establish the recovery scenario
below. [ADR-0021](../adr/0021-bounded-archive-format.md) and the
[bounded v1 design](archive-format-v1.md) now propose physical encoding, public
interfaces, finite catalog sealing and a backend/client candidate. Full archive
adoption and independent recovery acceptance remain pending; the final
S3 target is selected in the dated follow-up below. Bounded synthetic M3 is
accepted; archive/rebuild, serving and production remain open.
The subsequent bounded Linux runtime, under
[ADR-0027](../adr/0027-bounded-archive-runtime.md), now demonstrates this contract's
tiny local publication/commit and Kafka-off expiry reconstruction scenario.
Earlier increments retain their original narrower scope. Serving and production
failure-domain/capacity/response gates remain open.
The [production recovery gate](../guides/production-recovery-gate.md) owns capacity,
remaining-time monitoring, response and the evidence ledger.

The first executable scenario must use tiny authored synthetic records, a fresh
isolated Kafka profile and separate archive storage. Historical broker volumes,
topics, checkpoints and receipts are protected inputs, never test targets. A new
storage service still requires its distribution/version, security, maintenance
and compatibility review. ClickHouse adoption is a separate M4 decision.

[ADR-0020](../adr/0020-bounded-tests-and-s3-archive.md) subsequently selects Amazon
S3 as the final deployment archive target. Local tests stay at approximately
10-50 GB at most, with a conservative 50 GiB retained-Kafka-data planning ceiling;
this restore scenario still uses a tiny fixture. Local backend/format/client
runtime/expiry integration remains pending; storage/codec foundations and the
subsequent bounded graph/file-reconstruction checks are recorded separately. The selection creates no cloud resources.

## Failure boundary and source of truth

An archive qualifies for the tested Kafka-loss boundary only when its objects,
manifests and recovery catalog survive removal of the tested Kafka data and can
be read using an independent recovery process. A directory, named volume or
bucket name alone proves no independence. Record actual hosts, devices/mounts,
credentials, lifecycle policies and administrative deletion paths. A separate
volume on the same host may prove broker-volume independence; it cannot prove
host-loss recovery. Production evidence must name the supported failure domain
and demonstrate an off-host copy when host loss is in scope.

Preserve both original source bytes with provenance and observed transport
records. Source re-normalization can reproduce stable measurements but cannot
prove the original Kafka observation history. Original local converter outputs,
producer ACK receipts, post-expiry broker copies and Flink checkpoints do not
substitute for the observation archive.

## Required record and manifest semantics

These are logical requirements; the proposed physical batch format and versioned
reader interface are specified in [bounded archive v1](archive-format-v1.md).
Freeze the reviewed contract and independent executable acceptance inputs before
implementation; the public design alone is not a frozen test suite.
The [data contract](../data-contracts.md#archive-and-rebuild-identity-boundary)
owns the distinction between observation identity and measurement identity.

| Evidence | Required meaning |
| --- | --- |
| Observation key | Original cluster ID, topic UUID, topic name, partition and offset; same name after recreation is a different history |
| Original record | Exact nullable key and value bytes, ordered headers including repeated names and nullable values, Kafka timestamp and timestamp type; null and empty bytes differ |
| Measurement link | Event identity and source manifest when parseable; malformed observations still retain their original bytes in restricted storage |
| Batch integrity | Format version, immutable object identity/version, byte length, SHA-256 of stored bytes, record count, exact observation keys and declared half-open ranges |
| Source lineage | Original source/manifest hashes, contract and normalization versions, source run and rights/privacy classification; references must remain resolvable after Kafka loss |
| Durable receipt | Object and manifest identities/hashes, writer version, coverage, completed independent readback result and time; a successful PUT or listing is insufficient |
| Recovery catalog | Versioned, checksummed inventory sufficient to locate and validate receipts and objects without Kafka or an ephemeral writer cache |

Binary encoding must be lossless, including empty and null values; decoded
canonical JSON is not a replacement for original bytes. Archive access may be
restricted, but headers cannot be silently omitted or redacted while claiming
exact restoration. A privacy derivative needs separate lineage and checksum.
Checksums detect corruption relative to trusted manifests; they do not
authenticate a catalog that an attacker can rewrite together with its objects.
Record catalog protection and independent receipt retention accordingly.

All intervals are half-open and partition-specific. For the first fixture use
one non-transactional, delete-policy partition with known contiguous data
offsets. Let `S` be its declared first offset and `U` the captured exclusive end.
The independent oracle enumerates every expected observation in `[S,U)`.
Coverage is the union of verified observation keys, never `max(offset) + 1`,
object count, committed progress or equal record counts alone.

Overlapping batches are allowed only when every repeated observation key has
identical original record content. Different bytes, headers or timestamp at
one observation key invalidate coverage. Equal `event_id` at different offsets
is a repeated measurement observation and must remain in the archive.
Compaction, transactions/control offsets, multiple partitions and rebalances
need explicit coverage rules and additional boundary evidence before support;
do not extrapolate contiguous-offset assertions to them.

## Publication, readback and restart ordering

The writer uses a consumer group independent of processing and serving. Auto
commit is disabled. For a finite batch:

1. Validate source identity, assigned interval and declared size/count bounds.
2. Write the immutable object without replacing different content. Resolve an
   ambiguous write acknowledgement by reading and hashing the actual object.
3. Read the entire object through the storage read API, verify its bytes and
   parsed observation content, then publish/verify its manifest and receipt.
4. Read back manifest/receipt and make them discoverable through the durable
   catalog. Verify the catalog through a fresh reader, not a writer cache.
5. Advance archive progress only to the end of contiguous verified coverage.
   Commit that next offset; verify ambiguous commits through observed progress.

The proposed first v1 profile uses the entire captured finite interval as its
commit unit: no partial batch progress is committed. Its sealed catalog, full
fresh-process readback and externally retained trusted recovery descriptor must
exist before committing `U`. This satisfies the ordering above conservatively;
it does not specify incremental or concurrent archival. See the format design
for exact receipt/catalog references, retry behavior and resource bounds.

A crash before step 5 may produce repeated observations. An object without a
receipt is an orphan, not coverage: restart must read and validate it before
repairing catalog/receipt or use a fresh immutable object. A receipt without
readable matching bytes is invalid and blocks progress. Restart must detect a
committed offset beyond independently verified coverage; it must not infer
that Kafka commits establish archival success. An exact retry is idempotent;
different content under an existing identity fails visibly.

Readback at write time establishes that moment's observation. Periodic audits
and restore drills must have a declared freshness limit; a stale successful
receipt does not establish continued readability. Bound object/batch sizes,
catalog scanning and retry time before any unbounded runtime is admitted.

## Recovery modes and refusal rules

Normal checkpoint recovery and isolated archive rebuild are separate operator
choices. Neither may silently fall through to earliest/latest or a fresh group.
Resolve and verify cluster/topic identity before interpreting an offset.
Missing identity, checkpoint, receipt, credentials, catalog or readable object
is a failure or explicitly unknown state, never an empty successful input.

For every source partition, normal recovery needs checkpoint next offset `K`,
declared recovery endpoint `U` and fresh retained interval `[L,H)` with
`L <= K <= U <= H`. An endpoint equal to `H` is valid; it needs no record at `H`.
If `K < L`, `K > H`, or required suffix/identity is missing, refuse before
launching the job or publishing success. Report required, retained and missing
intervals with a safe reason. Keep checkpoint, group offsets and outputs
unchanged. A missing committed offset also requires explicit initialization,
not the client's default reset policy.

The preflight snapshot cannot reserve Kafka data. The actual client/connector
must disable automatic reset and treat later out-of-range/truncation and
unexpected gaps as failures. Test loss between preflight and first fetch as
well as loss at restart. Verify this on the actual Flink connector before
claiming production checkpoint recovery; the bounded M2 client guard does not
establish it. Do not advance committed progress over unprocessed missing data.

Archive coverage may make a separate rebuild possible; it does not turn the
refused checkpoint restart into a success. Rebuild validates the entire chosen
archive interval, source manifests and checksums before publishing a complete
result into a new dataset run and target namespace. Do not transplant an old
Kafka checkpoint into a new cluster/topic whose offsets mean something else.
The first scenario rebuilds the whole finite interval, avoiding an untested
live/archive handoff or partial state merge.

Retain original observation coordinates as lineage. Original bytes stay
immutable. If replay changes delivery metadata, record that transformation and
compare measurement identities and the pinned semantic projection separately
from archived byte hashes. External run metadata/target selection must isolate
even a replay that preserves original delivery bytes. No result from the new
run is added to the original run without a separately reviewed migration.

## Required expiry and restore scenario

This is an acceptance recipe, not an executed result or authorization to alter
historical storage. The future harness must own a fresh bounded profile,
finite deadlines and shutdown on success/failure; retain its evidence stopped.

1. Freeze the public contract, tiny synthetic input and independent expected
   identities/content before exposing the candidate in the strict workflow.
   Include at least one repeated measurement at a different Kafka offset and
   byte-sensitive header/null/empty cases at the archive boundary. Retain exact
   runtime/config/source hashes and the scope allowed for the candidate.
2. Publish the finite input once. Capture original cluster/topic identity,
   offsets, exact observed record bytes and committed progress independently.
   Archive `[S,U)`, including sources/manifests; verify full readback using a
   fresh process with no writer-local cache or source-output fallback.
3. Exercise object-before-receipt, receipt-before-commit and commit-ACK ambiguity
   crashes. Reconcile exact observation keys after retry and changed batching.
   Reuse one oracle; overlaps must not hide a hole or conflicting observation.
4. On this disposable topic only, let controlled time retention make `[S,U)`
   unavailable. Observe `L >= U` while identity remains unchanged. This proves
   source offsets are unavailable, not physical secure erasure. Leave historical
   profiles stopped and unchanged. Do not use topic recreation as expiry proof.
5. Request normal recovery from `S`. Require nonzero exit with missing interval,
   no reset, unchanged original group/checkpoint/receipts and no success output.
   Repeat with the gap arising after preflight; exercise the actual consumer
   error path, not only a mocked interval guard.
6. Stop/isolate the source broker. A fresh recovery process with no source Kafka,
   original converter-output or oracle access reads only archive/catalog and
   declared recovery configuration. Rebuild into a fresh run/namespace. A separate
   verifier uses the frozen oracle to reconcile every observation and stable
   measurement plus the declared bounded reference result. Original source
   regeneration is a different experiment; the oracle cannot be a recovery input.
7. Independently remove access to one required object, then test checksum
   corruption, missing receipt/catalog entry, a coverage hole and conflicting
   overlap on disposable archive copies. Each must fail without publishing a
   complete dataset or advancing old progress. Restore test copies, not originals.
8. Retain exact commands, exits/timeouts, before/after identities and progress,
   hashes, missing/extra/conflict sets, archive placement/access evidence and
   final stopped runtime state. Complete the restricted read-only review.

A local success permits only the tested broker-data-loss/readback/rebuild claim.
Production additionally needs the failure-domain, workload, retention, response
and operational ownership evidence in the production gate. It does not repair
the earlier historical preservation failure or establish analytical sink safety.

## Remaining decisions and next implementation

The [v1 proposal](archive-format-v1.md) specifies JSONL/base64 observation bytes,
content-addressed manifests/receipts, a sealed finite catalog, public operations
and refusal limits. The foundation increment accepts the
pinned SeaweedFS 4.48/SDK boundary and pure observation codec after frozen tests,
read-only review and deterministic acceptance. Those foundations alone do not validate a catalog or certify links. The
subsequent graph increment now checks them with independent
frozen inputs and implements finite coordination/file reconstruction. The
concrete runtime now executes the bounded Kafka-expiry
scenario with protected roots, fresh S3 fetch and isolated reconstruction.
Serving and production recovery remain separate.

Rollback of the original documentation increment restored its scoped baseline;
it performed no persistent format, service, configuration or stored data changes.
The current foundation guide owns the subsequent local rollback boundary. A future archive
format needs its own migration/rollback policy before persistent adoption.
