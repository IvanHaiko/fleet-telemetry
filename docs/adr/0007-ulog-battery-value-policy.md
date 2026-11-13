# ADR-0007: Propose explicit ULog current and disconnected-record rules

**Status:** Proposed for the reviewed primary firmware/library path only.
The authorized pure value-policy slice is implemented and tested on authored
synthetic records; actual `ulog-battery-v1` source adoption remains proposed.
No accepted ADR is superseded.

**Date:** 2026-10-19

## Context and evidence

The discovery review found no charging or
disconnected battery records in two logs. Observations alone therefore cannot
define these cases. In firmware `8583f1da30b63154d6ba0bc187d86135dfe33cf9`,
the [message definition](https://github.com/PX4/PX4-Autopilot/blob/8583f1da30b63154d6ba0bc187d86135dfe33cf9/msg/battery_status.msg)
reserves unfiltered current `-1` and voltage `0` for unknown values.
The [battery library](https://github.com/PX4/PX4-Autopilot/blob/8583f1da30b63154d6ba0bc187d86135dfe33cf9/src/lib/battery/battery.cpp)
excludes negative current from discharge integration. Reset initializes unknown
voltage/current and a false connection state; the update path may subsequently
report values and the supplied connection state. Thus `connected=false` alone
does not determine whether a particular voltage/current is known.

Matching a source enum in a log does not uniquely attribute it to that library.
This proposal is scoped to the reviewed library/power-module path, not every
producer in that firmware, other firmware or ULog in general. It establishes no
native charging semantics.

## Proposal

The [data contract](../data-contracts.md#primary-firmware-value-policy-proposed)
owns the complete proposed input/disposition rules. Preserve nonnegative
unfiltered current in amperes, map exact native sentinel `-1` to null, and reject
other negative current rather than infer charging or silently discard a value.
The latter is a conservative project admission policy inferred from incomplete
native semantics, not an upstream declaration that every negative value is a
sentinel. Canonical sign remains positive discharge and negative charging;
this profile has no supported native charging representation.

Preserve an otherwise valid disconnected record with a quality flag. Do not
overwrite valid native values solely because it is disconnected. Unknown or
invalid required voltage still rejects; a quality flag cannot repair it.

Use manually authored native-shaped synthetic cases and separately authored
expected dispositions, without copying flight-log measurements. Their JSON
format describes review cases and partial expected results, not a ULog file,
wire envelope, registered source manifest or implemented adapter. No event IDs
or schema-compatibility claims are fabricated.

## Alternatives and impact

- Treating every negative current as charging would misinterpret native `-1`.
- Turning every negative current into null would hide undocumented invalid
  values instead of exposing a reason for review.
- Dropping all disconnected records would lose source evidence even when their
  required measurements are valid. Admitting unknown voltage as measured zero
  would instead violate the required-value meaning.
- Changing canonical voltage to nullable would expand the shared contract and
  require a separately reviewed version/migration, without evidence that this
  task needs it.

No framework, dependency, service or cloud resource is introduced. Maintenance
is limited to the proposed rule table, small synthetic cases and their future
adapter assertions. The implemented synthetic `battery-v1` mapping, schema
`1.0.0` and its native current sign rules remain unchanged.

## Acceptance, limitations and rollback

### Execution update — 2026-10-19

The maintainer authorized the bounded pure mapping after reviewing this proposal.
[`normalize_ulog_battery`](../../fleet_telemetry.py) now executes the previously
authored cases with wire schema `1.0.0`, a separate normalization lineage and
`ulog-battery-semantic-v1`. [Unit/contract tests](../../tests/test_ulog_normalization.py)
assert the independent value expectations and identities on synthetic examples.
This authorizes the experiment and its value rules; it does not establish real
producer attribution, binary parsing, rights or general reader compatibility.
The implementation guide records exact boundaries.

The authored outcomes now have pure-function assertions, not passing binary
ULog adapter tests. Before source adoption, review the producer scope, prove
runtime attribution or explicitly constrain supported inputs, and execute the
cases across the separately scoped parser boundary. Remaining parser,
compatibility, clock, identity, rights and privacy gates still apply.

No persistent canonical data needs migration or rollback. Revise this proposed
record and fixture version while unaccepted; after acceptance, changed mapping
semantics need a new normalization version and isolated lineage.

## Related documents

[Discovery tooling ADR](0006-ulog-discovery-tooling.md),
[testing strategy](../testing-strategy.md), [roadmap](../roadmap.md).
