-- Require a closed, drained namespace and check every retained revision.
WITH (SELECT throwIf(count() > 0, 'serving_identity_conflict') FROM conflicts
      WHERE dataset_run_id = {run:String} AND pipeline_version = {pipeline:String}) AS guard
SELECT vehicle_id, metric_definition, start_ms, end_ms,
    content.1 AS unique_events, content.2 AS valid_count,
    content.3 AS value_sum,
    toFloat64(content.3) / nullIf(content.2, 0) AS mean
FROM unique_windows
WHERE dataset_run_id = {run:String} AND pipeline_version = {pipeline:String} AND guard = 0
ORDER BY vehicle_id, start_ms, end_ms, metric_definition
FORMAT JSONEachRow;
