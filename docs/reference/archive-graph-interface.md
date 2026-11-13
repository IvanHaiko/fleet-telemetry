# Bounded archive graph and coordination interfaces

This is the public acceptance interface for the next M4 increment. It refines
[archive v1](archive-format-v1.md), without claiming live Kafka integration,
expired-offset recovery or complete M4 acceptance. All APIs use Python 3.13,
standard-library types and fixed safe `ArchiveError(category, field)` diagnostics.
Every module stays below 500 lines after Ruff formatting.

## Trusted graph reader

`telemetry.archive_graph.verify_catalog(descriptor: bytes,
expected_sha256: str, store: ReadStore) -> VerifiedArchive` is read-only. The
caller independently supplies `sha256:<hex>` for the exact descriptor bytes.
`ReadStore.read(key: str, sha256: str, byte_length: int) -> bytes` receives
prefix-relative keys. The verifier independently checks returned lengths and
hashes; a transport cannot certify itself. No listing, Kafka, local source files,
converter run directory, current network provenance or writer cache is input.

`VerifiedArchive` has owned `descriptor: dict[str, object]`,
`coverage: Coverage`, `blobs: dict[str, bytes]` (all lineage objects by relative
key), and `measurements: tuple[dict[str, object], ...]`. Measurements are unique
admitted events ordered by first original offset. Repeated event IDs must have
the same `battery-semantic-v1` projection; conflicting semantic values fail.
Repeated observations at different offsets remain in coverage.

Validate every exact control-document schema and canonical JSON plus LF before
use, every ObjectRef's role-specific content-addressed key/length/null version,
receipt-to-manifest relationship and UTC calendar timestamp, manifest contiguous
range/count, identical run lineage, root source/interval and exact observation
union. Recheck full bytes on every invocation. Enforce the v1 limits before
unbounded fetch/parse/allocation; conflicting references for one key fail.
Root trust mismatch is `untrusted_catalog`; checksum, missing objects, lineage,
coverage and conflicting observations retain their documented categories.

For this first synthetic profile, the original provenance blob is the **exact
original `bounded-conversion-v1` job document**, already containing the reviewed
`manifest`, source checksum/length, and original delivery run. It is not the
generated `bounded-run-v1` output manifest. The embedded `input.path` and
`fixture_specification` are retained metadata and MUST NEVER be opened. Accept
only `mode=synthetic`, `battery-v1`, schema `1.0.0`, privacy `synthetic`, semantic
projection `battery-semantic-v1`; validate the embedded registration and clock
anchor under the existing M1 rules. No new provenance wrapper is generated.
The original job can retain pretty JSON; only archive control documents require
canonical encoding. Reject duplicate keys, excessive nesting and invalid strings
also in the original job. Keep at most two source/job pairs (four distinct blobs).
Every pair, including pairs without valid observations, must reconcile the source
blob hash and length, manifest source ID, rights/privacy evidence and delivery run.

Non-null measurement links must decode their **original value bytes** through
`telemetry_reader.read_battery_event`. Match the link event ID and job blob hash,
registered source/stream/vehicle/normalization/schema, manifest ID and privacy,
original delivery run, clock mapping and native time bounds. Unsupported or
malformed values are retained with null links. A null link must not hide an event
which passes this same admission and lineage match. Semantic projection uses
the existing `SEMANTIC_FIELDS`, independently of delivery metadata. These checks
do not re-normalize source files or prove all archived source records appeared
in Kafka; that is a separate source-to-observation reconciliation.

## Finite coordination engine

`telemetry.archive_worker.archive_interval(job: Mapping[str, object],
blobs: Mapping[str, bytes], source: ArchiveSource, store: PublishStore,
hooks: ArchiveHooks) -> bytes` returns the trusted descriptor bytes only after
observing committed `U`. This is a bounded coordination engine with explicit
ports, not a production Kafka command or a proof that an arbitrary supplied port
actually enforces its obligations.

