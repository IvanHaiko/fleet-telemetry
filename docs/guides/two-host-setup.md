# Complete two-host configuration and transfer procedure

The 2026-11-03 actual tiny slice records the first
successful Kafka/Flink/archive/SQL execution across the cable. It corrects
controller advertisements and Flink's relocated password provider, retains
initial failures and verifies 128 measurements before stopping the test. The
earlier preparation commands below are historical; use a fresh generated bundle
and the current pinned source, preserving old scopes and private boundaries.

## Prepared boundary

The core 3+3 laboratory configuration is implemented offline, 2026-10-27.
Kafka base recipes, laptop processing overlay, PC storage overlay, component TLS
credentials, role-specific client configurations and source/configuration ZIP
export are executable preparation commands. No additional code is required to
fill the previously pending service/transfer configuration. Real IP addresses,
host paths, certificate ownership, installed runtimes and network reachability
must be supplied or checked on the connected machines around 2026-10-30.
No target deployment or throughput result is claimed. ADR-0039 remains proposed.

Use WSL Linux shells and the installed Docker CLI on each host. Do not assume
Windows 10 supports the laptop's Windows 11 networking mode. The earlier
network/failure contract and client schema
remain authoritative. No firewall, WSL, service or retained-data change was made
by preparation. Commands below that start services belong to transfer day.

| Host | Base recipe | Runtime overlay | Private inputs |
| --- | --- | --- | --- |
| PC | Nodes 1, 2, 4; controllers 1, 2 | ClickHouse and SeaweedFS | Node TLS, S3 identities, SQL bootstrap password, initializer/archive/serving/metrics TLS |
| Laptop | Nodes 3, 5, 6; controller 3 | Flink JM/TM, explicit submit profile | Node/Flink TLS, processing JSON; publisher/live TLS and their restricted configs |

Flink state remains in a laptop-local named volume; PC archive/SQL use their own
named volumes. All storage APIs and Flink REST remain loopback. Kafka listener
ports are the only generated LAN publications. Six source lanes are not implied:
the existing eighteen partition-local watermark/Battery branches are preserved.
Submitting is explicit; ordinary `compose up` does not submit a job.

## 1. Freeze public files

From the current checkout, using the existing project Python:

```powershell
.venv/Scripts/python.exe -m runtime.continuous.split_tools export-source --directory .local-discovery/transfer-source-001
.venv/Scripts/python.exe -m runtime.continuous.split_tools verify-source --directory .local-discovery/transfer-source-001
.venv/Scripts/python.exe -m runtime.continuous.prepare_split --directory .local-discovery/split-final-001 --pc-ip <actual-PC-IPv4> --laptop-ip <actual-laptop-IPv4> --project fleet-split-20261030-001
.venv/Scripts/python.exe -m runtime.continuous.split_tools verify-bundle --directory .local-discovery/split-final-001
.venv/Scripts/python.exe -m runtime.continuous.split_tools export-bundle --bundle .local-discovery/split-final-001 --directory .local-discovery/transfer-config-001
```

Each destination must be new. Source export captures current tracked **and
untracked** reviewed source, so an initial/uncommitted Git checkout is supported.
It preserves bytes, includes maintained repairs in `contributions/`, and excludes
private names, keys/stores, ignored directories, retained data and virtualenvs.
The exporter now includes the two required live HTML pages; earlier source ZIPs
predating the live UI repair omitted them and must be
replaced by a freshly generated archive.
Its allowlist is a packaging boundary, not a general secret detector: review the
path inventory before transferring. Configuration export includes only the
public inventory, even if another file was accidentally placed beside it.

The 2026-10-28 transfer audit also found that earlier ZIPs omitted
`runtime/kafka/kafka-probe.properties` and
`runtime/pyflink/container/Dockerfile.backport`. Both are now explicitly included
and covered by the existing source-export regression. Replace earlier source
ZIPs; see the cleanup and PC transfer record.

Transfer `source.zip`, `source-manifest.json` and their `.sha256` files, plus
`configuration.zip` and its `.sha256`. Confirm hashes through the trusted
transfer channel, then verify on arrival and extract into fresh directories.
Same-channel hashes detect accidental corruption, not replacement of both the
package and its asserted hash. Do not overlay a historical checkout or volume.
Set public extracted directories/files readable by container UID 10001; ZIP
members carry mode 0644, and directories need traversal permission.

Call the extracted source directory `SOURCE` and configuration directory `BUNDLE`.
The project/run ID and cluster identity come from `BUNDLE/manifest.json`.
Example addresses in previous checks must not be reused as discovered addresses.

