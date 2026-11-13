# ADR-0046: Bounded live PX4 position through processing, archive and SQL

**Status:** Proposed; isolated local integration demonstrated, 2026-11-04.

The [execution record](../guides/live-position-source-query.md) reconciles 16 new live
positions and 18 deliveries through Kafka/Flink, immutable S3 and SQL. Repeated
SQL insertion preserves 16 logical measurements. Continuous integration and
recovery remain open; this result does not enlarge the accepted Battery scope.

## Problem and selected result

The maintainer authorized taking the existing live PX4 source through Kafka,
Flink, archive and SQL. The continuous Battery gate is contract-specific; the
earlier simulator position experiment has no retained archive/SQL reconciliation.
Deliver one coherent small result: 16 newly generated, fix-qualified position
observations and two byte-identical repeated deliveries, with exact identities,
source offsets, values and archive readback. Keep the running direct live monitor
and all historical evidence intact. No flight-control action is required.

Use a separate native-boot position input contract, preserving the already
documented `px4-mavlink-position-v1` identity recipe. The wire event carries
selected original GLOBAL_POSITION_INT integers and declared source boot session,
not invented UTC or timestamp-less battery samples. Flink performs validated
unit conversion and emits one source-coordinate-qualified fact per delivery.
SQL queries deduplicate measurements by identity only after full conflict/content
reconciliation. Its at-least-once Kafka output is not an exactly-once claim.

Retain complete original selected position and qualifying GPS packets before
publication. Independently consume Kafka input with the existing bounded native
reader and archive its exact observations with existing SegmentedArchive/S3
immutable publication and reader readback. Link retained packet bytes by hash in
the archive plan. This covers the selected interval, not every MAVLink message,
the whole flight or acquisition completeness.

## Runtime and alternatives

Reuse existing pinned one-broker Kafka, PyFlink 2.2.1 JobManager/TaskManager,
SeaweedFS and ClickHouse images in a fresh Compose project and fresh volumes.
Use retained native/S3 dependency artifacts after import checks; install nothing.
Loopback ports, explicit unused subnets, resource limits and scoped new storage
credentials remain required. Do not change old SQL grants or mount old datasets.
The closed local profile uses one broker/partition, so there is no broker/host
availability guarantee. Expect roughly 8 GiB of aggregate configured container
limits; the actual tiny-run use must be observed, not extrapolated as capacity.

The existing six-broker/eighteen-partition continuous wrapper deliberately
refuses this topology. Keep it unchanged. Reuse the maintained native reader's
single-broker boundary instead of weakening those guards. New observation types
do not enter the Battery gate or its historical identity/checkpoint state.

A filesystem-only archive would miss the required S3 publication/readback
boundary. A copied Battery timestamp anchor would mislabel physical time. A new
streaming framework or generic orchestration layer would add maintenance before
the first useful source-to-query result. The selected change is one small
contract/transform, bounded Flink graph and scenario driver with existing clients.

## Admission, verification and rollback

Source producer acknowledgement, independent archive observations, Flink source
receipts and SQL identities/content must agree exactly. Counts alone are
insufficient. Retention/source identity changes, competing event content or
unconfirmed writes refuse success. Demonstrate duplicate delivery and repeated
SQL insertion without inflated unique results. Preserve raw packets, generated
plans, receipts, checkpoints and all failed attempts.

The source boot session remains an operator assertion. Unsigned MAVLink,
physical source/clock admission, continuously unbounded operation, full recovery
and production/release gates remain open. A bounded live-source slice does not
complete those milestones. Rollback stops only the new integration project;
retain its volumes and source evidence. No old source/offset reset, credential
change, cloud mutation, commit or remote publication is authorized.
