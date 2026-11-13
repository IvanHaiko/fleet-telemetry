SET 'execution.runtime-mode' = 'streaming';
SET 'execution.target' = 'remote';
SET 'execution.attached' = 'false';
SET 'pipeline.name' = 'local-battery-projection-v1';
SET 'table.local-time-zone' = 'UTC';

CREATE TEMPORARY TABLE battery_input (
    raw_event STRING,
    source_partition INT METADATA FROM 'partition' VIRTUAL,
    source_offset BIGINT METADATA FROM 'offset' VIRTUAL
) WITH (
    'connector' = 'kafka',
    'topic' = 'telemetry.battery.input',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'local-battery-projection-v1',
    'properties.auto.offset.reset' = 'none',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'raw'
);

CREATE TEMPORARY TABLE battery_output (
    profile STRING,
    dataset_run_id STRING,
    event_id STRING,
    vehicle_id STRING,
    source_timestamp STRING,
    voltage_v DOUBLE,
    current_a DOUBLE,
    remaining_fraction DOUBLE,
    power_w DOUBLE,
    raw_event STRING,
    source_partition INT,
    source_offset BIGINT
) WITH (
    'connector' = 'kafka',
    'topic' = 'telemetry.battery.output',
    'properties.bootstrap.servers' = 'kafka:9092',
    'sink.delivery-guarantee' = 'at-least-once',
    'format' = 'json'
);

INSERT INTO battery_output
SELECT
    'local-battery-projection-v1',
    JSON_VALUE(raw_event, '$.delivery.dataset_run_id'),
    JSON_VALUE(raw_event, '$.event_id'),
    JSON_VALUE(raw_event, '$.vehicle_id'),
    JSON_VALUE(raw_event, '$.source_timestamp'),
    CAST(JSON_VALUE(raw_event, '$.payload.voltage_v') AS DOUBLE),
    CAST(JSON_VALUE(raw_event, '$.payload.current_a') AS DOUBLE),
    CAST(JSON_VALUE(raw_event, '$.payload.remaining_fraction') AS DOUBLE),
    CAST(JSON_VALUE(raw_event, '$.payload.voltage_v') AS DOUBLE)
        * CAST(JSON_VALUE(raw_event, '$.payload.current_a') AS DOUBLE),
    raw_event, source_partition, source_offset
FROM battery_input;
