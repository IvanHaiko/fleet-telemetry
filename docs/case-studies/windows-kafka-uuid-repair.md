# Windows Kafka UUID repair

## Result, 2026-10-24

The Windows x86-64 CPython 3.13.1 UUID boundary is repaired in the local
`confluent-kafka==2.16.0+fleet.uuid1` derivative. Full signed halves, broker-owned
128-bit identities, exact record reads and bounded recovery checks pass.
[ADR-0025](../adr/0025-windows-kafka-uuid-repair.md) bounds its adoption; the
[acceptance interface](../reference/windows-kafka-uuid-repair-interface.md) owns the contract.
The original Windows failures remain failed. This does not complete M4 or adopt
the retained experimental native archive reader.

The server is unchanged. The patch changes four integer conversion sites in
one upstream C file: two UUID getters and two broker-to-Python UUID halves.
The original 133 Python files, six DLLs, license files and wheel tags remain
byte-identical. Distribution metadata explicitly identifies the local build;
the extension API and librdkafka still report upstream `2.16.0`.

## Cause and minimal reproduction

On Windows, C `long` has 32 bits. The released C bridge uses
`cfl_PyLong_FromLong` in both UUID half getters and `cfl_PyDict_SetLong`, whose
argument is `long`, in `c_Uuid_to_py`. Signed 64-bit UUID halves are narrowed.
The latter happens before constructing the returned Python UUID, so converting
that already-corrupted object to a string cannot recover the original identity.
Linux x86-64's 64-bit `long` explains the earlier platform difference.

```python
from confluent_kafka import Uuid

value = 0x0123456789ABCDEF
print(Uuid(value, 0).get_most_significant_bits())
# Expected: 81985529216486895
# Stock Windows 2.16.0: -1985229329
```

Both stock wheel and unchanged source rebuilt with the same toolchain reproduce
five failing literal subcases in the independent constructor method, without
skips. The fixed build passes that method, including both signed extrema and
pairs whose low 32 bits collide. Broker-return conversion is checked separately
against Kafka's CLI, never against an expected UUID derived from the SDK.

The patch uses `PyLong_FromLongLong` and a local checked `int64_t` dictionary
helper. Allocation/dictionary failures follow the existing cleanup path. It
does not change generic integer helpers, UUID construction/encoding/hashing,
broker data, offsets or measurement identities. The exact source authority is
the pinned PyPI sdist; a repository tag is useful for locating the functions but
is not substituted for those build inputs.

