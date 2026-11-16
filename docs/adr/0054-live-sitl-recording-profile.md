# ADR-0054: Live PX4 SITL source on the single-machine recording profile

**Status:** Accepted, 2026-11-16. The maintainer selected this profile and the
receipt-ordered association below for roadmap step 4. The second evidence run,
`live-s4-full-20261116-02`, passed the criterion the maintainer approved before
it ([details](#second-evidence-run-2026-11-16)). The first evidence run failed
one limit because of a defect in the recovery analysis, which is fixed.

## Problem

Roadmap step 4 connects the reviewed PX4 SITL source to the responsibilities
that the F09 recording already exercises on the
[single-machine profile](0052-single-machine-recording-profile.md): Kafka
input, Flink association, independent archival, archive-gated SQL serving and
Grafana. It must retain the original capture, source and boot-session
identity, and the limits of untimed and missing streams. During source
silence and a gateway restart it must show the receipt and collector
uncertainty correctly.

Earlier live work stops short of that:

- [ADR-0045](0045-live-px4-mavlink-observation.md) observes position, battery
  summary and mode codes in a standalone receiver, without Kafka, Flink, an
  archive or SQL;
- [ADR-0046](0046-live-position-source-query-slice.md) and
  [ADR-0047](0047-continuous-local-position.md) carry position alone through a
  separate experimental stack.

The recording profile cannot take the live source as it is:

- **No reference.** Serving admits an F09 fact only if it equals a reference
  computed before the run, and the archive checks every delivery against a
  prepared bundle. A live session has neither.
- **No measurement time for battery or state.** HEARTBEAT and SYS_STATUS carry
  no measurement time, so the F09 association by native time cannot apply.
- **F09-typed modules.** The association runtime, output profile and SQL
  columns are specific to F09: its streams, its battery gap policy and its
  native microsecond order.

## Decision

Keep one profile and add a live source beside F09. Kafka, Flink, SeaweedFS,
ClickHouse, Grafana, the segmented archive, the batched serving writer, the
checkpoint settings and the step 3 observer are shared. The live source
replaces the F09 parts that depend on a prepared bundle.

| Responsibility | F09 recording | Live SITL |
| --- | --- | --- |
| Source | prepared bundle, paced publisher | one fresh PX4 SITL, SIH quadrotor, existing pinned image; no arming, takeoff or mission |
| Capture | original ULog | every parsed MAVLink packet received on the gateway port, durably retained before publication |
| Input event | `f09-recording-event-v1` | `px4-live-event-v1` |
| Flink runtime | `RecordingRuntime` | `LiveRuntime`: receipt-ordered association |
| Serving gate | fact equals the prepared reference | fact equals a recomputation from the archived input prefix |
| SQL | F09 fact columns | live fact columns and a current-state view |

**Gateway.** A gateway service runs on the recording worker image, with the
existing retained Linux package directory (pymavlink 2.4.50 and
confluent-kafka 2.16.0) mounted read-only, as ADR-0045 and ADR-0047 did.
Nothing is downloaded or installed. It binds UDP only inside the profile
network. It admits one configured system/component and three messages:

- `GLOBAL_POSITION_INT` becomes a position event;
- `SYS_STATUS` becomes a battery summary;
- `HEARTBEAT` becomes a mode and state event.

The gateway drains the packets that have arrived, appends them to the
epoch's capture with one fsync, and only then publishes the admitted events of
that batch. Every parsed packet is captured with its system and component IDs,
including other message types and other IDs on the same channel; only the
configured source is published. The gateway publishes to partition 0 of the
run's input topic with an idempotent producer, checks that the batch landed at
the next offsets in order, and keeps an acknowledgement ledger. Its status
file reports its epoch, the last source and heartbeat receipts and its counts.

**Detectable capture loss.** All packets on one MAVLink channel share an 8-bit
sequence, whatever their IDs. The capture records it, so a gap inside an epoch
is visible as lost packets; the criterion requires none. Packets sent while the
gateway is down are outside every epoch and show up as the restart gap.

**Declared stream.** The orchestrator starts a PX4 MAVLink instance in
`minimal` mode at 4,000 B/s, then sets `GLOBAL_POSITION_INT` to 5 Hz and
`SYS_STATUS` to 1 Hz; `HEARTBEAT` stays at 1 Hz. The first rehearsal used
`onboard` mode at 20,000 B/s, about 115 packets/s. With an fsync per packet the
gateway fell behind, the socket dropped packets, and heartbeats arrived at
about 0.4 Hz, which the live view rightly showed as *stale*.

**Identity and time.**

- A position keeps the ADR-0045 identity: a hash of the declared boot
  session, system and component IDs and the native `time_boot_ms`. It is
  timed in native boot milliseconds, with the clock basis unverified.
- A battery or state event has no measurement time and no measurement
  identity. Its key is an observation identity: a hash of the gateway epoch
  and its capture sequence. That identifies a receipt, not a measurement, so
  two identical heartbeats stay two observations.
- Receipt time is gateway Unix milliseconds, kept as delivery metadata. It
  never becomes measurement time or identity.
- A decreasing boot time, or competing content at the same boot time, is
  refused by the gateway, as in ADR-0045. The boot session can change only
  through a new run configuration.

**Receipt-ordered association.** `LiveRuntime` processes the input in topic
order. For each new position it attaches the latest battery and the latest
state that precede it in that order. Each association has one of these
statuses:

- `receipt_ordered`: received in the same gateway epoch, at most
  `max_receipt_age_ms` (3 s by default) before the position's receipt;
- `stale`: older than that limit;
- `unknown_after_restart`: received in an earlier gateway epoch;
- `none`: nothing received.

Values are carried only with `receipt_ordered`; the other statuses carry
nulls. The association also carries the receipt age. Never is it described as
an association by measurement time. All of this is a function of the event
content in topic order, so a replay from the archive yields the same facts.

**Archive and serving gate.** The archive worker uses the same
`SegmentedArchive`. Its control objects are the live session declaration
instead of the F09 bundle, manifest and reference. Live serving reads the
archived segments in order, recomputes the facts with `LiveRuntime`, and
admits a Flink output only if it equals the recomputed fact for the same
input offset. This is the step 3 rebuild path used incrementally. The
session ends when the gateway records its final published count and the
archive reaches it.

**Uncertainty in SQL.** Each second, live serving writes one collector row
from the gateway's status file. A `live_state` view derives three states, so
missing data never renews health:

- *observed*: a source receipt in the last 3 s;
- *stale*: the collector is current but the source is silent;
- *unknown*: no current collector row, or serving itself is not current.

Current values are null unless the state is observed.

**Bounds.** One session is limited to 50,000 deliveries (the recording lane's
event cap) and 30 minutes. Hitting either limit ends publication with a
recorded reason; it never drops data silently.

## Alternatives, cost and maintenance

- **Extend the ADR-0047 position stack.** Less operator work, but it would
  leave two MVP profiles with separate operations for step 5.
- **Associate battery and state by gateway receipt time as if it were
  measurement time.** It would look like the F09 association while inventing a
  clock meaning the source does not provide.
- **Leave battery and state unassociated.** Strict, but the dashboard could
  not show them beside the track point.
- **Add pymavlink to the worker image.** Cleaner packaging, but it needs a new
  image build and a download; the retained directory already passes the
  ADR-0045 import probe.
- **Generalize `RecordingRuntime` behind one interface.** The F09 battery gap
  policy and native-time order share little with the live rules. Two small
  runtimes with the same output and checkpoint pattern are easier to review.

New surface: a live event contract and runtime, a gateway, a live operator
selected by the job configuration, a live archive control set, a live serving
gate, live SQL columns and view, the PX4 and gateway services in the profile,
and a Grafana screen. No new dependency, image or service family.

## Acceptance

Before the evidence run the maintainer approves a `criterion.json` written by
the orchestrator. It is expected to cover:

- one fresh SITL session of about 10 minutes, with a declared source silence
  (the SITL container paused) and a gateway restart;
- capture coverage: every published event's raw packet is in the capture;
- archive coverage: every input delivery is archived and read back exactly;
- the SQL fact hash set equals an archive-only rebuild with `LiveRuntime`,
  with no logical repeats;
- no battery or state value carries a measurement time;
- after the gateway restart, positions show `unknown_after_restart` until new
  battery and state packets pass;
- `live_state` shows *stale* during the silence and *unknown* while the
  gateway is down, both within the 3 s receipt limit plus one sample;
- a declared visibility limit for position facts outside the drills.

## Rehearsals, 2026-11-16

Each rehearsal used a fresh scope, a 130-second session, a 15-second source
silence from 40 s and a 10-second gateway outage from 80 s. Evidence is under
`.local-discovery/<run>/`.

| Run | Result | What it showed |
| --- | --- | --- |
| `live-s4-reh-20261116-01` | failed: 72% *observed* | Correctness passed. With `onboard` streams and an fsync per packet, heartbeats reached the gateway at about 0.4 Hz |
| `-02` | failed: capture loss | Declared stream and batched capture: 100% *observed*. The new sequence check counted gaps |
| `-03` | failed: capture loss | The gaps were packets from other IDs on the same channel, which the gateway dropped before capture |
| `-04` | failed: capture loss, restart check | pymavlink reports system 0 and sequence 0 for message IDs outside its dialect (8 and 411). The restart check wrongly required an unknown state where the first new heartbeat preceded the first position |
| `-05` | **passed** | Header read from packet bytes; exact restart check |

Rehearsal `-05`:

- **Capture and archive.** 2,176 packets were captured in two epochs with no
  sequence gap, and every acknowledged event matches its capture record. 708
  deliveries were archived, equal to the published count.
- **SQL.** The SQL hash set of 506 position facts equals the archive-only
  rebuild, with no logical repeats.
- **Statuses.** No battery or state event carries time. Every position's
  statuses match what input order implies; after the restart, 5 battery and 4
  state statuses were `unknown_after_restart`.
- **live_state.** It showed *stale* in all 11 silence samples, *unknown* in
  all 6 gateway-down samples, and *observed* in 100% of the other samples.
- **Timing.** Visibility outside the drills stayed within 1 s (the sample
  interval); recovery was 17.3 s after the silence and 11.3 s after the
  restart, and the drain 0 s.

## Evidence run, 2026-11-16

`live-s4-full-20261116-01` ran the approved criterion: a 600-second session,
a 30-second source silence from 180 s and a 15-second gateway outage from
360 s, with the observer sampling every second. **Result: failed the declared
criterion** on one limit. Every correctness and live-view check passed.

- **Capture.** 11,633 packets were captured in two epochs, all from the
  configured source, with no sequence gap. All 3,783 acknowledged events match
  capture records marked published.
- **Archive and SQL.** 3,783 deliveries were archived, equal to the published
  count: 2,703 positions and 1,080 battery and state events, none of them with
  measurement time. The SQL hash set of 2,703 facts equals the archive-only
  rebuild, with 2,703 distinct identities and DISTINCT view rows and no
  conflicting content.
- **Statuses.** Every position's battery and state status matches what input
  order implies; after the restart, 4 battery and 3 state statuses were
  `unknown_after_restart`.
- **live_state.** It showed *stale* in all 25 silence samples, *unknown* in all
  10 gateway-down samples, and *observed* in all 545 other samples.
- **Timing.** Visibility outside the drills stayed within 1 s, and the drain
  was 0 s. The one Flink job ran throughout: 62 checkpoints completed, one
  failed, no exceptions and no operator refusal.

The failed limit was recovery after the source silence: 31.8 s against 30 s.
The analysis applied the limit to the whole window from the pause, so the
declared 30-second silence counted against it; the catch-up after the resume
took 1.6 s. Step 3 had already exempted the archive pause from this rule, but
not the live drills. The analysis now judges every drill of declared length by
its catch-up, and the criterion states the scope. A post-hoc re-evaluation
(`reanalysis-catch-up.json`, not acceptance evidence) passes every limit: the
catch-up took 1.6 s after the silence and 0.4 s after the gateway restart.

## Second evidence run, 2026-11-16

`live-s4-full-20261116-02` repeated the schedule with the corrected analysis.
Its `criterion.json` states that a drill's recovery limit applies to the
catch-up from the resume action. **Result: passed.**

| Check | Result |
| --- | --- |
| Capture | 11,631 packets in two epochs, all from the configured source, no sequence gap; all 3,782 acknowledged events match capture records |
| Archive | 3,782 deliveries, equal to the published count: 2,702 positions, 1,080 battery and state events without measurement time |
| SQL against the archive-only rebuild | equal hash sets of 2,702 facts; 2,702 identities and DISTINCT view rows; no conflicting content |
| Association statuses | all 2,702 match input order; after the restart, 2 battery and 1 state status were `unknown_after_restart` |
| `live_state` | *stale* in 26/26 silence samples, *unknown* in 10/10 gateway-down samples, *observed* in 543/543 other samples |
| Visibility outside the drills | at most 1 s (the sample interval) against 5 s |
| Catch-up after the silence / restart | 0.9 s / 0.8 s against 30 s |
| Terminal drain | 1 s against 30 s |
| Flink | one job, 63 of 63 checkpoints completed, no exception or operator refusal |

The session ran in one PX4 boot session. A simulator restart, a second
vehicle and a gateway restart while the simulator is silent were not
exercised.

## Not covered

A physical vehicle, an RF link, authenticated MAVLink, other firmware, a
second vehicle, physical UTC alignment, and flight control. Unsigned MAVLink
can be replayed or spoofed; the system and component IDs are filters, not
proof of the producer.
