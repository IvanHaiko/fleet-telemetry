# ADR-0042: Experimental position files in the Gold overview

**Status:** Proposed local synthetic profile, 2026-11-04. Canonical position
admission, real aircraft, live-session identity and production Gold remain open.

## Problem and decision

The Gold overview only recognized battery events, although structural fleet
summaries should extend to other reviewed measurements. The existing simulated
position stream is transient and has no durable identity. Do not relabel it as
canonical or infer live-device identity from arrival time or transport offsets.

Add a bounded file adapter for authored `simulated-position-v1` JSONL. Verify
its existing simulated position fields and convert WGS 84 coordinates to
latitude/longitude degrees and its named MSL and home-relative altitudes to
metres. Require a valid simulated 3D fix, an explicit one-to-one vehicle map,
and a fixed synthetic UTC anchor. Its source timestamp denotes source
publication, not a verified measurement time or real UTC. A source hash is over
exact file bytes and each system's ordinal counts every record of that stream.
Use the event-id-v1 positional recipe with event type `telemetry.position` and
an anchor-bound `sim-position-file-v1-<sha256 of anchor>` normalization version.
A changed anchor or vehicle mapping gives a different identity. No live session
or replay run ID participates in identity.

This is a distinct experimental position-file event profile with a strict reader,
not the existing canonical battery envelope or an accepted general position
contract. The adapter is atomic in memory and bounded to 1 MiB, 1000 records and
10 mapped systems; invalid input refuses the entire batch. The Gold reader
recognizes this profile and refuses incompatible profiles. A new type-specific
reader and semantic projection review are needed for each further event type.
Existing continuous Flink admission remains battery-only; the synthetic test
constructs processing facts locally and inserts them into an isolated ClickHouse
fixture, without claiming this is a real Flink output.

## Alternatives and consequences

Using simulator `system_id` and `boot_ms` as live identity would collide after
reboots or counter wrap; deriving identity from Kafka offsets or arrival time
would break replay. Accepting arbitrary native formats by field name would hide
units and time ambiguity. A file-byte identity and explicit mapping constrain
this first experiment but cannot establish that source labels are genuine or
that a real receiver is connected. Caller-owned source storage, privacy,
provenance and any archival/recovery proof remain outside the adapter.

No service type, dependency, existing table migration or persistent runtime
change is introduced. Roll back by not using the adapter and removing its Gold
reader only after dependent consumers have moved; retain prior data and evidence.
Promotion needs source-to-archive/processing/serving reconciliation, separate
live session/sequence semantics, time/provenance review, compatibility and
failure/recovery checks. This proposal does not supersede ADR-0040.
