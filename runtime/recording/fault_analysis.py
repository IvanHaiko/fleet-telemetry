"""Evaluate a fault run's observer samples against its predeclared criterion.

All times are on the observer's clock: the observer container samples the run,
and fault start/resume times come from the same Docker engine clock. A GPS
fact's acknowledgement time is the first sample whose producer count covers its
input offset; its visibility time is the first sample in which SQL holds it.
Both carry up to one sample interval of error.

For each fault, recovery ends at the first sample after the resume action at
which every fact acknowledged before the fault is visible, at least one fact
acknowledged after the resume action is visible (when one exists), and no
visible-pending fact is older than the visibility limit. The fault window runs
from the fault start to that sample. The recovery limit applies to the whole
window, except for a drill of declared length (an archive pause, a live
source silence or gateway outage), which is not a recovery: its limit applies
to the catch-up from the resume action. The
visibility limit applies to every fact whose acknowledgement-to-visibility
interval lies entirely outside all fault windows; facts that overlap a window
are covered by that fault's recovery limit instead.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence

type Row = Mapping[str, object]
type Document = dict[str, object]

MAX_SAMPLE_GAP_S = 10.0
# Drills whose length is declared: the archive pause (ADR-0053), and the live
# source silence and gateway outage (ADR-0054). Their limit is the catch-up.
DELIBERATE = ("archive-pause", "source-silence", "gateway-restart")


def _int(value: object) -> int:
    return value if type(value) is int else 0


def facts_timeline(samples: Sequence[Row]) -> tuple[dict[int, int], dict[int, int]]:
    """Return acknowledgement and visibility times per observed input offset."""
    times = [_int(row["t_ms"]) for row in samples]
    acks = [_int(row["ack"]) for row in samples]
    # Producer counts never decrease, so a running maximum is searchable.
    running: list[int] = []
    for ack in acks:
        running.append(max(ack, running[-1] if running else 0))
    visible: dict[int, int] = {}
    for row in samples:
        for offset in row["new"] or []:  # type: ignore[attr-defined]
            visible.setdefault(int(offset), _int(row["t_ms"]))
    acknowledged: dict[int, int] = {}
    for offset in visible:
        index = bisect_left(running, offset + 1)
        if index < len(times):
            acknowledged[offset] = times[index]
    return acknowledged, visible


def recovery(
    samples: Sequence[Row],
    acknowledged: Mapping[int, int],
    visible: Mapping[int, int],
    start_ms: int,
    resume_ms: int,
    visibility_ms: int,
) -> int | None:
    """First sample time after resume at which the fault's backlog is caught up."""
    before = [o for o, t in acknowledged.items() if t <= start_ms]
    backlog_done = max((visible[o] for o in before), default=start_ms)
    # The path must also carry a fact acknowledged after the resume action:
    # otherwise a stopped consumer whose last batch had landed looks recovered
    # until its pending facts age past the limit. Acknowledgement times carry
    # one sample of error, so only a fact that the first sample at or after the
    # resume did not yet cover is certainly acknowledged after it.
    first_after = next(
        (_int(r["t_ms"]) for r in samples if _int(r["t_ms"]) >= resume_ms), resume_ms
    )
    flowing = min(
        (visible[o] for o, t in acknowledged.items() if t > first_after),
        default=first_after,
    )
    order = sorted(acknowledged, key=lambda o: (acknowledged[o], o))
    first_pending = 0
    for row in samples:
        now = _int(row["t_ms"])
        while first_pending < len(order) and visible[order[first_pending]] <= now:
            first_pending += 1
        if now < resume_ms or now < backlog_done or now < flowing:
            continue
        oldest = 0
        for offset in order[first_pending:]:
            if acknowledged[offset] > now:
                break
            if visible[offset] > now:
                oldest = now - acknowledged[offset]
                break
        if oldest <= visibility_ms:
            return now
    return None


