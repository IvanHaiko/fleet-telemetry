# Windows UUID contribution package

Prepared 2026-10-24 for `confluentinc/confluent-kafka-python`. Nothing has been
posted, committed or pushed by this preparation.

There is already an open related contribution:
[PR #2325](https://github.com/confluentinc/confluent-kafka-python/pull/2325).
It addresses these UUID conversions and additional Admin offset/timestamp
conversions. Prefer adding the regression and Windows evidence to that PR.
Its source and test gap were checked through the official API on 2026-10-24.
Recheck status before posting; do not claim this is a previously unreported bug.

## Files and alternatives

- `regression-for-pr-2325.patch`: adds only `tests/test_uuid_int64.py` to the
  related PR head `050b1f59ff4e175cc1b397052a5ac5ccf215f1b9`. It contains no competing C fix.
- `confluent-kafka-uuid-int64.patch`: fallback narrow UUID C fix, the same native
  regression and an Unreleased changelog entry for master `fbb7c3b349a26f7ba32d7e00d55373f9b450efba`.
  The patch touches three upstream files and does not fix Admin offsets.
- `test_uuid_int64.py`: standalone copy of the regression in both patches.
- `verify_topic_uuid.py`: read-only AdminClient/independent CLI comparison.
- `REPORT.md`: environment, reproduction, cause, scope and validation limits.
- `COMMENT_FOR_PR_2325.md`: English text to post with the test patch/evidence.
- `provenance.json`, `SHA256SUMS` and `LICENSE`: source pins, package checksums
  and upstream source-license text. No local SDK wheel, DLL or private log is included.

Choose one patch according to the maintainer's request. They are alternatives;
do not apply both, because both add the same test file.

## Check and apply in a separate upstream checkout

For the existing PR, check out its contributor branch at `050b1f59ff4e175cc1b397052a5ac5ccf215f1b9` and run:

```sh
git apply --check /path/to/regression-for-pr-2325.patch
git apply /path/to/regression-for-pr-2325.patch
python -m pytest tests/test_uuid_int64.py -q
```

For the fallback fix, use the pinned master commit:

```sh
git switch -c codex/windows-uuid-int64 fbb7c3b349a26f7ba32d7e00d55373f9b450efba
git apply --check /path/to/confluent-kafka-uuid-int64.patch
git apply /path/to/confluent-kafka-uuid-int64.patch
python -m pytest tests/test_uuid_int64.py -q
git diff --check
```

Build/install the upstream extension using its own documented development
toolchain before testing the fix. Applying source alone does not replace an
already installed extension. To exercise the real LLP64 regression, run the
native test on Windows x64 too; a Linux-only green result misses the defect.
The standalone test also runs as `python test_uuid_int64.py -v`, without pytest.
Missing SDK is a failure; there is no platform skip or fake implementation.

## Broker-return conversion

On an owned test broker, obtain `TopicId` independently with Kafka's CLI:

```sh
bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --describe --topic uuid-int64-repro
python verify_topic_uuid.py --bootstrap-server 127.0.0.1:9092 --topic uuid-int64-repro --expected-topic-id CLI_TOPIC_ID
```

The topic must already exist. The Python script performs metadata reads only.
Pass the CLI's complete 22-character URLsafe ID, not an SDK-derived value.
Exit 0 means both native getters and the complete SDK string equal the original
16 bytes; exit 1 is a mismatch; exit 2 is invalid input/client failure.
This check is separate from the constructor regression and needs a real broker.

Follow the upstream contributor guide for final style, full CI and submission.
This package does not assert that MSVC, all upstream tests, PR #2325's build or
Admin offset/timestamp cases were executed locally. No remote publication is
necessary to inspect or validate these files.
