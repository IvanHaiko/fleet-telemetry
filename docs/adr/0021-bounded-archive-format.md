# ADR-0021: Bounded observation archive format and storage interfaces

**Status:** Proposed full catalog/publication/rebuild protocol. The observation
encoding subset is implemented and accepted on 2026-10-23 in the follow-up below;
the local byte-storage boundary is accepted separately in ADR-0024. The original
2026-10-22 design and documentation-only verification remain recorded below.
The dated [ADR-0027](0027-bounded-archive-runtime.md) follow-up selects the concrete
bounded Linux publication/commit/reconstruction runtime. Its
evidence covers actual expiry and protected roots;
this does not retroactively broaden the original design-only verification or
establish production recovery/full M4.

## Problem

The archive recovery contract specifies coverage but leaves encoding, catalog
discovery and commit boundaries unresolved. Implementation needs a bounded public
interface that an independent reader can verify without Kafka, converter output
or a writer cache. The historical retention failure cannot be repaired by this
design. M3 acceptance still precedes M4 integration.

## Proposed decision

Use the [bounded archive v1 specification](../reference/archive-format-v1.md): uncompressed
UTF-8 JSON Lines for observations, padded base64 for nullable binary fields,
SHA-256 references and immutable JSON manifests, receipts and a finite catalog.
Preserve source files and provenance manifests as separate exact-byte objects.
Neither decoding canonical events nor collapsing repeated event IDs substitutes
for storing transport observations.

The first profile has one non-transactional, non-compacted partition, a captured
nonempty interval and one writer. Seal the complete finite catalog and verify it
through a fresh reader **before committing any progress for that interval**.
This deliberately trades retry work for a simple bounded commit boundary; it is
not an incremental archival protocol. One trusted recovery descriptor carries
the catalog key, hash, expected identity and interval outside the archive writer's
control. No mutable `latest` pointer, listing-based completeness or new database
is required. Batching and exact overlaps do not change observation coverage.

