# Bounded archive v1 design

## Status and ownership

Proposed on 2026-10-22 under [ADR-0021](../adr/0021-bounded-archive-format.md).
The observation encoding/offset-union subset and separate byte-storage adapter
are now implemented and accepted in the M4 foundation increment.
The graph/coordination increment implements trusted
catalog/lineage verification, finite publication/progress ports and archive-only
file reconstruction. The subsequent bounded Linux runtime
adds concrete publication/commit, protected roots and actual expiry reconstruction
under [ADR-0027](../adr/0027-bounded-archive-runtime.md). Full M4 and production
recovery remain open. The
[recovery contract](archive-recovery-contract.md) owns recovery invariants;
[data contracts](../data-contracts.md#archive-and-rebuild-identity-boundary) own
measurement/observation identity. No canonical event schema changes here.

## Finite profile and resource admission

Version 1 of this experiment supports one writer, one Kafka cluster/topic UUID,
one non-transactional delete-policy partition and a known nonempty contiguous
interval `[S,U)`. Capture identity and `U` before reading. Refuse compaction,
transactions/control-offset gaps, assignment changes and unsupported metadata;
these require explicit future coverage rules. Do not start historical brokers.

These limits are not measured capacity. The codec implements its applicable
batch/line/coverage limits. The finite coordinator now checks object/body
admission through an inventory port; concrete disk/allocation and process
deadline admission remain runtime responsibilities:

| Item | Maximum |
| --- | --- |
| Unique offsets in `[S,U)` | 32 |
| Observation lines across all catalog batches, including overlaps | 64 |
| Observation lines per batch | 16 |
| Encoded observation line, including LF | 256 KiB |
| Stored batch bytes | 1 MiB |
| Headers per observation / UTF-8 header-name bytes | 32 / 256 bytes |
| Source or original provenance-manifest blob | 16 MiB each; at most four blobs |
| Manifest, receipt, catalog or recovery descriptor | 64 KiB each |
| Batch entries in a catalog | 16 |
| Total objects under the owned archive-run prefix, including orphans | 64 |
| Stored object-body bytes under that prefix, including orphans | 96 MiB |
| Total outer storage attempts per object operation | 3, including the first |
| Connect / read timeout per request | 2 / 5 seconds |
| Whole command deadline, including retries and shutdown | 120 seconds |

The request-attempt row includes the first attempt. Disable hidden SDK retries
(`total_max_attempts=1`); one outer retry policy owns the three-attempt limit.
The parent deadline must end owned children and close streams, including a
slow response that continuously delivers bytes. Fail on a limit before the
write/commit that would exceed it; never truncate an object or ignore a header.

Before publication, budget all simultaneous source, Kafka, archive, scratch,
checkpoint and restore copies on their actual devices. Reserve at least 1 GiB
free **after** the bounded copy estimate, plus measured backend overhead. The
96 MiB body limit does not bound backend allocation. Refuse startup until an
artifact-specific allocation estimate and container memory/CPU limits exist.
One writer excludes concurrent profile publishers; administrators remain a
trust boundary. On retry, inventory only the owned prefix with at most 64
entries plus one overflow sentinel; paginate with bounded requests/deadlines.
Listing is admission accounting, never proof of complete observation coverage.

## Encoding and exact observation content

An observation object is uncompressed JSON Lines. Each line is one JSON object
followed by exactly one LF byte, including the last line. No BOM, blank lines,
CRLF, duplicate JSON keys, NaN, Infinity or unpaired Unicode surrogates. Writers
use Python 3.13 `json.dumps(value, ensure_ascii=True, sort_keys=True,
separators=(",", ":"), allow_nan=False)` plus LF, encoded as UTF-8. Control
documents use the same encoding as a single JSON object plus LF. Integers are
JSON integers, excluding booleans; no JSON floating-point values are needed.
Readers validate the schema and canonical re-encoding. Unknown format versions
or fields fail rather than being silently discarded in this exact format.
Limit parsed nesting to 16 levels and identity/lineage strings to 512 UTF-8
bytes each; object keys remain bounded by their fixed prefix/key grammar.

Required observation fields:

| Field | Type and meaning |
| --- | --- |
| `format_version` | Literal `kafka-observation-v1` |
| `cluster_id`, `topic_id`, `topic` | Nonempty original identity strings; topic ID is the captured Kafka UUID string, never regenerated |
| `partition`, `offset` | Integers in `[0, 2^31-1]` and `[0, 2^63-1]` respectively |
| `timestamp_ms`, `timestamp_type` | Signed 64-bit integer and `create_time`/`log_append_time`, or null and `not_available` together |
| `key_b64`, `value_b64` | Null or canonical RFC 4648 standard padded base64; empty string means zero bytes |
| `headers` | Ordered array of objects with exactly `name_utf8` and `value_b64`; repeated names retained |
| `measurement` | Null, or object with exactly `event_id` and `source_manifest_sha256` |

Header names in the initial profile are strict valid UTF-8 with no normalization;
re-encoding must reproduce the captured name bytes. The adapter must prove this
for the selected client; refuse names/metadata it cannot losslessly expose.
Binary header values follow the same null/empty/base64 rule. Never decode original
value JSON and then serialize it as the archived value. Tombstones, invalid event
JSON and repeated measurements remain observations, with `measurement=null` when
not independently admissible. A non-null measurement link must pass the current
canonical reader and reference an archived source manifest; it supplies no
alternate observation identity. Errors reading metadata block that observation.

Within a batch, sort by original offset, with each offset occurring once.
Across batches, overlaps are permitted only if **all** observation fields agree.
Compare canonical observation-line bytes; changes in headers or Kafka timestamp
are conflicts even when the measurement identity agrees. Exactly enumerate
`[S,U)`; equal counts and a maximum offset cannot establish coverage.

## Objects, references and trust root

Use an explicit isolated bucket and prefix `archive-v1/<archive_run_id>/`.
Run IDs match `[a-z0-9][a-z0-9-]{0,63}`. All referenced keys must be relative to
that exact prefix; reject arbitrary endpoints, absolute paths, traversal or
cross-bucket references. Do not derive key paths from untrusted topic names.

An `ObjectRef` has exactly `key`, `sha256`, `byte_length`, `version_id`.
The digest is `sha256:` plus 64 lowercase hexadecimal digits over the complete
stored body, including LF for JSON. Length is a positive bounded integer;
source blobs may be empty and have length zero. `version_id` is null for the
first non-versioned profile. A future versioned profile must fetch the named
version and test its lifecycle. ETags are diagnostic, never SHA-256 evidence.

| Object | Key relative to the run prefix | Required document fields |
| --- | --- | --- |
| Source/manifest blob | `sources/<sha256-hex>.bin` | Exact original bytes, not a new JSON wrapper |
| Observations | `batches/<sha256-hex>.jsonl` | Observation lines defined above |
| Batch manifest | `manifests/<sha256-hex>.json` | `format_version=archive-batch-manifest-v1`, `archive_run_id`, `source`, `start_offset`, `next_offset`, `record_count`, `observations`, `lineage` |
| Readback receipt | `receipts/<sha256-hex>.json` | `format_version=archive-readback-v1`, `archive_run_id`, `writer_version`, `manifest`, `verified_at`, `readback_method=full_get_sha256` |
| Sealed finite catalog | `catalog.json` | `format_version=archive-catalog-v1`, `archive_run_id`, `source`, `start_offset`, `next_offset`, `lineage`, `batches` |

`source` has exactly `cluster_id`, `topic_id`, `topic`, `partition`. A manifest's
interval is nonempty, has no internal hole and contains exactly `record_count`
observations of that source. `observations` is its batch `ObjectRef`. `lineage`
is an ordered array of entries with exactly `role` (`original_source` or
`source_manifest`), `object` (`ObjectRef`), `source_log_id`, `schema_version`,
`normalization_version`, `source_dataset_run_id`, `privacy_classification` and
`semantic_projection`. These nonempty lineage strings must agree with the
archived source manifest and canonical events; `source_log_id` must also equal
the original source blob's SHA-256. At least one source/manifest pair is required;
each blob must be referenced, and four total blobs remain the upper bound.
Lineage arrays are sorted by role then object key and have no duplicates.
All catalogs/manifests in one run use identical lineage, including source pairs
without an admissible observation. Original manifests retain rights/provenance
evidence; unsupported or unresolved lineage fails admission rather than being
filled from a current network lookup. Synthetic is the only initial privacy
classification. This does not accept a real ULog source. The current
[graph interface](archive-graph-interface.md) pins the original synthetic
`bounded-conversion-v1` job bytes as the provenance blob, retaining registration,
rights and original delivery context without opening its embedded paths.

`manifest` in a receipt is an `ObjectRef`. `verified_at` is UTC RFC 3339 with six
fractional digits and `Z`, recording full GET completion. It does not enter
measurement identity or prove future readability. A receipt certifies the batch
body and manifest readback; all lineage blobs are additionally read on seal and
restore. `writer_version` identifies the exact recorded source/configuration
snapshot, not a generic development label. Each catalog `batches` entry has
exactly `manifest` and `receipt` references, sorted by manifest key with no
duplicate references. Receipts may differ after retries because readback times
differ; their content-addressed keys avoid overwriting earlier evidence.

A trusted `archive-recovery-descriptor-v1` contains exactly `format_version`,
`archive_run_id`, `bucket`, `prefix`, `catalog` (`ObjectRef`), `source`,
`start_offset`, `next_offset`. Its own hash is retained in operator-controlled
evidence outside the archive writer's writable namespace. Endpoint, region,
credentials, deadlines and fresh restore destination are explicit separate
configuration; they are never fetched from object contents. The descriptor
grants no access to an oracle or converter output. A catalog fetched without
the expected descriptor hash is untrusted; hashes do not authenticate a root
that can be rewritten together with all its descendants.

## Publication, retry and whole-interval commit

1. Validate the finite job, source/lineage, owned storage budget and fresh Kafka
   interval. Capture original group progress. Disable auto commit/reset. Use a
   dedicated archival group with explicit initialization at `S` or known progress;
   missing progress is not permission to accept a client default.
2. Conditionally create each blob/batch, GET it fully and check length/hash.
   Conditionally create and GET its manifest, then create and GET a readback
   receipt. An orphan is not coverage. On retry, reread an existing object before
   reuse; any same-key/different-content result fails without replacement.
3. Build the whole-interval catalog only from verified references. A separate
   reader path checks all objects, every observation, lineage and exact `[S,U)`
   coverage, including overlaps. Seal `catalog.json` with conditional creation.
   If it already exists, validate its entire existing graph against the job;
   reuse it only if the source, interval, lineage and exact observation content
   agree, even when the new attempt used different batching. Preserve new orphans.
4. Start a fresh read-only process to GET the sealed catalog and all referenced
   objects with no writer cache. After success retain the trusted descriptor
   outside writer-controlled storage. Verify its bytes/hash and independent
   readability. Before that retention succeeds there is no committable coverage.
5. Only now commit next offset `U` for the whole interval. An ambiguous commit
   is resolved by explicit group-progress observation; no blind offset reset.
   Report success only after observing `U`. A crash before commit repeats reads;
   a crash after commit revalidates the sealed graph and descriptor before success.

No partial interval is committed. Existing group progress beyond the verified
catalog interval, wrong source identity or unexplained intermediate progress
fails for operator investigation. On retry `S`/`U` stay captured, even when the
broker end offset grows. If Kafka needed for comparison/normal recovery expired,
fail normal recovery and use the separately requested archive-only rebuild.
Neither receipt presence nor a success flag bypasses fresh full validation.

`put_if_absent` must distinguish 412, retryable 409, transport ambiguity,
authorization failure and timeout. Read/compare after ambiguity; if absent,
retry conditionally within the same operation budget. Unsupported conditional
creation fails compatibility. No multipart upload, copy, delete, mutable pointer,
automatic cleanup or unbounded background worker is part of this profile.

## Public interface responsibilities

These names define operation responsibilities. The [codec interface](archive-codec-interface.md)
now supplies callable observation encode/decode/coverage functions, and
`runtime/s3/immutable.py` supplies separate create/read byte operations. The
[graph interface](archive-graph-interface.md) supplies the verifier, injectable
finite coordinator and file reconstruction APIs below. The
[runtime interface](archive-runtime-interface.md) adds the concrete Linux command
and enforced host-process boundaries without changing these formats.

| Operation | Inputs | Observable result |
| --- | --- | --- |
| `encode_observations` | Bounded typed observations | Exact bytes or explicit metadata/format/limit error; no transport |
| `put_if_absent` | Explicit endpoint/config, key, bytes, deadline | Created or existing identical bytes; otherwise conflict/failure |
| `read_verified` | Explicit store/config, `ObjectRef`, size/deadline | Complete verified bytes; no local-cache success path |
| `verify_catalog` | Descriptor, independently expected descriptor hash and read-only store | Enumerated observation set/lineage or failure; no writes or Kafka |
| `archive_interval` | Frozen interval/job, source/client and store | Verified sealed catalog/descriptor, then observed committed `U` |
| `rebuild_archive` | Descriptor, independently expected descriptor hash, store, fresh destination | Complete isolated output after all checks, or failure without complete output |

Rebuild emits exact archived observations in original offset order and preserves
source blobs. A separate processing layer may replay admissible measurements,
compare the pinned semantic projection and record new delivery metadata. It must
not silently feed tombstones or malformed records into the battery operator.
Its output completion marker appears only after whole-interval validation and
reconciliation. Existing destinations are refused, partial outputs stay explicitly
incomplete, and original Kafka/group/checkpoint state is never changed by rebuild.
Rebuilding online watermark decisions requires separately captured scheduling
evidence; this profile supplies bounded reference results only.

Use stable failure categories `invalid_format`, `unsupported_profile`,
`limit_exceeded`, `object_missing`, `checksum_mismatch`, `observation_conflict`,
`coverage_gap`, `lineage_mismatch`, `untrusted_catalog`, `permission_denied`,
`deadline_exceeded`, `source_unavailable`, `progress_mismatch` and
`conditional_create_unsupported`. Failures have nonzero exits and safe structured
context. Logs omit raw payloads, credentials and header values. Count archived
observations, repeated measurements, overlapping observations, rejected links,
retries, failures and verified progress separately; IDs remain outside metric labels.

## Acceptance inputs and independence

The future restricted Tester receives this specification, the recovery contract,
public interfaces and selected existing synthetic source/golden fixtures only.
No archive candidate, private converter output or implementation-generated oracle
is supplied. Freeze its executable suite and the exact public contract before
candidate exposure using the current external workflow. This document is not
evidence that freezing or independent verification has happened.

Use these literal byte expectations, then combine them with existing measurement
fixtures for a tiny Kafka scenario containing a repeated `event_id` at a new offset:

| Boundary input | Required decoded bytes or disposition |
| --- | --- |
| `key_b64=null` / `key_b64=""` | Null key / empty key, distinct |
| `value_b64="AP8="` | Two bytes `00 ff`, retained even though not event JSON |
| `value_b64=null` | Kafka tombstone, retained with null measurement link |
| Headers `[{"name_utf8":"trace","value_b64":null},{"name_utf8":"trace","value_b64":""}]` | Two ordered same-name headers, null then empty |
| `value_b64="AP9="` | Refuse noncanonical padding bits; no alternate encoding of `00 ff` |
| Overlaps `[40,42)` and `[41,43)` with identical observation 41 | Exactly offsets 40, 41, 42, with one overlap |
| Intervals `[40,41)` and `[42,43)` | Coverage gap at 41, regardless of highest offset |
| Same observation key with reversed headers or different timestamp | Conflict, regardless of equal event ID |

One focused suite should cover those invariants plus limit/unknown-format refusal,
same-key write races, lost PUT/commit acknowledgement, crashes before receipt/seal/
commit, readback after backend restart, reader/writer permission denials and
archive-only rebuild after Kafka expiry. Reuse existing M1/M2 identity fixtures;
do not duplicate their normalization assertions. A recovery process must have
observed access denial to source Kafka/oracle/converter outputs, with an independent
verifier reconciling final identities and reference aggregates. Corrupt/missing
objects, untrusted roots and inconsistent lineage fail without complete output.

## Deployment, evolution and next work

The bounded SeaweedFS/Boto3 byte-storage profile is now pinned and accepted
under [ADR-0024](../adr/0024-m4-storage-compatibility.md); the foundation guide records
its scope and limits. Compose owns the local service with a separate volume
and loopback-only S3 port. Keep
internal administrative endpoints private. Configure distinct bootstrap, writer
and restore-reader credentials; writer has no delete/admin rights and the reader
cannot PUT. Prove denial rather than infer it from credential names. Reject
ambient AWS credentials or default cloud endpoints in the local profile. Local
HTTP is scoped to loopback/private container traffic; TLS is required for a
separately reviewed shared deployment. Disable unsolicited telemetry and ancillary
services in the candidate, then verify effective listeners and outbound behavior.

Format versions change independently of canonical measurement versions. Breaking
archive changes use a new namespace and reader, with an explicit migration and
hash/coverage reconciliation; retain old bytes. No persistent migration is
performed by the original documentation step or current codec adoption. Bounded
synthetic M3 is accepted. The runtime guide records the
subsequent fresh reader/root/deadline and actual expiry/fetch-gap evidence. The
next M4 task is the separate serving compatibility gate. Production recovery and
complete M4 remain open.
