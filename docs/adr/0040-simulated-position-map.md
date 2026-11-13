# ADR-0040: Bounded simulator position map

**Status:** Proposed. The local simulator experiment is authorized; real
vehicle adoption, external deployment and canonical position admission remain open.

## Problem and decision

Show the latest position of a small simulated fleet on a map while retaining the
separation between the simulator, Kafka, Flink and the browser. Existing Battery
events and their checkpoint state cannot carry positions without a new contract.
Use a separate, explicitly simulation-only position stream, fresh Kafka topics
and an isolated Flink job. The result is an ephemeral operational view, not a
durable canonical measurement or evidence of real-flight connectivity.

Use the maintained `pymavlink` 2.4.50 client to decode PX4 MAVLink, and Leaflet
1.9.4 to render the map. GPS validity, units, source boot time, system identity,
monotonic freshness, duplicates and missing data remain explicit. No source time
is replaced with arrival time. Do not accept real-device traffic or claim
cross-restart identity, exact delivery, recovery or flight control in this scope.

## Alternatives and cost

A custom MAVLink decoder would add protocol and checksum maintenance; a full
ground station or another service would expand the footprint. A text coordinate
list would not satisfy the requested map. Pymavlink is an optional pinned
dependency with LGPL licensing and transitive dependencies. Leaflet is a pinned
browser dependency; map tiles require network availability and disclose viewed
map areas to the selected provider. Keep the demonstration to simulated
coordinates and visible attribution. These additions require version and security
maintenance; they do not establish a production tile or real-device policy.

## Verification and rollback

Validate invalid/unknown coordinates, source time ordering, duplicated data,
staleness, bounded fleet size and the actual simulator-to-Flink-to-map path.
Use separate topics and state; never migrate or reset historical scopes. Rollback
stops only the experiment and removes its optional source code/dependency from
a future deployment; retain its observed evidence and do not delete data.
