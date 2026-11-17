"""Explain why a value stopped updating (pure; roadmap step 2, ADR-0059).

Input: two status snapshots (runtime/recording/ops_view.py) a declared window
apart. Output: source mode, last source progress, archive progress and last
query-visible progress side by side, each with the clock it was measured on,
and one explanation:

- `advancing`: query-visible progress grew over the window;
- `completed`: serving wrote its completion marker, which it writes only when
  SQL holds every reference fact (end of file plus reconciled counts);
- `serving_behind`: input and archive advance (or the archive holds input the
  serving worker has not taken) while query-visible progress stays fixed;
- `archive_behind`: input advances while the archived prefix stays fixed;
- `replay_paused`: the publisher reports its explicit paused state;
- `replay_ended`: the publisher reached the end of its deliveries and the
  remaining stages have not finished;
- `replay_waiting`: the publisher is running and current, waiting for the
  next native timestamp (a gap in the recording);
- `source_silent` (live): the gateway is running and current while receipts
  age;
- `unknown`: a stage needed for the explanation was not measured, for example
  missing gateway health or an old publisher status.

Browser delay is not measured and is always `unknown`. Ages compare a status
file with the observer clock, or a SQL write with the SQL clock, never a
source clock with a host clock (ADR-0054).
"""

from __future__ import annotations

from runtime.recording.ops_view import (
    STATUS_AGE_LIMIT_S,
    _get,
    _grew,
    _number,
    age_s,
)

type Document = dict[str, object]

# Same as runtime/continuous/recording_worker.py BEHIND.
BEHIND_DELIVERIES = 100

EXPLANATIONS = {
    "advancing": "query-visible progress is advancing",
    "completed": "end of file reached and SQL holds every reference fact",
    "serving_behind": "input and archive advance while query-visible progress "
    "stays fixed: serving is behind or stopped",
    "archive_behind": "input advances while the archived prefix stays fixed: "
    "serving waits for the archive",
    "replay_paused": "the replay publisher is paused at its last acknowledged position",
    "replay_ended": "the replay publisher reached the end of the file; later "
    "stages are still finishing",
    "replay_waiting": "the replay publisher is current and waits for the next "
    "native timestamp of the recording",
    "source_silent": "the gateway is running and current but no new source "
    "receipts arrive: the source is silent",
    "unknown": "a stage needed for the explanation is not measured",
}


def _fresh(snap: Document, progress: str) -> bool | None:
    age = age_s(snap, progress)
    return None if age is None else age <= STATUS_AGE_LIMIT_S


def explain(prev: Document, cur: Document, window_s: float) -> Document:
    inside = cur.get("inside")
    live = _get(inside, "source") == "live"
    sender = "gateway-status" if live else "producer-status"
    source_state = _get(inside, "progress", sender, "status")
    end = _number(inside, "kafka", "input_end")
    archived = _number(inside, "progress", "archive-status", "input_next")
    served = _number(inside, "progress", "serving-status", "input_archived")
    # Growth needs two snapshots; over no window it is not measured.
    measured = window_s > 0
    input_grew = _grew(prev, cur, "inside", "kafka", "input_end") if measured else None
    archive_grew = (
        _grew(prev, cur, "inside", "progress", "archive-status", "input_next")
        if measured
        else None
    )
    query_grew = (
        _grew(prev, cur, "inside", "sql", "distinct_inputs") if measured else None
    )
    serving_fresh = _fresh(cur, "serving-status")
    source_fresh = _fresh(cur, sender)
    sql_now = _number(inside, "sql", "sql_clock_ms")
    written = _number(inside, "sql", "progress_written_ms")
    receipt_ms = _number(inside, "sql", "live_state", "source_receipt_age_ms")
    connection = _get(inside, "sql", "live_state", "connection")
    # A transient gap between archive and serving is normal; only a larger one
    # means serving holds archived input back (the serving worker's threshold).
    waiting_input = (
        archived is not None
        and served is not None
        and archived - served > BEHIND_DELIVERIES
    )

    code = "unknown"
    if _get(inside, "markers", "serving-complete") is True:
        code = "completed"
    elif query_grew is True:
        code = "advancing"
    elif waiting_input or (
        serving_fresh is False
        and (
            archive_grew is True
            or (archived is not None and served is not None and archived > served)
        )
    ):
        # Serving holds archived input back, or its status is old while the
        # archive holds input it has not taken (stopped or stuck).
        code = "serving_behind"
    elif input_grew is True and archive_grew is False:
        code = "archive_behind"
    elif not live and source_state == "paused" and source_fresh is True:
        code = "replay_paused"
    elif not live and source_state == "completed":
        code = "replay_ended"
    elif not live and source_state == "running" and source_fresh is True:
        code = "replay_waiting"
    elif (
        live
        and source_state == "running"
        and source_fresh is True
        and connection == "stale"
    ):
        code = "source_silent"
    return {
        "mode": "live" if live else "replay",
        "window_s": window_s,
        "source": {
            "state": source_state,
            "progress": _get(
                inside, "progress", sender, "published" if live else "acknowledged"
            ),
            "declared": None if live else _get(inside, "progress", sender, "declared"),
            "position_native_us": None
            if live
            else _get(inside, "progress", sender, "position_native_us"),
            "status_age_s": age_s(cur, sender),
            "receipt_age_ms": receipt_ms,
            "clock": "receipt age on the SQL clock (live); native time and "
            "observer-clock status age (replay)",
        },
        "input": {"end": end, "advancing": input_grew},
        "archive": {
            "prefix": archived,
            "advancing": archive_grew,
            "status_age_s": age_s(cur, "archive-status"),
        },
        "query": {
            "visible_inputs": _get(inside, "sql", "distinct_inputs"),
            "advancing": query_grew,
            "serving_taken": served,
            "serving_status_age_s": age_s(cur, "serving-status"),
            "last_visible_native_us": _get(inside, "sql", "last_visible_native_us"),
            "progress_write_age_s": None
            if sql_now is None or written is None
            else round((sql_now - written) / 1e3, 1),
        },
        "browser_delay": "unknown",
        "explanation": code,
        "detail": EXPLANATIONS[code],
    }


def _show(value: object) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def render(result: Document) -> str:
    source = result["source"]
    archive = result["archive"]
    query = result["query"]
    assert isinstance(source, dict)
    assert isinstance(archive, dict) and isinstance(query, dict)
    position = source.get("position_native_us")
    return "\n".join(
        [
            f"Why        {result['explanation']}: {result['detail']}",
            f"  source   {result['mode']} {_show(source['state'])}; progress "
            f"{_show(source['progress'])}"
            + (
                ""
                if result["mode"] == "live"
                else f" of {_show(source['declared'])}; position "
                f"{_show(None if position is None else int(position) / 1e6)} s native"
            )
            + f"; status age {_show(source['status_age_s'])} s"
            + (
                f"; receipt age {_show(source['receipt_age_ms'])} ms"
                if result["mode"] == "live"
                else ""
            ),
            f"  archive  prefix {_show(archive['prefix'])}; advancing "
            f"{_show(archive['advancing'])}; status age "
            f"{_show(archive['status_age_s'])} s",
            f"  query    visible inputs {_show(query['visible_inputs'])}; advancing "
            f"{_show(query['advancing'])}; serving status age "
            f"{_show(query['serving_status_age_s'])} s; last SQL progress "
            f"{_show(query['progress_write_age_s'])} s ago",
            "  browser  delay unknown (not measured)",
        ]
    )
