# Two supported recordings through a shared local view

## Result and boundary

The second-source increment in the [active roadmap](../roadmap.md#active-product-goal-2026-11-04)
adds registered F01 alongside F09, through `runtime.flight_analytics.recording`
and one recording-selectable Grafana dashboard. [ADR-0044](../adr/0044-two-recording-research-view.md)
keeps it an exact-file historical research scope. There is no general unknown-
firmware admission, verified physical vehicle identity, live drone connection,
validated UTC mapping or integrated real-source Kafka/Flink/archive replay.
Existing F09 adapters, artifacts, tables and dashboards remain intact.

F01 is deliberately different: its supported GPS subscription has zero records
(`empty_stream`), and its battery stream is absent (`missing_stream`). It has
41 land-detector and 77 commander observations. Missing values remain NULL.
The inspection follows original commander records, not fabricated GPS events.

## Source, meaning and privacy review

The unchanged F01 file is 1,594,052 bytes, registered SHA-256
`36e54ff7c13619f96c9fb56a74c9fb3efb0650600881412a9363f00a65d7141b`.
Its acquisition receipt pins community dataset commit
`0a0051aee0e899e461d4bc149cc529da628986ab`. The curator's
[CC BY 4.0 declaration](https://github.com/Zxbxdxd/px4-flight-log-dataset/blob/0a0051aee0e899e461d4bc149cc529da628986ab/LICENSE_DATA.md)
requires attribution to the original PX4 public-log portal/PX4 project and the
curated PX4 Flight Log Dataset. Those declarations do not independently verify
uploader rights or physical origin. The heuristic source label is not a flight
outcome. Source, acquisition metadata, derived records and all coordinates stay
in restricted ignored local storage; no measurement fixture is redistributed.

The exact reported firmware is `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`.
Reviewed upstream definitions are
[VehicleLandDetected](https://raw.githubusercontent.com/PX4/PX4-Autopilot/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLandDetected.msg)
and [VehicleStatus](https://raw.githubusercontent.com/PX4/PX4-Autopilot/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg).
The selected wire layouts match the already pinned F09 state definitions:
land definition SHA-256 `27a0f6bb53a636b60bd86e021e3db416a7cc6505701a6285f2bc793fc76cb687`,
commander definition SHA-256 `1831131423c63fe4eb3fc837cc6f4cf5aed73a01f475c6e4034aaec6044d26dd`.
These are embedded definition hashes, not upstream text-file hashes.

State time is unsigned microseconds since system start. Landed/ground-contact/
maybe-landed remain recorded detector flags; arming codes 1/2 mean recorded
disarmed/armed; navigation mode retains its uint8 code including reserved values;
failsafe remains a recorded commander flag. Do not infer phase, duration, safety
or current connectivity. The boot-clock relationship remains an assumption.

The adapter checks original checksum, complete framing, firmware, definitions,
stream counts, parser dtypes and strictly increasing per-stream native time.
It independently decodes every selected original timestamp/state field and
compares it with the upstream parser. F01 has no dropout frames; that does not
prove acquisition completeness. The additional Q/binary-M/default-parameter
support is enabled only for this checksum under the ordinary 16 MiB/100,000-frame
limits. F09's larger limits and unknown-input refusals remain unchanged.

## Commands

Prepare F01 without services, with the existing pinned `.venv`:

```powershell
.venv/Scripts/python.exe -m runtime.flight_analytics.recording --source .local-discovery/fleet-source-inventory-20261103/samples/0700a168-0eb6-4029-a6f0-bf0603f70363.ulg --output .local-discovery/gold-grafana-20261104/f01-connected-v1 --max-age-us 1000000
```

The shown output already exists: choose a fresh name for a new preparation.
F09 keeps its existing `--job ... --output ... --max-age-us ...` command.
Both accept `--serve` to admit the result into shared local ClickHouse tables.
Set `FLIGHT_CH_ADMIN_PASSWORD` and `FLIGHT_CH_READER_PASSWORD` in the process
environment from the existing protected `runtime.env`; do not print them.
An already prepared recording can be verified/admitted with the same entry point:

```powershell
.venv/Scripts/python.exe -m runtime.flight_analytics.recording --prepared .local-discovery/gold-grafana-20261104/f01-connected-v1 --serve
.venv/Scripts/python.exe -m runtime.flight_analytics.recording --prepared .local-discovery/gold-grafana-20261104/connected-recording-v1 --serve
```

Prepared mode validates bounded artifacts and digests, not original-source
authentication; protect its inputs and retain original preparation evidence.
Do not supply a new age threshold in this mode. Changed association policy
requires a fresh preparation. Without `--serve`, no SQL writes occur.

## Shared storage and interface

`f01-recording-inspection-v1` carries explicit commander observation identity,
stream, ordinal and native time, NULL GPS, missing battery and separate qualified
state associations. Its state identities are SHA-256 of
`f01-state-research-v1:<source_id>:<stream>:0:<original ordinal>`.
They do not depend on output directory, arrival or replay identity. State uses
the existing past-only/inclusive-age rule without a dropout mask for this file.
Both state streams match all 77 commander inspection points at the chosen
one-second exploratory threshold. The 41 land records remain separate retained
evidence, not 77 distinct land measurements.

The shared `recording-view-v1` projection normalizes the two inspection shapes
into `recording_views_v1.observations` and `recording_views_v1.recordings`.
Recording identity binds source checksum, inspection profile and age policy.
Observation identity/native time remains that of its actual timeline stream.
The registry retains source, recording pseudonym, capability statuses, bounds,
count and input/projection digests. Data retains nullable fields, units, separate
stream statuses/ages/references and complete projection JSON. Numeric projection
columns are Float64, with full typed/raw readback; this is not a replacement
canonical contract, exact-decimal aggregate or cross-source UTC alignment.

Admission validates the artifact scope, count, digest, ordinal/identity/time
ordering and unknown-value masks before SQL. A fresh schema is created only if
absent; incompatible schemas refuse. Every row is read back before registry
admission. Reader grants are SELECT only, and separate reader readback must
match. An identical replay verifies existing rows without inserts/DDL/grants.
A conflicting registry or partial unregistered scope refuses without repair or
deletion. Admissions must be serialized by the local operator; no concurrent
writer isolation, atomic SQL snapshot or transactional publication is claimed.
Failure after registry insertion or a grant may leave a locally visible scope.

The shared [supported-recordings dashboard](http://127.0.0.1:13002/d/recording-inspection)
uses one query set and a query-driven recording selector. A native-time textbox
uses zero for the last recorded observation; an earlier limit selects only a
preceding observation. It is unrelated to Grafana's UTC time picker, which is
hidden. Invalid limits/before-first intervals produce no snapshot. The view
shows available streams, 14 fields with separate availability/association/age,
an offline map when coordinates exist and the last 100 selected observations.
F01's map has no position; its capability table explains why. No external tiles
are requested. Query budgets are ten seconds, one thread, 256 MiB memory,
50,000 scanned rows and 64 MB scanned bytes. This is a bounded local viewer,
not a fleet-capacity benchmark.

## Verification

Two complete F01 original-file preparations produce identical state, inspection
and report bytes. The 118 original state records reconcile; 77 inspection rows
preserve missing GPS/battery. F01/F09 observation identities are disjoint.
The shared loader admitted 21,054 F09 and 77 F01 observations with complete typed
and projection-JSON readback through admin and SELECT-only reader. The shared
schema and queries are checked separately from the earlier F09 table evidence.

Focused commands:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_recording_store.py tests/test_recording_inspection.py tests/test_ulog_integrity.py tests/test_f09_state_time.py tests/test_f09_state.py tests/test_f09_battery_time.py tests/test_f09_coverage.py tests/test_f09_flight_analytics.py -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check runtime/flight_analytics/f01.py runtime/flight_analytics/recording_store.py runtime/flight_analytics/recording.py ulog_integrity.py tests/test_recording_store.py tests/test_ulog_integrity.py
.venv/Scripts/python.exe -m ruff format --check runtime/flight_analytics/f01.py runtime/flight_analytics/recording_store.py runtime/flight_analytics/recording.py ulog_integrity.py tests/test_recording_store.py tests/test_ulog_integrity.py
$env:MYPYPATH='tests'
.venv/Scripts/python.exe -m mypy --strict --explicit-package-bases runtime/flight_analytics/f01.py runtime/flight_analytics/recording_store.py runtime/flight_analytics/recording.py ulog_integrity.py tests/test_recording_store.py tests/test_ulog_integrity.py
git diff --check
```

113 focused tests, Ruff and strict mypy pass. An initial mypy invocation lacked
the existing tests fixture import path; the explicit `MYPYPATH` above passes.
Six actual SQL query shapes also pass SELECT-only constant-fixture checks for
available and unavailable GPS before table admission. Those fixtures establish
query compatibility, not real-source reconciliation.

Two existing-recording admissions through the shared loader added zero physical
rows: the total remained 21,131. A changed F01 inspection/digest refused against
the existing registry; a zero-row INSERT as `flight_reader` was denied. Thirty
actual datasource/query checks passed across both recordings at last-record,
first-record and before-first limits. Snapshots matched the prepared projection
field by field; the F01 map returned no coordinates. The public CLI itself also
passed F01 original preparation plus `--serve`, and F09 `--prepared --serve`,
both returning `verified_existing` without adding rows.

An in-app browser switched F01 to F09 through the query-driven selector,
displayed distinct 77/21,054 row counts and source capabilities, rendered F09's
offline marker/map and observation history, and showed no snapshot before the
first native timestamp. Resetting the limit restored the last recorded values.
The initial variable SQL returned label/value columns in the wrong order for
this plugin, yielding empty panels; placing recording ID first corrected that
observed failure. Explicit metadata column widths corrected clipped statuses.
This is one local browser observation, not a multi-browser/load or live test.

Private runtime, replay and browser results stay in the ignored research scope.
The initial database/grant operation was rejected by automatic approval review;
the maintainer then explicitly approved the two-table local load and SELECT
grant. No operation bypassed that refusal. No dependency or new service was added.

## Rollback and changed files

Stop using the shared dashboard/loader/profile, retaining both new tables and
prepared outputs for inspection. Existing F09 views remain available. Remove
the new dashboard from provisioning and reload only that existing Grafana if
rolling back the UI. No source, database, volume or offset is deleted. Existing
canonical events/checkpoints require no migration. Revoking the new reader
grants is a separate explicit local access change, not automatic cleanup.

Created: `runtime/flight_analytics/f01.py`,
`runtime/flight_analytics/recording_store.py`,
`runtime/flight_analytics/dashboards/recordings.json`,
`tests/test_recording_store.py`, this guide and ADR-0044.
Updated: `runtime/flight_analytics/recording.py`, `ulog_integrity.py`,
`tests/test_ulog_integrity.py`, README, roadmap, architecture, data contracts,
testing strategy, deployment guide, `docs/guides/recording-connection.md` and the source inventory.
No commit, push, cloud work or destructive cleanup is performed.
