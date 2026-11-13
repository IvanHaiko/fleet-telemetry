# ADR-0020: Bound local test data and use S3 for the final archive

**Status:** Accepted planning scope by the maintainer on 2026-10-22. The bounded
local topic profile is implemented and live-checked in the follow-up below;
archive implementation and cloud execution remain pending.

## Problem

Local tests will use data on the order of 10-50 GB at most. Designing their
runtime around hypothetical multi-terabyte capacity or a new Docker management
system adds work unrelated to the demonstrated workload. The retention incident
came from retaining required evidence in a one-hour Kafka test log for about
nine hours. The final archive destination is S3, as selected by the maintainer.

## Decision

Use 50 GiB as a conservative local planning ceiling for retained Kafka test log
data across a test profile's topics/partitions. This expresses the maintainer's
approximate upper range, not a requirement to generate that much data, a measured
workstation capacity or an enforced filesystem quota. Tiny fixtures remain the
default. Record exact bytes and units in each larger test. Account separately
for source files, local archive copies, checkpoints, restore output and overhead.

For new ordinary bounded fixture topics, plan explicit `cleanup.policy=delete`,
`retention.ms=-1` and `retention.bytes=-1` so elapsed wall time or a small byte
limit does not erase required test input. Admission must bound finite publication,
retries and cumulative retained data, and check actual free disk for all copies
plus a declared reserve. These settings do not impose the 50 GiB ceiling or
protect against full disk. Topic setup must verify the effective values.
Short-retention failure tests use separate disposable topics with explicit
settings. No historical topic, volume or current runtime setting changes here.

Use Amazon S3 as the final deployment's source and observation archive target.
Retain original bytes, checksums and observation coverage, and prove readback
and isolated replay after Kafka expiry under the existing archive contract.
A local S3-compatible test backend may support M4, but remains a candidate
requiring a reviewed distribution/client and compatibility evidence. Local
success does not establish actual S3 access, lifecycle or restore behavior.

Keep the current historical-profile quarantine. Do not add a Docker authorization
plugin, custom lifecycle service, extra broker cluster or tiered storage merely
to handle bounded local tests. Ordinary operator permissions and deliberate
historical-data preservation remain necessary. Production retention, disk and
archive monitoring will use measured workload values when that profile exists.

This supersedes only ADR-0002's unresolved final archive-provider choice and
ADR-0004's unresolved AWS archive-service choice. Local-first sequencing,
Compose/Terraform ownership and separate cloud execution authorization remain
intact. Other AWS services, region, budget and Terraform versions remain open.

## Alternatives, cost and maintenance

- Keep one-hour/64 MiB limits for ordinary reusable fixtures: rejected because
  required test evidence can expire between sessions.
- Increase retention arbitrarily: possible for a declared test duration, but
  adds an expiry deadline without a need in these finite ordinary fixtures.
- Unlimited input with unlimited retention: rejected; the data and disk budget
  must remain bounded even when automatic Kafka cleanup is disabled.
- Build a Docker policy platform now: disproportionate to this local scope.

The decision adds no package, service or present cloud spend. Local disk must
cover all simultaneous copies; the ceiling is not a disk reservation. Future
S3 storage, requests and restore transfer require a workload-specific estimate
and an approved lifecycle before resource creation. No price is assumed here.

## Acceptance and rollback

Before adopting the ordinary fixture profile, prove effective topic settings,
refusal when its retained-data/disk budget is insufficient and preservation
across the intended stopped interval. Reuse tiny existing inputs. Archive
acceptance still requires independent readback, expired-offset refusal and
rebuild into a new run; a selected S3 target does not close production reliability.

This is documentation only; rollback requires no storage migration. A later
runtime change must preserve old evidence and supply its own rollback procedure.
Changing the final archive target requires a linked superseding decision.

## Related documents

### Authorized local implementation follow-up, 2026-10-22

The [fixture profile](../guides/local-kafka-fixture-profile.md) implements fresh-topic
overrides, effective-value readback and pre-publication storage admission in the
two maintained creators. It checks allocated volume bytes and broker/workspace
free space with explicit tiny-fixture allowances. This single-publisher guard
is not a quota or proof of 50 GiB capacity. Existing topics and image/broker
defaults remain unchanged.

A fresh broker verified consumer recovery, producer retry, intentional expiry
and refusal, and old transport timestamps surviving cleanup/restart. It finished
stopped; both historical profiles stayed unchanged and stopped. This supplements
the planning decision without closing S3/rebuild or production gates. The
original historical preservation failure remains failed.

[Archive contract](../reference/archive-recovery-contract.md),
[deployment](../deployment-and-terraform.md),
[production gate](../guides/production-recovery-gate.md),
[ADR-0002](0002-archive-and-serving.md),
[ADR-0004](0004-local-first-and-terraform.md).
