# Bounded local conversion

**Setup/CI follow-up — 2026-10-19:** the [shared M1 checks](m1-checks.md) now pass
in fresh local synthetic-only and optional-reader environments. A Windows/Linux CI
workflow is configured; hosted execution remains pending. This report preserves
the original converter increment and its verification evidence.

**Portability follow-up — 2026-10-20:** Linux no-replace publication
extends the initial Windows writer under [ADR-0016](../adr/0016-linux-no-replace-publication.md).
The original Windows verification below remains historical evidence.

## Authorized scope and result — 2026-10-19

This M1 increment implements three connected features: whole-input ULog
integrity/count validation, an optional pinned semantic reader bridge, and a
local converter with rejection accounting and fresh run artifacts. See
[ADR-0009](../adr/0009-bounded-local-conversion.md). The existing pure mappings and
their golden identities remain unchanged. Actual firmware/producer adoption
remains proposed; successful parsing or a caller's attestation does not prove it.

## Setup and command

Use Python 3.13 and uv 0.11.19 from the repository root on Windows. The lockfile
pins development tools and optional pyulog 1.2.2 / NumPy 2.3.5 artifacts.

```powershell
uv sync --frozen --extra ulog --no-python-downloads --cache-dir .uv-cache --python python
.venv/Scripts/python.exe telemetry_convert.py --job tests/fixtures/synthetic-conversion-job.json --output .local-discovery/demo-synthetic-001
```

The example produces three events and one rejection from four original slots.
The output directory must be new and its basename must equal the job's run ID.
An existing directory fails without modification. A deliberate replay needs a
new run ID, new ingestion time and a fresh destination. Input paths are resolved
relative to the job file. Outputs are local artifacts, not remote publication.
Use `--verify EXISTING_DIRECTORY` instead of `--output` for the
[read-only exact check](run-verification.md) with original job/source bytes and
matching runtime. It compares all three artifacts without replacing them; v1
or different-environment metadata is not a v2 exact match.

Omit `--extra ulog` for a synthetic-only environment. Synthetic runtime also
works with Python's `-S` option, independently of optional site packages. Tests
requiring the optional reader are marked `ulog` and skip when it is absent.

## Job boundary

The strict UTF-8 JSON job has exactly `job_version`, `mode`, `input`, `manifest`
and `delivery`. Unknown keys, duplicate keys and NaN/Infinity fail. The example
[job](../../tests/fixtures/synthetic-conversion-job.json) is executable documentation.

| Field | Contract |
| --- | --- |
| `job_version` | `bounded-conversion-v1` |
| `mode` | `synthetic` for literal JSON fixture records, `ulog` for binary encoding |
| `input` | Exactly `path`, trusted `source_log_id` and integer `size_bytes`; checksum must also match the manifest |
| `manifest` | Fields of `SourceManifest` or `ULogSourceManifest`; unrecognized fields fail; model defaults apply only where declared |
| `delivery` | Exactly `dataset_run_id`, `ingest_timestamp`, `replay_mode` |

Shared required manifest fields are `source_manifest_id`, `source_log_id`,
`vehicle_id`, `source_stream`, `native_timestamp_min_us`,
`native_timestamp_max_us`, `clock_anchor`, `retrieved_at`, `license_evidence`
and `privacy_review`. Synthetic jobs additionally require `fixture_specification`;
their parser attribution must be `literal-records-v1`. See the typed models in
[fleet_telemetry.py](../../fleet_telemetry.py) for all optional/default fields and
the pure ULog guide for required ULog source metadata.

The anchor contains `native_anchor_us`, `utc_anchor` and optional nullable
`anchor_uncertainty_us`. It is explicit and synthetic-fixed for this slice.
Timestamps use six fractional digits and `Z`; bounds use integer microseconds.
Publication time is allowed only where sample time is absent. Source identifiers
`source_manifest_id`, `vehicle_id`, `source_stream` are capped at 256 characters.
Run IDs match `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`. Blank/NUL/invalid Unicode
strings and nonlocal device/UNC input paths fail.

`mode` selects encoding, not provenance: authored ULog binaries retain
`source_type: synthetic`, synthetic privacy and delivery metadata. Real `ulog`
sources require embedded firmware SHA to match the selected manifest. The bridge
requires `parser_version: pyulog-1.2.2` and `field_definition_reference` equal to
`sha256:` plus the digest of the complete UTF-8 embedded F-message body,
including message name, colon, fields and terminal semicolon. It never hashes
only a field list or accepts an arbitrary URL at this bridge boundary.
Nonempty producer evidence is a caller attestation; its factual adequacy,
rights/privacy and civilian scenario still require review.

