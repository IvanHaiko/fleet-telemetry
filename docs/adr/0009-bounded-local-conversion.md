# ADR-0009: Add a bounded local converter and optional ULog reader

**Status:** Selected for the authorized M1 implementation; real-source producer
attribution and redistribution remain separate review gates.

**Date:** 2026-10-19

**Partial supersession — 2026-10-20:**
[ADR-0016](0016-linux-no-replace-publication.md) replaces only the initial
Windows-only publication restriction with a tested Linux no-replace boundary.
The original decision and its initial evidence remain below.

## Problem and decision

Pure normalization and the parser probe do not yet give a reproducible local
file conversion boundary. The maintainer authorized several connected M1
features: whole-input integrity, a pinned parser bridge and a bounded local
command with explicit source/outcome reconciliation. Keep these responsibilities
separate and stop before Kafka, containers, services, CI publication or cloud work.

Implement a standard-library integrity/count gate, followed by the upstream
semantic reader and the existing pure mapping. Add an optional `ulog` dependency
group pinning pyulog `1.2.2` and NumPy `2.3.5`, the combination exercised in the
Python 3.13 probe. Pin artifact hashes in the existing uv lockfile. Synthetic
conversion remains standard-library-only. Package adoption here supports the
declared bounded reader subset, not arbitrary ULog or proven producer attribution.

The command accepts a strict versioned JSON job, exact source checksum and byte
size, typed manifest/anchor and explicit delivery metadata. It validates all
bounded input before publishing a fresh output directory containing events,
safe rejection references and a versioned run manifest. Record byte/output
hashes, normalization/projection versions, counts and deterministic semantic
content; never derive identity from delivery time, file paths or output names.
Refuse existing destinations and preserve them unchanged on failure.

The initial publication implementation targets the documented Windows runtime,
where directory rename to an existing target fails rather than replacing it.
Other operating systems must receive an explicit unsupported-publication error
until an atomic no-replace strategy is implemented and tested. This limitation
does not restrict in-memory integrity/reader/normalization logic.

## Alternatives and impact

- An unpinned reader or a global research import would make the runtime difficult
  to reproduce. The optional locked group makes installation explicit.
- A custom semantic ULog parser duplicates upstream format ownership and is
  excluded; the integrity gate covers framing/counts and the supported subset.
- Streaming output before validating the full source permits partial datasets
  after late corruption; bounded all-input validation avoids that release window.
- Reusing or overwriting a run directory risks mixing rebuilds; require a new
  destination and explicit new run identity instead.
- A service, scheduler or additional orchestration framework adds no value to
  the current file-boundary acceptance criterion.

Maintenance consists of a small input boundary, parser type adapter, job/output
contracts and tests. NumPy adds a platform wheel and memory use; hard input and
record limits bound this experiment. There is no cloud/service cost. Local
temporary output is adjacent to its destination; retain input evidence and
clean only temporary artifacts created by the converter on its own failure.

## Evidence and rollback

Demonstrate authored valid binaries, corrupt/truncated/unsupported input, original
ordinals after value rejection, strict metadata/schema checks, repeatable IDs
and semantic content across delivery runs, count/hash reconciliation, and no
published output on whole-source failure. Existing pure checks must still pass.
Record exact commands, environment, unsupported subsets and operational limits.

No existing canonical dataset or deployed service is migrated. Removing the
optional group and new modules rolls back this capability; preserve already
published run artifacts for their declared retention. Corrections to accepted
mapping behavior retain the existing normalization-lineage rules. This record
supersedes no accepted architectural boundary; ADR-0008's proposed integrity
policy is implemented with its exact supported subset documented alongside it.

## Related documents

[Integrity gate](0008-ulog-input-integrity-gate.md),
parser probe, [contracts](../data-contracts.md),
[roadmap](../roadmap.md), [testing strategy](../testing-strategy.md).
