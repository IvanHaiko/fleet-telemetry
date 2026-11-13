# ADR-0039: Two-host six-broker Wi-Fi laboratory

**Status:** Proposed, 2026-10-27. Offline preparation is authorized. Transfer and
startup are deferred until the maintainer connects the machines, approximately
2026-10-30. No remote publication, installation or host configuration change is
authorized by preparation. This adds a separate candidate to ADR-0035, not a
replacement for its retained single-host evidence.

## Problem and decision

The 2026-11-03 tiny two-host evidence now establishes
authenticated endpoint/replica placement and exact reconciliation for 128
measurements. Explicit controller host IPs/published ports repair reproduced
container-hostname TLS failures. Flink's pinned SQL connector also requires its
relocated password-provider class. These implement the intended TLS/routing
boundary; broker sizing, sustained load and host-failure availability remain
unaccepted. This ADR remains proposed outside the demonstrated tiny scope.

Six brokers on one host cannot exercise a physical network interruption. Use
one Kafka cluster split three brokers per host, with separate Docker Compose
projects and local SSD-backed volumes. The PC has Windows 10, 32 GiB RAM and an
i7-6700K; the connection is Wi-Fi. A read-only host query on 2026-10-27 identifies
the laptop as Windows 11 Home, Core Ultra 7 155H (16 cores/22 logical processors)
and 31.5 GiB OS-visible RAM. Exact Windows builds, Docker support, network
reachability and disk budgets need admission on transfer day.

Place broker/controller IDs 1 and 2 and broker ID 4 on the PC; place
broker/controller ID 3 and broker IDs 5 and 6 on the laptop. The shared dynamic
KRaft bootstrap contains exactly controllers 1, 2 and 3 with the same cluster
and controller-directory IDs in both host recipes. Keep the tested launcher
whose controller rule is `node.id <= 3`. Never generate each half independently.

Use host rack labels `pc` and `laptop`, eighteen partitions and RF=2/min ISR=2
for measurement/history/live topics; retain RF=3/min ISR=2 for internal topics.
Read back actual replica/rack placement before publishing. RF=2 must put one
replica on each host. All-replica acknowledgements deliberately trade write
availability for refusing a single remaining copy. Do not lower min ISR during
an outage. Two controllers on the PC keep a majority after laptop loss, but the
measurement topics still cannot accept writes without both replicas. PC loss
removes the controller majority. This is a two-failure-domain laboratory, not
host-failure HA or a production availability claim.

Advertise explicit stable private host IPv4 addresses with unique published
ports; use those same endpoints from brokers and clients on both machines.
Cross-host Docker bridge names and `127.0.0.1` are not routable peer identities.
Require mutual TLS on client/replication and controller listeners, verifying
IP subject alternative names. Separate per-node and per-component private keys
stay outside source/configuration archives. A lab CA authenticates trusted lab
participants; topic ACL enforcement is not implemented by this candidate.

Initially keep Flink JobManager/TaskManager and their local checkpoints on the
laptop alongside development, publisher and browser. Put archive, serving and
their Linux host workers on the PC, with loopback storage APIs. This corrects
the initial PC placement after inspecting the laptop hardware; it is a resource
allocation hypothesis, not a measured throughput comparison. Kafka replication,
some Flink reads and Flink output cross Wi-Fi. Flink RPC/checkpoint storage stay
within one host, as do S3/SQL access from their workers. Any laptop access to
PC-hosted management APIs requires a separately validated authenticated loopback
tunnel; no new publicly exposed storage endpoint is selected here.

## Alternatives and maintenance cost

- All services on the PC simplify operation but do not exercise inter-host Kafka.
- Two independent three-broker clusters require cross-cluster replication and a
  second identity/offset recovery model; that does not meet this single-cluster goal.
- Three brokers plus three dedicated controllers model role separation but do
  not provide three data brokers per host. Combined roles reuse the existing lab
  implementation; critical deployments should isolate controller resources.
- RF=3/min ISR=2 can improve individual-broker write availability but adds a
  third data copy and Wi-Fi/disk traffic. Two hosts still cannot each retain a
  majority after the other fails; a third physical failure domain is separate scope.

No new service type, orchestration platform or package is selected. Maintenance
adds one offline configuration renderer, TLS material/rotation procedures, two
host inventories and explicit endpoint/security admission in existing clients.
The client follow-up now implements
`two-host-kafka-client-v1`: six trusted endpoints across two hosts, native PEM
options and JVM PKCS12/file-provider options propagated into the existing
clients/source/sinks. Unknown fields, incomplete TLS and unexpected metadata
refuse. This shares only pure configuration admission; transport libraries,
delivery policy and current pinned repairs remain in place. Offline and mocked
SDK checks do not establish handshake behavior. Certificate issuance,
authorization, client security, network behavior,
aggregate resource usage and throughput require actual validation before adoption.

## Transfer, verification and rollback

The [complete configuration procedure](../guides/two-host-setup.md) now implements
laptop JM/TM/submit and PC archive/serving overlays without replacing the pinned
images or admitted Flink wrapper. Explicit source, adapter, processing and
private certificate binds refuse missing paths. Native-Linux OpenSSL/keytool
issuance supplies thirteen distinct node/component identities and private role
configs; exporters separate public source/config ZIPs from authority/storage
secrets. Short file/crypto/Compose checks pass; actual target admission remains
deferred. No separate orchestration system or new service type is adopted.

The transfer runbook defines source ZIP, image TAR and separate
private material; manifests bind bytes rather than relying on an uncommitted
Git revision. Start a new empty cluster and replay only a tiny authored fixture.
Historical Kafka volumes/checkpoints/cursors are retained on their original host.
Copying them would require a separately designed state-preserving migration.

The renderer is an offline Kafka candidate only. Two-host adoption requires
bidirectional TLS connectivity from actual containers, metadata endpoint/identity
checks, rack placement, exact source/archive/query reconciliation, broker return
and a timed Wi-Fi interruption/recovery. Observe failures and pressure at a small
rate before any load experiment. Stop only the new projects/workers to roll back;
retain volumes/evidence, and never reset historical offsets or discard state.

References: [Kafka 4.4 KRaft](https://kafka.apache.org/44/operations/kraft/),
[listeners](https://kafka.apache.org/44/security/listener-configuration/),
[rack-aware replica placement](https://kafka.apache.org/44/operations/basic-kafka-operations/#balancing-replicas-across-racks),
[WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking).
