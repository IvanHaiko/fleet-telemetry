WITH (SELECT throwIf(count() > 0, 'serving_identity_conflict') FROM conflicts
      WHERE dataset_run_id = {run:String} AND pipeline_version = {pipeline:String}) AS guard
SELECT vehicle_id, count() AS measurements,
    count(voltage_v) AS voltage_valid, count() - count(voltage_v) AS voltage_missing,
    count(current_a) AS current_valid, count() - count(current_a) AS current_missing,
    count(remaining_fraction) AS remaining_valid,
    count() - count(remaining_fraction) AS remaining_missing
FROM unique_events
WHERE dataset_run_id = {run:String} AND pipeline_version = {pipeline:String} AND guard = 0
GROUP BY vehicle_id ORDER BY vehicle_id
FORMAT JSONEachRow;
