# ADR-0011: Validate the current canonical battery boundary independently

**Status:** Implemented and locally validated for the authorized M1 reader
increment. Other versions and actual ULog source adoption remain unvalidated.

**Date:** 2026-10-20

## Problem and decision

Producer tests and exact run regeneration do not establish a consumer admission
boundary. Add a standard-library reader for schema `1.0.0` and the existing
`battery-v1` / `ulog-battery-v1` lineages before introducing transport clients.
This implements the ADR-0003 separation without changing or superseding its
identity/time semantics. Actual ULog source adoption remains proposed.

Validate required envelope/nested fields, identifiers, numeric types, canonical
units, declared clock/profile/privacy/delivery relationships, integer UTC mapping
and the documented positional event-ID recipe. Do not reuse native normalizers
as validators. Canonical signed current remains valid regardless of native
sentinels; a canonical reader cannot infer native sample availability, actual
producer attribution or source rights from an envelope.

Follow the existing compatibility contract: tolerate unknown optional fields,
omit them from the recognized typed projection, and normalize absent optional
payload measurements to null. Retain distinct opaque quality flags; do not
invent missing-value or connection flags. Require the declared fixed-anchor
flag. Unknown schema/normalization versions fail visibly rather than guessing
future semantics. Validate all JSON text/numbers, including ignored extensions.

Bound each UTF-8 event to 64 KiB. A local JSONL inspection command is limited to
64 MiB and 100,000 records; it reports only counts or safe errors and releases
no partial success. It does not verify source authenticity, detect conflicting
deliveries or replace exact job/source run verification.

## Alternatives, impact and rollback

Reusing producer normalization cannot validate independently received wire data.
Rejecting every unknown key contradicts existing optional-field compatibility.
A schema framework or registry adds a dependency without a current need, and
would still need separate identity/time relation checks. Keep one explicit,
typed and bounded implementation with no new runtime package/service.

Reuse published golden/producer scenarios for successful round trips. Add only
new consumer-boundary regressions for malformed JSON, invalid relations, tolerant
optional fields and bounded JSONL failure. Wire version and converter artifacts
remain unchanged. Rollback removes this reader/command and its CI scope; no
measurement migration or persisted-state deletion is required.
