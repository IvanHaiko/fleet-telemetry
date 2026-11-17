# ADR-0060: Recorded flights as virtual vehicles over MAVLink

**Status:** Proposed, 2026-11-17; first step implemented and run the same day
([evidence](#first-step-run-2026-11-17)). Extends the live source of
[ADR-0054](0054-live-sitl-recording-profile.md) from one PX4 SITL to several
MAVLink vehicles. The ULog replay of
[ADR-0057](0057-registered-recordings-in-the-integrated-path.md) and
[ADR-0058](0058-admission-by-mapping-profile.md) stays unchanged and remains
the only path with exact content reconciliation against a prepared reference.

## Problem

The maintainer wants a fleet monitor that can show recorded flights now and
connect a physical PX4 later through the same input. The intended
demonstration starts the profile once, replays three ULog files chosen at
random as three vehicles, adds a fourth while the others run, and pauses one
of them while the rest keep updating.

The current paths cannot do that:

- **File replay admits too little.** ADR-0058 admits a file only when its
  layout digests and firmware match a reviewed profile. Of the 3,989 distinct
  local ULog files, 5 replay; the rest are refused although the format
  describes its own structure.
- **One source per run.** The recording profile runs one recording or one
  live session per Docker engine; the live gateway admits one configured
  system and component, and the association, the `live_state` view and the
  dashboard assume one vehicle.
- **Two input paths.** A file replay and a live drone use different
  contracts, so a file demonstration exercises nothing a physical vehicle
  will use.

A survey of the local corpus on 2026-11-17 (every distinct `.ulg` file under
`.local-discovery/`, instance 0, non-empty subscriptions) shows that the
format variation that matters is small:

| Capability | Topic and fields | Subscriptions |
| --- | --- | --- |
| Position estimate | `vehicle_global_position` `lat`, `lon`: double degrees; `alt`: float metres | 141 |
| GPS position | `vehicle_gps_position` / `sensor_gps` `lat`, `lon`: int32 1e-7 degrees; `alt`: int32 mm | 273 |
| GPS position | `vehicle_gps_position` / `sensor_gps` `latitude_deg`, `longitude_deg`, `altitude_msl_m`: double | 12 |
| Battery | `battery_status` `voltage_v`, `current_a`, `remaining` (float) with optional `voltage_filtered_v`, `discharged_mah`, `connected` | 3,980 |
| State | `vehicle_status` `arming_state`, `nav_state` (uint8); `vehicle_land_detected` `landed`, `maybe_landed` (bool) | 3,968 |

300 files have a geographic position; 3,689 (mostly the 2018 UAV-SEAD indoor
set) have only `vehicle_local_position`. 141 of the 300 have a non-empty
`vehicle_global_position`, including F09, F07, F03 and the two admitted Flight
Review logs; the other 159 have only a GPS position. The median duration of files with a position is
46 s (10th percentile 11 s, 90th 158 s).

Field names and types identify units unambiguously. Enumerations do not:
ADR-0057 found `arming_state` and `nav_state` codes whose meaning changed
between firmware versions under identical field names and types.

## Decision

### Three boundaries

1. **The player knows ULog; the gateway knows MAVLink.** A new replay player
   reads a file, converts the fields it can interpret and sends MAVLink 2
   packets over UDP to the existing gateway at the pace of the recording.
   Everything from the UDP input to the browser is the path a physical PX4
   will use. A radio link and a physical vehicle remain separate checks.
2. **Each vehicle shows what its file supports, and nothing invented.** A
   value the player cannot derive from a reviewed field signature is
   declared unavailable and arrives in SQL as null. The heartbeat that the
   player sends to show the virtual vehicle is reachable is kept apart from
   any state recorded in the flight.
3. **A vehicle joins without a restart or dashboard edit.** The gateway,
   association, serving and dashboard keep their state per vehicle; the
   dashboard lists vehicles from SQL.

### Player

`runtime/continuous/replay_player.py` runs on the worker image in the
archive container's network namespace, like every worker, and sends to the
gateway on loopback. It uses pymavlink from the retained package directory
that the gateway already mounts; nothing is downloaded or installed. The pure
planning (`telemetry/ulog_replay.py`, `telemetry/ulog_samples.py`) has no
network. `python -m runtime.recording.fleet` starts a session without a
simulator and adds, pauses, resumes and removes one player per file while it
runs (`start`, `add`, `pause`, `resume`, `remove`, `status`, `complete`,
`verify`); `ops status`, `collect` and `stop` work on the session as on a
live one.

- **Structure.** The file must be `complete` under the
  [inventory](0058-admission-by-mapping-profile.md#offline-inventory-step-1)
  structural policy and within the ADR-0058 admitted limits (128 MiB,
  2,500,000 frames). Values are decoded only for the fields of the signature
  table below, with the bounded layout decoding the inventory already uses.
- **Field signatures.** A capability is available when its topic has
  instance 0, samples and exactly one of these signatures:

  | MAVLink output | Source, in order of preference | Conversion |
  | --- | --- | --- |
  | `GLOBAL_POSITION_INT.lat/lon` | `vehicle_global_position` `lat`, `lon` double; else GPS `latitude_deg`, `longitude_deg` double; else GPS `lat`, `lon` int32 | degrees × 10⁷ rounded half to even; int32 copied |
  | `GLOBAL_POSITION_INT.alt` | the same topic's `alt` float m, `altitude_msl_m` double m or `alt` int32 mm | to mm |
  | `GLOBAL_POSITION_INT.relative_alt` | `home_position` `alt` float, only for a metre-based position and a home recorded before the first replayed position | position altitude minus home altitude, mm |
  | `GLOBAL_POSITION_INT.vx/vy/vz` | `vehicle_local_position` `vx`, `vy`, `vz` float m/s at the nearest preceding native time | to cm/s |
  | `SYS_STATUS` battery | `battery_status` `voltage_v`, `current_a`, `remaining` | V to mV, A to cA, fraction to percent |
  | `HEARTBEAT` armed flag | `vehicle_status.arming_state` uint8 | 1 disarmed, 2 armed (the codes ADR-0057 found stable); one other code in the replayed interval makes armed unavailable for the whole file |
  | `HEARTBEAT.custom_mode` | not sent in the first step | the navigation mode needs a reviewed `nav_state` to PX4 custom-mode table per firmware; until then mode is unavailable for every file |

  The position estimate is preferred because a physical PX4 fills
  `GLOBAL_POSITION_INT` from it; the GPS signatures serve files without an
  estimate. A value outside the MAVLink field range makes that sample
  unavailable, never clamped.
- **Unavailable values.** Where MAVLink defines a sentinel (`SYS_STATUS`
  voltage `UINT16_MAX`, current and remaining `-1`; `hdg` `UINT16_MAX`), the
  player sends it. Where it defines none (`relative_alt`, `vx/vy/vz`, the
  armed flag, `custom_mode`), the player sends zero and the source
  declaration below marks the field unavailable; serving writes null.
- **Rate.** Position at most 5 Hz, battery and state at 1 Hz, the declared
  stream of ADR-0054. The selected sample is the first one at or after each
  200 ms (position) or 1 s (battery, state) boundary of the file's native
  time, so the sequence depends only on the file.
- **Time.** `time_boot_ms` is the native microsecond timestamp divided by
  1,000, rounded down. Two selected position samples in one millisecond keep
  the first.
- **Pace and control.** Packets go out at 1x native time. A pause stops all
  packets of that vehicle, the availability heartbeat included, so the
  vehicle goes *stale* exactly as a silent physical one would. End of file
  stops the player and is recorded as `ended` in its status file, which
  ADR-0059 reports as `replay_ended` rather than `source_silent`.
- **Ledger.** For every position it sends, the player records the
  measurement identity and a hash of the native fields. The ledger is evidence
  for loss detection, not an input to the pipeline; it holds no coordinates.

### Source declaration and system IDs

Before its first packet the player claims a free MAVLink system ID (2 to
250; 1 stays for a physical or SITL vehicle) by creating `system-<n>.claim`
exclusively in the session's `players/` directory, then writes its
declaration there. The gateway rereads the directory on every status tick and
when a packet arrives from an unknown system, and admits a system only when a
valid declaration exists for it:

```json
{"kind": "ulog-replay", "system": 3, "component": 1,
 "source_id": "sha256:…", "label": "ULog d8a1f180",
 "vehicle": "ulog-d8a1f18026a781ee", "firmware": "46a12a09…",
 "position_topic": "vehicle_global_position",
 "available": {"relative_alt": true, "velocity": true, "battery": true,
               "armed": true, "mode": false}}
```

The declaration is the `source` scope of every event that vehicle publishes,
so the archive holds it with each event and a recomputation from the archive
sees exactly what Flink saw; no separate declaration event is needed. A
declaration may not change while the session runs, and a file can be declared
once. Packets from an undeclared system are captured with their IDs and
counted, never published. A SITL vehicle keeps its run-configuration scope.

### Contract and identity

An event from a replay source carries the profile
`mavlink-vehicle-event-v1`, a new major profile because its source scope and
identity recipe differ. Events from a SITL source keep `px4-live-event-v1`
unchanged, so stored runs and new SITL runs read as before; nothing is
migrated.

- **Replay position identity:** a hash of the profile name, the file's
  `source_id` and `time_boot_ms`. The system ID is a session assignment and
  is not part of it, so replaying a file twice, in any run or under any system
  ID, yields the same measurement IDs, and query deduplication collapses them.
- **Live position identity:** unchanged from ADR-0045 (boot session, system,
  component, `time_boot_ms`).
- **Battery and state:** observation identities by gateway epoch and capture
  sequence, as in ADR-0054. A replayed battery or state value is still
  received as a timeless MAVLink packet; the player's native time is not
  carried through, because a physical vehicle would not supply it either.

### Fleet state downstream

- The gateway keeps packet sequence, loss, receipts, heartbeat age,
  boot-time order and refusal per system; one vehicle's refusal stops only
  that vehicle. Its status file lists every vehicle.
- `FleetRuntime` (`telemetry/fleet_runtime.py`) keeps one ordered lane with a
  contiguous input offset and one ADR-0054 `LiveRuntime` per vehicle, so a
  position is associated only with the same vehicle's latest battery and
  state. Flink, serving's recomputation and the archive-only rebuild all use
  it. A replay's values the declaration marks unavailable, and the player's
  own heartbeat system status, become null in the fact.
- SQL adds vehicle columns to the facts, a `vehicles` table written from each
  gateway snapshot and the players' status files, and a `fleet_state` view
  with *observed*, *stale*, *unknown* and *ended* per vehicle.
- The dashboard (`fleet-live.json`, generated by `build_fleet_live.py`) lists
  vehicles from SQL in a table, a map with every track and per-vehicle
  altitude and battery series. Every replay row says "replay of recording".
- Metrics stay without vehicle labels; per-vehicle values are in SQL and the
  access-controlled run evidence.

### Bounds

The ADR-0054 session bounds stay: 50,000 deliveries and the gateway lifetime.
Four players at the declared rates publish about 28 events per second, about
30 minutes inside the delivery bound. At most 8 concurrent vehicles. F09
(39 minutes) therefore plays a declared interval in a demonstration, not the
complete flight. Raising the bounds needs a measured resource run.

## Alternatives

- **Widen ADR-0058 file admission and replay several files in one recording
  run.** It keeps exact reconciliation against a prepared reference, but a
  file demonstration would exercise nothing a physical vehicle uses, and
  every additional source would need a prepared bundle before the run.
- **Accept a file only when its firmware is reviewed (ADR-0058).** Correct
  for every value, but 5 of 3,989 local files play. Field signatures give
  units; only enumerations need firmware evidence, and those stay
  unavailable without it.
- **Interpret every recorded topic.** Out of scope, as in ADR-0058.
- **Send the replayed native time in a custom MAVLink message.** It would
  keep battery and state timed for replays, but a physical vehicle never sends
  it, so the dashboard would behave differently for the two kinds of source.
- **Derive identity from the system ID.** The ID is assigned per session, so
  the same file would get new measurement IDs in every replay.

## Consequences

Any complete ULog file within the limits can be added as a vehicle; a file
without a position appears in the fleet table without a track, and one without
a battery shows battery unknown. Local-position-only files (3,689 local ones)
need `LOCAL_POSITION_NED` and a local-frame view; that is a later step.
ArduPilot and other autopilots stay refused by the gateway until their
`HEARTBEAT` and mode encoding are reviewed.

Replays through MAVLink lose precision against the file replay: milliseconds
instead of microseconds, millimetres and centivolts, timeless battery and
state. The ADR-0057/0058 file replay remains the path for exact analytics.

Rollback: stop the session; the `px4-live-event-v1` path and stored runs are
unaffected, and nothing deletes retained captures or archives.

## Acceptance of the first step

On one live session of the recording profile:

1. Start the session; `add-vehicle` F09. Its track advances on the map.
2. While F09 plays, `add-vehicle` F03. A second vehicle appears in the
   fleet table and map without a restart or dashboard edit.
3. Pause F09 for a declared interval longer than the 3 s staleness limit.
   F09 shows *stale* with its last receipt age; F03 stays *observed* and its
   track keeps advancing. Resume F09; it returns to *observed*.
4. F03 reaches the end of its file and shows `ended`, not `source_silent`.
5. `ops verify` passes: per vehicle, SQL facts equal the archive
   recomputation, and the replay positions in SQL equal the positions in the
   player's ledger by identity and content, with no capture gap.
6. Offline: a synthetic file built with `tests/ulog_binary.py` with only an
   int32 GPS signature and no battery plays with battery unknown; one with an
   arming code other than 1 and 2 shows armed unavailable, and mode is
   unavailable for every file.

Then: extend signatures to the most frequent unsupported variants of the
local corpus, and run the declared demonstration with 3 to 4 files chosen at
random in advance from those with a position.

## First step run, 2026-11-17

Run `fleet-s1-20261117-01` on one machine, with `runtime.recording.fleet`:

| Step | Observed |
| --- | --- |
| Start without a simulator | Profile, job, workers and gateway ready in 43 s |
| Add F09, interval 86.459 s to 686.459 s of native time | Published within 18 s; 2,999 positions, 601 battery summaries and 601 heartbeats planned |
| Add F03 while F09 played | Second row in `fleet_state` 10 s later; separate batteries (15.4 V and 24.0 V) |
| Pause F09 for 22 s | F09 *stale* at +8 s and +16 s, receipt age 9.0 s and 17.4 s, positions held at 159; F03 *observed*, positions 102 → 152 → 194 |
| Resume F09 | *observed* again 6 s later |
| F03 end of file | *ended*, all 648 planned positions in SQL, current values hidden |
| `complete`, `verify` | passed |

`verify` checked: capture covered, no MAVLink sequence loss for either sender,
SQL fact hash set equal to the archive-only recomputation (3,647 facts from
5,111 deliveries), zero logical repeats, the 1,464 battery and state events
untimed, association statuses as receipt order implies, and each player's
ledger equal to its vehicle's archived positions (2,999 and 648; none missing
or extra). The three `stale` associations are F09's first positions after the
resume, whose last battery and state receipts were older than 3 s.

The dashboard was checked in a signed-in browser. Its first version failed in
every panel: it asked for larger read limits than the read-only Grafana user
may set. It now uses the limits of the other dashboards, verified with both
vehicles drawn. Grafana did not pick up the changed dashboard file on this
Windows bind mount until its container restarted.

Not checked in this step: mode for any file, three or more vehicles, a file
refused by the planner through `add`, a player or gateway restart in a fleet
session, the session bounds, and the files of the 3,689 local logs without a
geographic position.
