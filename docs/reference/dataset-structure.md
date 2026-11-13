# Acquired telemetry dataset structure and fields

**Retention update, 2026-11-06:** the maintainer subsequently removed standalone
DJI/Mavic source sets, decoded DJI copies and the portable decoder to recover
space. UAV-SEAD and other manufacturer archives remain. The DJI schemas and
coverage counts below are historical inspection evidence, not current payload
availability. See the [current retention record](dataset-acquisition.md#current-retention-after-authorized-dji-removal-2026-11-06).
The original NIST inspection and its full-source verification now refuse to
overwrite this history after removal. The ULog inspection remains usable.

## Result and inspection scope, 2026-11-06

The [acquired sources](dataset-acquisition.md) are heterogeneous collections,
not a common flat telemetry table. This inspection reads original files and
creates separate, restricted research artifacts. It does not alter originals,
admit a source to the pipeline, create ML features or certify loss-event labels.

The [complete field-name/type catalog](acquired-dataset-field-catalog.md) contains
embedded ULog declarations, decoded DJI raw-record fields, normalized DJI CSV
headers, readable Yuneec CSV headers and the observed Parrot table columns.
It contains no measurement values, locations or device identifiers.

| Source | Inspected scope | Result |
| --- | --- | --- |
| UAV-SEAD | All 3,968 `.ulg` headers; mapping and supporting file structure | 3,962 headers read; six refused; 172 declared format names, 2,163 field/type/array variants, eight schema hashes |
| UAV-SEAD value sample | 20 files, selected by annotation class, file size and common schema variants | Selected streams, native timing and link-status fields inspected; no sample parser errors |
| NIST/VTO archives | All 71 acquired ZIP central directories | Mixed aircraft/controller exports, mobile backups, application files and media |
| Directly named DJI TXT | 34 `DJIFlightRecord*.txt` archive paths | 23 distinct content hashes; all decoded locally; 19 version-11 and four version-9 files |
| Yuneec flight-directory CSV | 101 candidates | 56 readable CSV tables; 45 binary/non-UTF-8 files under `FlightEncryptLog` |
| Parrot flight JSON | Two directly accessible FreeFlight6 files | One 21-column, 3,048-row details table and one summary |
| Other binary sources | 288 flight-related DAT candidates receive prefix inspection only | DAT records, ArduPilot binary/MAVLink logs and hashed iOS backup payloads remain undecoded |

Header declaration coverage and sampled record coverage are separate evidence.
The 20-file sample is purposeful, not a random estimate of corpus-wide behavior.

## UAV-SEAD organization

The acquired snapshot has this general shape:

```text
uav-sead/
  README.md
  mapping.json
  ulg_files/
    <recording>.ulg
    <session-or-date>/<recording>.ulg
    <some recordings>.ulg.mdat.csv
    population_data.csv
    <supporting text and PDF reports>
```

`mapping.json` has 1,396 recording keys. A key is a relative recording path
without the `ulg_files/` prefix and `.ulg` suffix. Its `annotations` array holds
`class`, `note`, an annotation metadata `timestamp`, and optional `ranges`.
Ranges associate a named signal with start/end intervals. Annotation metadata
timestamps are not admitted as flight measurement time.

There are 1,407 annotation entries because a recording can have multiple
annotations, including repeated classes. Distinct mapping-key counts per class
are: Normal 900, Uncategorized 141, External Position 197, Global Position 41,
Altitude 78 and Mechanical 47. These counts overlap. There are 364 annotation
entries with nonempty ranges. None is an explicit radio-link-loss class.
One mapping key does not resolve to an acquired path; its exact name remains in
the private report. Do not create a replacement recording or silently discard it.

The 95 CSV files are supporting reports rather than one complete telemetry
export: `.ulg.mdat.csv` examples contain `name`, `value`, `description` checks
such as estimator consistency; `population_data.csv` contains population-level
summaries. The 144 PDFs are supporting artifacts, not extra flight recordings.

## ULog structure and field groups

A ULog contains format definitions and multiple interleaved topic/instance
streams. Each stream has its own rows and timing. Nested structures and arrays
must be expanded deliberately; the declared format count includes nested types,
not only populated streams. There is no single row that automatically means a
simultaneous snapshot of every sensor.

The read headers declare two controller labels: `PX4_FMU_V5` in 1,707 files and
`PX4FMU_V2` in 2,255. These are controller hardware labels, not independently
verified aircraft models. Nine firmware hashes share eight declared schema
hashes. Matching layouts do not establish matching producer semantics.

| Stream | Example fields actually found in the acquired declarations | Interpretation boundary |
| --- | --- | --- |
| `input_rc` | `timestamp`, `timestamp_last_signal`, `rssi`, `rc_lost`, `rc_failsafe`, `rc_lost_frame_count`, `rc_total_frame_count`, `input_source`, `channel_count`, `values[18]` | Receiver/input state; physical RF and sentinel meaning need producer review |
| `telemetry_status` | `heartbeat_time`, `rssi`, `remote_rssi`, `noise`, `remote_noise`, `rxerrors`, `rate_rx`, `rate_tx`, `rate_txerr`, `type`, `mode` | Schemas vary; a telemetry channel can differ from the RC link |
| `vehicle_status` | `rc_signal_lost`, `data_link_lost`, `data_link_lost_counter`, `failsafe`, `nav_state`, `arming_state`, `failure_detector_status` | Recorded autopilot decisions, not independent failure ground truth |
| `vehicle_status_flags` | `offboard_control_signal_lost`, `offboard_control_loss_timeout`, position-validity and sensor-health fields | Offboard control, RC and ground-station connectivity are distinct |
| `battery_status` | `voltage_v`, `current_a`, `remaining`, cell/connection and status fields | Voltage/current/remaining meanings and unknown values need version review |
| `vehicle_local_position` | `x`, `y`, `z`, `vx`, `vy`, `vz`, validity and estimator fields | Local frame and origin must be retained |
| `vehicle_gps_position` | `lat`, `lon`, `alt`, `fix_type`, `satellites_used`, `eph`, `epv`, `time_utc_usec` | Raw scaling and UTC relation require the matching firmware |
| `sensor_combined`, `vehicle_attitude` | Accelerometer/gyro arrays, timestamps and attitude quaternion | Different publication rates and sample-time conventions |
| `ping`, `logger_status` | `rtt_ms`, `dropped_packets`; logging gaps/dropouts and buffer fields | Transport observations and logging loss are not interchangeable |

All 3,962 readable headers declare `input_rc.rssi`, `rc_lost`, `rc_failsafe`,
`timestamp_last_signal`, `vehicle_status.rc_signal_lost` and `data_link_lost`.
The old-style telemetry `rssi`/`remote_rssi` definitions appear in 2,255 headers;
rate fields appear in 1,699; newer message-loss counters in only eight.
These are declaration counts, not proof of usable measurements in every file.

The selected 20 files have actual `input_rc`, battery, attitude, IMU and vehicle
status records in all 20; telemetry in 19; GPS in only three. Observed average
logged rates range approximately from 1 to 5 Hz for RC/battery and from 1 to
250 Hz for IMU/attitude. These estimates assume native timestamp microseconds;
they describe logged samples, not peak sensor rate or physical clock accuracy.

In this sample, `input_rc.rssi` is constantly 255 in every file. Do not interpret
that value as strong reception without reviewing its sentinel/producer rules.
Telemetry RSSI/noise/error fields, where present in the sample, are constant
zero. RC lost/failsafe flags and `rc_signal_lost` never become true. Four files
have nonzero `data_link_lost`; three zero-to-nonzero transitions are observed.
These are candidates for contextual review, not three confirmed radio failures.

## NIST/VTO organization

The outer structure is device set, acquisition period and acquisition method:

```text
<device set>/<period>/
  aircraft_logical/<archive>.zip
  controller_logical/<archive>.zip
  mobile_android_logical/<archive>.zip
  mobile_iOS_backup/<archive>.zip
  DJI_Assistant_export/<archive>.zip
  README...txt
```

Names vary between sets. An aircraft export, controller dump and mobile backup
are different observation boundaries. A mobile backup also contains app
resources, settings, databases, media and unrelated history. Many `.csv` suffixes
belong to forensic inventory or phone configuration rather than flight data.

Six DJI content hashes occur across more than one device set. Six directly
named DJI TXT paths appear inside Parrot-labeled collections. This establishes
cross-collection duplication/history, not that Parrot uses DJI logging. Do not
use the acquisition folder as physical vehicle identity, model ground truth or
a safe training/test partition boundary.

### DJI TXT fields

The 23 unique directly named TXT files decode to 17 raw record types and a
123-column normalized CSV union. Decoder model enums include Mavic Pro, Mavic
Air, Mavic 2, Mavic 2 Enterprise, Phantom 4 Pro V2, Inspire and Matrice, plus an
unmapped numeric value. These remain decoder/source declarations.

| Record/view | Example fields | Notes |
| --- | --- | --- |
| Raw `OSD` | `flyTime`, `latitude`, `longitude`, `altitude`, `speedX/Y/Z`, `pitch/roll/yaw`, `flightMode`, `rcOutcontrol`, `gpsNum`, `gpsLevel`, `flightAction` | `rcOutcontrol` is present in raw output but omitted from this decoder's normalized CSV |
| Raw `RC` | `aileron`, `elevator`, `throttle`, `rudder`, switches/buttons, `bandwidth` | Controller inputs do not by themselves measure radio quality |
| `SmartBattery`, `CenterBattery`, battery groups | Voltage/current/capacity/temperature/cell fields | Some normalized cell values are estimated; retain the estimation flag |
| `Custom` | Update timestamp | Decoder UTC representation does not validate the device clock |
| `Home`, `AppGPS` | Home/controller positions and associated state | Location and identity values remain restricted |
| `AppTip` | Text message | Decoded message text needs its original context and type |
| CSV `RC.*` | `downlinkSignal`, `uplinkSignal`, stick inputs | Both signal columns are unpopulated in all 23 decoded files |
| CSV `DETAILS.*` | Total flight time/distance and maximum values | Whole-flight aggregates require a leakage review before predictive use |

This decoder populates normalized uplink/downlink signals from OFDM records;
none is emitted in this decoded sample. This is an observation about this tool
and these directly accessible TXT files, not proof that DJI DAT or other exports
lack link information. `rcOutcontrol` is nonzero in three files, but those
episodes are not yet validated radio-loss labels.

Normalized frames carry previous state, use default values and calculate
derived fields. They are not guaranteed simultaneous physical measurements.
The inspected tool version also returns one fewer normalized frame than raw
OSD records in every file: 44,594 frames versus 44,617 OSD records. The final
OSD is not flushed by its frame builder. Two files have decreasing `flyTime`.
Keep raw records and boundaries; do not adopt these CSVs as a lossless pipeline
or training source without a separate fix/admission and clock review.

### Yuneec and Parrot fields

Readable Yuneec tables occur in two acquired Q5004K device sets:

- 18 telemetry CSVs: `fsk_rssi`, `voltage`, `current`, `altitude`,
  `latitude`, `longitude`, `tas`, `gps_used`, `fix_type`, `satellites_num`,
  `roll`, `yaw`, `pitch`, motor/IMU/GPS state, `f_mode`, `error_flags1`.
- 19 remote-input CSVs: unnamed first column and `CH0` through `CH23`.
- 19 remote-GPS CSVs: unnamed first column, `lon`, `lat`, `alt`,
  `accuracy`, `speed`, `angle`.

The 45 non-readable CSV candidates all occur under `FlightEncryptLog`. They
remain binary/encryption candidates rather than fabricated text columns.
Signal scale, units and the unnamed timestamp column still need source review.

The observed Parrot FreeFlight6 details JSON has `details_headers` and
`details_data`: 21 named columns with 3,048 rows. Columns include `time`,
`battery_level`, `wifi_signal`, `flying_state`, `alert_state`, controller/product
GPS, GPS availability/error/satellite count, `speed_vx/vy/vz`, `angle_phi/theta/psi`
and `altitude`. Metadata and a separate summary include software/controller
information and recorded state flags. Their meanings are not yet admitted.

## Tools, evidence and limitations

The ULog research uses existing CPython 3.13.1, pyulog 1.2.2 and NumPy 2.3.5.
For DJI, the project has no existing decoder. Rather than introduce a new
runtime dependency or upload private log content, this inspection uses the
upstream [portable CLI v0.5.7](https://github.com/lvauvillier/dji-log-parser/tree/v0.5.7)
under its retained MIT license. Its 1,431,617-byte Windows ZIP has local SHA-256
`c036d9314bdfa72a9c13e93b956cca89747637c4d5c2a0cabed64a7544242dfd`.
The release did not supply a digest in its API metadata. This locally computed
hash identifies the retained tool; it is not an independent publisher attestation.
Source CLI/frame definitions and tool receipts are retained. No installation,
PATH change, API credential or service is introduced. Version-9/11 parsing runs
offline without the version-13 keychain path. The decoder remains a research
utility with the fidelity limitations above, not a supported project adapter.

Private evidence is under `.local-discovery/dataset-structure-20261106-001/`:

- `uav-sead-headers.json`, `uav-sead-declared-fields.json`,
  `uav-sead-structure-summary.json`: all-header declarations and mapping counts.
- `uav-sead-stream-samples.json`, `uav-sead-link-value-profile.json`,
  `uav-sead-link-profile-summary.json`: the bounded selected-stream readout.
- `nist-archive-inventory.json`, `nist-dji-txt-candidates.json`,
  `nist-dat-header-sample.json`: archive membership and candidate boundaries.
- `nist-dji-decoded-inventory.json`, `nist-dji-raw-field-catalog.json`,
  `nist-dji-csv-field-catalog.json`, `nist-structure-summary.json`: decoded schemas.
- `nist-yuneec-csv-fields.json`, `nist-parrot-json-fields.json`: other readable schemas.
- `tools/`, `dji-tool-receipt.json`, `dji-release.json`, `dji-source-tree.json`:
  pinned tool and source evidence; `dji-decoded/` retains restricted research copies.
- Inspection/profile/catalog scripts and focused verification output.

Actual commands use the existing project environment:

```powershell
.venv/Scripts/python.exe .local-discovery/dataset-structure-20261106-001/inspect_ulog_structure.py
.venv/Scripts/python.exe .local-discovery/dataset-structure-20261106-001/profile_link_fields.py
.venv/Scripts/python.exe .local-discovery/dataset-structure-20261106-001/inspect_nist_structure.py
.venv/Scripts/python.exe .local-discovery/dataset-structure-20261106-001/build_field_catalog.py
```

The checks cover the stated header/sample/archive scopes, decoder exit outcomes,
schema/mapping reconciliation and public-document hygiene. They do not establish
whole-corpus framing, original acquisition completeness, physical producer
identity, UTC accuracy, valid radio-failure labels or ML readiness. Logs hidden
inside iOS backup manifests and DAT containers can add further records; 23 is
not a complete count of all DJI flights in NIST/VTO. Existing canonical limits,
normalization lineages and milestone gates remain unchanged.

The smallest useful continuation is to review a few candidate link-loss episodes
with channel type, changing link-quality measurements, valid clocks and retained
surrounding context before choosing a labeling rule or a larger feature build.
