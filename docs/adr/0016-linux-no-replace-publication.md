# ADR-0016: Publish bounded runs on Linux without replacing destinations

**Status:** Selected for the authorized M1 portability follow-up.

**Date:** 2026-10-20

**Supersedes:** Only the Windows-only publication restriction in
[ADR-0009](0009-bounded-local-conversion.md). Its validation, mapping, artifact,
dependency and source-adoption boundaries remain unchanged.

## Problem and decision

The independent M2 acceptance cycle could exercise pure interfaces under Linux,
but the full M1 suite failed at the explicit Windows-only publication guard.
Ordinary POSIX rename can replace an existing empty directory. An existence
check followed by rename therefore cannot preserve the no-overwrite contract
when another process creates a destination between those operations.

Keep adjacent staging, complete source validation, artifact reconciliation and
file flush/fsync before publication. On Linux use the libc `renameat2` entry
point with `RENAME_NOREPLACE`, through the Python standard-library foreign
function interface. Declare its argument and return types explicitly. The
[Linux manual](https://man7.org/linux/man-pages/man2/rename.2.html) documents
the atomic no-replace operation and the required filesystem support.

Keep Windows directory rename behavior. Refuse other platforms. A missing libc
entry point, unavailable kernel operation or unsupported filesystem must fail
explicitly without a replacing rename or copy fallback. Existing destinations
and late collisions must remain intact; ordinary failures clean only staging
created by that invocation. Use trusted local parent directories.

## Alternatives and impact

- Removing the platform guard while retaining plain rename leaves the empty
  destination race unresolved.
- Locks coordinate only cooperating writers and do not protect another process's
  destination. Creating the destination first exposes an incomplete final run.
- Copying files into the final directory loses whole-directory publication.
- A third-party portability library adds packaging and maintenance obligations
  for one system operation. Architecture-specific raw syscall numbers add an
  unnecessary ABI assumption. Neither is needed for this bounded Linux target.

There are no new packages, services or cloud costs. Maintenance adds a small
typed platform boundary and focused failure/race tests. The operation requires
Linux libc/kernel/filesystem support; it does not promise arbitrary Unix or
network filesystems. Validation records the actual filesystem exercised.

## Evidence, limitations and rollback

The portability report owns commands and results:
independent frozen tests, a late empty-directory collision, independent competing
processes, unsupported-operation failures, both M1 dependency profiles, and
Windows regressions. Historical Linux failures remain failed historical evidence.
Local results do not establish hosted CI execution, real-source adoption,
power-loss durability or a concurrent service API.

Existing job/run, pipeline, schema, identity and mapping versions remain unchanged.
No persistent data migration is required. Rollback restores the Windows-only
publication guard and its tests; preserve completed Linux runs and verify them
with their recorded runtime. Do not delete or rewrite existing runs.
