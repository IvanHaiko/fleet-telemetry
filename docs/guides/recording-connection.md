# Supported recording connection and combined inspection

The [subsequent two-recording increment](two-recording-view.md) adds F01,
optional shared SQL admission and a recording-selectable Grafana dashboard.
This document preserves the first F09 preparation boundary and its evidence;
the commands and existing outputs remain valid without `--serve`.

## Product boundary

The [active product goal](../roadmap.md#active-product-goal-2026-11-04) is a supported
source-to-state workflow. This increment connects the exact retained F09 original
to one local GPS/battery/recorded-state inspection command. It reuses the reviewed
research mappings, pinned toolchain and existing Grafana/ClickHouse view, with no
new dependency or service. General ULog admission, a second recording, reusable
SQL/view registration, live MAVLink and integrated archive/Kafka/Flink remain open.
The file command does not load SQL: the dashboard uses the earlier, separately
materialized and read-checked F09 tables.

## One command from original source

From the repository root, with the existing pinned `.venv`, private source and
reviewed conversion job, choose a fresh output whose parent already exists:

```powershell
.venv/Scripts/python.exe -m runtime.flight_analytics.recording --job .local-discovery/real-ulog-20261027-001/f09-research-replay-20261103-003.job.json --output .local-discovery/gold-grafana-20261104/connected-recording-v1 --max-age-us 1000000
```

That exact output now exists; use a new name for another attempt. The job supplies
the original path, registered checksum, reviewed battery manifest and delivery
metadata. Only the F09 checksum, supported mapping and existing pseudonym are
enabled. Unknown profiles refuse; rights, producer and clocks are not inferred.
Each adapter rechecks original bytes. Original native timestamps and dropout
framing are checked again before combining the streams. Outputs are:

- `gps/`, `state/`: existing versioned prepared deliveries with manifests.
- `battery/<dataset_run_id>/`: canonical events, rejections and run manifest.
- `inspection.jsonl`: one original GPS observation with independently qualified
  battery, land-detector and commander associations per line.
- `recording.json`: final completion report, artifact digest, source evidence,
  counts, quality distributions, age threshold and limitations.

Existing output and linked output ancestors refuse without replacement. Failure
can leave a partial new directory; retain it and choose a fresh destination. Only
a successfully written, valid `recording.json` reports completion. This is not
atomic whole-directory publication or crash durability. No database, offset or
service is modified. Stdout contains counts/statuses, not coordinates or secrets.
All generated artifacts contain restricted information and must remain ignored.

## Data meaning and bounds

`f09-recording-inspection-v1` retains original GPS rows and measurement IDs.
Each association has `status`, referenced `event_id`, native `age_us` and `values`.
Non-matched associations have NULL ID, age and values. An admitted battery field
may itself be NULL: association and value availability are separate.

The timeline is the observed GPS stream, not simultaneous physical samples or
all source messages. Existing past-only rules and inclusive age bounds remain:
battery uses `f09-native-association-v1` and `rejection_gap` for unknown rejected
timestamps; state uses `f09-gps-state-association-v1`, with file-neighbor
`recording_gap` masks and independent `stale` results. Do not apply one stream's
quality to the others. Battery matching does not establish absence of dropouts.
Units, codes, clock meanings and measurement identities remain unchanged.

The common boot clock is assumed. GPS receiver UTC is display time; battery UTC
has its existing synthetic anchor. No current freshness, physical simultaneity,
flight phase, duration, distance or completeness is inferred. The age parameter
is exploratory. Combined caps are 25,000 GPS rows, 100,000 admitted battery rows
and 64 MiB inspection serialization. Existing adapter/original-file limits remain;
these are input/output bounds, not measured process RSS limits.

## Grafana

The [recording dashboard](http://127.0.0.1:13002/d/flight-f09-details/flight-research-recording-detail)
now has **Latest recorded values in selected interval** near the top. It selects
the last original GPS ordinal inside the receiver-UTC filter, showing 14 fields
with units, association status, value availability and association age. SQL NULLs
display as `Unknown`. GPS ordinal/native boot time identify the inspection point.
This is recorded state, not current aircraft status. Empty intervals have no
snapshot. Each battery/state value is masked by its own association status.

The existing SELECT-only account and nullable joins remain. The new query caps
time at ten seconds, threads at one, memory at 256 MiB and read bytes at 64 MB.
Its six joins need a separate 200,000-row scan bound: the first real Grafana query
refused at 152,010 scanned rows under 150,000. Older panel limits are unchanged.
This is not capacity or sealed concurrent-snapshot evidence.

## Verification, 2026-11-04

Two complete original-file runs with different battery delivery IDs/admission
times produced identical inspection bytes. GPS/state bytes and battery semantic
digests also agree. The report accounts for 21,054 GPS rows, 11,723 admitted
battery records, seven rejections, 2,337 land and 4,644 commander records.

| Stream | Matched | Before first | Rejection gap | Recording gap | Stale |
| --- | ---: | ---: | ---: | ---: | ---: |
| Battery | 21,028 | 1 | 25 | n/a | 0 |
| Land detector | 20,883 | 0 | n/a | 49 | 122 |
| Commander | 21,005 | 0 | n/a | 49 | 0 |

The actual SELECT-only panel query matched the combined artifact field by field
at six points covering both endpoints and all five observed joint quality
combinations. This is sampled combined SQL reconciliation, not full-table
readback. Grafana returned a nonempty frame and the provisioned query matched
the file. An in-app browser rendered the table; explicit widths corrected clipped
status/age columns. No browser package was installed. Earlier individual-table
full-readback and ASOF evidence remains separate and was not rerun.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_recording_inspection.py tests/test_f09_state_time.py tests/test_f09_state.py tests/test_f09_battery_time.py tests/test_f09_coverage.py tests/test_f09_flight_analytics.py -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check runtime/flight_analytics/recording.py runtime/flight_analytics/gps.py scripts/prepare-f09-gps.py tests/test_recording_inspection.py
.venv/Scripts/python.exe -m ruff format --check runtime/flight_analytics/recording.py runtime/flight_analytics/gps.py scripts/prepare-f09-gps.py tests/test_recording_inspection.py
.venv/Scripts/python.exe -m mypy --strict --explicit-package-bases runtime/flight_analytics/recording.py runtime/flight_analytics/gps.py scripts/prepare-f09-gps.py tests/test_recording_inspection.py
git diff --check
```

Results: 21 tests, Ruff lint/format and strict mypy passed. Private probes/reports
remain in the ignored research directory as `recording-replay-check.json` and
`recording-runtime-check.json`. The initial loopback check was sandbox-denied;
permitted execution exposed SQL alias and scan-limit failures, corrected before
the final success. A standalone Playwright package was unavailable; the existing
in-app browser supplied visual verification instead.

## Files and rollback

Created: `runtime/flight_analytics/gps.py` (unchanged GPS preparation extracted
from its script), `runtime/flight_analytics/recording.py`,
`tests/test_recording_inspection.py`, and this document.
Updated: `scripts/prepare-f09-gps.py` (compatible entry point),
`runtime/flight_analytics/dashboards/flight-f09-details.json`, README, roadmap,
architecture, data contracts, testing strategy, the F09 state guide and ADR-0043.

Rollback stops using the command, removes panel 19 and shifts later panels up
13 grid units, then reloads existing Grafana provisioning. The GPS script keeps
its extracted implementation. Preserve sources, outputs, SQL tables and volumes.
No schema migration, new credentials, commit, publication or cloud work occurred.
Next: second real log through this entry point and shared view, with reviewed
missing-stream and multi-recording behavior.