Job fields are exactly `archive_run_id`, `bucket`, `source`, `start_offset`,
`next_offset`, `lineage`, `writer_version`, `verified_at`, `batch_size`.
`writer_version` is a recorded source/configuration `sha256:<hex>`; `batch_size`
is 1..16; the other values follow archive v1. Blobs contain exactly the distinct
lineage keys with their original bytes. Job `verified_at` is the earliest
acceptable receipt time, captured when preparing the job, with the receipt UTC
syntax. A future lower bound fails before publication. The engine generates
each actual receipt timestamp after full batch/manifest GET completion; the job
timestamp cannot certify that completion. Changed receipt keys and their catalog
references must pass projected storage admission before publication.

`SourceState` is a frozen dataclass with `source: Mapping[str, object]`,
`low: int`, `high: int`, `committed: int | None`, `delete_only: bool`,
`non_transactional: bool`, `assigned: bool`.
`ArchiveSource.snapshot() -> SourceState` must return fresh identity, retained
bounds, effective profile and progress. `observations(start: int, next_offset:
int) -> Sequence[Mapping[str, object]]` preserves all Kafka metadata;
`commit(next_offset: int) -> None` uses explicit synchronous commit. A lost commit
acknowledgement raises `CommitAmbiguous`; resolve through a fresh snapshot. Any
other error fails. Auto reset/commit are forbidden in a future concrete adapter.
Missing progress fails; explicit initialization at S is the caller's separate
operation. Only S or already committed U is valid; never repair intermediate or
beyond-U progress. Retained `[L,H)` must contain `[S,U)` even on retries.

`PublishStore` extends `ReadStore` with `create(key, body) -> str`,
`lookup(key: str) -> bytes | None`, and
`inventory() -> Sequence[tuple[str, int]]`. Create has the accepted immutable
adapter's atomic conditional-create/readback semantics. Lookup returns fresh
bounded bytes, None only for 404. Inventory lists only the owned prefix, includes
orphans and is bounded to 64 objects plus an overflow sentinel. The engine checks
actual inventory sizes and projected writes before publication, including a
maximum 96 MiB stored body budget. Listing never proves coverage. Backend/disk
allocation and CPU/memory admission remain the concrete runtime's responsibility.

`ArchiveHooks.verify_fresh(descriptor: bytes, expected_sha256: str) -> None`
must launch a fresh read-only graph reader process with separate reader access.
`retain(descriptor: bytes, expected_sha256: str) -> None` durably retains the
descriptor outside the writer's control; `read_retained() -> bytes` independently
reads that retained copy. The engine checks exact retained bytes/hash before
commit. The host owns a 120-second command deadline and process-group shutdown.
Tests use deterministic fault ports for ordering, and an actual restricted
separate process for archive-only reconstruction. Injected hooks alone do not
establish process isolation or durable external retention.

The engine revalidates a sealed existing graph against captured job source,
interval, lineage and exact fresh observation bytes, allowing changed batching.
Orphans are retained. Publication order is blobs, batch, manifest, readback
receipt, complete verified catalog, fresh verification, retained root/readback,
fresh source precommit check, commit U, fresh observed progress U. No partial
commit, replacement, deletion or automatic rebuild fallback exists.

## Archive-only output

`telemetry.archive_rebuild.rebuild_archive(descriptor: bytes,
expected_sha256: str, store: ReadStore, destination: Path) -> VerifiedArchive`
validates the complete graph before creating output. Require a fresh target
under an existing real directory; refuse symlink/junction destinations or
ancestors and all existing targets. Output contains ordered exact canonical
`observations.jsonl`, unique admitted `measurements.jsonl`, original blobs at
their relative `sources/` keys, exact `descriptor.json`, and `complete.json`
written last after closing/fsyncing data files. POSIX also fsyncs output
directories; Windows explicitly records directory fsync as unavailable.
Neither profile claims power-loss or host-loss durability. Completion pins descriptor,
output hashes/counts and the original source/interval. Existing output is never
replaced; failures leave no completion marker. No old group, checkpoint, source,
oracle or converter path is read or changed. This is a new isolated file dataset;
no online watermark or analytical window claim is made.

Rollback retains objects, descriptors and incomplete output and stops using the
new engine. No persistent migration, object deletion, offset reset, checkpoint
change or publication is authorized by this increment. Actual client gap/expiry
and storage/process/deadline integration remain separate acceptance gates.
