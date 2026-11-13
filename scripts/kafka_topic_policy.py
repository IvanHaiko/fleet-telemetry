"""Non-expiring finite fixture topics and conservative local storage admission."""

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import AdminClient
from confluent_kafka.admin._config import ConfigResource
from confluent_kafka.admin._resource import ResourceType
from kafka_evidence import BrokerQuarantined, require_mutable_profile

GiB = 1024**3
MAX_STORAGE_BYTES = 50 * GiB
MIN_FREE_BYTES = GiB
DATA_PATH = "/var/lib/kafka/data"


class FixturePolicyError(ValueError):
    """A safe refusal before fixture creation or publication."""


def require(condition: bool, reason: str) -> None:
    """Keep admission checks enabled under optimized Python."""
    if not condition:
        raise FixturePolicyError(reason)


def obj(value: object) -> dict[str, object]:
    """Validate untrusted Docker JSON without assuming its structure."""
    require(isinstance(value, dict), "fixture_storage_metadata_invalid")
    mapping = cast(dict[object, object], value)
    require(
        all(isinstance(k, str) for k in mapping), "fixture_storage_metadata_invalid"
    )
    return cast(dict[str, object], mapping)


def command(*args: str) -> str:
    """Bound read-only inspection and avoid exposing Docker diagnostics."""
    try:
        result = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise FixturePolicyError("fixture_storage_inspection_failed") from error
    require(
        result.returncode == 0 and len(result.stdout) <= 64 * 1024,
        "fixture_storage_inspection_failed",
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class Storage:
    """Allocated Kafka-volume bytes and free bytes on its actual filesystem."""

    allocated: int
    free: int


def storage(admin: AdminClient) -> Storage:
    """Match the local endpoint to a running owned container, then read du/df."""
    require(not os.environ.get("DOCKER_HOST"), "fixture_local_engine_required")
    context = command("context", "show")
    endpoint = command(
        "context", "inspect", context, "--format", "{{.Endpoints.docker.Host}}"
    )
    require(
        (context, endpoint)
        in {
            ("desktop-linux", "npipe:////./pipe/dockerDesktopLinuxEngine"),
            ("default", "unix:///var/run/docker.sock"),
        },
        "fixture_local_engine_required",
    )
    container = command(
        "--context", context, "ps", "--filter", "publish=19092", "--format", "{{.ID}}"
    )
    require(
        bool(container) and all(c in "0123456789abcdef" for c in container),
        "fixture_single_broker_required",
    )
    try:
        info = obj(
            json.loads(
                command(
                    "--context", context, "inspect", container, "--format", "{{json .}}"
                )
            )
        )
    except json.JSONDecodeError as error:
        raise FixturePolicyError("fixture_storage_metadata_invalid") from error
    config = obj(info.get("Config"))
    labels = obj(config.get("Labels"))
    project = labels.get("com.docker.compose.project")
    require(isinstance(project, str) and bool(project), "fixture_owner_required")
    try:
        require_mutable_profile(cast(str, project), context)
    except BrokerQuarantined as error:
        raise FixturePolicyError(str(error)) from error
    require(
        labels.get("com.docker.compose.service") == "kafka"
        and obj(info.get("State")).get("Running") is True,
        "fixture_running_broker_required",
    )
    ports = obj(obj(info.get("NetworkSettings")).get("Ports"))
    require(
        ports.get("19092/tcp") == [{"HostIp": "127.0.0.1", "HostPort": "19092"}],
        "fixture_loopback_listener_required",
    )
    mounts = info.get("Mounts")
    require(isinstance(mounts, list), "fixture_storage_metadata_invalid")
    matching = [
        obj(m)
        for m in cast(list[object], mounts)
        if obj(m).get("Destination") == DATA_PATH
    ]
    require(
        len(matching) == 1
        and matching[0].get("Type") == "volume"
        and matching[0].get("Name") == f"{project}_kafka-data"
        and matching[0].get("RW") is True,
        "fixture_owned_volume_required",
    )
    metadata = admin.list_topics(timeout=10)
    require(
        isinstance(metadata.cluster_id, str)
        and bool(metadata.cluster_id)
        and len(metadata.brokers) == 1
        and all(
            b.host == "127.0.0.1" and b.port == 19092 for b in metadata.brokers.values()
        )
        and isinstance(config.get("Env"), list)
        and f"KAFKA_CLUSTER_ID={metadata.cluster_id}"
        in cast(list[object], config["Env"]),
        "fixture_storage_cluster_differs",
    )
    used = command("--context", context, "exec", container, "du", "-sk", DATA_PATH)
    disk = command("--context", context, "exec", container, "df", "-Pk", DATA_PATH)
    try:
        usage = used.split()
        rows = disk.splitlines()
        require(
            len(usage) == 2 and usage[1] == DATA_PATH and len(rows) == 2,
            "fixture_storage_measurement_invalid",
        )
        fields = rows[1].split()
        require(len(fields) == 6, "fixture_storage_measurement_invalid")
        allocated, free, total = (
            int(usage[0]) * 1024,
            int(fields[3]) * 1024,
            int(fields[1]) * 1024,
        )
        require(
            0 <= allocated <= total and 0 <= free <= total and total > 0,
            "fixture_storage_measurement_invalid",
        )
    except (ValueError, IndexError) as error:
        raise FixturePolicyError("fixture_storage_measurement_invalid") from error
    return Storage(allocated, free)


def admit_fixture(
    admin: AdminClient, values: tuple[bytes, ...], keys: tuple[bytes, ...]
) -> None:
    """Admit only the existing three-record profile with spare disk for retries."""
    require(len(values) == len(keys) == 3, "three_event_fixture_required")
    payload = sum(len(v) + len(k) + 1024 for v, k in zip(values, keys, strict=True))
    require(payload <= 64 * 1024**2, "fixture_publication_bound_exceeded")
    # Allow two publication attempts and 64 MiB for topic/index allocation.
    required = 2 * payload + 64 * 1024**2
    measured = storage(admin)
    require(
        measured.allocated + required <= MAX_STORAGE_BYTES,
        "fixture_retained_data_budget_exceeded",
    )
    require(
        measured.free >= required + MIN_FREE_BYTES, "fixture_free_disk_budget_exceeded"
    )
    try:
        workspace_free = shutil.disk_usage(Path(__file__).resolve().parents[1]).free
    except OSError as error:
        raise FixturePolicyError("fixture_workspace_disk_measurement_failed") from error
    require(
        workspace_free >= required + MIN_FREE_BYTES,
        "fixture_workspace_free_disk_budget_exceeded",
    )


def topic_config() -> dict[str, str]:
    """Return explicit overrides for a fresh ordinary finite fixture topic."""
    return {
        "cleanup.policy": "delete",
        "retention.ms": "-1",
        "retention.bytes": "-1",
        "segment.bytes": "1048576",
        "min.insync.replicas": "1",
    }


def verify_topic_config(admin: AdminClient, topic: str) -> None:
    """Read effective values before sending records; retry only creation visibility."""
    resource = ConfigResource(ResourceType.TOPIC, topic)
    deadline = time.monotonic() + 15
    while True:
        remaining = deadline - time.monotonic()
        require(remaining > 0, "fixture_topic_config_deadline")
        try:
            actual = admin.describe_configs(
                [resource], request_timeout=min(10, remaining)
            )[resource].result(timeout=min(12, remaining))
            break
        except KafkaException as error:
            if (
                not error.args
                or not isinstance(error.args[0], KafkaError)
                or error.args[0].code() != KafkaError.UNKNOWN_TOPIC_OR_PART
            ):
                raise
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
    require(
        all(
            name in actual and actual[name].value == value
            for name, value in topic_config().items()
        ),
        "fixture_topic_config_differs",
    )
