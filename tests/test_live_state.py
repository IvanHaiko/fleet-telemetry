"""At-least-once Flink output must not duplicate or regress displayed state."""

import json
import threading
import time
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from test_reference import SOURCE, event

from runtime.continuous import live as live_runtime
from runtime.continuous.link_watch import Server
from telemetry.link_watch import LinkWatch
from telemetry.live_state import LiveState


def fact(index: int, stamp: str, **changes: object) -> bytes:
    return json.dumps(
        {
            "format_version": "continuous-processing-v1",
            "run_id": "test-run",
            "kind": "event",
            "disposition": "eligible",
            "event": event(index=index, timestamp=stamp),
            "semantic_sha256": str(index),
            "source": {"partition": 0, "offset": index},
            **changes,
        }
    ).encode()


def test_replay_out_of_order_and_conflict_do_not_regress_live_state() -> None:
    state = LiveState("test-run", {"vehicle-a": SOURCE})
    older = fact(0, "1970-01-01T00:00:00.000000Z")
    newer = fact(1, "1970-01-01T00:00:01.000000Z")
    assert state.accept(older, 1000)
    assert state.accept(newer, 2000)
    assert not state.accept(newer, 3000)  # Recovery repeats cannot renew freshness.
    assert not state.accept(older, 4000)
    assert state.values["vehicle-a"]["live_received_unix_ms"] == 2000
    assert state.values["vehicle-a"]["event_id"] == event(index=1)["event_id"]
    for disposition in ("duplicate", "conflict", "late"):
        assert not state.accept(
            fact(2, "1970-01-01T00:00:02.000000Z", disposition=disposition), 5000
        )
    with pytest.raises(ValueError, match="competing"):
        state.accept(
            fact(1, "1970-01-01T00:00:01.000000Z", semantic_sha256="different"), 6000
        )
    assert len(state.values) == 1
    state.ready, state.polled_at = True, 10
    assert state.snapshot(10.1)["collection_ok"]
    assert not state.snapshot(11.1)["collection_ok"]
    state.error = "KafkaException"
    assert not state.snapshot(10.1)["collection_ok"]


def test_live_scope_and_fleet_bound() -> None:
    with pytest.raises(ValueError, match="bound"):
        LiveState("test-run", {str(n): SOURCE for n in range(1025)})
    state = LiveState("test-run", {"different-vehicle": SOURCE})
    body = fact(0, "1970-01-01T00:00:00.000000Z")
    with pytest.raises(ValueError, match="vehicle_scope"):
        state.accept(body, 0)
    with pytest.raises(ValueError, match="fact_scope"):
        state.accept(fact(0, "1970-01-01T00:00:00.000000Z", run_id="other"), 0)
    assert not state.values


def test_freshness_is_monotonic_and_rebuild_does_not_masquerade_as_live() -> None:
    state = LiveState("test-run", {"vehicle-a": SOURCE})
    replayed = fact(0, "1970-01-01T00:00:00.000000Z")
    current = fact(1, "1970-01-01T00:00:01.000000Z")
    state.ready, state.polled_at = True, 10.0
    assert state.accept(replayed, 86_401_000)
    replay = cast(list[dict[str, object]], state.snapshot(10.0)["vehicles"])[0]
    assert replay["event_id"] == state.values["vehicle-a"]["event_id"]
    assert replay["live_age_seconds"] is None
    assert replay["admission_to_live_ms"] is None

    assert state.accept(current, 86_402_500, 10.0)
    assert not state.accept(current, 86_409_000, 12.0)
    state.polled_at = 12.5
    live = cast(list[dict[str, object]], state.snapshot(12.5)["vehicles"])[0]
    assert live["live_age_seconds"] == 2.5
    assert live["admission_to_live_ms"] == 2500
    assert live["live_received_unix_ms"] == 86_402_500
    # A monotonic reversal or a negative wall-clock difference is unknown.
    state.polled_at = 9.0
    reversed_clock = cast(list[dict[str, object]], state.snapshot(9.0)["vehicles"])[0]
    assert reversed_clock["live_age_seconds"] is None
    future = fact(2, "1970-01-01T00:00:02.000000Z")
    assert state.accept(future, 86_399_000, 20.0)
    state.polled_at = 20.4
    future_clock = cast(list[dict[str, object]], state.snapshot(20.5)["vehicles"])[0]
    assert future_clock["admission_to_live_ms"] is None
    state.error = "KafkaException"
    unavailable = cast(list[dict[str, object]], state.snapshot(20.5)["vehicles"])[0]
    assert unavailable["live_age_seconds"] is None
    assert unavailable["admission_to_live_ms"] is None


