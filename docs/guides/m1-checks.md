# M1 setup checks and CI

## Scope and commands

This 2026-10-19 follow-up prepares CI and exercises the existing M1 checks in
separate fresh project environments. It adds no telemetry behavior or tests.
The maintainer's test preference is recorded in [the contributor guide](../../CONTRIBUTING.md): checks
must establish meaningful invariants or failure risks and reuse existing
coverage. Increasing test counts is not an objective.

The 2026-10-20 Linux publication follow-up records
successful local M1 suites on Linux and Windows. The subsequent setup increment
moves the shared check logic into a standard-library Python runner and extends
the prepared CI matrix to both platforms. Local evidence does not establish
hosted execution. The original 2026-10-19 results below remain historical.

With Python 3.13 and uv 0.11.19 available on Windows or Linux:

```sh
python scripts/check-m1.py --profile synthetic
python scripts/check-m1.py --profile ulog
```

Use `python3.13` in place of `python` where that is the installed interpreter
name. The runner selects its own interpreter for uv setup and refuses other
Python minor versions and platforms before invoking uv. It resolves the project
from its own location, so an absolute script path also works outside the root.
On Windows the existing `./scripts/check-m1.ps1 -Profile synthetic` and equivalent
`ulog` invocation delegate to this runner with the original parameter names.
Run profiles sequentially in one checkout: each sync owns that checkout's `.venv`.
Use separate source copies for parallel lanes.

The [shared script](../../scripts/check-m1.py) checks lockfile consistency, installs
the frozen lockfile, checks the optional-dependency boundary, runs Ruff,
formatting, mypy and the existing pytest suite, then executes the documented
synthetic conversion with Python `-S`. Its 2026-10-20 follow-up also performs
[read-only verification](run-verification.md) and
[canonical reader validation](canonical-reader.md) of that output. Each smoke run has
a fresh parent directory under
`.local-discovery/m1-check-*`; it retains the run artifacts and refuses to
reuse existing output. The base fixture's run ID remains unchanged because each
isolated check is its own workspace. These outputs are disposable verification
evidence, not a shared dataset registry.