def evaluate(
    samples: Sequence[Row],
    faults: Sequence[Row],
    expected_facts: int,
    visibility_s: float,
    drain_s: float,
) -> Document:
    """Return measured figures and a pass flag for each predeclared limit."""
    times = [_int(row["t_ms"]) for row in samples]
    gaps = [(b - a) / 1000 for a, b in zip(times, times[1:], strict=False)]
    acknowledged, visible = facts_timeline(samples)
    limit_ms = int(visibility_s * 1000)
    measured: list[Document] = []
    windows: list[tuple[int, int]] = []
    for fault in faults:
        start, resume = _int(fault["start_ms"]), _int(fault["resume_ms"])
        done = recovery(samples, acknowledged, visible, start, resume, limit_ms)
        end = done if done is not None else (times[-1] if times else start)
        windows.append((start, end))
        limit = fault["recovery_limit_s"]
        seconds = None if done is None else (done - start) / 1000
        catch_up = None if done is None else (done - resume) / 1000
        # A deliberate pause lasts as long as declared; its limit is the catch-up.
        deliberate = fault.get("kind") in DELIBERATE
        judged = catch_up if deliberate else seconds
        row: Document = {
            "name": fault["name"],
            "start_ms": start,
            "resume_ms": resume,
            "recovered_ms": done,
            "outage_s": (resume - start) / 1000,
            "recovery_s": seconds,
            "catch_up_after_resume_s": catch_up,
            "recovery_limit_s": limit,
            "limit_applies_to": "catch_up_after_resume_s"
            if deliberate
            else "recovery_s",
            "pass_recovery": judged is not None
            and isinstance(limit, (int, float))
            and judged <= limit,
        }
        if fault.get("kind") == "archive-pause":
            held = [r for r in samples if start <= _int(r["t_ms"]) <= resume]
            if held:
                last = held[-1]
                shown = [o for o, t in visible.items() if t <= _int(last["t_ms"])]
                row["held_at_resume"] = {
                    "producer_acknowledged": last.get("ack"),
                    "archive_next": last.get("archived"),
                    "serving_archived": last.get("serving_archived"),
                    "sql_visible_facts": len(shown),
                    "max_visible_input_offset": max(shown, default=None),
                }
        measured.append(row)
    inside = 0
    delays: list[float] = []
    for offset, ack in acknowledged.items():
        seen = visible[offset]
        if any(ack <= end and seen >= start for start, end in windows):
            inside += 1
            continue
        delays.append((seen - ack) / 1000)
    delays.sort()
    completed = next(
        (_int(r["t_ms"]) for r in samples if r.get("producer") == "completed"), None
    )
    full = next(
        (_int(r["t_ms"]) for r in samples if _int(r["visible"]) >= expected_facts),
        None,
    )
    drain = None if completed is None or full is None else (full - completed) / 1000
    drain_in_window = completed is not None and any(
        start <= completed <= end for start, end in windows
    )
    coverage = bool(gaps) and max(gaps) <= MAX_SAMPLE_GAP_S
    return {
        "samples": len(samples),
        "observation_errors": sum(1 for r in samples if r.get("error")),
        "max_sample_gap_s": max(gaps, default=None),
        "coverage_established": coverage,
        "facts_observed": len(visible),
        "facts_inside_fault_windows": inside,
        "facts_outside_fault_windows": len(delays),
        "visibility_outside_windows_s": {
            "p50": delays[len(delays) // 2] if delays else None,
            "p99": delays[min(len(delays) - 1, int(0.99 * len(delays)))]
            if delays
            else None,
            "max": delays[-1] if delays else None,
            "over_limit": sum(d > visibility_s for d in delays),
            "limit": visibility_s,
        },
        "terminal_drain_s": drain,
        "terminal_drain_inside_fault_window": drain_in_window,
        "faults": measured,
        "pass_visibility": coverage
        and len(visible) == expected_facts
        and bool(delays)
        and delays[-1] <= visibility_s,
        "pass_drain": drain is not None and (drain_in_window or drain <= drain_s),
        "pass_recovery": all(bool(row["pass_recovery"]) for row in measured),
    }
