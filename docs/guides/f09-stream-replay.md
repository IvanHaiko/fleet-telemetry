# Bounded F09 stream preparation and reference facts

## Implemented boundary, 2026-11-11

[ADR-0049](../adr/0049-bounded-f09-stream-events.md) scopes an offline step toward
the [integrated MVP](../roadmap.md#integrated-mvp-priority-2026-11-10). The preparer
exposes GPS, battery, land-detector and commander observations separately. The
reference processor consumes their ordered stream and emits GPS-centred facts.
Neither command starts Kafka, Flink, S3, SQL or dashboards; this does not complete
the source-to-query path.

Use the existing Python 3.13 environment with its pinned optional ULog
dependencies. Preparation verifies the registered original's bytes and protected
prepared artifact hashes/counts. It does not independently parse the original
again or authenticate an unsigned manifest from an untrusted party. Protect
those inputs and retain their original preparation evidence.

## Event and context semantics

`f09-recording-event-v1` carries the registered checksum, delivery run, original
stream/ordinal, native timestamp, existing measurement ID and unchanged payload.
Equal-time precedence is battery, land detector, commander, then GPS. Battery
keeps its original nested delivery metadata and synthetic UTC anchor; the outer
run is a separate delivery scope. GPS/state receive no invented physical UTC
or current-device freshness. Selection does not rebase measurement identities.

The interval is native boot microseconds `[start_us,end_us)`. Context retains at
most three immediately preceding battery/state observations and reviewed quality
masks; predecessors are not selected measurements. Battery ordinal-hole masks
have open boundaries; state recording masks have inclusive start/exclusive end.
They express research uncertainty, not measured physical dropout durations.

Associations use preceding observations with inclusive `max_age_us` (default one
second). Rejection gaps and recording gaps remain different statuses. Unmatched
values, references and ages are NULL; state codes are not interpreted as phases.
Exact repeated delivery does not multiply facts or renew state. Conflicting
content and unsupported order refuse. This file reference does not define Flink
watermarks, out-of-order admission or broker recovery.

## Commands and artifacts

Example fresh destinations below have not been run in the main checkout:

```powershell
.venv/Scripts/python.exe -m runtime.flight_analytics.stream_prepare --prepared .local-discovery/gold-grafana-20261104/connected-recording-v1 --source .local-discovery/real-ulog-20261027-001/log_67_2025-8-21-14-24-48.ulg --output .local-discovery/f09-stream-20261110-example --run-id f09-stream-example --start-us 86459069 --end-us 146459069
.venv/Scripts/python.exe -m runtime.flight_analytics.stream_reference --bundle .local-discovery/f09-stream-20261110-example --output .local-discovery/f09-reference-20261110-example --max-age-us 1000000
```

Preparation writes `events.jsonl`, `context.json` and a final `manifest.json`.
The manifest binds source artifact references, exact output lengths/hashes,
scope and counts. The reader verifies permitted files, event/context scope,
ordering, identities and counts even if modified bytes were rehashed. Input
references do not authorize arbitrary external reads. Reference output is
`facts.jsonl` plus its final manifest and input bundle manifest hash.

Events are at most 65,536 bytes, bundles/reference output have 64-MiB bounds,
and at most 50,000 selected events are admitted. The processor bounds signature
state and counts duplicates against its delivery limit; context is also bounded.
Caller options cannot expand hard caps. The exact 122,463,132-byte original has
its own source boundary, not a global reader-limit increase. Age policy is an
integer in `0..60,000,000` microseconds.

Existing destinations refuse before reading inputs. Failures retain incomplete
evidence without a successful completion manifest. No automatic repair/deletion
follows. Generated coordinates stay in restricted ignored storage; CLI output
contains safe status/counts. Completion is a bounded file result, not a generic
crash-durability guarantee or independent S3 archive receipt.

## Verification and remaining integration

Pinned Linux Python 3.13.1, pytest 9.1.1, Ruff 0.16.5, mypy 1.15.0, pyulog 1.2.2
and NumPy 2.3.5 checks pass: 93 selected new/regression cases, Ruff, formatting
and strict mypy across eight new source/test files. Source inputs are read-only
during checks; only owned scratch is writable. Tests were authored with the
implementation; no blind-test independence is claimed. Review identified a
reference completion-manifest failure window. Publication now uses the existing
atomic no-replace helper after closing a pending file; two regression cases
verify that write/close failures retain partial evidence without completion.
Further review found that direct processing did not reconcile battery masks
with available accepted ordinals. Bundle admission and direct processing now use
the same consistency validator. A direct regression checks valid internal holes,
missing masks and masks contradicting accepted points before any facts return.

The protected real F09 interval `[86459069,146459069)` yields:

| Stream | Selected events |
| --- | ---: |
| GPS | 538 |
| Battery | 299 |
| Land detector | 62 |
| Commander | 118 |
| Total | 1,017 |

Two state predecessors provide context. Two preparations have identical
event/context/manifest bytes. All 538 complete inspections match the retained
historical result, including one before-first battery result, five land recording
gaps and two stale land associations. The actual reference CLI agrees with the
processor's complete facts. This compares two association implementations over
reviewed preparation, not independently measured physical ground truth.

Restricted process results, preserved candidates/failures and real-data outputs
remain under `.local-discovery/mvp-batch-20261110-001/` and its recorded owned
Linux workspaces. No private measurements are redistributed as fixtures. No
service startup, credential/table change, commit or publication belongs here.

Next connect these streams/calculations to Kafka/Flink, independently archive
exact admitted input and gate serving/SQL progress on verified coverage. Actual
observation coordinates, freshness and selected recovery failures must be tested
there. The offline input-event hash/comparison does not provide those guarantees.
Rollback stops using the new commands and retains inputs/outputs; no persistent
dataset migration is involved.
