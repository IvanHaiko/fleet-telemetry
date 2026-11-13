# Bounded M3 window reference

## Scope and observable result

This first M3 slice implements a pure, standard-library reference calculation
for a tiny synthetic arrival/watermark trace. It is an oracle for a future Flink
experiment, not a running stream processor. It adds no service or dependency.
[ADR-0018](../adr/0018-flink-processing-candidate.md) records the maintainer's PyFlink
direction and the separate environment/runtime gates. M2's local synthetic
acceptance remains unchanged; M3 is not accepted.

Acceptance for this slice is exact authored outcomes for epoch-aligned windows,
nullable measurement counts/sums, duplicate/late/conflict precedence, expiry,
external time bounds and explicit finite completion, under Python 3.13. Actual
watermark generation, idleness and checkpoint recovery require Flink tests.

## Public reference interface

`telemetry_reference.py` exports frozen dataclasses:

- `ReferenceScope(dataset_run_id: str, pipeline_version: str, source_log_id: str,
  timestamp_min: str, timestamp_max: str)`: one trusted synthetic source and run;
  inclusive external source-time bounds in six-digit UTC `Z` format.
- `Observation(wire: bytes)`: one canonical envelope; observation position is
  its zero-based position among observations, excluding trace control steps.
- `Watermark(timestamp_ms: int)`: explicit downstream global watermark in Unix
  milliseconds. These steps are observations/control inputs, not inferred clocks.
- `EndOfInput()`: required final step; finite source completion, never silence.
- `MeasureSummary(count: int, total: Fraction | None)`: exact sum of recognized
  decimal values; null total precisely when count is zero.
- `BatteryWindow(dataset_run_id: str, pipeline_version: str, vehicle_id: str,
  start_ms: int, end_ms: int, unique_events: int, voltage: MeasureSummary,
  current: MeasureSummary, remaining: MeasureSummary)`.
- `Disposition(observation_index: int, kind: str, reason: str,
  event_id: str | None)`: fixed kinds `eligible`, `duplicate`, `late`, `invalid`,
  `conflict`; invalid input never includes raw payloads or diagnostic values.
- `ReferenceResult(windows: tuple[BatteryWindow, ...],
  dispositions: tuple[Disposition, ...], conflict_free: bool,
  peak_active_identities: int, reconciled_identities: int)`.

`calculate_windows(scope: ReferenceScope, trace: Sequence[Observation | Watermark
| EndOfInput]) -> ReferenceResult` performs no I/O and mutates no input.
`epoch_milliseconds(timestamp: str) -> int` exposes the exact timestamp boundary.
`ReferenceError` has a fixed `reason` string and no supplied input values.

The interface is an internal reference, not a new canonical wire/sink contract.
The fixed policy identifier is `battery-window-reference-v1`. Window size is
10,000 ms and active identity horizon is 600,000 ms. Export `POLICY_VERSION`,
`WINDOW_MS`, `DEDUP_MS`, `MAX_TRACE_STEPS = 1024`, and
`MAX_TRACE_BYTES = 1048576`. These bounds apply before envelope processing.

## Exact time and disposition rules

1. Validate the scope identifiers, source hash and inclusive time bounds first.
   Identifiers use printable nonempty ASCII. Hash format is `sha256:` plus 64
   lowercase hex digits. Bounds use years 0001-9999; start must not exceed end.
2. A trace must contain at most 1024 steps and at most 1 MiB of observation bytes.
   Reject unknown/malformed step types, non-bytes observations, bool/non-integer
   watermarks, decreasing watermarks, a missing EOF or any step after EOF using
   `ReferenceError`. Empty finite input `[EndOfInput()]` is valid. Equal watermarks
   are valid. Watermarks are restricted to signed 64-bit values, reserving the
   maximum value for terminal EOF. No partial result escapes an invalid trace.
3. Validate each observation using the existing `read_battery_event`. Then
   require synthetic `battery-v1`, the scope's source hash and dataset run,
   and source time inside its external inclusive bounds. Invalid observations
   get kind `invalid`/reason `envelope_invalid` or `scope_mismatch` and do not
   enter identity state or a window. This is admission to a trusted test scope,
   not authentication of the source or proof of fixture provenance.
