"""Snapshot denominators, absent-data refusal and actual HTTP fault visibility."""

import json
import os
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

import pytest

from telemetry.observability import MAX_BYTES, collect, make_server
from telemetry_metrics import metrics_record


def capture(path: Path) -> None:
    records = [
        metrics_record("producer_retry", "callback", {"acknowledged_records": 1}),
        metrics_record(
            "producer_retry",
            "completed",
            {"acknowledged_records": 3, "duration_seconds": 0.5},
        ),
        metrics_record(
            "consumer", "completed", {"captured_lag_records": 2, "observed_records": 3}
        ),
    ]
    path.write_text("\n".join(json.dumps(row) for row in records) + "\n")


def test_latest_snapshot_preserves_denominators_without_callback_sum(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capture.jsonl"
    capture(path)
    body, reason = collect(path, 300)
    assert reason == "ok"
    assert (
        'acknowledged_records{operation="producer_retry",event="completed"} 3\n' in body
    )
    assert (
        'duration_seconds{operation="producer_retry",event="completed"} 0.5\n' in body
    )
    assert 'captured_lag_records{operation="consumer",event="completed"} 2\n' in body
    assert "callback" not in body
    assert "# TYPE fleet_m2_snapshot_acknowledged_records gauge\n" in body
    assert body.endswith("\n")

    with path.open("a") as stream:
        stream.write(
            json.dumps(
                metrics_record("producer_retry", "failed", {"pending_records": 1})
            )
            + "\n"
        )
    body, reason = collect(path, 300)
    assert reason == "ok"  # Valid instrumentation can describe a failed operation.
    assert 'pending_records{operation="producer_retry",event="failed"} 1\n' in body
    assert "acknowledged_records" not in body  # No stale fields or invented zeros.


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"native diagnostic\n", "capture_empty"),
        (b'{"metrics_version":\n', "invalid_metric_json"),
        (b'{"metrics_version":', "capture_incomplete"),
        (b"\xff\n", "capture_encoding"),
        (b"x" * (MAX_BYTES + 1), "capture_too_large"),
        (
            (
                json.dumps(
                    metrics_record(
                        "consumer", "completed", {"observed_records": 10**400}
                    )
                )
                + "\n"
            ).encode(),
            "capture_numeric_overflow",
        ),
    ],
    ids=["empty", "malformed", "partial", "encoding", "oversize", "overflow"],
)
def test_bad_capture_has_no_source_samples(
    tmp_path: Path, content: bytes, reason: str
) -> None:
    path = tmp_path / "capture.jsonl"
    path.write_bytes(content)
    body, actual = collect(path, 300)
    assert actual == reason
    assert "fleet_capture_success 0\n" in body
    assert "fleet_m2_snapshot_" not in body


def test_stale_future_and_missing_capture_are_unknown_not_zero(tmp_path: Path) -> None:
    path = tmp_path / "capture.jsonl"
    capture(path)
    os.utime(path, (1, 1))
    body, reason = collect(path, 300)
    assert reason == "capture_stale"
    assert "fleet_m2_snapshot_" not in body
    os.utime(path, (10**10, 10**10))
    body, reason = collect(path, 300)
    assert reason == "capture_clock_error"
    assert "fleet_capture_age_seconds" not in body
    path.unlink()
    assert collect(path, 300)[1] == "capture_unavailable"


def test_real_http_fault_and_repair_have_safe_cause_logs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "private-vehicle-secret.jsonl"
    capture(path)
    with make_server(path, 300, 0) as server:
        assert server.server_address[0] == "127.0.0.1"
        url = f"http://127.0.0.1:{server.server_port}/metrics"
        for healthy in (True, False, True):
            if healthy:
                capture(path)
            else:
                path.write_text('{"metrics_version":"private-payload-secret"}\n')
            thread = Thread(target=server.handle_request)
            thread.start()
            try:
                with urlopen(url, timeout=3) as response:
                    body = response.read().decode()
                    assert response.status == 200
                    assert "version=0.0.4" in response.headers["Content-Type"]
                assert f"fleet_capture_success {int(healthy)}\n" in body
                assert ("fleet_m2_snapshot_" in body) == healthy
            finally:
                thread.join(timeout=3)
            assert not thread.is_alive()
    logs = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert logs == [
        {"event": "metrics_capture", "reason": reason}
        for reason in ("ok", "invalid_metric_shape", "ok")
    ]
    assert "secret" not in json.dumps(logs)
