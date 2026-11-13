# ADR-0049: Bounded F09 stream events and reference processing

**Status:** Proposed implementation boundary, 2026-11-10. Offline checks do not
establish Kafka/Flink/archive/SQL runtime admission or completed MVP acceptance.

The [implemented offline step](../guides/f09-stream-replay.md) passes pinned checks and
a complete-field comparison of 538 GPS-centred facts from a 60-second F09
interval. Runtime integration and the gates below remain open.

## Problem and decision

[ADR-0048](0048-integrated-mvp-and-evidence-preservation.md) prioritizes one F09
GPS/battery/state path. Existing battery replay and preloaded recording inspection
do not provide a shared independent-stream input for that path. Introduce a small,
explicit F09 research event profile and bounded replay preparation using existing
protected prepared artifacts. Define a deterministic streaming reference before
connecting the transport and processing runtime. No framework, new service,
package, canonical Battery revision or source/producer admission is introduced.

`f09-recording-event-v1` wraps each original GPS, battery, land-detector or
commander observation with its existing measurement ID, source checksum, original
stream ordinal and native boot timestamp. The outer run ID identifies a delivery,
not a measurement. The original payload and its time meanings remain intact:
battery has a publication timestamp and its declared synthetic anchor, while GPS
and state retain native/source-specific meanings without invented physical UTC.
The wrapper does not reinterpret an unknown source as an accepted F09 record.

Use a half-open native interval and deterministic native-time/stream/ordinal
ordering. A separate bounded context retains preceding battery/state observations
and the reviewed rejection/dropout uncertainty intervals. Equal-time state and
battery inputs precede GPS snapshots. Context records remain evidence, not newly
selected measurements or timestamped fabricated rejections. Full original ULog
bytes, including unprocessed topics, remain retained read-only.

The reference processor consumes ordered events, applies past-only associations
with the existing inclusive age bound and distinct uncertainty masks, and emits
one `f09-recording-fact-v1` per unique selected GPS observation. Facts retain
input-event content hashes and an inspection shape comparable with the existing
recording view. Exact repeated delivery does not multiply snapshots or renew
state; competing content refuses. The reference is an explicitly bounded file
replay, not Flink out-of-order/watermark or transport recovery behavior.

## Integrity, publication and compatibility

The preparer verifies original-source identity and protected prepared artifact
integrity before selecting streams. This reuses earlier reviewed preparation;
it is not a fresh independent parse of the original. The output binds exact
event/context file lengths and hashes, source input references, selected counts,
versions and limitations. Existing output refuses. A completion manifest is
published last; failures retain partial evidence without certifying success.

The bundle reader validates its own permitted files, strict event/context scope,
counts/order and hashes. Input provenance references do not authorize arbitrary
file reads from an untrusted manifest. Bounds cap event count, wire size and
serialized artifacts. No new remote endpoint or storage receipt is created.

These separate experimental profiles do not supersede canonical Battery,
research recording, live-position, archive or checkpoint contracts. Future Kafka
integration must add and verify exact observation coordinates, independently
archive admitted input, and gate serving on coverage. The offline input-event
hash is not a Kafka receipt or a substitute for that archival evidence.

## Alternatives and rollback

Replaying only battery leaves the selected product gap open. Sending already
joined research snapshots as though Flink computed the associations hides the
processing responsibility. General source dispatch/schema infrastructure would
add maintenance before a second admitted stream path is demonstrated. The
selected approach exposes the existing source streams and comparison result
without changing their reviewed interpretations.

Rollback stops using these new preparation/reference commands and retains their
inputs and outputs. No historical source, table, offset, checkpoint, credential
or volume is changed. Runtime integration and broader delivery/recovery tests
remain the next increment after offline evidence is recorded.
