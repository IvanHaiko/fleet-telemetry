I reproduced the UUID part of this issue with the actual Windows x64 CPython
3.13.1 confluent-kafka 2.16.0 wheel and librdkafka 2.16.0.

```python
from confluent_kafka import Uuid
value = 0x0123456789ABCDEF
print(Uuid(value, 0).get_most_significant_bits())
# Expected 81985529216486895; observed -1985229329 on Windows.
```

The attached `regression-for-pr-2325.patch` adds a native regression with ten
literal signed-half pairs, including extrema and high-bit/low32 collisions.
It has no platform skip and requires the actual SDK. Five subcases fail on the
stock Windows build; the same test passes on a narrow local UUID repair and on
stock Linux x86-64. A Linux pass alone does not exercise LLP64.

I also verified the separate broker-return boundary on Windows: decoded
`AdminClient.describe_topics()` UUID strings and both signed getters must equal
Kafka CLI's independently decoded 16-byte TopicId. `verify_topic_uuid.py` is a
read-only reproduction for that check; it accepts the CLI ID as an explicit
oracle and does not create topics or change offsets.

This complements the existing fix rather than proposing an additional broad
Admin change. I have not built this PR head or tested its offset/timestamp cases;
the repaired execution above used a local UUID-only 2.16.0 derivative. The
package README records the exact source bases and validation limits.