def test_live_collector_marks_only_records_after_startup_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = {"topic": "live", "cluster_id": "test-cluster"}
    config = {
        "run_id": "test-run",
        "bootstrap": "unused",
        "live_source": source,
        "source_logs": {"vehicle-a": SOURCE},
        "writer_token": "w" * 32,
        "reader_token": "r" * 32,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    finished = threading.Event()
    snapshots: list[dict[str, object]] = []
    owner: list[object] = []

    class FakeServer:
        def __init__(
            self,
            address: object,
            watch: object,
            writer: str,
            reader: str,
            *,
            live: LiveState,
        ) -> None:
            self.live = live
            self.lock = threading.Lock()
            owner.append(self)

        def monitor(self, stop: threading.Event) -> None:
            stop.wait()

        def serve_forever(self, poll_interval: float) -> None:
            assert finished.wait(3), "collector did not finish"

        def server_close(self) -> None:
            pass

    class FakeMessage:
        def __init__(self, offset: int) -> None:
            self.index = offset

        def partition(self) -> int:
            return 0

        def offset(self) -> int:
            return self.index

        def error(self) -> None:
            return None

        def value(self) -> bytes:
            return fact(self.index, f"1970-01-01T00:00:0{self.index}.000000Z")

    class FakeConsumer:
        def __init__(self) -> None:
            self.index = 0

        def get_watermark_offsets(
            self, position: object, timeout: int, cached: bool
        ) -> tuple[int, int]:
            return (0, int(cast(SimpleNamespace, position).partition == 0))

        def assign(self, positions: object) -> None:
            pass

        def poll(self, timeout: float) -> FakeMessage | None:
            if self.index:
                server = cast(FakeServer, owner[0])
                snapshots.append(server.live.snapshot(time.monotonic()))
            if self.index >= 2:
                finished.set()
                time.sleep(0.01)
                return None
            message = FakeMessage(self.index)
            self.index += 1
            return message

        def close(self) -> None:
            pass

    class FakeKafka:
        def __init__(self, *args: object) -> None:
            pass

        def describe(self, topic: str) -> dict[str, str]:
            return source

        def consumer(self, group: str) -> FakeConsumer:
            return FakeConsumer()

        def positions(
            self, topic: str, offsets: dict[str, int]
        ) -> list[SimpleNamespace]:
            return [SimpleNamespace(partition=int(p)) for p in offsets]

    monkeypatch.setattr(live_runtime, "Kafka", FakeKafka)
    monkeypatch.setattr(live_runtime, "Server", FakeServer)
    live_runtime.run(path, 0)
    replay = cast(list[dict[str, object]], snapshots[0]["vehicles"])[0]
    fresh = cast(list[dict[str, object]], snapshots[1]["vehicles"])[0]
    assert replay["live_age_seconds"] is None
    assert fresh["live_age_seconds"] is not None
    assert fresh["event_id"] != replay["event_id"]


def test_telemetry_http_keeps_existing_fields_and_adds_freshness() -> None:
    state = LiveState("test-run", {"vehicle-a": SOURCE})
    assert state.accept(
        fact(0, "1970-01-01T00:00:00.000000Z"), 86_401_000, time.monotonic()
    )
    state.ready, state.polled_at = True, time.monotonic()
    server = Server(
        ("127.0.0.1", 0),
        LinkWatch(["vehicle-a"], "epoch", time.monotonic()),
        "w" * 32,
        "r" * 32,
        live=state,
    )
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}
    )
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=1)
        connection.request(
            "GET", "/v1/telemetry", headers={"Authorization": "Bearer " + "r" * 32}
        )
        response = connection.getresponse()
        assert response.status == 200
        document = json.loads(response.read())
        connection.close()
        assert document["format_version"] == "flink-live-state-v1"
        row = document["vehicles"][0]
        assert all(
            row[key] == value for key, value in state.values["vehicle-a"].items()
        )
        assert 0 <= row["live_age_seconds"] < 1
        assert row["admission_to_live_ms"] == 1000
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)
