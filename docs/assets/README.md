# README screenshots

These are unedited captures of local runs. Most contain synthetic telemetry or
local component metrics. The two flight captures show the public CC BY 4.0 F09
research recording; the recording itself is not distributed here. No capture
contains an entered token or credential. They illustrate interfaces, not current
runtime health or integrated-flight acceptance.

| File | Captured profile | Original check |
| --- | --- | --- |
| `synthetic-telemetry.png` | Three synthetic vehicles showing fresh, stale and unknown battery state | 2026-10-27 live UI check; original `live-ui-20261027-001/telemetry-final.png` |
| `system-monitoring.png` | Grafana local synthetic service/processing monitoring | 2026-10-26 local monitoring check; original `m6-live-20261026-001/dashboard.png` |
| `flight-overview.png` | Grafana dashboard `runtime/flight_analytics/dashboards/flight-overview.json` over the retained F09 research recording in ClickHouse; no map tiles, so the route has no geographic background | 2026-11-13 capture of the existing local flight research stack |
| `flight-recording-detail.png` | Grafana dashboard `flight-f09-details.json` for the same recording; its table shows the last recorded coordinates of the public CC BY 4.0 research flight | 2026-11-13 capture of the existing local flight research stack |
| `flink-local-demo.png` | Flink UI after `scripts/local.py demo`: `local-battery-projection-v1` running at parallelism 2, 3 records in and 3 out | 2026-11-13 one-machine starter; demo reported `"status": "verified", "measurements": 3` |

The originals remain in ignored `.local-discovery/`. Their empty or unavailable
panels retain their original meaning. The screenshots were visually inspected
before copying into this directory; they were not generated as product mockups.
