"""A serving batch must never move the cursor past an unconfirmed member."""

import pytest

from runtime.continuous.recording_batch import MAX_BATCH, ServingBatch
from runtime.continuous.recording_config import Document


def test_failed_write_keeps_cursor_and_success_advances_each_partition() -> None:
    committed: Document = {"0": 5, "1": 0}
    batch = ServingBatch(committed)
    batch.add(0, 5, {"id": "a"})
    batch.add(1, 0, {"id": "b"})
    batch.add(0, 6, {"id": "c"})
    persisted: list[Document] = []

    def lost_reply(outputs: list[Document]) -> None:
        raise ValueError("recording_sql_content_readback")

    with pytest.raises(ValueError):
        batch.flush(lost_reply, lambda: persisted.append(dict(committed)))
    assert committed == {"0": 5, "1": 0} and persisted == []

    written: list[list[Document]] = []
    batch.flush(written.append, lambda: persisted.append(dict(committed)))
    assert written == [[{"id": "a"}, {"id": "b"}, {"id": "c"}]]
    assert committed == {"0": 7, "1": 1} and persisted == [{"0": 7, "1": 1}]
    batch.flush(written.append, lambda: persisted.append(dict(committed)))
    assert len(written) == 1 and len(persisted) == 1


def test_batch_refuses_gaps_and_more_than_the_sql_bound() -> None:
    batch = ServingBatch({"0": 0})
    with pytest.raises(ValueError, match="recording_output_offset"):
        batch.add(0, 1, {})
    for offset in range(MAX_BATCH):
        batch.add(0, offset, {})
    with pytest.raises(ValueError, match="recording_output_offset"):
        batch.add(0, MAX_BATCH, {})


def test_stop_after_sql_ack_before_cursor_rereads_the_same_batch() -> None:
    """The durable cursor stays behind until it is written, so restart repeats."""
    disk: Document = {"0": 3}

    class Stopped(Exception):
        pass

    def stop_before_cursor() -> None:
        raise Stopped

    written: list[list[Document]] = []
    batch = ServingBatch(dict(disk))
    batch.add(0, 3, {"id": "a"})
    batch.add(0, 4, {"id": "b"})
    with pytest.raises(Stopped):
        batch.flush(written.append, stop_before_cursor)
    assert written == [[{"id": "a"}, {"id": "b"}]] and disk == {"0": 3}

    # A restarted worker starts from the durable cursor and accepts the same
    # offsets again; only a completed persist moves the cursor past them.
    restarted = ServingBatch(dict(disk))
    restarted.add(0, 3, {"id": "a"})
    restarted.add(0, 4, {"id": "b"})
    restarted.flush(written.append, lambda: disk.update(restarted.committed))
    assert written[0] == written[1] and disk == {"0": 5}