## 2. Existing runtimes, images and adapter

Host workers require x86-64 Linux CPython 3.13 and confluent-kafka/librdkafka
2.16.0. PC workers also require the exact existing S3 SDK lock in
`runtime/s3/requirements.lock`. The selected PyFlink image retains its own
Python 3.12.13/JDK 17/Flink 2.2.1 runtime; do not mix host and processing Python.
Do not copy a Windows virtualenv into Linux or assume a Linux virtualenv is
relocatable. Host interpreter/SDK preparation is a transfer-day prerequisite.
No dependency was downloaded or installed by this task. Existing locked setup
commands, when separately executed on the target, are:

```bash
# Existing supported uv/Python must already be available; installation is deferred.
uv sync --locked --extra kafka --no-dev --python <installed-Linux-CPython-3.13>
# PC only; reuse reviewed wheels/cache or a deliberately authorized SDK install.
uv pip install --python .venv/bin/python --require-hashes -r runtime/s3/requirements.lock
export SDK_PYTHON="$SOURCE/.venv/bin/python"
export PYTHONPATH="$SOURCE:$SOURCE/scripts"
"$SDK_PYTHON" -m runtime.continuous.split_tools check-runtime --host pc
# Laptop: use --host laptop; no S3 dependency is required for its publisher/live view.
```

Save existing images by their current tags, record `docker image inspect` image
IDs/repository digests, and hash each TAR. On arrival use `docker image load`,
compare image IDs and verify the exact pinned references resolve offline:

| Both hosts | Laptop additionally | PC additionally |
| --- | --- | --- |
| `fleet-telemetry/kafka-probe:4.4.0` | `fleet-telemetry/pyflink-m3:2.2.1-local2` | `fleet-telemetry/seaweed-m4:4.48-local1`, `clickhouse/clickhouse-server:26.8.34.13` |

```bash
docker image save --output <image.tar> <existing-tag>
sha256sum <image.tar> > <image.tar.sha256>
# Destination: sha256sum -c <image.tar.sha256>; docker image load --input <image.tar>
```

Recipes retain `pull_policy: never` and exact digest references. Missing local
images refuse; do not replace the maintained connector image with upstream.
Large image export/load is deferred. No registry publication is required.

On the laptop, build the native adapter with the existing pinned runtime:

```bash
bash "$SOURCE/runtime/pyflink/build-partition-time.sh" "$NATIVE_RUNTIME" "$ADAPTER"
```

`NATIVE_RUNTIME` is the existing `m3-compatibility-002` runtime; `ADAPTER` is a
fresh output directory. The script records source/JAR hashes. The generated
recipe mounts it at `/adapter`; initialization uses
`file:///adapter/partition-time.jar`. Never mount the private working checkout
as Flink's `/workspace`; mount the source-only export.

## 3. Fresh credentials, issued once

Choose the actual host-local private paths **before** issuing: `PC_PRIVATE_ROOT`
means the final `.../private/pc` path on the PC; `LAPTOP_PRIVATE_ROOT` means
`.../private/laptop` on the laptop. They can differ. The staging directory
`PRIVATE` holds `authority/`, `binding.json`, `pc/` and `laptop/`.

```bash
python -m runtime.continuous.split_tools credentials \
  --bundle "$BUNDLE" --directory "$PRIVATE" \
  --keytool "$NATIVE_RUNTIME/jdk/jdk-17.0.20.1+1/bin/keytool" \
  --pc-private-root "$PC_PRIVATE_ROOT"
```

This uses installed OpenSSL/keytool, generates fresh RSA-2048 lab CA and distinct
node/component keys, verifies each issued certificate's host IP, writes native
PEM and PKCS12 stores, and creates private SQL/S3 credentials. It uses mode 0700
directories/0600 files under a temporary 0077 umask; run it on a native Linux
filesystem that honors those modes. It never silently overwrites credentials.
Certificates last 30 days; check validity/clock on startup, and issue a fresh
credential scope for renewal. Runtime certificate authentication does not add
topic ACLs; all CA-issued lab participants remain trusted administrators.

Only `pc/` plus `binding.json` go to the PC, using a protected channel; the
laptop runtime receives only `laptop/` plus binding metadata. Keep the CA signing
key in the operator's protected authority directory, outside both runtime binds.
No private material goes into public ZIPs. S3 writer/reader actions are scoped
to the single generated `fleet-<run_id>` bucket; bootstrap retains administration.

Container UID 10001 must read broker/Flink credentials. On each host, for only
its explicit `node-N` directories and (on the laptop) `roles/flink`, set owner
10001 and the trusted operator's group, directory mode 0750 and file mode 0640.
For example, **after checking the resolved target path**:

