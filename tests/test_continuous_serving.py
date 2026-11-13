"""Ambiguous serving requests must retain bytes and bound retries."""

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux worker runtime")


def test_ambiguous_insert_retries_identical_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runtime.clickhouse.transport import HttpConfig
    from runtime.continuous import serve
    from telemetry.serving_sink import SinkError

    calls: list[tuple[bytes, bool, dict[str, str] | None]] = []
    body = b'{"source_offset":17}\n'
    params = {"database": "test_run"}

    def request(
        config: HttpConfig,
        sql: str,
        payload: bytes,
        *,
        write: bool = False,
        parameters: dict[str, str] | None = None,
    ) -> bytes:
        calls.append((payload, write, parameters))
        if len(calls) == 1:
            raise SinkError("write_ambiguous", "write")
        return b""

    monkeypatch.setattr(serve, "_request", request)
    monkeypatch.setattr("runtime.continuous.serve.time.sleep", lambda delay: None)
    serve.request_with_retry(
        HttpConfig(8123, "test_run", "writer", "synthetic"),
        "INSERT",
        body,
        write=True,
        parameters=params,
    )
    assert calls == [(body, True, params), (body, True, params)]


@pytest.mark.parametrize(
    ("category", "attempts"), [("sink_unavailable", 4), ("permission_denied", 1)]
)
def test_retry_exhaustion_and_permission_refusal(
    monkeypatch: pytest.MonkeyPatch, category: str, attempts: int
) -> None:
    from runtime.clickhouse.transport import HttpConfig
    from runtime.continuous import serve
    from telemetry.serving_sink import SinkError

    seen = 0

    def request(*args: object, **kwargs: object) -> bytes:
        nonlocal seen
        seen += 1
        raise SinkError(category, "read")

    monkeypatch.setattr(serve, "_request", request)
    monkeypatch.setattr("runtime.continuous.serve.time.sleep", lambda delay: None)
    with pytest.raises(SinkError, match=category):
        serve.request_with_retry(
            HttpConfig(8123, "test_run", "reader", "synthetic"), "SELECT", b""
        )
    assert seen == attempts
