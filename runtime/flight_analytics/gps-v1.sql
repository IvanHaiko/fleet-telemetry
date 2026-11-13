CREATE TABLE f09_flight_analytics_v1.gps_v1
(
  event_id String,
  vehicle_id String,
  source_ordinal UInt32,
  native_timestamp_us UInt64,
  native_sample_us UInt64,
  gps_utc Nullable(DateTime64(6, 'UTC')),
  gps_time_relative_us Int32,
  latitude_deg Nullable(Float64),
  longitude_deg Nullable(Float64),
  altitude_msl_m Nullable(Float64),
  ground_speed_m_s Nullable(Float64),
  fix_type UInt8,
  row_json String
)
ENGINE = MergeTree ORDER BY (vehicle_id, source_ordinal)
