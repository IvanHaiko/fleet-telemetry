# ADR-0008: Propose a whole-input integrity gate before ULog row ordinals

**Status:** Implemented for the bounded subset selected on 2026-10-19; see the
dated adoption below. Originally proposed after the isolated parser probe.
The original flat-definition/message subset is partially superseded by
[ADR-0010](0010-ulog-nested-and-service-frames.md); its integrity requirements
and the original adoption record below remain unchanged.

**Date:** 2026-10-19

## Context and evidence

The Python 3.13 parser probe found that pinned
pyulog `1.2.2` can return partial data with `file_corruption: false` after an
incomplete tail. It can skip an undersized middle data message, set the
corruption flag, and return an array whose row indices no longer match original
record positions. This contradicts using a successful return and array
enumeration alone as proof of identity correctness.

The [ULog specification](https://docs.px4.io/main/en/dev_log/ulog_file_format)
permits readers to discard an unfinished final message. That tolerance is useful
for log inspection; canonical admission needs an explicit disposition and cannot
silently treat incomplete input as a complete bounded source.

## Proposal

Before canonical emission, verify exact bytes against the registered source
checksum and expected size; establish complete message framing for the selected
bounded source; run the pinned upstream parser in strict string mode; and fail
the whole input on parser exceptions, reported corruption or unsupported
definitions/flags. Retain safe source/error evidence and emit no canonical
events from a failed input. Do not invent per-record identity for unreadable
bytes or enumerate rows after parser recovery.

Use a minimal framing/integrity check alongside the upstream semantic parser,
not a replacement binary parser. A framed-message count reconciliation for the
selected stream must be resolved before claiming original ordinal preservation.
Appended sections, subscription changes, padding and unknown compatible messages
need explicit support or a visible unsupported-input error; do not generalize
from the tiny probe examples.

After whole-input validation, retain row positions before value filtering.
Verify embedded field types and convert their scalar representations explicitly.
Native connection values `0`/`1` become booleans only under a verified `bool`
definition; reject other encodings rather than applying truthiness. Do not
silently cast `uint8_t connected` as the supported boolean schema. Check clock
order/discontinuities independently; the upstream reader does not enforce the
required session split for the tested decreasing-time case.

A file cut exactly between complete frames is indistinguishable from a shorter
valid log without trusted external expectations. Registered checksum/size and
source receipts can detect alteration relative to known bytes; they cannot
prove loss-free device acquisition before registration. Preserve dropout marks
as loss evidence without fabricating unknown missing record ordinals.

## Alternatives and impact

- Parser return/`file_corruption` alone fails the demonstrated tail cases.
- Per-row continuation after corruption can change measurement identities.
- An upstream parser exposing exact positions, truncation and recovery status
  could replace some guard responsibilities after a separately pinned and
  tested compatibility review.
- A custom semantic ULog parser duplicates format ownership and is outside scope.

No service, framework, production dependency or cloud resource is adopted by
this proposal. A future guard adds a small maintained input boundary and tests;
its exact supported subset must be documented before implementation. The
existing pure mapping remains usable on validated records.

## Acceptance and rollback

Before adoption, demonstrate the probe's truncated/malformed cases fail visibly,
valid input counts and source positions reconcile, invalid values retain their
original positions, and no canonical output escapes a whole-input failure.
Include clean-boundary truncation against trusted source expectations and state
the remaining acquisition-loss limit. Review producer attribution separately.

This record supersedes no accepted decision. No persistent canonical data is
changed; revising a proposed guard requires no migration. Once mapping behavior
is accepted, corrections retain the existing normalization-lineage rules.

## Bounded adoption — 2026-10-19

The maintainer explicitly requested several connected implementation features.
This authorizes the integrity boundary, pinned upstream bridge and local file
converter described in [ADR-0009](0009-bounded-local-conversion.md). The original
proposal and research findings above remain the record of why the boundary was
needed; this dated update selects its limited implementation rather than
silently changing an accepted decision.

`ulog_integrity.py` verifies external SHA-256/byte-size expectations before
scanning all complete message frames. Input is bounded to 16 MiB and 100,000
total frames. The supported message types are `B`, `F`, `I`, `P`, `A`, `D`, `O`;
definitions are flat primitive fields/arrays with checked packet widths.
Terminal padding may be complete or omitted, with partial padding rejected.
Unknown messages and flags, appended data, subscription replacement/removal and
unsupported definitions fail visibly. Dropout count and duration are retained
as loss evidence, without inventing missing source ordinals.

`ulog_reader.py` invokes the optional pinned pyulog reader on the same verified
bytes, in strict string mode. It rejects exceptions, reported corruption and
stream/count mismatches before returning selected rows. The manifest binds the
complete embedded battery definition by its UTF-8 SHA-256 digest. Required field
types and NumPy scalar widths are checked, including explicit `bool` byte `0`/`1`
conversion. Selected timestamps must not decrease; equal times retain distinct
ordinals. Every framed stream's record count reconciles, while value mapping
remains a separate pure function.

The [local converter](../guides/bounded-conversion.md) validates all outcomes before
releasing a new run directory. Authored binary and run tests cover malformed
input, preserved indices and failure before final output. Exact final commands
and results belong to that guide. The local bridge serializes its parser calls;
upstream diagnostic redirection is process-global, so this does not establish
safe use amid unrelated concurrent threads.

Real producer attribution, complete firmware-policy applicability and source
rights remain review gates. Matching firmware metadata and a caller attestation
cannot independently prove the producer. Checksums detect change relative to
registered bytes, not loss before registration. No services, CI, unrestricted
ULog support or cloud resources are adopted. Removal of these new modules and
the optional dependency group rolls back the feature without migrating existing
datasets; retain completed run evidence according to its declared retention.

## Related documents

[Discovery tooling](0006-ulog-discovery-tooling.md),
[value policy](0007-ulog-battery-value-policy.md),
[data contracts](../data-contracts.md), [testing strategy](../testing-strategy.md).
