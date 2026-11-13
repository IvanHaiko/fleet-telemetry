# Read-only bounded run verification

## Scope — 2026-10-20

The M1 converter now verifies an existing completed run against the external
job and registered source. It detects modified, missing or unexpected artifacts
without writing a replacement run. Both operations reuse bounded preparation;
there is no second normalizer.

```powershell
.venv/Scripts/python.exe telemetry_convert.py --job tests/fixtures/synthetic-conversion-job.json --verify PATH/TO/demo-synthetic-001
```

Replace the path with the completed directory. `--verify` and `--output` are
mutually exclusive; its basename must match the job's run ID. Synthetic
verification works with Python `-S`; authored binary ULog jobs require the same
pinned optional packages as conversion. The shared
`./scripts/check-m1.ps1 -Profile ulog -Offline` command now converts and verifies
its fresh demonstration, including in the prepared CI workflow.

## Exact verification boundary

The verifier reloads the strict bounded job, verifies source size/checksum,
repeats input validation and normalization, and regenerates expected bytes for
`events.jsonl`, `rejections.jsonl` and `run-manifest.json`. This covers identities,
ordinals, counts, hashes, semantic digest and provenance. A modified run cannot
pass merely by recomputing its own hashes to match altered events.
The external job and source receipt must themselves be trusted; replacing the
entire job/source/run set is outside this consistency check's authenticity claim.

Reads are bounded by expected artifact lengths; directory enumeration stops at
the fourth entry. Exactly three regular files are required. Symlink/junction
ancestors and artifact entries fail. Verification creates no staging directory
and rewrites no run artifact. Use a trusted local parent: protection against
hostile concurrent ancestor/file replacement is not established.

Success exits 0 with `status: verified` and reconciled counts. Failure exits 2
with a safe code, such as `run_artifact_mismatch`, `invalid_run_contents` or an
existing input-validation reason. No raw measurement or private parser
diagnostic is returned. The command does not repair or remove damaged output.

This is byte-exact replay verification under the current pinned pipeline and
runtime. It needs the original job bytes, registered source and matching
environment. Job/output reformatting, different ingestion metadata, a changed
Python/parser version or an older pipeline manifest can cause a mismatch.
Failure therefore means exact reproduction was not established; it does not
alone distinguish tampering from version/environment drift. Historical runs
remain unchanged and require their recorded software/environment. This adds
no generic wire reader, source-free authenticity proof or digital signature.

## Primary-source provenance follow-up

The pinned upstream file history identifies its addition in
[commit 0197eba](https://github.com/PX4/pyulog/commit/0197ebaad28a1d73c366acf0064311e3d289ec40),
associated with [PR 70](https://github.com/PX4/pyulog/pull/70) for SQLite database
support. The commit, PR body and 16 issue/review comments inspected on
2026-10-20 do not supply a flight-generation procedure, actual battery-producer
attribution or independent flight-data permission/civilian-scenario evidence.
This bounded review does not establish that evidence is absent elsewhere.
The original commit's Git blob ID also matches the retained file bytes, linking
the inspected history to this exact candidate without redownloading the log.

The exact retained log reports `CUBEPILOT_CUBEORANGE`, `NuttX` and `SYS_HITL: 0`,
without groundtruth streams. These self-reported metadata do not establish
simulation provenance or independently authenticate a physical flight.
Third-party descriptions are insufficient to relabel it a project-authored or
verified simulator fixture. Repository license evidence remains as recorded in
the acquisition; actual source adoption remains proposed. No real-source
manifest, normalized run or redistributed flight fixture was created.

Filtered official-history evidence and platform-only observations are retained
under ignored `.local-discovery/provenance-20261020/`. Original acquisition/log
bytes are unchanged. This verifier advances M1 while source-adoption evidence
remains open.

## Checks and changed files

Existing golden/two-delivery, authored binary, standard-library CLI and safe
diagnostic scenarios now exercise verification. One new focused test forges
events and their artifact/semantic hashes, alters metadata and checks
missing/extra files; failures leave supplied artifacts unchanged. Existing
source validation and independent golden expectations are reused.

Final commands, outcomes and hashes are retained in
`.local-discovery/run-verification-evidence.json`. The pipeline remains
`bounded-converter-v2`: extracting preparation and adding a separate read-only
operation changes no conversion bytes. Fixtures and dependencies are unchanged.

The final shared command passed **331 tests**, lock consistency, Ruff, format
(10 files) and strict mypy (10 source files), followed by successful `-S`
conversion and verification. An independent review reran the 27 converter
checks and reported no blockers. Artifact checks confirmed all three conversion
files are byte-identical to the preceding v2 run; verification preserves their
bytes. The retained verifier command is
`.venv/Scripts/python.exe .local-discovery/verify_run_feature.py`; it also
resolved 317 local Markdown links/anchors, verified all 12 acquisition hashes
and matched the original Git blob to the retained source bytes. The shared
command used workspace-local `TEMP`/`TMP` and `UV_LINK_MODE=copy` for this sandbox.

| Files | Change |
| --- | --- |
| [telemetry_convert.py](../../telemetry_convert.py) | Shared preparation, verification API and `--verify` |
| [test_conversion.py](../../tests/test_conversion.py) | Existing checks extended; one tampering/read-only regression |
| [check-m1.ps1](../../scripts/check-m1.ps1) | Verify the completed smoke run with `-S` |
| [README](../../README.md), [contracts](../data-contracts.md), [architecture](../architecture.md), [roadmap](../roadmap.md), [testing strategy](../testing-strategy.md), [converter guide](bounded-conversion.md), [setup guide](m1-checks.md), [this guide](run-verification.md) | Capability, exact boundary, evidence and provenance limits |

Rollback removes verification and restores inline preparation without changing
completed data. No service, framework, dependency or persistent-state migration
is introduced. Git metadata is absent; no commit, publication or hosted workflow
dispatch was performed. M1 still needs actual-source acceptance evidence and a
hosted CI run after maintainer publication. The next source-adoption step needs
trustworthy producer/provenance and usage evidence; do not manufacture
attestations to satisfy a manifest.
