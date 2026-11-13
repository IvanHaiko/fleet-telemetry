# ADR-0024: Local M4 storage compatibility gate

**Status:** Accepted on 2026-10-23 for the bounded local synthetic byte-storage
profile following the maintainer's M4 continuation. This accepts the tested
SeaweedFS/SDK boundary only; it does not accept the archive worker, recovery,
serving layer, complete M4 milestone or production deployment.
It follows [ADR-0021](0021-bounded-archive-format.md) without changing its
conditional-create requirement or [ADR-0020](0020-bounded-tests-and-s3-archive.md).

## Problem and proposed experiment

The archive cannot safely publish immutable references until its actual S3
client/backend pair proves atomic conditional creation, byte readback,
authorization refusal and restart persistence. A tagged source implementation
is insufficient. Test that boundary before adding the archive worker.

Use the official SeaweedFS 4.48 Linux amd64 release at source commit
`530be3e37337488ecc34d58441e0bc476e121c93`. The release API advertises
`linux_amd64.tar.gz`, 46,067,365 bytes, SHA-256
`4a7d108384d044d95212d1342cdda9533fa55842c1c9b41f606ca3c8a9561124`.
Verify the downloaded archive and extracted executable before use; preserve
distribution metadata, license and Go module provenance. Record the actual
local image digest and build inputs before starting Compose. Never fetch a
floating image at startup.

Inspect the bundled `server` and `mini` command capabilities before selecting
the smallest single-process topology. Prefer disabling unused admin, worker,
WebDAV, IAM, Iceberg, Lance, metrics and telemetry surfaces. An administrative
listener required by the selected command must stay inaccessible outside its
private container network and be explicitly documented. Use a fresh named
volume, an internal network, loopback-only S3 publication, a read-only root
filesystem, bounded writable scratch, CPU and memory limits, and no privileged
capabilities. No historical broker or storage volume is started or mounted.

Use Boto3/botocore 1.43.117 on an isolated Python 3.13 interpreter. Resolve the
compatible complete transitive set and hash-lock every wheel before installing;
keep root project dependencies and the PyFlink environment unchanged. Use
explicit local endpoint, region and component credentials, SigV4, path-style
requests, no environment proxies, 2/5-second connect/read timeouts and one SDK
attempt. A single outer policy owns the bounded retries. A parent process owns
the whole-command deadline and shutdown, including a trickling response.

## Alternatives, security and cost

The archived MinIO community distribution remains unadopted. A filesystem fake
can establish adapter logic but cannot replace the live S3 gate. Immediate
Amazon S3 execution crosses the separate cloud authorization boundary. A new
maintained backend would require a linked decision and the same compatibility
checks. Do not repair a failing backend or emulate atomicity with HEAD/PUT.

The upstream advisory API was inspected on 2026-10-22. Its 25 published entries
declare affected ranges below 4.48; that is a dated upstream assessment, not a
complete vulnerability scan. In particular, the recent S3 identity injection,
POST authorization and SFTP issues end at 4.45 or earlier. Disable unused
surfaces and keep internal management endpoints unpublished regardless. Retain
the exact advisory response locally and reassess before a shared deployment.

This adds one local storage process/container plus a separately locked SDK.
Maintenance includes pinned binary/license/advisory review and repeatable
compatibility checks. No cloud charges arise. Budget downloads, executable,
image layers, four bounded data volumes, metadata, source/archive/restore copies
and scratch simultaneously; reserve at least 1 GiB after the estimate. This is
a tiny compatibility workload, not a 50 GiB capacity result or off-host backup.

## Acceptance and rollback

Use the current external restricted CLI workflow: public contract and
independent tests frozen before candidate exposure, observed access denials,
separate Implementer, read-only checks and separate read-only Reviewer.

Require byte-sensitive readback, bounded safe retry behavior, real conflicting
create races between two independent signed clients, credential denials and
fresh-process readback after container replacement with its volume retained.
Exactly one writer may win a conflicting create; the winner's bytes must not
change. Failure blocks backend adoption. Store readback, archive coverage and
source progress remain separate guarantees.

Retain stopped test services, volume and all failed evidence. Rollback stops
the new profile and removes only its use from the application; no automatic
object or volume deletion, migration, cloud operation or Git publication occurs.
Archive sealing/rebuild, actual Kafka expiry refusal and the ClickHouse gate
remain subsequent M4 work. Checkpoints retain the accepted filesystem profile.

Primary inputs: [release](https://github.com/seaweedfs/seaweedfs/releases/tag/4.48),
[license](https://github.com/seaweedfs/seaweedfs/blob/4.48/LICENSE),
[advisories](https://github.com/seaweedfs/seaweedfs/security/advisories),
[SDK metadata](https://pypi.org/pypi/boto3/1.43.117/json),
[S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html).

## Desktop networking finding

The first isolated profile used a Docker `internal: true` bridge. The installed
Desktop engine produced no effective published-port mapping (`8333/tcp: []`)
and the explicitly configured Windows loopback client timed out. Its stopped
container and volume remain retained; this is a connectivity failure, not an
S3 compatibility result. No historical service was involved.

For the second profile use a dedicated ordinary bridge with only S3 published
on Windows loopback. Master, volume and filer bind container loopback; unused
surfaces stay disabled. This permits the selected Python 3.13 client without
adding another interpreter, proxy or test service. It does not enforce an
outbound network denial: record effective listeners/connections and the disabled
telemetry setting, and do not claim an egress firewall. Docker administration
and the local host remain trusted. Shared deployment and stronger network
enforcement require a separate decision; neither is accepted by this spike.

## Accepted evidence, 2026-10-23

The foundation guide records adopted files and exact
commands. Final evidence includes eight new signed conflicting-create races,
unchanged winning bytes, actual role denials, full eleven-object readback from
a new process after container replacement with the same data volume, real-SDK
redirect/ambient-configuration refusal and a parent-owned trickle deadline.
The source-only eight-file candidate passes restricted read-only review and
deterministic acceptance for both frozen storage and codec input sets.

Original test failures and incorrect supplementary SDK mock assumptions remain
retained. Reviewed superseding versions follow the unchanged publication,
resource-limit and explicit-configuration rules; no backend or application
exception handler was weakened to satisfy a fake. Ambient AWS selectors now
fail safely before SDK construction. Core retry behavior remains unchanged.

The offline image preparer validates the exact original context bytes; it does
not establish reproducible upstream compilation or a bit-identical rebuilt
image. The SDK library has no internal whole-command deadline; its future caller
must enforce the contract's process lifetime. The local HTTP/ordinary-bridge,
host-admin trust, incomplete security audit, no capacity/off-host guarantee and
separate cloud authorization limits above remain in force. Both owned profiles
finish stopped with their volumes retained.