Select Boto3's low-level S3 client as the proposed transport interface. Evaluate
`boto3==1.43.117` with `botocore==1.43.117` on the existing project Python 3.13
profile, isolated from PyFlink. The tagged
[Boto3 dependency declaration](https://github.com/boto/boto3/blob/1.43.117/setup.py)
admits that botocore version and Python 3.13. Before installation, resolve and
hash-lock the full transitive environment; these two pins are not a lockfile.
Keep the current root dependency files unchanged during this design step.

Evaluate **SeaweedFS 4.48** as the local S3-compatible backend, using the
[upstream release](https://github.com/seaweedfs/seaweedfs/releases/tag/4.48) and
its [Apache-2.0 source license](https://github.com/seaweedfs/seaweedfs/blob/4.48/LICENSE).
Its tagged `weed mini` implementation offers a single-process local topology,
but compatibility, disk expansion, restart durability and idle/peak memory are
unmeasured here. Review the chosen Linux distribution artifact, full source
commit, SHA-256, image digest/build route, bundled notices and current advisories
before startup. A release tag alone is not an executable artifact pin.

The original MinIO candidate is not adopted: its
[upstream repository](https://github.com/minio/minio) is archived and read-only
as observed on 2026-10-22. This proposal replaces that candidate only if accepted;
it does not rewrite ADR-0002's history or change ADR-0020's final Amazon S3 target.

## Required backend behavior

Use signed, low-level `PutObject` with `If-None-Match: *`, followed by full
`GetObject` readback and application SHA-256 verification. AWS documents this
[conditional creation boundary](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html).
An existence check followed by unconditional PUT is insufficient. Resolve a
precondition failure or ambiguous acknowledgement by reading the existing bytes;
different bytes fail, and bounded retries never remove the condition.

SeaweedFS 4.48 has a tagged
[conditional-header implementation](https://github.com/seaweedfs/seaweedfs/blob/4.48/weed/s3api/s3api_object_handlers_put.go),
which is source evidence, not proof of atomic create under concurrency. A real
two-client conflicting-create probe must demonstrate one winner and unchanged
winning bytes. Failure blocks this backend, even for the single-writer profile;
do not emulate conditional creation with HEAD/PUT or silently patch the backend.
An alternative requires a linked decision and the same gate.

## Alternatives and impact

- Parquet/Avro: useful at larger scale, but add libraries and schema/encoding
  complexity before any measured query or compression requirement.
- A filesystem-only archive: useful for pure format checks, but cannot validate
  the S3 publication, credentials or ambiguous-write boundary.
- MinIO community: historical candidate; adopting an archived distribution would
  create maintenance obligations without evidence of a need.
- Immediate Amazon S3 execution: matches the final target but crosses the
  separately authorized cloud gate before local acceptance.
- Incremental catalogs or a catalog database: unnecessary for one tiny captured
  interval; concurrent/infinite archival requires a separate protocol decision.

Base64 expands each binary value to `4 * ceil(n / 3)` bytes before JSON overhead.
Manifests, receipts, duplicate observations, orphan attempts, readback, restore
outputs and backend metadata add disk and I/O. The proposed small profile admits
at most 32 observations and 64 archive objects; it establishes no 50 GiB capacity
claim. One additional backend process/container and the SDK dependency graph
need maintenance. No cloud spend is introduced. Later S3 estimates must include
storage, requests, retained versions and recovery transfer.

## Acceptance, compatibility and rollback

Design review must find explicit schemas, bounds, trust roots, operations,
failure outcomes and independent acceptance inputs in the linked specification.
The design's examples are public inputs, not a frozen independent test suite.
The future high-risk implementation must use the current external workflow:
restricted Tester first, frozen contract/tests before candidate exposure,
observed permission denials and separate read-only review. Shared sessions do
not establish that isolation.

Live acceptance requires conditional-create races, restart/readback, credential
denials, crash/commit ambiguity, byte-sensitive round trips, coverage conflicts
and archive-only rebuild with missing Kafka offsets. Actual Amazon S3 acceptance
remains a later separately authorized exercise. Flink checkpoints remain on
their existing filesystem; no S3 plugin is adopted by this proposal.

No stored format or runtime changes in this step. Revert only these scoped
documentation edits to roll back. Before persisted v1 adoption, retain old
objects and add new readers/namespaces for incompatible format changes; never
rewrite evidence in place. No automatic orphan deletion or volume cleanup.

## Design verification, 2026-10-22

The documentation-only check uses the existing project interpreter:

```powershell
.venv/Scripts/python.exe -B .local-discovery/archive-design-20261022T081934Z/check_design.py
```

It checks local link targets/heading anchors, whitespace/fences, the literal
base64 and coverage vectors, the final permitted file set, protected source
hashes and the saved original Git index hash. It also runs `git diff --check`
with `GIT_INDEX_FILE` set to the saved disposable inspection copy and
`GIT_OPTIONAL_LOCKS=0`. The command passes; exact counts and file names are in
the ignored local `verification.json` alongside the checker and scoped baseline.
These are author checks, not independent restricted review or runtime acceptance.

Created: this ADR and `docs/reference/archive-format-v1.md`. Updated: `README.md`,
`docs/architecture.md`, `docs/reference/archive-recovery-contract.md`,
`docs/data-contracts.md`, `docs/deployment-and-terraform.md`,
`docs/guides/production-recovery-gate.md`, `docs/roadmap.md`,
`docs/testing-strategy.md` and the dated follow-up in ADR-0002.
Local evidence contains the checker, source/index hashes, scoped pre-edit file
copies and the verification report; it remains outside publication inputs.

Direct PowerShell requests for upstream release/package metadata failed DNS
resolution. Primary release/source/API documentation was reviewed through
read-only web retrieval instead. No package/binary/image was downloaded or
installed; no distribution checksum, resolved SDK lock, live backend behavior
or measured resource bound was established. No service, cloud operation,
executable project change, commit or publication occurred. The next runtime
work package is M3 multi-input idleness under the existing PyFlink direction.

## Observation-codec adoption, 2026-10-23

The maintainer's M4 continuation implements only this proposal's exact
observation encoding and finite offset-union subset, through the
[public codec interface](../reference/archive-codec-interface.md). Separate restricted
Tester/Implementer sessions, frozen literal byte/coverage cases, read-only
review and deterministic acceptance pass. The foundation guide
records source files, exact checks, failures, reviewed test supersessions and
limitations. Canonical measurement identity and wire-version meanings are
unchanged; no persistent format migration or old-object rewrite occurred.

Non-null measurement links remain syntax until the future graph verifier
admits the event and resolves archived source evidence. Manifests, catalog,
trusted descriptor, fresh-process whole-graph verification, publication/commit
and archive-only rebuild remain proposed and unimplemented. ADR-0024 accepts
only the separately tested local byte-storage profile. This follow-up does not
accept complete M4, a checkpoint S3 plugin, production or AWS execution.

## Graph/coordination follow-up, 2026-10-23

The [public graph interface](../reference/archive-graph-interface.md) and
evidence guide now implement and check trusted catalog
references, original synthetic source/job admission, exact observation coverage,
finite publication/progress ports and isolated file reconstruction. Original
provenance is the exact original bounded conversion job, not its generated run
manifest. Receipt times are sampled after actual full GET completion; the input
job time is an earliest acceptable bound. The detected timestamp/Windows
portability failures and their repairs remain recorded alongside frozen inputs.

Independent tests, separate restricted reconstruction and live local S3
readback/restart provide bounded evidence. Source/progress and host process
ports still need a concrete Kafka command and enforced runtime boundaries.
Actual Kafka expiry, selected-client gap refusal, bounded processing-reference
reconciliation and serving remain open. The full protocol's Proposed status
is unchanged; no production, host-loss or AWS adoption follows from this subset.
