"""Same-parent monotonic stage observations for the bounded source/query slice."""

import json
import time
from pathlib import Path


class SliceMeasurement:
    """Record finite batch visibility; never infer per-event streaming percentiles."""

    def __init__(self, evidence: Path, observations: int) -> None:
        self.evidence = evidence
        self.observations = observations
        self.started = time.perf_counter()
        self.stages: dict[str, float] = {"source_job_admission": 0.0}

    def mark(self, stage: str) -> None:
        if stage in self.stages:
            raise ValueError("duplicate_measurement_stage")
        self.stages[stage] = time.perf_counter() - self.started

    def finish(self, unique: int, payload_bytes: int) -> None:
        self.mark("retry_verification_complete")
        visibility = self.stages["first_verified_sql_visibility"]
        ack = self.stages["producer_acked"]
        with (self.evidence / "measurement.json").open("x", encoding="utf8") as stream:
            json.dump(
                {
                    "profile": "finite-source-query-timing-v1",
                    "stages_seconds_from_admission": self.stages,
                    "attempted_observations": self.observations,
                    "acknowledged_observations": self.observations,
                    "unique_visible_measurements": unique,
                    "payload_value_bytes": payload_bytes,
                    "attempted_per_second_to_visibility": self.observations
                    / visibility,
                    "acknowledged_per_second_to_last_ack": self.observations / ack,
                    "unique_visible_per_second": unique / visibility,
                    "batch_visibility_seconds": visibility,
                    "latency_sample_count": 1,
                    "streaming_percentiles": None,
                    "query_policy": "terminal-reference complete fact reconciliation",
                    "includes_deliberate_sink_ambiguity": True,
                },
                stream,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            stream.write("\n")
