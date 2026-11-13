# Non-expiring bounded Kafka fixture profile

## Implemented scope, 2026-10-22

The authorized [ADR-0020](../adr/0020-bounded-tests-and-s3-archive.md) follow-up applies
non-expiring retention to newly created ordinary topics in `scripts/kafka-probe.py`
and `scripts/check-kafka-producer.py`. Their existing three-record input,
receipt and recovery protocol is unchanged. Producer retry also checks admission
and effective settings before publishing again. This does not implement a
general 50 GiB ingestion command or S3 archival.

The shared `scripts/kafka_topic_policy.py` sets and reads back:

```properties
cleanup.policy=delete
retention.ms=-1
retention.bytes=-1
segment.bytes=1048576
min.insync.replicas=1
```

Only fresh-topic creation applies these overrides. The helper never alters
existing settings. Drift fails before publication; unknown-topic visibility
after creation is retried for at most 15 seconds. The retention harness still
shortens time retention only on its own disposable topic after publication.
Receipt resume tests the missing-offset refusal without requiring non-expiring
settings on that intentionally expired topic.

## Admission and storage boundary

Before creation or producer retry, the helper requires the finite three-record
fixture and inspects the local Docker runtime. Supported contexts are Desktop's
Linux-engine named pipe and the default local Linux Unix socket; `DOCKER_HOST`
and other endpoints are refused. It identifies the single running broker
publishing port 19092, verifies loopback binding and Compose service/volume
ownership, then matches its cluster ID to Kafka metadata. The historical Desktop
profile is refused before data-directory inspection.

Read-only `du -sk` measures allocated bytes of the whole Kafka volume, including
other topics and internal files. `df -Pk` reads free bytes on that filesystem.
Workspace free space is checked independently for local evidence. Failed
commands, missing permissions and invalid measurements refuse admission; there
is no host-filesystem fallback for measuring the broker's disk.

For this tiny profile, let `P` be the sum of key/value lengths plus 1 KiB per
record. Require `P <= 64 MiB`. Reserve `R = 64 MiB + 2*P` for topic/index
allocation and two publication attempts. Require allocated volume bytes plus
`R <= 50 GiB`, and at least `R + 1 GiB` free on both broker and workspace
filesystems. These are conservative admission allowances, not measured expansion
factors or a reservation of 50 GiB. They do not size a future large-input reader,
S3 copies, unbounded retries or a new checkpoint topology.

This point-in-time check is neither a filesystem quota nor a lock against
concurrent writers. Use one bounded publisher at a time. Other disk users and
Docker Desktop's backing host disk can still consume capacity; check backing
placement and all simultaneous copies before larger work. No 10-50 GB capacity,
long-duration uptime, full-disk safety or production durability is claimed.

## Live validation

The existing Kafka 4.4.0 image
`sha256:676a930ab90762c2c32ef79642ad2293c18e5cea96381fc72af54e51fb3cd1c3`
was reused without build/pull. Fresh Compose project `fleet-fixture-policy-001`
used its own cluster ID and `fleet-fixture-policy-001_kafka-data` volume. This is
a validation fixture, not another adopted broker topology.

- Consumer interruption before commit replayed three observations; interruption
  after commit replayed none. Two corrupt receipts refused; final progress was 3.
- Producer ACK-before-receipt retry yielded six observations, three unique
  identities and three duplicates with matching content.
- An ordinary topic acknowledged three records with Kafka transport timestamp
  `1` ms after Unix epoch. Their exact values and offsets `[0,3)` survived real
  retention cleanup cycles and a stopped-volume restart.
- The disposable retention topic expired `[0,3)`. Recovery refused the explicit
  gap, left committed progress at 0 and created no success artifact.
- Both historical container IDs, images, mounts and stopped states matched
  before/after. The fresh broker finished stopped with its volume retained.

The old-timestamp case does not claim long downtime was observed. Its timestamp
is transport metadata; canonical measurement bytes stayed unchanged. This is
not archive restoration, physical secure erasure or hosted CI evidence.

## Checks and evidence

The existing full root suite with the pinned optional Kafka client passed all
443 cases, including 19 new policy cases: refusal before mutation on full,
over-budget and unknown storage; workspace pressure; effective-setting drift;
selective visibility retry/deadline; wrong cluster; quarantine; invalid readings.
Root/script strict typing, script/new-test Ruff and format checks and the
module-size guard passed. No package was installed.

Exact commands, outputs and exits remain in ignored
`.local-discovery/fixture-topic-policy-001/`:

```powershell
.venv/Scripts/python.exe -B .local-discovery/fixture-topic-policy-001/checks.py
$env:PYTHONPATH = "$PWD;$PWD/scripts"
.venv/Scripts/python.exe -B .local-discovery/fixture-topic-policy-001/live_check.py
```

The live command requires a fresh project/container/volume and stops its own
project in `finally`. It is retained reproduction evidence, not a reusable public
CLI; another run needs reviewed fresh project/evidence identities. Detailed
results are in `runtime-commands.json`, `runtime-completion.json`,
`old-timestamp.json`, the three harness directories and `checks.json`.
`completion.json` lists source scope and hashes. No independent restricted
Reviewer or blind-test cycle is claimed for this increment.

## Rollback and next task

Restore the scoped source increment from `source-before.zip`, remove only the
new policy/test/guide files and reverse its navigation/status additions. Keep
all old and fresh evidence and volumes. Source rollback restores former defaults
for future topic creation; it does not change retained non-expiring topics.
Never restart historical storage or shorten existing retention as an automatic
rollback step. No canonical or receipt migration is required.

Next: choose bounded archive format/client interfaces and prove independent
readback and expired-Kafka rebuild with tiny fixtures. Amazon S3 is the selected
final target; archive implementation and cloud execution remain separate work.