## Integrity and reader subset

[ulog_integrity.py](../../ulog_integrity.py) checks registered byte size and SHA-256
before structural interpretation. A receipt must come from a trusted external
registration; deriving it from the suspect bytes cannot detect clean-boundary
loss. Complete version-1 headers and frames, unique bounded nested/fixed-array
definitions, subscriptions and declared payload widths are required. Terminal
uint8 padding may be fully present or fully omitted, not partly truncated.

Supported messages are `B`, `F`, `I`, `M`, `P`, `A`, `D`, `L`, `S`, `O`.
[ADR-0010](../adr/0010-ulog-nested-and-service-frames.md) and the
format guide define nested layout and service-frame
limits. Flags must be all zero; parameter types are `int32_t` and `float`.
Appended sections, changed/reused definitions or subscriptions, unknown message
kinds and unsupported extensions reject the whole input. This subset deliberately
does not accept arbitrary flight logs. Dropout marks are observations, not a
count of lost measurements or proof of device-level completeness.

[ulog_reader.py](../../ulog_reader.py) gives the same verified bytes to the pinned
upstream parser, checks corruption and reconciles all framed stream counts.
The selected battery schema requires `uint64_t timestamp`, float voltage/current/
remaining, bool connection and uint8 source, with no separate sample timestamp.
Scalar conversion verifies types; bool bytes must be 0 or 1. Selected timestamps
may be equal but must not decrease. Other streams receive framing/count checks,
not session-clock validation. Ordinals are assigned before value filtering.

Synthetic fixture positions must already be exactly `0..N-1`; invalid positions
or decreasing in-bounds timestamps fail the source. Value-policy failures become
safe local rejection references. Whole-source metadata, framing or parser
failures publish no run. Source-level context errors are not multiplied into
one rejection per row. Duplicate identities and conflicting contents fail the
run rather than being silently discarded.

Limits are 64 KiB per job, 16 MiB per source, 100,000 synthetic records or ULog
frames (including metadata), and 64 MiB cumulative serialized events/rejections
plus semantic-digest input. All processing is bounded and in memory. These are
input/output budgets, not an exact process RSS guarantee. The reader redirects
parser diagnostics process-wide; use this local command serially, not as a
concurrent service API.

## Artifacts and reconciliation

Each completed directory has exactly these three files:

| File | Meaning |
| --- | --- |
| `events.jsonl` | Compact sorted-key UTF-8 canonical events in retained native order; schema `1.0.0` |
| `rejections.jsonl` | Safe manifest/stream/original ordinal, field and reason references; no raw payload |
| `run-manifest.json` | `bounded-run-v1` metadata, counts, versions, hashes and outcome |

New manifests pin `pipeline_version: bounded-converter-v2`, exact job-byte SHA,
source-byte SHA/size, safe source references, parser/runtime versions,
normalization/projection/digest versions, synthetic-time label, rejection
reasons and data-file byte hashes/lengths. It does not hash itself. ULog dropout
observations are included. Raw job paths, private evidence and source payloads
are not copied into it.

For this one-event-per-record mapping, `source_records = admitted_records +
rejected_records`, `unique_events = admitted_records` and `duplicate_events = 0`.
Empty accepted output is allowed when all value records reject. Status is
`completed` or `completed_with_rejections`; both exit 0. Source/job/IO failures
exit 2 with a fixed safe reason on stderr.

`bounded-semantic-digest-v1` hashes, in retained order, compact sorted-key JSON
lines containing `event_id` and the documented measurement projection. It
excludes ingestion/delivery/provenance/schema fields. Changing delivery metadata
changes the job SHA and event bytes while preserving identities and semantic
digest. This is an integrity/replay check, not proof of producer semantics.

Only after complete validation and reconciliation does the writer create an
adjacent temporary directory, flush/fsync files and rename it to the fresh
destination. Windows directory rename and Linux `renameat2` with `RENAME_NOREPLACE`
provide the no-replace boundary; unavailable operations and other operating
systems fail explicitly. Output symlink/junction ancestors are
rejected. Use a trusted local parent: hostile concurrent ancestor replacement
and power-loss durability are not established. An interrupted process may leave
an unpublished temporary directory; ordinary failures clean only the stage it
created. Run-ID uniqueness across different parents is the caller's duty.

## Verification and evidence

The following commands passed on Windows with CPython 3.13.1, pytest 9.1.1,
Ruff 0.16.5 and mypy 1.15.0:

