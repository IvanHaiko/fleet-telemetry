# Windows Kafka UUID repair acceptance interface

This contract scopes the authorized repair under
[ADR-0025](../adr/0025-windows-kafka-uuid-repair.md). It does not adopt an archive
worker or change measurement or observation identity semantics.

## Corrected native boundary

The local candidate is derived from exact upstream confluent-kafka 2.16.0 source
and the exact CPython 3.13 Windows x86-64 wheel. It must expose the same public
Python API and librdkafka 2.16.0 runtime. Its distribution metadata records a
distinct local version, `2.16.0+fleet.uuid1`; `confluent_kafka.version()` may retain
the upstream extension API version `2.16.0`. Original DLLs and Python files are
unchanged. The patch changes only UUID integer conversion boundaries; it adds
no process-global monkeypatch or private-memory-layout access.

For all signed 64-bit halves `a`, `b`, construct `confluent_kafka.Uuid(a,b)`.
`get_most_significant_bits()` must equal `a` and
`get_least_significant_bits()` must equal `b`, without truncation or unsigned
reinterpretation. String bytes must encode exactly the concatenation of the two
64-bit two's-complement bit patterns, big endian, as standard unpadded base64.
Include 0, -1, signed extrema and distinct pairs with identical low 32 bits.
The zero UUID is valid for direct constructor tests; actual topic identity must
be nonzero. Do not assume an undocumented `int(Uuid)` implementation.

Broker-returned UUIDs must preserve every one of the original 128 bits too.
Decode the independent Kafka CLI's URLsafe base64 before comparing bytes; an
SDK-derived expected value cannot certify this conversion. Test both half
getters and full strings. Existing stock Windows failures remain failures.

## Project admission guard

`telemetry.kafka_compat.require_uuid_boundary() -> None` is a lazy boundary
guard, without importing the optional SDK at module import. It imports the SDK
only when called. It accepts only distribution versions `2.16.0` and
`2.16.0+fleet.uuid1`, native API version `2.16.0`, and CPython 3.13. Its observed
UUID self-checks include high bits and negative/extreme halves plus complete
encoded bytes. A stock Linux pair may pass; a truncated Windows pair must fail.
Version alone is not evidence of correctness. The guard returns None only after
all checks; a missing SDK, unsupported version/profile or failed/malformed UUID
conversion raises `KafkaCompatibilityError(ValueError)` with fixed string
`kafka_uuid_boundary_unavailable`. No raw native message or supplied data leaks.
Other programming errors must not be silently turned into successful admission.

The guard does not access Kafka, create clients, modify modules or write files.
It runs before project broker mutation or publication in the maintained M2/M3
entry paths. Existing safe diagnostics may wrap the guard error. It does not
repair or normalize already-corrupted historical topic UUIDs.

## Acceptance and limits

Use a small independent stdlib suite with literals as its oracle. Constructor
tests require the actual SDK and must not pass by skipping stock failures.
Guard tests may inject an SDK-shaped module and distribution metadata, but must
exercise observable refusal before any client/network operation and lazy import.
Keep all test inputs frozen during repairs. Build/ABI and actual AdminClient
checks are separate parent integration gates, not mocked SDK evidence.

The final checks must compare real Windows broker/SDK UUIDs, exact records and
unchanged committed progress, retain all failures and show stopped runtime state.
An isolated new environment receives the candidate wheel; never overwrite an
original installed environment. A local success does not establish complete
SDK feature coverage, shared deployment or full archive recovery.
