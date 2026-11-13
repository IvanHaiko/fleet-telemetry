-- Counts are unique valid measurements per flag, not transport observations.
WITH (SELECT throwIf(count() > 0, 'serving_identity_conflict') FROM conflicts
      WHERE dataset_run_id = {run:String} AND pipeline_version = {pipeline:String}) AS guard
SELECT disposition, arrayJoin(quality_flags) AS quality_flag, count() AS measurements
FROM unique_events
WHERE dataset_run_id = {run:String} AND pipeline_version = {pipeline:String} AND guard = 0
GROUP BY disposition, quality_flag ORDER BY disposition, quality_flag
FORMAT JSONEachRow;