4. Convert canonical UTC to signed integer epoch microseconds using datetime
   subtraction, then floor-divide by 1000. Never use float `timestamp()` or round
   to the nearest millisecond. Keep original microseconds in the semantic
   comparison. Pre-epoch dates therefore floor toward negative infinity.
5. Compare each valid identity against the entire bounded trace's recognized
   semantic content before active dedup/late routing. Use the M1 projection:
   omit ingestion time, provenance and delivery; include vehicle/type/time,
   source identifiers/ordinal, normalization, source-time interpretation, payload
   and sorted quality flags. Missing optional fields are reader-normalized null.
   Equal ID/different semantics gives `conflict`/`identity_conflict`, does not
   replace prior content, sets `conflict_free=False` and suppresses all returned
   windows. Continue dispositions for diagnostic accounting. This full-trace
   reconciliation ledger is distinct from the expiring streaming state.
6. Active identity expires when global watermark is at least event time in ms
   plus 600,000. Duplicates do not refresh expiry. A copy still active gives
   `duplicate`/`identity_repeat`, even if its window is closed. Expiry runs at
   each explicit watermark; inactive equal copies proceed to window eligibility.
7. Windows are UTC epoch aligned: `start = (event_ms // 10000) * 10000`, end is
   exclusive. A zero-lateness window is closed when the observed watermark is
   at least `end - 1`, matching the millisecond window maximum timestamp. Closed
   window input gives `late`/`window_closed`; otherwise `eligible`/`window_open`.
   With no watermark yet, all valid windows are open. A valid identity enters
   active state only while its expiry is greater than the observed watermark;
   a late first observation may therefore be deduplicated until that expiry.
8. EOF explicitly flushes every eligible terminal window. Group by dataset run,
   pipeline version, vehicle and interval; return windows sorted by vehicle and
   start. Emit only nonempty windows. Equal timestamps with distinct identities
   are separate measurements. Exact duplicates never inflate counts or sums.
9. Summaries use `Fraction(str(value))` for each recognized numeric value, sum
   exactly and count non-null values separately. A missing optional value is not
   zero. A mean, when needed, is total/count without invented rounding. This
   reference numeric representation is not a published Flink sink schema.

