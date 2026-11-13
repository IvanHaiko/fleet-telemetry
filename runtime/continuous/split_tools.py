"""Offline two-host setup operations; never start services or publish data."""

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path

from runtime.continuous.prepare import ROOT
from runtime.continuous.split_credentials import provision, role_configs
from runtime.continuous.split_transfer import (
    export_bundle,
    export_source,
    verify_bundle,
    verify_source,
)
from telemetry.kafka_compat import require_uuid_boundary


def main() -> None:
    """Run explicit certificate, source and configuration preparation steps."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    certs = sub.add_parser("credentials")
    certs.add_argument("--bundle", type=Path, required=True)
    certs.add_argument("--directory", type=Path, required=True)
    certs.add_argument("--keytool", type=Path, required=True)
    certs.add_argument("--pc-private-root", required=True)
    roles = sub.add_parser("configs")
    roles.add_argument("--bundle", type=Path, required=True)
    roles.add_argument("--private", type=Path, required=True)
    roles.add_argument("--initialized", type=Path, required=True)
    roles.add_argument("--directory", type=Path, required=True)
    roles.add_argument("--laptop-private-root", required=True)
    roles.add_argument("--pc-private-root", required=True)
    source = sub.add_parser("export-source")
    source.add_argument("--directory", type=Path, required=True)
    config_zip = sub.add_parser("export-bundle")
    config_zip.add_argument("--bundle", type=Path, required=True)
    config_zip.add_argument("--directory", type=Path, required=True)
    check_source = sub.add_parser("verify-source")
    check_source.add_argument("--directory", type=Path, required=True)
    check_bundle = sub.add_parser("verify-bundle")
    check_bundle.add_argument("--directory", type=Path, required=True)
    runtime = sub.add_parser("check-runtime")
    runtime.add_argument("--host", choices=("pc", "laptop"), required=True)
    options = parser.parse_args()
    if options.action == "credentials":
        verify_bundle(options.bundle)
        provision(
            options.bundle, options.directory, options.keytool, options.pc_private_root
        )
    elif options.action == "configs":
        verify_bundle(options.bundle)
        role_configs(
            options.bundle,
            options.private,
            options.initialized,
            options.directory,
            options.laptop_private_root,
            options.pc_private_root,
        )
    elif options.action == "export-source":
        export_source(options.directory)
    elif options.action == "export-bundle":
        export_bundle(options.bundle, options.directory)
    elif options.action == "verify-source":
        verify_source(options.directory)
    elif options.action == "check-runtime":
        require_uuid_boundary()
        if sys.platform != "linux":
            raise ValueError("split_workers_require_linux")
        versions = {"confluent-kafka": "2.16.0"}
        if options.host == "pc":
            for line in (
                (ROOT / "runtime/s3/requirements.lock").read_text().splitlines()
            ):
                name, version = line.split(" --hash=", 1)[0].split("==", 1)
                versions[name] = version
        for name, expected in versions.items():
            if importlib.metadata.version(name) != expected:
                raise ValueError("split_worker_version")
        print(json.dumps({"python": sys.version.split()[0], "packages": versions}))
    else:
        verify_bundle(options.directory)


if __name__ == "__main__":
    main()
