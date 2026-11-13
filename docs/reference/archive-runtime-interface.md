# Bounded local archive runtime acceptance interface

## Scope

This implements the next M4 boundary under [ADR-0027](../adr/0027-bounded-archive-runtime.md),
using the unchanged [graph](archive-graph-interface.md),
[reader](archive-kafka-reader-interface.md) and [format](archive-format-v1.md)
contracts. Only Linux x86-64 CPython 3.13, bubblewrap 0.11.1 and the existing pinned
Kafka/S3 SDKs are supported. Missing prerequisites refuse before clients or
publication. Windows retains its admitted reader but not this command profile.
No serving, checkpoint migration, AWS action or complete M4 acceptance follows.
All Python modules remain below 500 formatted lines, with typed boundaries and
fixed safe `ArchiveError(category, field)` failures. Existing formats are unchanged.

## Concrete finite source

`runtime.kafka_archive.source.ArchiveKafkaSource(reader, committer, source,
start_offset, next_offset, registrations, *, non_transactional: bool,
timeout_seconds: float = 120)` implements the existing `ArchiveSource`.
`reader` has the accepted `SliceClient` plus `close()`; `committer` has
`commit(next_offset: int, timeout: float) -> None` and `close()`.
Registrations are the validated tuple from `telemetry.archive_lineage.registrations`.
Construction validates the exact source/partition, nonempty interval of at most
32 offsets, duration and `non_transactional is True` before any port call.
It does not inspect or assign during construction. Boolean offsets/durations fail.

The first `snapshot()` inspects fresh metadata and validates identity, delete
policy, retained containment and committed S/U before assigning S if needed.
Subsequent assignment loss raises `unsupported_profile/assignment`, never silently
repairs assignment. Snapshot returns
the existing `SourceState`. `non_transactional=True` records the explicit fixture
profile, not a discovered claim that the topic never used transactions. Exact
consecutive reads still reject control/aborted/gap offsets.

`observations(S,U)` accepts only the captured interval and uses the existing
`read_slice`. Preserve all original metadata/bytes. Add links only by decoding
original value bytes with the canonical reader and matching the original archived
registrations using the existing lineage rules. Malformed/tombstone/unmatched
values remain null links; more than one matching registration refuses ambiguity.
No normalization or embedded job-path access. `commit(U)` accepts only U and calls
the explicit committer once, with positive remaining timeout at most five seconds.
`CommitAmbiguous` is propagated to the existing coordinator for fresh progress
resolution; no commit retry/reset. Close both owned clients. All operations share
the source's monotonic budget inside the supervisor's overall budget.

`open_source(endpoint, group, source, S, U, registrations, *,
non_transactional, timeout_seconds=120)` supplies the admitted read-only reader
and a separate pinned native synchronous commit consumer. Validate before clients,
recheck the existing UUID guard, disable automatic commit/store/reset/creation,
check every returned TopicPartition error and sanitize known native failures.
No commit method is added to `NativeSliceClient`.

## Concrete archive storage

`runtime.s3.archive_store.ArchiveStore(transport, listing, *, bucket: str,
prefix: str)` implements `PublishStore`. Transport has existing `put/get` methods;
listing has `list_objects_v2(**named_arguments) -> Mapping[str, object]`.
The native factory `make_archive_store(endpoint, region, bucket, prefix,
access_key, secret_key)` uses the existing pinned explicit `make_client` and
`BotoTransport`; its returned store has `close()`. No ambient discovery or cloud
fallback. Validate bucket/prefix/config before SDK clients.

Create/read reuse `ImmutableStore`. `lookup(key)` returns fresh bounded bytes,
None only for an actual 404, and refuses malformed keys/oversize bodies. Use the
existing three-attempt GET budget; permission and other failures cannot look absent.
No listing-as-coverage shortcut or cache.

