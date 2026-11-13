-- Finite integration facts. Canonical events retain their own admitted table.
CREATE TABLE slice_dispositions_v1
(
    dataset_run_id String, pipeline_version String, observation_index UInt64,
    event_id String, disposition String, reason String, watermark_ms Int64,
    archive_descriptor_sha256 String
)
ENGINE = MergeTree
ORDER BY (dataset_run_id, pipeline_version, observation_index);

CREATE TABLE slice_windows_v1
(
    dataset_run_id String, pipeline_version String, vehicle_id String,
    start_ms Int64, end_ms Int64, metric String, unique_events UInt64,
    valid_count UInt64, value_sum Decimal(18,6),
    archive_descriptor_sha256 String
)
ENGINE = MergeTree
ORDER BY (dataset_run_id, pipeline_version, vehicle_id, start_ms, metric);
