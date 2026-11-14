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
