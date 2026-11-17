# ADR-0058: Admission by mapping profile and an offline inventory of any ULog

**Status:** Proposed, 2026-11-17. Successor to the admission rule of
[ADR-0057](0057-registered-recordings-in-the-integrated-path.md) for files
that are not registered; registered recordings keep ADR-0057 unchanged.

## Problem

ADR-0057 admits a file to the integrated replay only by its exact checksum.
Every new flight therefore needed a code entry, a hand-written battery job and
local paths, even when its firmware and embedded layouts were already
reviewed. A file that was refused gave the operator no answer to "what can I
see in this file?" without starting Kafka, Flink, ClickHouse and Grafana.
Steps 1 and 3 of the [roadmap](../roadmap.md#next-steps-after-the-mvp-evidence-runs-2026-11-17)
ask for both; the background is in the
[design notes](../ulog-replay-and-monitoring.md).

## Decision

### Offline inventory (step 1)

`python -m telemetry.ulog_inventory FILE [--json] [--fields]` reads any file
without services and prints one row per subscription: topic, instance, field
names and types (padding omitted), sample count, native time span, timestamp
regressions and mapping status, then the map, battery and state views and the
replay decision.

Its structural policy is published in `POLICY` and is separate from the strict
checksum-bound scanner (`ulog_integrity.py`), whose bounded definition and
layout decoding it reuses:

- format versions 0 and 1; message kinds B F I M P Q A R D L C S O; other
  ASCII letters are skipped and counted, as the format allows;
- incompatibility flag bit 0 (appended data) is read through, any other bit is
  `unsupported`;
- 512 MiB and 20,000,000 frames by default; the ulog_integrity bounds on
  nesting, expansion, arrays and names;
- the only decoded value is each sample's top-level `uint64_t timestamp`,
  which the format defines.

A file that cannot be read to the end gets `incomplete` (truncated tail,
corrupt frame, unknown message ID, size mismatch, frame limit; the valid
prefix is inventoried and the byte offset given) or `unsupported` (version,
flags, definitions, size limit). Dropout markers are reported apart from
sample counts. A view distinguishes `missing_subscription`,
`empty_subscription`, `unknown_mapping` and `available`; values a reviewed
mapping refuses are counted only where that mapping runs (the admission
report's `battery_rejected_by_mapping`).

### Mapping profiles (step 3)

`telemetry/recordings.py` gains `MappingProfile`: the layout digests of the
four selected topics (`vehicle_gps_position`, `battery_status`,
`vehicle_land_detected`, `vehicle_status`) and the reviewed firmware
revisions. A layout digest is the SHA-256 of the topic's definition joined
with every definition it references, transitively; for a flat topic it equals
the digest ADR-0057 already pins. There is one profile per reviewed reference
recording: `px4-f09-v1`, `px4-f07-v1`, `px4-f03-v1`.

An unregistered file is **admitted** when the inventory is complete, all four
topics are subscribed in instance 0 with their layout digests equal to one
profile's, GPS and battery have samples, no selected topic regresses in time
or is removed, the reported firmware is listed in that profile, and the strict
scanner accepts the file under the admitted limits (128 MiB, 2,500,000 frames,
those of F09). Otherwise the inventory names one reason per unavailable part
(`vehicle_gps_position:empty_subscription`,
`battery_status:candidate_unreviewed_firmware`, `integrity:<reason>`, …) and
the file stays inspectable.

An admitted file gets every name from the profile key
(`px4-f09-v1-recording-event-v1`, `px4-f09-v1-gps-research-v1`,
`ulog-battery-px4-f09-v1-research-v1`, …), its own source identity (the
SHA-256 of the original), counts measured from the file, a file pseudonym
`ulog-<first 16 hex digits>` as vehicle ID (a firmware review is no evidence
of physical vehicle identity) and the label `ULog <8 hex digits>`. The
identity recipes are unchanged, so two files never share a measurement ID, and
a registered checksum always keeps its legacy names.

Admission is decided where the original is read (`runtime/recording/admission.py`,
the `stream_prepare` command, `ops start`). A validator that never sees the
original (Flink, the archive and serving workers, the reference builder)
resolves an unregistered source ID from the versioned name its envelope
carries; it gets the identity and meanings only, with per-file counts
`UNMEASURED` and no firmware, so any count or firmware check fails closed. The
admission decision, the measured counts and the provenance the operator
supplied (`--rights`, `--reference`) are written to `admission.json` in the
run directory; the battery conversion job is generated from the profile.

```text
.venv/Scripts/python.exe -m telemetry.ulog_inventory <file.ulg>
.venv/Scripts/python.exe -m runtime.recording.ops start --run-id <run> --source-file <file.ulg> --rights "<licence evidence>" --reference "<where it came from>"
```

### Firmware reviewed beyond the reference recordings

`px4-f09-v1` also lists `54f0455ffcd755534539a7cf33a09a20bf71d29d` and
`94cb2012792b2ae89f0b147cfee53ee31ae550be`. At both commits the upstream
`msg/versioned/BatteryStatus.msg`, `msg/SensorGps.msg` and
`msg/versioned/VehicleLandDetected.msg` are byte-identical to those at F09's
`9a2a8d4d…`, and `msg/versioned/VehicleStatus.msg` differs only in the
`VEHICLE_TYPE_*` constants (rotary wing 0→1, fixed wing 1→2, rover 2→3), a
field no mapping reads. Units, sentinels, the arming and navigation-state
enumerations and the boot-microsecond clock of every selected field are
therefore those already reviewed for F09. The fetched files are kept in
ignored local storage (`.local-discovery/admission-20261117/firmware-review/`).

## Alternatives

- **Keep exact-file registration (ADR-0057).** Safe, but every flight costs a
  code change and a hand-written job even when nothing new is reviewed.
- **Admit by layout digest alone.** Rejected: ADR-0057 found meanings changing
  between firmware with equal topic names (F03's arming enumeration and GPS
  units); equal layouts on unreviewed firmware stay `candidate`.
- **Persist admissions in a shared registry file read by every process.** It
  adds a format, a lifecycle and a place where processes can disagree. The
  versioned name in each envelope already identifies the profile; the
  admission record stays evidence in the run directory.
- **A generic decoder of every topic for the dashboards.** Out of scope:
  interpreted values appear only through reviewed mappings. Raw streaming of
  all topics is step 4 and waits for a named consumer.

## Consequences

Any structurally valid ULog can be inspected without services; any file on a
reviewed firmware with reviewed layouts replays through the integrated path
without a code change. A new firmware revision needs a review like the one
above and one line in `REVIEWED_FIRMWARE`. Generated rights and provenance
remain the operator's assertion. The admission record is not recomputed
downstream; a tampered bundle is still refused by its checksummed manifest.

Rollback: remove the profile entries; admitted runs stay readable as stored
evidence, and registered recordings are unaffected.

## Evidence, 2026-11-17

Offline, with this decision's code:

- F01 inventory: `vehicle_gps_position` subscribed with 0 samples (map
  `empty_subscription`), no `battery_status` subscription (battery
  `missing_subscription`), 41 `vehicle_land_detected` and 77 `vehicle_status`
  samples (state `available`); replay `unavailable` with those two reasons.
- Synthetic fixture (`tests/test_ulog_inventory.py`): a custom topic in two
  instances and no GPS lists both instance counts (3 and 1) and its fields
  with no registry edit; a truncated tail is `incomplete` with the valid
  prefix counted; other incompatibility flags and format version 2 are
  `unsupported`.
- Derived copy of F09, cut at the first frame boundary after 24 MiB
  (25,165,877 bytes, `sha256:7a490a1c…`): admitted under `px4-f09-v1` with
  4,361 GPS, 2,422 battery, 485 and 960 state records; bundle of 8,228 events
  and a reference of 4,361 facts, none of whose measurement IDs is among
  F09's 21,054. The same copy with its `ver_sw` value replaced by forty zeros
  stays inspectable, every selected topic
  `candidate_unreviewed_firmware`, replay `unavailable`.
- F09 regenerated from the original with this code (`recording --job`,
  `stream_prepare` over the complete flight, `stream_reference`) equals the
  stored inspection, GPS and state artifacts and the `f09-full-20261113-001`
  bundle and reference byte for byte.
- Two real flights from the 2026-11-03 Flight Review acquisition, not
  previously processed, are admitted under `px4-f09-v1` after the firmware
  review: `695ad7af…` (firmware `54f0455f`; 467 GPS, 468 battery, 99 + 189
  state; 1,223 events, 467 facts) and `d0d747d2…` (firmware `94cb2012`; 303
  GPS, 303 battery, 67 + 120 state; 793 events, 303 facts). No battery value
  was refused.
- Inventory of the six Flight Review originals: F07 and F03 `registered`; two
  more with layouts unknown to every profile (`unknown_definition`).
- Every ULog file in ignored local storage (4,180 files, 3,987 distinct;
  mostly the 2018 UAV-SEAD set), before the firmware review above: a report
  for every file, none raised. 3,965 `complete`; 14 `incomplete` (13
  truncated tails, 1 data size mismatch); 8 `unsupported` (6 not ULog, 1
  invalid UTF-8 in a definition, 1 unsupported incompatibility flag). Replay:
  3 `registered`, none admitted, 3,984 `unavailable`; 20 files matched a
  profile's layouts on unreviewed firmware. The map view was `available` in 5
  files, `missing_subscription` in 3,698 (older logs name the topic
  differently), `unknown_mapping` in 274. Older layouts therefore remain
  inspection-only until a profile reviews them.
- Ruff, format and strict mypy pass; pytest 738 passed, 7 skipped
  (environment-specific, unchanged).

Integrated run on the single-machine profile: `x695-s2-drill-20261117-02`
replayed `695ad7af…` whole with `ops start --source-file`, with no registry or
code entry for that file. Admission wrote `admission.json` (profile
`px4-f09-v1`, firmware `54f0455f`, measured counts, operator-supplied rights
and reference); 1,225 deliveries (1,223 events and the 2 declared repeats)
gave 467 facts; `ops verify` passed: the SQL fact hash set equals the
reference, zero logical repeats, and an archive-only rebuild is equal. The
same run was the step 2 drill; its phases are in
[ADR-0059](0059-explaining-stalled-values.md#drill-2026-11-17).

Not checked: the dashboard of that run rendered in a signed-in browser (its
queries were run through the Grafana datasource API only); `d0d747d2…` and
the derived F09 copy through the integrated path; fault injection or
restoration on an admitted file.
