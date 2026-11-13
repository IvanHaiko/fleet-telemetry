# ADR-0043: Local real-flight Grafana and ClickHouse research view

## Combined inspection continuation, 2026-11-04

The authorized [source-to-state priority](../roadmap.md#active-product-goal-2026-11-04)
starts with [one F09 preparation command](../guides/recording-connection.md) and a
combined values/status/age panel in the existing Grafana. Reuse pinned adapters
and existing tables; retain distinct battery/state uncertainty rules. A separate
custom UI or generic adapter framework would add maintenance before a second
source exists. This increment adds no dependency, service or canonical schema.
The new six-join query has a measured need for a finite 200,000-row scan bound;
other query limits remain. This continuation preserves the proposed research
status and does not supersede source identity, producer or clock decisions.

**Status:** Proposed local research profile, 2026-11-04. General real-source,
live-drone and production admission remain open.

## Problem and decision

The maintainer needs one interface linking a flight map and telemetry, with
ClickHouse for investigation and Grafana for both flight and infrastructure
views. Current Grafana reads Prometheus only; existing position paths are
simulation-only. Build a separately scoped local F09 historical research view
using the existing ClickHouse/Grafana runtime families. Do not alter retained
volumes, credentials, live jobs or existing monitoring.

The first source is the exact F09 file already registered under ADR-0041. GPS
fields require original checksum and framing verification, pinned firmware and
embedded message-definition checks, whole-stream ordinal reconciliation, and
explicit validity/units. Preserve native timestamps and identify GPS-provided
UTC separately: GPS UTC describes its reported time and is not silently
relabelled as physical sample time. Source dropouts remain visible; physical
origin and original acquisition completeness remain unproven. This narrow
research profile is not a generic ULog mapping. Keep real coordinates local,
within a separate authenticated, loopback-bound runtime; external map tile
providers must not receive location-sensitive requests by default.

Use Grafana's maintained ClickHouse datasource plugin pinned to 4.23.2, with
its official signed distribution and matching Grafana 13.2.4. Configure a
separate SELECT-only database user. Grafana datasource/plugin adds supply-chain,
upgrade and compatibility maintenance and a query privilege boundary; pin and
review the artifact, use bounded query resources, and do not add automated plugin
updates. Link the map to a selected recording dashboard with the same context.
Keep Prometheus for operational service metrics. Ordinary dataset queries must
not claim exactly-once or source completeness from ClickHouse counts.

## Alternatives and boundaries

A bespoke map and API could avoid the plugin, but adds an authentication,
frontend, transport and operational component while fragmenting Grafana.
Prometheus is suitable for bounded operational metrics, not per-measurement
coordinates or long-term flight history. External tiles are convenient but may
leak the viewed area; require an explicitly reviewed local tile policy instead.
The plugin download and runtime are local only; no cloud or remote publication.

Use separate test data and credentials for verification. Reconcile selected real
rows and identities with the file without printing private values. Record exact
commands, unsupported cases and rollback. Rollback stops only this profile; do
not delete old data or reset offsets. Preserve retained research source bytes.

## Local state extension, 2026-11-04

The five-item F09 state increment uses the same local
runtime and dependencies. A separate checksum/firmware/definition-bound profile
retains two native state streams in a fresh database, with full typed/raw
readback before SELECT grants. A read-time per-recording report and four
full-recording tables expose recorded flags, mode codes, counts and changes.
This extends the proposed research view without promoting it to accepted source
admission. No canonical contract, existing database, UTC mapping or processing
path is superseded. Flight phase/duration inference and state-to-GPS temporal
association remain deferred; the alternative of deriving them directly from
landed or armed flags lacks the required time/coverage evidence. Maintenance is
one small exact-file adapter and query set, with no added service or dependency.

## Native-time association extension, 2026-11-04

The subsequently authorized state-to-GPS association
uses a separate versioned reference table with past-only selection, an explicit
inclusive age limit and NULL unknowns. Native timestamps are independently
decoded from all selected original frames. Because dropout frames have no
timestamp, file-neighbor masks qualify the result without claiming physical loss
intervals. Nearest-in-time selection could choose future states; interpolation
would invent flag values; matching on receiver UTC would rely on an unaccepted
clock mapping. The selected rule keeps these assumptions visible. It adds one
small bounded original-frame projection and local query set, with no new
dependency or service. Earlier tables and measurement identities remain intact;
common-clock proof, physical phases and source completeness remain open.
