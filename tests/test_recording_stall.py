"""Why a value stopped updating: distinct explanations per stalled stage."""

from runtime.recording.stall import explain

type Document = dict[str, object]


def _snap(
    *,
    source: str = "f09",
    sender: Document | None = None,
    end: int = 100,
    archived: int = 100,
    served: int = 100,
    visible: int = 50,
    serving_age_ms: int = 1_000,
    markers: Document | None = None,
    live_state: Document | None = None,
) -> Document:
    clock = 1_000_000
    name = "gateway-status" if source == "live" else "producer-status"
    return {
        "inside": {
            "source": source,
            "clock_ms": clock,
            "progress": {
                name: {"written_ms": clock - 500, **(sender or {"status": "running"})},
                "archive-status": {"input_next": archived, "written_ms": clock - 500},
                "serving-status": {
                    "input_archived": served,
                    "written_ms": clock - serving_age_ms,
                },
            },
            "kafka": {"input_end": end},
            "sql": {"distinct_inputs": visible, "live_state": live_state},
            "markers": markers or {},
        }
    }


def test_serving_paused_while_input_and_archive_advance() -> None:
    before = _snap(end=100, archived=100, served=100, visible=50)
    after = _snap(end=160, archived=160, served=100, visible=50, serving_age_ms=20_000)
    why = explain(before, after, 10.0)
    assert why["explanation"] == "serving_behind"
    assert why["browser_delay"] == "unknown"


def test_paused_ended_and_completed_replay_are_distinct() -> None:
    paused = _snap(sender={"status": "paused", "acknowledged": 80})
    assert explain(paused, paused, 10.0)["explanation"] == "replay_paused"
    ended = _snap(sender={"status": "completed", "acknowledged": 100})
    assert explain(ended, ended, 10.0)["explanation"] == "replay_ended"
    done = _snap(
        sender={"status": "completed"}, markers={"serving-complete": True}, visible=60
    )
    assert explain(ended, done, 10.0)["explanation"] == "completed"
    moving = _snap(visible=55)
    assert explain(_snap(), moving, 10.0)["explanation"] == "advancing"


def test_live_silence_needs_a_current_gateway() -> None:
    silent = _snap(
        source="live",
        sender={"status": "running"},
        live_state={"connection": "stale", "source_receipt_age_ms": 9_000},
    )
    why = explain(silent, silent, 10.0)
    assert why["explanation"] == "source_silent"
    assert why["source"]["receipt_age_ms"] == 9_000  # type: ignore[index]
    # Missing gateway health is unknown, never silence.
    no_gateway = _snap(source="live", live_state={"connection": "stale"})
    del no_gateway["inside"]["progress"]["gateway-status"]  # type: ignore[index]
    assert explain(no_gateway, no_gateway, 10.0)["explanation"] == "unknown"


def test_one_snapshot_or_a_small_gap_is_not_serving_behind() -> None:
    # Live baseline of 2026-11-17: the first sample compared a snapshot with
    # itself while serving had taken 211 of 217 archived inputs.
    first = _snap(end=220, archived=217, served=211, visible=155)
    assert explain(first, first, 0.0)["explanation"] != "serving_behind"
    later = _snap(end=230, archived=227, served=221, visible=155)
    assert explain(first, later, 10.0)["explanation"] != "serving_behind"
