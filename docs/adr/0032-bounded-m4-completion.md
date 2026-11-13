# ADR-0032: Complete bounded M4 with archive replay and sealed report admission

**Status:** Accepted for the closed bounded local synthetic M4 profile,
2026-10-26, following the recorded acceptance.
This does not admit production.

## Problem and decision

The integrated run demonstrates source-to-query correctness but has no archive-only
serving replay or persistent trust input for a later report. A caller could run
the SQL companion without checking canonical events, or pass arbitrary expected
processing facts. Closing M4 needs a concrete finite recovery and query path.

Reuse the existing archive supervisor for Kafka-inaccessible reconstruction.
Recompute the declared terminal bounded-reference policy from freshly verified
observations, with no source-file or Kafka fallback. Publish into a caller-selected
isolated serving scope. Refuse a target equal to the original archive/source run
before any database write. Attest an existing original scope only through the
SELECT-only `seal-existing` command. Keep original measurement identities, archive descriptor
and original source/job/delivery lineage. Do not reproduce online dispositions
from archive order; this profile intentionally has no intermediate watermarks.

Persist a small `sealed-battery-run-v1` receipt containing exact expected canonical
event, observation-disposition and metric/window facts. The receipt is derived
from the verified archive and existing independent reference, never user-supplied
facts. Publish it only after all stored facts reconcile. Reuse existing immutable
conditional S3 creation in a separate receipt prefix and retain its SHA-256 as an
independent trust input. A report must freshly verify the receipt, archive and
all three ClickHouse tables before and after SQL, refusing any change or mismatch.

The supported scope is closed, finite and administrator-trusted. Writers stop
before admission. This is not a concurrent writer transaction, general run-lock
protocol or shared-deployment enforcement claim. The approved report CLI is the
product entry point; raw database access remains diagnostic and administrator-owned.

## Alternatives and maintenance

Inferring completeness from counts or unsealed table rows cannot detect omitted
or competing content. Trusting local trace files during recovery would fail the
archive-only boundary. Adding a continuous supervisor, transaction coordinator,
new SDK, database or Flink connector is unnecessary for this finite profile.
One scenario-specific module and CLI reuse the current projection, HTTP sink,
reference, S3 adapter and archive supervision. A receipt is the minimum retained
input needed to make future report admission explicit; it adds a versioned format
and focused integrity/admission tests, without changing canonical/archive formats.

## Acceptance and limits

Require Kafka-inaccessible S3-only reconstruction, exact isolated serving replay,
unchanged original target, changed-batch retry, missing/conflicting canonical and
processing-fact refusal, untrusted/incomplete receipt refusal, and fresh readback
after storage/serving replacement. Existing archive interruption, actual expiry,
checksum/coverage and sink lost-response evidence is reused with its original
scope and identity qualification. Review M4 criteria as a coherent increment.

Bounded-reference semantics satisfy M4's online-or-reference criterion. Positive
online-late integration belongs to the whole-slice M5 work; it is not silently
claimed by this reference replay. Production failure domains, retention/capacity,
alert response, shared TLS/authentication and AWS execution remain separate gates.

Rollback stops using the new receipt/report path. Preserve original tables,
archive roots, partial failures and named volumes. No historical data cleanup,
canonical migration, dependency installation, cloud action, commit or publication
is authorized by adopting this local profile. This record supersedes ADR-0028's
candidate-only local serving status only after its stated acceptance passes.
