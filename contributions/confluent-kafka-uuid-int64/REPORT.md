# Windows UUID narrowing in confluent-kafka-python

## Existing report and tested environment

Related open [PR #2325](https://github.com/confluentinc/confluent-kafka-python/pull/2325)
already identifies this LLP64 conversion issue. This package supplies a small
automated regression and actual Windows Python/client/broker evidence for that
discussion. The fallback C patch intentionally covers UUID conversion only.

Observed environment: Windows x86-64; CPython 3.13.1; official
`confluent-kafka==2.16.0` cp313 Windows wheel; librdkafka 2.16.0; local Apache
Kafka 4.4.0 for the separate metadata check. A stock Linux x86-64 CPython 3.13.1
pair passes the same constructor regression.

## Minimal reproduction

```python
from confluent_kafka import Uuid

value = 0x0123456789ABCDEF
print(Uuid(value, 0).get_most_significant_bits())
# Expected: 81985529216486895
# Stock Windows 2.16.0: -1985229329
```

The least-significant getter has the same narrowing. In addition,
`AdminClient.describe_topics(...)[topic].result().topic_id` can lose both high
32-bit portions while crossing from librdkafka into Python. Compare decoded
UUID bytes against Kafka CLI `TopicId`; the CLI uses URLsafe base64 while the
Python UUID string uses standard base64. Alphabet differences alone are not a bug.

## Cause and narrow fix

Windows uses a 32-bit C `long` even on x86-64. Both getters pass native signed
64-bit halves through `cfl_PyLong_FromLong`. `c_Uuid_to_py` passes both native
halves through `cfl_PyDict_SetLong`, whose parameter is `long`, before constructing
the Python UUID. Linux x86-64 uses a 64-bit `long`, hiding the defect there.

The fallback patch uses `PyLong_FromLongLong` for the getters and a small checked
`int64_t` dictionary helper for the two broker-return halves. It checks failed
allocation/dictionary insertion and uses the existing cleanup path. Generic
integer helpers, UUID construction/string encoding/hash, Kafka records and
offset behavior are unchanged. PR #2325 offers a broader shared-helper fix;
the test-only patch can accompany that approach instead.

## Validation and exact scope

The independent native regression uses ten literal signed-half pairs, including
zero, -1, signed extrema and high-bit values with identical low 32 bits. Expected
bytes come from Python signed big-endian integers, independently of the SDK.
The original stock Windows wheel and unchanged rebuilt source fail five
subcases. The local narrowly repaired 2.16.0 build passes; stock Linux passes.
These are real native SDK executions, with no skip or substitute implementation.

Earlier live Windows checks independently compared three broker-owned UUIDs,
four exact binary/null/empty/header observations, and later expiry refusal with
unchanged committed progress. Existing producer retry and consumer interruption
checks also passed on that local repaired build. These broader project checks
are corroborating evidence, not proposed upstream test/dependency additions.

The submission preparation additionally checks patch application/reversal,
exact C/test/changelog output and the standalone constructor/broker scripts.
Exact commands and observed outcomes are summarized in the prepared validation
receipt. No project guards, fixtures, local build recipe, machine paths, topic
inventories, private logs or binaries are included in the patches.

The tested source archive and tag v2.16.0 (`4a1bcb01a1c977bc61faa6c8ae72f56aa250c121`) have identical original
`confluent_kafka.c` SHA-256
`09a6cdf3447b0ae654dbaccc4ec3714b831a9aae1539d121435bf3fdec8811c1`.
The fallback patch is rebased and apply-checked against master `fbb7c3b349a26f7ba32d7e00d55373f9b450efba`;
the test-only patch is checked against PR head `050b1f59ff4e175cc1b397052a5ac5ccf215f1b9`. Those two new upstream
heads are not claimed to have been rebuilt or to have passed their complete CI.
The published branch/PR may advance after these pinned observations.

## Impact and limits

Applications that record topic UUIDs for provenance, recovery or topic-recreation
checks can persist an incorrect identity even when record bytes and offsets look
correct. Lost bits cannot be reconstructed from a narrowed UUID alone. A fixed
client does not repair old receipts automatically; independent broker evidence
is required. This report does not claim a broker defect, end-to-end exactly-once
delivery or coverage of other Admin 64-bit fields.
