# ruff: noqa: E402
"""Archive-only finite serving replay and sealed report admission on Linux."""

import argparse
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path
from typing import cast

# Match the existing archive entry point: direct invocation needs no installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.archive_runtime.config import load_config, regular, strict_json
from runtime.archive_runtime.processes import _alarm
from runtime.clickhouse.transport import HttpConfig
from runtime.s3.archive_store import ArchiveStore, make_archive_store
from runtime.s3.immutable import StoreError
from scripts.slice_queries import require
from scripts.slice_run import admitted_report, publish_run, seal_existing
from telemetry.archive_codec import ArchiveError
from telemetry.archive_documents import digest, document
from telemetry.local_io import read_bounded
from telemetry.serving_projection import ServingError, ServingScope
from telemetry.serving_sink import SinkError

MAX_BYTES = 1_048_576


def http_config(value: object) -> HttpConfig:
    require(isinstance(value, dict), "invalid_http_config")
    fields = cast(dict[str, object], value)
    require(
        set(fields) == {"port", "database", "user", "password"}, "invalid_http_config"
    )
    return HttpConfig(
        cast(int, fields["port"]),
        cast(str, fields["database"]),
        cast(str, fields["user"]),
        cast(str, fields["password"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("publish", "seal-existing", "report"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--descriptor-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-run")
    parser.add_argument("--pipeline-version", default="source-query-v1")
    parser.add_argument("--rebuild-output", type=Path)
    parser.add_argument("--scratch-parent", type=Path)
    parser.add_argument("--seal-key")
    parser.add_argument("--seal-sha256")
    parser.add_argument("--batch-size", type=int, default=2)
    args = parser.parse_args()
    stores: list[ArchiveStore] = []
    try:
        require(
            sys.platform == "linux"
            and sys.version_info[:2] == (3, 13)
            and platform.machine().lower() == "x86_64",
            "unsupported_runtime_profile",
        )
        # One enforced Linux wall-clock budget covers all network operations.
        import time

        with _alarm(time.monotonic() + 120):
            config = strict_json(
                read_bounded(regular(args.config), MAX_BYTES), MAX_BYTES
            )
            required = {"archive_config", "reader", "seal_reader", "seal_prefix"}
            if args.mode == "publish":
                required |= {"writer", "seal_writer"}
            elif args.mode == "seal-existing":
                required.add("seal_writer")
            require(set(config) == required, "invalid_config")
            storage = load_config(
                Path(cast(str, config["archive_config"])), publish=False
            )
            descriptor = read_bounded(regular(args.descriptor), MAX_BYTES)
            require(
                digest(descriptor) == args.descriptor_sha256, "untrusted_descriptor"
            )
            spec = document(descriptor, "descriptor")
            require(spec["bucket"] == storage.bucket, "archive_bucket_mismatch")
            prefix = cast(str, spec["prefix"])
            archive = make_archive_store(
                storage.endpoint,
                storage.region,
                storage.bucket,
                prefix,
                storage.reader.access_key,
                storage.reader.secret_key,
            )
            stores.append(archive)

            def receipt_store(role: str) -> ArchiveStore:
                credentials = cast(dict[str, str], config[role])
                require(
                    set(credentials) == {"access_key", "secret_key"}, "invalid_config"
                )
                store = make_archive_store(
                    storage.endpoint,
                    storage.region,
                    storage.bucket,
                    cast(str, config["seal_prefix"]),
                    credentials["access_key"],
                    credentials["secret_key"],
                )
                stores.append(store)
                return store

            reader = http_config(config["reader"])
            require(
                not args.output.exists() and not args.output.is_symlink(),
                "output_exists",
            )
            if args.mode == "publish":
                from runtime.archive_runtime.supervisor import Supervisor

                require(
                    args.target_run is not None
                    and args.rebuild_output is not None
                    and args.scratch_parent is not None,
                    "missing_replay_arguments",
                )
                # This existing worker path independently fetches the graph and
                # reconstructs in a private network namespace without Kafka/source.
                scratch = args.scratch_parent.resolve(strict=True)
                rebuilt = Supervisor(storage, scratch, 90).rebuild(
                    descriptor,
                    args.descriptor_sha256,
                    args.rebuild_output,
                    protected_root=args.descriptor.parent,
                )
                scope = ServingScope(args.target_run, args.pipeline_version)
                body, reports = publish_run(
                    descriptor,
                    args.descriptor_sha256,
                    archive,
                    scope,
                    http_config(config["writer"]),
                    reader,
                    receipt_store("seal_writer"),
                    batch_size=args.batch_size,
                )
                key = (
                    scope.dataset_run_id
                    + "/"
                    + scope.pipeline_version
                    + "/complete.json"
                )
                observed = receipt_store("seal_reader").read(
                    key, digest(body), len(body)
                )
                admitted = admitted_report(
                    observed,
                    digest(body),
                    descriptor,
                    args.descriptor_sha256,
                    archive,
                    reader,
                )
                result: dict[str, object] = {
                    "scope": asdict(scope),
                    "rebuild": rebuilt,
                    "seal_key": key,
                    "seal_sha256": digest(body),
                    "reports": reports,
                    "admitted_report": admitted,
                }
            elif args.mode == "seal-existing":
                require(args.target_run is not None, "missing_target_run")
                scope = ServingScope(args.target_run, args.pipeline_version)
                body, reports = seal_existing(
                    descriptor,
                    args.descriptor_sha256,
                    archive,
                    scope,
                    reader,
                    receipt_store("seal_writer"),
                )
                key = (
                    scope.dataset_run_id
                    + "/"
                    + scope.pipeline_version
                    + "/complete.json"
                )
                observed = receipt_store("seal_reader").read(
                    key, digest(body), len(body)
                )
                result = {
                    "scope": asdict(scope),
                    "seal_key": key,
                    "seal_sha256": digest(body),
                    "reports": reports,
                    "database_access": "select_only",
                    "admitted_report": admitted_report(
                        observed,
                        digest(body),
                        descriptor,
                        args.descriptor_sha256,
                        archive,
                        reader,
                    ),
                }
            else:
                require(
                    args.seal_key is not None and args.seal_sha256 is not None,
                    "missing_seal_arguments",
                )
                fetched_seal = receipt_store("seal_reader").lookup(args.seal_key)
                require(fetched_seal is not None, "run_not_sealed")
                result = admitted_report(
                    cast(bytes, fetched_seal),
                    args.seal_sha256,
                    descriptor,
                    args.descriptor_sha256,
                    archive,
                    reader,
                )
            # No success file is created for refusals or ambiguous writes.
            with args.output.open("xb") as stream:
                stream.write(
                    (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
                )
        print(json.dumps({"complete": True, "output": str(args.output)}))
        return 0
    except (ArchiveError, StoreError, SinkError, ServingError) as error:
        print(json.dumps({"error": error.category}))
    except (ValueError, OSError, TypeError, KeyError, UnicodeError, RecursionError):
        print(json.dumps({"error": "run_admission_refused"}))
    finally:
        for store in stores:
            store.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
