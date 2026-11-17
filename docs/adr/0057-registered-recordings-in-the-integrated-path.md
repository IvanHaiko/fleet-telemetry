# ADR-0057: Registered recordings in the integrated replay path

**Status:** Proposed, 2026-11-17.

## Problem

The integrated recording profile (source, Kafka, Flink, independent archive,
ClickHouse, Grafana; [ADR-0052](0052-single-machine-recording-profile.md))
admitted one file only. About twenty modules compared inputs with the F09
checksum and wrote its vehicle pseudonym, battery normalization version and
identity profile names as constants. Step 2 of the
[active product goal](../roadmap-history.md#active-product-goal-2026-11-04) asks for a
second real log through the same entry point and the same view, without
editing SQL or dashboards per recording, after a review of its firmware,
rights, field meanings and time mapping.

"Any log of the right format" is not an admissible scope. Equal ULog topic
names do not establish equal units, enumerations, sentinels or clocks; the
F03 review below found all three changing between firmware versions.

## Decision

Keep exact-file admission and replace the scattered F09 constants with one
registration table, `telemetry/recordings.py`. An entry is a reviewed
original: its checksum and size, reported firmware, the SHA-256 of each
selected embedded definition (`battery_status`, `vehicle_gps_position`,
`vehicle_land_detected`, `vehicle_status`), the record count of each selected
stream, the vehicle pseudonym, the GPS field layout and the reader's frame
limit. Every adapter and validator resolves the registration from the checksum
(or from the source ID an envelope carries) and refuses an unregistered file
before any parser runs.

Every recording-specific name derives from the registration key:
`<key>-gps-research-v1`, `<key>-state-research-v1`,
`<key>-recording-event-v1`, `<key>-recording-context-v1`,
`<key>-recording-fact-v1`, `ulog-battery-<key>-research-v1`. With key `f09`
these are exactly the names ADR-0041 and ADR-0049 fixed, so F09 measurement
identities, events, facts and bytes do not change. A replay of one recording
can never produce another's identities.

Shared wrapper and configuration formats keep their historical names:
`f09-recording-output-v1`, `f09-recording-runtime-state-v2`,
`f09-recording-job-v1`, `f09-recording-run-v1`. They carry the wrapped fact or
configuration unchanged; the recording's own profile and source ID are inside.
Renaming them would change F09 bytes and stored runs for no semantic gain.

`ops start --source <key>` replays any registered recording; `live` stays the
SITL profile. Stored runs with `"source": "f09"` remain valid. The local
locations of each recording's verified inspection and original are listed in
`runtime/recording/fault_run.py`; they are ignored local storage, not
fixtures. The SQL schema, the quality checks and the dashboard are shared. The
dashboard is rendered from one template; only the run database and the
recording label in titles vary.

## Admitted recordings

Both come from the community sample described in the
[source inventory](../reference/telemetry-source-inventory.md); the full
originals were retrieved from PX4 Flight Review on 2026-11-03 and compared
with the sample prefixes byte for byte. The curator declares CC BY 4.0 and the
portal a CC-BY PX4 terms statement. Neither verifies uploader rights or the
physical producer. Originals, derived records and coordinates stay in ignored
local storage; nothing is redistributed.

| | F07 | F03 |
| --- | --- | --- |
| Controller reported | PX4_FMU_V6C | PX4_FMU_V5 |
| Firmware | `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` | `46a12a09bf11c8cbafc5ad905996645b4fe1a9df` |
| Bytes / frames | 8,079,735 / 159,459 | 12,386,279 / 250,072 |
| GPS / battery / land / commander records | 182 / 932 / 199 / 379 | 259 / 649 / 139 / 258 |
| Dropout markers | 0 | 0 |
| Registered frame limit | 200,000 | 300,000 |

Both need more than the default 100,000-frame bound; each limit applies to its
checksum only. The 16 MiB byte bound and every other input's limits are
unchanged. Both use the service frames (default parameters, binary multi-info)
already admitted for F01 under ADR-0044.

### Field meanings

The upstream message definitions at each exact commit were reviewed
(`msg/versioned/BatteryStatus.msg`, `msg/SensorGps.msg`,
`msg/versioned/VehicleStatus.msg`, `msg/versioned/VehicleLandDetected.msg` for
F07; `msg/battery_status.msg`, `msg/vehicle_gps_position.msg`,
`msg/vehicle_status.msg`, `msg/vehicle_land_detected.msg` for F03).

- **Battery.** For both firmware versions `voltage_v` is volts with 0 invalid,
  `current_a` amperes with -1 invalid, `remaining` a 0–1 fraction with -1
  invalid, `source` 0 the power module. The existing ADR-0007 policy applies
  unchanged. Both files have every record connected, `source` 0 and no
  sentinel; all 932 and 649 records were admitted.
- **GPS, F07.** The selected fields have the F09 names and types and the same
  meaning. The definition differs only in unselected fields
  (`system_error`, `authentication_state`, no `serial_number` in the battery).
- **GPS, F03.** The older layout records `lat` and `lon` as int32 in 1e-7
  degrees and `alt` as int32 millimetres above MSL, and has no
  `timestamp_sample`. The adapter divides by 10,000,000 and 1,000 exactly and
  writes `native_sample_us` as null; only a `scaled_integer` registration may
  carry a null sample time. Fix types and the validity rule are unchanged.
- **State, F07.** The embedded definitions are byte-identical to F09's.
- **State, F03.** `arming_state` in this firmware has INIT 0, STANDBY 1,
  ARMED 2, STANDBY_ERROR 3, SHUTDOWN 4 and IN_AIR_RESTORE 5; newer firmware
  has DISARMED 1 and ARMED 2. The existing check still admits only 1 and 2,
  read as recorded disarmed and armed; any other code refuses the file. F03
  contains only 1 and 2.
- **Navigation state.** Codes are stored as recorded. Their meaning depends on
  firmware (code 8 is AUTO_LANDENGFAIL in F03's firmware and ALTITUDE_CRUISE
  in F07's; code 6 is POSITION_SLOW in F07's). No labels are attached, and
  comparing codes across recordings needs a firmware-aware mapping that this
  decision does not provide.

### Time

All selected streams use microseconds since system start. Battery keeps the
synthetic fixed UTC anchor (2000-01-01T00:00:00Z at native zero) and the
`synthetic_time_anchor` flag; GPS receiver UTC remains display time. One
common boot clock is assumed, as for F09.

## Alternatives

- **A copy of the F09 modules per recording.** Fast to start, but duplicates
  the adapters, stream, processing, serving and operations checks for every
  file and needs per-recording SQL and dashboards.
- **A generic adapter for any ULog file.** It would read files whose units,
  enumerations and sentinels nobody reviewed. F03 shows the risk: a reader
  assuming F09's layout would mis-scale coordinates by 10^7.
- **Registrations in a data file.** Possible later; it adds a format and its
  validation and loses the typed review in code. Three entries do not need it.

## Consequences

Adding a recording needs the review above, one registration entry, a battery
conversion job and its local paths. No other code, SQL or dashboard change is
needed. A file that differs from its registration in any byte, definition or
count is refused.

Rollback: remove an entry and its input paths. F09 and stored runs are
unaffected, because F09's names and bytes are unchanged.

## Evidence, 2026-11-17

Offline, with the code of this decision:

- F09 regenerated from the original (`recording --job`, `stream_prepare` over
  the complete flight, `stream_reference`) equals the stored inspection, GPS
  and state artifacts, the `f09-full-20261113-001` bundle (39,758 events,
  context, manifest) and its reference (21,054 facts) byte for byte.
- F07: inspection with 182 GPS rows, 932 of 932 battery records admitted,
  every association matched; bundle of 1,692 events; 182 reference facts.
- F03: 259 GPS rows, 649 of 649 battery records admitted, every association
  matched; bundle of 1,305 events; 259 reference facts.
- Ruff, format and strict mypy pass; pytest 729 passed, 7 skipped
  (environment-specific, unchanged).

Integrated runs on the single-machine profile, each the complete recording at
native time with `ops start`, `complete`, `verify`, `collect` and `stop`:

- `f07-full-20261117-01`: ready with all 13 readiness checks; every health
  signal `ok` and all 13 SQL quality checks at 0 violations at mid-run.
  1,694 deliveries (1,692 events and the 2 declared repeats) gave 182 facts.
  `verify` passed: the SQL fact hash set equals the reference, zero logical
  repeats, and a rebuild from archive objects alone into a separate database
  has the same hash set. Every association is `matched`; the 23 GPS rows
  without a fix keep a NULL position.
- `f03-full-20261117-01`: the same readiness, health and quality results,
  including 0 latitude/longitude range violations after the 1e-7 degree
  conversion. 1,307 deliveries gave 259 facts; `verify` passed with SQL, the
  reference and the archive-only rebuild equal.

Not checked: the dashboards of these two runs in a signed-in browser (the
manual datasource step of the runbook); fault injection and restoration on
F07 or F03; any recording other than F09, F07 and F03.
