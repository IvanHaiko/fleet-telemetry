"""Recovery measure of a fault run, on a tiny synthetic observer timeline."""

from runtime.recording.fault_analysis import facts_timeline, recovery


def test_recovery_waits_for_a_fact_acknowledged_after_resume() -> None:
    # Serving writes its last batch (facts 2-4) at 4.5 s, stops, and is
    # restarted at 5 s, but writes nothing more until 10 s. Fact 4 was
    # acknowledged just before the fault, yet the 2-second samples first show
    # it at 6 s, after the resume. Only facts that the 6 s sample did not yet
    # cover show the consumer is back; complete-flight runs
    # f09-s3-full-20261116-01 and -02 closed their serving windows 32 s early.
    samples = [
        {"t_ms": 0, "ack": 2, "new": [0, 1]},
        {"t_ms": 2000, "ack": 4, "new": []},
        {"t_ms": 4000, "ack": 4, "new": []},
        {"t_ms": 6000, "ack": 6, "new": [2, 3, 4]},
        {"t_ms": 8000, "ack": 8, "new": []},
        {"t_ms": 10000, "ack": 8, "new": [5, 6, 7]},
    ]
    acknowledged, visible = facts_timeline(samples)
    assert recovery(samples, acknowledged, visible, 4500, 5000, 15000) == 10000
