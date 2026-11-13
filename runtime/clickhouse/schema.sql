-- Fresh experiment database only. No IF NOT EXISTS masks prior state.
CREATE TABLE events
(
    dataset_run_id String, pipeline_version String, event_id String,
    vehicle_id String, source_timestamp DateTime64(6, 'UTC'),
    voltage_v Nullable(Decimal(18, 6)), current_a Nullable(Decimal(18, 6)),
    remaining_fraction Nullable(Decimal(18, 6)),
    disposition Enum8('eligible' = 1, 'late' = 2),
    quality_flags Array(String), semantic_json String
)
ENGINE = MergeTree ORDER BY (dataset_run_id, pipeline_version, event_id);

CREATE TABLE windows
(
    dataset_run_id String, pipeline_version String, vehicle_id String,
    metric_definition String, start_ms Int64, end_ms Int64,
    revision UInt64, unique_events UInt64, valid_count UInt64,
    value_sum Decimal(18, 6)
)
ENGINE = MergeTree
ORDER BY (dataset_run_id, pipeline_version, vehicle_id,
          metric_definition, start_ms, end_ms, revision);

CREATE VIEW event_groups AS
SELECT dataset_run_id, pipeline_version, event_id,
    any(tuple(vehicle_id, source_timestamp, voltage_v, current_a,
              remaining_fraction, disposition, quality_flags, semantic_json)) AS content,
    uniqExact(tuple(vehicle_id, source_timestamp, voltage_v, current_a,
                    remaining_fraction, disposition, quality_flags, semantic_json)) AS variants
FROM events GROUP BY dataset_run_id, pipeline_version, event_id;

CREATE VIEW window_groups AS
SELECT dataset_run_id, pipeline_version, vehicle_id, metric_definition,
    start_ms, end_ms, revision,
    any(tuple(unique_events, valid_count, value_sum)) AS content,
    uniqExact(tuple(unique_events, valid_count, value_sum)) AS variants
FROM windows
GROUP BY dataset_run_id, pipeline_version, vehicle_id, metric_definition,
         start_ms, end_ms, revision;

CREATE VIEW conflicts AS
SELECT dataset_run_id, pipeline_version FROM event_groups WHERE variants != 1
UNION ALL
SELECT dataset_run_id, pipeline_version FROM window_groups WHERE variants != 1;

CREATE VIEW unique_events AS
SELECT dataset_run_id, pipeline_version, event_id,
    content.1 AS vehicle_id, content.2 AS source_timestamp,
    content.3 AS voltage_v, content.4 AS current_a,
    content.5 AS remaining_fraction, content.6 AS disposition,
    content.7 AS quality_flags, content.8 AS semantic_json
FROM event_groups WHERE variants = 1;

CREATE VIEW unique_windows AS
SELECT dataset_run_id, pipeline_version, vehicle_id, metric_definition,
    start_ms, end_ms, argMax(content, revision) AS content
FROM window_groups WHERE variants = 1
GROUP BY dataset_run_id, pipeline_version, vehicle_id, metric_definition,
         start_ms, end_ms;
