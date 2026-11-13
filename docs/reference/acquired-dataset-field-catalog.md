# Acquired dataset field catalog

**Retention update, 2026-11-06:** standalone DJI source sets, decoded copies
and the portable decoder were intentionally removed by the maintainer.
DJI field tables below remain historical inspection metadata.
See [current retention](dataset-acquisition.md#current-retention-after-authorized-dji-removal-2026-11-06).

Generated from the [2026-11-06 structural inspection](dataset-structure.md).
Only schema names, types and coverage counts are published. Source values,
locations, serials, source paths and decoded records remain in ignored local storage.

## UAV-SEAD embedded ULog declarations

Denominator: 3,962 successfully read headers out of 3,968 `.ulg` paths.
There are 172 declared format names and 2,163 field/type/array variants.
Nested structure definitions are included. A declared format is not proof
that its topic was subscribed, populated or physically measured.
The separate 20-file sample confirms records only for its selected topic filter.
Arrays are shown at declared length; nested types require recursive expansion.
Field meanings, units, enums, sentinels and clock semantics still require the
matching firmware definition. Equal names do not establish compatibility.

### `action_request`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `action` | `uint8_t` | 0 | 8 |
| `mode` | `uint8_t` | 0 | 8 |
| `source` | `uint8_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |

### `actuator_armed`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `armed` | `bool` | 0 | 2266 |
| `armed_time_ms` | `uint32_t` | 0 | 2258 |
| `force_failsafe` | `bool` | 0 | 2266 |
| `in_esc_calibration_mode` | `bool` | 0 | 2266 |
| `lockdown` | `bool` | 0 | 2266 |
| `manual_lockdown` | `bool` | 0 | 2266 |
| `prearmed` | `bool` | 0 | 2266 |
| `ready_to_arm` | `bool` | 0 | 2266 |
| `soft_stop` | `bool` | 0 | 2266 |
| `timestamp` | `uint64_t` | 0 | 2266 |

### `actuator_controls`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control` | `float` | 8 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_sample` | `uint64_t` | 0 | 2255 |

### `actuator_controls_0`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control` | `float` | 8 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 3962 |

### `actuator_controls_1`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control` | `float` | 8 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 3962 |

### `actuator_controls_2`

Declared in 2263 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control` | `float` | 8 | 2263 |
| `timestamp` | `uint64_t` | 0 | 2263 |
| `timestamp_sample` | `uint64_t` | 0 | 2263 |

### `actuator_controls_3`

Declared in 2263 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control` | `float` | 8 | 2263 |
| `timestamp` | `uint64_t` | 0 | 2263 |
| `timestamp_sample` | `uint64_t` | 0 | 2263 |

### `actuator_controls_virtual_fw`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control` | `float` | 8 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_sample` | `uint64_t` | 0 | 2255 |

### `actuator_controls_virtual_mc`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control` | `float` | 8 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_sample` | `uint64_t` | 0 | 2255 |

### `actuator_direct`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `nvalues` | `uint32_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `values` | `float` | 16 | 2255 |

### `actuator_outputs`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `noutputs` | `uint32_t` | 0 | 3962 |
| `output` | `float` | 16 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |

### `adc_report`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `channel_id` | `int16_t` | 12 | 2255 |
| `channel_value` | `float` | 12 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `airspeed`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `air_temperature_celsius` | `float` | 0 | 3962 |
| `confidence` | `float` | 0 | 3962 |
| `indicated_airspeed_m_s` | `float` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `true_airspeed_m_s` | `float` | 0 | 3962 |
| `true_airspeed_unfiltered_m_s` | `float` | 0 | 2255 |

### `airspeed_validated`

Declared in 1699 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `airspeed_sensor_measurement_valid` | `bool` | 0 | 3 |
| `equivalent_airspeed_m_s` | `float` | 0 | 1699 |
| `equivalent_ground_minus_wind_m_s` | `float` | 0 | 3 |
| `indicated_airspeed_m_s` | `float` | 0 | 1699 |
| `indicated_ground_minus_wind_m_s` | `float` | 0 | 1696 |
| `selected_airspeed_index` | `int8_t` | 0 | 1699 |
| `timestamp` | `uint64_t` | 0 | 1699 |
| `true_airspeed_m_s` | `float` | 0 | 1699 |
| `true_ground_minus_wind_m_s` | `float` | 0 | 1699 |

### `att_pos_mocap`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `id` | `uint32_t` | 0 | 2255 |
| `q` | `float` | 4 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_received` | `uint64_t` | 0 | 2255 |
| `x` | `float` | 0 | 2255 |
| `y` | `float` | 0 | 2255 |
| `z` | `float` | 0 | 2255 |

### `autotune_attitude_control_status`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `att_p` | `float` | 0 | 8 |
| `coeff` | `float` | 5 | 8 |
| `coeff_var` | `float` | 5 | 8 |
| `dt_model` | `float` | 0 | 8 |
| `fitness` | `float` | 0 | 8 |
| `innov` | `float` | 0 | 8 |
| `kc` | `float` | 0 | 8 |
| `kd` | `float` | 0 | 8 |
| `kff` | `float` | 0 | 8 |
| `ki` | `float` | 0 | 8 |
| `rate_sp` | `float` | 3 | 8 |
| `state` | `uint8_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `u_filt` | `float` | 0 | 8 |
| `y_filt` | `float` | 0 | 8 |

### `battery_status`

Declared in 3962 headers; selected records observed in 20/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `available_energy` | `float` | 0 | 8 |
| `average_current_a` | `float` | 0 | 3848 |
| `average_power` | `float` | 0 | 8 |
| `average_time_to_empty` | `uint16_t` | 0 | 3856 |
| `average_time_to_full` | `uint16_t` | 0 | 8 |
| `capacity` | `uint16_t` | 0 | 3856 |
| `cell_count` | `int32_t` | 0 | 3954 |
| `cell_count` | `uint8_t` | 0 | 8 |
| `connected` | `bool` | 0 | 3962 |
| `current_a` | `float` | 0 | 3962 |
| `current_average_a` | `float` | 0 | 8 |
| `current_filtered_a` | `float` | 0 | 3962 |
| `custom_faults` | `uint32_t` | 0 | 8 |
| `cycle_count` | `uint16_t` | 0 | 3856 |
| `design_capacity` | `float` | 0 | 8 |
| `discharged_mah` | `float` | 0 | 3962 |
| `faults` | `uint16_t` | 0 | 8 |
| `full_charge_capacity_wh` | `float` | 0 | 8 |
| `id` | `uint8_t` | 0 | 11 |
| `interface_error` | `uint16_t` | 0 | 8 |
| `is_powering_off` | `bool` | 0 | 3856 |
| `is_required` | `bool` | 0 | 8 |
| `manufacture_date` | `uint16_t` | 0 | 8 |
| `max_cell_voltage_delta` | `float` | 0 | 1707 |
| `max_error` | `uint16_t` | 0 | 11 |
| `mode` | `uint8_t` | 0 | 8 |
| `nominal_voltage` | `float` | 0 | 8 |
| `over_discharge_count` | `uint16_t` | 0 | 8 |
| `priority` | `uint8_t` | 0 | 3962 |
| `remaining` | `float` | 0 | 3962 |
| `remaining_capacity_wh` | `float` | 0 | 8 |
| `run_time_to_empty` | `uint16_t` | 0 | 3848 |
| `scale` | `float` | 0 | 3962 |
| `serial_number` | `uint16_t` | 0 | 3856 |
| `source` | `uint8_t` | 0 | 11 |
| `state_of_health` | `uint16_t` | 0 | 11 |
| `system_source` | `bool` | 0 | 3951 |
| `temperature` | `float` | 0 | 3856 |
| `time_remaining_s` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `voltage_cell_v` | `float` | 4 | 1696 |
| `voltage_cell_v` | `float` | 10 | 3 |
| `voltage_cell_v` | `float` | 14 | 8 |
| `voltage_filtered_v` | `float` | 0 | 3962 |
| `voltage_v` | `float` | 0 | 3962 |
| `warning` | `uint8_t` | 0 | 3962 |

### `camera_capture`

Declared in 3957 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `float` | 0 | 3957 |
| `ground_distance` | `float` | 0 | 3957 |
| `lat` | `double` | 0 | 3957 |
| `lon` | `double` | 0 | 3957 |
| `q` | `float` | 4 | 3957 |
| `result` | `int8_t` | 0 | 3957 |
| `seq` | `uint32_t` | 0 | 3957 |
| `timestamp` | `uint64_t` | 0 | 3957 |
| `timestamp_utc` | `uint64_t` | 0 | 3957 |

### `camera_trigger`

Declared in 3957 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `feedback` | `bool` | 0 | 1702 |
| `seq` | `uint32_t` | 0 | 3957 |
| `timestamp` | `uint64_t` | 0 | 3957 |
| `timestamp_utc` | `uint64_t` | 0 | 3957 |

### `camera_trigger_secondary`

Declared in 1699 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `feedback` | `bool` | 0 | 1699 |
| `seq` | `uint32_t` | 0 | 1699 |
| `timestamp` | `uint64_t` | 0 | 1699 |
| `timestamp_utc` | `uint64_t` | 0 | 1699 |

### `cellular_status`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `failure_reason` | `uint8_t` | 0 | 11 |
| `lac` | `uint16_t` | 0 | 11 |
| `mcc` | `uint16_t` | 0 | 11 |
| `mnc` | `uint16_t` | 0 | 11 |
| `quality` | `uint8_t` | 0 | 11 |
| `status` | `uint16_t` | 0 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `type` | `uint8_t` | 0 | 11 |

### `collision_report`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `action` | `uint8_t` | 0 | 2255 |
| `altitude_minimum_delta` | `float` | 0 | 2255 |
| `horizontal_minimum_delta` | `float` | 0 | 2255 |
| `id` | `uint32_t` | 0 | 2255 |
| `src` | `uint8_t` | 0 | 2255 |
| `threat_level` | `uint8_t` | 0 | 2255 |
| `time_to_minimum_delta` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `commander_state`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `main_state` | `uint8_t` | 0 | 2266 |
| `main_state_changes` | `uint16_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 2266 |

### `control_allocator_status`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `actuator_saturation` | `int8_t` | 16 | 8 |
| `allocated_thrust` | `float` | 3 | 8 |
| `allocated_torque` | `float` | 3 | 8 |
| `thrust_setpoint_achieved` | `bool` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `torque_setpoint_achieved` | `bool` | 0 | 8 |
| `unallocated_thrust` | `float` | 3 | 8 |
| `unallocated_torque` | `float` | 3 | 8 |

### `cpuload`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `load` | `float` | 0 | 3962 |
| `ram_usage` | `float` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |

### `debug_key_value`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `key` | `char` | 10 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_ms` | `uint32_t` | 0 | 2255 |
| `value` | `float` | 0 | 2255 |

### `debug_value`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `ind` | `int8_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_ms` | `uint32_t` | 0 | 2255 |
| `value` | `float` | 0 | 2255 |

### `debug_vect`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `name` | `char` | 10 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_us` | `uint64_t` | 0 | 2255 |
| `x` | `float` | 0 | 2255 |
| `y` | `float` | 0 | 2255 |
| `z` | `float` | 0 | 2255 |

### `differential_pressure`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `device_id` | `uint32_t` | 0 | 2266 |
| `differential_pressure_filtered_pa` | `float` | 0 | 2258 |
| `differential_pressure_pa` | `float` | 0 | 8 |
| `differential_pressure_raw_pa` | `float` | 0 | 2258 |
| `error_count` | `uint32_t` | 0 | 8 |
| `error_count` | `uint64_t` | 0 | 2258 |
| `temperature` | `float` | 0 | 2266 |
| `timestamp` | `uint64_t` | 0 | 2266 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `distance_sensor`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `covariance` | `float` | 0 | 2255 |
| `current_distance` | `float` | 0 | 3962 |
| `device_id` | `uint32_t` | 0 | 8 |
| `h_fov` | `float` | 0 | 1707 |
| `id` | `uint8_t` | 0 | 3954 |
| `max_distance` | `float` | 0 | 3962 |
| `min_distance` | `float` | 0 | 3962 |
| `orientation` | `uint8_t` | 0 | 3962 |
| `q` | `float` | 4 | 1707 |
| `signal_quality` | `int8_t` | 0 | 1707 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `type` | `uint8_t` | 0 | 3962 |
| `v_fov` | `float` | 0 | 1707 |
| `variance` | `float` | 0 | 1707 |

### `ekf2_innovations`

Declared in 3951 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `airspeed_innov` | `float` | 0 | 3951 |
| `airspeed_innov_var` | `float` | 0 | 3951 |
| `aux_vel_innov` | `float` | 2 | 3845 |
| `beta_innov` | `float` | 0 | 3951 |
| `beta_innov_var` | `float` | 0 | 3951 |
| `drag_innov` | `float` | 2 | 3951 |
| `drag_innov_var` | `float` | 2 | 3951 |
| `flow_innov` | `float` | 2 | 3951 |
| `flow_innov_var` | `float` | 2 | 3951 |
| `hagl_innov` | `float` | 0 | 3951 |
| `hagl_innov_var` | `float` | 0 | 3951 |
| `heading_innov` | `float` | 0 | 3951 |
| `heading_innov_var` | `float` | 0 | 3951 |
| `mag_innov` | `float` | 3 | 3951 |
| `mag_innov_var` | `float` | 3 | 3951 |
| `output_tracking_error` | `float` | 3 | 3951 |
| `timestamp` | `uint64_t` | 0 | 3951 |
| `vel_pos_innov` | `float` | 6 | 3951 |
| `vel_pos_innov_var` | `float` | 6 | 3951 |

### `ekf2_timestamps`

Declared in 2929 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `airspeed_timestamp_rel` | `int16_t` | 0 | 2929 |
| `distance_sensor_timestamp_rel` | `int16_t` | 0 | 2929 |
| `gps_timestamp_rel` | `int16_t` | 0 | 2921 |
| `optical_flow_timestamp_rel` | `int16_t` | 0 | 2929 |
| `timestamp` | `uint64_t` | 0 | 2929 |
| `vehicle_air_data_timestamp_rel` | `int16_t` | 0 | 2823 |
| `vehicle_magnetometer_timestamp_rel` | `int16_t` | 0 | 2823 |
| `vision_attitude_timestamp_rel` | `int16_t` | 0 | 2255 |
| `vision_position_timestamp_rel` | `int16_t` | 0 | 2255 |
| `visual_odometry_timestamp_rel` | `int16_t` | 0 | 674 |

### `ekf_gps_drift`

Declared in 1699 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `blocked` | `bool` | 0 | 1699 |
| `hpos_drift_rate` | `float` | 0 | 1699 |
| `hspd` | `float` | 0 | 1699 |
| `timestamp` | `uint64_t` | 0 | 1699 |
| `vpos_drift_rate` | `float` | 0 | 1699 |

### `ekf_gps_position`

Declared in 666 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `int32_t` | 0 | 666 |
| `alt_ellipsoid` | `int32_t` | 0 | 666 |
| `eph` | `float` | 0 | 666 |
| `epv` | `float` | 0 | 666 |
| `fix_type` | `uint8_t` | 0 | 666 |
| `heading` | `float` | 0 | 666 |
| `heading_offset` | `float` | 0 | 666 |
| `lat` | `int32_t` | 0 | 666 |
| `lon` | `int32_t` | 0 | 666 |
| `s_variance_m_s` | `float` | 0 | 666 |
| `satellites_used` | `uint8_t` | 0 | 666 |
| `selected` | `uint8_t` | 0 | 666 |
| `timestamp` | `uint64_t` | 0 | 666 |
| `vel_d_m_s` | `float` | 0 | 666 |
| `vel_e_m_s` | `float` | 0 | 666 |
| `vel_m_s` | `float` | 0 | 666 |
| `vel_n_m_s` | `float` | 0 | 666 |
| `vel_ned_valid` | `bool` | 0 | 666 |

### `esc_report`

Declared in 3954 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `esc_address` | `uint16_t` | 0 | 3951 |
| `esc_address` | `uint8_t` | 0 | 3 |
| `esc_current` | `float` | 0 | 3954 |
| `esc_errorcount` | `uint32_t` | 0 | 3954 |
| `esc_rpm` | `int32_t` | 0 | 3954 |
| `esc_setpoint` | `float` | 0 | 3951 |
| `esc_setpoint_raw` | `uint16_t` | 0 | 3951 |
| `esc_state` | `uint16_t` | 0 | 2255 |
| `esc_state` | `uint8_t` | 0 | 1699 |
| `esc_temperature` | `float` | 0 | 2255 |
| `esc_temperature` | `uint8_t` | 0 | 1699 |
| `esc_vendor` | `uint8_t` | 0 | 2255 |
| `esc_version` | `uint16_t` | 0 | 2255 |
| `esc_voltage` | `float` | 0 | 3954 |
| `failures` | `uint8_t` | 0 | 3 |
| `timestamp` | `uint64_t` | 0 | 3954 |

### `esc_status`

Declared in 3954 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `counter` | `uint16_t` | 0 | 3954 |
| `esc` | `esc_report` | 8 | 3954 |
| `esc_armed_flags` | `uint8_t` | 0 | 3 |
| `esc_connectiontype` | `uint8_t` | 0 | 3954 |
| `esc_count` | `uint8_t` | 0 | 3954 |
| `esc_online_flags` | `uint8_t` | 0 | 1699 |
| `timestamp` | `uint64_t` | 0 | 3954 |

### `estimator_attitude`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `delta_q_reset` | `float` | 4 | 8 |
| `q` | `float` | 4 | 8 |
| `quat_reset_counter` | `uint8_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_baro_bias`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `baro_device_id` | `uint32_t` | 0 | 8 |
| `bias` | `float` | 0 | 8 |
| `bias_var` | `float` | 0 | 8 |
| `innov` | `float` | 0 | 8 |
| `innov_test_ratio` | `float` | 0 | 8 |
| `innov_var` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_event_flags`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `bad_yaw_using_gps_course` | `bool` | 0 | 8 |
| `emergency_yaw_reset_gps_yaw_stopped` | `bool` | 0 | 8 |
| `emergency_yaw_reset_mag_stopped` | `bool` | 0 | 8 |
| `gps_checks_passed` | `bool` | 0 | 8 |
| `gps_data_stopped` | `bool` | 0 | 8 |
| `gps_data_stopped_using_alternate` | `bool` | 0 | 8 |
| `gps_fusion_timout` | `bool` | 0 | 8 |
| `gps_quality_poor` | `bool` | 0 | 8 |
| `height_sensor_timeout` | `bool` | 0 | 8 |
| `information_event_changes` | `uint32_t` | 0 | 8 |
| `invalid_accel_bias_cov_reset` | `bool` | 0 | 8 |
| `reset_pos_to_gps` | `bool` | 0 | 8 |
| `reset_pos_to_last_known` | `bool` | 0 | 8 |
| `reset_pos_to_vision` | `bool` | 0 | 8 |
| `reset_vel_to_flow` | `bool` | 0 | 8 |
| `reset_vel_to_gps` | `bool` | 0 | 8 |
| `reset_vel_to_vision` | `bool` | 0 | 8 |
| `reset_vel_to_zero` | `bool` | 0 | 8 |
| `starting_gps_fusion` | `bool` | 0 | 8 |
| `starting_vision_pos_fusion` | `bool` | 0 | 8 |
| `starting_vision_vel_fusion` | `bool` | 0 | 8 |
| `starting_vision_yaw_fusion` | `bool` | 0 | 8 |
| `stopping_mag_use` | `bool` | 0 | 8 |
| `stopping_navigation` | `bool` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `vision_data_stopped` | `bool` | 0 | 8 |
| `warning_event_changes` | `uint32_t` | 0 | 8 |
| `yaw_aligned_to_imu_gps` | `bool` | 0 | 8 |

### `estimator_global_position`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `float` | 0 | 8 |
| `alt_ellipsoid` | `float` | 0 | 8 |
| `alt_reset_counter` | `uint8_t` | 0 | 8 |
| `dead_reckoning` | `bool` | 0 | 8 |
| `delta_alt` | `float` | 0 | 8 |
| `eph` | `float` | 0 | 8 |
| `epv` | `float` | 0 | 8 |
| `lat` | `double` | 0 | 8 |
| `lat_lon_reset_counter` | `uint8_t` | 0 | 8 |
| `lon` | `double` | 0 | 8 |
| `terrain_alt` | `float` | 0 | 8 |
| `terrain_alt_valid` | `bool` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_gps_status`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `check_fail_gps_fix` | `bool` | 0 | 8 |
| `check_fail_max_horz_drift` | `bool` | 0 | 8 |
| `check_fail_max_horz_err` | `bool` | 0 | 8 |
| `check_fail_max_horz_spd_err` | `bool` | 0 | 8 |
| `check_fail_max_pdop` | `bool` | 0 | 8 |
| `check_fail_max_spd_err` | `bool` | 0 | 8 |
| `check_fail_max_vert_drift` | `bool` | 0 | 8 |
| `check_fail_max_vert_err` | `bool` | 0 | 8 |
| `check_fail_max_vert_spd_err` | `bool` | 0 | 8 |
| `check_fail_min_sat_count` | `bool` | 0 | 8 |
| `checks_passed` | `bool` | 0 | 8 |
| `filtered_horizontal_speed_m_s` | `float` | 0 | 8 |
| `position_drift_rate_horizontal_m_s` | `float` | 0 | 8 |
| `position_drift_rate_vertical_m_s` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_innovation_test_ratios`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `airspeed` | `float` | 0 | 11 |
| `aux_hvel` | `float` | 2 | 11 |
| `aux_vvel` | `float` | 0 | 11 |
| `baro_vpos` | `float` | 0 | 11 |
| `beta` | `float` | 0 | 11 |
| `drag` | `float` | 2 | 11 |
| `ev_hpos` | `float` | 2 | 11 |
| `ev_hvel` | `float` | 2 | 11 |
| `ev_vpos` | `float` | 0 | 11 |
| `ev_vvel` | `float` | 0 | 11 |
| `fake_hpos` | `float` | 2 | 3 |
| `fake_hvel` | `float` | 2 | 3 |
| `fake_vpos` | `float` | 0 | 3 |
| `fake_vvel` | `float` | 0 | 3 |
| `flow` | `float` | 2 | 11 |
| `gps_hpos` | `float` | 2 | 11 |
| `gps_hvel` | `float` | 2 | 11 |
| `gps_vpos` | `float` | 0 | 11 |
| `gps_vvel` | `float` | 0 | 11 |
| `hagl` | `float` | 0 | 11 |
| `hagl_rate` | `float` | 0 | 8 |
| `heading` | `float` | 0 | 11 |
| `mag_field` | `float` | 3 | 11 |
| `rng_vpos` | `float` | 0 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_innovation_variances`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `airspeed` | `float` | 0 | 11 |
| `aux_hvel` | `float` | 2 | 11 |
| `aux_vvel` | `float` | 0 | 11 |
| `baro_vpos` | `float` | 0 | 11 |
| `beta` | `float` | 0 | 11 |
| `drag` | `float` | 2 | 11 |
| `ev_hpos` | `float` | 2 | 11 |
| `ev_hvel` | `float` | 2 | 11 |
| `ev_vpos` | `float` | 0 | 11 |
| `ev_vvel` | `float` | 0 | 11 |
| `fake_hpos` | `float` | 2 | 3 |
| `fake_hvel` | `float` | 2 | 3 |
| `fake_vpos` | `float` | 0 | 3 |
| `fake_vvel` | `float` | 0 | 3 |
| `flow` | `float` | 2 | 11 |
| `gps_hpos` | `float` | 2 | 11 |
| `gps_hvel` | `float` | 2 | 11 |
| `gps_vpos` | `float` | 0 | 11 |
| `gps_vvel` | `float` | 0 | 11 |
| `hagl` | `float` | 0 | 11 |
| `hagl_rate` | `float` | 0 | 8 |
| `heading` | `float` | 0 | 11 |
| `mag_field` | `float` | 3 | 11 |
| `rng_vpos` | `float` | 0 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_innovations`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `airspeed` | `float` | 0 | 11 |
| `aux_hvel` | `float` | 2 | 11 |
| `aux_vvel` | `float` | 0 | 11 |
| `baro_vpos` | `float` | 0 | 11 |
| `beta` | `float` | 0 | 11 |
| `drag` | `float` | 2 | 11 |
| `ev_hpos` | `float` | 2 | 11 |
| `ev_hvel` | `float` | 2 | 11 |
| `ev_vpos` | `float` | 0 | 11 |
| `ev_vvel` | `float` | 0 | 11 |
| `fake_hpos` | `float` | 2 | 3 |
| `fake_hvel` | `float` | 2 | 3 |
| `fake_vpos` | `float` | 0 | 3 |
| `fake_vvel` | `float` | 0 | 3 |
| `flow` | `float` | 2 | 11 |
| `gps_hpos` | `float` | 2 | 11 |
| `gps_hvel` | `float` | 2 | 11 |
| `gps_vpos` | `float` | 0 | 11 |
| `gps_vvel` | `float` | 0 | 11 |
| `hagl` | `float` | 0 | 11 |
| `hagl_rate` | `float` | 0 | 8 |
| `heading` | `float` | 0 | 11 |
| `mag_field` | `float` | 3 | 11 |
| `rng_vpos` | `float` | 0 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_local_position`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `ax` | `float` | 0 | 8 |
| `ay` | `float` | 0 | 8 |
| `az` | `float` | 0 | 8 |
| `delta_heading` | `float` | 0 | 8 |
| `delta_vxy` | `float` | 2 | 8 |
| `delta_vz` | `float` | 0 | 8 |
| `delta_xy` | `float` | 2 | 8 |
| `delta_z` | `float` | 0 | 8 |
| `dist_bottom` | `float` | 0 | 8 |
| `dist_bottom_sensor_bitfield` | `uint8_t` | 0 | 8 |
| `dist_bottom_valid` | `bool` | 0 | 8 |
| `eph` | `float` | 0 | 8 |
| `epv` | `float` | 0 | 8 |
| `evh` | `float` | 0 | 8 |
| `evv` | `float` | 0 | 8 |
| `hagl_max` | `float` | 0 | 8 |
| `hagl_min` | `float` | 0 | 8 |
| `heading` | `float` | 0 | 8 |
| `heading_good_for_control` | `bool` | 0 | 8 |
| `heading_reset_counter` | `uint8_t` | 0 | 8 |
| `ref_alt` | `float` | 0 | 8 |
| `ref_lat` | `double` | 0 | 8 |
| `ref_lon` | `double` | 0 | 8 |
| `ref_timestamp` | `uint64_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `v_xy_valid` | `bool` | 0 | 8 |
| `v_z_valid` | `bool` | 0 | 8 |
| `vx` | `float` | 0 | 8 |
| `vxy_max` | `float` | 0 | 8 |
| `vxy_reset_counter` | `uint8_t` | 0 | 8 |
| `vy` | `float` | 0 | 8 |
| `vz` | `float` | 0 | 8 |
| `vz_max` | `float` | 0 | 8 |
| `vz_reset_counter` | `uint8_t` | 0 | 8 |
| `x` | `float` | 0 | 8 |
| `xy_global` | `bool` | 0 | 8 |
| `xy_reset_counter` | `uint8_t` | 0 | 8 |
| `xy_valid` | `bool` | 0 | 8 |
| `y` | `float` | 0 | 8 |
| `z` | `float` | 0 | 8 |
| `z_deriv` | `float` | 0 | 8 |
| `z_global` | `bool` | 0 | 8 |
| `z_reset_counter` | `uint8_t` | 0 | 8 |
| `z_valid` | `bool` | 0 | 8 |

### `estimator_optical_flow_vel`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `flow_compensated_integral` | `float` | 2 | 8 |
| `flow_uncompensated_integral` | `float` | 2 | 8 |
| `gyro_rate_integral` | `float` | 3 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `vel_body` | `float` | 2 | 8 |
| `vel_ne` | `float` | 2 | 8 |

### `estimator_selector_status`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_device_id` | `uint32_t` | 0 | 8 |
| `accel_fault_detected` | `bool` | 0 | 8 |
| `accumulated_accel_error` | `float` | 4 | 8 |
| `accumulated_gyro_error` | `float` | 4 | 8 |
| `baro_device_id` | `uint32_t` | 0 | 8 |
| `combined_test_ratio` | `float` | 9 | 8 |
| `gyro_device_id` | `uint32_t` | 0 | 8 |
| `gyro_fault_detected` | `bool` | 0 | 8 |
| `healthy` | `bool` | 9 | 8 |
| `instance_changed_count` | `uint32_t` | 0 | 8 |
| `instances_available` | `uint8_t` | 0 | 8 |
| `last_instance_change` | `uint64_t` | 0 | 8 |
| `mag_device_id` | `uint32_t` | 0 | 8 |
| `primary_instance` | `uint8_t` | 0 | 8 |
| `relative_test_ratio` | `float` | 9 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |

### `estimator_sensor_bias`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_bias` | `float` | 3 | 11 |
| `accel_bias_limit` | `float` | 0 | 8 |
| `accel_bias_stable` | `bool` | 0 | 8 |
| `accel_bias_valid` | `bool` | 0 | 8 |
| `accel_bias_variance` | `float` | 3 | 8 |
| `accel_device_id` | `uint32_t` | 0 | 11 |
| `gyro_bias` | `float` | 3 | 11 |
| `gyro_bias_limit` | `float` | 0 | 8 |
| `gyro_bias_stable` | `bool` | 0 | 8 |
| `gyro_bias_valid` | `bool` | 0 | 8 |
| `gyro_bias_variance` | `float` | 3 | 8 |
| `gyro_device_id` | `uint32_t` | 0 | 11 |
| `mag_bias` | `float` | 3 | 11 |
| `mag_bias_limit` | `float` | 0 | 8 |
| `mag_bias_stable` | `bool` | 0 | 8 |
| `mag_bias_valid` | `bool` | 0 | 8 |
| `mag_bias_variance` | `float` | 3 | 8 |
| `mag_device_id` | `uint32_t` | 0 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_states`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `covariances` | `float` | 24 | 8 |
| `n_states` | `uint8_t` | 0 | 8 |
| `states` | `float` | 24 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_status`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_device_id` | `uint32_t` | 0 | 8 |
| `baro_device_id` | `uint32_t` | 0 | 8 |
| `beta_test_ratio` | `float` | 0 | 3962 |
| `control_mode_flags` | `uint32_t` | 0 | 3962 |
| `covariances` | `float` | 24 | 3954 |
| `filter_fault_flags` | `uint16_t` | 0 | 3954 |
| `filter_fault_flags` | `uint32_t` | 0 | 8 |
| `gps_check_fail_flags` | `uint16_t` | 0 | 3962 |
| `gyro_device_id` | `uint32_t` | 0 | 8 |
| `hagl_test_ratio` | `float` | 0 | 3962 |
| `health_flags` | `uint8_t` | 0 | 3962 |
| `hgt_test_ratio` | `float` | 0 | 3962 |
| `innovation_check_flags` | `uint16_t` | 0 | 3962 |
| `mag_device_id` | `uint32_t` | 0 | 8 |
| `mag_test_ratio` | `float` | 0 | 3962 |
| `n_states` | `float` | 0 | 2255 |
| `n_states` | `uint8_t` | 0 | 1699 |
| `nan_flags` | `uint8_t` | 0 | 2255 |
| `output_tracking_error` | `float` | 3 | 11 |
| `pos_horiz_accuracy` | `float` | 0 | 3962 |
| `pos_test_ratio` | `float` | 0 | 3962 |
| `pos_vert_accuracy` | `float` | 0 | 3962 |
| `pre_flt_fail` | `bool` | 0 | 2255 |
| `pre_flt_fail_innov_heading` | `bool` | 0 | 1707 |
| `pre_flt_fail_innov_height` | `bool` | 0 | 1707 |
| `pre_flt_fail_innov_vel_horiz` | `bool` | 0 | 1707 |
| `pre_flt_fail_innov_vel_vert` | `bool` | 0 | 1707 |
| `pre_flt_fail_mag_field_disturbed` | `bool` | 0 | 11 |
| `reset_count_pod_d` | `uint8_t` | 0 | 8 |
| `reset_count_pos_ne` | `uint8_t` | 0 | 8 |
| `reset_count_quat` | `uint8_t` | 0 | 8 |
| `reset_count_vel_d` | `uint8_t` | 0 | 8 |
| `reset_count_vel_ne` | `uint8_t` | 0 | 8 |
| `solution_status_flags` | `uint16_t` | 0 | 3962 |
| `states` | `float` | 24 | 3954 |
| `tas_test_ratio` | `float` | 0 | 3962 |
| `time_slip` | `float` | 0 | 3962 |
| `timeout_flags` | `uint8_t` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `vel_test_ratio` | `float` | 0 | 3962 |
| `vibe` | `float` | 3 | 3954 |

### `estimator_status_flags`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `control_status_changes` | `uint32_t` | 0 | 8 |
| `cs_baro_hgt` | `bool` | 0 | 8 |
| `cs_ev_hgt` | `bool` | 0 | 8 |
| `cs_ev_pos` | `bool` | 0 | 8 |
| `cs_ev_vel` | `bool` | 0 | 8 |
| `cs_ev_yaw` | `bool` | 0 | 8 |
| `cs_fixed_wing` | `bool` | 0 | 8 |
| `cs_fuse_aspd` | `bool` | 0 | 8 |
| `cs_fuse_beta` | `bool` | 0 | 8 |
| `cs_gnd_effect` | `bool` | 0 | 8 |
| `cs_gps` | `bool` | 0 | 8 |
| `cs_gps_hgt` | `bool` | 0 | 8 |
| `cs_gps_yaw` | `bool` | 0 | 8 |
| `cs_gps_yaw_fault` | `bool` | 0 | 8 |
| `cs_in_air` | `bool` | 0 | 8 |
| `cs_inertial_dead_reckoning` | `bool` | 0 | 8 |
| `cs_mag_3d` | `bool` | 0 | 8 |
| `cs_mag_aligned_in_flight` | `bool` | 0 | 8 |
| `cs_mag_dec` | `bool` | 0 | 8 |
| `cs_mag_fault` | `bool` | 0 | 8 |
| `cs_mag_field_disturbed` | `bool` | 0 | 8 |
| `cs_mag_hdg` | `bool` | 0 | 8 |
| `cs_opt_flow` | `bool` | 0 | 8 |
| `cs_rng_fault` | `bool` | 0 | 8 |
| `cs_rng_hgt` | `bool` | 0 | 8 |
| `cs_rng_kin_consistent` | `bool` | 0 | 8 |
| `cs_rng_stuck` | `bool` | 0 | 8 |
| `cs_synthetic_mag_z` | `bool` | 0 | 8 |
| `cs_tilt_align` | `bool` | 0 | 8 |
| `cs_vehicle_at_rest` | `bool` | 0 | 8 |
| `cs_wind` | `bool` | 0 | 8 |
| `cs_wind_dead_reckoning` | `bool` | 0 | 8 |
| `cs_yaw_align` | `bool` | 0 | 8 |
| `fault_status_changes` | `uint32_t` | 0 | 8 |
| `fs_bad_acc_bias` | `bool` | 0 | 8 |
| `fs_bad_acc_clipping` | `bool` | 0 | 8 |
| `fs_bad_acc_vertical` | `bool` | 0 | 8 |
| `fs_bad_airspeed` | `bool` | 0 | 8 |
| `fs_bad_hdg` | `bool` | 0 | 8 |
| `fs_bad_mag_decl` | `bool` | 0 | 8 |
| `fs_bad_mag_x` | `bool` | 0 | 8 |
| `fs_bad_mag_y` | `bool` | 0 | 8 |
| `fs_bad_mag_z` | `bool` | 0 | 8 |
| `fs_bad_optflow_x` | `bool` | 0 | 8 |
| `fs_bad_optflow_y` | `bool` | 0 | 8 |
| `fs_bad_pos_d` | `bool` | 0 | 8 |
| `fs_bad_pos_e` | `bool` | 0 | 8 |
| `fs_bad_pos_n` | `bool` | 0 | 8 |
| `fs_bad_sideslip` | `bool` | 0 | 8 |
| `fs_bad_vel_d` | `bool` | 0 | 8 |
| `fs_bad_vel_e` | `bool` | 0 | 8 |
| `fs_bad_vel_n` | `bool` | 0 | 8 |
| `innovation_fault_status_changes` | `uint32_t` | 0 | 8 |
| `reject_airspeed` | `bool` | 0 | 8 |
| `reject_hagl` | `bool` | 0 | 8 |
| `reject_hor_pos` | `bool` | 0 | 8 |
| `reject_hor_vel` | `bool` | 0 | 8 |
| `reject_mag_x` | `bool` | 0 | 8 |
| `reject_mag_y` | `bool` | 0 | 8 |
| `reject_mag_z` | `bool` | 0 | 8 |
| `reject_optflow_x` | `bool` | 0 | 8 |
| `reject_optflow_y` | `bool` | 0 | 8 |
| `reject_sideslip` | `bool` | 0 | 8 |
| `reject_ver_pos` | `bool` | 0 | 8 |
| `reject_ver_vel` | `bool` | 0 | 8 |
| `reject_yaw` | `bool` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `estimator_visual_odometry_aligned`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `local_frame` | `uint8_t` | 0 | 8 |
| `pitchspeed` | `float` | 0 | 8 |
| `pose_covariance` | `float` | 21 | 8 |
| `q` | `float` | 4 | 8 |
| `q_offset` | `float` | 4 | 8 |
| `reset_counter` | `uint8_t` | 0 | 8 |
| `rollspeed` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `velocity_covariance` | `float` | 21 | 8 |
| `velocity_frame` | `uint8_t` | 0 | 8 |
| `vx` | `float` | 0 | 8 |
| `vy` | `float` | 0 | 8 |
| `vz` | `float` | 0 | 8 |
| `x` | `float` | 0 | 8 |
| `y` | `float` | 0 | 8 |
| `yawspeed` | `float` | 0 | 8 |
| `z` | `float` | 0 | 8 |

### `estimator_wind`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `beta_innov` | `float` | 0 | 8 |
| `beta_innov_var` | `float` | 0 | 8 |
| `tas_innov` | `float` | 0 | 8 |
| `tas_innov_var` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `variance_east` | `float` | 0 | 8 |
| `variance_north` | `float` | 0 | 8 |
| `windspeed_east` | `float` | 0 | 8 |
| `windspeed_north` | `float` | 0 | 8 |

### `event`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `arguments` | `uint8_t` | 25 | 8 |
| `event_sequence` | `uint16_t` | 0 | 8 |
| `id` | `uint32_t` | 0 | 8 |
| `log_levels` | `uint8_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |

### `failure_detector_status`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `fd_alt` | `bool` | 0 | 8 |
| `fd_arm_escs` | `bool` | 0 | 8 |
| `fd_battery` | `bool` | 0 | 8 |
| `fd_ext` | `bool` | 0 | 8 |
| `fd_high_wind` | `bool` | 0 | 8 |
| `fd_imbalanced_prop` | `bool` | 0 | 8 |
| `fd_pitch` | `bool` | 0 | 8 |
| `fd_roll` | `bool` | 0 | 8 |
| `imbalanced_prop_metric` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |

### `follow_target`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `float` | 0 | 2255 |
| `est_cap` | `uint8_t` | 0 | 2255 |
| `lat` | `double` | 0 | 2255 |
| `lon` | `double` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `vx` | `float` | 0 | 2255 |
| `vy` | `float` | 0 | 2255 |
| `vz` | `float` | 0 | 2255 |

### `fw_pos_ctrl_status`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `abort_landing` | `bool` | 0 | 2255 |
| `landing_flare_length` | `float` | 0 | 2255 |
| `landing_horizontal_slope_displacement` | `float` | 0 | 2255 |
| `landing_slope_angle_rad` | `float` | 0 | 2255 |
| `nav_bearing` | `float` | 0 | 2255 |
| `nav_pitch` | `float` | 0 | 2255 |
| `nav_roll` | `float` | 0 | 2255 |
| `target_bearing` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `turn_distance` | `float` | 0 | 2255 |
| `wp_dist` | `float` | 0 | 2255 |
| `xtrack_error` | `float` | 0 | 2255 |

### `fw_virtual_attitude_setpoint`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `apply_flaps` | `bool` | 0 | 2255 |
| `disable_mc_yaw_control` | `bool` | 0 | 2255 |
| `fw_control_yaw` | `bool` | 0 | 2255 |
| `landing_gear` | `float` | 0 | 2255 |
| `pitch_body` | `float` | 0 | 2255 |
| `pitch_reset_integral` | `bool` | 0 | 2255 |
| `q_d` | `float` | 4 | 2255 |
| `q_d_valid` | `bool` | 0 | 2255 |
| `roll_body` | `float` | 0 | 2255 |
| `roll_reset_integral` | `bool` | 0 | 2255 |
| `thrust` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `yaw_body` | `float` | 0 | 2255 |
| `yaw_reset_integral` | `bool` | 0 | 2255 |
| `yaw_sp_move_rate` | `float` | 0 | 2255 |

### `fw_virtual_rates_setpoint`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `pitch` | `float` | 0 | 2255 |
| `roll` | `float` | 0 | 2255 |
| `thrust` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `yaw` | `float` | 0 | 2255 |

### `geofence_result`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `geofence_action` | `uint8_t` | 0 | 2255 |
| `geofence_violated` | `bool` | 0 | 2255 |
| `home_required` | `bool` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `gps_dump`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `data` | `uint8_t` | 79 | 2255 |
| `len` | `uint8_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `gps_inject_data`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `data` | `uint8_t` | 182 | 2255 |
| `flags` | `uint8_t` | 0 | 2255 |
| `len` | `uint8_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `home_position`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `float` | 0 | 3962 |
| `lat` | `double` | 0 | 3962 |
| `lon` | `double` | 0 | 3962 |
| `manual_home` | `bool` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `valid_alt` | `bool` | 0 | 3962 |
| `valid_hpos` | `bool` | 0 | 3962 |
| `valid_lpos` | `bool` | 0 | 8 |
| `x` | `float` | 0 | 3962 |
| `y` | `float` | 0 | 3962 |
| `yaw` | `float` | 0 | 3962 |
| `z` | `float` | 0 | 3962 |

### `hover_thrust_estimate`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_innov` | `float` | 0 | 11 |
| `accel_innov_test_ratio` | `float` | 0 | 11 |
| `accel_innov_var` | `float` | 0 | 11 |
| `accel_noise_var` | `float` | 0 | 11 |
| `hover_thrust` | `float` | 0 | 11 |
| `hover_thrust_var` | `float` | 0 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |
| `valid` | `bool` | 0 | 11 |

### `input_rc`

Declared in 3962 headers; selected records observed in 20/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `channel_count` | `uint32_t` | 0 | 3951 |
| `channel_count` | `uint8_t` | 0 | 11 |
| `input_source` | `uint8_t` | 0 | 3962 |
| `rc_failsafe` | `bool` | 0 | 3962 |
| `rc_lost` | `bool` | 0 | 3962 |
| `rc_lost_frame_count` | `uint16_t` | 0 | 3962 |
| `rc_ppm_frame_length` | `uint16_t` | 0 | 3962 |
| `rc_total_frame_count` | `uint16_t` | 0 | 3962 |
| `rssi` | `int32_t` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_last_signal` | `uint64_t` | 0 | 3962 |
| `values` | `uint16_t` | 18 | 3962 |

### `iridiumsbd_status`

Declared in 2149 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `failed_sbd_sessions` | `uint16_t` | 0 | 2149 |
| `last_heartbeat` | `uint64_t` | 0 | 2149 |
| `num_tx_buf_reset` | `uint16_t` | 0 | 2149 |
| `ring_pending` | `bool` | 0 | 2149 |
| `rx_buf_end_index` | `uint16_t` | 0 | 2149 |
| `rx_buf_read_index` | `uint16_t` | 0 | 2149 |
| `rx_read_pending` | `bool` | 0 | 2149 |
| `rx_session_pending` | `bool` | 0 | 2149 |
| `signal_quality` | `uint8_t` | 0 | 2149 |
| `state` | `uint8_t` | 0 | 2149 |
| `successful_sbd_sessions` | `uint16_t` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |
| `tx_buf_write_index` | `uint16_t` | 0 | 2149 |
| `tx_buf_write_pending` | `bool` | 0 | 2149 |
| `tx_session_pending` | `bool` | 0 | 2149 |

### `irlock_report`

Declared in 2149 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `pos_x` | `float` | 0 | 2149 |
| `pos_y` | `float` | 0 | 2149 |
| `signature` | `uint16_t` | 0 | 2149 |
| `size_x` | `float` | 0 | 2149 |
| `size_y` | `float` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |

### `landing_target_innovations`

Declared in 2149 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `innov_cov_x` | `float` | 0 | 2149 |
| `innov_cov_y` | `float` | 0 | 2149 |
| `innov_x` | `float` | 0 | 2149 |
| `innov_y` | `float` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |

### `landing_target_pose`

Declared in 2149 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `abs_pos_valid` | `bool` | 0 | 2149 |
| `cov_vx_rel` | `float` | 0 | 2149 |
| `cov_vy_rel` | `float` | 0 | 2149 |
| `cov_x_rel` | `float` | 0 | 2149 |
| `cov_y_rel` | `float` | 0 | 2149 |
| `is_static` | `bool` | 0 | 2149 |
| `rel_pos_valid` | `bool` | 0 | 2149 |
| `rel_vel_valid` | `bool` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |
| `vx_rel` | `float` | 0 | 2149 |
| `vy_rel` | `float` | 0 | 2149 |
| `x_abs` | `float` | 0 | 2149 |
| `x_rel` | `float` | 0 | 2149 |
| `y_abs` | `float` | 0 | 2149 |
| `y_rel` | `float` | 0 | 2149 |
| `z_abs` | `float` | 0 | 2149 |
| `z_rel` | `float` | 0 | 2149 |

### `led_control`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `color` | `uint8_t` | 0 | 2255 |
| `led_mask` | `uint8_t` | 0 | 2255 |
| `mode` | `uint8_t` | 0 | 2255 |
| `num_blinks` | `uint8_t` | 0 | 2255 |
| `priority` | `uint8_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `log_message`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `severity` | `uint8_t` | 0 | 2255 |
| `text` | `uint8_t` | 127 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `logger_status`

Declared in 3 headers; selected records observed in 1/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `backend` | `uint8_t` | 0 | 3 |
| `buffer_size_bytes` | `uint32_t` | 0 | 3 |
| `buffer_used_bytes` | `uint32_t` | 0 | 3 |
| `dropouts` | `uint32_t` | 0 | 3 |
| `message_gaps` | `uint32_t` | 0 | 3 |
| `num_messages` | `uint8_t` | 0 | 3 |
| `timestamp` | `uint64_t` | 0 | 3 |
| `total_written_kb` | `float` | 0 | 3 |
| `type` | `uint8_t` | 0 | 3 |
| `write_rate_kb_s` | `float` | 0 | 3 |

### `magnetometer_bias_estimate`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `bias_x` | `float` | 4 | 8 |
| `bias_y` | `float` | 4 | 8 |
| `bias_z` | `float` | 4 | 8 |
| `stable` | `bool` | 4 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `valid` | `bool` | 4 | 8 |

### `manual_control_setpoint`

Declared in 3962 headers; selected records observed in 20/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `acro_switch` | `uint8_t` | 0 | 3954 |
| `arm_switch` | `uint8_t` | 0 | 3954 |
| `aux1` | `float` | 0 | 3962 |
| `aux2` | `float` | 0 | 3962 |
| `aux3` | `float` | 0 | 3962 |
| `aux4` | `float` | 0 | 3962 |
| `aux5` | `float` | 0 | 3962 |
| `aux6` | `float` | 0 | 1707 |
| `data_source` | `uint8_t` | 0 | 3962 |
| `flaps` | `float` | 0 | 3962 |
| `gear_switch` | `uint8_t` | 0 | 3954 |
| `kill_switch` | `uint8_t` | 0 | 3954 |
| `loiter_switch` | `uint8_t` | 0 | 3954 |
| `man_switch` | `uint8_t` | 0 | 3954 |
| `mode_slot` | `int8_t` | 0 | 2255 |
| `mode_slot` | `uint8_t` | 0 | 1699 |
| `mode_switch` | `uint8_t` | 0 | 3954 |
| `offboard_switch` | `uint8_t` | 0 | 3954 |
| `posctl_switch` | `uint8_t` | 0 | 3954 |
| `r` | `float` | 0 | 3962 |
| `rattitude_switch` | `uint8_t` | 0 | 3954 |
| `return_switch` | `uint8_t` | 0 | 3954 |
| `stab_switch` | `uint8_t` | 0 | 3954 |
| `sticks_moving` | `bool` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `transition_switch` | `uint8_t` | 0 | 3954 |
| `valid` | `bool` | 0 | 8 |
| `x` | `float` | 0 | 3962 |
| `y` | `float` | 0 | 3962 |
| `z` | `float` | 0 | 3962 |

### `manual_control_switches`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `arm_switch` | `uint8_t` | 0 | 8 |
| `gear_switch` | `uint8_t` | 0 | 8 |
| `kill_switch` | `uint8_t` | 0 | 8 |
| `loiter_switch` | `uint8_t` | 0 | 8 |
| `mode_slot` | `uint8_t` | 0 | 8 |
| `offboard_switch` | `uint8_t` | 0 | 8 |
| `photo_switch` | `uint8_t` | 0 | 8 |
| `return_switch` | `uint8_t` | 0 | 8 |
| `switch_changes` | `uint32_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `transition_switch` | `uint8_t` | 0 | 8 |
| `video_switch` | `uint8_t` | 0 | 8 |

### `mavlink_log`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `severity` | `uint8_t` | 0 | 2255 |
| `text` | `uint8_t` | 50 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `mc_att_ctrl_status`

Declared in 106 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `pitch_rate_integ` | `float` | 0 | 106 |
| `roll_rate_integ` | `float` | 0 | 106 |
| `timestamp` | `uint64_t` | 0 | 106 |
| `yaw_rate_integ` | `float` | 0 | 106 |

### `mc_virtual_attitude_setpoint`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `apply_flaps` | `bool` | 0 | 2255 |
| `disable_mc_yaw_control` | `bool` | 0 | 2255 |
| `fw_control_yaw` | `bool` | 0 | 2255 |
| `landing_gear` | `float` | 0 | 2255 |
| `pitch_body` | `float` | 0 | 2255 |
| `pitch_reset_integral` | `bool` | 0 | 2255 |
| `q_d` | `float` | 4 | 2255 |
| `q_d_valid` | `bool` | 0 | 2255 |
| `roll_body` | `float` | 0 | 2255 |
| `roll_reset_integral` | `bool` | 0 | 2255 |
| `thrust` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `yaw_body` | `float` | 0 | 2255 |
| `yaw_reset_integral` | `bool` | 0 | 2255 |
| `yaw_sp_move_rate` | `float` | 0 | 2255 |

### `mc_virtual_rates_setpoint`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `pitch` | `float` | 0 | 2255 |
| `roll` | `float` | 0 | 2255 |
| `thrust` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `yaw` | `float` | 0 | 2255 |

### `mission`

Declared in 3954 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `count` | `uint16_t` | 0 | 3954 |
| `current_seq` | `int32_t` | 0 | 3954 |
| `dataman_id` | `int8_t` | 0 | 106 |
| `dataman_id` | `uint8_t` | 0 | 3848 |
| `timestamp` | `uint64_t` | 0 | 3954 |

### `mission_result`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `execution_mode` | `uint8_t` | 0 | 3856 |
| `failure` | `bool` | 0 | 3962 |
| `finished` | `bool` | 0 | 3962 |
| `flight_termination` | `bool` | 0 | 3962 |
| `instance_count` | `uint32_t` | 0 | 3962 |
| `item_changed_index` | `uint16_t` | 0 | 3962 |
| `item_do_jump_changed` | `bool` | 0 | 3962 |
| `item_do_jump_remaining` | `uint16_t` | 0 | 3962 |
| `seq_current` | `uint16_t` | 0 | 3962 |
| `seq_reached` | `int32_t` | 0 | 3962 |
| `seq_total` | `uint16_t` | 0 | 3962 |
| `stay_in_failsafe` | `bool` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `valid` | `bool` | 0 | 3962 |
| `warning` | `bool` | 0 | 3962 |

### `mount_orientation`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `attitude_euler_angle` | `float` | 3 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `multirotor_motor_limits`

Declared in 2258 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `saturation_status` | `uint16_t` | 0 | 2258 |
| `timestamp` | `uint64_t` | 0 | 2258 |

### `navigator_mission_item`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `acceptance_radius` | `float` | 0 | 8 |
| `altitude` | `float` | 0 | 8 |
| `altitude_is_relative` | `bool` | 0 | 8 |
| `autocontinue` | `bool` | 0 | 8 |
| `force_heading` | `bool` | 0 | 8 |
| `frame` | `uint8_t` | 0 | 8 |
| `instance_count` | `uint32_t` | 0 | 8 |
| `latitude` | `float` | 0 | 8 |
| `loiter_exit_xtrack` | `bool` | 0 | 8 |
| `loiter_radius` | `float` | 0 | 8 |
| `longitude` | `float` | 0 | 8 |
| `nav_cmd` | `uint16_t` | 0 | 8 |
| `origin` | `uint8_t` | 0 | 8 |
| `sequence_current` | `uint16_t` | 0 | 8 |
| `time_inside` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `vtol_back_transition` | `bool` | 0 | 8 |
| `yaw` | `float` | 0 | 8 |

### `npfg_status`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `adapted_period` | `float` | 0 | 8 |
| `airspeed_ref` | `float` | 0 | 8 |
| `bearing` | `float` | 0 | 8 |
| `bearing_feas` | `float` | 0 | 8 |
| `bearing_feas_on_track` | `float` | 0 | 8 |
| `heading_ref` | `float` | 0 | 8 |
| `lat_accel` | `float` | 0 | 8 |
| `lat_accel_ff` | `float` | 0 | 8 |
| `min_ground_speed_ref` | `float` | 0 | 8 |
| `p_gain` | `float` | 0 | 8 |
| `signed_track_error` | `float` | 0 | 8 |
| `time_const` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `track_error_bound` | `float` | 0 | 8 |
| `wind_est_valid` | `uint8_t` | 0 | 8 |

### `obstacle_distance`

Declared in 2149 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `distances` | `uint16_t` | 72 | 2149 |
| `increment` | `uint8_t` | 0 | 2149 |
| `max_distance` | `uint16_t` | 0 | 2149 |
| `min_distance` | `uint16_t` | 0 | 2149 |
| `sensor_type` | `uint8_t` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |

### `offboard_control_mode`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `acceleration` | `bool` | 0 | 8 |
| `actuator` | `bool` | 0 | 8 |
| `attitude` | `bool` | 0 | 8 |
| `body_rate` | `bool` | 0 | 8 |
| `ignore_acceleration_force` | `bool` | 0 | 2258 |
| `ignore_alt_hold` | `bool` | 0 | 2258 |
| `ignore_attitude` | `bool` | 0 | 2258 |
| `ignore_bodyrate` | `bool` | 0 | 2255 |
| `ignore_bodyrate_x` | `bool` | 0 | 3 |
| `ignore_bodyrate_y` | `bool` | 0 | 3 |
| `ignore_bodyrate_z` | `bool` | 0 | 3 |
| `ignore_position` | `bool` | 0 | 2258 |
| `ignore_thrust` | `bool` | 0 | 2258 |
| `ignore_velocity` | `bool` | 0 | 2258 |
| `position` | `bool` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 2266 |
| `velocity` | `bool` | 0 | 8 |

### `offboard_mission`

Declared in 106 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `count` | `uint16_t` | 0 | 106 |
| `current_seq` | `int32_t` | 0 | 106 |
| `dataman_id` | `int8_t` | 0 | 106 |
| `timestamp` | `uint64_t` | 0 | 106 |

### `onboard_computer_status`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `cpu_combined` | `uint8_t` | 10 | 11 |
| `cpu_cores` | `uint8_t` | 8 | 11 |
| `fan_speed` | `int16_t` | 4 | 11 |
| `gpu_combined` | `uint8_t` | 10 | 11 |
| `gpu_cores` | `uint8_t` | 4 | 11 |
| `link_rx_max` | `uint32_t` | 6 | 11 |
| `link_rx_rate` | `uint32_t` | 6 | 11 |
| `link_tx_max` | `uint32_t` | 6 | 11 |
| `link_tx_rate` | `uint32_t` | 6 | 11 |
| `link_type` | `uint32_t` | 6 | 11 |
| `ram_total` | `uint32_t` | 0 | 11 |
| `ram_usage` | `uint32_t` | 0 | 11 |
| `storage_total` | `uint32_t` | 4 | 11 |
| `storage_type` | `uint32_t` | 4 | 11 |
| `storage_usage` | `uint32_t` | 4 | 11 |
| `temperature_board` | `int8_t` | 0 | 11 |
| `temperature_core` | `int8_t` | 8 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `type` | `uint8_t` | 0 | 11 |
| `uptime` | `uint32_t` | 0 | 11 |

### `onboard_mission`

Declared in 106 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `count` | `uint16_t` | 0 | 106 |
| `current_seq` | `int32_t` | 0 | 106 |
| `dataman_id` | `int8_t` | 0 | 106 |
| `timestamp` | `uint64_t` | 0 | 106 |

### `optical_flow`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `frame_count_since_last_readout` | `uint16_t` | 0 | 3962 |
| `ground_distance_m` | `float` | 0 | 3962 |
| `gyro_temperature` | `int16_t` | 0 | 3962 |
| `gyro_x_rate_integral` | `float` | 0 | 3962 |
| `gyro_y_rate_integral` | `float` | 0 | 3962 |
| `gyro_z_rate_integral` | `float` | 0 | 3962 |
| `integration_timespan` | `uint32_t` | 0 | 3962 |
| `max_flow_rate` | `float` | 0 | 3856 |
| `max_ground_distance` | `float` | 0 | 3856 |
| `min_ground_distance` | `float` | 0 | 3856 |
| `mode` | `uint8_t` | 0 | 8 |
| `pixel_flow_x_integral` | `float` | 0 | 3962 |
| `pixel_flow_y_integral` | `float` | 0 | 3962 |
| `quality` | `uint8_t` | 0 | 3962 |
| `sensor_id` | `uint8_t` | 0 | 3962 |
| `time_since_last_sonar_update` | `uint32_t` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |

### `parameter_update`

Declared in 2263 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `active` | `uint16_t` | 0 | 8 |
| `changed` | `uint16_t` | 0 | 8 |
| `custom_default` | `uint16_t` | 0 | 8 |
| `dummy` | `uint32_t` | 0 | 106 |
| `export_count` | `uint32_t` | 0 | 8 |
| `find_count` | `uint32_t` | 0 | 8 |
| `get_count` | `uint32_t` | 0 | 8 |
| `instance` | `uint32_t` | 0 | 2157 |
| `set_count` | `uint32_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 2263 |

### `ping`

Declared in 2149 headers; selected records observed in 7/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `component_id` | `uint8_t` | 0 | 2149 |
| `dropped_packets` | `uint32_t` | 0 | 2149 |
| `ping_sequence` | `uint32_t` | 0 | 2149 |
| `ping_time` | `uint64_t` | 0 | 2149 |
| `rtt_ms` | `float` | 0 | 2149 |
| `system_id` | `uint8_t` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |

### `position_controller_status`

Declared in 1707 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `acceptance_radius` | `float` | 0 | 1707 |
| `altitude_acceptance` | `float` | 0 | 1707 |
| `nav_bearing` | `float` | 0 | 1707 |
| `nav_pitch` | `float` | 0 | 1707 |
| `nav_roll` | `float` | 0 | 1707 |
| `target_bearing` | `float` | 0 | 1707 |
| `timestamp` | `uint64_t` | 0 | 1707 |
| `type` | `uint8_t` | 0 | 8 |
| `wp_dist` | `float` | 0 | 1707 |
| `xtrack_error` | `float` | 0 | 1707 |
| `yaw_acceptance` | `float` | 0 | 1707 |

### `position_setpoint`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `a_x` | `float` | 0 | 3954 |
| `a_y` | `float` | 0 | 3954 |
| `a_z` | `float` | 0 | 3954 |
| `acceleration_is_force` | `bool` | 0 | 3954 |
| `acceleration_valid` | `bool` | 0 | 3954 |
| `acceptance_radius` | `float` | 0 | 3962 |
| `allow_weather_vane` | `bool` | 0 | 1696 |
| `alt` | `float` | 0 | 3962 |
| `alt_valid` | `bool` | 0 | 3962 |
| `cruising_speed` | `float` | 0 | 3962 |
| `cruising_throttle` | `float` | 0 | 3962 |
| `disable_weather_vane` | `bool` | 0 | 11 |
| `landing_gear` | `int8_t` | 0 | 1707 |
| `lat` | `double` | 0 | 3962 |
| `loiter_direction` | `int8_t` | 0 | 3962 |
| `loiter_radius` | `float` | 0 | 3962 |
| `lon` | `double` | 0 | 3962 |
| `pitch_min` | `float` | 0 | 3954 |
| `position_valid` | `bool` | 0 | 3954 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `type` | `uint8_t` | 0 | 3962 |
| `valid` | `bool` | 0 | 3962 |
| `velocity_frame` | `uint8_t` | 0 | 3962 |
| `velocity_valid` | `bool` | 0 | 3962 |
| `vx` | `float` | 0 | 3962 |
| `vy` | `float` | 0 | 3962 |
| `vz` | `float` | 0 | 3962 |
| `x` | `float` | 0 | 3954 |
| `y` | `float` | 0 | 3954 |
| `yaw` | `float` | 0 | 3962 |
| `yaw_valid` | `bool` | 0 | 3962 |
| `yawspeed` | `float` | 0 | 3962 |
| `yawspeed_valid` | `bool` | 0 | 3962 |
| `z` | `float` | 0 | 3954 |

### `position_setpoint_triplet`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `current` | `position_setpoint` | 0 | 3962 |
| `next` | `position_setpoint` | 0 | 3962 |
| `previous` | `position_setpoint` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |

### `power_button_state`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `event` | `uint8_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `pwm_input`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `error_count` | `uint64_t` | 0 | 2255 |
| `period` | `uint32_t` | 0 | 2255 |
| `pulse_width` | `uint32_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `px4io_status`

Declared in 3 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `actuators` | `int16_t` | 8 | 3 |
| `alarm_acc_current` | `bool` | 0 | 3 |
| `alarm_fmu_lost` | `bool` | 0 | 3 |
| `alarm_pwm_error` | `bool` | 0 | 3 |
| `alarm_rc_lost` | `bool` | 0 | 3 |
| `alarm_servo_current` | `bool` | 0 | 3 |
| `alarm_temperature` | `bool` | 0 | 3 |
| `alarm_vbatt_low` | `bool` | 0 | 3 |
| `alarm_vservo_fault` | `bool` | 0 | 3 |
| `arming_always_pwm_enable` | `bool` | 0 | 3 |
| `arming_failsafe_custom` | `bool` | 0 | 3 |
| `arming_fmu_armed` | `bool` | 0 | 3 |
| `arming_fmu_prearmed` | `bool` | 0 | 3 |
| `arming_force_failsafe` | `bool` | 0 | 3 |
| `arming_inair_restart_ok` | `bool` | 0 | 3 |
| `arming_io_arm_ok` | `bool` | 0 | 3 |
| `arming_lockdown` | `bool` | 0 | 3 |
| `arming_manual_override_ok` | `bool` | 0 | 3 |
| `arming_override_immediate` | `bool` | 0 | 3 |
| `arming_rc_handling_disabled` | `bool` | 0 | 3 |
| `arming_termination_failsafe` | `bool` | 0 | 3 |
| `free_memory_bytes` | `uint16_t` | 0 | 3 |
| `raw_inputs` | `uint16_t` | 18 | 3 |
| `rssi_v` | `float` | 0 | 3 |
| `servos` | `uint16_t` | 8 | 3 |
| `status_arm_sync` | `bool` | 0 | 3 |
| `status_failsafe` | `bool` | 0 | 3 |
| `status_fmu_initialized` | `bool` | 0 | 3 |
| `status_fmu_ok` | `bool` | 0 | 3 |
| `status_init_ok` | `bool` | 0 | 3 |
| `status_mixer_ok` | `bool` | 0 | 3 |
| `status_outputs_armed` | `bool` | 0 | 3 |
| `status_override` | `bool` | 0 | 3 |
| `status_raw_pwm` | `bool` | 0 | 3 |
| `status_rc_dsm` | `bool` | 0 | 3 |
| `status_rc_ok` | `bool` | 0 | 3 |
| `status_rc_ppm` | `bool` | 0 | 3 |
| `status_rc_sbus` | `bool` | 0 | 3 |
| `status_rc_st24` | `bool` | 0 | 3 |
| `status_rc_sumd` | `bool` | 0 | 3 |
| `status_safety_off` | `bool` | 0 | 3 |
| `timestamp` | `uint64_t` | 0 | 3 |
| `voltage_v` | `float` | 0 | 3 |

### `qshell_req`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `string` | `int32_t` | 100 | 2255 |
| `strlen` | `uint64_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `radio_status`

Declared in 1707 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `fix` | `uint16_t` | 0 | 1707 |
| `noise` | `uint8_t` | 0 | 1707 |
| `remote_noise` | `uint8_t` | 0 | 1707 |
| `remote_rssi` | `uint8_t` | 0 | 1707 |
| `rssi` | `uint8_t` | 0 | 1707 |
| `rxerrors` | `uint16_t` | 0 | 1707 |
| `timestamp` | `uint64_t` | 0 | 1707 |
| `txbuf` | `uint8_t` | 0 | 1707 |

### `rate_ctrl_status`

Declared in 3856 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `additional_integ1` | `float` | 0 | 3856 |
| `pitchspeed` | `float` | 0 | 2149 |
| `pitchspeed_integ` | `float` | 0 | 3856 |
| `rollspeed` | `float` | 0 | 2149 |
| `rollspeed_integ` | `float` | 0 | 3856 |
| `timestamp` | `uint64_t` | 0 | 3856 |
| `yawspeed` | `float` | 0 | 2149 |
| `yawspeed_integ` | `float` | 0 | 3856 |

### `rc_channels`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `channel_count` | `uint8_t` | 0 | 2255 |
| `channels` | `float` | 18 | 2255 |
| `frame_drop_count` | `uint32_t` | 0 | 2255 |
| `function` | `int8_t` | 26 | 2255 |
| `rssi` | `uint8_t` | 0 | 2255 |
| `signal_lost` | `bool` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp_last_valid` | `uint64_t` | 0 | 2255 |

### `rc_parameter_map`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `param_id` | `char` | 51 | 2255 |
| `param_index` | `int32_t` | 3 | 2255 |
| `scale` | `float` | 3 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `valid` | `bool` | 3 | 2255 |
| `value0` | `float` | 3 | 2255 |
| `value_max` | `float` | 3 | 2255 |
| `value_min` | `float` | 3 | 2255 |

### `rpm`

Declared in 3 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `estimated_accurancy_rpm` | `float` | 0 | 3 |
| `indicated_frequency_rpm` | `float` | 0 | 3 |
| `timestamp` | `uint64_t` | 0 | 3 |

### `rtl_time_estimate`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `safe_time_estimate` | `float` | 0 | 8 |
| `time_estimate` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `valid` | `bool` | 0 | 8 |

### `safety`

Declared in 3736 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `override_available` | `bool` | 0 | 3728 |
| `override_enabled` | `bool` | 0 | 3728 |
| `safety_off` | `bool` | 0 | 3736 |
| `safety_switch_available` | `bool` | 0 | 3736 |
| `timestamp` | `uint64_t` | 0 | 3736 |

### `satellite_info`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `azimuth` | `uint8_t` | 20 | 2255 |
| `count` | `uint8_t` | 0 | 2255 |
| `elevation` | `uint8_t` | 20 | 2255 |
| `snr` | `uint8_t` | 20 | 2255 |
| `svid` | `uint8_t` | 20 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `used` | `uint8_t` | 20 | 2255 |

### `sensor_accel`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `clip_counter` | `uint8_t` | 3 | 11 |
| `device_id` | `uint32_t` | 0 | 2266 |
| `error_count` | `uint32_t` | 0 | 11 |
| `error_count` | `uint64_t` | 0 | 2255 |
| `integral_dt` | `uint64_t` | 0 | 2255 |
| `range_m_s2` | `float` | 0 | 2255 |
| `samples` | `uint8_t` | 0 | 8 |
| `scaling` | `float` | 0 | 2255 |
| `temperature` | `float` | 0 | 2266 |
| `temperature_raw` | `int16_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2266 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |
| `x` | `float` | 0 | 2266 |
| `x_integral` | `float` | 0 | 2255 |
| `x_raw` | `int16_t` | 0 | 2255 |
| `y` | `float` | 0 | 2266 |
| `y_integral` | `float` | 0 | 2255 |
| `y_raw` | `int16_t` | 0 | 2255 |
| `z` | `float` | 0 | 2266 |
| `z_integral` | `float` | 0 | 2255 |
| `z_raw` | `int16_t` | 0 | 2255 |

### `sensor_baro`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `altitude` | `float` | 0 | 106 |
| `device_id` | `uint32_t` | 0 | 2266 |
| `error_count` | `uint32_t` | 0 | 11 |
| `error_count` | `uint64_t` | 0 | 2255 |
| `pressure` | `float` | 0 | 2266 |
| `temperature` | `float` | 0 | 2266 |
| `timestamp` | `uint64_t` | 0 | 2266 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |

### `sensor_bias`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_x` | `float` | 0 | 2255 |
| `accel_x_bias` | `float` | 0 | 2255 |
| `accel_y` | `float` | 0 | 2255 |
| `accel_y_bias` | `float` | 0 | 2255 |
| `accel_z` | `float` | 0 | 2255 |
| `accel_z_bias` | `float` | 0 | 2255 |
| `gyro_x` | `float` | 0 | 106 |
| `gyro_x_bias` | `float` | 0 | 2255 |
| `gyro_y` | `float` | 0 | 106 |
| `gyro_y_bias` | `float` | 0 | 2255 |
| `gyro_z` | `float` | 0 | 106 |
| `gyro_z_bias` | `float` | 0 | 2255 |
| `mag_x` | `float` | 0 | 106 |
| `mag_x_bias` | `float` | 0 | 2255 |
| `mag_y` | `float` | 0 | 106 |
| `mag_y_bias` | `float` | 0 | 2255 |
| `mag_z` | `float` | 0 | 106 |
| `mag_z_bias` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `sensor_combined`

Declared in 3962 headers; selected records observed in 20/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_calibration_count` | `uint8_t` | 0 | 8 |
| `accelerometer_clipping` | `uint8_t` | 0 | 11 |
| `accelerometer_integral_dt` | `uint32_t` | 0 | 3962 |
| `accelerometer_m_s2` | `float` | 3 | 3962 |
| `accelerometer_timestamp_relative` | `int32_t` | 0 | 3962 |
| `baro_alt_meter` | `float` | 0 | 106 |
| `baro_temp_celcius` | `float` | 0 | 106 |
| `baro_timestamp_relative` | `int32_t` | 0 | 106 |
| `gyro_calibration_count` | `uint8_t` | 0 | 8 |
| `gyro_integral_dt` | `uint32_t` | 0 | 3962 |
| `gyro_rad` | `float` | 3 | 3962 |
| `magnetometer_ga` | `float` | 3 | 106 |
| `magnetometer_timestamp_relative` | `int32_t` | 0 | 106 |
| `timestamp` | `uint64_t` | 0 | 3962 |

### `sensor_correction`

Declared in 2258 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_device_ids` | `uint32_t` | 3 | 3 |
| `accel_mapping` | `uint8_t` | 3 | 2255 |
| `accel_offset_0` | `float` | 3 | 2258 |
| `accel_offset_1` | `float` | 3 | 2258 |
| `accel_offset_2` | `float` | 3 | 2258 |
| `accel_scale_0` | `float` | 3 | 2255 |
| `accel_scale_1` | `float` | 3 | 2255 |
| `accel_scale_2` | `float` | 3 | 2255 |
| `baro_device_ids` | `uint32_t` | 3 | 3 |
| `baro_mapping` | `uint8_t` | 3 | 2255 |
| `baro_offset_0` | `float` | 0 | 2258 |
| `baro_offset_1` | `float` | 0 | 2258 |
| `baro_offset_2` | `float` | 0 | 2258 |
| `baro_scale_0` | `float` | 0 | 2255 |
| `baro_scale_1` | `float` | 0 | 2255 |
| `baro_scale_2` | `float` | 0 | 2255 |
| `gyro_device_ids` | `uint32_t` | 3 | 3 |
| `gyro_mapping` | `uint8_t` | 3 | 2255 |
| `gyro_offset_0` | `float` | 3 | 2258 |
| `gyro_offset_1` | `float` | 3 | 2258 |
| `gyro_offset_2` | `float` | 3 | 2258 |
| `gyro_scale_0` | `float` | 3 | 2255 |
| `gyro_scale_1` | `float` | 3 | 2255 |
| `gyro_scale_2` | `float` | 3 | 2255 |
| `selected_accel_instance` | `uint8_t` | 0 | 2255 |
| `selected_baro_instance` | `uint8_t` | 0 | 2255 |
| `selected_gyro_instance` | `uint8_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2258 |

### `sensor_gnss_relative`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accuracy_length` | `float` | 0 | 8 |
| `carrier_solution_fixed` | `bool` | 0 | 8 |
| `carrier_solution_floating` | `bool` | 0 | 8 |
| `device_id` | `uint32_t` | 0 | 8 |
| `differential_solution` | `bool` | 0 | 8 |
| `gnss_fix_ok` | `bool` | 0 | 8 |
| `heading` | `float` | 0 | 8 |
| `heading_accuracy` | `float` | 0 | 8 |
| `heading_valid` | `bool` | 0 | 8 |
| `moving_base_mode` | `bool` | 0 | 8 |
| `position` | `float` | 3 | 8 |
| `position_accuracy` | `float` | 3 | 8 |
| `position_length` | `float` | 0 | 8 |
| `reference_observations_miss` | `bool` | 0 | 8 |
| `reference_position_miss` | `bool` | 0 | 8 |
| `reference_station_id` | `uint16_t` | 0 | 8 |
| `relative_position_normalized` | `bool` | 0 | 8 |
| `relative_position_valid` | `bool` | 0 | 8 |
| `time_utc_usec` | `uint64_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `sensor_gps`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `int32_t` | 0 | 8 |
| `alt_ellipsoid` | `int32_t` | 0 | 8 |
| `automatic_gain_control` | `uint16_t` | 0 | 8 |
| `c_variance_rad` | `float` | 0 | 8 |
| `cog_rad` | `float` | 0 | 8 |
| `device_id` | `uint32_t` | 0 | 8 |
| `eph` | `float` | 0 | 8 |
| `epv` | `float` | 0 | 8 |
| `fix_type` | `uint8_t` | 0 | 8 |
| `hdop` | `float` | 0 | 8 |
| `heading` | `float` | 0 | 8 |
| `heading_accuracy` | `float` | 0 | 8 |
| `heading_offset` | `float` | 0 | 8 |
| `jamming_indicator` | `int32_t` | 0 | 8 |
| `jamming_state` | `uint8_t` | 0 | 8 |
| `lat` | `int32_t` | 0 | 8 |
| `lon` | `int32_t` | 0 | 8 |
| `noise_per_ms` | `int32_t` | 0 | 8 |
| `s_variance_m_s` | `float` | 0 | 8 |
| `satellites_used` | `uint8_t` | 0 | 8 |
| `time_utc_usec` | `uint64_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_time_relative` | `int32_t` | 0 | 8 |
| `vdop` | `float` | 0 | 8 |
| `vel_d_m_s` | `float` | 0 | 8 |
| `vel_e_m_s` | `float` | 0 | 8 |
| `vel_m_s` | `float` | 0 | 8 |
| `vel_n_m_s` | `float` | 0 | 8 |
| `vel_ned_valid` | `bool` | 0 | 8 |

### `sensor_gyro`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `device_id` | `uint32_t` | 0 | 2266 |
| `error_count` | `uint32_t` | 0 | 11 |
| `error_count` | `uint64_t` | 0 | 2255 |
| `integral_dt` | `uint64_t` | 0 | 2255 |
| `range_rad_s` | `float` | 0 | 2255 |
| `samples` | `uint8_t` | 0 | 8 |
| `scaling` | `float` | 0 | 2255 |
| `temperature` | `float` | 0 | 2266 |
| `temperature_raw` | `int16_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2266 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |
| `x` | `float` | 0 | 2266 |
| `x_integral` | `float` | 0 | 2255 |
| `x_raw` | `int16_t` | 0 | 2255 |
| `y` | `float` | 0 | 2266 |
| `y_integral` | `float` | 0 | 2255 |
| `y_raw` | `int16_t` | 0 | 2255 |
| `z` | `float` | 0 | 2266 |
| `z_integral` | `float` | 0 | 2255 |
| `z_raw` | `int16_t` | 0 | 2255 |

### `sensor_gyro_fft`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `device_id` | `uint32_t` | 0 | 8 |
| `peak_frequencies_x` | `float` | 3 | 8 |
| `peak_frequencies_y` | `float` | 3 | 8 |
| `peak_frequencies_z` | `float` | 3 | 8 |
| `peak_snr_x` | `float` | 3 | 8 |
| `peak_snr_y` | `float` | 3 | 8 |
| `peak_snr_z` | `float` | 3 | 8 |
| `resolution_hz` | `float` | 0 | 8 |
| `sensor_sample_rate_hz` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `sensor_mag`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `device_id` | `uint32_t` | 0 | 2266 |
| `error_count` | `uint32_t` | 0 | 11 |
| `error_count` | `uint64_t` | 0 | 2255 |
| `is_external` | `bool` | 0 | 2258 |
| `range_ga` | `float` | 0 | 2255 |
| `scaling` | `float` | 0 | 2255 |
| `temperature` | `float` | 0 | 2266 |
| `timestamp` | `uint64_t` | 0 | 2266 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |
| `x` | `float` | 0 | 2266 |
| `x_raw` | `int16_t` | 0 | 2255 |
| `y` | `float` | 0 | 2266 |
| `y_raw` | `int16_t` | 0 | 2255 |
| `z` | `float` | 0 | 2266 |
| `z_raw` | `int16_t` | 0 | 2255 |

### `sensor_preflight`

Declared in 3954 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_inconsistency_m_s_s` | `float` | 0 | 3954 |
| `gyro_inconsistency_rad_s` | `float` | 0 | 3954 |
| `mag_inconsistency_angle` | `float` | 0 | 1699 |
| `mag_inconsistency_ga` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 3954 |

### `sensor_selection`

Declared in 2932 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_device_id` | `uint32_t` | 0 | 2932 |
| `baro_device_id` | `uint32_t` | 0 | 2921 |
| `gyro_device_id` | `uint32_t` | 0 | 2932 |
| `mag_device_id` | `uint32_t` | 0 | 2924 |
| `timestamp` | `uint64_t` | 0 | 2932 |

### `sensors_status_imu`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_device_id_primary` | `uint32_t` | 0 | 8 |
| `accel_device_ids` | `uint32_t` | 4 | 8 |
| `accel_healthy` | `bool` | 4 | 8 |
| `accel_inconsistency_m_s_s` | `float` | 4 | 8 |
| `accel_priority` | `uint8_t` | 4 | 8 |
| `gyro_device_id_primary` | `uint32_t` | 0 | 8 |
| `gyro_device_ids` | `uint32_t` | 4 | 8 |
| `gyro_healthy` | `bool` | 4 | 8 |
| `gyro_inconsistency_rad_s` | `float` | 4 | 8 |
| `gyro_priority` | `uint8_t` | 4 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |

### `servorail_status`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `rssi_v` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `voltage_v` | `float` | 0 | 2255 |

### `subsystem_info`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `enabled` | `bool` | 0 | 2255 |
| `ok` | `bool` | 0 | 2255 |
| `present` | `bool` | 0 | 2255 |
| `subsystem_type` | `uint64_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `system_power`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `brick_valid` | `uint8_t` | 0 | 3962 |
| `can1_gps1_5v_valid` | `uint8_t` | 0 | 8 |
| `comp_5v_valid` | `uint8_t` | 0 | 8 |
| `hipower_5V_OC` | `uint8_t` | 0 | 2255 |
| `hipower_5v_oc` | `uint8_t` | 0 | 1707 |
| `periph_5V_OC` | `uint8_t` | 0 | 2255 |
| `periph_5v_oc` | `uint8_t` | 0 | 1707 |
| `sensors3v3` | `float` | 4 | 8 |
| `sensors3v3_valid` | `uint8_t` | 0 | 8 |
| `servo_valid` | `uint8_t` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `usb_connected` | `uint8_t` | 0 | 3962 |
| `usb_valid` | `uint8_t` | 0 | 3962 |
| `v3v3_valid` | `uint8_t` | 0 | 3954 |
| `voltage3V3_v` | `float` | 0 | 2255 |
| `voltage3v3_v` | `float` | 0 | 1699 |
| `voltage5V_v` | `float` | 0 | 2255 |
| `voltage5v_v` | `float` | 0 | 1707 |

### `takeoff_status`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `takeoff_state` | `uint8_t` | 0 | 8 |
| `tilt_limit` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |

### `task_stack_info`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `stack_free` | `uint16_t` | 0 | 2255 |
| `task_name` | `uint8_t` | 16 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `tecs_status`

Declared in 3954 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `airspeedDerivative` | `float` | 0 | 2255 |
| `airspeedDerivativeSp` | `float` | 0 | 2255 |
| `airspeedSp` | `float` | 0 | 2255 |
| `airspeed_derivative` | `float` | 0 | 1699 |
| `airspeed_derivative_sp` | `float` | 0 | 1699 |
| `airspeed_filtered` | `float` | 0 | 3954 |
| `airspeed_sp` | `float` | 0 | 1699 |
| `altitudeSp` | `float` | 0 | 2255 |
| `altitude_filtered` | `float` | 0 | 3954 |
| `altitude_sp` | `float` | 0 | 1699 |
| `energyDistributionError` | `float` | 0 | 2255 |
| `energyDistributionRateError` | `float` | 0 | 2255 |
| `energy_distribution_error` | `float` | 0 | 1699 |
| `energy_distribution_rate_error` | `float` | 0 | 1699 |
| `flightPathAngle` | `float` | 0 | 2255 |
| `flightPathAngleSp` | `float` | 0 | 2255 |
| `height_rate` | `float` | 0 | 1699 |
| `height_rate_setpoint` | `float` | 0 | 1699 |
| `mode` | `uint8_t` | 0 | 3954 |
| `pitch_integ` | `float` | 0 | 3954 |
| `throttle_integ` | `float` | 0 | 3954 |
| `timestamp` | `uint64_t` | 0 | 3954 |
| `totalEnergyError` | `float` | 0 | 2255 |
| `totalEnergyRateError` | `float` | 0 | 2255 |
| `total_energy_error` | `float` | 0 | 1699 |
| `total_energy_rate_error` | `float` | 0 | 1699 |

### `telemetry_heartbeat`

Declared in 3 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `component_id` | `uint8_t` | 0 | 3 |
| `state` | `uint8_t` | 0 | 3 |
| `system_id` | `uint8_t` | 0 | 3 |
| `timestamp` | `uint64_t` | 0 | 3 |
| `type` | `uint8_t` | 0 | 3 |

### `telemetry_status`

Declared in 3962 headers; selected records observed in 19/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `avoidance_system_healthy` | `bool` | 0 | 8 |
| `component_id` | `uint8_t` | 0 | 2255 |
| `data_rate` | `float` | 0 | 1707 |
| `fixed` | `uint16_t` | 0 | 2255 |
| `flow_control` | `bool` | 0 | 1707 |
| `forwarding` | `bool` | 0 | 1707 |
| `ftp` | `bool` | 0 | 1707 |
| `heartbeat_component_log` | `bool` | 0 | 8 |
| `heartbeat_component_obstacle_avoidance` | `bool` | 0 | 8 |
| `heartbeat_component_osd` | `bool` | 0 | 8 |
| `heartbeat_component_pairing_manager` | `bool` | 0 | 8 |
| `heartbeat_component_telemetry_radio` | `bool` | 0 | 8 |
| `heartbeat_component_uart_bridge` | `bool` | 0 | 8 |
| `heartbeat_component_udp_bridge` | `bool` | 0 | 8 |
| `heartbeat_component_vio` | `bool` | 0 | 8 |
| `heartbeat_time` | `uint64_t` | 0 | 3951 |
| `heartbeat_type_adsb` | `bool` | 0 | 8 |
| `heartbeat_type_antenna_tracker` | `bool` | 0 | 8 |
| `heartbeat_type_camera` | `bool` | 0 | 8 |
| `heartbeat_type_gcs` | `bool` | 0 | 8 |
| `heartbeat_type_gimbal` | `bool` | 0 | 8 |
| `heartbeat_type_onboard_controller` | `bool` | 0 | 8 |
| `heartbeat_type_parachute` | `bool` | 0 | 8 |
| `heartbeats` | `telemetry_heartbeat` | 4 | 3 |
| `mavlink_v2` | `bool` | 0 | 1707 |
| `mode` | `uint8_t` | 0 | 1707 |
| `noise` | `uint8_t` | 0 | 2255 |
| `parachute_system_healthy` | `bool` | 0 | 8 |
| `rate_multiplier` | `float` | 0 | 1707 |
| `rate_rx` | `float` | 0 | 1699 |
| `rate_tx` | `float` | 0 | 1699 |
| `rate_txerr` | `float` | 0 | 1699 |
| `remote_component_id` | `uint8_t` | 0 | 1696 |
| `remote_noise` | `uint8_t` | 0 | 2255 |
| `remote_rssi` | `uint8_t` | 0 | 2255 |
| `remote_system_id` | `uint8_t` | 0 | 1696 |
| `remote_system_status` | `uint8_t` | 0 | 1696 |
| `remote_type` | `uint8_t` | 0 | 1696 |
| `rssi` | `uint8_t` | 0 | 2255 |
| `rx_buffer_overruns` | `uint32_t` | 0 | 8 |
| `rx_message_count` | `uint32_t` | 0 | 8 |
| `rx_message_lost_count` | `uint32_t` | 0 | 8 |
| `rx_message_lost_rate` | `float` | 0 | 8 |
| `rx_packet_drop_count` | `uint32_t` | 0 | 8 |
| `rx_parse_errors` | `uint32_t` | 0 | 8 |
| `rx_rate_avg` | `float` | 0 | 8 |
| `rxerrors` | `uint16_t` | 0 | 2255 |
| `streams` | `uint8_t` | 0 | 1707 |
| `system_id` | `uint8_t` | 0 | 2255 |
| `telem_time` | `uint64_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `tx_buffer_overruns` | `uint32_t` | 0 | 8 |
| `tx_error_rate_avg` | `float` | 0 | 8 |
| `tx_message_count` | `uint32_t` | 0 | 8 |
| `tx_rate_avg` | `float` | 0 | 8 |
| `txbuf` | `uint8_t` | 0 | 2255 |
| `type` | `uint8_t` | 0 | 3962 |

### `test_motor`

Declared in 2258 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `action` | `uint8_t` | 0 | 3 |
| `driver_instance` | `uint8_t` | 0 | 3 |
| `motor_number` | `uint32_t` | 0 | 2258 |
| `timeout_ms` | `uint32_t` | 0 | 3 |
| `timestamp` | `uint64_t` | 0 | 2258 |
| `value` | `float` | 0 | 2258 |

### `time_offset`

Declared in 106 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `offset_ns` | `uint64_t` | 0 | 106 |
| `timestamp` | `uint64_t` | 0 | 106 |

### `timesync_status`

Declared in 2149 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `estimated_offset` | `int64_t` | 0 | 2149 |
| `observed_offset` | `int64_t` | 0 | 2149 |
| `remote_timestamp` | `uint64_t` | 0 | 2149 |
| `round_trip_time` | `uint32_t` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |

### `trajectory_setpoint`

Declared in 1707 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `acc_x` | `float` | 0 | 1696 |
| `acc_y` | `float` | 0 | 1696 |
| `acc_z` | `float` | 0 | 1696 |
| `acceleration` | `float` | 3 | 11 |
| `jerk` | `float` | 3 | 11 |
| `jerk_x` | `float` | 0 | 1696 |
| `jerk_y` | `float` | 0 | 1696 |
| `jerk_z` | `float` | 0 | 1696 |
| `thrust` | `float` | 3 | 1707 |
| `timestamp` | `uint64_t` | 0 | 1707 |
| `vx` | `float` | 0 | 1707 |
| `vy` | `float` | 0 | 1707 |
| `vz` | `float` | 0 | 1707 |
| `x` | `float` | 0 | 1707 |
| `y` | `float` | 0 | 1707 |
| `yaw` | `float` | 0 | 1707 |
| `yawspeed` | `float` | 0 | 1707 |
| `z` | `float` | 0 | 1707 |

### `transponder_report`

Declared in 2263 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `ICAO_address` | `uint32_t` | 0 | 2255 |
| `altitude` | `float` | 0 | 2263 |
| `altitude_type` | `uint8_t` | 0 | 2263 |
| `callsign` | `char` | 9 | 2263 |
| `emitter_type` | `uint8_t` | 0 | 2263 |
| `flags` | `uint16_t` | 0 | 2263 |
| `heading` | `float` | 0 | 2263 |
| `hor_velocity` | `float` | 0 | 2263 |
| `icao_address` | `uint32_t` | 0 | 8 |
| `lat` | `double` | 0 | 2263 |
| `lon` | `double` | 0 | 2263 |
| `squawk` | `uint16_t` | 0 | 2263 |
| `timestamp` | `uint64_t` | 0 | 2263 |
| `tslc` | `uint8_t` | 0 | 2263 |
| `uas_id` | `uint8_t` | 18 | 8 |
| `ver_velocity` | `float` | 0 | 2263 |

### `tune_control`

Declared in 2149 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `duration` | `uint32_t` | 0 | 2149 |
| `frequency` | `uint16_t` | 0 | 2149 |
| `silence` | `uint32_t` | 0 | 2149 |
| `strength` | `uint8_t` | 0 | 2149 |
| `timestamp` | `uint64_t` | 0 | 2149 |
| `tune_id` | `uint8_t` | 0 | 2149 |
| `tune_override` | `uint8_t` | 0 | 2149 |

### `uavcan_parameter_request`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `int_value` | `int64_t` | 0 | 2255 |
| `message_type` | `uint8_t` | 0 | 2255 |
| `node_id` | `uint8_t` | 0 | 2255 |
| `param_id` | `char` | 17 | 2255 |
| `param_index` | `int16_t` | 0 | 2255 |
| `param_type` | `uint8_t` | 0 | 2255 |
| `real_value` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `uavcan_parameter_value`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `int_value` | `int64_t` | 0 | 2255 |
| `node_id` | `uint8_t` | 0 | 2255 |
| `param_count` | `uint16_t` | 0 | 2255 |
| `param_id` | `char` | 17 | 2255 |
| `param_index` | `int16_t` | 0 | 2255 |
| `param_type` | `uint8_t` | 0 | 2255 |
| `real_value` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `ulog_stream`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `data` | `uint8_t` | 249 | 2255 |
| `first_message_offset` | `uint8_t` | 0 | 2255 |
| `flags` | `uint8_t` | 0 | 2255 |
| `length` | `uint8_t` | 0 | 2255 |
| `sequence` | `uint16_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `ulog_stream_ack`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `sequence` | `uint16_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `vehicle_acceleration`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `xyz` | `float` | 3 | 8 |

### `vehicle_air_data`

Declared in 3856 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `baro_alt_meter` | `float` | 0 | 3856 |
| `baro_device_id` | `uint32_t` | 0 | 11 |
| `baro_pressure_pa` | `float` | 0 | 3856 |
| `baro_temp_celcius` | `float` | 0 | 3856 |
| `calibration_count` | `uint8_t` | 0 | 8 |
| `rho` | `float` | 0 | 3856 |
| `timestamp` | `uint64_t` | 0 | 3856 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |

### `vehicle_angular_acceleration`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |
| `xyz` | `float` | 3 | 11 |

### `vehicle_angular_velocity`

Declared in 1707 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `timestamp` | `uint64_t` | 0 | 1707 |
| `timestamp_sample` | `uint64_t` | 0 | 1707 |
| `xyz` | `float` | 3 | 1707 |

### `vehicle_attitude`

Declared in 3962 headers; selected records observed in 20/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `delta_q_reset` | `float` | 4 | 3962 |
| `pitchspeed` | `float` | 0 | 2255 |
| `q` | `float` | 4 | 3962 |
| `quat_reset_counter` | `uint8_t` | 0 | 3962 |
| `rollspeed` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `yawspeed` | `float` | 0 | 2255 |

### `vehicle_attitude_groundtruth`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `delta_q_reset` | `float` | 4 | 2255 |
| `pitchspeed` | `float` | 0 | 2255 |
| `q` | `float` | 4 | 2255 |
| `quat_reset_counter` | `uint8_t` | 0 | 2255 |
| `rollspeed` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `yawspeed` | `float` | 0 | 2255 |

### `vehicle_attitude_setpoint`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `apply_flaps` | `bool` | 0 | 2255 |
| `apply_flaps` | `uint8_t` | 0 | 1707 |
| `disable_mc_yaw_control` | `bool` | 0 | 2255 |
| `fw_control_yaw` | `bool` | 0 | 3962 |
| `landing_gear` | `float` | 0 | 2255 |
| `pitch_body` | `float` | 0 | 3962 |
| `pitch_reset_integral` | `bool` | 0 | 3962 |
| `q_d` | `float` | 4 | 3962 |
| `q_d_valid` | `bool` | 0 | 3951 |
| `roll_body` | `float` | 0 | 3962 |
| `roll_reset_integral` | `bool` | 0 | 3962 |
| `thrust` | `float` | 0 | 2255 |
| `thrust_body` | `float` | 3 | 1707 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `yaw_body` | `float` | 0 | 3962 |
| `yaw_reset_integral` | `bool` | 0 | 3962 |
| `yaw_sp_move_rate` | `float` | 0 | 3962 |

### `vehicle_command`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `command` | `uint16_t` | 0 | 3954 |
| `command` | `uint32_t` | 0 | 8 |
| `confirmation` | `uint8_t` | 0 | 3962 |
| `from_external` | `bool` | 0 | 3962 |
| `param1` | `float` | 0 | 3962 |
| `param2` | `float` | 0 | 3962 |
| `param3` | `float` | 0 | 3962 |
| `param4` | `float` | 0 | 3962 |
| `param5` | `double` | 0 | 3962 |
| `param6` | `double` | 0 | 3962 |
| `param7` | `float` | 0 | 3962 |
| `source_component` | `uint8_t` | 0 | 3962 |
| `source_system` | `uint8_t` | 0 | 3962 |
| `target_component` | `uint8_t` | 0 | 3962 |
| `target_system` | `uint8_t` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |

### `vehicle_command_ack`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `command` | `uint16_t` | 0 | 2255 |
| `from_external` | `bool` | 0 | 2255 |
| `result` | `uint8_t` | 0 | 2255 |
| `result_param1` | `uint8_t` | 0 | 2255 |
| `result_param2` | `int32_t` | 0 | 2255 |
| `target_component` | `uint8_t` | 0 | 2255 |
| `target_system` | `uint8_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |

### `vehicle_constraints`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `speed_down` | `float` | 0 | 8 |
| `speed_up` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `want_takeoff` | `bool` | 0 | 8 |

### `vehicle_control_mode`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `flag_armed` | `bool` | 0 | 2266 |
| `flag_control_acceleration_enabled` | `bool` | 0 | 2266 |
| `flag_control_altitude_enabled` | `bool` | 0 | 2266 |
| `flag_control_attitude_enabled` | `bool` | 0 | 2266 |
| `flag_control_auto_enabled` | `bool` | 0 | 2266 |
| `flag_control_climb_rate_enabled` | `bool` | 0 | 2266 |
| `flag_control_fixed_hdg_enabled` | `bool` | 0 | 2258 |
| `flag_control_force_enabled` | `bool` | 0 | 2258 |
| `flag_control_manual_enabled` | `bool` | 0 | 2266 |
| `flag_control_offboard_enabled` | `bool` | 0 | 2266 |
| `flag_control_position_enabled` | `bool` | 0 | 2266 |
| `flag_control_rates_enabled` | `bool` | 0 | 2266 |
| `flag_control_rattitude_enabled` | `bool` | 0 | 2258 |
| `flag_control_termination_enabled` | `bool` | 0 | 2266 |
| `flag_control_velocity_enabled` | `bool` | 0 | 2266 |
| `flag_control_yawrate_override_enabled` | `bool` | 0 | 3 |
| `flag_external_manual_override_ok` | `bool` | 0 | 2258 |
| `flag_multicopter_position_control_enabled` | `bool` | 0 | 8 |
| `flag_system_hil_enabled` | `bool` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2266 |

### `vehicle_global_position`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `float` | 0 | 3962 |
| `alt_ellipsoid` | `float` | 0 | 1707 |
| `alt_reset_counter` | `uint8_t` | 0 | 3962 |
| `dead_reckoning` | `bool` | 0 | 3962 |
| `delta_alt` | `float` | 0 | 3962 |
| `eph` | `float` | 0 | 3962 |
| `epv` | `float` | 0 | 3962 |
| `evh` | `float` | 0 | 106 |
| `evv` | `float` | 0 | 106 |
| `lat` | `double` | 0 | 3962 |
| `lat_lon_reset_counter` | `uint8_t` | 0 | 3962 |
| `lon` | `double` | 0 | 3962 |
| `pos_d_deriv` | `float` | 0 | 106 |
| `pressure_alt` | `float` | 0 | 106 |
| `terrain_alt` | `float` | 0 | 3962 |
| `terrain_alt_valid` | `bool` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `vel_d` | `float` | 0 | 3951 |
| `vel_e` | `float` | 0 | 3951 |
| `vel_n` | `float` | 0 | 3951 |
| `yaw` | `float` | 0 | 3951 |

### `vehicle_global_position_groundtruth`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `float` | 0 | 2255 |
| `alt_reset_counter` | `uint8_t` | 0 | 2255 |
| `dead_reckoning` | `bool` | 0 | 2255 |
| `delta_alt` | `float` | 0 | 2255 |
| `eph` | `float` | 0 | 2255 |
| `epv` | `float` | 0 | 2255 |
| `evh` | `float` | 0 | 106 |
| `evv` | `float` | 0 | 106 |
| `lat` | `double` | 0 | 2255 |
| `lat_lon_reset_counter` | `uint8_t` | 0 | 2255 |
| `lon` | `double` | 0 | 2255 |
| `pos_d_deriv` | `float` | 0 | 106 |
| `pressure_alt` | `float` | 0 | 106 |
| `terrain_alt` | `float` | 0 | 2255 |
| `terrain_alt_valid` | `bool` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `vel_d` | `float` | 0 | 2255 |
| `vel_e` | `float` | 0 | 2255 |
| `vel_n` | `float` | 0 | 2255 |
| `yaw` | `float` | 0 | 2255 |

### `vehicle_gps_position`

Declared in 3962 headers; selected records observed in 3/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `int32_t` | 0 | 3962 |
| `alt_ellipsoid` | `int32_t` | 0 | 3962 |
| `c_variance_rad` | `float` | 0 | 3962 |
| `cog_rad` | `float` | 0 | 3962 |
| `eph` | `float` | 0 | 3962 |
| `epv` | `float` | 0 | 3962 |
| `fix_type` | `uint8_t` | 0 | 3962 |
| `hdop` | `float` | 0 | 3962 |
| `heading` | `float` | 0 | 1707 |
| `heading_offset` | `float` | 0 | 1707 |
| `jamming_indicator` | `int32_t` | 0 | 3962 |
| `jamming_state` | `uint8_t` | 0 | 8 |
| `lat` | `int32_t` | 0 | 3962 |
| `lon` | `int32_t` | 0 | 3962 |
| `noise_per_ms` | `int32_t` | 0 | 3962 |
| `s_variance_m_s` | `float` | 0 | 3962 |
| `satellites_used` | `uint8_t` | 0 | 3962 |
| `selected` | `uint8_t` | 0 | 8 |
| `time_utc_usec` | `uint64_t` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_time_relative` | `int32_t` | 0 | 3962 |
| `vdop` | `float` | 0 | 3962 |
| `vel_d_m_s` | `float` | 0 | 3962 |
| `vel_e_m_s` | `float` | 0 | 3962 |
| `vel_m_s` | `float` | 0 | 3962 |
| `vel_n_m_s` | `float` | 0 | 3962 |
| `vel_ned_valid` | `bool` | 0 | 3962 |

### `vehicle_imu`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_calibration_count` | `uint8_t` | 0 | 8 |
| `accel_device_id` | `uint32_t` | 0 | 11 |
| `delta_angle` | `float` | 3 | 11 |
| `delta_angle_dt` | `uint16_t` | 0 | 11 |
| `delta_velocity` | `float` | 3 | 11 |
| `delta_velocity_clipping` | `uint8_t` | 0 | 11 |
| `delta_velocity_dt` | `uint16_t` | 0 | 11 |
| `gyro_calibration_count` | `uint8_t` | 0 | 8 |
| `gyro_device_id` | `uint32_t` | 0 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 11 |

### `vehicle_imu_status`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `accel_clipping` | `uint32_t` | 3 | 11 |
| `accel_device_id` | `uint32_t` | 0 | 11 |
| `accel_error_count` | `uint32_t` | 0 | 11 |
| `accel_rate_hz` | `float` | 0 | 8 |
| `accel_rate_hz` | `uint16_t` | 0 | 3 |
| `accel_raw_rate_hz` | `float` | 0 | 8 |
| `accel_vibration_metric` | `float` | 0 | 11 |
| `delta_angle_coning_metric` | `float` | 0 | 8 |
| `gyro_coning_vibration` | `float` | 0 | 3 |
| `gyro_device_id` | `uint32_t` | 0 | 11 |
| `gyro_error_count` | `uint32_t` | 0 | 11 |
| `gyro_rate_hz` | `float` | 0 | 8 |
| `gyro_rate_hz` | `uint16_t` | 0 | 3 |
| `gyro_raw_rate_hz` | `float` | 0 | 8 |
| `gyro_vibration_metric` | `float` | 0 | 11 |
| `mean_accel` | `float` | 3 | 8 |
| `mean_gyro` | `float` | 3 | 8 |
| `temperature_accel` | `float` | 0 | 8 |
| `temperature_gyro` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `var_accel` | `float` | 3 | 8 |
| `var_gyro` | `float` | 3 | 8 |

### `vehicle_land_detected`

Declared in 3962 headers; selected records observed in 20/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt_max` | `float` | 0 | 3954 |
| `at_rest` | `bool` | 0 | 8 |
| `close_to_ground_or_skipped_check` | `bool` | 0 | 8 |
| `freefall` | `bool` | 0 | 3962 |
| `ground_contact` | `bool` | 0 | 3962 |
| `has_low_throttle` | `bool` | 0 | 8 |
| `horizontal_movement` | `bool` | 0 | 8 |
| `in_descend` | `bool` | 0 | 8 |
| `in_ground_effect` | `bool` | 0 | 1707 |
| `landed` | `bool` | 0 | 3962 |
| `maybe_landed` | `bool` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `vertical_movement` | `bool` | 0 | 8 |

### `vehicle_local_position`

Declared in 3962 headers; selected records observed in 19/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `ax` | `float` | 0 | 3962 |
| `ay` | `float` | 0 | 3962 |
| `az` | `float` | 0 | 3962 |
| `delta_heading` | `float` | 0 | 11 |
| `delta_vxy` | `float` | 2 | 3962 |
| `delta_vz` | `float` | 0 | 3962 |
| `delta_xy` | `float` | 2 | 3962 |
| `delta_z` | `float` | 0 | 3962 |
| `dist_bottom` | `float` | 0 | 3962 |
| `dist_bottom_rate` | `float` | 0 | 3951 |
| `dist_bottom_sensor_bitfield` | `uint8_t` | 0 | 8 |
| `dist_bottom_valid` | `bool` | 0 | 3962 |
| `eph` | `float` | 0 | 3962 |
| `epv` | `float` | 0 | 3962 |
| `evh` | `float` | 0 | 3962 |
| `evv` | `float` | 0 | 3962 |
| `hagl_max` | `float` | 0 | 3856 |
| `hagl_min` | `float` | 0 | 3856 |
| `heading` | `float` | 0 | 11 |
| `heading_good_for_control` | `bool` | 0 | 8 |
| `heading_reset_counter` | `uint8_t` | 0 | 11 |
| `ref_alt` | `float` | 0 | 3962 |
| `ref_lat` | `double` | 0 | 3962 |
| `ref_lon` | `double` | 0 | 3962 |
| `ref_timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `v_xy_valid` | `bool` | 0 | 3962 |
| `v_z_valid` | `bool` | 0 | 3962 |
| `vx` | `float` | 0 | 3962 |
| `vxy_max` | `float` | 0 | 3856 |
| `vxy_reset_counter` | `uint8_t` | 0 | 3962 |
| `vy` | `float` | 0 | 3962 |
| `vz` | `float` | 0 | 3962 |
| `vz_max` | `float` | 0 | 3856 |
| `vz_reset_counter` | `uint8_t` | 0 | 3962 |
| `x` | `float` | 0 | 3962 |
| `xy_global` | `bool` | 0 | 3962 |
| `xy_reset_counter` | `uint8_t` | 0 | 3962 |
| `xy_valid` | `bool` | 0 | 3962 |
| `y` | `float` | 0 | 3962 |
| `yaw` | `float` | 0 | 3951 |
| `z` | `float` | 0 | 3962 |
| `z_deriv` | `float` | 0 | 3962 |
| `z_global` | `bool` | 0 | 3962 |
| `z_reset_counter` | `uint8_t` | 0 | 3962 |
| `z_valid` | `bool` | 0 | 3962 |

### `vehicle_local_position_groundtruth`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `ax` | `float` | 0 | 2255 |
| `ay` | `float` | 0 | 2255 |
| `az` | `float` | 0 | 2255 |
| `delta_vxy` | `float` | 2 | 2255 |
| `delta_vz` | `float` | 0 | 2255 |
| `delta_xy` | `float` | 2 | 2255 |
| `delta_z` | `float` | 0 | 2255 |
| `dist_bottom` | `float` | 0 | 2255 |
| `dist_bottom_rate` | `float` | 0 | 2255 |
| `dist_bottom_valid` | `bool` | 0 | 2255 |
| `eph` | `float` | 0 | 2255 |
| `epv` | `float` | 0 | 2255 |
| `evh` | `float` | 0 | 2255 |
| `evv` | `float` | 0 | 2255 |
| `hagl_max` | `float` | 0 | 2149 |
| `hagl_min` | `float` | 0 | 2149 |
| `ref_alt` | `float` | 0 | 2255 |
| `ref_lat` | `double` | 0 | 2255 |
| `ref_lon` | `double` | 0 | 2255 |
| `ref_timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `v_xy_valid` | `bool` | 0 | 2255 |
| `v_z_valid` | `bool` | 0 | 2255 |
| `vx` | `float` | 0 | 2255 |
| `vxy_max` | `float` | 0 | 2149 |
| `vxy_reset_counter` | `uint8_t` | 0 | 2255 |
| `vy` | `float` | 0 | 2255 |
| `vz` | `float` | 0 | 2255 |
| `vz_max` | `float` | 0 | 2149 |
| `vz_reset_counter` | `uint8_t` | 0 | 2255 |
| `x` | `float` | 0 | 2255 |
| `xy_global` | `bool` | 0 | 2255 |
| `xy_reset_counter` | `uint8_t` | 0 | 2255 |
| `xy_valid` | `bool` | 0 | 2255 |
| `y` | `float` | 0 | 2255 |
| `yaw` | `float` | 0 | 2255 |
| `z` | `float` | 0 | 2255 |
| `z_deriv` | `float` | 0 | 2255 |
| `z_global` | `bool` | 0 | 2255 |
| `z_reset_counter` | `uint8_t` | 0 | 2255 |
| `z_valid` | `bool` | 0 | 2255 |

### `vehicle_local_position_setpoint`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `acc_x` | `float` | 0 | 3951 |
| `acc_y` | `float` | 0 | 3951 |
| `acc_z` | `float` | 0 | 3951 |
| `acceleration` | `float` | 3 | 11 |
| `jerk` | `float` | 3 | 11 |
| `jerk_x` | `float` | 0 | 1696 |
| `jerk_y` | `float` | 0 | 1696 |
| `jerk_z` | `float` | 0 | 1696 |
| `thrust` | `float` | 3 | 3856 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `vx` | `float` | 0 | 3962 |
| `vy` | `float` | 0 | 3962 |
| `vz` | `float` | 0 | 3962 |
| `x` | `float` | 0 | 3962 |
| `y` | `float` | 0 | 3962 |
| `yaw` | `float` | 0 | 3962 |
| `yawspeed` | `float` | 0 | 3856 |
| `z` | `float` | 0 | 3962 |

### `vehicle_magnetometer`

Declared in 3856 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `calibration_count` | `uint8_t` | 0 | 8 |
| `device_id` | `uint32_t` | 0 | 8 |
| `magnetometer_ga` | `float` | 3 | 3856 |
| `timestamp` | `uint64_t` | 0 | 3856 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |

### `vehicle_rates_setpoint`

Declared in 3962 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `pitch` | `float` | 0 | 3962 |
| `roll` | `float` | 0 | 3962 |
| `thrust` | `float` | 0 | 2255 |
| `thrust_body` | `float` | 3 | 1707 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `yaw` | `float` | 0 | 3962 |

### `vehicle_roi`

Declared in 2266 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `alt` | `float` | 0 | 2266 |
| `lat` | `double` | 0 | 2266 |
| `lon` | `double` | 0 | 2266 |
| `mission_seq` | `uint32_t` | 0 | 106 |
| `mode` | `uint8_t` | 0 | 2266 |
| `pitch_offset` | `float` | 0 | 2160 |
| `roll_offset` | `float` | 0 | 2160 |
| `target_seq` | `uint32_t` | 0 | 106 |
| `timestamp` | `uint64_t` | 0 | 2266 |
| `yaw_offset` | `float` | 0 | 2160 |

### `vehicle_status`

Declared in 3962 headers; selected records observed in 20/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `armed_time` | `uint64_t` | 0 | 8 |
| `arming_state` | `uint8_t` | 0 | 3962 |
| `arspd_check_level` | `float` | 0 | 1696 |
| `aspd_check_failing` | `bool` | 0 | 1696 |
| `aspd_fail_rtl` | `bool` | 0 | 1696 |
| `aspd_fault_declared` | `bool` | 0 | 1696 |
| `aspd_use_inhibit` | `bool` | 0 | 1696 |
| `component_id` | `uint8_t` | 0 | 3962 |
| `data_link_lost` | `bool` | 0 | 3962 |
| `data_link_lost_counter` | `uint8_t` | 0 | 3962 |
| `engine_failure` | `bool` | 0 | 3962 |
| `failsafe` | `bool` | 0 | 3962 |
| `failsafe_timestamp` | `uint64_t` | 0 | 8 |
| `failure_detector_status` | `uint8_t` | 0 | 1707 |
| `geofence_violated` | `bool` | 0 | 8 |
| `high_latency_data_link_active` | `bool` | 0 | 2149 |
| `high_latency_data_link_lost` | `bool` | 0 | 1707 |
| `hil_state` | `uint8_t` | 0 | 3962 |
| `in_transition_mode` | `bool` | 0 | 3962 |
| `in_transition_to_fw` | `bool` | 0 | 3962 |
| `is_rotary_wing` | `bool` | 0 | 2255 |
| `is_vtol` | `bool` | 0 | 3962 |
| `is_vtol_tailsitter` | `bool` | 0 | 11 |
| `latest_arming_reason` | `uint8_t` | 0 | 11 |
| `latest_disarming_reason` | `uint8_t` | 0 | 11 |
| `load_factor_ratio` | `float` | 0 | 1696 |
| `mission_failure` | `bool` | 0 | 3962 |
| `nav_state` | `uint8_t` | 0 | 3962 |
| `nav_state_timestamp` | `uint64_t` | 0 | 11 |
| `onboard_control_sensors_enabled` | `uint32_t` | 0 | 3954 |
| `onboard_control_sensors_enabled` | `uint64_t` | 0 | 8 |
| `onboard_control_sensors_health` | `uint32_t` | 0 | 3954 |
| `onboard_control_sensors_health` | `uint64_t` | 0 | 8 |
| `onboard_control_sensors_present` | `uint32_t` | 0 | 3954 |
| `onboard_control_sensors_present` | `uint64_t` | 0 | 8 |
| `rc_input_mode` | `uint8_t` | 0 | 3954 |
| `rc_signal_lost` | `bool` | 0 | 3962 |
| `system_id` | `uint8_t` | 0 | 3962 |
| `system_type` | `uint8_t` | 0 | 3962 |
| `takeoff_time` | `uint64_t` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `vehicle_type` | `uint8_t` | 0 | 1707 |
| `vtol_fw_permanent_stab` | `bool` | 0 | 3962 |

### `vehicle_status_flags`

Declared in 3962 headers; selected records observed in 19/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `angular_velocity_valid` | `bool` | 0 | 8 |
| `attitude_valid` | `bool` | 0 | 8 |
| `auto_mission_available` | `bool` | 0 | 8 |
| `avoidance_system_required` | `bool` | 0 | 1707 |
| `avoidance_system_valid` | `bool` | 0 | 1707 |
| `battery_healthy` | `bool` | 0 | 8 |
| `calibration_enabled` | `bool` | 0 | 8 |
| `circuit_breaker_engaged_airspd_check` | `bool` | 0 | 3856 |
| `circuit_breaker_engaged_enginefailure_check` | `bool` | 0 | 3856 |
| `circuit_breaker_engaged_gpsfailure_check` | `bool` | 0 | 3845 |
| `circuit_breaker_engaged_posfailure_check` | `bool` | 0 | 3856 |
| `circuit_breaker_engaged_power_check` | `bool` | 0 | 3856 |
| `circuit_breaker_engaged_usb_check` | `bool` | 0 | 3856 |
| `circuit_breaker_flight_termination_disabled` | `bool` | 0 | 3856 |
| `circuit_breaker_vtol_fw_arming_check` | `bool` | 0 | 11 |
| `circuit_breakers` | `uint8_t` | 0 | 106 |
| `condition_auto_mission_available` | `bool` | 0 | 3848 |
| `condition_battery_healthy` | `bool` | 0 | 1699 |
| `condition_calibration_enabled` | `bool` | 0 | 3848 |
| `condition_escs_error` | `bool` | 0 | 1699 |
| `condition_global_position_valid` | `bool` | 0 | 3848 |
| `condition_home_position_valid` | `bool` | 0 | 3848 |
| `condition_local_altitude_valid` | `bool` | 0 | 3848 |
| `condition_local_position_valid` | `bool` | 0 | 3848 |
| `condition_local_velocity_valid` | `bool` | 0 | 3848 |
| `condition_power_input_valid` | `bool` | 0 | 3848 |
| `condition_system_hotplug_timeout` | `bool` | 0 | 3848 |
| `condition_system_returned_to_home` | `bool` | 0 | 3848 |
| `condition_system_sensors_initialized` | `bool` | 0 | 3848 |
| `conditions` | `uint16_t` | 0 | 106 |
| `dead_reckoning` | `bool` | 0 | 8 |
| `escs_error` | `bool` | 0 | 8 |
| `escs_failure` | `bool` | 0 | 8 |
| `flight_terminated` | `bool` | 0 | 8 |
| `global_position_valid` | `bool` | 0 | 8 |
| `gps_position_valid` | `bool` | 0 | 8 |
| `home_position_valid` | `bool` | 0 | 8 |
| `local_altitude_valid` | `bool` | 0 | 8 |
| `local_position_valid` | `bool` | 0 | 8 |
| `local_velocity_valid` | `bool` | 0 | 8 |
| `offboard_control_loss_timeout` | `bool` | 0 | 3845 |
| `offboard_control_set_by_command` | `bool` | 0 | 3848 |
| `offboard_control_signal_found_once` | `bool` | 0 | 3848 |
| `offboard_control_signal_lost` | `bool` | 0 | 3856 |
| `other_flags` | `uint16_t` | 0 | 106 |
| `parachute_system_healthy` | `bool` | 0 | 8 |
| `parachute_system_present` | `bool` | 0 | 8 |
| `position_reliant_on_gps` | `bool` | 0 | 8 |
| `position_reliant_on_optical_flow` | `bool` | 0 | 8 |
| `position_reliant_on_vision_position` | `bool` | 0 | 8 |
| `power_input_valid` | `bool` | 0 | 8 |
| `rc_calibration_in_progress` | `bool` | 0 | 8 |
| `rc_calibration_valid` | `bool` | 0 | 3856 |
| `rc_input_blocked` | `bool` | 0 | 3848 |
| `rc_signal_found_once` | `bool` | 0 | 3856 |
| `sd_card_detected_once` | `bool` | 0 | 8 |
| `system_hotplug_timeout` | `bool` | 0 | 8 |
| `system_sensors_initialized` | `bool` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 3962 |
| `usb_connected` | `bool` | 0 | 3856 |
| `vtol_transition_failure` | `bool` | 0 | 3856 |

### `vehicle_vision_attitude`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `delta_q_reset` | `float` | 4 | 2255 |
| `pitchspeed` | `float` | 0 | 2255 |
| `q` | `float` | 4 | 2255 |
| `quat_reset_counter` | `uint8_t` | 0 | 2255 |
| `rollspeed` | `float` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `yawspeed` | `float` | 0 | 2255 |

### `vehicle_vision_position`

Declared in 2255 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `ax` | `float` | 0 | 2255 |
| `ay` | `float` | 0 | 2255 |
| `az` | `float` | 0 | 2255 |
| `delta_vxy` | `float` | 2 | 2255 |
| `delta_vz` | `float` | 0 | 2255 |
| `delta_xy` | `float` | 2 | 2255 |
| `delta_z` | `float` | 0 | 2255 |
| `dist_bottom` | `float` | 0 | 2255 |
| `dist_bottom_rate` | `float` | 0 | 2255 |
| `dist_bottom_valid` | `bool` | 0 | 2255 |
| `eph` | `float` | 0 | 2255 |
| `epv` | `float` | 0 | 2255 |
| `evh` | `float` | 0 | 2255 |
| `evv` | `float` | 0 | 2255 |
| `hagl_max` | `float` | 0 | 2149 |
| `hagl_min` | `float` | 0 | 2149 |
| `ref_alt` | `float` | 0 | 2255 |
| `ref_lat` | `double` | 0 | 2255 |
| `ref_lon` | `double` | 0 | 2255 |
| `ref_timestamp` | `uint64_t` | 0 | 2255 |
| `timestamp` | `uint64_t` | 0 | 2255 |
| `v_xy_valid` | `bool` | 0 | 2255 |
| `v_z_valid` | `bool` | 0 | 2255 |
| `vx` | `float` | 0 | 2255 |
| `vxy_max` | `float` | 0 | 2149 |
| `vxy_reset_counter` | `uint8_t` | 0 | 2255 |
| `vy` | `float` | 0 | 2255 |
| `vz` | `float` | 0 | 2255 |
| `vz_max` | `float` | 0 | 2149 |
| `vz_reset_counter` | `uint8_t` | 0 | 2255 |
| `x` | `float` | 0 | 2255 |
| `xy_global` | `bool` | 0 | 2255 |
| `xy_reset_counter` | `uint8_t` | 0 | 2255 |
| `xy_valid` | `bool` | 0 | 2255 |
| `y` | `float` | 0 | 2255 |
| `yaw` | `float` | 0 | 2255 |
| `z` | `float` | 0 | 2255 |
| `z_deriv` | `float` | 0 | 2255 |
| `z_global` | `bool` | 0 | 2255 |
| `z_reset_counter` | `uint8_t` | 0 | 2255 |
| `z_valid` | `bool` | 0 | 2255 |

### `vehicle_visual_odometry`

Declared in 674 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `local_frame` | `uint8_t` | 0 | 674 |
| `pitchspeed` | `float` | 0 | 674 |
| `pose_covariance` | `float` | 21 | 674 |
| `q` | `float` | 4 | 674 |
| `q_offset` | `float` | 4 | 674 |
| `reset_counter` | `uint8_t` | 0 | 8 |
| `rollspeed` | `float` | 0 | 674 |
| `timestamp` | `uint64_t` | 0 | 674 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `velocity_covariance` | `float` | 21 | 674 |
| `velocity_frame` | `uint8_t` | 0 | 8 |
| `vx` | `float` | 0 | 674 |
| `vy` | `float` | 0 | 674 |
| `vz` | `float` | 0 | 674 |
| `x` | `float` | 0 | 674 |
| `y` | `float` | 0 | 674 |
| `yawspeed` | `float` | 0 | 674 |
| `z` | `float` | 0 | 674 |

### `vehicle_visual_odometry_aligned`

Declared in 666 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `local_frame` | `uint8_t` | 0 | 666 |
| `pitchspeed` | `float` | 0 | 666 |
| `pose_covariance` | `float` | 21 | 666 |
| `q` | `float` | 4 | 666 |
| `q_offset` | `float` | 4 | 666 |
| `rollspeed` | `float` | 0 | 666 |
| `timestamp` | `uint64_t` | 0 | 666 |
| `velocity_covariance` | `float` | 21 | 666 |
| `vx` | `float` | 0 | 666 |
| `vy` | `float` | 0 | 666 |
| `vz` | `float` | 0 | 666 |
| `x` | `float` | 0 | 666 |
| `y` | `float` | 0 | 666 |
| `yawspeed` | `float` | 0 | 666 |
| `z` | `float` | 0 | 666 |

### `vtol_vehicle_status`

Declared in 3954 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `fw_permanent_stab` | `bool` | 0 | 3954 |
| `in_transition_to_fw` | `bool` | 0 | 3954 |
| `timestamp` | `uint64_t` | 0 | 3954 |
| `vtol_in_rw_mode` | `bool` | 0 | 3954 |
| `vtol_in_trans_mode` | `bool` | 0 | 3954 |
| `vtol_transition_failsafe` | `bool` | 0 | 3954 |

### `wind`

Declared in 8 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `beta_innov` | `float` | 0 | 8 |
| `beta_innov_var` | `float` | 0 | 8 |
| `tas_innov` | `float` | 0 | 8 |
| `tas_innov_var` | `float` | 0 | 8 |
| `timestamp` | `uint64_t` | 0 | 8 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `variance_east` | `float` | 0 | 8 |
| `variance_north` | `float` | 0 | 8 |
| `windspeed_east` | `float` | 0 | 8 |
| `windspeed_north` | `float` | 0 | 8 |

### `wind_estimate`

Declared in 3954 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `beta_innov` | `float` | 0 | 3848 |
| `beta_innov_var` | `float` | 0 | 3848 |
| `tas_innov` | `float` | 0 | 3848 |
| `tas_innov_var` | `float` | 0 | 3848 |
| `tas_scale` | `float` | 0 | 3848 |
| `timestamp` | `uint64_t` | 0 | 3954 |
| `variance_east` | `float` | 0 | 3954 |
| `variance_north` | `float` | 0 | 3954 |
| `windspeed_east` | `float` | 0 | 3954 |
| `windspeed_north` | `float` | 0 | 3954 |

### `yaw_estimator_status`

Declared in 11 headers; selected records observed in 0/20 sampled files. A zero sample count may mean the topic was outside the filter.

| Field | Declared type | Array length (0 = scalar) | Headers with this variant |
| --- | --- | ---: | ---: |
| `innov_ve` | `float` | 5 | 11 |
| `innov_vn` | `float` | 5 | 11 |
| `timestamp` | `uint64_t` | 0 | 11 |
| `timestamp_sample` | `uint64_t` | 0 | 8 |
| `weight` | `float` | 5 | 11 |
| `yaw` | `float` | 5 | 11 |
| `yaw_composite` | `float` | 0 | 11 |
| `yaw_variance` | `float` | 0 | 11 |

## DJI decoded raw-record fields

Research decoder: `dji-log-parser` v0.5.7. These are JSON decoder output
types, not native wire types or an accepted DJI contract. The catalog covers
23 unique directly named TXT files; 34 archive paths include duplicates.
A field occurrence count is a decoded-record count, not a flight count.

### `AppGPS`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `latitude` | `float` | 1289 |
| `longitude` | `float` | 1289 |

### `AppTip`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `message` | `str` | 1 |

### `Camera`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `cameraType` | `int` | 4807 |
| `contiCapture` | `bool` | 4807 |
| `encryptStatus` | `int` | 4807 |
| `fileSynState` | `bool` | 4807 |
| `getFocusState` | `bool` | 4807 |
| `hasSdCard` | `bool` | 4807 |
| `hdmiOutputStatus` | `bool` | 4807 |
| `isCaptureDisable` | `bool` | 4807 |
| `isConnect` | `bool` | 4807 |
| `isDdrStoring` | `bool` | 4807 |
| `isEnableTrackingMode` | `bool` | 4807 |
| `isHeat` | `bool` | 4807 |
| `isRecording` | `bool` | 4807 |
| `isShootingSinglePhoto` | `bool` | 4807 |
| `isUpgrading` | `int` | 4807 |
| `isUsbConnect` | `bool` | 4807 |
| `panoTimelapseGimbalState` | `bool` | 4807 |
| `rcBtnForbidState` | `bool` | 4807 |
| `recordTime` | `int` | 4807 |
| `remainPhotoNum` | `int` | 4807 |
| `remainVideoTimer` | `int` | 4807 |
| `sdCardRemainCapacity` | `int` | 4807 |
| `sdCardState` | `str` | 4807 |
| `sdCardTotalCapacity` | `int` | 4807 |
| `timerSyncState` | `int` | 4807 |
| `workMode` | `int` | 1 |
| `workMode` | `str` | 4806 |

### `CenterBattery`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `batteryOnCharge` | `bool` | 610 |
| `connectState` | `int` | 610 |
| `current` | `float` | 610 |
| `currentCapacity` | `int` | 610 |
| `errorType` | `int` | 610 |
| `fullCapacity` | `int` | 610 |
| `latestLearnCycle` | `int` | 610 |
| `life` | `int` | 610 |
| `numberOfDischarges` | `int` | 610 |
| `productDate` | `int` | 610 |
| `relativeCapacity` | `int` | 610 |
| `reverse` | `int` | 610 |
| `serialNumber` | `int` | 610 |
| `sumLearnCount` | `int` | 610 |
| `temperature` | `float` | 610 |
| `voltage` | `float` | 610 |
| `voltageCell1` | `float` | 610 |
| `voltageCell2` | `float` | 610 |
| `voltageCell3` | `float` | 610 |
| `voltageCell4` | `float` | 610 |
| `voltageCell5` | `float` | 610 |
| `voltageCell6` | `float` | 610 |

### `ComponentSerial`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `componentType` | `int` | 1 |
| `componentType` | `str` | 52 |
| `serial` | `str` | 53 |

### `Custom`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `distance` | `NoneType` | 262 |
| `distance` | `float` | 45819 |
| `hSpeed` | `float` | 46081 |
| `updateTimestamp` | `str` | 46081 |

### `Deform`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `deformMode` | `str` | 1305 |
| `deformStatus` | `str` | 1305 |
| `isDeformProtected` | `bool` | 1305 |

### `Firmware`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `senderType` | `dict` | 25 |
| `senderType` | `str` | 107 |
| `subSenderType` | `int` | 132 |
| `version` | `str` | 132 |

### `Gimbal`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `autoCalibrationResult` | `bool` | 41901 |
| `installDirection` | `bool` | 41901 |
| `isAutoCalibration` | `bool` | 41901 |
| `isDoubleClick` | `bool` | 41901 |
| `isPitchAtLimit` | `bool` | 41901 |
| `isRollAtLimit` | `bool` | 41901 |
| `isSingleClick` | `bool` | 41901 |
| `isStuck` | `bool` | 41901 |
| `isTripleClick` | `bool` | 41901 |
| `isYawAtLimit` | `bool` | 41901 |
| `mode` | `str` | 41901 |
| `pitch` | `float` | 41901 |
| `reset` | `int` | 41901 |
| `roll` | `float` | 41901 |
| `rollAdjust` | `float` | 41901 |
| `version` | `int` | 41901 |
| `yaw` | `float` | 41901 |
| `yawAngle` | `float` | 41901 |

### `Home`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `aircraftHeadDirection` | `int` | 2576 |
| `altitude` | `float` | 2576 |
| `compassState` | `str` | 2576 |
| `currentFlightRecordIndex` | `int` | 2576 |
| `flightRecordSdState` | `int` | 2576 |
| `goHomeHeight` | `int` | 2576 |
| `goHomeMode` | `str` | 2576 |
| `hasGoHome` | `bool` | 2576 |
| `iocCourseLockAngle` | `int` | 2576 |
| `iocMode` | `int` | 1 |
| `iocMode` | `str` | 2575 |
| `isBeginnerMode` | `bool` | 2576 |
| `isCompassAdjust` | `bool` | 2576 |
| `isDynamicHomePointEnabled` | `bool` | 2576 |
| `isHomeRecord` | `bool` | 2576 |
| `isIocOpen` | `bool` | 2576 |
| `isMultipleModeOpen` | `bool` | 2576 |
| `isNearDistanceLimit` | `bool` | 2576 |
| `isNearHeightLimit` | `bool` | 2576 |
| `latitude` | `float` | 2576 |
| `longitude` | `float` | 2576 |
| `maxAllowedHeight` | `float` | 2576 |
| `recordSdCapacityPercent` | `int` | 2576 |
| `recordSdLeftTime` | `int` | 2576 |

### `MCParams`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `avoidObstacleEnabled` | `bool` | 487 |
| `failSafeProtection` | `str` | 487 |
| `mvoFuncEnabled` | `bool` | 487 |
| `userAvoidEnabled` | `bool` | 487 |

### `OSD`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `altitude` | `float` | 44617 |
| `appCommand` | `int` | 30886 |
| `appCommand` | `str` | 13731 |
| `battery` | `int` | 44617 |
| `batteryType` | `str` | 44617 |
| `canIocWork` | `bool` | 44617 |
| `droneType` | `int` | 1 |
| `droneType` | `str` | 44616 |
| `flightAction` | `int` | 1 |
| `flightAction` | `str` | 44616 |
| `flightMode` | `str` | 44617 |
| `flyTime` | `float` | 44617 |
| `goHomeStatus` | `int` | 29630 |
| `goHomeStatus` | `str` | 14987 |
| `gpsLevel` | `int` | 44617 |
| `gpsNum` | `int` | 44617 |
| `groundOrSky` | `str` | 44617 |
| `imuInitFailReason` | `int` | 1 |
| `imuInitFailReason` | `str` | 44616 |
| `isAcceletorOverRange` | `bool` | 44617 |
| `isBarometerDeadInAir` | `bool` | 44617 |
| `isCompassError` | `bool` | 44617 |
| `isGoHomeHeightModified` | `bool` | 44617 |
| `isGpsValid` | `bool` | 44617 |
| `isImuPreheated` | `bool` | 44617 |
| `isMotorBlocked` | `bool` | 44617 |
| `isMotorUp` | `bool` | 44617 |
| `isNotEnoughForce` | `bool` | 44617 |
| `isOutOfLimit` | `bool` | 44617 |
| `isPropellerCatapult` | `bool` | 44617 |
| `isSwaveWork` | `bool` | 44617 |
| `isVibrating` | `bool` | 44617 |
| `isVisionUsed` | `bool` | 44617 |
| `latitude` | `float` | 44617 |
| `longitude` | `float` | 44617 |
| `modeChannel` | `int` | 44617 |
| `motorRevolution` | `int` | 44617 |
| `motorStartFailedCause` | `str` | 44617 |
| `nonGpsCause` | `int` | 1 |
| `nonGpsCause` | `str` | 44616 |
| `pitch` | `float` | 44617 |
| `rcOutcontrol` | `bool` | 44617 |
| `roll` | `float` | 44617 |
| `sWaveHeight` | `float` | 44617 |
| `speedX` | `float` | 44617 |
| `speedY` | `float` | 44617 |
| `speedZ` | `float` | 44617 |
| `versionC` | `int` | 44617 |
| `voltageWarning` | `int` | 44617 |
| `waveError` | `bool` | 44617 |
| `waypointLimitMode` | `bool` | 44617 |
| `yaw` | `float` | 44617 |

### `RC`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `aileron` | `int` | 20840 |
| `bandwidth` | `int` | 20840 |
| `customFunctionBtn1Down` | `bool` | 20840 |
| `customFunctionBtn2Down` | `bool` | 20840 |
| `customFunctionBtn3Down` | `bool` | 20840 |
| `customFunctionBtn4Down` | `bool` | 20840 |
| `elevator` | `int` | 20840 |
| `flightModeSwitch` | `int` | 2 |
| `flightModeSwitch` | `str` | 20838 |
| `gimbal` | `int` | 20840 |
| `gimbalControlEnable` | `int` | 20840 |
| `playbackBtnDown` | `bool` | 20840 |
| `recordBtnDown` | `bool` | 20840 |
| `returnBtn` | `bool` | 20840 |
| `rudder` | `int` | 20840 |
| `shutterBtnDown` | `bool` | 20840 |
| `throttle` | `int` | 20840 |
| `transformBtnReserve` | `int` | 20840 |
| `transformSwitch` | `int` | 20840 |
| `wheelBtnDown` | `bool` | 20840 |
| `wheelChange` | `int` | 20840 |
| `wheelOffset` | `int` | 20840 |
| `wheelPolarity` | `int` | 20840 |

### `RCGPS`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `accuracy` | `float` | 1001 |
| `day` | `int` | 1001 |
| `gpsNum` | `int` | 1001 |
| `hour` | `int` | 1001 |
| `latitude` | `int` | 1001 |
| `longitude` | `int` | 1001 |
| `minute` | `int` | 1001 |
| `month` | `int` | 1001 |
| `second` | `int` | 1001 |
| `speedX` | `int` | 1001 |
| `speedY` | `int` | 1001 |
| `validData` | `int` | 1001 |
| `year` | `int` | 1001 |

### `Recover`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `aircraftName` | `str` | 99 |
| `aircraftSn` | `str` | 99 |
| `appPlatform` | `int` | 17 |
| `appPlatform` | `str` | 82 |
| `appVersion` | `str` | 99 |
| `batterySn` | `str` | 99 |
| `cameraSn` | `str` | 99 |
| `productType` | `int` | 13 |
| `productType` | `str` | 86 |
| `rcSn` | `str` | 99 |
| `timestamp` | `str` | 99 |

### `SmartBattery`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `goHomeBattery` | `int` | 4552 |
| `goHomeCountdown` | `int` | 4552 |
| `goHomeStatus` | `int` | 1 |
| `goHomeStatus` | `str` | 4551 |
| `goHomeTime` | `int` | 4552 |
| `landBattery` | `int` | 4552 |
| `landTime` | `int` | 4552 |
| `lowWarning` | `int` | 4552 |
| `lowWarningGoHome` | `int` | 4552 |
| `percent` | `int` | 4552 |
| `reserve` | `int` | 4552 |
| `safeFlyRadius` | `float` | 4552 |
| `seriousLowWarning` | `int` | 4552 |
| `seriousLowWarningLanding` | `int` | 4552 |
| `status` | `int` | 4552 |
| `usefulTime` | `int` | 4552 |
| `voltage` | `float` | 4552 |
| `volumeConsume` | `float` | 4552 |

### `SmartBatteryGroup`

| Field | Decoder JSON type | Occurrences |
| --- | --- | ---: |
| `battery_life` | `int` | 2993 |
| `battery_type` | `int` | 2993 |
| `cell_count` | `int` | 3153 |
| `cell_voltages` | `list` | 3153 |
| `designed_capacity` | `int` | 2993 |
| `full_voltage` | `int` | 2993 |
| `index` | `int` | 6146 |
| `loop_times` | `int` | 2993 |
| `serial_number` | `int` | 2993 |
| `type` | `str` | 6146 |
| `version_number` | `list` | 2993 |

## DJI normalized CSV columns

These 123 union columns are the decoder view, not 123 measured quantities.
Frames carry prior values, include defaults and derived fields, and omit
one final OSD record per decoded file in this tool version.
`RC.downlinkSignal` and `RC.uplinkSignal` are unpopulated in all 23 files.
Raw `OSD.rcOutcontrol` is not included in this CSV view.
Identity/serial/name columns contain restricted information and must not
be published as values. `DETAILS.*` flight aggregates are not pre-event
features without a separate leakage review.

| CSV column | Decoded files whose header includes it (of 23) |
| --- | ---: |
| `APP.tip` | 23 |
| `APP.warn` | 23 |
| `BATTERY.cellNum` | 23 |
| `BATTERY.cellVoltage1` | 23 |
| `BATTERY.cellVoltage2` | 23 |
| `BATTERY.cellVoltage3` | 23 |
| `BATTERY.cellVoltage4` | 20 |
| `BATTERY.cellVoltage5` | 4 |
| `BATTERY.cellVoltage6` | 4 |
| `BATTERY.cellVoltageDeviation` | 23 |
| `BATTERY.chargeLevel` | 23 |
| `BATTERY.current` | 23 |
| `BATTERY.currentCapacity` | 23 |
| `BATTERY.fullCapacity` | 23 |
| `BATTERY.isCellVoltageEstimated` | 23 |
| `BATTERY.maxCellVoltageDeviation` | 23 |
| `BATTERY.maxTemperature` | 23 |
| `BATTERY.minTemperature` | 23 |
| `BATTERY.temperature` | 23 |
| `BATTERY.voltage` | 23 |
| `CAMERA.isPhoto` | 23 |
| `CAMERA.isVideo` | 23 |
| `CAMERA.sdCardIsInserted` | 23 |
| `CAMERA.sdCardState` | 23 |
| `CUSTOM.dateTime` | 23 |
| `DETAILS.aircraftName` | 23 |
| `DETAILS.aircraftSerial` | 23 |
| `DETAILS.appPlatform` | 23 |
| `DETAILS.appVersion` | 23 |
| `DETAILS.cameraSerial` | 23 |
| `DETAILS.maxHeight` | 23 |
| `DETAILS.maxHorizontalSpeed` | 23 |
| `DETAILS.maxVerticalSpeed` | 23 |
| `DETAILS.photoNum` | 23 |
| `DETAILS.rcSerial` | 23 |
| `DETAILS.totalDistance` | 23 |
| `DETAILS.totalTime` | 23 |
| `DETAILS.videoTime` | 23 |
| `GIMBAL.isPitchAtLimit` | 23 |
| `GIMBAL.isRollAtLimit` | 23 |
| `GIMBAL.isStuck` | 23 |
| `GIMBAL.isYawAtLimit` | 23 |
| `GIMBAL.mode` | 23 |
| `GIMBAL.pitch` | 23 |
| `GIMBAL.roll` | 23 |
| `GIMBAL.yaw` | 23 |
| `HOME.IOCCourseLockAngle` | 23 |
| `HOME.IOCMode` | 23 |
| `HOME.altitude` | 23 |
| `HOME.compassCalibrationState` | 23 |
| `HOME.currentFlightRecordIndex` | 23 |
| `HOME.goHomeHeight` | 23 |
| `HOME.goHomeMode` | 23 |
| `HOME.heightLimit` | 23 |
| `HOME.isBeginnerMode` | 23 |
| `HOME.isCompassCalibrating` | 23 |
| `HOME.isDynamicHomePointEnabled` | 23 |
| `HOME.isHomeRecord` | 23 |
| `HOME.isIOCEnabled` | 23 |
| `HOME.isMultipleModeEnabled` | 23 |
| `HOME.isNearDistanceLimit` | 23 |
| `HOME.isNearHeightLimit` | 23 |
| `HOME.latitude` | 23 |
| `HOME.longitude` | 23 |
| `HOME.maxAllowedHeight` | 23 |
| `OSD.altitude` | 23 |
| `OSD.batteryType` | 23 |
| `OSD.canIOCWork` | 23 |
| `OSD.droneType` | 23 |
| `OSD.flightAction` | 23 |
| `OSD.flyTime` | 23 |
| `OSD.flycCommand` | 23 |
| `OSD.flycState` | 23 |
| `OSD.goHomeStatus` | 23 |
| `OSD.gpsLevel` | 23 |
| `OSD.gpsNum` | 23 |
| `OSD.height` | 23 |
| `OSD.heightMax` | 23 |
| `OSD.imuInitFailReason` | 23 |
| `OSD.isAcceleratorOverRange` | 23 |
| `OSD.isBarometerDeadInAir` | 23 |
| `OSD.isCompassError` | 23 |
| `OSD.isGPSUsed` | 23 |
| `OSD.isGoHomeHeightModified` | 23 |
| `OSD.isImuPreheated` | 23 |
| `OSD.isMotorBlocked` | 23 |
| `OSD.isMotorOn` | 23 |
| `OSD.isNotEnoughForce` | 23 |
| `OSD.isOnGround` | 23 |
| `OSD.isOutOfLimit` | 23 |
| `OSD.isPropellerCatapult` | 23 |
| `OSD.isSwaveWork` | 23 |
| `OSD.isVibrating` | 23 |
| `OSD.isVisionUsed` | 23 |
| `OSD.latitude` | 23 |
| `OSD.longitude` | 23 |
| `OSD.motorStartFailedCause` | 23 |
| `OSD.nonGPSCause` | 23 |
| `OSD.pitch` | 23 |
| `OSD.roll` | 23 |
| `OSD.voltageWarning` | 23 |
| `OSD.vpsHeight` | 23 |
| `OSD.waveError` | 23 |
| `OSD.xSpeed` | 23 |
| `OSD.xSpeedMax` | 23 |
| `OSD.ySpeed` | 23 |
| `OSD.ySpeedMax` | 23 |
| `OSD.yaw` | 23 |
| `OSD.zSpeed` | 23 |
| `OSD.zSpeedMax` | 23 |
| `RC.aileron` | 23 |
| `RC.downlinkSignal` | 23 |
| `RC.elevator` | 23 |
| `RC.rudder` | 23 |
| `RC.throttle` | 23 |
| `RC.uplinkSignal` | 23 |
| `RECOVER.aircraftName` | 23 |
| `RECOVER.aircraftSerial` | 23 |
| `RECOVER.appPlatform` | 23 |
| `RECOVER.appVersion` | 23 |
| `RECOVER.batterySerial` | 23 |
| `RECOVER.cameraSerial` | 23 |
| `RECOVER.rcSerial` | 23 |

## Yuneec readable CSV schemas

56 of 101 flight-directory CSV candidates are readable UTF-8 tables.
The remaining 45 are binary/non-UTF-8 entries under `FlightEncryptLog`;
their extensions do not establish CSV readability. No decryption is attempted.
The first column is unnamed. Timestamp units, timezone and signal scale
are not admitted by this header inspection. CSV cells are read as text.

### Readable schema 1 (19 files)

| Column |
| --- |
| (unnamed first column) |
| `lon` |
| `lat` |
| `alt` |
| `accuracy` |
| `speed` |
| `angle` |

### Readable schema 2 (19 files)

| Column |
| --- |
| (unnamed first column) |
| `CH0` |
| `CH1` |
| `CH2` |
| `CH3` |
| `CH4` |
| `CH5` |
| `CH6` |
| `CH7` |
| `CH8` |
| `CH9` |
| `CH10` |
| `CH11` |
| `CH12` |
| `CH13` |
| `CH14` |
| `CH15` |
| `CH16` |
| `CH17` |
| `CH18` |
| `CH19` |
| `CH20` |
| `CH21` |
| `CH22` |
| `CH23` |

### Readable schema 3 (18 files)

| Column |
| --- |
| (unnamed first column) |
| `fsk_rssi` |
| `voltage` |
| `current` |
| `altitude` |
| `latitude` |
| `longitude` |
| `tas` |
| `gps_used` |
| `fix_type` |
| `satellites_num` |
| `roll` |
| `yaw` |
| `pitch` |
| `motor_status` |
| `imu_status` |
| `gps_status` |
| `cgps_used` |
| `press_compass_status` |
| `f_mode` |
| `gps_pos_used` |
| `vehicle_type` |
| `error_flags1` |
| `gps_accH` |

## Parrot flight-details table

One readable FreeFlight6 `flightDetails` JSON supplies 21 named columns
and 3,048 rows, plus a separate summary JSON. This is one observed recording,
not general Parrot support. Units and channel semantics remain unreviewed.

| Column |
| --- |
| `time` |
| `battery_level` |
| `controller_gps_latitude` |
| `controller_gps_longitude` |
| `flying_state` |
| `alert_state` |
| `wifi_signal` |
| `product_gps_available` |
| `product_gps_longitude` |
| `product_gps_latitude` |
| `product_gps_position_error` |
| `product_gps_sv_number` |
| `speed_vx` |
| `speed_vy` |
| `speed_vz` |
| `angle_phi` |
| `angle_theta` |
| `angle_psi` |
| `altitude` |
| `flip_type` |
| `speed` |

## Formats not decoded

The inspection does not decode DJI DAT, ArduPilot binary/MAVLink logs or
hashed iOS backup payloads. It does not enumerate every possible field in
those formats and does not establish any source as a loss-event dataset.
