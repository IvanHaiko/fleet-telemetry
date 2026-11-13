# Canonical telemetry contracts

## Local battery demonstration projection, 2026-11-11

The [one-machine starter](local-development.md) emits
`local-battery-projection-v1` in its dedicated output topic. It retains the exact
original canonical event as `raw_event`, together with the original `event_id`,
`vehicle_id`, `source_timestamp` and voltage/current/remaining values. Its
`dataset_run_id` comes from delivery metadata; changing that run never changes
measurement identity. `source_partition` and `source_offset` describe the input
observation, not a new measurement identity.

`power_w` is instantaneous `voltage_v * current_a` in watts. A missing current
produces an unknown power value; negative current retains its sign. No energy,
window aggregate, physical UTC or current vehicle freshness is inferred. Kafka
output is at least once, so repeated measurements can have multiple physical
observations. The verifier requires current-run content equality rather than
assuming output count equals unique measurement count.

This separate demo projection does not alter canonical Battery versions or
provide general JSON/source admission. Its producer uses the existing reviewed
synthetic converter and reader; the SQL job itself is not an arbitrary-input
validator. Full archival/serving and recovery contracts remain unchanged.

## Bounded F09 stream research profiles, 2026-11-10

[ADR-0049](adr/0049-bounded-f09-stream-events.md) and the
[stream guide](guides/f09-stream-replay.md#event-and-context-semantics) define the
implemented offline `f09-recording-event-v1`, `f09-recording-context-v1` and
`f09-recording-fact-v1` profiles. They retain original GPS/battery/state IDs,
ordinals, units and native boot microseconds; outer delivery runs do not change
measurement identity. Context records interval predecessors and distinct quality
masks. Facts retain input-event hashes and complete research inspection values,
including NULL references/ages for unknown associations. These are separate
research profiles; canonical battery semantics, physical clock admission and
broker delivery contracts remain unchanged.

## Preserved evidence and future reuse, 2026-11-10

[ADR-0048](adr/0048-integrated-mvp-and-evidence-preservation.md) requires reusable
source/run evidence alongside the [integrated MVP](architecture.md#integrated-local-mvp-target-2026-11-10).
This is a preservation requirement, not a new wire envelope or permission to
reinterpret the existing Battery, position or research contracts.

Preserve the complete original ULog with its checksum, provenance, firmware and
embedded stream definitions, including streams the current online path does not
interpret. For live input, identify the actual captured message/stream set,
capture interval, sampling/filter policy, native framing/bytes and observed gaps.
Uncaptured data is unavailable; later normalization must not invent it. Raw
retention is distinct from schema/producer/clock admission.

Retained source records keep original stream/instance and ordinals; filtering
does not renumber them. Measurement identity survives replay; cluster/topic UUID,
partition/offset and delivery run identify observations and executions separately.
Original byte identity, normalized semantic identity and a derived association
are different links. Retain schema, parser, mapping, calculation and association
versions, including the policy that produced an unknown value or rejection.

Native measurement/publication time, receipt time and processing/SQL observation
time remain distinct. Record the clock basis, synthetic anchors, reset/wrap
uncertainty and any measured cross-host clock bound. Pacing a historical log at
1x does not turn its measurement times into current physical UTC. A future
GPS/battery/state stream contract must preserve these distinctions and define
its own missing/late/conflict behavior before integration; optional fields must
not silently change the established identity recipe or required semantics.

Keep rejected, malformed, duplicate and late evidence with original references
and explicit dispositions. Preserve known quality/dropout masks separately from
an inferred count of lost measurements. Derived values reference the contributing
measurements, calculation version, native interval and coverage/uncertainty;
derived aggregates never replace their source evidence.

Retain scenario commands/timing and their intended faults as experiment metadata,
separately from observed failures or source annotations. An operator pause is not
a physical radio-loss label; an unavailable metric or absent stream is not zero.
Future analyses can build reviewed derivatives from these records without
rewriting originals. [Storage/retention ownership](deployment-and-terraform.md#run-evidence-and-retention-policy-2026-11-10)
and [evidence checks](testing-strategy.md#integrated-mvp-evidence-2026-11-10)
govern how those links remain usable.

The [live Grafana projection](guides/continuous-position.md#live-grafana-screen) adds no
wire or identity fields. Numeric boot seconds remain the position chart axis;
current status/values come from `position_stream.live_state`, history from the
deduplicated position view. The five-second display refresh does not change the
three-second SQL receipt expiry. Missing status snapshots never renew health.

The [continuous position projection](guides/continuous-position.md#current-sql-state-and-time-meaning)
keeps those position input/fact versions and identity recipe. Its explicit
offset budget does not change the default short-profile guard. SQL receipt
health is separate from native measurement time: `fresh`, `stale`, `unknown`
and `catching_up` classify current availability, with NULL current values outside
fresh state. Replayed historical measurements do not renew the selected source
receipt. No health timestamp establishes physical sample UTC or clock alignment.

The separate [live position source-to-query contract](guides/live-position-source-query.md#contract-and-calculation)
uses `px4-live-position-input-v1` and `px4-live-position-fact-v1`, outside canonical
Battery. It preserves the existing declared-boot/system/component/native-ms
identity and selected original integers; Flink converts explicit units and
retains input byte hashes and source coordinates. No measurement UTC is invented.
Full retained packets and Kafka observations bind to the archive plan. SQL
deduplication follows conflict/content reconciliation, not arbitrary last-writer
selection. These profiles do not alter historical schemas or checkpoint lineage.

The separate [live PX4 observational profile](guides/live-px4-mavlink.md#fields-clocks-and-missing-values)
defines `px4-mavlink-live-view-v1` outside the canonical battery envelope.
Position uses exact caller-declared boot-session/source/native-ms identity and
retains a boot timestamp without claiming physical sample/publication semantics.
GPS raw microseconds are retained as a decimal string with unverified clock
basis. Heartbeat/SYS_STATUS receive NULL measurement time and identity. Receipt
age is separate from source time and heartbeat presence. Sentinels remain NULL;
repeated native positions do not renew freshness. No historical contract or
checkpoint schema changes; unsigned-wire replay and physical boot proof remain open.

The [second recording and shared projection](guides/two-recording-view.md#shared-storage-and-interface)
add `f01-recording-inspection-v1`, source-bound `f01-state-research-v1` identities
and `recording-view-v1`. F01 observations are commander records with native time;
GPS is NULL/`empty_stream`, battery is NULL/`missing_stream`. Recording identity
binds source checksum, inspection profile and age policy. Existing F09 identity
recipes and association semantics remain unchanged. Shared Float64 projections
retain raw JSON and require full typed readback; they do not change canonical
battery contracts, define exact-decimal aggregates or prove physical time alignment.

The separate [combined recording inspection](guides/recording-connection.md#data-meaning-and-bounds)
uses `f09-recording-inspection-v1` outside the canonical envelope. It preserves
GPS identities and each battery/state association's own status, reference, age
and values. Non-matched references/ages/values are NULL; matched fields may also
be unavailable. No common "healthy" state or physical synchronization is inferred.
Existing measurement identities, units and association versions are unchanged.

## Status and ownership

This is the proposed wire contract with documentation clarification `1.0.1`, dated 2026-10-19. The clarification preserves the existing `measurement` and `publication` timestamp meanings; it adds no required fields or changed wire semantics. Both pure normalization functions emit `schema_version: 1.0.0`: the accepted synthetic mapping and an experimental bounded ULog value mapping tested on authored synthetic cases. Actual ULog source adoption and old/new producer-reader compatibility remain unvalidated. Neither function validates arbitrary envelopes or parses a binary log. The envelope is independent of flight protocols; event-specific payloads retain explicit meanings.

The contract owns measurement identity, timestamps, units, missing values, provenance and compatibility. Transport offsets, Flink state and database schemas must preserve those meanings rather than redefine them. A separate [bounded local converter](guides/bounded-conversion.md) now connects verified file bytes to these functions and reconciled outputs; it does not change the wire contract or prove real-source adoption.

## Envelope

Use UTF-8 JSON, one event per Kafka value. Initial contract identifiers use printable ASCII; textual descriptions may use UTF-8. JSON numbers must be finite. NaN, Infinity, duplicate object keys and numeric strings in numeric fields are invalid. Do not serialize executable objects or native binary formats in the envelope.

| Field | Proposed type | Requirement and meaning |
| --- | --- | --- |
| `event_id` | String, `sha256:` plus 64 lowercase hex characters | Required; deterministic measurement identity defined below |
| `vehicle_id` | Nonempty string | Required; pseudonymous identity from a versioned mapping; stable within the dataset |
| `event_type` | String | Required; initially `telemetry.battery`; future types get documented payload contracts |
| `schema_version` | Semantic version string | Required; initially `1.0.0` |
| `source_timestamp` | UTC RFC 3339 string | Required for admitted telemetry; exactly six fractional digits and `Z` |
| `ingest_timestamp` | UTC RFC 3339 string | Required; first adapter admission time in the current delivery run |
| `source_log_id` | Content checksum string | Required for file/synthetic sources; SHA-256 of exact source bytes |
| `source_type` | String | Required; initially `ulog` or `synthetic`; new values require a contract review |
| `source_stream` | Nonempty string | Required; native message name and instance, such as `battery_status:0` |
| `source_record_index` | Nonnegative integer | Required; zero-based ordinal within that stream, including rejected records |
| `normalization_version` | String | Required; mapping/clock version: `battery-v1` for accepted synthetic inputs; `ulog-battery-v1` for the bounded experimental ULog profile |
| `source_time` | Object | Required; native clock value, basis, anchor and precision metadata |
| `provenance` | Object | Required; source manifest ID and privacy classification |
| `quality_flags` | Array of distinct strings | Required; empty when no documented condition applies |
| `payload` | Object | Required; shape depends on `event_type` |
| `delivery` | Object | Required; `dataset_run_id` and `replay_mode` (`historical` or `synthetic` initially) |

`source_record_index` must not be renumbered after filtering. A record that expands into multiple canonical events needs distinct documented event types or a new identity recipe with a child index. Do not improvise identity suffixes.

`provenance.source_manifest_id` resolves to a manifest containing exact input checksum, origin URL or fixture specification, retrieval time, license / permission evidence, parser and mapping versions, vehicle pseudonym mapping version, privacy review and any derivative lineage. Keep sensitive origin details in a restricted manifest. No external URL is required in a public event.

`delivery.dataset_run_id` is a unique identifier for an isolated dataset build, not a measurement identity. Preserve it through checkpoint recovery and sink retries. A deliberate rebuild uses a new run ID. `pipeline_version`, configuration hash and environment versions belong to the run manifest and derived rows.

## Bounded local job and run artifacts

The implemented file boundary uses `job_version: bounded-conversion-v1` and
`run_manifest_version: bounded-run-v1`, independently of event wire version
`1.0.0`. The [converter guide](guides/bounded-conversion.md#job-boundary) specifies the
strict job shape, bounds and typed manifest fields; its
[artifact contract](guides/bounded-conversion.md#artifacts-and-reconciliation) defines
JSONL ordering, rejection references, count equations, hashes and publication.
These local rejection references do not adopt the proposed transport rejection
envelope below. Input-level failure produces no run artifacts.

The ULog bridge binds `field_definition_reference` to the SHA-256 of the entire
embedded UTF-8 F-message body, including the name and delimiters, and requires
`parser_version: pyulog-1.2.2`. Its real-source firmware SHA must match embedded
`ver_sw`. Caller-supplied producer evidence remains an attestation rather than
automatically verified attribution. Binary-encoded authored fixtures retain
synthetic provenance. Measurement identity and timestamp meanings are unchanged.

New runs pin `pipeline_version: bounded-converter-v2`, job/source hashes,
mapping/parser/projection versions, data-file hashes and reconciliation counts.
`bounded-semantic-digest-v1` covers ordered event IDs plus the existing semantic
projection, excluding delivery metadata. A duplicate identity or conflicting
measurement fails the run. Both normalizers still emit `schema_version: 1.0.0`;
documentation clarification `1.0.1` proves no producer-reader compatibility.
Pipeline v2 adds bounded nested layouts and validated `M/L/S` frames under
[ADR-0010](adr/0010-ulog-nested-and-service-frames.md); existing v1 run artifacts
retain their original provenance. This changes supported file admission, not
the measurement projection, mapping version or identity recipe.

The [read-only verifier](guides/run-verification.md) regenerates all three expected
artifact files from the original job/source with the current pinned runtime.
Stored manifest hashes alone cannot rule out coordinated event/manifest edits.
Verification changes no artifact version; reformatted or old-environment runs
may fail exact comparison and require their recorded software. It supplies no
missing producer or source-rights evidence.

## Implemented canonical reader

[ADR-0011](adr/0011-bounded-canonical-battery-reader.md) and the
[reader guide](guides/canonical-reader.md) define `battery-envelope-reader-v1` for
schema `1.0.0` and the two current normalization lineages. It independently
validates required fields, canonical units, supported metadata relationships,
integer UTC mapping and positional identity. Other versions fail visibly.

Existing optional-field read compatibility is implemented without a wire-version
change: unknown optional object fields are ignored, absent optional payload
measurements become null and distinct opaque quality flags are retained. JSON
extensions must still be finite valid UTF-8; duplicate keys fail at every level.
Canonical signed current remains valid for both lineages. Native sentinels are
not applied again and missing-value flags are not invented.

Each event is bounded to 64 KiB. The JSONL command checks at most 64 MiB and
100,000 records, releasing counts only after complete success. Positional IDs
do not authenticate payloads; per-envelope admission does not establish source
completeness or rule out cross-delivery conflicts. Existing golden/current
producer roundtrips are checked; general released old/new versions remain open.

## Time semantics

The initial wire precision is one microsecond; greater source precision is retained in provenance before any deliberate rounding. Source clock precision and UTC-anchor accuracy are independent and must not be inferred from the six displayed digits.

| Clock observation | Meaning | Replay behavior |
| --- | --- | --- |
| Physical sample time | When the sensor measured a value; use a documented sample timestamp when available | Stable |
| Source publication time | When source software emitted a message; use only if no sample time exists and label it | Stable |
| Ingestion time | When the adapter first admitted the event in this delivery run | New for a new run; unchanged on a retry of the same serialized event |
| Processing time | When a processing operator handled it | Runtime observation, outside measurement identity |
| Sink visibility time | When an acknowledged write can be observed by the defined query | Measured separately, not assumed from enqueue time |

`source_timestamp` is required in every admitted event. It represents the
selected source time mapped to UTC: use physical sample time when available,
and source publication time only when no sample time exists. Preserve the
distinction in `source_time.timestamp_kind`; publication time must never be
presented as physical measurement time. A synthetic anchor changes the UTC
reference, not whether the native timestamp denotes measurement or publication.

PX4 ULog has microsecond timestamp fields; do not assume these are Unix timestamps. The [ULog format specification](https://docs.px4.io/main/en/dev_log/ulog_file_format) describes its representation. Each chosen message's field definition must be checked at M1.

For boot-relative sources, `source_time` records `clock_basis: boot_relative`, `native_timestamp_us`, `timestamp_kind: measurement` or `publication`, and a mapping with `native_anchor_us`, `utc_anchor`, `anchor_kind` and `anchor_uncertainty_us` (nullable if unknown). The proposed conversion is `utc_anchor + (native_timestamp_us - native_anchor_us)` using integer microseconds. Select the anchor once from a reviewed manifest; do not repeatedly anchor against changing GPS samples.

If reliable UTC is unavailable, an explicitly fixed synthetic anchor is allowed for historical experiments. Set `anchor_kind: synthetic_fixed`, use the `synthetic_time_anchor` quality flag and label the run as synthetic-time. A missing anchor is a rejection, not permission to use the host clock. Boot resets or clock discontinuities require separate sessions / source manifests. Do not merge incomparable epochs.

Flink timer and event-time APIs may operate at millisecond resolution. Preserve wire microseconds, specify floor-to-millisecond conversion for the M3 experiment, and test near-boundary samples. Never overwrite the original measurement timestamp with the reduced-precision runtime value. Reject leap-second strings for the initial subset and document that restriction.

## Deterministic identity

File-source identity uses native position, not timestamp or payload alone. Multiple measurements may legitimately have the same value and timestamp.

The proposed `event-id-v1` recipe hashes the UTF-8 bytes of a compact JSON array in this exact order:

```text
["event-id-v1", source_type, source_log_id, vehicle_id, source_stream,
 source_record_index, event_type, normalization_version]
```

The displayed line break is explanatory. The actual input has no whitespace outside strings, uses JSON escaping, and contains an integer record index without a decimal point. Use ASCII identifiers and lowercase source checksums. Prefix the lowercase SHA-256 digest with `sha256:`. The initial index range is `0` through `9007199254740991` to avoid cross-language JSON integer loss.

Exclude ingestion / processing time, run IDs, Kafka offsets, replay speed, random UUIDs, database IDs and software build timestamps. A transport retry republishes the same serialized event. A new replay run regenerates the same stable measurement projection with fresh delivery metadata.

A correction to units, coordinates, timestamp mapping, or vehicle mapping requires a new `normalization_version` and therefore new event IDs. Keep old and corrected datasets separate and record their lineage. Merely fixing packaging without changing mapping behavior does not require new measurement identities. Do not let both normalization versions contribute to the same analytical run.

For seeded synthetic inputs, hash the exact fixture specification bytes, including generator version, seed and scenario definition. Record generation order as the native stream ordinal. Live-source identity is deferred until an adapter defines durable device-session IDs and a restart-safe sequence; it must not reuse file-source assumptions.

## Duplicate and conflict behavior

An observation is a delivery instance. An event is a uniquely identified measurement. Several observations may reference the same event.

At M1, define a canonical semantic projection for each supported payload: vehicle, event type, source timestamp, source identifiers / position, normalization version, source-time interpretation, normalized payload and quality flags sorted lexically. Normalize optional fields to their declared null form. Exclude delivery metadata, ingestion time, retrieval metadata and serializer formatting. Pin the projection version in the run manifest. Compare typed normalized content rather than arbitrary JSON byte order or unrounded floating-point text.

Within a run, equal event ID and equal semantic projection is a duplicate. Equal event ID with different semantic content is an identity conflict: quarantine it, count it and invalidate release of that run. Neither last-write-wins nor arrival time resolves conflicting measurements. After streaming state expiry, bounded reconciliation still checks conflicts across the entire run.

The stream processor's deduplication horizon is bounded. Serving queries enforce uniqueness over the complete dataset run, and reconciliation detects copies outside the streaming horizon. Transport-level idempotence is an additional optimization, not the event identity policy.

## Initial battery payload

The first synthetic native mapping was accepted in
[ADR-0005](adr/0005-synthetic-battery-mapping.md). Its rules are defined below;
PX4 source field and sign review remains a separate gate.

| Field | Type | Units and interpretation |
| --- | --- | --- |
| `voltage_v` | Number | Required, finite and nonnegative, volts |
| `current_a` | Number or null | Amperes; positive means discharge, negative means charging; source sign mapping must be reviewed |
| `remaining_fraction` | Number or null | Inclusive range `[0, 1]`, never a percentage in `[0, 100]` |

Unknown optional measurements use explicit `null`, not zero, a sentinel, an empty string, or carry-forward values. Missing optional keys may be accepted on read and normalized to null; producers emit them explicitly. Required-field absence or invalid units is a rejection. Hardware-specific plausibility thresholds are quality checks with versioned configuration, not invented universal flight limits.

Proposed flags include `synthetic_time_anchor` and `source_value_missing`. A documented flag cannot make a required invalid field acceptable. Out-of-range remaining fraction is rejected rather than clipped.

### Synthetic native mapping: `synthetic-battery-native-v1`

This is a project-defined synthetic input, not a PX4 message definition.
Its mapping uses `normalization_version: battery-v1`, the existing envelope,
and the unchanged `event-id-v1` identity recipe.

| Native field | Accepted input | Mapping |
| --- | --- | --- |
| `source_record_index` | Required integer in `[0, 9007199254740991]` | Original stream ordinal, never renumbered after rejection |
| `timestamp_us` | Required integer in `[0, 9007199254740991]`, within inclusive manifest session bounds | Boot-relative physical measurement time; `timestamp_kind: measurement` |
| `voltage_mv` | Required nonnegative integer | Divide by 1000 to produce volts |
| `current_ma` | Optional signed integer or null | Divide by 1000; positive discharge, negative charging; no numeric sentinel |
| `remaining_pct` | Optional integer in `[0, 100]`, null, or sentinel `-1` | Divide by 100, or produce null for the sentinel |

Missing optional keys and explicit null both produce explicit null.
Emit `source_value_missing` if either optional measurement becomes null.
Zero remains valid. Reject booleans, numeric strings, floats (including integer
valued floats), non-finite numbers, invalid required values, and remaining
percentages outside the stated range except `-1`. A numeric conversion that
cannot produce a finite JSON number is rejected. Unknown optional native keys
are ignored; they do not extend the canonical payload.

The caller supplies the registered source manifest, its fixed `ClockAnchor`,
and `DeliveryMetadata`. The manifest records checksum, fixture specification,
retrieval time, rights evidence, parser and native-format versions, vehicle
mapping version and pseudonym, privacy review/classification, stream,
normalization version, inclusive session timestamp bounds, and the reviewed
clock anchor. The accepted in-memory types are defined in
[`fleet_telemetry.py`](../fleet_telemetry.py); a general manifest file reader is
outside this slice. Original synthetic data needs no derivative lineage.

The supplied anchor must equal the manifest anchor. Native anchor values use
the same integer range as native timestamps. Anchor uncertainty is null or a
nonnegative integer in that range. Apply the existing integer-microsecond
formula; native values before the anchor are allowed within session bounds.
Reject a missing or changed anchor, malformed UTC string, leap second, value
outside session bounds, or conversion outside UTC years 0001 through 9999.
The slice requires UTC strings with six fractional digits and `Z`, including
ingestion and manifest retrieval times. Ingestion time does not constrain
historical source time. Delivery mode and privacy classification are
`synthetic`; emit `synthetic_time_anchor`.

The function performs no I/O and does not allocate ordinals or read a clock.
The caller verifies exact fixture bytes against the registered checksum;
the unit fixture demonstrates this boundary. Separate source manifests are
required for clock resets. A stateless one-record function cannot detect a
reset across successive calls or prove a complete session was supplied.

The local rejection result contains a stable reason code, field, manifest ID,
stream, and native ordinal when valid. It is not a new serialized rejection
envelope. Validation proceeds through manifest, delivery, anchor, required
native keys, ordinal, timestamp, and battery values; the first invalid field
determines the local rejection. Codes are `invalid_manifest`,
`unsupported_schema`, `invalid_delivery`, `missing_time_anchor`,
`invalid_time_anchor`, `missing_required_field`, `invalid_record`,
`invalid_timestamp`, and `invalid_unit_value`. No raw values are echoed.

### Proposed ULog mapping: `ulog-battery-v1`

The 2026-10-27 real-source review registers a separate
IDF_DS research candidate by exact original checksum under CC BY 4.0. Its
`9a2a8d4d` firmware is outside this profile. Matching 39 declared battery fields
and observed GPS UTC pairs do not authorize reuse of the `8583f1da` producer
profile, identity lineage or synthetic anchor. Its native battery clock has no
sample timestamp; GPS offsets require `timestamp_time_relative` and an explicit
uncertainty policy before a real UTC mapping can be accepted. No contract or
normalization identifier changes in this review.

**Status: Proposed for actual source adoption; pure record mapping implemented
and tested on authored synthetic cases.** This profile is separate from the accepted synthetic
`battery-v1` mapping. Do not reuse synthetic native scaling or sentinel rules
for ULog. The local discovery review records two
parsed test logs and exact firmware sources; unresolved producer semantics and
compatibility checks still block acceptance. The candidate acceptance review
records the original format rejections. The format extension
now passes the primary source's structural/count boundary; this is insufficient
for real-source acceptance or producer attribution.

Before acceptance, record the selected firmware version/commit, exact message
definition and fields, parser/version, stream instances, native units, scaling,
sentinels and timestamp semantics with reviewable evidence. Confirm native
current semantics and map them to the common canonical sign: positive discharge,
negative charging. Native scaling and sentinel rules remain source-specific;
the canonical sign does not.

Select sample time when available. Use publication time only if no sample time
exists, with `timestamp_kind: publication`. Both require `source_timestamp`
under the existing clock rules. If reliable UTC is unavailable, explicitly
choose and record literal `native_anchor_us` and `utc_anchor` values once in the
reviewed manifest, with `anchor_kind: synthetic_fixed` and uncertainty metadata.
Emit `synthetic_time_anchor` and label the run synthetic-time. Do not choose an
anchor implicitly from host time or discovery execution time.

The proposed disconnected-record policy preserves a structurally valid native
record with `connected=false` as an admitted event carrying
`source_battery_disconnected`. Required canonical values must still be valid;
the flag cannot admit an invalid required voltage or timestamp. Confirm the
firmware's disconnected-value and sentinel semantics before accepting this
policy. This proposal adds no `connected` payload field to the current envelope
and does not change the implemented synthetic producer or its flags.

#### Primary firmware value policy (proposed)

[ADR-0007](adr/0007-ulog-battery-value-policy.md) proposes the following bounded
policy for the reviewed Battery library/power-module path at firmware commit
`8583f1da30b63154d6ba0bc187d86135dfe33cf9`. It is not a rule for all ULog
producers. A matching `source: 0` enum alone does not prove producer attribution;
that evidence remains required before accepting a supported input.
The pure mapping guide records the implemented
record/context boundary and its evidence; real producer adoption remains open.

| Native field | Proposed interpretation and outcome |
| --- | --- |
| `current_a` | Finite, nonnegative amperes are preserved without rescaling or sign inversion. Exact `-1` means unknown: emit null and `source_value_missing`. Reject every other negative value with `invalid_unit_value` on `current_a`. Numeric negative zero is zero. |
| `voltage_v` | Require a finite positive value in volts. Native `0` is unknown and rejects with `invalid_unit_value`, as do negatives. This source-specific sentinel rule does not change the canonical nonnegative voltage domain or the accepted synthetic mapping. |
| `remaining` | Preserve finite `[0, 1]` fractions. Exact `-1` becomes null and `source_value_missing`; reject other out-of-range values. |
| `connected` | Require a boolean at the validated record boundary. False adds `source_battery_disconnected` only to an otherwise admitted record; it neither nulls valid measurements nor permits invalid required values. |

The negative-current rejection is a conservative project policy: the reviewed
library excludes negative current from discharge integration, but does not
establish charging semantics. Do not equate every negative with the `-1`
sentinel. Canonical negative current still means charging; this proposed
profile has no verified native charging representation. Any later support for
such a representation needs explicit source evidence and normalization-lineage
review, with a new normalization version if accepted semantics change.

For the exact F09 checksum, proposed [ADR-0041](adr/0041-f09-battery-research-profile.md)
defines the separate `ulog-battery-f09-research-v1` lineage and unverified
producer profile. It applies these conservative value dispositions only for
restricted local research; source producer semantics remain unverified. The
same positional identity recipe includes this distinct normalization version.
The source publication clock uses an explicitly synthetic anchor; no real UTC
or general PX4 mapping is claimed. Execution evidence
records the seven rejected current values and two replay results.

At this proposed record boundary all selected native fields (`timestamp`,
`voltage_v`, `current_a`, `remaining`, `connected`, `source`) must exist. An absent
field produces `missing_required_field`. Canonical optionality does not make a
field absent from the selected native schema valid. Reject null, booleans,
strings and nonfinite values in the numeric battery fields with
`invalid_unit_value`; reject a nonboolean `connected` with `invalid_record`.
A parser bridge must convert the verified native bool representation to a
boolean using its embedded type, never generic truthiness. The bounded bridge
now enforces that conversion and rejects bool encodings outside 0/1. The pure
function checks manifest, delivery, anchor and external
ordinal first. It rejects declared sample-time availability or a native
`timestamp_sample` key instead of falling back to publication time. Then check
required keys in the listed
order, then validate timestamp, voltage, current, remaining, connection type
and source in that order; the first failure determines the proposed local
rejection field. Timestamp checks
retain the existing anchor/session rules. These codes specify local review
outcomes, not a new wire rejection envelope.

The [22 authored cases](../tests/fixtures/ulog-battery-policy-v1.json) and
[separate expected outcomes](../tests/fixtures/expected-ulog-battery-policy-v1.json)
exercise this proposal with literal synthetic values, including retained
ordinals, publication time under the fixed anchor, both sides of the current
sentinel, and valid/invalid disconnected records. There are nine proposed
admissions and thirteen rejections, now asserted against the pure mapping.
No flight values were copied or ULog binary generated. These expected partial results do
not extend `battery-semantic-v1`, select a producer schema version, or establish
compatibility. Synthetic continues to emit `1.0.0` unchanged.

The experimental function pins wire `1.0.0` and a separate
`ulog-battery-semantic-v1` projection with the same named measurement fields
listed below, retaining its ULog normalization and source-time interpretation.
It does not extend `battery-semantic-v1`. A registered manifest must retain
firmware/producer/field evidence, parser and vehicle-mapping versions and the
projection identifier. Real ULog inputs use source type `ulog`, restricted
privacy and historical delivery; ULog-shaped synthetic fixtures use source type,
privacy and delivery `synthetic`. Exact bytes/checksums and producer attribution
are caller responsibilities; no synthetic fixture is relabeled as a real log.

The isolated parser probe now demonstrates
Python 3.13 execution and explicit scalar conversion on the selected samples,
without adding a runtime bridge in that research step. Its truncated-tail and skipped-record cases
show that parser success/array row numbers are insufficient evidence of source
completeness or original ordinals. [ADR-0008](adr/0008-ulog-input-integrity-gate.md)
now records implemented validation of whole-input framing, registered bytes and parsed counts
before assigning ordinals or emitting canonical events. Clean-boundary loss
without trusted source expectations remains undetectable from framing alone.

#### Remaining ULog gates

A future local discovery result must identify exact source checksum and reviewed
rights/privacy evidence, firmware/message definitions, parser version, discovered
streams and fields, native record counts, timestamp ranges and discontinuities,
candidate field mappings, and unresolved questions. Record the explicit anchor
choice or missing-anchor blocker and references supporting time, sign, scaling,
sentinel and disconnected interpretations. Keep sensitive source details local
and restricted; do not echo raw payloads or coordinates. Discovery is evidence
for review, not acceptance of the mapping or a source of canonical events. No
discovery result or dataset was created by the documentation clarification;
the subsequent authorized experiment is recorded in the local discovery review.

Before implementation, pin the target schema and semantic projection and define
independent compatibility fixtures; demonstrate them before producer adoption.
Include each supported native current sign and invalid/sentinel negatives,
sample-time precedence, publication fallback, synthetic anchors, sentinels and
disconnected records. `battery-semantic-v1` below remains scoped to the synthetic
`1.0.0` payload. Mapping corrections after acceptance require a new normalization
version and isolated lineage under the existing evolution rules. The shared
canonical sign tests still require positive discharge and negative charging;
this source profile must not invent a charging case from a sentinel or invalid
native value.

### Battery semantic projection: `battery-semantic-v1`

The proposed serving spike copies existing golden
fixture identities/values into experimental tables. Its `semantic_json` stores
that golden fixture record, not the complete canonical semantic projection below.
Decimal(18,6) is an experimental SQL precision, not a new canonical numeric rule.
A reviewed projection/precision bridge and lineage reconciliation are required
before canonical sink admission. No canonical identity or mapping changes here.

The subsequent [pure projection interface](reference/serving-projection-interface.md)
under [ADR-0029](adr/0029-lossless-serving-projection.md) addresses that boundary
without altering canonical validity. Its exact6 profile refuses excess precision
or range instead of rounding. It normalizes numeric JSON spelling and flag order
for typed semantic equality, retaining original job/descriptor hashes and source
run separately from target scope. It does not migrate the earlier SQL schema;
the projection evidence owns its independent gate.

The [versioned event sink](reference/serving-sink-interface.md) stores that projection
with original job/run/descriptor lineage in a new table. It preserves exact
Decimal(18,6) scale through toDecimalString(column,6) readback; it neither rounds
canonical values nor changes identity. A different descriptor under the same
target event key conflicts, so differently sealed archives need isolated target
runs. The observed receipt is not a persisted completion seal or a window/late
disposition. Existing experimental tables are not migrated by this addition.

Compare typed values for exactly these envelope fields: `vehicle_id`,
`event_type`, `source_timestamp`, `source_log_id`, `source_type`,
`source_stream`, `source_record_index`, `normalization_version`, `source_time`,
`payload`, and lexically sorted `quality_flags`. Retain the complete nested
source-time mapping and the three payload fields, including explicit nulls.
Compare `event_id` separately. Exclude `schema_version`, provenance/retrieval
metadata, ingestion time, delivery metadata, and JSON formatting. This
projection is scoped to the supported `1.0.0` battery payload. The implemented
bounded run writer pins `battery-semantic-v1` for synthetic jobs and the separate
`ulog-battery-semantic-v1` for ULog jobs, as specified above.

### Illustrative event

This example is synthetic. Its source checksum is the SHA-256 of the UTF-8 string `synthetic-battery-fixture-v1` without a trailing newline; it is not a downloaded log. The event digest follows the identity recipe above. Index 42 represents a hypothetical record in that scenario.

```json
{
  "event_id": "sha256:720eb3715d64d401929ec27b6f11bbdb5cb3a7c53c1d6e619afd492fe8113714",
  "vehicle_id": "demo-vehicle-001",
  "event_type": "telemetry.battery",
  "schema_version": "1.0.0",
  "source_timestamp": "2026-01-01T12:00:01.234567Z",
  "ingest_timestamp": "2026-01-02T09:00:00.000000Z",
  "source_log_id": "sha256:f71b1ba9fda9c72427902180a4f964eec46949d721a0928c6de84971ff298b80",
  "source_type": "synthetic",
  "source_stream": "battery_status:0",
  "source_record_index": 42,
  "normalization_version": "battery-v1",
  "source_time": {
    "clock_basis": "boot_relative",
    "native_timestamp_us": 1234567,
    "timestamp_kind": "measurement",
    "mapping": {
      "native_anchor_us": 0,
      "utc_anchor": "2026-01-01T12:00:00.000000Z",
      "anchor_kind": "synthetic_fixed",
      "anchor_uncertainty_us": null
    }
  },
  "provenance": {
    "source_manifest_id": "synthetic-battery-manifest-v1",
    "privacy_classification": "synthetic"
  },
  "quality_flags": ["synthetic_time_anchor"],
  "payload": {
    "voltage_v": 15.8,
    "current_a": 4.2,
    "remaining_fraction": 0.72
  },
  "delivery": {
    "dataset_run_id": "demo-run-001",
    "replay_mode": "synthetic"
  }
}
```

### Finite processing facts, 2026-10-26

The integrated slice adds demonstration-only window
and observation-disposition tables alongside admitted canonical event facts.
Observation indexes refer to the exact archived partition-0 offsets; the archive
descriptor is content in every processing fact. Duplicate observations remain
visible without increasing measurement counts. Physical time, identity, units,
original delivery and source/job lineage remain unchanged. Only successful
terminal-reference execution with exact source-byte and rational reference
reconciliation admits those diagnostics as this fixture's serving facts. Their
zero late count is not evidence of positive online-late integration or a new
replay disposition policy.

### Sealed finite serving runs, 2026-10-26

[ADR-0032](adr/0032-bounded-m4-completion.md) adds `sealed-battery-run-v1`, a
separate completion receipt binding target run/version, archive descriptor,
terminal-reference policy and exact expected event/disposition/window facts.
Canonical JSON comparison preserves JSON types, including refusing booleans in
integer fields. The reference is recomputed from authenticated observations with
no intermediate watermarks; it does not infer online late decisions. Original
source/job/delivery lineage and physical measurement identities remain unchanged.
Replay refuses original archive/source target runs; SELECT-only attestation can
seal an already reconciled original scope without rewriting its rows.
Receipt objects live in a separate immutable prefix and use an independently
retained digest. This format does not change canonical or archive v1 semantics.
The M4 acceptance runbook defines the narrow profile and limits.

### Online reliability observations and finite source completion

The [M5 case](case-studies/m5-reliability.md) preserves native source order and physical time
while intentionally delaying Kafka delivery. Observation dispositions distinguish
within-horizon duplicates from expired repeats that become late. Serving event
facts retain first measurement eligibility; later late copies remain explicit
in the observation trace and do not add another window contribution. Native
units, optional nulls, full semantic content and deterministic IDs are unchanged.

[ADR-0033](adr/0033-finite-flink-source-coverage.md) changes no event or archive
format. It requires complete finite source coordinates and retained bounds for
command certification. `kafka_source_gap` is an operational refusal, not a
measurement rejection or permission to reset offsets. The Java connector may
commit progress before completion-stage refusal; use explicit isolated recovery
and reconciliation. Existing original topic-UUID trust and recreation rules
remain mandatory; offset checks do not migrate historical identities.

### Continuous local documents, 2026-10-27

The continuous runtime preserves canonical event
identity, measurement timestamps, payload units and source bytes. Its separate
`continuous-processing-v1` facts carry event disposition and source coordinates
or exact rational window sums; they are not finite terminal-reference facts.
`continuous-archive-plan-v1`, `continuous-archive-segment-v1` and
`continuous-archive-cursor-v1` bind immutable originals, contiguous per-partition
segments and durable progress. `continuous-serving-cursor-v1` binds output
progress. These formats do not replace sealed v1 catalogs/reports. The original
post-source lane mixing is corrected by eighteen isolated partition lanes
through canonical admission and watermark assignment. This fixed topology
changes neither physical measurement time nor late/window semantics. Late
delivery after actual idleness remains observable; it does not reopen windows.
The [local v3 state repair](case-studies/m6-identity-state-limit.md) keeps each partition's
watermark separate through deduplication and window state, then merges output
facts. Gate additionally requires the existing publisher's stable
`sha256(vehicle_id) % 18` partition ownership. A misplaced measurement emits an
invalid fact. Identity bytes, units, signatures and the 600-second horizon do
not change; expiry/late decisions now use the owning partition frontier rather
than an unrelated partition's minimum. Before-expiry duplicates and conflicts,
after-expiry late observations and unique window contributions are covered by
targeted tests. The processing topology uses fresh v3 UIDs; existing v2 state
cannot be silently discarded or reused. This is not an arbitrary per-vehicle
clock policy: vehicles sharing a partition retain its common two-second
out-of-orderness requirement.
The actual v3 preflight now checks duplicate-before-expiry and
late-after-expiry behavior after checkpoint restore with unequal partition
frontiers. Full-path window verification uses each vehicle's owning partition
frontier and refuses a vehicle observed in multiple partitions. This changes no
canonical identity, payload, delivery coordinate or persistent fact format.

## Future position payload conventions

The isolated experiment in [ADR-0040](adr/0040-simulated-position-map.md) uses
`simulated-position-v1`, which is not a canonical `telemetry.position` event.
Its exact fields are `format_version`, `source` (`px4-sitl`), `system_id`,
`boot_ms`, `latitude_e7`, `longitude_e7`, `altitude_msl_mm`,
`relative_altitude_mm`, and `fix_type`. Coordinates are WGS 84 degrees scaled
by 10,000,000; the two altitudes are millimetres above mean sea level and
relative to home respectively, as reported by the simulator. A current 3D GPS
fix is required. `boot_ms` is the source's unsigned 32-bit boot-relative time,
not UTC or an arrival timestamp. The view retains only a newer boot time per
system; source restarts and counter wrap require a fresh isolated run. Restored
records alone have unknown freshness. The local monotonic receipt age marks a
new observation stale after three seconds; it is not measurement latency.
This transient stream has no durable measurement identity, replay or real-device
admission guarantee. See the experiment record.

A future `telemetry.position` contract must specify WGS 84 latitude and longitude in decimal degrees, named altitude fields that distinguish metres above mean sea level from ellipsoid height and local-relative height, and an explicit validity indicator. Latitude is within `[-90, 90]`, longitude within `[-180, 180]`. Unknown position is null, never `(0, 0)` by convention.

Velocity components must name their frame, such as `velocity_north_m_s`, `velocity_east_m_s`, and `velocity_down_m_s` for NED. Do not combine ENU and NED vectors or use an ambiguous `altitude` / `speed` field. Attitude fields will need axis order, radians versus degrees, and quaternion conventions before admission. This section reserves meanings; M1 does not implement these payloads.

## Evolution and malformed data

Use semantic versions: additive optional fields without changed meaning can be minor releases, documentation clarifications can be patches, and changed required fields, types or units require a new major version. Major versions use separate canonical topics and an explicit migration. Within a major version, consumers tolerate unknown optional fields but reject unknown event types they cannot interpret; unsupported versions go to quarantine.

Compatibility must be demonstrated with old/new producer-reader fixtures. An optional addition that changes a calculation requires a new processing version and semantic projection review. Run-level configuration prevents mixing conflicting interpretations under one identity. A schema registry is deferred until code and compatibility needs justify it; documentation alone does not enforce compatibility.

Rejection records use a separate proposed envelope, so they can represent bytes that never formed valid telemetry:

| Rejection field | Meaning |
| --- | --- |
| `rejection_version`, `reason_code`, `stage` | Versioned rejection format and stable machine-readable reason |
| `observed_at`, `dataset_run_id` | Operational time and run context |
| `source_reference` | Restricted source manifest plus native stream/index, if known |
| `kafka_reference` | Topic, partition and offset, only when rejection occurred after admission |
| `raw_reference`, `raw_sha256` | Restricted object reference and checksum; no unrestricted payload echo |
| `event_id` | Optional; absent if identity could not be established |

Examples of reasons are `parse_error`, `unsupported_schema`, `missing_time_anchor`, `invalid_unit_value`, and `identity_conflict`. Preserve source evidence, prevent recursive rejection loops, and stop the affected input if neither a durable rejection path nor safe local evidence is available. Unknown schemas must not be silently coerced.

Late valid events are not malformed records. Their separate envelope preserves the canonical event plus watermark, affected window, pipeline version and late reason.

## Archive and rebuild identity boundary

The proposed [archive recovery contract](reference/archive-recovery-contract.md) preserves
transport observation identity separately from deterministic measurement
identity. An observation is keyed by original cluster ID, topic UUID, topic
name, partition and offset. A recreated topic with the same name has different
history. Repeated `event_id` values at different offsets remain separate archived
observations; overlapping batches at the same observation key must agree on
all original record content or fail with a conflict.

Preserve exact key/value bytes, null versus empty, ordered repeated headers,
Kafka timestamp/type and source/contract lineage. Transport time never replaces
physical `source_timestamp`; Kafka offsets and restore run IDs never enter the
measurement identity recipe. The proposed [archive v1 format](reference/archive-format-v1.md)
specifies JSONL/base64, strict null/empty/header preservation and immutable
coverage references. The [observation codec](reference/archive-codec-interface.md) now
implements strict encoding/decoding and finite offset union. Its non-null
measurement references are syntax only. The subsequent
[graph verifier](reference/archive-graph-interface.md) performs canonical admission and
resolves exact archived source/job provenance before sealing or reconstruction.
The codec alone cannot certify those links.
This increment changes no emitted canonical schema or measurement identity.

An isolated rebuild retains original observation coordinates as lineage and
publishes into a new run/namespace. Preserve archived original bytes even if
replay creates a new delivery envelope. Compare original byte hashes separately
from event identities and the pinned semantic projection; delivery changes do
not create a new physical measurement. Do not mix the rebuild with the original
run, reset missing Kafka offsets or claim reproduction of online watermark
decisions without the required arrival/watermark evidence.

## Privacy and public examples

The bounded runtime now preserves these observation and
lineage meanings through actual Kafka/S3 publication and Kafka-off reconstruction.
Its explicit non-transactional fixture flag is an operator attestation, not broker
proof of a topic's entire history. Rebuilt files retain original delivery bytes;
a fresh destination separates the rebuilt dataset. No schema, identity recipe,
unit, timestamp meaning or historical receipt is migrated. Protected descriptor
hashes remain independently supplied recovery inputs.

Coordinates, routes, serial numbers and operator identifiers may identify people or assets. Default demo data to synthetic records. Public-source availability does not imply redistribution permission. Review rights and privacy before storing a sample in Git or a release artifact.

Keep original source bytes restricted. Create a separately checksummed, explicitly versioned derivative for approved redaction or spatial transformation, with its own identity and lineage. Protect any reversible pseudonym mapping outside Git. Retention and deletion procedures must cover source files, observed events, manifests, serving rows and backups; archival immutability does not remove those responsibilities.

## Native topic identity compatibility, 2026-10-24

The [Windows UUID repair](case-studies/windows-kafka-uuid-repair.md) preserves the existing
complete 128-bit broker topic identity. It changes neither observation encoding
nor measurement/delivery identity semantics. Decode CLI URLsafe and SDK standard
base64 before comparing the same 16 bytes; alphabet differences are not lost
bits. A truncated historical UUID is not a compatible alternate representation.
The new SDK and guard do not rewrite or certify old receipts. Reuse requires
an independent audit/migration against trusted original broker evidence;
unknown high bits cannot be reconstructed from a narrowed value.

The bounded historical audit now supplies independently
observed full UUID candidates for 59 narrowed identities. Its correction map
is diagnostic only: no receipt schema, original UUID field, measurement identity
or offset is changed. Cluster IDs stay opaque strings; only topic UUIDs are
decoded as 16-byte values. A later append-only correction must bind original
file hashes, exact locations, trusted broker evidence and remaining continuity/
record-coverage limits before any identity-dependent reuse.


## Continuous Battery internal state v4

The managed-state optimization changes only Flink's
internal storage layout: one typed vehicle value contains identities, expiry
buckets, rational windows and count. Canonical identity/signature bytes, units,
physical time, delivery provenance, fact format, duplicate/conflict/late policy,
600-second horizon and 4096 retained-ID refusal are unchanged. V4 uses a new
state descriptor and battery UIDs; v3 checkpoints cannot be silently reused.
[ADR-0036](adr/0036-managed-vehicle-state.md) requires fresh isolated state or an
explicitly tested migration. Old state and source data are preserved for rollback.


## Operational live heartbeat boundary

The additive `live-heartbeat-v1` input and `live-link-state-v1` response are
operational contracts outside canonical measurement identity;
the exact fields and admission rules
are owned by the live receiver. Gateway receive time is distinct from physical
measurement time and historical ingestion time. Increasing gateway sequence,
receive-time freshness and a receiver-start epoch prevent ordinary stale/retry
observations from renewing connectivity. An authenticated trusted gateway must
never restamp replayed input. No measurement ID, normalization version, event
meaning, canonical wire format or stored fact changes.


## Flink live measurement projection

The live path reuses unchanged `continuous-processing-v1`
facts and adds an operational `flink-live-state-v1` API response. Eligible facts
can be visible before their processing checkpoint is durable and can repeat
after recovery. The bounded latest projection refuses competing equal-time
versions and ignores older/repeated versions without renewing freshness. Its
initial profile supports one-Hz source measurements; same-millisecond competing
measurements need a separate version policy. Physical measurement time, current
delivery admission time, live receive time and browser visibility are distinct.
Canonical identity, source bytes, 600-second deduplication and the 4096 guard
are unchanged. This projection is not a durable exactly-once analytical result.

The live interface follow-up adds optional
`live_age_seconds` and `admission_to_live_ms` to observed vehicle rows without
removing existing `flink-live-state-v1` fields. Missing/null means unknown.
Age uses the collector's monotonic clock only for a new eligible arrival at or
after its partition's captured startup frontier, and is null on unhealthy
collection or reconstruction. Delay compares admission and collector wall
clocks; negative differences are unknown and positive clock skew is not detected.
Neither value changes identity, measurement time, provenance or units, and
neither proves device connectivity or a bounded current Kafka backlog.

## Bounded Gold overview v1

The Gold overview derives its structural groups from recognized canonical events, retaining source type, normalization version and timestamp kind. Run and processing-fact version stay explicit. Disposition counts refer to output observations; quality flags and measurement counts use unique canonical identities. The result is an unreconciled observation, not a new canonical event, source-completeness assertion or cross-run aggregate. Unsupported event contracts refuse.

The separate [proposed synthetic position-file profile](adr/0042-experimental-position-gold.md) validates WGS 84 positions and synthetic source-publication time, with file-byte and per-system-ordinal identity. It is an experimental strict event shape, not canonical or real-device admission. Its normalization version binds the selected synthetic anchor.

## Restricted F09 GPS research view

The separate F09 state research profile
defines strict land-detector/commander rows, exact-file and original-stream
ordinal identity, unsigned boot-relative microseconds and explicit NULLs for
non-applicable fields. `f09-recording-state-gold-v1` reports record-weighted
counts and adjacent changes; its observed span is not flight duration. New
field meanings or shapes require a new research profile version. These rows
are outside the canonical battery envelope and do not admit a real device.

`f09-gps-state-association-v1`
is a derived research table keyed by original GPS ordinal and state stream in
an isolated fixed scope. It retains GPS ID, association version, state stream,
status, optional state ID/age in microseconds and explicit inclusive age bound.
Only the latest preceding native-time observation can be `matched`.
`before_first`, `recording_gap` and `stale` carry NULL ID/age; file-neighbor masks
use inclusive-start/exclusive-end bounds and are not physical loss intervals.
Native-time matching assumes a common boot clock. Parameter changes require a
separate reviewed materialization; no existing measurement identity, canonical
contract or battery association is changed.

The F09 flight view stores WGS 84 coordinates, MSL altitude, GPS ground speed, fix, native timestamps and receiver-reported GPS UTC under a separate checksum-bound research profile. GPS UTC is not promoted to a verified sample-time mapping; the original ordinal is retained. This does not amend the canonical event contract or accept arbitrary real devices.
