"""Issue private lab TLS material with installed OpenSSL/keytool; no networking."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import cast

from runtime.continuous.split_runtime import write_json
from telemetry.continuous_connection import parse_connection

ROLES = {
    "pc": ("initializer", "archive", "serving", "metrics"),
    "laptop": ("publisher", "live", "flink"),
}


def private_json(path: Path, value: object) -> None:
    """Create a private document, never overwrite an earlier scope."""
    write_json(path, value)
    path.chmod(0o600)


def provision(bundle: Path, target: Path, keytool: Path, pc_private_root: str) -> None:
    """Generate fresh certificates and storage credentials for one frozen bundle."""
    if os.name != "posix":
        raise ValueError("split_credentials_require_linux_permissions")
    openssl = shutil.which("openssl")
    if openssl is None or not keytool.is_file():
        raise ValueError("existing_openssl_and_jdk_keytool_required")
    manifest = json.loads((bundle / "manifest.json").read_text())
    template = json.loads((bundle / "client-connection.example.json").read_text())
    parse_connection(template)
    if template["endpoints"] != manifest["bootstrap"].split(","):
        raise ValueError("split_credential_endpoint_binding")
    target = target.resolve()
    if target.is_relative_to(bundle.resolve()):
        raise ValueError("private_material_must_be_outside_bundle")
    previous_mask = os.umask(0o077)
    try:
        target.mkdir(mode=0o700, exist_ok=False)
        authority = target / "authority"
        authority.mkdir()

        def run(arguments: list[str], password: str | None = None) -> None:
            env = dict(os.environ)
            if password is not None:
                env["FLEET_CERT_PASSWORD"] = password
            subprocess.run(
                arguments,
                check=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=30,
            )

        ca, ca_key = authority / "ca.pem", authority / "ca.key"
        run(
            [
                openssl,
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-sha256",
                "-days",
                "30",
                "-subj",
                "/CN=Fleet private laboratory CA",
                "-addext",
                "basicConstraints=critical,CA:TRUE",
                "-addext",
                "keyUsage=critical,keyCertSign,cRLSign",
                "-keyout",
                str(ca_key),
                "-out",
                str(ca),
            ]
        )

        def issue(directory: Path, name: str, address: str, node: bool) -> None:
            directory.mkdir(parents=True, mode=0o700)
            password = secrets.token_hex(32)
            key, cert, csr = (
                directory / n for n in ("client.key", "client.pem", "request.csr")
            )
            extension = directory / "extensions.cnf"
            extension.write_text(
                "basicConstraints=critical,CA:FALSE\n"
                "keyUsage=critical,digitalSignature,keyEncipherment\n"
                "extendedKeyUsage=serverAuth,clientAuth\n"
                + "subjectAltName=IP:"
                + address
                + "\n",
                encoding="utf8",
            )
            run(
                [
                    openssl,
                    "req",
                    "-new",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-subj",
                    "/CN=" + name,
                    "-keyout",
                    str(key),
                    "-out",
                    str(csr),
                ]
            )
            run(
                [
                    openssl,
                    "x509",
                    "-req",
                    "-in",
                    str(csr),
                    "-CA",
                    str(ca),
                    "-CAkey",
                    str(ca_key),
                    "-set_serial",
                    str(secrets.randbits(128) + 1),
                    "-days",
                    "30",
                    "-sha256",
                    "-extfile",
                    str(extension),
                    "-out",
                    str(cert),
                ]
            )
            run(
                [
                    openssl,
                    "verify",
                    "-CAfile",
                    str(ca),
                    "-verify_ip",
                    address,
                    str(cert),
                ]
            )
            shutil.copyfile(ca, directory / "ca.pem")
            (directory / "passwords.properties").write_text(
                "password=" + password + "\n"
            )
            run(
                [
                    openssl,
                    "pkcs12",
                    "-export",
                    "-in",
                    str(cert),
                    "-inkey",
                    str(key),
                    "-certfile",
                    str(ca),
                    "-name",
                    name,
                    "-out",
                    str(directory / ("kafka.p12" if node else "client.p12")),
                    "-passout",
                    "env:FLEET_CERT_PASSWORD",
                ],
                password,
            )
            run(
                [
                    str(keytool),
                    "-importcert",
                    "-noprompt",
                    "-alias",
                    "lab-ca",
                    "-file",
                    str(ca),
                    "-storetype",
                    "PKCS12",
                    "-keystore",
                    str(directory / "ca.p12"),
                    "-storepass:env",
                    "FLEET_CERT_PASSWORD",
                ],
                password,
            )

        for host, roles in ROLES.items():
            for node, owner in manifest["owners"].items():
                if owner == host:
                    issue(
                        target / host / f"node-{node}",
                        f"node-{node}",
                        manifest["hosts"][host],
                        True,
                    )
            for role in roles:
                issue(
                    target / host / "roles" / role, role, manifest["hosts"][host], False
                )
        password = secrets.token_hex(32)
        storage = {
            role: {
                "access_key": secrets.token_hex(12),
                "secret_key": secrets.token_hex(24),
            }
            for role in ("bootstrap", "writer", "reader")
        }
        native = cast(dict[str, object], template["native_tls"])
        for field, name in (
            ("ca_file", "ca.pem"),
            ("certificate_file", "client.pem"),
            ("key_file", "client.key"),
        ):
            native[field] = str(Path(pc_private_root) / "roles/initializer" / name)
        parse_connection(template)
        private_json(
            target / "pc/initializer.json",
            {
                "cluster_id": manifest["cluster_id"],
                "bootstrap": manifest["bootstrap"],
                "kafka_connection": template,
                "serving_bootstrap": password,
                "writer": secrets.token_hex(32),
                "reader": secrets.token_hex(32),
                "s3": storage,
            },
        )
        private_json(
            target / "pc/s3.json",
            {
                "identities": [
                    {
                        "name": role,
                        "credentials": [
                            {
                                "accessKey": keys["access_key"],
                                "secretKey": keys["secret_key"],
                            }
                        ],
                        "actions": [
                            action
                            if role == "bootstrap"
                            else action + ":fleet-" + manifest["run_id"]
                            for action in {
                                "bootstrap": ["Admin", "Read", "Write", "List"],
                                "writer": ["Read", "Write", "List"],
                                "reader": ["Read", "List"],
                            }[role]
                        ],
                    }
                    for role, keys in storage.items()
                ]
            },
        )
        # Compose reads this file explicitly; it never enters the public bundle.
        (target / "pc/compose.env").write_text("M4_SERVING_PASSWORD=" + password + "\n")
        private_json(
            target / "binding.json",
            {
                "cluster_id": manifest["cluster_id"],
                "bootstrap": manifest["bootstrap"],
                "run_id": manifest["run_id"],
            },
        )
    finally:
        os.umask(previous_mask)


def role_configs(
    bundle: Path,
    private: Path,
    initialized: Path,
    output: Path,
    laptop_private_root: str,
    pc_private_root: str,
) -> None:
    """Separate storage credentials from portable laptop publisher/live configs."""
    manifest = json.loads((bundle / "manifest.json").read_text())
    config = json.loads(initialized.read_text())
    binding = json.loads((private / "binding.json").read_text())
    if (
        any(binding[k] != manifest[k] for k in ("cluster_id", "bootstrap", "run_id"))
        or config["source"]["cluster_id"] != binding["cluster_id"]
        or config["run_id"] != binding["run_id"]
        or config["bootstrap"] != binding["bootstrap"]
    ):
        raise ValueError("split_role_cluster_binding")
    output.mkdir(mode=0o700, exist_ok=False)
    base = {k: config[k] for k in ("run_id", "bootstrap", "kafka_connection")}
    selections = {
        "archive": ("archive_plan", "archive_group", "storage"),
        "serving": ("output_source", "serving_group", "writer", "reader"),
        "metrics": ("source", "reader"),
        "publisher": ("source", "input_topic", "source_logs"),
        "live": ("live_source", "source_logs", "reader_token", "writer_token"),
    }
    for host, roles in ROLES.items():
        (output / host).mkdir(mode=0o700)
        for role in roles:
            if role in ("initializer", "flink"):
                continue
            doc = {**base, **{k: config[k] for k in selections[role]}}
            connection = json.loads(json.dumps(doc["kafka_connection"]))
            host_root = PurePosixPath(
                pc_private_root if host == "pc" else laptop_private_root
            )
            connection["native_tls"] = {
                field: str(host_root / "roles" / role / name)
                for field, name in (
                    ("ca_file", "ca.pem"),
                    ("certificate_file", "client.pem"),
                    ("key_file", "client.key"),
                )
            }
            doc["kafka_connection"] = connection
            parse_connection(connection)
            private_json(output / host / (role + ".json"), doc)
    processing = json.loads(initialized.with_suffix(".processing.json").read_text())
    required = (
        "run_id",
        "input_topic",
        "output_topic",
        "processing_group",
        "source",
        "source_logs",
        "timestamp_min",
        "timestamp_max",
        "kafka_connection",
    )
    allowed = set(required) | {
        "live_output_topic",
        "partition_time_jar",
        "battery_parallelism",
    }
    if set(processing) - allowed or any(
        processing.get(k) != config[k] for k in required
    ):
        raise ValueError("split_processing_config_binding")
    processing["kafka_connection"]["native_tls"] = {
        "ca_file": "/run/secrets/flink/ca.pem",
        "certificate_file": "/run/secrets/flink/client.pem",
        "key_file": "/run/secrets/flink/client.key",
    }
    (output / "laptop/job").mkdir(mode=0o700)
    # Flink's bind contains only processing settings, not publisher/live tokens.
    private_json(output / "laptop/job/processing.json", processing)