`inventory()` lists only the exact owned prefix with MaxKeys at most 65, bounded
pages/tokens and at most 65 calls. Return unique prefix-relative `(key, size)`
tuples for at most 64 objects, including orphans. Every returned full key must
start with the exact prefix and pass the existing relative-key grammar. Reject
duplicates, wrong types/boolean/negative sizes, repeated or missing continuation
tokens, out-of-prefix keys, overflow and invalid responses. IsTruncated must be a
boolean. A 65th object fails; counts/body budget remain independently enforced by
the coordinator. Listing requests use one SDK attempt, and the parent deadline
bounds the entire operation. Known SDK/transport failures are safe StoreError
categories; programming errors propagate. No delete, bucket creation or mutable
write API is exposed by this adapter.

## Parent-owned retained root

The public existing immutable-byte dependency for independent tests is
`runtime.s3.immutable.Transport`: `put(key: str, body: bytes) -> None` performs one
conditional-create request; `get(key: str, max_bytes: int) -> bytes` performs one
fresh bounded full-body GET. Errors are
`RequestFailure(status: int | None, reason: str)`, where status is the actual
HTTP status or None for transport ambiguity, and `StoreError(category: str)` with
public `.category`. A 404 get is missing; 401/403 is permission denial; None,
409 and 5xx are retryable within three GET slots. Store create returns the string
`created` or `existing`, never a response object. Store read takes the original
`sha256:<hex>` and byte length and verifies both. The maximum body is 16 MiB.
These are public dependency interfaces, not permission to inspect a candidate.

`runtime.archive_runtime.retention.RetainedRoot(parent: Path, archive_run_id: str)`
requires an existing real directory and a valid archive run ID; symlink/junction
ancestors and traversal fail. `retain(descriptor: bytes, expected_sha256: str)`
validates the bounded canonical descriptor, its independent hash and run ID,
then durably creates an exclusive run directory containing exact `descriptor.json`
and `descriptor.sha256` (ASCII digest plus LF). Fsync files/directories before
publishing with the existing no-replace Linux primitive. Retain incomplete staging
on failure. Existing exact two-file roots may be reused after fresh byte/hash
validation; conflicting, incomplete, extra-file or linked roots refuse without
replacement. `read() -> bytes` independently rereads the retained root and checks
its hash. The parent owns this namespace; it is never mounted into workers.
No automatic cleanup or persisted format change to the descriptor itself.

## Bounded child protocol and isolation

`runtime.archive_runtime.processes.run_worker(argv: Sequence[str],
request: Mapping[str, object], handler: Callable[[dict[str, object]],
dict[str, object]] | None = None, *, expires: float) -> dict[str, object]`
launches a new owned POSIX process group. `expires` is a finite positive remaining
monotonic deadline at most 120 seconds; invalid inputs refuse before launch.
Use nonblocking bounded pipe I/O; partial/trickling startup input/output must not
escape the deadline. Startup request is one JSON line (at most 96 MiB); ordinary
child frames are at most 128 KiB including LF. Reject duplicate keys/nonfinite
numbers, malformed/unknown protocol, unexpected EOF/nonzero exit and output
overflow. Drain stderr with a bounded buffer and never forward raw child errors.

Child frames use `op`: `verify`/`retain` carry exactly `op`, `descriptor_b64`,
`sha256`; `read_retained` carries only `op`; `done` may carry bounded result
fields. A handler returns one bounded JSON reply. `error` carries exactly `op`,
`category`, `field` and only known safe diagnostics may be propagated. Unknown
requests or a request without handler refuse. Return the final done mapping only
after zero child exit and verified owned-group shutdown. End/reap owned groups
on every failure/deadline, including descendants after a nominal parent exit.
An unexpected remaining descendant is failure even if cleanup succeeds. No
success is fabricated from a final packet before process exit.

The runtime sandbox mounts only a fresh read-only production-code closure,
explicit existing interpreter/SDK directories and role-specific staging/output
where required. No project checkout, tests, source data, converter output, parent
roots, credentials file or oracle mount. Clear inherited environment; send only
the role's credentials through pipes. Use user/PID/mount namespaces and
die-with-parent; reconstruction additionally unshares the network. Unsupported
namespace/version/platform is a hard failure. Parent checks actual denied access
and preserves outcomes before accepting the profile. Apply bounded worker memory,
CPU and output limits. Docker/container administration remains trusted.

## Command contract

