# Real-flight and simulator telemetry inventory

The later [UAV-SEAD and NIST/VTO acquisition](dataset-acquisition.md),
2026-11-06, originally acquired about 73.0 GB of additional research sources,
with explicit unavailable files and source-quality findings. The maintainer
subsequently removed standalone DJI data; about 42.2 GB of source data remains.
The linked record distinguishes historical acquisition from current retention.
Acquisition does not
extend this eleven-file schema/semantic inventory or admit new source profiles.

The [2026-11-04 F01 continuation](../guides/two-recording-view.md) reviews the exact retained
file's firmware state definitions and admits a separate historical state
inspection alongside F09. Its GPS subscription is empty and battery stream is
absent. Source labels and physical origin remain unverified; all other inventory
files still require their own source/semantic admission. This is not general
adoption of the community collection.

## Scope and findings, 2026-11-03

This local research compares eleven PX4 ULog files: eight logs identifying flight
controller hardware and three SITL logs. One hardware log is the previously
reviewed fixed-wing flight; seven are community public logs described by their
curator as quadrotor flights. Those labels and hardware metadata do not prove
each airframe model, operator, flight conditions or origin. The SITL logs are
one community sample and locally generated PX4 SIH and Gazebo flights. Flight-controller
models, firmware versions and simulator instances are not interchangeable with
independently verified drone models.

The eleven files contain **143 distinct observed topic names** across instances.
The [field catalog](telemetry-field-catalog.md) lists observed field names,
wire types and file coverage. Neither catalog is an inventory of every possible
PX4 version, MAVLink message, vehicle, configuration or sensor. It contains
only schema metadata; source measurement values, locations, serials, parameters
and free-text messages remain outside the repository.

## File matrix

`Topics/instances` counts parsed topic-instance datasets, not unique names.
A successful frame walk only means each encountered message fits within the
downloaded bytes; it does not prove original producer completeness or semantic
validity. The parser did not set its corruption flag on any of these files.

| ID | Source / controller reported by file | Firmware hash prefix | Topics/instances | Dropout marks | Framing walk |
| --- | --- | --- | ---: | ---: | --- |
| F01 | Community, CUAV_FMU_V6X | d6f12ad1c4f7 | 126 | 0 | Complete |
| F02 | Community, PX4_FMU_V5 | 71db0903a910 | 56 | 0 | Complete |
| F03 | Community, PX4_FMU_V5 | 46a12a09bf11 | 115 | 0 | Complete |
| F04 | Community sample, PX4_SITL | 2e8918da66af | 151 | 0 | Complete |
| F05 | Community, CUAV_X7PRO | 54f0455ffcd7 | 130 | 1 | Complete |
| F06 | Community, CUAV_X7PRO | a84a11ddd1a2 | 109 | 0 | Complete |
| F07 | Community, PX4_FMU_V6C | d6f12ad1c4f7 | 88 | 0 | Complete |
| F08 | Community, PX4_FMU_V6C | 94cb2012792b | 114 | 0 | Complete |
| F09 | Fixed-wing research, PX4_FMU_V6X | 9a2a8d4d3cf3 | 156 | 15 | Complete |
| F10 | Local SIH quadrotor, PX4_SITL | fca3df865af3 | 88 | 0 | Complete |
| F11 | Local Gazebo X500, PX4_SITL | fca3df865af3 | 88 | 0 | Complete |

