"""Full lab recipe placement, credential separation and safe source transfer."""

import json
import signal
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.continuous.generate import prepare as prepare_fixture
from runtime.continuous.generate import publish
from runtime.continuous.prepare_split import prepare
from runtime.continuous.split_credentials import role_configs
from runtime.continuous.split_transfer import (
    allowed_source,
    export_bundle,
    export_source,
    verify_bundle,
    verify_source,
)


def test_runtime_recipes_keep_flink_state_local_and_storage_off_laptop(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    prepare(bundle, "192.168.50.10", "192.168.50.20", "fleet-split-test")
    verify_bundle(bundle)
    laptop = json.loads((bundle / "laptop/runtime.json").read_text())
    pc = json.loads((bundle / "pc/runtime.json").read_text())
    manifest = json.loads((bundle / "manifest.json").read_text())
    for host, recipe in (("pc", pc), ("laptop", laptop)):
        base = json.loads((bundle / host / "compose.json").read_text())
        declared = set(manifest["images"][host])
        actual = {
            service["image"]
            for service in [*recipe["services"].values(), *base["services"].values()]
        }
        assert declared == actual
    assert set(laptop["services"]) == {"jobmanager", "taskmanager", "submit"}
    assert set(pc["services"]) == {"archive", "serving"}
    assert laptop["services"]["taskmanager"]["pids_limit"] == 4096
    assert laptop["services"]["taskmanager"]["environment"]["FLEET_TASK_SLOTS"] == "18"
    assert laptop["services"]["submit"]["profiles"] == ["submit"]
    assert "/job/processing.json" in laptop["services"]["submit"]["command"]
    for recipe in (laptop, pc):
        for service in recipe["services"].values():
            assert service["pull_policy"] == "never"
            assert "@sha256:" in service["image"]
            assert all(
                port.startswith("127.0.0.1:") for port in service.get("ports", [])
            )
            for mount in service["volumes"]:
                if isinstance(mount, dict):
                    assert mount["read_only"]
                    assert mount["bind"]["create_host_path"] is False
    packaged = tmp_path / "packaged"
    # An extra private file must not be captured by an inventory-based ZIP.
    (bundle / "private.json").write_text('{"password":"sentinel"}')
    export_bundle(bundle, packaged)
    with zipfile.ZipFile(packaged / "configuration.zip") as archive:
        assert "private.json" not in archive.namelist()
    (bundle / "laptop/runtime.json").write_text("{}")
    with pytest.raises(ValueError, match="split_bundle_checksum"):
        verify_bundle(bundle)


def test_role_configs_bind_new_cluster_and_do_not_transfer_storage_secrets(
    tmp_path: Path,
) -> None:
    bundle, private = tmp_path / "bundle", tmp_path / "private"
    prepare(bundle, "192.168.50.10", "192.168.50.20", "fleet-split-test")
    manifest = json.loads((bundle / "manifest.json").read_text())
    connection = json.loads((bundle / "client-connection.example.json").read_text())
    private.mkdir()
    (private / "binding.json").write_text(
        json.dumps({k: manifest[k] for k in ("cluster_id", "bootstrap", "run_id")})
    )
    processing = {
        "run_id": manifest["run_id"],
        "bootstrap": manifest["bootstrap"],
        "input_topic": "input",
        "output_topic": "output",
        "processing_group": "processing",
        "source": {"cluster_id": manifest["cluster_id"]},
        "source_logs": {"vehicle": "source"},
        "timestamp_min": "start",
        "timestamp_max": "end",
        "kafka_connection": connection,
    }
    config = {
        **processing,
        "archive_plan": {},
        "archive_group": "archive",
        "storage": {"secret_key": "storage-sentinel"},
        "output_source": {},
        "serving_group": "serving",
        "writer": {"password": "writer-sentinel"},
        "reader": {"password": "reader-sentinel"},
        "live_source": {},
        "reader_token": "live-reader",
        "writer_token": "live-writer",
    }
    initialized = private / "initialized.json"
    initialized.write_text(json.dumps(config))
    processing.pop("bootstrap")
    initialized.with_suffix(".processing.json").write_text(json.dumps(processing))
    output = tmp_path / "roles"
    role_configs(
        bundle,
        private,
        initialized,
        output,
        "/home/other/private/laptop",
        "/home/pc/private/pc",
    )
    for path in (output / "laptop").rglob("*.json"):
        text = path.read_text()
        assert "storage-sentinel" not in text
        assert "writer-sentinel" not in text
        assert "reader-sentinel" not in text
    publisher = json.loads((output / "laptop/publisher.json").read_text())
    assert publisher["kafka_connection"]["native_tls"]["key_file"] == (
        "/home/other/private/laptop/roles/publisher/client.key"
    )
    assert set((output / "laptop/job").iterdir()) == {
        output / "laptop/job/processing.json"
    }
    config["source"]["cluster_id"] = "different"
    initialized.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="split_role_cluster_binding"):
        role_configs(
            bundle,
            private,
            initialized,
            tmp_path / "refused",
            "/private/laptop",
            "/private/pc",
        )
    assert not (tmp_path / "refused").exists()


