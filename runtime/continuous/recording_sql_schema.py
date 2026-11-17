"""ClickHouse columns and scope of a projected recording fact."""

_GPS_FIELDS = ("latitude_deg", "longitude_deg", "altitude_msl_m", "ground_speed_m_s")
_GROUPS = {
    "battery": ("voltage_v", "current_a", "remaining_fraction"),
    "land": ("landed", "ground_contact", "maybe_landed"),
    "vehicle_status": ("arming_state", "nav_state", "failsafe"),
}
_SCOPE = (
    "source_cluster_id",
    "source_topic_id",
    "source_topic",
    "source_partition",
    "context_sha256",
    "run_id",
)
_COLUMNS = {
    "event_id": "String",
    "input_offset": "UInt64",
    "native_timestamp_us": "UInt64",
    "native_seconds": "Float64",
    **{name: "Nullable(Float64)" for name in _GPS_FIELDS},
    **{group + "_status": "String" for group in _GROUPS},
    **{group + "_age_us": "Nullable(UInt64)" for group in _GROUPS},
    **{group + "_event_id": "Nullable(String)" for group in _GROUPS},
    **{name: "Nullable(Float64)" for name in _GROUPS["battery"]},
    **{name: "Nullable(UInt8)" for name in _GROUPS["land"] + _GROUPS["vehicle_status"]},
    "source_cluster_id": "String",
    "source_topic_id": "String",
    "source_topic": "String",
    "source_partition": "UInt8",
    "context_sha256": "String",
    "run_id": "String",
    "output_json": "String",
    "fact_json": "String",
    "inspection_json": "String",
}
