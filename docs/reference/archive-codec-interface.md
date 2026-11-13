# Bounded observation codec interface

This interface implements only the observation encoding and exact-offset union
parts of [archive v1](archive-format-v1.md). It adds no storage, source consumer,
catalog publication, commit, restore command or new dependency. The existing
canonical measurement contract and the proposed archive wire version are
unchanged. Full archive acceptance still requires the independent object graph,
lineage, fresh-reader, source-progress and rebuild gates.

## Public Python surface

Use `telemetry.archive_codec` on the supported Python 3.13 profile. All failures
raise `ArchiveError`, a `ValueError` with safe public `category` and `field`
strings. Diagnostics contain fixed field/reason names, never supplied payloads,
header values or identity text. Public functions accept ordinary dictionaries
with string keys and object values; export typed structures at the source
boundary. No input may be changed by a function, including nested headers.

- `encode_observations(rows: Sequence[Mapping[str, object]]) -> bytes` validates
  and emits the exact canonical JSONL bytes from archive v1, sorting a nonempty
  batch by offset. A batch has at most 16 lines and at most 1 MiB total bytes;
  every encoded line, including LF, is at most 256 KiB. Duplicate offsets in
  one batch, even byte-identical copies, fail `observation_conflict`. Every row
  in a batch must have identical cluster/topic/partition source coordinates.
- `decode_observations(data: bytes) -> tuple[dict[str, object], ...]` validates
  the same strict schema and returns fresh owned dictionaries, with ordered
  headers and nullable byte strings preserved in canonical base64 form.
  Require nonempty bytes, exact canonical re-encoding, ascending unique offsets
  and the same bounds/source rules. Do not accept mutable bytearray inputs.
- `reconcile_coverage(batches: Sequence[bytes], source: Mapping[str, object],
  start_offset: int, next_offset: int) -> Coverage` independently decodes every
  supplied batch, then checks source and exact finite offset coverage. `Coverage`
  exposes `observations` (an offset-sorted tuple of fresh dictionaries),
  `overlap_count` (each repeated same-offset observation after its first copy),
  and `repeated_measurement_count` (each repeated non-null event ID at another
  unique offset after its first observation). Repeated measurement observations
  are retained, not collapsed.

`source` has exactly `cluster_id`, `topic_id`, `topic`, `partition`. Require
`0 <= start_offset < next_offset <= 2**63`, excluding bool/float, and at most
32 unique offsets. Accept at most 16 batches and 64 total lines including
overlaps. Enumerate the full declared interval rather than allocate state
proportional to an untrusted integer range. Every observation must belong to
the expected source and interval. Matching overlaps compare complete canonical
line bytes, including ordered repeated headers and timestamps. A gap fails
`coverage_gap`; different content at an existing observation key fails
`observation_conflict`; source/interval mismatch fails `lineage_mismatch`.

## Exact schema checks

The exact fields and canonical encoding are defined in archive v1. No unknown
fields, duplicate JSON keys, floats, NaN/Infinity, unpaired surrogates, BOM,
blank lines, CRLF, missing final LF or alternate JSON spacing/key order survive
decoding. Maximum parsed container nesting is 16; refuse deeper input before
unbounded parser recursion. All identity strings are nonempty valid UTF-8 and
at most 512 UTF-8 bytes. Integers exclude bool. Partition and offset use the
archive v1 ranges. Timestamp type/value pairs must agree, including signed
64-bit timestamp bounds and null/not_available pairing.

Header names are valid UTF-8, at most 256 encoded bytes, with no normalization;
the empty header name is allowed. Retain at most 32 ordered header entries,
including duplicate names. Nullable base64 fields distinguish null, empty and
nonempty bytes. Standard alphabet and padding must round-trip exactly; refuse
noncanonical padding bits such as `AP9=` for bytes `00 ff`.

A non-null `measurement` has exactly `event_id` and
`source_manifest_sha256`, each `sha256:` plus 64 lowercase hexadecimal digits.
At this layer it is a **syntactic link only**. The codec does not certify the
event JSON, manifest existence, source rights or admissibility. The future graph
verifier must call the independent canonical reader, resolve the archived
manifest and verify these links before seal/rebuild. Do not pass codec-only
output directly into the processing operator as admitted measurements.

Wrong wire version fails `unsupported_profile`; invalid shape/encoding/type
fails `invalid_format`; admitted size/count/nesting/string bounds exceeded fail
`limit_exceeded`. Meaningful duplicate, gap and lineage categories are specified
above. No transport or filesystem I/O is permitted in these functions.

## Independent verification and evolution

Freeze this interface and archive v1 with a separate restricted Tester's small
executable suite before exposing the codec candidate. Use literal byte vectors
for null/empty/binary and repeated headers, plus independently enumerated
overlap/gap/conflict sets. Existing M1 identity tests own normalization; do not
retest the converter or use implementation-generated expected bytes.

There is no persistent format migration in this increment. Canonical encoding
is already specified by ADR-0021. Later incompatible changes require a new wire
version/namespace; existing archived bytes remain immutable.
