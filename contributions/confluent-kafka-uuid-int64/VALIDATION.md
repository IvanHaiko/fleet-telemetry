# Validation observed on 2026-10-24

| Check | Result |
| --- | --- |
| Standalone native regression, stock Windows x64 CPython 3.13.1 / SDK 2.16.0 | Expected failure: one method, five failing literal subcases, no skips |
| Same test, local UUID-only repaired SDK 2.16.0+fleet.uuid1 | Pass: one method and ten signed-half pairs |
| Same repaired Windows test under `-O` | Pass, no skips |
| pytest discovery/execution of the standalone regression | One passed test, ten passed subtests |
| Stock Linux x86-64 CPython 3.13.1 / SDK 2.16.0, normal and `-O` | Pass in both modes, no skips |
| Ruff check and format, both supplied Python files | Pass |
| Strict mypy, read-only broker script | Pass |
| Full master patch and related-PR test patch | Apply/check/reverse/reapply match exact pinned preimages/outputs |
| Actual Windows AdminClient against fresh Kafka 4.4.0 topic, stock SDK | Expected UUID mismatch, exit 1 |
| Same topic and oracle, local repaired SDK | Complete strings and signed getters match CLI bytes, exit 0 |

The fresh synthetic metadata-only example independently obtained from Kafka CLI
was `RNBWTSOBRBiMiT5_UJniGw`. Its complete 16 bytes were
`44d0564d238144188c893e7f5099e21b`. Stock Windows returned
`0000000023814418000000005099e21b`; the repaired SDK returned all original bytes.
The topic UUID was compared again afterward and was unchanged. No record was
published and no consumer group/progress was created by this reproduction.
The separately owned local broker finished stopped.

The full patch was checked against master commit recorded in `provenance.json`;
the test-only patch was checked against PR #2325's recorded head. Checks used
source-only exports of their exact relevant files, without a Git commit or push.
The submitted C change preserves the previously tested UUID-only repair; no
official MSVC/upstream-head build, whole upstream suite, PR-head runtime test,
offset/timestamp regression or Windows CI modification is claimed.

Original SDK environments and earlier failed observations were retained.
The package contains source patches, standalone reproductions and sanitized
validation summaries only. It contains no project receipt inventory, broker
volume snapshot, private logs, credentials, vehicle data or compiled wheel.
