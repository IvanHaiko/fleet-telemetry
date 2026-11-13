# ADR-0027: Supervised local archive publication and reconstruction

**Status:** Bounded local Linux runtime decision, 2026-10-26. Final adoption is
gated by the runtime evidence, independent frozen
tests, actual broker/storage evidence, read-only review and deterministic acceptance.
This does not supersede earlier accepted decisions or authorize cloud execution.

## Problem and bounded choice

The accepted graph coordinator depends on trusted source, storage and process
ports. The native Kafka reader is now admitted, but there is no concrete commit
adapter, bounded S3 inventory, externally protected recovery root or complete
command deadline. A writer-owned descriptor cannot establish independent root
trust. A library timeout cannot end a blocked stream or child process tree.

Use a Linux CPython 3.13 supervisor and the already selected SDKs. Keep the
read-only native reader unchanged; a separate commit adapter supplies explicit
synchronous whole-interval progress. Reuse immutable S3 create/read and graph
verification. The supervisor retains/fsyncs the descriptor outside worker mounts
only after a fresh reader with separate credentials verifies the full graph.

The installed bubblewrap 0.11.1 supplies separate user/PID/mount namespaces.
Writer and S3-reader workers share the host network solely for the configured
loopback clients; they receive only a read-only production-code closure,
interpreter, SDK paths and their role's request over pipes. Parent roots, original
source paths, converter output and oracles are not mounted. A separate final
reconstruction process receives only newly downloaded archive objects and has a
private network namespace. Actual denial probes precede use; unavailable
namespaces or the wrong runtime fail closed. This is an explicit Linux runtime
requirement, not another orchestration service or a Windows isolation claim.

For rebuild, a fresh reader downloads and verifies the S3 graph into a new
bounded staging directory using reader credentials. Only after its successful
exit does the network-isolated process reverify that staged archive against the
independently supplied descriptor hash and create fresh output. Staging is
restore input freshly obtained from S3, never an old writer cache. Report the
networked fetch and offline reconstruction as separate process boundaries.

The supervisor owns one monotonic deadline of at most 120 seconds, including
pipe I/O, verification, retention and child shutdown. It terminates/reaps its
owned process groups on failure or deadline. Preserve incomplete directories
and objects. A timeout after a commit remains ambiguous until explicit retry
revalidates the graph and observes broker progress; never invent a rollback.

## Alternatives and maintenance

In-process hooks leave root access and process lifetime unenforced. Windows-only
children lack demonstrated filesystem/process-tree isolation. A second service
for root retention or a new orchestration framework adds unnecessary operations
for one finite fixture. A custom syscall sandbox would duplicate an installed,
reviewable OS tool. Docker-based worker images add a build/runtime compatibility
gate which is unnecessary for this local host-process profile.

No new Python dependency, SDK version, image, persistent service, cloud resource
or archive format is selected. Bubblewrap and the Linux kernel/user-namespace
policy become explicit prerequisites; maintain their version/probe evidence.
The existing system util-linux is not a new product dependency. Bound per-worker
memory/CPU/file output and budget source, archive, staging and rebuilt copies.
Disk/backend admission and Compose service resource evidence are recorded for the
actual fixture; no production capacity, host-loss or malicious-admin guarantee.

Fresh storage startup exposed a separate local-profile defect: default master
growth requests seven single-copy volumes, exceeding the four-volume fixture
limit after initial filer allocation. Keep the failed fresh profile stopped.
The pinned executable's generated master scaffold specifies the public
`master.volume_growth.copy_1` setting. Mount an explicit local master configuration
with growth counts of one and maintenance scripts disabled; keep the four-volume
and 64 MiB limits. Increasing volume capacity would mask the bounded-profile
problem. Verify fresh bucket writes and role denials on a new volume. This changes
startup configuration only, introduces no new service/version and never alters
historical containers or deletes their existing volumes. Retain the original
failed commands and successful configuration bytes with the runtime evidence.

## Acceptance and rollback

Require independent adapter/process/root tests frozen before candidate exposure;
wrong APIs or oracles need explicit preserved adjudication. Verify denied worker
root/source/oracle access, immutable root reuse/refusal, actual S3 reader/writer
denials, bounded inventory and whole-command timeout/shutdown. Publish real
Kafka observations, verify exact archive bytes and lineage before explicit commit,
and exercise interruption/retry around batch, receipt, retention and commit.
Expire only fresh fixture topics with unchanged UUID, refuse normal recovery,
stop Kafka and reconstruct from freshly read S3 without source/oracle access.
Reconcile exact observations, unique measurements and a separate bounded reference.

Rollback stops invoking the command and restores this increment's source/tests
and navigation together. Keep the original native guard, all archive objects,
root descriptors, broker progress, stopped volumes and failed evidence. No
deletion, schema migration, offset reset or automatic fallback is introduced.
