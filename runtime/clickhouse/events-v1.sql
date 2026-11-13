CREATE TABLE serving_events_v1
(
    projection_version String,
    dataset_run_id String,
    pipeline_version String,
    event_id String,
    vehicle_id String,
    source_timestamp DateTime64(6, 'UTC'),
    voltage_v Decimal(18, 6),
    current_a Nullable(Decimal(18, 6)),
    remaining_fraction Nullable(Decimal(18, 6)),
    quality_flags Array(String),
    semantic_json String,
    source_dataset_run_id String,
    source_job_sha256 String,
    archive_descriptor_sha256 String
)
ENGINE = MergeTree
ORDER BY (dataset_run_id, pipeline_version, event_id);