```bash
sudo chown -R 10001:"$(id -g)" "$PC_PRIVATE_ROOT/node-1"
sudo find "$PC_PRIVATE_ROOT/node-1" -type d -exec chmod 750 '{}' +
sudo find "$PC_PRIVATE_ROOT/node-1" -type f -exec chmod 640 '{}' +
```

Repeat for the exact three local nodes, never the authority or host-worker keys.
Do the same for the laptop's `roles/flink` and later processing `job/` directory.
Do not make private keys world-readable. Ownership changes are transfer-day
administration, not operations performed during configuration preparation.

## 4. Validate both hosts, then start only the new scope

On each host define the local paths; laptop job/config paths may be declared
before files arrive but must exist before starting Flink:

```bash
export HOST=pc                     # laptop on the other host
export KAFKA_TLS_DIR="$PRIVATE/$HOST"
export FLEET_PRIVATE_DIR="$PRIVATE/$HOST"
export FLEET_SOURCE_ROOT="$SOURCE"
export FLEET_JOB_DIR="$ROLES/laptop/job"
export FLEET_ADAPTER_DIR="$ADAPTER"
DC=(docker compose -f "$BUNDLE/$HOST/compose.json" -f "$BUNDLE/$HOST/runtime.json")
# PC uses the private SQL bootstrap environment file:
if [ "$HOST" = pc ]; then DC+=(--env-file "$PRIVATE/pc/compose.env"); fi
"${DC[@]}" config --quiet
```

Verify existing OS/Docker/WSL support, all six TLS endpoints from actual
containers, controller endpoints, firewall peer scope, disk reserve, available
memory, power/sleep policy and time synchronization as described in the network
runbook. A configuration syntax check is not network readiness. Then, on the
PC start `kafka-1 kafka-2 kafka-4 archive serving`; on the laptop start
`kafka-3 kafka-5 kafka-6`, using `"${DC[@]}" up -d <named-services>`.
Wait for all six nodes, one shared quorum, TLS success/denial checks and storage
readiness before creating topics. Verify cross-host replica placement, RF=2 and
min ISR=2; internal topics retain RF=3/min ISR=2. Do not lower durability settings.

## 5. Initialize the tiny authored scope on the PC

Prepare the fixture using `manifest.json`'s `run_id`, exactly 64 base records and
64 vehicles. The generator adds 64 tail measurements: **128 unique measurements
total**, covering all eighteen partition lanes without a large replay.

```bash
"$SDK_PYTHON" -m runtime.continuous.generate prepare --directory "$FIXTURE" \
  --records 64 --vehicles 64 --run-id <run_id-from-manifest>
"$SDK_PYTHON" -m runtime.continuous.initialize \
  --private "$PRIVATE/pc/initializer.json" --fixture "$FIXTURE" \
  --output "$PRIVATE/pc/initialized.json" \
  --partition-time-jar file:///adapter/partition-time.jar
"$SDK_PYTHON" -m runtime.continuous.split_tools configs \
  --bundle "$BUNDLE" --private "$PRIVATE" \
  --initialized "$PRIVATE/pc/initialized.json" --directory "$ROLES" \
  --pc-private-root "$PC_PRIVATE_ROOT" --laptop-private-root "$LAPTOP_PRIVATE_ROOT"
```

Initialization talks to PC-local storage and the new Kafka cluster; it must not
be run during offline preparation. If it fails, preserve all evidence; use its
existing explicit `--resume-initialization` only on the same checked empty scope.
Do not issue credentials or create the other half of the cluster again.

Transfer only the authored `FIXTURE`, `ROLES/laptop/` and the declared laptop
private branch to the laptop. The role exporter strips all storage passwords
and S3 keys from publisher/live/processing files. `job/` contains only
`processing.json`; fix its UID/group/modes as above before Flink starts.
Keep `pc/initialized.json` on the PC for final reconciliation.

## 6. Run, inspect, reconcile and stop on transfer day

PC, in separate attended terminals (first startup only uses `--initialize`):

```bash
"$SDK_PYTHON" -m runtime.continuous.archive --config "$ROLES/pc/archive.json" --state "$STATE/archive" --initialize
"$SDK_PYTHON" -m runtime.continuous.serve --config "$ROLES/pc/serving.json" --state "$STATE/serving" --initialize
# Optional existing exporter, bound explicitly to loopback:
"$SDK_PYTHON" -m runtime.continuous.metrics --config "$ROLES/pc/metrics.json" --state "$STATE" --host 127.0.0.1 --port 18766
```

