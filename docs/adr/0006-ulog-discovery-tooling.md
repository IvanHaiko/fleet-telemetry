# ADR-0006: Isolate ULog discovery from the normalization runtime

**Status:** Selected for the authorized local discovery experiment only.
The original research scope is unchanged; a dated follow-up below links separate
optional runtime adoption. Actual-source `ulog-battery-v1` adoption remains proposed.

**Date:** 2026-10-19

## Context

Battery mapping needs evidence from an actual ULog, including embedded message
definitions, firmware metadata, stream instances, counts and timestamp ranges.
The synthetic runtime has no parser or NumPy dependency. A binary parser written
for one experiment would add correctness and maintenance risk.

## Decision

Use the official PX4 pyulog parser source at release `v1.2.2`, commit
`e328bd3359c0d2ef817cbc03491df44fe5e5c750`, for local discovery. Use only its
core reader, package initializer and required PX4 helper, retaining its license. Run outside the
project virtual environment with the available Python 3.12.14 and NumPy 2.3.5.
Compatibility of that combination is an experimental result to record, not a
claim about the project's supported Python 3.13 runtime.

Store exact downloaded sample bytes, parser sources, license, checksums and
discovery output in ignored `.local-discovery/`. Review repository licensing
before acquisition; keep source coordinates, identifiers and other private
metadata out of the public report. Repository licensing is acquisition evidence,
not proof of data-subject consent or permission to redistribute flight data.
Do not redistribute the log as a project fixture without a separate review.

No project dependency, lockfile change, adapter or service is introduced.
Costs are bounded local download, disk and analysis time; no cloud spending.
Future adoption requires Python 3.13 compatibility checks, pinned dependencies,
malformed/truncated log tests and review of ordinal preservation. Discovery
scripts are experiment artifacts, not a supported conversion command.

## Authorized compatibility probe — 2026-10-19

Extend the local experiment to project CPython 3.13.1 with NumPy `2.3.5` and
the same pinned pyulog sources. Use a separate virtual environment under
ignored `.local-discovery/`, installing only the NumPy wheel without dependency
resolution or source builds. Its release metadata lists Python 3.13 support;
the experiment must still demonstrate the required parser behavior locally.
The selected [NumPy release](https://pypi.org/project/numpy/2.3.5/) is a comparison
pin shared with the earlier Python 3.12 experiment, not a latest-version claim.

This adds a temporary research dependency only. Project `dependencies`, lockfile
and runtime environment remain unchanged. Cost is one bounded wheel download
and local disk/test time; no services or cloud spending. Retain wheel provenance
and environment metadata locally. Alternatives are postponing the probe or
prematurely adopting the parser in the production toolchain; neither supplies
the needed isolated compatibility evidence now.

Check real-sample inventories and embedded field types, native boolean/scalar
conversion, original row positions, truncated messages, malformed data and
unsupported compatibility flags. Use project-authored tiny binary cases for
error experiments, keeping original logs unchanged and restricted. Do not infer
losslessness from a successful parser return or `file_corruption: false`.
Production parser adoption, framing/integrity policy and producer attribution
remain separate gates. Removing the isolated environment after preserving its
evidence has no project dependency or canonical-data migration impact.

The completed probe matched the prior battery
inventories on Python 3.13.1, but demonstrated silent truncated tails and ordinal
shift after a skipped middle record. [ADR-0008](0008-ulog-input-integrity-gate.md)
proposes the integrity boundary required before production row enumeration.
The local compatibility result does not adopt the parser for canonical emission.

## Alternatives

- A custom binary parser avoids NumPy but duplicates format handling and
  introduces unnecessary maintenance and validation work.
- Adding pyulog directly to the project runtime would prematurely select the
  production parser before field, privacy and compatibility review.
- External log-viewing services add data disclosure without resolving the
  requirement for reproducible local evidence.

## Acceptance and rollback

Record the input checksum, parser/runtime versions, parse outcome, firmware,
embedded fields, per-stream counts, time ranges/discontinuities and blockers.
Discovery does not accept the mapping or establish replay correctness. Stop on
unsupported semantics or parser errors rather than fabricating canonical data.
Rollback requires no persistent-data migration: the ignored experiment directory
can be removed after retaining any needed evidence; production files are unchanged.

## Related documents

[Data contract](../data-contracts.md#proposed-ulog-mapping-ulog-battery-v1),
[M1 roadmap](../roadmap.md), [testing strategy](../testing-strategy.md).

## Separate optional runtime adoption — 2026-10-19

Following the isolated probe, the maintainer explicitly authorized a connected
M1 implementation. [ADR-0009](0009-bounded-local-conversion.md) separately selects
an optional `ulog` project extra pinning pyulog `1.2.2` and NumPy `2.3.5` in the
existing lockfile. The [implemented bounded gate](0008-ulog-input-integrity-gate.md)
precedes strict upstream decoding and all-stream count reconciliation. This is
a later runtime decision; it does not rewrite the research-only installation,
unchanged-runtime statements or results recorded above.

The [bounded conversion guide](../guides/bounded-conversion.md) describes the local
command, authored-fixture evidence and supported subset. Synthetic conversion
retains a standard-library runtime. The optional reader does not authorize
redistribution of the restricted discovery logs, independently establish actual
producer attribution or prove general firmware/parser compatibility. No service,
CI workflow or cloud resource is introduced by this adoption.
