# ADR-0005: Define the first synthetic native battery mapping

**Status:** Accepted by the maintainer for the first synthetic M1 slice.

**Date:** 2026-10-19

## Context

The first M1 slice needs a pure function that maps one synthetic native record
to the existing canonical battery envelope, or returns an explicit rejection.
The canonical contract specifies output units and clock conversion, but does
not define native fields, native current sign, or native sentinel values.
Choosing those rules implicitly in code would make the tests certify an
undocumented interpretation.

## Decision

Define a synthetic-only native record format named `synthetic-battery-native-v1`.
This format makes no claim about PX4 fields or ULog compatibility. Bind its
first normalization to `battery-v1`; no previously implemented mapping exists.
Use the existing `1.0.0` envelope and `event-id-v1` recipe unchanged.

| Native field | Type and validity | Canonical mapping |
| --- | --- | --- |
| `source_record_index` | Required integer in `[0, 9007199254740991]` | Preserve the original stream ordinal, including positions of rejected records |
| `timestamp_us` | Required nonnegative integer in `[0, 9007199254740991]` | Boot-relative physical measurement time; `timestamp_kind: measurement` |
| `voltage_mv` | Required nonnegative integer | `voltage_v = voltage_mv / 1000` |
| `current_ma` | Optional signed integer or null; positive is discharge and negative is charging | `current_a = current_ma / 1000`; no numeric sentinel |
| `remaining_pct` | Optional integer in `[0, 100]`, null, or sentinel `-1` | `remaining_fraction = remaining_pct / 100`; sentinel becomes null |

Reject booleans, numeric strings, non-finite numbers, and non-integer values
in these integer fields. Missing or null optional values become explicit null.
Emit `source_value_missing` when either optional measurement becomes null.
Zero is a valid measurement. A missing, null, or invalid required field is a
rejection. Reject remaining percentages outside the stated range except for
the explicit `-1` sentinel; never clip values.

Use the existing fixed synthetic clock anchor and integer-microsecond
conversion. The source manifest declares inclusive native timestamp bounds for
one session; reject records outside those bounds. A missing anchor, invalid
UTC string, leap second, or UTC conversion overflow is a rejection. Ingestion
time is supplied by the caller and never determines source time or identity.
Emit `synthetic_time_anchor` and use delivery mode `synthetic`.

The fixture specification must contain the format/generator version, explicit
seed, scenario, and literal records. Hash its exact bytes under the existing
synthetic identity rules. Its checksum is independent of the illustrative
contract vector, which remains a separate golden identity test. Do not assign
the illustrative checksum to different fixture bytes.

The pure function performs no I/O, clock reads, filtering, or ordinal allocation.
Its rejection result identifies the reason and available source position
without echoing the raw record. This decision does not introduce another wire
envelope or change the existing rejection-envelope proposal.

## Alternatives considered

- **Synthetic fields already in volts, amperes, and fractions:** less conversion
  logic, but provides weaker evidence for unit conversion in the first slice.
- **A PX4-shaped native record:** closer to a future adapter, but requires a
  separately reviewed source message/version, sign convention, timestamps,
  and sentinel definitions before claiming that mapping.

## Consequences and acceptance

This adds no runtime service or production dependency. Maintenance is limited
to a small synthetic format and its tests; actual ULog mapping remains a
separate reviewed task. A future correction to accepted mapping behavior must
use a new normalization version and separate lineage.

The data contract owns the accepted mapping. The implementation must demonstrate
the published identity vector, independently specified golden output, stable
semantic content across delivery runs, both current signs, unit conversion,
null/sentinel handling, invalid timestamps and required fields, and preserved
native ordinals when rejected records are filtered by a caller.

## Related documents

[Canonical contracts](../data-contracts.md), [canonical boundary ADR](0003-canonical-events.md),
[M1 roadmap](../roadmap.md), [testing strategy](../testing-strategy.md).
