"""Live loss deadlines must not depend on input, replay or event-time progress."""

import json
import threading
import time
from http.client import HTTPConnection

import pytest

from runtime.continuous.link_watch import Server
from telemetry.link_watch import LinkWatch


def beat(
    vehicle: str = "drone-1", sequence: int = 0, stamp: int = 100_000
) -> dict[str, object]:
    return {
        "format_version": "live-heartbeat-v1",
        "receiver_epoch": "epoch-1",
        "vehicle_id": vehicle,
        "sequence": sequence,
        "gateway_received_unix_ms": stamp,
    }


def test_silence_replay_and_monitor_pause() -> None:
    watch = LinkWatch(["drone-1", "drone-2"], "epoch-1", 0)
    watch.heartbeat(beat(), 0, 100_000)
    assert watch.tick(0)[0]["status"] == "connected"
    for step in range(1, 30):
        watch.tick(step / 10)
    for row in (
        beat(),
        beat(sequence=1, stamp=98_000),
        beat(sequence=1, stamp=101_000),
        {**beat(sequence=1), "receiver_epoch": "previous-boot"},
        {**beat(sequence=1), "format_version": "canonical-event-v1"},
        beat(vehicle="unregistered"),
        beat(sequence=True),
    ):
        with pytest.raises(ValueError):
            watch.heartbeat(row, 2.9, 100_000)
    assert len(watch.links) == 2
    assert watch.tick(3.0)[0]["status"] == "lost"
    assert watch.links["drone-2"].status == "unknown"
    watch.heartbeat(beat(sequence=1, stamp=103_000), 3.1, 103_000)
    assert watch.tick(3.1)[0]["status"] == "connected"
    assert watch.snapshot(4.0)["monitor_ok"] is False
    assert watch.tick(4.0)[0]["status"] == "unknown"
    # An old sequence is still refused after monitor delay.
    with pytest.raises(ValueError, match="replayed"):
        watch.heartbeat(beat(sequence=1, stamp=103_000), 4.0, 103_000)
    watch.heartbeat(beat(sequence=2, stamp=104_000), 4.1, 104_000)
    assert watch.tick(4.1)[0]["status"] == "connected"
    # Wall-clock changes after admission do not change the monotonic deadline.
    for step in range(42, 72):
        watch.tick(step / 10)
    assert watch.links["drone-1"].status == "lost"
    assert "drone-" not in watch.metrics(7.1).decode()
    restarted = LinkWatch(["drone-1"], "epoch-2", 8)
    with pytest.raises(ValueError, match="epoch"):
        restarted.heartbeat(beat(sequence=3, stamp=108_000), 8, 108_000)


def test_gateway_delay_consumes_deadline_and_state_is_fixed() -> None:
    with pytest.raises(ValueError):
        LinkWatch([f"v{i}" for i in range(1025)], "epoch-1", 0)
    watch = LinkWatch([f"v{i}" for i in range(128)], "epoch-1", 0)
    for sequence in range(100):
        for vehicle in watch.links:
            watch.heartbeat(beat(vehicle, sequence, 100_000 + sequence), 0, 100_100)
    assert len(watch.links) == 128
    assert all(link.sequence == 99 for link in watch.links.values())
    for step in range(31):
        watch.tick(step / 10)
    assert all(link.status == "lost" for link in watch.links.values())
    delayed = LinkWatch(["drone-1"], "epoch-1", 0)
    delayed.heartbeat(beat(), 0, 101_000)
    for step in range(21):
        transitions = delayed.tick(step / 10)
    assert transitions[0]["status"] == "lost"  # Already one second old at receipt.


def test_real_http_loss_recovery_and_unavailable_monitor() -> None:
    watch = LinkWatch(
        ["drone-1", "drone-2"], "epoch-1", time.monotonic(), timeout=1, max_age=0.5
    )
    server = Server(("127.0.0.1", 0), watch, "w" * 32, "r" * 32)
    stop = threading.Event()
    monitor = threading.Thread(target=server.monitor, args=(stop,))
    serving = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}
    )
    monitor.start()
    serving.start()

    def request(
        method: str, path: str, token: str, body: bytes = b""
    ) -> tuple[int, bytes]:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=1)
        try:
            connection.request(method, path, body, {"Authorization": "Bearer " + token})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    try:
        assert request("GET", "/v1/links", "w" * 32)[0] == 401
        assert request("POST", "/v1/heartbeat", "r" * 32, b"{}")[0] == 401
        assert request("POST", "/v1/heartbeat", "w" * 32, b"x" * 1025)[0] == 400
        assert request("GET", "/v1/session", "w" * 32)[0] == 200
        payload = json.dumps(beat(stamp=time.time_ns() // 1_000_000)).encode()
        start = time.monotonic()
        assert request("POST", "/v1/heartbeat", "w" * 32, payload)[0] == 202
        # No more input arrives; the monitor and API still expose the timeout.
        deadline = start + 2
        while time.monotonic() < deadline:
            _, raw = request("GET", "/v1/links", "r" * 32)
            if json.loads(raw)["vehicles"][0]["status"] == "lost":
                break
            time.sleep(0.02)
        else:
            pytest.fail("silence deadline did not fire")
        assert time.monotonic() - start < 1.5
        assert request("POST", "/v1/heartbeat", "w" * 32, payload)[0] == 400
        payload = json.dumps(
            beat(sequence=1, stamp=time.time_ns() // 1_000_000)
        ).encode()
        assert request("POST", "/v1/heartbeat", "w" * 32, payload)[0] == 202
        assert (
            json.loads(request("GET", "/v1/links", "r" * 32)[1])["vehicles"][0][
                "status"
            ]
            == "connected"
        )
        assert b"drone-" not in request("GET", "/metrics", "r" * 32)[1]
        stop.set()
        monitor.join(timeout=1)
        time.sleep(0.55)
        snapshot = json.loads(request("GET", "/v1/links", "r" * 32)[1])
        assert snapshot["monitor_ok"] is False
        assert snapshot["vehicles"][0]["status"] == "unknown"
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        serving.join(timeout=1)
        monitor.join(timeout=1)