The future generator's two-second out-of-order bound is separate from an
explicit watermark trace. The pinned
[Flink generator source](https://github.com/apache/flink/blob/release-2.2.1/flink-core/src/main/java/org/apache/flink/api/common/eventtime/BoundedOutOfOrdernessWatermarks.java)
emits `maxTimestamp - bound - 1` periodically. The reference does not simulate
periodic scheduling or the proposed 30-second idle timeout. Capture actual
downstream watermark decisions to compare online eligibility; identical events
alone do not define identical online results.

## Verification, limits and rollback

Independent tests are authored against this public interface before candidate
implementation and frozen locally. They must use literal boundary expectations,
not call candidate helpers to calculate expected results. Existing synthetic
normalization/envelope fixtures may construct valid input; no real log is needed.
Keep cases purposeful and test the table's observable semantics rather than
implementation details. The external workflow owns restricted worker evidence.

The reference's full-history ledger and eligible records are bounded by both
trace limits, not by event-time expiry. `peak_active_identities` measures only
the proposed streaming dedup state, not process bytes or total reference memory.
A stalled watermark can retain all active trace identities. No checkpoint,
source recovery, multi-partition idleness, Kafka ACK, performance or Flink
compatibility claim follows from a reference test pass.

Rollback removes the reference, focused tests and matching check/navigation
entries. Retain frozen inputs, failed results and review archives locally.
No persistent state, schema, source identity or M2 runtime migration is involved.

## Executed reference checks

The independent Tester authored 12 focused functions, expanded by boundary
parameters to 23 cases, before `telemetry_reference.py` existed. Its source
write-open probe failed. The original test and public contract bytes are frozen
in local `frozen-v1/`; they were not changed to fit the implementation. The first
candidate passed all 23 cases. A typed/formatted project copy retains identical
assertion ASTs after removing type-only casts; `project-test-adaptation.json`
records that comparison. The full project suite uses the typed copy; independent
acceptance uses the original frozen tests.

| Check | Windows | Restricted Linux / WSL |
| --- | --- | --- |
| Frozen independent reference | 23 passed | 23 passed |
| Full synthetic profile | 372 passed, 32 expected optional-reader skips | 372 passed, 32 expected optional-reader skips |
| Full optional ULog profile | 404 passed | 404 passed |
| Ruff / format / strict mypy | Passed through shared runner | Passed against read-only source |
| File converter, external verification, canonical reader smoke | Passed in both shared profiles | Existing pure/CLI regression cases passed; fresh shared-runner environment setup not rerun |

Exact entry points and child commands/results are retained under ignored
`.local-discovery/m3-reference-001/`:

```powershell
.venv/Scripts/python.exe .local-discovery/m3-reference-001/check-windows.py
.venv/Scripts/python.exe .local-discovery/m3-reference-001/check-windows-repair.py
wsl -d Ubuntu -- bash -lc 'python3 -B <repo>/.local-discovery/m3-reference-001/check-linux.py'
```

The first Windows ULog profile synchronization failed while writing uv's PE
trampoline in the sandbox's default temporary directory. That actual exit 2 is
preserved in `windows-ulog.json`. A targeted rerun used owned `TEMP`/`TMP` under
this cycle, without a source/dependency change or network, and passed all ULog
checks. Earlier successful synthetic/frozen checks were retained. The repair
records source hashes before/after; the earlier successful Windows commands
have separate captures rather than a retroactively claimed full-run hash check.

Linux used a read-only 97-file source export plus the frozen inputs, existing
Python 3.13.1/tool sites and owned scratch. Every exercised input hash matched
before/after, and profile isolation was checked. The workspace was archived and
removed with ownership-checked helpers. No Python 3.12, PyFlink, JVM, connector
JAR, service, image or new package version was installed. Windows profiles reused
cached locked packages; root `uv.lock` and all existing runtime settings remain
unchanged. Subsequent documentation records the maintainer's API preference and
these outcomes; it is not represented as exercised runtime code.

Git index bytes and the original 93 staged entries are preserved. This slice's
six modified files and four new files remain unstaged; there is no commit or
publication. The original public contract/test version, Tester results, failed
Windows synchronization and later review results remain separate artifacts.

## File inventory and next boundary

| File | Change |
| --- | --- |
| `telemetry_reference.py` | New pure bounded calculation and typed reference results |
| `tests/test_reference.py` | New typed copy of independently authored meaningful cases |
| `scripts/check-m1.py` | Include the new pure module in the shared checks |
| `pyproject.toml` | Include the pure module in strict type checking; dependency pins unchanged |
| `docs/adr/0018-flink-processing-candidate.md` | New maintainer-selected PyFlink direction, alternatives/cost and runtime gates |
| `docs/reference/m3-window-reference.md` | New reference contract, exact checks and limitations |
| `README.md` | Link the first M3 slice and distinguish it from a Flink runtime |
| `docs/roadmap.md` | Record the first slice and pending compatibility/recovery criteria |
| `docs/architecture.md` | Link the reference and API/environment decision |
| `docs/testing-strategy.md` | Separate calculation invariants from actual Flink tests |

At this slice's closeout, the next task was to pin the isolated Linux
Python 3.12/JDK 17/PyFlink 2.2.1 environment and its complete dependency/JAR
hashes, then demonstrate a tiny bounded worker/connector run. The subsequent
compatibility profile now passes those checks,
without Java application code or downgrading M1. It does not import this
reference as a production window implementation. The next stateful operator
must still compare its independently calculated results with this reference.

## Independent review and closeout

The separate restricted read-only Reviewer accepted this reference slice with
no blockers. It independently reran both the frozen and project reference suites
(23 passed each), confirmed all 40 assertion ASTs match after removing type-only
casts, and checked input preservation/output immutability. Source/test write-open
probes failed with `EROFS`; review input bytes remained unchanged. Its verdict
and execution are retained in `review.json` and `review-execution.json`.

Tester, Linux-check and Reviewer workspaces were archived before ownership-checked
cleanup. `scope-check.json` verifies the exact ten-file scope, prior artifact
and external-framework hashes, unchanged raw Git index and staged contents,
unchanged executable/configuration bytes since regressions and unchanged frozen
v1 inputs. `completion.json` records acceptance of the reference slice only;
`reference-evidence.zip` preserves the selected results and final project files.
No runtime adoption or full M3 acceptance follows from this closeout.
