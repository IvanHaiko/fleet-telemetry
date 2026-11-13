# Live PX4 MAVLink observation and recovery

## Result and supported boundary

One newly started PX4 SITL generates live MAVLink into a bounded receiver and
[live page](http://127.0.0.1:18771/). Position, battery summary, recorded mode
codes, receipt age and observed heartbeat presence update without historical
replay. The actual sender stop/resume and gateway restart drill passes.
This follows the maintainer's explicit choice of existing PX4 SITL; it is not a
physical drone, RF-link test, flight-control system or production source admission.
[ADR-0045](../adr/0045-live-px4-mavlink-observation.md) records the scoped decision.
Kafka/Flink/archival delivery of this source remains the next integration task.

## Existing dependencies and isolated runtime

`compose/mavlink-live.yml` owns project `fleetmavlink20261104`, independent of
older simulators and historical/analytical projects. It reuses existing images:

- Python digest `ae14d4ce8771606477a81446e7ef429edd6762305fc50c84507c1041fa8285d1`,
  actually CPython 3.13.18; gateway limit 128 MiB, 0.5 CPU and 32 PIDs.
- Official PX4 SITL digest
  `39d5a950208a5a45fccbbb0670bd8716663ed0b350ef738447581395e0c92d97`,
  SIH quadrotor model; limit 512 MiB, one CPU and 256 PIDs.

The existing Linux package directory imports pymavlink 2.4.50, lxml 6.1.3 and
fastcrc 0.5.0 in the pinned container. No package/image was downloaded or
installed. The directory is a retained local dependency artifact, not a newly
validated fresh-install recipe. `pyproject.toml`/`uv.lock` remain unchanged.
The gateway mounts code, this dependency artifact and its own private config
read-only; it has no historical sources, SQL credentials, Kafka or Docker socket.

The internal network uses checked `10.254.247.0/28`; only the gateway also joins
the `10.254.247.16/28` access bridge for Docker's loopback HTTP publication.
The latter permits egress and is not enforced full network isolation. Neither
UDP nor the simulator ports are published. Override `FLEET_MAVLINK_SUBNET` and
`FLEET_MAVLINK_ACCESS_SUBNET` after inspecting host networks on another machine.
Automatic Docker pools were exhausted locally; no old networks were deleted.
The first internal-only configuration could not publish HTTP; the access bridge
corrects that runtime limitation. Existing credentials/listeners are unchanged.

## Configure and start

The current protected config is
`.local-discovery/mavlink-live-20261104-001/live.json`; its `runtime.env` contains
only code/dependency/config paths. The config fixes `source_kind: px4-sitl`, one
system/component pair, vehicle pseudonym, explicit `source_boot_session`, UDP
bind/port, and distinct random reader/writer strings of at least 32 characters.
The inherited HTTP resource wrapper requires distinct strings; the new API
implements no writer endpoint. Generate tokens locally and never commit or print
them in command logs. In-container UDP binds `0.0.0.0:14560` only on this profile's
networks. A direct local process can instead bind UDP/HTTP to `127.0.0.1`.

```powershell
docker compose --env-file .local-discovery/mavlink-live-20261104-001/runtime.env -p fleetmavlink20261104 -f compose/mavlink-live.yml up -d --pull never
$liveGatewayIp = docker inspect fleetmavlink20261104-gateway-1 --format '{{(index .NetworkSettings.Networks "fleetmavlink20261104_live-internal").IPAddress}}'
docker exec fleetmavlink20261104-sitl-1 /opt/px4/bin/px4-mavlink start -u 14620 -o 14560 -t $liveGatewayIp -m onboard -r 20000
```

Run the stream-start command only when that source instance is not already
running; the current demonstration is running. Wait for the new simulator's
startup completion. The receiver sends no MAVLink frames. The CLI above configures
only telemetry inside the new simulator, without arming, takeoff or missions.

Open the live page and enter its `reader_token` from the private config. It is
held in browser memory only, never persisted or put in a URL. `GET /v1/mavlink`
and `/metrics` require `Authorization: Bearer <reader_token>`; invalid credentials
return 401, POST returns 405. HTTP is local plaintext; no shared-deployment TLS,
signing or authorization guarantee is implied. The retained in-app tab is signed
in for the current local session. Reloading requires entering the token again.

An operator-declared source boot session identifies the actual uninterrupted
SITL boot, not a replay run or gateway epoch. Preserve it across sender pause
and gateway restart. A simulator reboot/recreation requires explicitly choosing
a new boot session and restarting the gateway. A cold gateway cannot independently
verify that operator assertion; no cross-boot identity guarantee is claimed.

## Fields, clocks and missing values

The maintained pymavlink decoder handles MAVLink framing/checksums. Only the
configured system/component pair and four message types update the view. Those
IDs filter a source; they do not authenticate it. The adapter implements:

| Message | Projection and qualifications |
| --- | --- |
| HEARTBEAT | PX4 autopilot code 12; armed flag from base-mode bit 128; raw base/custom mode and system-status codes. Receipt drives presence, independently of measurement streams. No physical measurement timestamp or measurement identity is invented. |
| GPS_RAW_INT | Fix code 0–8, with separate receipt age. Raw `time_usec` is retained as an exact decimal string in `source_time_raw_us`, with its boot/epoch clock unverified. A recent fix of at least 3 qualifies position display. |
| GLOBAL_POSITION_INT | Native uint32 boot milliseconds; WGS 84 coordinates divided by 10^7; MSL/above-home millimetres divided by 1000; horizontal speed `hypot(vx, vy)/100` and down velocity `vz/100`. The message is a filtered position estimate, not raw GPS. |
| SYS_STATUS | Summary voltage in mV divided by 1000, signed cA divided by 100, remaining percentage divided by 100. UINT16_MAX voltage and -1 current/remaining become NULL. Other negative currents remain signed values without a charging interpretation. No source sample time or measurement identity is supplied. |

Primary definitions: [MAVLink common messages](https://mavlink.io/en/messages/common.html)
and [heartbeat semantics](https://mavlink.io/en/services/heartbeat.html), checked
2026-11-04, together with the pinned installed SDK. SYS_STATUS can be ambiguous
on multi-battery systems; this is not the canonical ULog Battery contract.

`px4-mavlink-live-view-v1` separates heartbeat state from each stream's receipt
freshness. Three seconds is the selected local threshold, not a universal radio
deadline. Fields can remain recent briefly after heartbeat loss because their
last packets arrived later; they expire against their own receipt times. Unknown
values remain NULL. Stale values may remain visible with an explicit stale label;
collector/monitor uncertainty clears displayed values and connection confidence.
Scheduling gaps over 500 ms require new observations. No physical UTC mapping,
sample-age guarantee, source-to-browser latency distribution, phase or safety
verdict is inferred from receipt age or mode codes.

Position time is labelled `source_boot_timestamp`, without asserting whether it
is physical sample or publication time. GPS raw microseconds are not converted
to UTC or interpreted as boot time; the UI's source-boot column therefore remains
unprovided for the fix stream. Decimal-string encoding prevents loss of uint64
precision in browser JSON readers.

Position observation identity is SHA-256 of
`px4-mavlink-position-v1:<declared boot session>:<system>:<component>:GLOBAL_POSITION_INT:<boot_ms>`.
Arrival time, wrapping MAVLink packet sequence and random receiver epoch do not
enter it. Equal native position/content does not renew freshness; competing
content at one native time or decreasing/wrapping source time refuses the live
session with an explicit cause. A decrease may also be reordering, so operator
review is required rather than automatically inventing a new boot identity.
No canonical event contract, historical identity or checkpoint schema is changed.

Unsigned heartbeat/SYS_STATUS messages cannot provide general replay protection
or sample ordering: recorded wire traffic can mimic receipt. The demo never
replays stored facts into this live view. Retained-memory freshness is lost on
receiver restart, and new packets are required. Signing, authenticated producer
attribution, durable alarms and physical radio/device recovery remain open.

## Actual interruption and recovery evidence

The retained `live-drill-v2.json` is generated by a bounded, image-checked public
drill. It controls only the explicitly named isolated SITL project:

```powershell
$env:PYTHONPATH='.'
.venv/Scripts/python.exe scripts/check-mavlink-live.py --config .local-discovery/mavlink-live-20261104-001/live.json --output .local-discovery/mavlink-live-20261104-001/<fresh-report>.json
```

| Observation | Actual result |
| --- | ---: |
| Sender stop command to observed heartbeat loss | 3.012 s |
| Sender resume command to fresh required streams | 1.197 s |
| Gateway restart plus sender resume to fresh streams | 6.458 s |

These are single local command-to-API observations, including polling and
startup/command overhead, not RF detection or steady-state p95/p99. The drill
checks all streams eventually become stale on silence, source boot time advances
on resume, receiver epoch changes on gateway restart, and a restarted gateway
with a silent source returns unknown/NULL instead of old fresh values. Position
IDs reconstruct from the declared boot session/native time across recovery;
battery time/identity stays NULL. Auth and receive-only HTTP checks pass. No OOM
kill is recorded. The new simulator's file logger is stopped after its bounded
startup capture to prevent continued file growth; existing files remain intact.

One later resource snapshot observed 31.6 MiB/128 MiB for the gateway and
10.8 MiB/512 MiB for SITL, not peaks or capacity limits. The two services remain
running for inspection; old projects were not started or modified.

An actual in-app browser signed in without exposing the token, displayed all
14 fields with units/status/receipt age, observed `Connection lost` and stale
values, then `Reconnected` with newer boot times. A gateway restart during source
silence cleared displayed values to Unknown; resuming restored them. This is
one local browser observation, not general browser/sustained-load evidence.

Initial failures remain explicit: zero `recv_match` timeout could expire before
reading the socket, corrected with nonblocking `timeout=None`; the first drill
incorrectly expected all streams to expire at the heartbeat deadline, corrected
to check their independent receipt deadlines. No runtime freshness threshold
was raised. The short initial post-restart HTTP probe preceded server readiness;
the bounded drill waits for actual readiness instead of treating it as success.

## Focused checks and continuation

```powershell
.venv/Scripts/python.exe -m pytest tests/test_mavlink_live.py tests/test_link_watch.py tests/test_live_state.py tests/test_position_live.py -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check telemetry/mavlink_live.py runtime/continuous/mavlink_live.py runtime/continuous/link_watch.py tests/test_mavlink_live.py scripts/check-mavlink-live.py
.venv/Scripts/python.exe -m ruff format --check telemetry/mavlink_live.py runtime/continuous/mavlink_live.py runtime/continuous/link_watch.py tests/test_mavlink_live.py scripts/check-mavlink-live.py
.venv/Scripts/python.exe -m mypy --strict --explicit-package-bases telemetry/mavlink_live.py runtime/continuous/mavlink_live.py runtime/continuous/link_watch.py tests/test_mavlink_live.py scripts/check-mavlink-live.py
docker compose --env-file .local-discovery/mavlink-live-20261104-001/runtime.env -p fleetmavlink20261104 -f compose/mavlink-live.yml config --quiet
git diff --check
```

14 focused tests, Ruff and strict mypy pass. The two existing HTTP tests initially
hit Windows loopback sandbox denial; the permitted loopback run passes. Tests
establish units/sentinels, source filtering, native identity across receiver
epochs, duplicate non-renewal, clock/conflict refusal, separate freshness and
unknown after collector pause. The reused HTTP server's LiveState import is now
type-only, avoiding historical reader dependencies in this isolated runtime.
Fixed-label metrics expose accepted/rejected/ignored packets, gateway health and
heartbeat counts. Rejected includes repeated native position observations and
validation refusals, not a network-loss estimate. They are not yet scraped by
the old Prometheus or wired to durable alerts.

Next: retain this source's original evidence and integrate reviewed event types
through Kafka/Flink/archive/query, without relabelling timestamp-less summaries
as physical samples. Physical PX4/RF, authenticated transport, source-boot proof
and production recovery remain separate gates.

## Changed files and rollback

Created: `telemetry/mavlink_live.py`, `runtime/continuous/mavlink_live.py`,
`runtime/continuous/mavlink_live.html`, `compose/mavlink-live.yml`,
`scripts/check-mavlink-live.py`, `tests/test_mavlink_live.py`, this guide and
ADR-0045. Updated: `runtime/continuous/link_watch.py`, README, roadmap,
architecture, data contracts, testing strategy and deployment guide.
All config/tokens, snapshots, runtime reports and the source startup log remain
local. No existing database, source file or credential was changed; no commit,
push, cloud mutation or destructive cleanup occurred.

Rollback stops only the new profile, retaining containers/networks/files:

```powershell
docker compose --env-file .local-discovery/mavlink-live-20261104-001/runtime.env -p fleetmavlink20261104 -f compose/mavlink-live.yml stop
```

Do not remove old evidence, prune networks or reset offsets. Restarting SITL
after stop is a new source boot: update the explicit boot session before serving
new observations. There is no persistent measurement migration in this increment.