`--offline` requires the complete locked artifacts already cached. Use
`--cache-directory /absolute/cache/path` to share a download cache across fresh
workspaces. The PowerShell wrapper retains `-Offline` and `-CacheDirectory`.
The environment and tool-state caches remain local to each project. Both uv
commands disable automatic interpreter downloads; `lock --check` verifies
consistency before `sync --frozen` installs. See the upstream
[uv CLI reference](https://docs.astral.sh/uv/reference/cli/). The script checks
every external command's exit code; a failing check stops the lane.
Pytest receives a fresh owned `pytest` subtree inside the retained smoke parent,
so it never clears a previous check's scratch directory. An evidence parent
resolving outside the project is rejected. Trusted project ancestors remain
required; concurrent hostile path replacement is outside this setup boundary.

## Prepared workflow

The 2026-10-21 maintenance refactoring adds
`telemetry/` to the shared lint/format/type source list. Copy that package along
with the root modules when preparing a source-only workspace. Before uv setup,
the runner checks root, package, script and test Python files and fails if any
contains 500 or more lines. It excludes local environments and evidence trees.
Existing workflow commands and dependency profiles are unchanged.

[m1.yml](../../.github/workflows/m1.yml) configures four independent jobs:
`windows-2025` and `ubuntu-24.04`, each with synthetic dependencies only or the
optional ULog extra. These are explicit labels from the official
[runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Each lane calls `python scripts/check-m1.py --profile <profile>` using Bash,
available on both hosted targets. The existing action SHAs and dependency pins
are retained.
It is configured for push, pull-request and manual events, with a 15-minute
timeout per job and read-only repository contents permission. Checkout does not
persist credentials. There are no dataset downloads, artifact uploads, services,
deployment or publication steps.

Action references were resolved through the official GitHub release/commit API
on 2026-10-19 and pinned to full SHAs:

| Action | Release | SHA |
| --- | --- | --- |
| Checkout | [v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| Setup Python | [v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0) | `5fda3b95a4ea91299a34e894583c3862153e4b97` |

The workflow installs uv `0.11.19`; the project lockfile pins the Python tools
and optional reader packages. `.python-version` selects the supported 3.13
minor line, so the hosted patch version may differ from the local 3.13.1
observation. Runner images and preinstalled bootstrap pip are managed by GitHub;
this is not a fully immutable machine image. The official
[workflow reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
defines event, permission and job semantics.

CI is configured locally, not demonstrated on a hosted runner. This directory
has no Git metadata or remote. No workflow was dispatched, repository created,
commit made or source published. The maintainer controls later publication.

## Original Windows clean-environment evidence

Two separate source copies under ignored `.local-discovery/clean-m1-*` received
new virtual environments from the frozen lockfile. Copies included runtime,
tests, fixtures and documentation, because the existing golden-vector test reads
the contract example directly. No preexisting virtual environment, Ruff/mypy
cache or research parser source was copied. Both reused the workstation's
installed CPython 3.13.1, uv 0.11.19 and download cache; this demonstrates fresh
project setup on the same Windows host, not a fresh OS or hosted execution.

Each lane ran this command in its own source copy, with the original workspace
cache supplied as an absolute path:

```powershell
./scripts/check-m1.ps1 -Profile synthetic -Offline -CacheDirectory <repo>/.uv-cache
./scripts/check-m1.ps1 -Profile ulog -Offline -CacheDirectory <repo>/.uv-cache
```

| Observation | Result |
| --- | --- |
| Synthetic environment | pyulog and NumPy absent; existing optional-reader checks skip |
| ULog environment | pyulog 1.2.2 and NumPy 2.3.5 required before running checks |
| Existing tests | Synthetic: 284 passed, 32 skipped; ULog: 316 passed |
| Quality checks | Lock consistency, Ruff, format and strict mypy passed in both environments |
| Standard-library command | Four original slots reconcile into three events and one rejection |

The first installation attempt hit sandbox restrictions while writing uv's
Windows executable wrappers in the system temporary directory. Retrying with
per-lane `TEMP`/`TMP` under the workspace and `UV_LINK_MODE=copy` allowed the
locked installation. These overrides are local environment accommodations,
not new project dependencies or hosted-run requirements. An initial script run
also exposed a missing temporary-directory parent; the shared script now creates
it. No extra test was needed to expose or verify the fix.

The ignored `.local-discovery/m1-setup-verification.json` records exact commands,
environment, logs and relevant hashes. No raw flight data is used or published.
The original converter [316-test evidence](bounded-conversion.md#verification-and-evidence)
remains a historical result; this follow-up reuses that suite.
The retained standard-library verifier also checks 250 local Markdown links and
anchors and confirms the exercised runtime, tests, contract, lock and check
script match the working sources byte-for-byte. Its command is
`.venv/Scripts/python.exe .local-discovery/verify_m1_setup.py`.

## Original setup file inventory and remaining work

| File | Change |
| --- | --- |
| Private working instructions | Original maintainer preference for purposeful tests; the public policy now lives in the [contributor guide](../../CONTRIBUTING.md) |
| [scripts/check-m1.ps1](../../scripts/check-m1.ps1) | Original shared setup command; now delegates to the Python runner |
| [.github/workflows/m1.yml](../../.github/workflows/m1.yml) | Original Windows lanes; now four Windows/Linux dependency lanes |
| [README](../../README.md), [roadmap](../roadmap.md), [testing strategy](../testing-strategy.md), [converter guide](bounded-conversion.md), [this guide](m1-checks.md) | Distinguish configured CI, local setup evidence and remaining acceptance |

No runtime, contract, fixture, dependency lock or test file changes are needed.
Rollback removes the workflow and check script; completed verification runs can
be retained independently. Hosted CI still needs its first run after authorized
publication. Real-source rights, producer attribution, firmware-policy review
and producer-reader compatibility remain M1 acceptance gates. The next local
task identified by this setup slice was a bounded evidence review of the
retained candidate source. That review is now complete
and identifies concrete runtime-format gaps; it keeps actual source adoption
proposed. A parser success or synthetic test count does not establish adoption.


## Windows/Linux shared-command increment — 2026-10-20

The new runner owns setup and verification on both supported platforms; the
PowerShell wrapper forwards its established parameters. The CI matrix is the
Cartesian product of two operating systems and two dependency profiles, as
specified by the official [matrix guide](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations).
This is a tooling increment with no new dependency, contract, telemetry behavior
or product test. The runner itself joins the existing Ruff/format/mypy inputs.
It uses explicit dependency checks that also remain active under Python `-O`.

Local commands were:

```powershell
./scripts/check-m1.ps1 -Profile synthetic -Offline
./scripts/check-m1.ps1 -Profile ulog -Offline
```

```sh
python3.13 -B scripts/check-m1.py --profile synthetic
python3.13 -B scripts/check-m1.py --profile ulog
```

The Windows commands used the existing project environment/cache. Linux used a
source-only copy on the native WSL home filesystem, a fresh project environment,
the previously retained CPython 3.13.1 interpreter and locally installed uv
0.11.19. The locked profile setup downloaded Linux tool/reader wheels; there was
no interpreter download. The source copy included the unchanged contract used
by the existing golden-vector tests. Both profiles ran sequentially in each
checkout; this checks the extra being added, while the Windows synthetic lane
also verified removal of previously installed optional packages. The later
source-bound offline repeat verifies that removal on Linux as well. This is local
setup evidence, not a hosted Ubuntu or fresh-OS result.

| Check | Windows | Linux / WSL |
| --- | --- | --- |
| Synthetic profile | 310 passed, 32 expected optional-reader skips | 310 passed, 32 expected optional-reader skips |
| ULog profile | 342 passed | 342 passed |
| Lock consistency / frozen sync | Passed in both profiles | Passed in both profiles |
| Dependency isolation / pinned ULog versions | Passed | Passed |
| Ruff / format / strict mypy, including runner | Passed in both profiles | Passed in both profiles |
| Standard-library conversion / verification / reader | Passed in both profiles | Passed in both profiles |

A separate local standard-library harness injected exit 17 at each of the ten
post-version subprocess stages. Each stopped the runner immediately and
propagated that exit without running later commands. Three invalid uv version
strings and a missing executable failed before setup. Three unsupported
Python/platform combinations returned usage exit 2 before external execution.
These 17 focused harness cases use mocked subprocesses/runtime metadata; they
are control-flow evidence, not additional product tests or real tool executions.
The first harness attempt used an incorrect stage count; it was corrected to
the runner's ten subprocess stages without changing product code.

Detailed commands, complete output and exits, source hashes, baseline bytes,
scope checks and prior-evidence checks are retained in ignored
`.local-discovery/linux-checks-001/`. `windows-*.json` and `linux-*.json` own the
initial profile results; the four `bound-windows-*.json` / `bound-linux-*.json`
reports add pre/post source hashes for the repeated offline lanes.
`source-and-yaml.json` binds 23 exercised source/configuration inputs and records
parsed CI matrix checks using the already installed PyYAML 6.0.3 BaseLoader.
This checks YAML structure, not hosted action execution.
`failure-probes.json` and `runtime-guards.json` own the
injected checks. The Linux parent entry point is:

```powershell
wsl -d Ubuntu -- bash -lc 'python3 -B <repo>/.local-discovery/linux-checks-001/run-linux.py'
```

The dependency preparation required explicit maintainer approval after the
initial automatic approval rejection. That failed launch installed nothing;
the approved retry installed only pinned uv in the ignored local tools tree.
The runner then synchronized the existing locked project profiles in its owned
Linux source copy. No external framework source or earlier evidence was edited.

| Current created or modified file | Purpose |
| --- | --- |
| [scripts/check-m1.py](../../scripts/check-m1.py) — new | Shared locked setup, profile isolation, quality checks, fresh scratch and CLI smoke |
| [scripts/check-m1.ps1](../../scripts/check-m1.ps1) | Compatibility wrapper forwarding existing parameters |
| [.github/workflows/m1.yml](../../.github/workflows/m1.yml) | Four Windows/Linux profile combinations, shared command, unchanged action/tool pins |
| [README](../../README.md), [roadmap](../roadmap.md), [testing strategy](../testing-strategy.md), [converter guide](bounded-conversion.md), Linux publication report, this guide | Current setup boundary, evidence, historical-result separation and navigation |

No data migration is required. Rollback restores the saved PowerShell runner,
Windows-only workflow and affected documentation, and removes the Python runner;
completed verification artifacts can be retained independently. The existing
application modules, tests, fixtures, contract, lockfile and runtime configuration
are unchanged. Git metadata remains absent; no commit or publication occurred.
Independent read-only review initially blocked on missing source-hash records
in its supplied package. The corrected evidence package includes a repeated
offline run of all four profiles with source hashes captured before/after each
command; the original review remains retained. A parent closeout initially
refused a reviewer-created symlink in scratch. Inputs were checked separately,
and the workspace was preserved with link metadata before cleanup; no source
permission was relaxed. This increment uses a separate restricted Reviewer,
not a blind Tester/Implementer acceptance cycle.

Hosted execution and reviewed real-source producer/rights evidence remain open.
The smallest next implementation task is the remaining M2 instrumentation and
operational receipt inventory; it must retain the bounded synthetic transport
scope until the separate real-source and hosted-release gates are satisfied.


The evidence-only repair passed the second independent read-only review with
`accepted: true` and no blockers. The Reviewer checked all 23 bound hashes and
the identical pre/post inventories in all four passing logs. Actual candidate
and test write-open probes returned `EROFS` (errno 30). Reviewer results and
process outcomes are `review-v2.json` and `review-v2-execution.json`; the first
review remains unchanged. Both Reviewer workspaces and the Linux check workspace
were preserved, archive-verified and removed through the external workflow's
ownership-checked helpers. The Linux archive retains its virtual environment,
smoke runs and scratch link metadata without following links. This paragraph
records the post-review verdict/cleanup only; reviewed runtime, CI and test
behavior remain unchanged. Final scope is eight modified files and one new
runner, with 578 local documentation links valid and 110 earlier JSON evidence
files byte-identical. `completion.json` and `scope-check.json` record closeout.
Two dash characters in this guide were restored after the parent closeout
exposed a Windows default-encoding read failure; source/configuration bytes
were unaffected.