def test_source_zip_includes_current_untracked_source_but_excludes_private_data(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    files = {
        "README.md": b"source",
        "CONTRIBUTING.md": b"development guide",
        "compose.yaml": b"services: {}\n",
        "runtime/new.py": b"print('new')\n",
        "AGENTS.md": b"local working agreements",
        "docs/AGENTS.md": b"local documentation instructions",
        "CLAUDE.md": b"local tool instructions",
        "GEMINI.md": b"local tool instructions",
        ".agents/skills/example/SKILL.md": b"local skill",
        ".codex/config.toml": b"local configuration",
        ".github/copilot-instructions.md": b"local instructions",
        ".github/instructions/review.instructions.md": b"local instructions",
        ".github/prompts/review.prompt.md": b"local prompt",
        "runtime/continuous/live.html": b"<html>live</html>",
        "runtime/continuous/link_watch.html": b"<html>links</html>",
        "runtime/continuous/position_map.html": b"<html>map</html>",
        "runtime/continuous/mavlink_live.html": b"<html>observer</html>",
        "runtime/kafka/kafka-probe.properties": b"node.id=1\n",
        "runtime/pyflink/container/Dockerfile.backport": b"FROM pinned-base\n",
        "LICENSE": b"MIT License\n",
        "docs/assets/telemetry.png": b"public synthetic screenshot",
        "docs/mvp-target.png": b"public architecture diagram",
        "runtime/private.png": b"private screenshot",
        "runtime/private.html": b"secret",
        "runtime/private.json": b"secret",
        ".local-discovery/state.json": b"retained",
        "runtime/key.p12": b"key",
        "runtime/client.key": b"key",
        ".env": b"password",
    }
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    listing = ("\0".join(files) + "\0").encode()
    with patch(
        "runtime.continuous.split_transfer.subprocess.check_output",
        return_value=listing,
    ):
        export_source(tmp_path / "export", root)
    verify_source(tmp_path / "export")
    with zipfile.ZipFile(tmp_path / "export/source.zip") as archive:
        assert set(archive.namelist()) == {
            "README.md",
            "CONTRIBUTING.md",
            "compose.yaml",
            "runtime/new.py",
            "runtime/continuous/live.html",
            "runtime/continuous/link_watch.html",
            "runtime/continuous/position_map.html",
            "runtime/continuous/mavlink_live.html",
            "runtime/kafka/kafka-probe.properties",
            "runtime/pyflink/container/Dockerfile.backport",
            "LICENSE",
            "docs/assets/telemetry.png",
            "docs/mvp-target.png",
        }
    assert allowed_source("runtime/continuous/split_credentials.py")
    with pytest.raises(ValueError, match="split_unsafe_relative_path"):
        allowed_source("../outside.py")
    with (tmp_path / "export/source.zip").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="split_source_archive_checksum"):
        verify_source(tmp_path / "export")


