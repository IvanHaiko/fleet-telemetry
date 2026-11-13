# Native PC worker environment

## Prepared boundary, 2026-11-03

Following PC storage and monitoring admission,
the maintainer authorized preparing the remaining PC worker runtime. A separate
Linux environment is now installed and admitted for the existing archive,
serving and metrics worker commands. No worker consumer, Kafka broker or Flink
processing job was started by this preparation. The subsequent
tiny two-host slice exercises those prepared workers
and reconciles 128 source/archive/query measurements; its test processes finish
stopped with state retained.

The initial PATH-based probe found Ubuntu's default Python 3.14.4 and no
`python3.13` command. A deeper inventory found an already installed uv-managed
CPython **3.13.18**. That interpreter was reused rather than downloaded or
replacing system Python. Existing user uv **0.13.6** remains unchanged; an
isolated project uv **0.11.19** satisfies the repository's required tool version.

## Placement and versions

The native Linux root is
`~/telemetry-workers/pc-20261103-001`. Ubuntu's registered disk
location is `H:\WSL\Ubuntu`, so the environment, package cache, tools and
temporary files are physically backed by the requested H: volume.

| Item | Selected location/version |
| --- | --- |
| Existing CPython | `~/.local/share/uv/python/cpython-3.13.18-linux-x86_64-gnu/bin/python3.13` |
| Frozen source | `<root>/source`, 398 files checked against the transferred source manifest |
| Worker interpreter | `<root>/source/.venv/bin/python`, CPython 3.13.18 |
| Project uv | `<root>/bin/uv`, 0.11.19 |
| Tool environments | `<root>/tools` |
| Cache / temporary files / logs | `<root>/cache`, `<root>/tmp`, `<root>/logs` |
| Shell environment | `<root>/env.sh`, mode 0600, explicitly sourced per shell |

Kafka client is `confluent-kafka==2.16.0`, with matching librdkafka and the
existing full-width signed UUID admission check. The installed S3 packages
exactly match `runtime/s3/requirements.lock`: boto3/botocore 1.43.117,
jmespath 1.1.0, s3transfer 0.19.3, python-dateutil 2.9.0.post0, six 1.17.0 and
urllib3 2.8.0. S3 installation uses every required wheel hash from that lock.

The reviewed local preparation script uses:

```bash
# Bootstrap outside the project, into explicitly scoped tool/cache directories.
"$bootstrap_uv" tool install --python "$python" 'uv==0.11.19'
# Then use only that project's pinned uv and existing CPython.
"$uv" sync --locked --extra kafka --no-dev --python "$python"
"$uv" pip install --python .venv/bin/python --require-hashes -r runtime/s3/requirements.lock
```

Necessary packages were downloaded into the new H:-backed project cache. No
system package, system interpreter, existing user uv, repository dependency
specification or lockfile was modified. The native source copy is independently
hashed before installing its environment; no historical native source directory
was overlaid. Private credentials remain in the existing ACL-restricted PC
deployment directory rather than in this public source snapshot.

H: had 81.46 GiB free before preparation and 81.28 GiB at successful admission;
C: had approximately 13.3 GiB free before and 13.32 GiB afterward. These are
snapshots, not peak disk measurements or continuous quotas. No WSL/Docker disk
was moved, compacted or deleted.

## Checks and actual endpoint access

The existing entry point passes:

```bash
"$SDK_PYTHON" -m runtime.continuous.split_tools check-runtime --host pc
"$SDK_PYTHON" -m runtime.continuous.split_tools verify-source --directory /mnt/h/telemetry/pc-20261103-001/transfer
```

The full signed UUID conversion boundary passes without creating Kafka clients.
Archive, serving and metrics modules all import and accept `--help` under the
new interpreter. This checks loading and CLI dispatch, not consumer execution.

An additional read-only check runs **on the PC in native Ubuntu**:

- Authenticated ClickHouse loopback query returns the existing admission facts:
  three rows, sum 60.
- The independent S3 reader retrieves exactly 72 bytes with SHA-256
  `c316a87f0629f0a7d06fed729590c4ee340a38271e40938eec8e8c7a173d0577`.
- All six current Prometheus targets are healthy after the monitoring repair
  below.
- The existing Windows Docker CLI works through WSL interop at
  `/mnt/h/Docker/resources/bin/docker.exe`; no Docker Desktop settings were
  changed and no Docker daemon/socket was installed in Ubuntu.

Loopback reachability was actually tested before assuming Windows-to-WSL
behavior. It works in the current target runtime. `docker` without an explicit
path still refers to the unavailable WSL-integration path; the project exports
`DOCKER_EXE` instead. This Windows CLI expects Windows-compatible Compose/bind
paths; generic Linux-path Compose behavior is not established by `docker info`.

The package/version/lock-hash report is retained on the PC at
`H:\telemetry\pc-20261103-001\evidence\worker-environment.json`;
`native-worker-admission.json` records the authenticated Linux-side readback.
Preparation/check logs and script copies remain in that deployment's evidence
and transfer directories, with laptop copies under the ignored
`.local-discovery/pc-deploy-20261103-001/` scope. No credentials are printed.

## Monitoring defect found during admission

The first final native-worker check refused because Grafana's native scrape
had crossed its 5,000-sample limit. Other five targets were healthy. This was
an actual `sample limit exceeded` result, not an interpreter or SQL/S3 failure.
The failed log and target snapshot remain retained.

Only the PC profile's Grafana scrape was narrowed to the metrics required by
the current process/runtime dashboard:

```yaml
sample_limit: 5000
label_limit: 20
body_size_limit: 8MB
metric_relabel_configs:
  - action: keep
    source_labels: [__name__]
    regex: process_.*|go_.*|grafana_build_info
```

The original sample limit is preserved rather than raised. The previous
configuration is saved on the PC. Promtool validates the complete configuration
and three rules; only the owned Prometheus container is restarted, retaining
its TSDB. The profile generator is updated to reproduce this allowlist.

After repair Grafana has 272 post-relabel samples, all six targets are UP,
and all ten overview expressions still return valid direct Prometheus results
and finite Grafana points, with empty firing alerts explicitly allowed. The
native-worker admission then passes. Unselected Grafana application metric
families are deliberately unavailable; this repair does not claim all native
Grafana metrics are collected. No source, storage, Kafka offset or checkpoint
was reset.

## Use, rollback and remaining gates

From a PC Ubuntu shell:

```bash
source ~/telemetry-workers/pc-20261103-001/env.sh
cd "$FLEET_PC_WORKERS/source"
"$SDK_PYTHON" -m runtime.continuous.split_tools check-runtime --host pc
"$DOCKER_EXE" ps
```

The environment file affects only the shell that sources it. Existing default
Python/uv commands outside that shell remain unchanged. No worker is configured
to run at login or boot. Exiting the shell is sufficient to stop using this
environment; retain its source/cache/evidence rather than deleting runtime data
as rollback. To revert the scrape filter, use the saved PC Prometheus file and
validate with promtool before restarting the owned collector; the original
sample-limit failure would remain unresolved.

Next is a small two-host Kafka-to-query scenario using a deliberately selected
topology and fresh input/output scopes. Worker configuration still needs actual
topic identities, partition bounds, groups, TLS bindings and protected cursors;
those are not fabricated by runtime installation. Sustained throughput,
checkpoint/host recovery and the 100-vehicle load remain unvalidated. No commit
or Git publication was performed.
