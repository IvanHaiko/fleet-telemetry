# UUID repair acceptance checks

These frozen stdlib tests implement the public interface in
`docs/reference/windows-kafka-uuid-repair-interface.md` and ADR-0025 without inspecting a
candidate implementation. Run from the repository root in the target environment:

```
python -m unittest discover -s checks -p 'test_*uuid*.py' -v
```

| Gate | Evidence and limits |
| --- | --- |
| ActualSDK | Requires importing the real installed `confluent_kafka`; missing SDK is an error, never a skip. Literal signed64 pairs cover zero, -1, both extrema, mixed signs, asymmetric halves and three pairs with identical low32 but different high32 in both halves. Independent signed `int.to_bytes` concatenation and stdlib standard base64 certify both getters and the entire unpadded string. Zero is valid here. No `int(Uuid)` assumption. Stock Windows getter truncation must fail. |
| Lazy guard | Fresh `telemetry.kafka_compat` import with `sys.modules['confluent_kafka'] = None` must succeed; calling its public guard must raise its public `KafkaCompatibilityError`, a `ValueError`, with exactly `kafka_uuid_boundary_unavailable`. |
| Admission | Full-width fake public UUID conversion permits both exact distribution versions, upstream native API 2.16.0 and CPython 3.13. This models the passing stock Linux and corrected local boundary without imposing an OS restriction. CPython profile patches permit this suite to run under the tester's Python 3.14. Wrong distribution/native API versions, missing metadata, unsupported Python/implementation and malformed SDK surfaces must refuse. |
| Conversion refusal | Separate corruption of constructor high bits, either getter, unsigned reinterpretation, getter return type, string high bits and string tail must refuse, even with approved version labels. Native errors carrying sensitive detail must produce only the fixed safe error. A correct admission followed by a broken SDK must refuse. |
| Side effects / isolation | Client constructors, socket creation/connections and builtins file opening are forbidden during admission. SDK module attributes and UUID class attributes must remain unchanged. Public module-cache, metadata and runtime-profile patches restore their original state on context exit, including failures; fresh guard import restores the parent package binding. No private helper or import-style assumption is used. |

## Required parent integration gates

Constructor tests cannot certify the separate broker metadata-to-Python C
conversion. A candidate can pass every constructor case while still returning
truncated topic IDs. On the actual CPython 3.13 Windows x86-64 runtime, the parent
must use a real AdminClient to describe real topics and compare both signed half
getters and complete string bytes with independently collected Kafka Admin CLI
UUIDs. Decode CLI URLsafe base64 to 16 bytes before comparison; do not derive the
expected identity from the SDK. Require nonzero real topic IDs. Preserve stock
Windows failures and repeat equivalent Linux checks. These checks are
complementary, and both must pass before acceptance.

The parent also owns guard-before-mutation checks in the maintained M2/M3 entry
paths, exact record and committed-progress checks, stopped runtime evidence,
ABI/build reproducibility and changed-file inventory. No mocked guard test
certifies those properties or repairs historical identities. Broker access is
unavailable in this restricted tester role.

## Local validation

Both Python files were parsed with `ast.parse` only. The candidate guard and SDK
were not exposed, so no runtime pass or broker result is claimed. No SDK code,
implementation, documentation, installed environment or network resource was
modified. The suite uses only the Python standard library, apart from the
intentionally required real SDK in ActualSDK and the candidate guard under test.