`scripts/archive.py` exposes `publish` and `rebuild`, with safe JSON result/error
and nonzero failure exits. Common flags: `--config PATH`, `--scratch-parent PATH`,
`--timeout-seconds FLOAT` (default 120, finite positive at most 120).
Parents must be existing real directories. Keep owned scratch after failures.

Configuration is strict JSON with exactly `runtime_version=local-archive-runtime-v1`,
`python_root`, `sdk_paths` (explicit existing absolute directories) and `storage`.
Interpreter is `<python_root>/bin/python3.13`. Storage has exactly `endpoint`,
`region`, `bucket`, `reader`, and additionally `writer` for publish. Each role has
exactly `access_key`, `secret_key`, with distinct credentials. Rebuild configuration
contains no writer credentials. Validate profile/paths/size/version and refuse
ambient AWS selectors before clients. Paths/configuration are trusted operator
capabilities, not fields from an untrusted archive. Never print credentials.

Publish additionally requires `--job PATH`, repeated `--blob KEY=PATH`,
`--group NAME`, `--root-parent PATH`, `--non-transactional-fixture`.
Kafka endpoint is exactly 127.0.0.1:19092. Job and blobs are the existing engine
inputs; read only explicitly named files with their established bounds and reject
duplicate blob keys. Embedded original job paths are metadata only. Validate the
whole job/blob/lineage input before any publication. One operator-owned writer
per prefix; administrative concurrent mutation remains outside this profile.

The supervisor creates fresh production closure/scratch and one overall deadline.
Only writer credentials/blobs enter the writer. It reuses `archive_interval` and
its explicit source/store adapters. `verify_fresh` is an IPC request: the parent
launches a new bounded S3 graph reader with reader credentials and no writer cache.
Only after success may the matching descriptor be retained by the parent. The
parent checks descriptor source/interval/bucket/run against the original job and
serves independently reread retained bytes before allowing the writer to proceed.
The writer's existing coordinator handles final source check, commit U and observed
U. Success includes descriptor hash and observation/unique-measurement/progress
counts; the externally retained root remains the recovery input.

Optional fixture-only `--test-failpoint` values are `after_batch`,
`after_receipt`, `after_retain`, `after_commit`. They terminate the writer with
exit 77 after the named real boundary, without rollback or success. A normal
explicit retry revalidates original S/U/graph/root, allowing changed batching;
it does not recreate missing Kafka data. These are process interruption probes,
not claims of actual network packet/ACK loss. Existing engine tests separately
exercise ambiguous commit resolution.

Rebuild additionally requires `--descriptor PATH`, `--expected-sha256 DIGEST`,
`--output PATH` (fresh under an existing real parent). Check root trust before
fetching. A fresh bounded reader with reader credentials verifies/downloads all
referenced S3 objects into new staging. A separate process with no network then
reverifies that archive and calls existing `rebuild_archive` into fresh output.
No Kafka/source/converter/oracle is an input or fallback. Preserve exact objects,
observation coordinates and original delivery metadata; fresh output path isolates
the reconstruction. Full graph failure or child/deadline failure cannot produce
a successful command. Output completion follows the established marker-last
rebuild rules; report a failure after completed output honestly, never delete it.

## Acceptance evidence and limits

Freeze independent purposeful source/store/root/process tests before implementation.
Reuse existing lineage and immutable/graph suites. Actual pinned clients must
publish byte-sensitive records with repeated measurements, commit only after
fresh graph verification and protected retention, and recover from each declared
interruption without a gap. Use fresh Compose profiles with measured admission,
separate volumes/roles, existing pins/resource limits and unused explicit subnets.
No original broker starts, prune, cloud operations or downloads.

Exercise real same-UUID expiry and pre/post-preflight refusals with unchanged
progress; stop source Kafka, fetch archive freshly from S3 and reconstruct with
observed source/oracle/root and network denials. Independent verification reconciles
all observations, unique measurement identities/semantics and bounded reference
results; that verifier is not a recovery input. Corrupt/missing archive objects,
untrusted descriptor, retention-root conflict and a forced command timeout fail
without false success. Keep failures, partial artifacts, volumes and receipts.
No host/power-loss, production capacity, malicious administrator, online watermark
replay or analytical-serving guarantee is established by a local success.
