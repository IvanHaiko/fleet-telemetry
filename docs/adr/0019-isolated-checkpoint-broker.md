# ADR-0019: Isolated Kafka storage for checkpoint experiments

**Status:** Scoped local experiment under the maintainer's 2026-10-21 M3
continuation authorization; persistent runtime adoption and M3 acceptance remain
open. This record does not relabel the earlier failed preservation attempt.

## Problem and observed incident

The existing Kafka probe has one-hour retention and a ten-second retention
check interval. Starting its stopped shared broker for a later experiment can
expire old records even when that experiment never publishes to their topics.
During checkpoint cycle 003, broker logs show time-retention deletion of the
offset-zero segment in four historical synthetic topics. Their earlier receipts
remain valid historical observations, but those records cannot be described as
currently retained. Cycle 004's interval guard failed before its job started.

The original broker is stopped. A read-only `docker cp` archive preserves its
current post-expiry data, explicitly not a pre-expiry backup. Source events,
prior successful/failed receipts, checkpoint evidence and deletion logs are
retained separately. No old topic is republished and no offset is reset to
manufacture preservation. The original shared-broker preservation check failed.

## Experiment boundary and alternatives

Use `compose/checkpoint.yml` with project `fleet-m3-checkpoint`, a separate
`fleet-m3-checkpoint_kafka-data` volume and a different declared cluster ID.
Reuse the existing Kafka 4.4.0 image, verify its expected locally recorded image
ID before use, and start with `--no-build --pull never`. The existing shared
broker must remain stopped. Both profiles publish only loopback port 19092;
they cannot run concurrently. Retain the isolated broker stopped after checks.

The new nine-record test topic has an explicit seven-day retention setting.
This is a finite experiment horizon, not archival durability. The first recovery
job remains a transient embedded PyFlink MiniCluster with native filesystem
checkpoints; no persistent Flink service/image is introduced here.

Alternatives:

- Continue using shared storage: rejected because ordinary broker retention
  can mutate unrelated historical evidence during a long test.
- Change every old topic's retention: rejected because it changes independent
  test settings and does not recover already expired records.
- Restore or republish the expired source: rejected as preservation evidence;
  it would create a new observation history and could change offsets/UUIDs.
- Introduce a different broker or hosted cluster: unnecessary dependency,
  maintenance and deployment scope for a nine-record local test.

## Cost, ownership and rollback

Compose owns the additional container, network and named volume. Reuse the
existing 1,536 MiB container limit, two-CPU bound and loopback security boundary.
Only one broker runs at a time; one additional stopped volume/container remains
for evidence. Native checkpoint/diagnostic storage is separate from both broker
volumes. No cloud cost, package installation or new broker distribution follows.
Resource peaks and shared deployment/TLS behavior are not measured here.

Rollback stops only the isolated project and restores its scoped source/config
increment. Keep both broker volumes and all receipts; deleting storage requires
separate explicit authorization. The post-expiry backup cannot restore the
expired pre-incident history. Future reuse of any stopped Kafka profile must
account for retention before startup and use isolated storage for new work.

## Root-cause and local quarantine follow-up, 2026-10-22

The [incident investigation](../case-studies/kafka-retention-incident.md) reconciles deletion
logs with topic overrides and record ages near nine hours against one-hour
retention. Post-start checking detected loss rather than preventing it. Legacy
Desktop matrix/restart entry points now refuse before process launch. Direct
Docker/ad hoc paths are not sandboxed by this gate and remain outside authorization
for the old volume. No retention setting or broker bytes changed; no broker started.

Seven-day experiment retention remains finite. Production requires workload-based
time/size budgets, independent archive/readback and expired-offset rebuild,
recovery preflight and an exercised response before the remaining margin expires.
These are required evidence, not adoption of a new service or production acceptance.