F01–F08 were selected from a [public community sample repository](https://github.com/Zxbxdxd/px4-flight-log-dataset),
whose [data license](https://github.com/Zxbxdxd/px4-flight-log-dataset/blob/main/LICENSE_DATA.md)
declares CC BY 4.0. Its `success`/`fail` labels are heuristic and are not used as
flight-ground-truth labels here. F04 identifies itself as SITL despite the
sample grouping. Six sample files were exact prefixes of longer originals and
ended inside a message; pyulog still reported no corruption. Their full public
originals were obtained from [PX4 Flight Review](https://logs.px4.io/browse),
the prefix bytes were compared exactly, and the table uses the originals. The
portal documents CC-BY PX4; individual uploader rights and privacy are not
independently verified. Checksums, source URLs and a commit-pinned acquisition
receipt remain local.

F09 is the previously acquired fixed-wing research flight,
with a documented CC BY 4.0 dataset, but without accepted canonical admission
or a validated UTC anchor. F10–F11 were generated locally as described below. Raw
logs stay in ignored local research storage and are not published as fixtures.

## Observed data families

The average rates below are `(record count - 1) / (last native timestamp - first
native timestamp)` for topic instance 0. They describe recorded data in this
sample, not sensor capability, peak rate, a live MAVLink stream, or a guarantee
that every record was captured. Multiple instances and rates for all observed
topics are retained in the local machine-readable inventory.

| Family | Example observed topic | Files with instance 0 | Observed mean rate |
| --- | --- | ---: | --- |
| Battery and power | `battery_status` | 10 / 11 | 3.3–5.0 Hz |
| Inertial measurements | `sensor_combined` | 11 / 11 | 161.7–250.0 Hz |
| GNSS solution | `vehicle_gps_position` | 9 / 11 | 1.0–30.3 Hz |
| Attitude | `vehicle_attitude` | 11 / 11 | 20.0–250.0 Hz |
| Local position / velocity | `vehicle_local_position` | 11 / 11 | 10.0–125.0 Hz |
| Vehicle state | `vehicle_status` | 11 / 11 | 2.0–8.9 Hz |
| Telemetry link status | `telemetry_status` | 11 / 11 | about 1.0 Hz |
| Air data | `vehicle_air_data` | 11 / 11 | 5.0–20.0 Hz |
| Airspeed sensor | `airspeed` | 1 / 11 | about 1.0 Hz |
| Distance sensor | `distance_sensor` | 3 / 11 | 1.0–50.0 Hz |

`battery_status` is absent from F01. Across the other files the selected stream
has 35–53 parser-expanded fields; `timestamp`, `voltage_v`, `current_a`,
`remaining` and `connected` appear in all ten, with matching declared wire
types in this sample. This does **not** establish matching producer semantics,
calibration, sentinel rules or UTC interpretation. GPS and distance topics
are also absent from some logs. Absence from a log does not prove a sensor was
absent from the aircraft: logging profiles, firmware and run conditions matter.

The 500-events/s benchmark was a 5-Hz *battery-only* profile. An additional
250-Hz stream from 100 vehicles would itself contribute 25,000 events/s before
other streams, transport overhead or batching. This is workload arithmetic,
not a measurement of that larger profile.

## Simulator check

PX4 provides [SIH and Gazebo simulation](https://docs.px4.io/main/en/simulation/).
The fixed official `px4io/px4-sitl:v1.18.0-rc1` image index digest
`sha256:39d5a950208a5a45fccbbb0670bd8716663ed0b350ef738447581395e0c92d97`
was tested as an isolated experiment; it is a release candidate, not a project
runtime dependency. The simulator ran with no network, a 1 GiB limit and two
CPUs. A quadrotor executed an internal takeoff to the default 2.5 m target and
landing; PX4 reported takeoff, landing and disarm. The generated 26,883,362-byte
ULog, SHA-256 `6275a6ddd9019489b1d094fe3af278e616685806fbda17c634d7d5b45c6e7abb`,
is F10. PX4 shut down cleanly and the container remains stopped.

One live `uorb top` snapshot showed 131 topics, including 250-Hz IMU and
attitude, 8-Hz simulated GPS and 100-Hz in-process battery publication. The
logged F10 battery rate is 5 Hz: internal publication and logged output are
different boundaries. These are simulated values, not validation of real
sensors, radio, dynamics fidelity, or the pipeline in this initial source
inventory. SIH is headless. A later, separate position-map experiment
did exercise a simulator MAVLink gateway through Kafka and Flink; it did not
validate real-device ingestion.

The fixed official `px4io/px4-sitl-gazebo:v1.18.0-rc1` image index digest
`sha256:aa4bbf35f0bd6bdb3269cc96e317c8e78b87f1fc769c734c0818094074e1cc0a`
was also run with no network, 4 GiB, four CPUs and `HEADLESS=1`. Gazebo 8.15.0
started the default 3D world and X500 quadrotor model, and PX4 confirmed a
simulated takeoff, landing and disarm. The initial takeoff was refused because
the isolated experiment had no ground-control station. Only inside this isolated
simulator, `NAV_DLL_ACT` was changed from 2 to 0 for the test; this is not a
real-aircraft configuration recommendation. Startup also reported loopback and
SDF extension warnings. The F11 log is 13,553,509 bytes with SHA-256
`83bf32ac1c753ce5707e92c298b0815f84e4318bfe6c9fe373389b07c79682b4`.
The container stopped cleanly. Gazebo's graphical window, external control,
camera/lidar payloads and MAVLink gateway were not exercised.

## Reproduction and interpretation

Originals, download receipts, per-file full schema/timing inventory, truncated
prefix evidence, simulator log and console output are under ignored
`.local-discovery/fleet-source-inventory-20261103/`; F09 remains in its prior
restricted directory. To regenerate the inventory and field catalog from the
retained files, using the existing pinned pyulog environment:

```powershell
.venv/Scripts/python.exe .local-discovery/fleet-source-inventory-20261103/inspect.py
.venv/Scripts/python.exe .local-discovery/fleet-source-inventory-20261103/build-catalog.py
```

The parser and frame walk are research tools here, not canonical admission.
The next source-to-query increment should select an exact source and versioned
mapping, review clock, units, missing values, identity and source rights, and
reconcile its unmodified input through archive and SQL. Extending the platform
to further topics, MAVLink or real-time gateway traffic needs separate contracts
and workload measurements.