def test_small_transfer_fixture_covers_all_partition_lanes(tmp_path: Path) -> None:
    from hashlib import sha256

    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 64, 64, "split-test")
    plan = json.loads((fixture / "plan.json").read_text())
    assert plan["records"] + plan["tail_measurements"] == 128
    assert {
        int(sha256(vehicle.encode()).hexdigest(), 16) % 18
        for vehicle in plan["source_logs"]
    } == set(range(18))
    assert (
        sum(
            len(json.loads(path.read_text())["records"])
            for path in fixture.glob("stream-vehicle-*.json")
        )
        == 128
    )


def test_five_hz_fixture_preserves_measurement_time_and_closing_tail(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 300, 100, "split-five-hz", 200_000)
    plan = json.loads((fixture / "plan.json").read_text())
    rows = json.loads((fixture / "stream-vehicle-0000.json").read_text())["records"]
    assert plan["interval_us"] == 200_000
    assert [row["timestamp_us"] for row in rows] == [0, 200_000, 400_000, 20_600_000]
    assert plan["timestamp_max"] == "2026-01-01T12:00:20.600000Z"


def test_publisher_refuses_interval_that_disagrees_with_source(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 300, 100, "split-five-hz", 200_000)
    plan_path = fixture / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan["interval_us"] = 1_000_000
    plan_path.write_text(json.dumps(plan))
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "run_id": "split-five-hz",
                "bootstrap": "x",
                "source": {"cluster_id": "c"},
                "input_topic": "input",
            }
        )
    )
    kafka = MagicMock()
    kafka.describe.return_value = {"cluster_id": "c"}
    kafka.positions.return_value = [object()]
    kafka.consumer.return_value.get_watermark_offsets.return_value = (0, 0)
    with patch("runtime.continuous.generate.Kafka", return_value=kafka):
        with pytest.raises(ValueError, match="continuous_native_plan_mismatch"):
            publish(config_path, fixture, tmp_path / "ledger.jsonl", 10_000)
    kafka.sdk.Producer.return_value.produce.assert_not_called()


@pytest.mark.parametrize("signal_during_flush", [False, True])
def test_publisher_flushes_acknowledgements_on_sigterm(
    tmp_path: Path, signal_during_flush: bool
) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 300, 100, "split-five-hz", 200_000)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "run_id": "split-five-hz",
                "bootstrap": "x",
                "source": {"cluster_id": "c"},
                "input_topic": "input",
            }
        )
    )
    kafka = MagicMock()
    kafka.describe.return_value = {"cluster_id": "c"}
    kafka.positions.return_value = [object()]
    kafka.consumer.return_value.get_watermark_offsets.return_value = (0, 0)
    producer = kafka.sdk.Producer.return_value
    message = MagicMock()
    message.partition.return_value = 0
    message.offset.return_value = 0
    pending = []

    def produce(*args: object, **kwargs: object) -> None:
        pending.append(kwargs["on_delivery"])
        if not signal_during_flush:
            handler = signal.getsignal(signal.SIGTERM)
            assert callable(handler)
            handler(signal.SIGTERM, None)

    def flush(timeout: float) -> int:
        assert 0 < timeout <= 1
        if signal_during_flush:
            handler = signal.getsignal(signal.SIGTERM)
            assert callable(handler)
            handler(signal.SIGTERM, None)
        for callback in pending:
            assert callable(callback)
            callback(None, message)
        return 0

    producer.produce.side_effect = produce
    producer.flush.side_effect = flush
    ledger = tmp_path / "ledger.jsonl"
    with patch("runtime.continuous.generate.Kafka", return_value=kafka):
        with pytest.raises(InterruptedError, match="continuous_publish_interrupted"):
            publish(config_path, fixture, ledger, 10_000)
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    summary = json.loads(ledger.with_suffix(".summary.json").read_text())
    expected = 400 if signal_during_flush else 1
    assert len(rows) == summary["attempted"] == summary["acknowledged"] == expected
    assert summary["interrupted"] is True
    assert summary["unconfirmed"] == 0
