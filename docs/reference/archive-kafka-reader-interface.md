# Bounded read-only Kafka slice interface

This M4 increment implements the source-read boundary before a concrete
Kafka/S3 publisher. It introduces no dependency or service: the native adapter
uses the already pinned confluent-kafka/librdkafka 2.16.0 pair. There is no
commit, reset, topic/group creation, archive write or recovery fallback API.
The caller owns closing the native client and enforcing process lifetime.

**Status, 2026-10-23:** only the pure `read_slice`/`SliceClient`/`SourceInfo`
boundary is adopted. The native interface below remains proposed. Its Windows
2.16.0 candidate failed the real broker identity gate: described topic UUIDs
lose high bits. The evidence guide records the independent
broker/SDK comparison. No native adapter or integrated publisher is adopted.
The original pre-candidate interface and tests remain frozen unchanged.

**Current status, 2026-10-26:** the separately guarded native adapter is admitted
for the bounded x86-64 CPython 3.13 Linux/Windows profiles in the
admission evidence. Stock Windows refuses before
clients; the verified local derivative and stock Linux pass. The original failed
candidate remains historical. Kafka/S3 publication and full recovery remain open.

## Public interface

`runtime.kafka_archive.reader.read_slice(client: SliceClient,
source: Mapping[str, object], start: int, next_offset: int, *,
timeout_seconds: float = 30) -> tuple[dict[str, object], ...]` returns complete
`kafka-observation-v1` rows with `measurement=null`. Measurement admission and
lineage linking remain the graph integration's responsibility. Original bytes
are never parsed as JSON or regenerated. Sources have exactly the archive v1
`cluster_id`, `topic_id`, `topic`, `partition` fields. Only partition 0 of a
single-partition topic is supported; require `0 <= S < U <= 2**63-1` and at
most 32 offsets. Validate input before any client operation, also under `-O`.
The timeout must be finite, positive and at most 120 seconds; booleans fail.

`runtime.kafka_archive.types.SourceInfo` is a frozen dataclass with fields
`source: Mapping[str, object]`, `low: int`, `high: int`,
`committed: int | None`, `delete_only: bool`.

`SliceClient` is a typed protocol with only these methods:

- `inspect(timeout: float) -> SourceInfo`: fresh cluster/topic identity,
  effective cleanup policy, uncached retained bounds and committed group offset.
- `assign(start: int) -> None`: explicit manual assignment to the declared
  source partition and absolute offset, without subscribing or resetting.
- `poll(timeout: float) -> Mapping[str, object] | None`: one lossless observation
  with a null measurement link, or no record yet. Errors are never rows.
- `assigned() -> bool`: exact single declared partition remains assigned.

The reader verifies source identity, delete-only policy, retained containment
`L <= S < U <= H` and committed progress equal to S or U before assignment.
Missing, intermediate or beyond-U progress fails; initialization is a separate
operator action. It then assigns S, requires exact assignment, and checks every
observation's full codec schema, source identity and next consecutive offset.
None polls may wait only within the one monotonic deadline. An unexpected
offset (including EOF before U), source change, error or assignment loss fails
without returning partial success. After reading U-S rows, recheck fresh identity,
profile, retained containment, unchanged original committed progress and exact
assignment. Appends beyond captured U are allowed. Codec line, header and batch
bounds still apply; validate rows individually and in groups of at most 16.
No client method is called with an expired or nonpositive remaining timeout.

Expected failures are safe `ArchiveError(category, field)` diagnostics from the
existing codec. `source_gap` uses field `retention` for failed containment or
`offset` for an unexpected observation position; `source_identity` uses `source`;
`progress_mismatch` uses `committed`; unsupported cleanup/assignment use
`unsupported_profile` with `cleanup_policy`/`assignment`. Timeout is
`deadline_exceeded`, field `source`; permission and native availability errors
are `permission_denied`/`source_unavailable`, field `source`. Original error
messages and payloads never enter safe diagnostics. Codec validation errors
retain their established categories. An injected client's PermissionError,
TimeoutError and OSError are translated accordingly; programming errors propagate.

## Native boundary

`runtime.kafka_archive.native.NativeSliceClient(endpoint: str, group: str,
source: Mapping[str, object])` permits only `127.0.0.1:19092` and a group matching
`m4-reader-[a-z0-9-]{1,64}`. It refuses unknown client/native versions. Validate
these inputs before constructing SDK clients. Consumer configuration explicitly
sets auto commit and auto offset store false, auto reset `error`, isolation
`read_committed`, EOF enabled, bounded receive/fetch queues and metadata
auto-creation false. The native client exposes the protocol above and `close()`;
it supplies no commit, seek, subscribe, producer, admin mutation or reset API.

Inspect uses AdminClient describe-cluster, describe-topics and describe-configs,
not listing as proof of identity. Require one loopback-advertised broker, exactly
one partition numbered zero, a nonempty nonzero topic UUID and cleanup.policy
exactly `delete`. Check TopicPartition errors, including committed queries.
Every blocking native request/future/poll is capped by the supplied remaining
deadline and a five-second per-request ceiling. Native EOF/out-of-range becomes
`source_gap`; other broker failures fail safely. No implicit retry to success.
`close()` disables all automatic progress mutation; its wall-clock bound requires
the future command's parent deadline and owned process shutdown.

Preserve Kafka timestamps (types create_time/log_append_time/not_available),
null versus empty keys/values, ordered repeated header names and nullable binary
header values. Header names must round-trip strict UTF-8. Invalid metadata or
Unicode conversion fails rather than omitting/replacing a header. The selected
client exposes C-string header names; embedded NUL names are outside this profile
and cannot be claimed lossless. Controlled fixtures use UTF-8 names without NUL.
Contiguous read_committed coverage detects missing/control/aborted offsets in
the chosen interval; it cannot certify that a topic never used transactions.

## Acceptance and limits

### Guarded native admission increment, 2026-10-26

The native boundary above is implemented for this increment.
Support is limited to x86-64 Linux and Windows, CPython 3.13 and the UUID-safe
SDK profiles in ADR-0025. Before importing SDK client modules or constructing
any clients, validate source/endpoint/group and platform, then call
`telemetry.kafka_compat.require_uuid_boundary()` on every construction. Import
the compatibility module and call its function so the public admission seam can
be independently exercised. A `KafkaCompatibilityError` becomes
`ArchiveError("unsupported_profile", "source")` without native details.
Missing/unsupported SDKs also refuse through this guard. Never cache admission.
Unknown platform, architecture or interpreter refuses before client creation.
This admission does not change the original frozen pure interface.

Independent native tests may replace the public compatibility function and SDK
module imports to observe client construction and protocol behavior. Such tests
do not certify the actual SDK: separate stock/fixed Windows and stock Linux
probes, full broker-owned UUID comparison, exact reads and real post-preflight
expiry refusal remain required evidence before adoption. Keep earlier rejected
candidates and historical identity findings intact.

Freeze independently authored port tests before exposing the candidate. Exercise
exact raw bytes, duplicate measurements as distinct offsets, source/progress
changes, fetch gaps after a successful preflight, invalid metadata and deadline
refusal. Run the real pinned client on a fresh owned broker/topic, capture its
identity and original records, then expire only that disposable topic. Verify
preflight refusal and actual reset-disabled fetch failure after preflight;
observe unchanged committed progress. Historical brokers stay stopped.

This read-only slice does not establish archival commit ordering, external root
retention, a whole-command process deadline, S3 recovery or Flink gap refusal.
No persistent format changes. Rollback stops using the reader and retains all
evidence and experiment data. Never reset progress or delete historical storage.
