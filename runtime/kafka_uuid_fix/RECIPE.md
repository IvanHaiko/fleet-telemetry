# Local Windows UUID candidate recipe

This is a project-maintained derivative of upstream 2.16.0, not an upstream
release. Only the patch, recipe modules and pin files are adoption inputs.
No source copy, compiler, wheel or DLL is versioned here. Python modules use
only the standard library. Existing SDK environments are never replaced.

The parent must first compile the unchanged seven upstream sources with the
same Zig `cc` arguments recorded by this recipe and validate its Windows
CPython 3.13/librdkafka ABI. Keep that baseline, compiler output and failed
probes. Then run this recipe with a fresh output path whose parent exists:

```sh
python3.13 runtime/kafka_uuid_fix/build.py \
  --inputs /path/to/provisioned/inputs \
  --python-root /path/to/Python313 \
  --output /path/to/fresh-owned-output
```

The inputs tree is the supplied tree, including `sdk-source/confluent_kafka-2.16.0`,
`zig/zig-x86_64-linux-0.17.0`, the original wheel and sdist, `zig.tar.xz`, and
`librdkafka/rdkafka.h`. The Python root supplies `include` and `libs/python313.lib`.
`pins.json` contains the three ADR-0025 archive hashes and observed compiler,
source and librdkafka header hashes. `python-pins.json` pins every supplied
Python header and import library. Input files and their ancestors must not be
symlinks. Compiler files are compared against every regular file in the pinned
Zig archive, including its libraries. No downloads, installs or system caches
are used. Compiler caches and temporary files stay inside fresh output.

The output owns `OWNER`, `source`, `include`, `cache`, `global-cache`, `tmp`,
`build`, `wheel` and `build-manifest.json`. Existing output is refused. It is
never cleaned or resumed automatically. Compilation failures retain their log
and manifest; pre-compilation input failures stop without invoking Zig. Keep
failed output, and choose another fresh path for retries. Do not change SDK
logic or compiler flags silently to get a successful build; baseline and
candidate must share flags. The only source differences are the reviewed patch.

The first two complete candidate wheels failed exact reproducibility: their
extensions differed only in 20 PE timestamp/build-ID bytes; `.text` and all
other sections apart from `.buildid` were identical. Retain both failed builds,
their wheels, logs, manifests and comparison diagnostics as failed evidence.
The recipe now adds exactly `-s` to the Zig `cc` flags to strip unshipped debug
metadata. Tiny probes with pinned Zig 0.17.0 across different source/output
paths produced byte-identical binaries with `-s`; timestamp-control alternatives
`--no-insert-timestamp` and `/timestamp:0` are unsupported. These probes do not
establish full-wheel reproducibility. No metadata mutation or binary patching
is used.

The parent must repeat complete builds with the revised recipe in separate
fresh output trees, compare exact extension and wheel bytes/hashes and retain
the complete member inventory. Baseline and candidate must both use the revised
flags. Repeat the full ABI, frozen constructor/guard tests, real Windows broker
UUID comparison, exact record/progress checks, Linux compatibility and restricted
read-only review gates before adoption. This recipe repair leaves those gates
pending; it does not turn the original reproducibility failure into a pass.

The source patch touches only `src/confluent_kafka/src/confluent_kafka.c`:
two signed 64-bit getters and two `c_Uuid_to_py` half conversions through a local
checked helper. Allocation failure in that conversion follows the existing
cleanup path. Generic long helpers, constructors, base64 and hashing are intact.
The original wheel supplies all Python files, DLLs and license files unchanged.
The recipe parses the bundled librdkafka PE exports and invokes pinned Zig
`dlltool` to generate an import library; it never executes the DLL.

The seven sources, include paths, explicit `x86_64-windows-gnu` target and link
inputs are recorded in the manifest commands. The wheel has the local version
`2.16.0+fleet.uuid1`, matching dist-info/METADATA, the original
`cp313-cp313-win_amd64` tag, and a regenerated RECORD. The manifest records all
added/deleted/changed member names, member hashes, wheel hash, native DLL hashes,
input hashes, patched-source hashes and patch hash. It does not certify ABI or
correctness: successful output is marked `built_unvalidated`.

Parent-owned gates remain: baseline ABI probe, actual candidate build, isolated
Windows environment, frozen native constructor tests without skips, independent
broker UUID byte comparison/getters, exact records and unchanged committed
progress, repeated build, and restricted read-only review. Preserve stock
Windows failures. No broker work is part of this recipe. Rollback selects the
preserved stock environment, whose unsafe UUID boundary must still refuse
admission; no historical receipts or offsets are rewritten.

## Provisioned source provenance

Provision inputs explicitly, verify `pins.json`, then extract into the named
input directories. The builder performs no acquisition. Archives and extracted
files are both checked before compiler execution. The authoritative URLs are:

- `zig.tar.xz`: https://ziglang.org/download/0.17.0/zig-x86_64-linux-0.17.0.tar.xz; SHA-256 `1cbe9df9f27e6b78d14ccbca43b6703a404ef79ef1c463de901d7f088d4e2026`.
- `confluent_kafka-2.16.0-cp313-cp313-win_amd64.whl`: https://files.pythonhosted.org/packages/99/5c/4cdf2d9c660f52d87746793218917f03b1978291ac102c25d61f4fda838a/confluent_kafka-2.16.0-cp313-cp313-win_amd64.whl; SHA-256 `3b00c1ea376d80288b03f36389d603c3d9fef9f62a5e180f48565ac1c6368004`.
- `confluent_kafka-2.16.0.tar.gz`: https://files.pythonhosted.org/packages/b4/28/ef5544a6c1120b5e5da5098ec93238a8f753b01a701351e3fc83ba72e1d2/confluent_kafka-2.16.0.tar.gz; SHA-256 `8268b8763a0c0503a99a55a9cac0132ed010932135d4222f67e2c804d1597508`.
- `librdkafka/rdkafka.h`: https://raw.githubusercontent.com/confluentinc/librdkafka/v2.16.0/src/rdkafka.h; SHA-256 `09f5d9bf81240b985d1adb83d1cb4e84faa7d0591de01478b2a47e776550cd1a`.

The Zig archive is extracted beneath `inputs/zig/` and the PyPI sdist beneath
`inputs/sdk-source/`; keep the exact original archive filenames above.
The exact installed Windows CPython 3.13.1 include tree and `libs/python313.lib`
are provisioned read-only as `--python-root`. `python-pins.json` is the required
per-file inventory, not a permission to use another header/API version.
The original wheel is read directly; no extracted wheel is trusted by the build.

Run the adopted independent checks with an actual compatible SDK installed:

```powershell
.local-discovery/kafka-client-2.16.0-fleet-uuid1-verified/Scripts/python.exe -B -m unittest discover -s runtime/kafka_uuid_fix/checks -v
```

Both constructor and guard suites must run, without native skips. Broker UUID
conversion, ABI and recovery are additional integration gates in the repair
report. A constructor-only success cannot certify `AdminClient` conversion.
