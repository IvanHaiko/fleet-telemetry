"""Explicit two-host Kafka endpoints and separate native/JVM TLS properties."""

from __future__ import annotations

import ipaddress
import re
from collections import Counter
from dataclasses import dataclass
from typing import cast

LOCAL_ENDPOINTS = frozenset(f"127.0.0.1:{port}" for port in range(19092, 19098))
LOCAL_FLINK_BOOTSTRAP = "kafka-1:9092,kafka-2:9092,kafka-3:9092"


def _object(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("continuous_connection_fields")
    return cast(dict[str, object], value)


def _path(value: object) -> str:
    # These Linux client/container paths also enter Flink SQL options. Reject
    # traversal, quoting and substitution rather than accepting executable text.
    if (
        not isinstance(value, str)
        or re.fullmatch(r"/[a-zA-Z0-9_./-]+", value) is None
        or any(part in (".", "..", "") for part in value.split("/")[1:])
    ):
        raise ValueError("continuous_tls_absolute_linux_path")
    return value


@dataclass(frozen=True)
class Connection:
    """Validated lab topology; contains paths, never key bytes or passwords."""

    endpoints: tuple[str, ...]
    ca_file: str
    certificate_file: str
    key_file: str
    truststore_file: str
    keystore_file: str
    password_file: str

    def native_properties(self) -> dict[str, str]:
        """Use librdkafka PEM options and mandatory broker identity checks."""
        return {
            "security.protocol": "SSL",
            "ssl.ca.location": self.ca_file,
            "ssl.certificate.location": self.certificate_file,
            "ssl.key.location": self.key_file,
            "enable.ssl.certificate.verification": "true",
            "ssl.endpoint.identification.algorithm": "https",
        }

    def jvm_properties(self) -> dict[str, str]:
        """Keep PKCS12 passwords in the JVM's mounted properties file."""
        secret = "${file:" + self.password_file + ":password}"
        return {
            "security.protocol": "SSL",
            "ssl.endpoint.identification.algorithm": "https",
            "ssl.truststore.type": "PKCS12",
            "ssl.truststore.location": self.truststore_file,
            "ssl.truststore.password": secret,
            "ssl.keystore.type": "PKCS12",
            "ssl.keystore.location": self.keystore_file,
            "ssl.keystore.password": secret,
            "ssl.key.password": secret,
            "config.providers": "file",
            # The pinned Flink SQL connector relocates Kafka's provider classes.
            "config.providers.file.class": (
                "org.apache.flink.kafka.shaded.org.apache.kafka.common.config.provider."
                "FileConfigProvider"
            ),
            "config.providers.file.param.allowed.paths": self.password_file,
        }


def parse_connection(value: object) -> Connection | None:
    """Keep absent settings local; reject incomplete or downgraded split mode."""
    if value is None:
        return None
    config = _object(value, {"format_version", "endpoints", "native_tls", "flink_tls"})
    if config["format_version"] != "two-host-kafka-client-v1":
        raise ValueError("continuous_connection_version")
    raw = config["endpoints"]
    if not isinstance(raw, list) or len(raw) != 6:
        raise ValueError("continuous_connection_six_endpoints")
    endpoints: list[str] = []
    hosts: list[str] = []
    for endpoint in raw:
        if (
            not isinstance(endpoint, str)
            or re.fullmatch(r"[0-9.]+:[0-9]{1,5}", endpoint) is None
        ):
            raise ValueError("continuous_connection_endpoint")
        host, port = endpoint.split(":")
        address = ipaddress.IPv4Address(host)
        if (
            not any(
                address in ipaddress.IPv4Network(network)
                for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
            )
            or not 1024 <= int(port) <= 65535
        ):
            raise ValueError("continuous_connection_private_endpoint")
        endpoints.append(endpoint)
        hosts.append(host)
    if len(set(endpoints)) != 6 or sorted(Counter(hosts).values()) != [3, 3]:
        raise ValueError("continuous_connection_host_placement")
    native = _object(config["native_tls"], {"ca_file", "certificate_file", "key_file"})
    jvm = _object(
        config["flink_tls"], {"truststore_file", "keystore_file", "password_file"}
    )
    return Connection(
        tuple(endpoints),
        *(_path(native[key]) for key in ("ca_file", "certificate_file", "key_file")),
        *(
            _path(jvm[key])
            for key in ("truststore_file", "keystore_file", "password_file")
        ),
    )


def flink_properties(config: dict[str, object]) -> dict[str, str]:
    """Select the legacy Docker route or the validated mutual-TLS route."""
    connection = parse_connection(config.get("kafka_connection"))
    if connection is None:
        return {"bootstrap.servers": LOCAL_FLINK_BOOTSTRAP}
    return {
        "bootstrap.servers": ",".join(connection.endpoints),
        **connection.jvm_properties(),
    }


def source_options(properties: dict[str, str]) -> str:
    """Quote Kafka properties as Flink SQL options, including literal file refs."""
    return ",\n".join(
        "'properties." + key.replace("'", "''") + "'='" + value.replace("'", "''") + "'"
        for key, value in properties.items()
    )
