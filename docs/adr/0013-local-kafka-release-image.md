# ADR-0013: Build an isolated Kafka 4.4.0 experiment image from release bytes

**Status:** Accepted and locally validated for the authorized synthetic-only
image/admission experiment. Evidence records the
built versions and three-event checks. This does not accept M2 as a whole or
change the maintainer's selected Kafka version.

**Date:** 2026-10-20

## Problem and evidence

The maintainer selected Kafka 4.4.0 under
[ADR-0012](0012-kafka-ingestion-candidate.md). Direct Docker registry inspection
reports `apache/kafka:4.4.0: not found`, and the Docker Hub tag API returns 404.
The Apache 4.4.0 binary release and published SHA-512 are available. The selected
Python client imports on Windows with librdkafka 2.16.0. Its unavailable-endpoint
probe returns three timeout callbacks and no acknowledgements within its bound.

Waiting for the ready-made image would block the experiment. Substituting an
older broker contradicts the selected version. A third-party broker distribution
would add a different provenance/maintenance boundary without solving that need.

## Decision and reproducibility boundary

Build a clearly local experiment image from the unmodified official
`kafka_2.13-4.4.0.tgz` distribution. Use its published SHA-512:

```text
f5ceba8a265ab6bb2d68362b1f6859a95e15d60ef92ba83b43fdf065b557dc18e98d6383c15b9977320e25b3a2c8b6f11decb17b0fa6c0f163423793a0eb95cb
```

Pin the Linux amd64 base to
`eclipse-temurin:25-jre@sha256:171ffcf2a9ca207dfbc77b825cd3aaf8ab08d6113c086ee11514b965269fde28`.
Registry metadata identifies Temurin `25.0.4.1_1` on Ubuntu 26.04; record actual
`java -version` in the built image before startup. The platform manifest, not a
floating tag, owns base bytes. No OS package installation or source compilation
is needed. Keep the distribution's license and notice files in the image.

Retrieve archive and checksum over verified HTTPS, compare against the pinned
checksum before extraction and again during the build. This is checksum/TLS
evidence, not independently verified OpenPGP publisher authentication. No host
GPG executable was found; do not claim signature verification. Retain source URL,
observed checksum and image ID with the experiment. The result is a project-built
image, not an official Apache container or a bit-reproducible image-build claim.

Compose owns one combined KRaft broker/controller with loopback host access,
a named data volume, CPU/memory limits and bounded retention. Run as a non-root
user with read-only root filesystem and writable data/tmp mounts. Refuse to format
nonempty unformatted storage or reuse a mismatched cluster ID. Keep the fixed
cluster ID separate from measurement identity. Publish only synthetic fixtures.

## Impact, acceptance and rollback

This adds maintenance of a small Dockerfile/start script and explicit JVM/base
patch review. It consumes local image/disk/RAM capacity, with no cloud cost.
The first run is capped at one broker, 2 CPUs, 1536 MiB container memory and
512 MiB Java heap. These limits are experiment inputs, not a capacity claim.

Require broker version 4.4.0, inspected JRE version, identical three-event keys
and value bytes, explicit offsets and verified receipt-before-commit behavior.
Record runtime measurements and stop the experiment afterward, preserving the
named volume. Producer/consumer crash windows, retention deletion and host-loss
recovery remain unvalidated until separately exercised. No real-source ULog
acceptance or hosted CI claim follows.

Rollback stops only this Compose project and retains its volume and evidence;
do not downgrade that volume or delete unrelated resources. Future use of an
official 4.4.0 image requires a new digest/JRE inspection and the same boundary
checks. This supersedes only ADR-0012's proposed image-acquisition route; the
selected broker version and event contracts are unchanged.
