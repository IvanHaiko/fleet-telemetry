# Development guide

For a first Kafka/Flink run, use the [single-machine quickstart](docs/local-development.md).
It needs Docker/Compose and Python 3.13, with no host package installation.
The locked development environment below is for source checks and optional readers.

Read the [architecture](docs/architecture.md) and the
relevant contract before changing behavior. Keep changes focused, preserve local
work and update the document that owns the changed behavior. Tests should prove
an observable invariant or a reproduced failure, rather than duplicate code.

## Root Python environment

Use Python 3.13 and uv 0.11.19. `pyproject.toml` and `uv.lock` own the root
environment; optional ULog, Kafka and MAVLink dependencies are separate extras.

```sh
uv sync --frozen
uv run --no-sync python scripts/check-m1.py --profile synthetic
```

The check runner verifies the lock, synchronizes the chosen profile, runs Ruff
lint and format checks over the whole repository, strict mypy over the library
and root tests, and the root test suite, then converts, verifies and reads a fresh
synthetic run. Pass `--profile ulog` to include the binary reader, or `--offline`
when all locked packages are already cached. The synthetic profile deliberately
omits optional parser/client packages; it must not reuse a mixed environment
without synchronization.

For a small change, reuse focused checks in the existing environment:

```sh
uv run --no-sync python -m pytest tests/test_recording_runtime.py -q
uv run --no-sync python -m ruff check .
uv run --no-sync python -m ruff format --check .
uv run --no-sync python -m mypy
```

The default mypy configuration covers the library and root tests. Changed
runtime/scripts need explicit type checking in the environment that supplies
their optional dependencies. The module-size guard covers owned Python modules
in the root, library, scripts, runtime and tests. Files must stay below 500 lines;
responsibility boundaries matter more than splitting a file to meet a number.

HTTP tests open loopback sockets. Symlink checks require symlink privileges.
Linux-only workers and the isolated ClickHouse test have explicit environment
requirements. Report skips and setup failures separately from passing tests.

## Runtime checks

PyFlink has a separate Linux/Python 3.12.13 project under `runtime/pyflink/`.
Its dependencies and tests are not part of a root `uv sync`. S3 and native
service boundaries also have their own checks. Follow the selected runbook
instead of recursively running all experiment code or starting every Compose file.

The [M1 guide](docs/guides/m1-checks.md) and
[testing strategy](docs/testing-strategy.md) describe the existing check lanes.
The manual M2 GitHub workflow builds and exercises a synthetic broker profile;
it can download/build dependencies and start services. Run it only in a selected
empty scope. Historical broker evidence and local data must not be reused as
disposable test storage.

## Source and data hygiene

Keep credentials, original flight logs, sensitive coordinates, database files,
checkpoints and run receipts in ignored local storage. `.local-discovery/` contains
retained evidence as well as scratch; it is not a disposable cache. Keep virtual
environments and offline dependency caches local too.

Public fixtures are small and synthetic unless their redistribution rights have
been reviewed. Review screenshots for tokens, account details and coordinates.
Keep third-party notices with maintained repair artifacts. Project contributions
use the [MIT License](LICENSE); external recordings and vendored material retain
their own licensing.

Before publication, inspect the complete file inventory, run relevant checks and
review the actual diff. Commits and remote publication require the maintainer's
instruction.