Primary sources: [released distribution](https://pypi.org/project/confluent-kafka/2.16.0/),
[upstream C bridge](https://github.com/confluentinc/confluent-kafka-python/blob/v2.16.0/src/confluent_kafka/src/confluent_kafka.c),
[upstream header](https://github.com/confluentinc/confluent-kafka-python/blob/v2.16.0/src/confluent_kafka/src/confluent_kafka.h).
The source distribution is Apache-2.0 licensed. Its original license bytes are
retained. No upstream issue, pull request or remote publication was performed.

## Build and artifact evidence

The [recipe](../../runtime/kafka_uuid_fix/RECIPE.md) and pin files define all seven
C sources, original wheel/sdist, librdkafka header, portable Zig 0.17.0 and the
Windows Python 3.13.1 header/import-library tree. Builds run in owned Linux
scratch for the Windows `x86_64-windows-gnu` target. No system compiler is
installed; no original Python environment is overwritten.

Two complete final builds use separate fresh source/output/cache trees and
produce the same wheel and extension hashes:

- Wheel SHA-256: `0dc6e8f18580d0825b1cabb1ce7d228610601b847088dc3a8ba90790705022f3`.
- Extension SHA-256: `d509d3cf74d61075dac67332d483753cb3b198d885b1567b5d45360a9342c769`.

After normalizing the dist-info directory rename, only the extension, METADATA
version and regenerated RECORD change. Both extensions export only
`PyInit_cimpl`. PE imports retain Python 3.13, the exact original librdkafka DLL
and Windows UCRT/Kernel32 libraries; the rebuilt extension does not require an
additional runtime DLL. This is observed compatibility for the exercised API,
not certification of every SDK feature or another Python/architecture profile.

The first complete builds differed in 20 bytes of PE timestamps/build IDs;
all machine-code and other section bytes matched. A narrowly scoped recipe
repair adds `-s` to omit unshipped debug metadata. Supported tiny compiler
probes preceded two new complete builds. No binary bytes were patched after
linking. Original non-reproducible wheels and failed flag probes are retained.
An unchanged final-flag control still reproduces the UUID failure.

## Admission and local use

`telemetry.kafka_compat.require_uuid_boundary` imports the optional SDK lazily,
checks CPython 3.13, the supported distribution/API/native versions and full
signed-half/string behavior on every call. It creates no client, contacts no
broker and caches no successful result. Maintained M2 consumer/producer fixture
entry points and M3 transport construction call it before downstream work.
Stock Windows refuses with `kafka_uuid_boundary_unavailable`; stock Linux and
the corrected Windows profile pass. A fixed error carries no native details.

The final wheel is retained under the ignored evidence directory's
`verified-artifacts/`. It is installed into a separate environment:

```powershell
$env:UV_CACHE_DIR = "$PWD/.local-discovery/uuid-repair-cache"
uv venv --python 3.13.1 --no-python-downloads .local-discovery/kafka-client-2.16.0-fleet-uuid1-verified
uv pip install --python .local-discovery/kafka-client-2.16.0-fleet-uuid1-verified/Scripts/python.exe --no-index --no-deps --link-mode copy .local-discovery/windows-uuid-fix-20261024-001/verified-artifacts/confluent_kafka-2.16.0+fleet.uuid1-cp313-cp313-win_amd64.whl
.local-discovery/kafka-client-2.16.0-fleet-uuid1-verified/Scripts/python.exe -B -m unittest discover -s runtime/kafka_uuid_fix/checks -v
```

These setup commands require a fresh environment name; the delivered environment
already exists. The explicit SDK suite requires the actual optional dependency;
absence is an error, never a skip. The existing `uv.lock` is unchanged and an
ordinary sync selects the stock release, not this derivative. Select the
verified environment explicitly for Windows Kafka commands; a lock sync into it
would discard that selection. Original SDK environments remain available.

## Actual broker and recovery checks

The final Windows profile uses the existing Kafka 4.4.0 image, fresh owned
Compose project `fleet-windows-uuid-verified-001` and loopback
`127.0.0.1:19092`, with the existing 2 CPU / 1536 MiB
limits and 128 MiB temporary mount. At least 2 GiB free workspace space is
checked before the tiny fixture. Its new topics and volume are retained; all
historical profiles remain stopped and unchanged.

Three metadata topics reconcile full SDK strings and both signed getters with
independently decoded Kafka CLI bytes. The exact-read topic adds four binary,
null/empty, timestamped and ordered/repeated-header observations. Its group is
explicitly initialized to committed next offset `0` by setup only. Readback is
exact and does not change progress.

A separate read process first observes the real valid `[0,4)` interval and
correct full identity, then waits at assignment. The parent enables short
retention only on this disposable topic, observes expiry and checks the same
CLI UUID before releasing original offset `0`. Real fetch raises
`source_gap/offset`; a later ordinary preflight raises `source_gap/retention`.
Retained bounds become `[5,5)`. Committed progress stays `0` throughout.
The retained native reader is exercised unchanged and stays outside adoption
inputs. The barrier fabricates no data, metadata or error.

Existing producer checks prove ACK-before-receipt interruption, explicit retry,
six observations/three unique events/three duplicates and bounded unavailable
endpoint failure. Existing consumer checks prove pre-commit exit/replay,
post-commit exit/no replay and two corrupt-receipt refusals. Four M2 topic
identities additionally reconcile with Kafka CLI. Expected failpoint exits
remain explicit. The broker is stopped after each owned experiment.

## Checks, failures and independence

| Check | Observed result |
| --- | --- |
| Independent frozen UUID/guard suite, Linux 3.13.1 and final Windows 3.13.1 | Five methods pass normally and with `-O`; no skips |
| Stock Windows guard, M2 consumer, M2 producer, M3 initialization | Fixed refusal before client/input work |
| Existing Linux synthetic dependency profile | 411 passed; 32 explicit optional ULog skips |
| Existing offline M4 regression | 66 methods pass; no skips |
| Changed production/build modules | Ruff, format and strict mypy pass |
| Adopted independent tests | Same complete AST as frozen inputs; formatting only |
| Final artifact inventory and repeated build | Exact member/section/hash checks pass |
| Full Windows broker UUID/read/expiry and M2 recovery checks | Pass; services finish stopped |

The Tester ran in a separate restricted Linux CLI session before candidate
exposure. Its tests/contract were frozen outside writable role paths. The
Implementer and the single recipe-only repair used separate restricted sessions;
read-only execution and a separate read-only Reviewer observed real permission
denials. The installed CLI could not mount individual writable files, so
implementation directories were writable and exact file scope was checked
afterward. This limitation does not turn those directories into read-only inputs.
Windows/broker integration is trusted-parent verification; strict Windows child
isolation, host-loss durability and general SDK/production coverage are unproven.

Earlier failures are preserved: NTFS compiler timeout, the initial writable-file
profile failure, two non-reproducible wheels, rejected linker flags, an omitted
scripts import path in the parent pytest harness, pytest scratch symlinks rejected
by whole-workspace snapshots, Windows test working-directory shadowing, the
initial default cache permission failure, a Windows/WSL harness path translation
failure before broker mutation, a draft Markdown encoding error caught before
adoption, and a conversion harness output name
that disagreed with the existing dataset-run contract. Corrected harnesses use
the documented paths; source-only scope is verified independently. None changes
the frozen expectations or relabels an unsuccessful attempt as successful.

Ignored `.local-discovery/windows-uuid-fix-20261024-001/` retains original inputs,
source/index baselines, download receipts, all build manifests/logs, independent
role archives, frozen-v1 hashes, PE/member comparisons, actual Windows/Linux
commands, broker CLI output, observations, progress/failure receipts, historical
container comparisons, read-only review and deterministic final acceptance.
The original raw index bytes and logical staged state are checked separately.
No Git commit, push, cloud operation or storage cleanup is performed.

## Files, rollback and next task

Production changes are `telemetry/kafka_compat.py`,
`scripts/kafka_probe_contract.py`, `scripts/kafka_producer_transport.py` and
`scripts/m3_transport.py`. Build inputs are
`runtime/kafka_uuid_fix/{build.py,wheel_tools.py,pins.json,python-pins.json,sdk-uuid-int64.patch,RECIPE.md}`;
the two independent test modules and coverage note live in its `checks/`.
Documentation changes are this report, its interface and ADR-0025, README,
architecture/decision index, data contracts, roadmap, testing/deployment guides,
and dated follow-ups in the earlier Windows/Linux reader reports.
The final scope receipt lists every path and hash.

Rollback selects the preserved stock environment and retains explicit safe
refusal. Revert the guard and its three callers together only if reverting the
repair increment; never publish observations through the known defective SDK.
Keep all original receipts, wheels, evidence and volumes. No schema, data or
offset migration is performed. Historical Windows IDs require an independent
audit against trusted original broker identities; a new correct SDK cannot
reconstruct lost bits in old receipts.

The smallest next task is guarded native-reader admission using this verified
boundary, followed by the finite Kafka/S3 publisher and complete archive-only
expiry rebuild. Serving, production recovery and full M4 acceptance remain open.
The minimal C patch and literal constructor regression are suitable inputs to an
upstream report; they exclude project guards and the local compiler recipe.

## Historical audit and upstream preparation, 2026-10-24

The subsequent read-only audit confirms 59 narrowed
historical identities and 18 full matches against retained topic metadata.
[ADR-0026](../adr/0026-historical-topic-identity-qualification.md) qualifies the
earlier topic-identity trust portion of M2/M3 evidence while preserving original
bytes and all separate observations. Correcting new native calls does not admit
the diagnostic mapping as a migrated receipt.

The [submission package](../../contributions/confluent-kafka-uuid-int64/README.md)
contains a minimal native regression, independent metadata reproduction and
English source patches/report. An already-open Confluent PR #2325 addresses
the same cause; the preferred contribution adds tests/evidence to it. Current
master and PR-head preimages are pinned and patch-checked. No upstream message,
commit or push was performed, and the project's pinned runtime is unchanged.
