# ADR-0025: Bounded Windows Kafka UUID boundary repair

**Status:** Accepted for the maintainer-authorized bounded Windows correctness
repair on 2026-10-24, with [evidence and limits](../case-studies/windows-kafka-uuid-repair.md).
This is not an upstream release or complete M4 acceptance.

## Problem and repair boundary

The pinned confluent-kafka 2.16.0 Windows CPython 3.13 wheel loses the high
32 bits of each described topic UUID half. Its UUID half getters also narrow
signed 64-bit values. Linux x86-64 passes the same checks. The release C bridge
uses C `long` at those boundaries, while Windows uses LLP64 (`long` is 32 bits).
See the retained Windows failure and
Linux comparison.

Investigate a narrowly patched build of the same released C extension: replace
only UUID-to-Python integer conversions with signed 64-bit CPython conversions.
Do not reconstruct identity from truncated values, change UUID encoding, alter
Kafka records, reset progress, rewrite historical receipts or suppress failures.
The existing librdkafka 2.16.0 DLLs and all Python package files stay byte-identical
except explicit local distribution metadata and the rebuilt extension.

## Build experiment and alternatives

No MSVC Build Tools or Windows cross-compiler was found in the current local
environment. Try the official portable Zig 0.17.0 Linux x86-64 C toolchain for
a Windows x86-64 build. It adds no system installation or runtime service and is
confined to ignored project-owned build scratch. The official archive SHA-256 is
`1cbe9df9f27e6b78d14ccbca43b6703a404ef79ef1c463de901d7f088d4e2026`.
Validate the actual compiler/linker/Python/librdkafka ABI before any adoption.
A compilation result alone is insufficient.

The exact PyPI 2.16.0 source archive SHA-256 is
`8268b8763a0c0503a99a55a9cac0132ed010932135d4222f67e2c804d1597508`;
the original cp313 Windows wheel SHA-256 is
`3b00c1ea376d80288b03f36389d603c3d9fef9f62a5e180f48565ac1c6368004`.
Pin librdkafka headers, compiler, Python headers/import library, all seven
extension sources and final artifact hashes. Preserve original installed SDKs.

Alternatives: wait for an upstream release (no released fix found in the current
metadata); use Linux only (already verified, but does not fix the requested
Windows boundary); install MSVC Build Tools (larger system/toolchain change);
or use another Kafka client (new dependency/API/recovery validation). A private
memory-layout or binary-edit workaround is excluded. Do not adopt an unexplained
binary modification or a lossy Python-level identity workaround.

## Cost, validation and rollback

The portable compiler download is approximately 55 MiB, plus bounded build/cache
and source scratch. No cloud spend, broker upgrade or additional orchestration.
A maintained derivative adds source-patch, toolchain/ABI, license and upgrade
review work; prefer an equivalently tested upstream fix when available.

Freeze independent full-width UUID tests before patching. Require signed-half
edge cases and values differing only in high bits; known stock Windows failure;
an independently repeated build; complete changed-file/ABI inventory; full
broker UUID comparison on Windows; exact records, progress and recovery checks;
Linux compatibility; and separate restricted read-only review. Keep the original
failed observations. Pin an explicit local derivative version rather than
representing the wheel as an official unmodified release.

Project entry points must refuse an uncorrected UUID boundary before a broker
mutation. A corrected runtime does not retroactively certify historical IDs;
their audit/migration remains separate. No event identity/schema changes.
Rollback selects the preserved stock environment with explicit safe refusal,
retains wheels/source/evidence/volumes, and never rewrites old offsets or receipts.

## Observed adoption boundary

The exact derivative `2.16.0+fleet.uuid1` passes independent frozen probes,
Windows broker CLI identity/read/expiry and existing M2 recovery checks.
Unchanged controls reproduce the stock defect. Two final fresh builds have
matching hashes after omitting variable unshipped debug metadata with `-s`;
the earlier 20-byte reproducibility failure remains retained. The source patch
still changes only four UUID conversion sites plus local allocation cleanup.
Original SDK Python files, DLLs and license bytes are unchanged.
The recipe/pins, five-purpose-method suite and M2/M3 guard are adopted only for
this profile. The experimental archive native reader, historical UUID audit,
full archive recovery and general SDK/production support are not accepted.