Laptop, using its own `DC` array and paths:

```bash
"${DC[@]}" up -d jobmanager taskmanager
"${DC[@]}" run --rm --no-deps submit
"$SDK_PYTHON" -m runtime.continuous.live --config "$ROLES/laptop/live.json" --port 18769
# Separate terminal, after readiness:
"$SDK_PYTHON" -m runtime.continuous.generate publish --config "$ROLES/laptop/publisher.json" --fixture "$FIXTURE" --ledger "$LEDGER" --rate 16
```

Do not repeat submission into an already running job. Inspect the loopback Flink
REST/job state and checkpoint health first. Native live API/page is laptop-local;
use its private reader token from `live.json`, never a query-string secret or
unauthenticated LAN listener. Worker restarts omit `--initialize` and keep their
exact original cursors. An already populated source requires an explicit replay;
normal first publication refuses it.

After archive/SQL catch-up, transfer the laptop's acknowledged ledger to the PC
and run the existing exact verifier:

```bash
"$SDK_PYTHON" -m runtime.continuous.verify --config "$PRIVATE/pc/initialized.json" --state "$STATE" --ledger <received-ledger> --output <fresh-report.json>
```

Then perform the bounded broker-return and 10-15-second Wi-Fi interruption drills
from the network runbook, preserving failures and reconciling results. Do not
infer success from running containers, raw SQL row counts or a live page alone.
Stop host workers with their terminal interrupt and use `"${DC[@]}" stop` on each
new project. Retain all volumes, checkpoints, source, ledger and cursors. No
`down -v`, retained-data cleanup, offset reset, commit, push or cloud action is
part of this setup.

## Preparation evidence and file scope, 2026-10-27

The short Windows selection passes 23 checks with 3 explicit Linux-worker skips
in 1.49 seconds. The final Linux selection passes 26 checks in 7.72 seconds:

```text
python -m pytest tests/test_split_setup.py tests/test_split_preparation.py tests/test_continuous_connection.py tests/test_continuous_archive.py tests/test_continuous_serving.py tests/test_live_state.py -q --basetemp .local-discovery/split-complete-linux-002 --tb=short
```

The Linux command uses the existing pinned Python 3.12.13 test environment,
`PYTHONPATH=$PWD:$PWD/scripts`, `PYTHONDONTWRITEBYTECODE=1` and a 30-second timeout.
It does not invoke the native Python 3.13 Kafka boundary or launch a JVM/service.
Windows runs use the existing Python 3.13 project environment and a fresh
`.local-discovery/split-complete-check-004` pytest base directory.

For each host, the generated final example passes this actual Docker Compose
CLI check, without an engine lifecycle operation:

```text
docker compose -f .local-discovery/split-complete-final-example-001/<host>/compose.json -f .local-discovery/split-complete-final-example-001/<host>/runtime.json config --no-interpolate --quiet
```

The ignored `.local-discovery/split-pki-probe.py` calls the real issuance function
with installed JDK 17.0.20.1/keytool and OpenSSL 3.5.5. It verifies thirteen leaf
certificates during issuance, counts the resulting leaves and checks that no
private file has group/other permission bits. The probe completes in 8.62 seconds;
its nonsecret result is `.local-discovery/split-pki-result.json`. Test private
keys stay in native Linux temporary storage and are not deployment credentials.
An earlier successful issuance's `/tmp` directory was unavailable to a later
inspection; that later check failed and is not counted as passing. The final
probe performs issuance/count/permission checks in the same process and retains
only the result outside temporary storage. Neither probe establishes broker TLS.

Ruff lint/format and Linux-platform mypy pass for the eight changed Python files:
`runtime/continuous/{split_runtime,split_credentials,split_transfer,split_tools,prepare_split,generate,metrics}.py`
and `tests/test_split_setup.py`. The exact type command uses
`python -m mypy --explicit-package-bases --platform linux --follow-imports=silent`
and those eight explicit paths. Initial checks found formatting and a Windows
versus POSIX path-rendering defect in role exports; using explicit POSIX target
roots repaired it before the passing tests. No target services, image export,
dependency installation, heavy replay or retained-state mutation ran.

New files: the four `split_*` preparation modules listed above,
`tests/test_split_setup.py` and this procedure. Modified files: the other three
Python modules, `.gitignore` (private PKCS12 exclusions), README,
`docs/architecture.md`, `docs/deployment-and-terraform.md`, `docs/roadmap.md`,
`docs/testing-strategy.md`, `two-host-lab.md`,
`m6-two-host-client-preparation.md` and ADR-0039. Existing unrelated local
changes remain intact; no commit or publication was performed.
