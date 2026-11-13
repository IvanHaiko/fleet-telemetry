# ADR-0045: Live PX4 SITL MAVLink observation and interruption drill

**Status:** Proposed bounded local simulation profile, 2026-11-04.

## Problem and selected scope

The maintainer selected existing PX4 SITL as the next live MAVLink source. The
historical two-recording view cannot establish live connectivity. Use one fresh
simulator and a standalone receiver/API/page, reusing the pinned pymavlink
2.4.50 dependency, existing image family and bounded heartbeat HTTP server.
Keep Kafka/Flink/archive integration for the following increment. No arming,
takeoff, mission, flight-control or physical-device action is required.

Receive only one configured PX4 system/component. Decode HEARTBEAT,
GPS_RAW_INT, GLOBAL_POSITION_INT and SYS_STATUS with maintained protocol code;
retain raw mode/status codes, units, missing sentinels and native boot time.
Heartbeat receipt qualifies observed presence separately from per-stream update
age. Lack of position/battery does not prove a sensor is absent. An independent
monitor/collector-health check makes gateway failure unknown rather than healthy.

Position identity binds a caller-declared source boot session, source IDs,
profile and native boot milliseconds. Repeated or competing native position
observations do not renew freshness. A boot-time decrease/wrap refuses the
session until an explicit new source boot-session configuration. Never use
arrival time, packet sequence or random receiver epoch as measurement identity.
Heartbeat/SYS_STATUS do not provide measurement time: retain NULL measurement
time/identity and describe their age as receipt age. Do not invent physical UTC.

Unsigned local MAVLink is not authenticated or generally replay-protected.
System/component IDs are filters, not producer proof. A recorded unsigned
heartbeat can mimic receipt; this experiment cannot establish a radio-security
or physical-device guarantee. Do not label SYS_STATUS as a per-battery canonical
measurement or infer charging/flight phases from raw flags.

## Runtime, alternatives and cost

Use a separate internal Compose network, one 512 MiB/one-CPU PX4 container and
a bounded receiver container. Publish only its authenticated HTTP UI/API on
loopback; do not publish UDP or mount old datasets/credentials. Reuse existing
pinned Linux dependency files after an actual import probe; no install, image
download, new service family or cloud work is needed. Existing operational
credentials and historical SQL access remain unchanged.

Runtime admission found exhausted automatic Docker pools and internal-only
networks without host-port publication. Use checked explicit subnets plus a
gateway-only access bridge for loopback HTTP; UDP remains unpublished. That
bridge permits egress, so it is not full enforced isolation. No old network is
removed. Preserve GPS raw microseconds as an exact string with unverified clock
basis, and label position time as a native boot timestamp without asserting
physical sample/publication semantics.

Copying the simulation-only Kafka gateway would retain unnecessary historical
stack coupling and missing battery/state support. Changing canonical Battery
events to fit timestamp-less messages would obscure time meaning. A custom
MAVLink decoder adds checksum/format maintenance. The selected profile adds one
small observational projection and bounded runtime/page using existing clients.

## Evidence and rollback

Verify units/sentinels, wrong-source refusal, duplicate/clock rules, per-stream
staleness and unknown-on-gateway-failure with tiny inputs. Then observe actual
SITL packets, stop/resume its MAVLink sender, and restart the gateway without
restarting PX4 or renewing retained data. Record transition times and resource
limits. This tests a live simulator and application boundary, not RF loss or
physical flight. Stop only this new Compose project on rollback and retain all
outputs and previous projects. Production signing, durable alarms and integrated
Kafka/Flink/archive replay remain open.
