# ADR-0061: Build the recording Flink image independently of the broker

**Status:** Adopted for local recording on 18 November 2026 after both runtime checks.

The recording JobManager, TaskManager and submission client need the same
PyFlink runtime. Building it through two unpublished project images requires
restoring an unrelated broker payload before compiling the connector.
The root starter uses a different Flink distribution. Switching recording to
the starter would also change the Python environment and connector.

The [recording recipe](../../runtime/pyflink/container/Dockerfile.recording)
uses the digest-pinned Temurin base of the previous broker recipe directly.
Keeping that OS layer preserves the launcher ABI. It also retains the unused
base JRE. The active JDK is Temurin 17.0.20.1+1. The retained Linux payload
pins Python 3.12.13 and PyFlink 2.2.1 at the original absolute prefix.
The separate compilation stage runs the existing [ADR-0023](0023-bounded-kafka-enumerator-backport.md)
builder with SQL Kafka connector 5.0.0-2.2. Each runtime or base upgrade
requires another build, native preflight and recovery run.

An empty BuildKit content store produced manifest
`sha256:48b7eb2aa98e49b2c50099e7e04d74c61f34acb4a174bb4180ad7ec30c17d2a1`.
The final UID/GID was 10001:10001, the 14,625-file preflight passed and
the launcher reported Flink 2.2.1. The compiled JAR matched ADR-0023.
The runtime tar digest is
`77495b61bec4821e502bfe7c2277171e0cfbca4d6a45ecf7df3f3b65d5513a34`.
Its build receipt records SHA-256
`9f1b414c32f0fd79db55379f2929c4f264361b8c510608242e86287f0abc951c`
for the PyFlink uv.lock and
`2480c9654e757a4eb98b23f79bc24e4268b1fcd577fc7d2005b0e424911de09d`
for the upstream artifact list as retained with CRLF line endings.
The checked-in LF copy has identical content after newline normalization.
Repeat the [build and inventory](../guides/f09-single-machine-run.md#building-the-recording-flink-candidate)
using the retained payload and source. Availability of these external inputs
on the build host is a prerequisite. Preserve the previous image by digest
for existing runs, including their checkpoints.

The 180-second F09 slice `flink-image-f09-20261118-01` produced 3,057 input
deliveries. After SIGKILL the TaskManager restored checkpoint 8 at committed
offset 1,045. Recovery took 30.577 s against a 120 s limit. SQL held 1,705
physical rows and 1,619 unique facts. The query-visible and archive-rebuilt
fact hash sets both equalled the independent reference. Maximum visibility
delay outside the fault window was 2.001 s. The run passed its declared
correctness and timing checks. The retained rollback digest also passed a
standalone runtime preflight. Cross-image checkpoint migration was not tested.

The 200-second SITL run `flink-image-live-20261118-01` archived all 1,108
deliveries and reproduced all 792 positions in SQL. The 19 silence observations
were stale and the ten gateway-down observations were unknown. Every declared
timing and correctness check passed. Compose selects the tested digest for both
managers and submission.