| Exact command from repository root | Outcome |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp=.local-discovery/pytest-m1-features` | 316 passed |
| `.venv/Scripts/python.exe -m pytest -q -m "not ulog" --tb=short --basetemp=.local-discovery/pytest-m1-features` | 284 passed, 32 deselected |
| `.venv/Scripts/python.exe -m ruff check fleet_telemetry.py ulog_integrity.py ulog_reader.py telemetry_convert.py tests` | Passed |
| `.venv/Scripts/python.exe -m ruff format --check fleet_telemetry.py ulog_integrity.py ulog_reader.py telemetry_convert.py tests` | 10 files already formatted |
| `.venv/Scripts/python.exe -m mypy` | Passed, 10 source files |
| `uv lock --check --offline --cache-dir .uv-cache --python python` | Passed, 13 packages |
| `.venv/Scripts/python.exe .local-discovery/verify_bounded_conversion.py` | 231 local Markdown links/anchors and 3 demo artifact sets verified; 23 changed/created file hashes recorded |

The default system temporary directory is unwritable in this sandbox; the
verified workspace temporary path above is used for pytest fixtures. This is
not evidence of a clean-machine installation or a Linux test run. The suite
checks independent golden content, two-delivery replay, original ordinals,
strict metadata, malformed/truncated input, parser counts/types, no partial run,
duplicate/conflict refusal, output races, write failure, bounded output and safe
CLI failure. No real flight payload was used as an executable fixture.

Two local synthetic runs each produced 3 events and 1 rejection from 4 slots,
with identical IDs and semantic SHA:
`sha256:6d400c78a283e088eb15df0227e8248e05247e2147f1c4ef3bf8b8bcc6e62b6e`.
An authored binary ULog run produced 2 events from original positions `[0, 2]`
and 1 rejection at position 1. Repeating an occupied destination failed with
`output_exists` and left its artifacts unchanged. These runs remain ignored
under `.local-discovery/demo-synthetic-001`, `demo-synthetic-002` and
`demo-ulog-001`. Their jobs/input bytes and a verification record remain local.
The ignored `.local-discovery/bounded-conversion-verification.json` records the
exact check commands/results, demo counts/digests and implementation/document
hashes. Its standard-library verifier is retained beside it; neither is part of
the runtime or a redistributed flight fixture.

## Created and modified files in this increment

| Files | Change |
| --- | --- |
| [ulog_integrity.py](../../ulog_integrity.py), [test_ulog_integrity.py](../../tests/test_ulog_integrity.py) | Bounded framing/receipt gate and fault checks |
| [ulog_reader.py](../../ulog_reader.py), [test_ulog_reader.py](../../tests/test_ulog_reader.py) | Pinned bridge, types/counts/ordinal checks |
| [telemetry_convert.py](../../telemetry_convert.py), [test_conversion.py](../../tests/test_conversion.py) | Strict jobs, replay, reconciliation, fresh atomic output and failure checks |
| [ulog_binary.py](../../tests/ulog_binary.py), [synthetic-conversion-job.json](../../tests/fixtures/synthetic-conversion-job.json) | Authored binary builder and runnable synthetic job |
| [pyproject.toml](../../pyproject.toml), [uv.lock](../../uv.lock) | Optional pinned reader dependencies, test marker and type-check scope |
| [ADR-0009](../adr/0009-bounded-local-conversion.md), [ADR-0008](../adr/0008-ulog-input-integrity-gate.md), [ADR-0006](../adr/0006-ulog-discovery-tooling.md) | Selected increment, gate implementation and dated dependency adoption |
| [README](../../README.md), [architecture](../architecture.md), [contracts](../data-contracts.md), [roadmap](../roadmap.md), [testing strategy](../testing-strategy.md) | Current boundaries, versions, evidence and remaining gates |
| Synthetic guide, pure ULog guide, parser probe, discovery review, [this guide](bounded-conversion.md) | Preserve historical evidence and link current implemented scope |

Existing pure runtime/fixtures are unchanged. The later setup/CI follow-up linked
above supplies fresh project-environment evidence and a workflow; hosted CI and
reviewed real-source acceptance/compatibility remain pending. No services,
infrastructure or benchmark were added. Git metadata is absent; no commit or
remote publication was performed. Rollback removes this capability and optional
dependencies; retain completed runs according to their retention needs. No
persistent dataset migration or automatic deletion is introduced. The smallest
next acceptance task is reviewed primary-source producer/provenance evidence
and a real-source manifest after the completed format extension.
Real-source adoption remains separate.
