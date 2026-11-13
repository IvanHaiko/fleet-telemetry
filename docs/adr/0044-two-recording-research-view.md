# ADR-0044: Two-recording local research admission and shared view

**Status:** Proposed bounded research increment, 2026-11-04.

## Problem and decision

The active product goal needs a second real recording through one entry point
and view. F09 alone hides assumptions that every input contains GPS and battery.
Select retained F01 from the inventory: its complete 1,594,052 registered bytes
contain 41 land-detector and 77 commander records. The supported GPS subscription
is empty and the battery stream is absent. Its checksum and reported firmware select a state
research profile. Preserve F09 adapters, identities, tables and dashboards.

Review the exact firmware's versioned VehicleLandDetected and VehicleStatus
definitions; retain code/flag meanings and boot-relative microseconds. The
community curator declares CC BY 4.0, with original portal/PX4 and curator
attribution. Keep original acquisition receipts and all measurements restricted;
the declaration does not verify uploader rights or actual physical producer.
Do not use the curator's heuristic fail label as a flight outcome.

F01 needs the existing default-parameter/binary multi-info service-frame support.
Permit it only for its registered checksum; retain the ordinary 16 MiB/100,000
frame bounds. F09's separate larger limits and every other source's refusals
remain unchanged. Check whole-file framing, exact definitions and counts, parser
dtypes, and independently decode selected original timestamps/state values.

Use commander observations as F01's inspection timeline, without inventing GPS
records or UTC. Mark GPS/battery missing, keep unknown values NULL, and associate
land state only with past observations under the explicit age bound. A recording
pseudonym is not a proven stable physical vehicle identity.

Add a bounded shared projection in fresh `recording_views_v1` tables on the
existing ClickHouse. The same loader and Grafana queries serve both profiles.
Store recording/source/observation identity, native time, optional receiver UTC,
values, separate association/availability status and exact projection JSON.
Registry admission follows complete row readback; identical replay verifies
without inserting, competing or partial existing scopes refuse. SQL has one
documented local writer; no concurrent snapshot/transactional publication is
claimed. Keep the reader SELECT-only and all endpoints/coordinates local.

## Alternatives, maintenance and rollback

Copying F09 tables/queries for each file would perpetuate manual integration.
Generic unknown-firmware interpretation would hide missing-source and clock
assumptions. A new UI, database service or adapter framework is unnecessary.
The selected change maintains one additional exact-file adapter and one shared
research schema/loader/dashboard, using existing dependencies and resources.
Native time drives inspection; epoch or arrival time must not masquerade as UTC.

Rollback stops using the new projection/dashboard and source profile. Preserve
all original data, existing tables, outputs and volumes. No source replacement,
canonical contract migration, cloud action or remote publication is authorized.
Second-source research success does not close live-device or integrated
archive/Kafka/Flink admission.
