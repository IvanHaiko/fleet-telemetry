# Observed PX4 telemetry fields

This generated catalog records field names and wire types observed in eleven local
ULog files; it contains no measurement values. It is a sample, not the full
PX4, MAVLink, drone or simulator schema. Types come from each file definition,
and array fields may be expanded by the parser. File IDs and limitations are
defined in [the source comparison](telemetry-source-inventory.md).

Presence lists files, not vehicles: multiple instances in one file count once.
A missing field can reflect firmware, hardware, settings or logging profile.
Units and semantics require the matching source version; names alone are not
an accepted normalized contract. No geolocation values or identifiers are shown.

## `action_request`

Observed in: F01, F03, F05, F06, F07, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `action` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `mode` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `source` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `timestamp` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |

## `actuator_armed`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `armed` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `armed_time_ms` | `uint32_t` (F02) | F02 |
| `force_failsafe` | `bool` (F02, F03, F04, F05, F06, F08, F09) | F02, F03, F04, F05, F06, F08, F09 |
| `in_esc_calibration_mode` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `kill` | `bool` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `lockdown` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `manual_lockdown` | `bool` (F02, F03, F04, F05, F06, F08, F09) | F02, F03, F04, F05, F06, F08, F09 |
| `prearmed` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ready_to_arm` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `soft_stop` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `termination` | `bool` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `actuator_controls_0`

Observed in: F02, F03, F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `control[0]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `control[1]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `control[2]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `control[3]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `control[4]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `control[5]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `control[6]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `control[7]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `timestamp` | `uint64_t` (F02, F03, F04) | F02, F03, F04 |
| `timestamp_sample` | `uint64_t` (F02, F03, F04) | F02, F03, F04 |

## `actuator_controls_3`

Observed in: F03.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `control[0]` | `float` (F03) | F03 |
| `control[1]` | `float` (F03) | F03 |
| `control[2]` | `float` (F03) | F03 |
| `control[3]` | `float` (F03) | F03 |
| `control[4]` | `float` (F03) | F03 |
| `control[5]` | `float` (F03) | F03 |
| `control[6]` | `float` (F03) | F03 |
| `control[7]` | `float` (F03) | F03 |
| `timestamp` | `uint64_t` (F03) | F03 |
| `timestamp_sample` | `uint64_t` (F03) | F03 |

## `actuator_controls_status_0`

Observed in: F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `control_power[0]` | `float` (F11) | F11 |
| `control_power[1]` | `float` (F11) | F11 |
| `control_power[2]` | `float` (F11) | F11 |
| `timestamp` | `uint64_t` (F11) | F11 |

## `actuator_motors`

Observed in: F01, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `control[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[10]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[11]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[3]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[4]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[5]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[6]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[7]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[8]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `control[9]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `reversible_flags` | `uint16_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |

## `actuator_outputs`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `noutputs` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[10]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[11]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[12]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[13]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[14]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[15]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[3]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[4]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[5]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[6]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[7]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[8]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output[9]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `actuator_servos`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `control[0]` | `float` (F09) | F09 |
| `control[1]` | `float` (F09) | F09 |
| `control[2]` | `float` (F09) | F09 |
| `control[3]` | `float` (F09) | F09 |
| `control[4]` | `float` (F09) | F09 |
| `control[5]` | `float` (F09) | F09 |
| `control[6]` | `float` (F09) | F09 |
| `control[7]` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |
| `timestamp_sample` | `uint64_t` (F09) | F09 |

## `airspeed`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `confidence` | `float` (F09) | F09 |
| `indicated_airspeed_m_s` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |
| `timestamp_sample` | `uint64_t` (F09) | F09 |
| `true_airspeed_m_s` | `float` (F09) | F09 |

## `airspeed_validated`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `airspeed_derivative_filtered` | `float` (F09) | F09 |
| `airspeed_source` | `int8_t` (F09) | F09 |
| `calibraded_airspeed_synth_m_s` | `float` (F09) | F09 |
| `calibrated_airspeed_m_s` | `float` (F09) | F09 |
| `calibrated_ground_minus_wind_m_s` | `float` (F09) | F09 |
| `indicated_airspeed_m_s` | `float` (F09) | F09 |
| `pitch_filtered` | `float` (F09) | F09 |
| `throttle_filtered` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |
| `true_airspeed_m_s` | `float` (F09) | F09 |

## `airspeed_wind`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `beta_innov` | `float` (F09) | F09 |
| `beta_innov_var` | `float` (F09) | F09 |
| `source` | `uint8_t` (F09) | F09 |
| `tas_innov` | `float` (F09) | F09 |
| `tas_innov_var` | `float` (F09) | F09 |
| `tas_scale_raw` | `float` (F09) | F09 |
| `tas_scale_raw_var` | `float` (F09) | F09 |
| `tas_scale_validated` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |
| `timestamp_sample` | `uint64_t` (F09) | F09 |
| `variance_east` | `float` (F09) | F09 |
| `variance_north` | `float` (F09) | F09 |
| `windspeed_east` | `float` (F09) | F09 |
| `windspeed_north` | `float` (F09) | F09 |

## `battery_status`

Observed in: F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `available_energy` | `float` (F03, F04, F06) | F03, F04, F06 |
| `average_current_a` | `float` (F02) | F02 |
| `average_power` | `float` (F03, F04, F06) | F03, F04, F06 |
| `average_time_to_empty` | `uint16_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `average_time_to_full` | `uint16_t` (F03, F04, F06) | F03, F04, F06 |
| `capacity` | `uint16_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cell_count` | `int32_t` (F02, F04); `uint8_t` (F03, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `connected` | `bool` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `current_a` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `current_average_a` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `current_filtered_a` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `custom_faults` | `uint32_t` (F03, F06) | F03, F06 |
| `cycle_count` | `uint16_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `design_capacity` | `float` (F03, F04, F06) | F03, F04, F06 |
| `discharged_mah` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `estimation_covariance_norm` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `faults` | `uint16_t` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `full_charge_capacity_wh` | `float` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `id` | `uint8_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `interface_error` | `uint16_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `internal_resistance_estimate` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `is_powering_off` | `bool` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `is_required` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `manufacture_date` | `uint16_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `max_cell_voltage_delta` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `max_error` | `uint16_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mode` | `uint8_t` (F03, F06) | F03, F06 |
| `nominal_voltage` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ocv_estimate` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `ocv_estimate_filtered` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `over_discharge_count` | `uint16_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `prediction_error` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `priority` | `uint8_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `remaining` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `remaining_capacity` | `float` (F04) | F04 |
| `remaining_capacity_wh` | `float` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `run_time_to_empty` | `uint16_t` (F02, F04) | F02, F04 |
| `scale` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `serial_number` | `uint16_t` (F02, F03, F04, F05, F06, F08, F09) | F02, F03, F04, F05, F06, F08, F09 |
| `source` | `uint8_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `state_of_health` | `uint16_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `temperature` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `time_remaining_s` | `float` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `volt_based_soc_estimate` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `voltage_cell_v[0]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[10]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[11]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[12]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[13]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[1]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[2]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[3]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[4]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[5]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[6]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[7]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[8]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_cell_v[9]` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_filtered_v` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `voltage_prediction` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `voltage_v` | `float` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `warning` | `uint8_t` (F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `can_interface_status`

Observed in: F01, F05, F07, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `frames_rx` | `uint64_t` (F01, F05, F07, F08, F09) | F01, F05, F07, F08, F09 |
| `frames_tx` | `uint64_t` (F01, F05, F07, F08, F09) | F01, F05, F07, F08, F09 |
| `interface` | `uint8_t` (F01, F05, F07, F08, F09) | F01, F05, F07, F08, F09 |
| `io_errors` | `uint64_t` (F01, F05, F07, F08, F09) | F01, F05, F07, F08, F09 |
| `timestamp` | `uint64_t` (F01, F05, F07, F08, F09) | F01, F05, F07, F08, F09 |

## `commander_state`

Observed in: F02, F03, F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `main_state` | `uint8_t` (F02, F03, F04) | F02, F03, F04 |
| `main_state_changes` | `uint16_t` (F03, F04) | F03, F04 |
| `timestamp` | `uint64_t` (F02, F03, F04) | F02, F03, F04 |

## `config_overrides`

Observed in: F01, F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `defer_failsafes` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `defer_failsafes_timeout_s` | `int16_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `disable_auto_disarm` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `disable_auto_set_home` | `bool` (F10, F11) | F10, F11 |
| `source_id` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `source_type` | `int8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |

## `control_allocator_status`

Observed in: F01, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `actuator_group_preflight_check_active` | `bool` (F10, F11) | F10, F11 |
| `actuator_saturation[0]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[10]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[11]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[12]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[13]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[14]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[15]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[1]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[2]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[3]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[4]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[5]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[6]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[7]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[8]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `actuator_saturation[9]` | `int8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `handled_motor_failure_mask` | `uint16_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `motor_stop_mask` | `uint16_t` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `thrust_setpoint_achieved` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `torque_setpoint_achieved` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `unallocated_thrust[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `unallocated_thrust[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `unallocated_thrust[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `unallocated_torque[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `unallocated_torque[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `unallocated_torque[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |

## `cpuload`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `load` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ram_usage` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `differential_pressure`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F09) | F09 |
| `differential_pressure_pa` | `float` (F09) | F09 |
| `error_count` | `uint32_t` (F09) | F09 |
| `temperature` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |
| `timestamp_sample` | `uint64_t` (F09) | F09 |

## `distance_sensor`

Observed in: F03, F08, F10.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `current_distance` | `float` (F03, F08, F10) | F03, F08, F10 |
| `device_id` | `uint32_t` (F03, F08, F10) | F03, F08, F10 |
| `h_fov` | `float` (F03, F08, F10) | F03, F08, F10 |
| `max_distance` | `float` (F03, F08, F10) | F03, F08, F10 |
| `min_distance` | `float` (F03, F08, F10) | F03, F08, F10 |
| `mode` | `uint8_t` (F08, F10) | F08, F10 |
| `orientation` | `uint8_t` (F03, F08, F10) | F03, F08, F10 |
| `q[0]` | `float` (F03, F08, F10) | F03, F08, F10 |
| `q[1]` | `float` (F03, F08, F10) | F03, F08, F10 |
| `q[2]` | `float` (F03, F08, F10) | F03, F08, F10 |
| `q[3]` | `float` (F03, F08, F10) | F03, F08, F10 |
| `signal_quality` | `int8_t` (F03, F08, F10) | F03, F08, F10 |
| `timestamp` | `uint64_t` (F03, F08, F10) | F03, F08, F10 |
| `type` | `uint8_t` (F03, F08, F10) | F03, F08, F10 |
| `v_fov` | `float` (F03, F08, F10) | F03, F08, F10 |
| `variance` | `float` (F03, F08, F10) | F03, F08, F10 |

## `distance_sensor_mode_change_request`

Observed in: F01, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `request_on_off` | `uint8_t` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |

## `dronecan_node_status`

Observed in: F01.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `health` | `uint8_t` (F01) | F01 |
| `mode` | `uint8_t` (F01) | F01 |
| `node_id` | `uint16_t` (F01) | F01 |
| `sub_mode` | `uint8_t` (F01) | F01 |
| `timestamp` | `uint64_t` (F01) | F01 |
| `uptime_sec` | `uint32_t` (F01) | F01 |
| `vendor_specific_status_code` | `uint16_t` (F01) | F01 |

## `ekf2_timestamps`

Observed in: F04, F07, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `airspeed_timestamp_rel` | `int16_t` (F04, F07, F10, F11) | F04, F07, F10, F11 |
| `airspeed_validated_timestamp_rel` | `int16_t` (F07, F10, F11) | F07, F10, F11 |
| `distance_sensor_timestamp_rel` | `int16_t` (F04, F07, F10, F11) | F04, F07, F10, F11 |
| `optical_flow_timestamp_rel` | `int16_t` (F04, F07, F10, F11) | F04, F07, F10, F11 |
| `timestamp` | `uint64_t` (F04, F07, F10, F11) | F04, F07, F10, F11 |
| `vehicle_air_data_timestamp_rel` | `int16_t` (F04, F07, F10, F11) | F04, F07, F10, F11 |
| `vehicle_magnetometer_timestamp_rel` | `int16_t` (F04, F07, F10, F11) | F04, F07, F10, F11 |
| `visual_odometry_timestamp_rel` | `int16_t` (F04, F07, F10, F11) | F04, F07, F10, F11 |

## `ekf_gps_drift`

Observed in: F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `blocked` | `bool` (F04) | F04 |
| `hpos_drift_rate` | `float` (F04) | F04 |
| `hspd` | `float` (F04) | F04 |
| `timestamp` | `uint64_t` (F04) | F04 |
| `vpos_drift_rate` | `float` (F04) | F04 |

## `esc_status`

Observed in: F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `counter` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[0]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[0]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[0]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[0]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[0]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[0].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[0].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[0].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[0].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[0].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[0].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[0].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[0].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[0].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[0].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[0].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[10]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[10]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[10]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[10]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[10]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[10].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[10].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[10].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[10].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[10].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[10].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[10].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[10].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[10].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[10].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[10].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[11]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[11]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[11]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[11]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[11]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[11].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[11].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[11].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[11].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[11].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[11].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[11].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[11].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[11].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[11].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[11].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[1]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[1]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[1]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[1]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[1]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[1].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[1].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[1].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[1].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[1].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[1].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[1].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[1].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[1].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[1].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[1].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[2]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[2]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[2]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[2]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[2]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[2].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[2].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[2].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[2].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[2].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[2].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[2].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[2].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[2].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[2].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[2].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[3]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[3]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[3]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[3]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[3]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[3].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[3].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[3].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[3].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[3].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[3].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[3].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[3].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[3].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[3].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[3].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[4]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[4]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[4]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[4]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[4]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[4].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[4].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[4].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[4].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[4].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[4].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[4].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[4].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[4].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[4].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[4].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[5]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[5]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[5]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[5]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[5]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[5].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[5].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[5].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[5].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[5].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[5].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[5].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[5].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[5].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[5].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[5].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[6]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[6]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[6]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[6]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[6]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[6].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[6].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[6].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[6].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[6].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[6].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[6].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[6].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[6].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[6].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[6].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[7]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[7]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[7]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[7]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[7]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[7].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[7].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[7].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[7].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[7].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[7].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[7].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[7].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[7].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[7].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[7].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[8]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[8]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[8]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[8]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[8]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[8].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[8].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[8].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[8].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[8].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[8].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[8].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[8].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[8].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[8].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[8].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc[9]._padding0[0]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[9]._padding0[1]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[9]._padding0[2]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[9]._padding0[3]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[9]._padding0[4]` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[9].actuator_function` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[9].esc_current` | `float` (F10, F11) | F10, F11 |
| `esc[9].esc_errorcount` | `uint32_t` (F10, F11) | F10, F11 |
| `esc[9].esc_power` | `int8_t` (F10, F11) | F10, F11 |
| `esc[9].esc_rpm` | `int32_t` (F10, F11) | F10, F11 |
| `esc[9].esc_state` | `uint8_t` (F10, F11) | F10, F11 |
| `esc[9].esc_temperature` | `float` (F10, F11) | F10, F11 |
| `esc[9].esc_voltage` | `float` (F10, F11) | F10, F11 |
| `esc[9].failures` | `uint16_t` (F10, F11) | F10, F11 |
| `esc[9].motor_temperature` | `int16_t` (F10, F11) | F10, F11 |
| `esc[9].timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `esc_armed_flags` | `uint16_t` (F10, F11) | F10, F11 |
| `esc_connectiontype` | `uint8_t` (F10, F11) | F10, F11 |
| `esc_count` | `uint8_t` (F10, F11) | F10, F11 |
| `esc_online_flags` | `uint16_t` (F10, F11) | F10, F11 |
| `timestamp` | `uint64_t` (F10, F11) | F10, F11 |

## `estimator_aid_src_baro_hgt`

Observed in: F01, F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `estimator_instance` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `fused` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_filtered` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_rejected` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_variance` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation_variance` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `time_last_fuse` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |

## `estimator_aid_src_ev_hgt`

Observed in: F01.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01) | F01 |
| `estimator_instance` | `uint8_t` (F01) | F01 |
| `fused` | `bool` (F01) | F01 |
| `innovation` | `float` (F01) | F01 |
| `innovation_filtered` | `float` (F01) | F01 |
| `innovation_rejected` | `bool` (F01) | F01 |
| `innovation_variance` | `float` (F01) | F01 |
| `observation` | `float` (F01) | F01 |
| `observation_variance` | `float` (F01) | F01 |
| `test_ratio` | `float` (F01) | F01 |
| `test_ratio_filtered` | `float` (F01) | F01 |
| `time_last_fuse` | `uint64_t` (F01) | F01 |
| `timestamp` | `uint64_t` (F01) | F01 |
| `timestamp_sample` | `uint64_t` (F01) | F01 |

## `estimator_aid_src_ev_pos`

Observed in: F01.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01) | F01 |
| `estimator_instance` | `uint8_t` (F01) | F01 |
| `fused` | `bool` (F01) | F01 |
| `innovation[0]` | `float` (F01) | F01 |
| `innovation[1]` | `float` (F01) | F01 |
| `innovation_filtered[0]` | `float` (F01) | F01 |
| `innovation_filtered[1]` | `float` (F01) | F01 |
| `innovation_rejected` | `bool` (F01) | F01 |
| `innovation_variance[0]` | `float` (F01) | F01 |
| `innovation_variance[1]` | `float` (F01) | F01 |
| `observation[0]` | `double` (F01) | F01 |
| `observation[1]` | `double` (F01) | F01 |
| `observation_variance[0]` | `float` (F01) | F01 |
| `observation_variance[1]` | `float` (F01) | F01 |
| `test_ratio[0]` | `float` (F01) | F01 |
| `test_ratio[1]` | `float` (F01) | F01 |
| `test_ratio_filtered[0]` | `float` (F01) | F01 |
| `test_ratio_filtered[1]` | `float` (F01) | F01 |
| `time_last_fuse` | `uint64_t` (F01) | F01 |
| `timestamp` | `uint64_t` (F01) | F01 |
| `timestamp_sample` | `uint64_t` (F01) | F01 |

## `estimator_aid_src_ev_yaw`

Observed in: F01.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01) | F01 |
| `estimator_instance` | `uint8_t` (F01) | F01 |
| `fused` | `bool` (F01) | F01 |
| `innovation` | `float` (F01) | F01 |
| `innovation_filtered` | `float` (F01) | F01 |
| `innovation_rejected` | `bool` (F01) | F01 |
| `innovation_variance` | `float` (F01) | F01 |
| `observation` | `float` (F01) | F01 |
| `observation_variance` | `float` (F01) | F01 |
| `test_ratio` | `float` (F01) | F01 |
| `test_ratio_filtered` | `float` (F01) | F01 |
| `time_last_fuse` | `uint64_t` (F01) | F01 |
| `timestamp` | `uint64_t` (F01) | F01 |
| `timestamp_sample` | `uint64_t` (F01) | F01 |

## `estimator_aid_src_fake_hgt`

Observed in: F09, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F09, F11) | F09, F11 |
| `estimator_instance` | `uint8_t` (F09, F11) | F09, F11 |
| `fused` | `bool` (F09, F11) | F09, F11 |
| `innovation` | `float` (F09, F11) | F09, F11 |
| `innovation_filtered` | `float` (F09, F11) | F09, F11 |
| `innovation_rejected` | `bool` (F09, F11) | F09, F11 |
| `innovation_variance` | `float` (F09, F11) | F09, F11 |
| `observation` | `float` (F09, F11) | F09, F11 |
| `observation_variance` | `float` (F09, F11) | F09, F11 |
| `test_ratio` | `float` (F09, F11) | F09, F11 |
| `test_ratio_filtered` | `float` (F09, F11) | F09, F11 |
| `time_last_fuse` | `uint64_t` (F09, F11) | F09, F11 |
| `timestamp` | `uint64_t` (F09, F11) | F09, F11 |
| `timestamp_sample` | `uint64_t` (F09, F11) | F09, F11 |

## `estimator_aid_src_fake_pos`

Observed in: F09, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F09, F11) | F09, F11 |
| `estimator_instance` | `uint8_t` (F09, F11) | F09, F11 |
| `fused` | `bool` (F09, F11) | F09, F11 |
| `innovation[0]` | `float` (F09, F11) | F09, F11 |
| `innovation[1]` | `float` (F09, F11) | F09, F11 |
| `innovation_filtered[0]` | `float` (F09, F11) | F09, F11 |
| `innovation_filtered[1]` | `float` (F09, F11) | F09, F11 |
| `innovation_rejected` | `bool` (F09, F11) | F09, F11 |
| `innovation_variance[0]` | `float` (F09, F11) | F09, F11 |
| `innovation_variance[1]` | `float` (F09, F11) | F09, F11 |
| `observation[0]` | `double` (F09, F11) | F09, F11 |
| `observation[1]` | `double` (F09, F11) | F09, F11 |
| `observation_variance[0]` | `float` (F09, F11) | F09, F11 |
| `observation_variance[1]` | `float` (F09, F11) | F09, F11 |
| `test_ratio[0]` | `float` (F09, F11) | F09, F11 |
| `test_ratio[1]` | `float` (F09, F11) | F09, F11 |
| `test_ratio_filtered[0]` | `float` (F09, F11) | F09, F11 |
| `test_ratio_filtered[1]` | `float` (F09, F11) | F09, F11 |
| `time_last_fuse` | `uint64_t` (F09, F11) | F09, F11 |
| `timestamp` | `uint64_t` (F09, F11) | F09, F11 |
| `timestamp_sample` | `uint64_t` (F09, F11) | F09, F11 |

## `estimator_aid_src_gnss_hgt`

Observed in: F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `estimator_instance` | `uint8_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `fused` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_filtered` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_rejected` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_variance` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation_variance` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `time_last_fuse` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |

## `estimator_aid_src_gnss_pos`

Observed in: F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `estimator_instance` | `uint8_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `fused` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_rejected` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_variance[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_variance[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation[0]` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation[1]` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation_variance[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation_variance[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `time_last_fuse` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |

## `estimator_aid_src_gnss_vel`

Observed in: F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `estimator_instance` | `uint8_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `fused` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation[2]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[2]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_rejected` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_variance[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_variance[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `innovation_variance[2]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation[2]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation_variance[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation_variance[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `observation_variance[2]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio[2]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[0]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[1]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[2]` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `time_last_fuse` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |

## `estimator_aid_src_gravity`

Observed in: F01, F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `estimator_instance` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `fused` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_rejected` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_variance[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_variance[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_variance[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation_variance[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation_variance[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation_variance[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `time_last_fuse` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |

## `estimator_aid_src_mag`

Observed in: F01, F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `estimator_instance` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `fused` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_filtered[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_rejected` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_variance[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_variance[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innovation_variance[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation_variance[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation_variance[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `observation_variance[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[0]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[1]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `test_ratio_filtered[2]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `time_last_fuse` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |

## `estimator_aid_src_rng_hgt`

Observed in: F08, F10.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F08, F10) | F08, F10 |
| `estimator_instance` | `uint8_t` (F08, F10) | F08, F10 |
| `fused` | `bool` (F08, F10) | F08, F10 |
| `innovation` | `float` (F08, F10) | F08, F10 |
| `innovation_filtered` | `float` (F08, F10) | F08, F10 |
| `innovation_rejected` | `bool` (F08, F10) | F08, F10 |
| `innovation_variance` | `float` (F08, F10) | F08, F10 |
| `observation` | `float` (F08, F10) | F08, F10 |
| `observation_variance` | `float` (F08, F10) | F08, F10 |
| `test_ratio` | `float` (F08, F10) | F08, F10 |
| `test_ratio_filtered` | `float` (F08, F10) | F08, F10 |
| `time_last_fuse` | `uint64_t` (F08, F10) | F08, F10 |
| `timestamp` | `uint64_t` (F08, F10) | F08, F10 |
| `timestamp_sample` | `uint64_t` (F08, F10) | F08, F10 |

## `estimator_attitude`

Observed in: F01, F03, F04, F05, F06, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `delta_q_reset[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_q_reset[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_q_reset[2]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_q_reset[3]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `q[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `q[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `q[2]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `q[3]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `quat_reset_counter` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |

## `estimator_baro_bias`

Observed in: F01, F03, F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `baro_device_id` | `uint32_t` (F03) | F03 |
| `bias` | `float` (F01, F03, F05, F07, F08, F09, F10, F11) | F01, F03, F05, F07, F08, F09, F10, F11 |
| `bias_var` | `float` (F01, F03, F05, F07, F08, F09, F10, F11) | F01, F03, F05, F07, F08, F09, F10, F11 |
| `device_id` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `innov` | `float` (F01, F03, F05, F07, F08, F09, F10, F11) | F01, F03, F05, F07, F08, F09, F10, F11 |
| `innov_test_ratio` | `float` (F01, F03, F05, F07, F08, F09, F10, F11) | F01, F03, F05, F07, F08, F09, F10, F11 |
| `innov_var` | `float` (F01, F03, F05, F07, F08, F09, F10, F11) | F01, F03, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F05, F07, F08, F09, F10, F11) | F01, F03, F05, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F05, F07, F08, F09, F10, F11) | F01, F03, F05, F07, F08, F09, F10, F11 |

## `estimator_event_flags`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `bad_yaw_using_gps_course` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `emergency_yaw_reset_gps_yaw_stopped` | `bool` (F03, F06) | F03, F06 |
| `emergency_yaw_reset_mag_stopped` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `gps_checks_passed` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_data_stopped` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `gps_data_stopped_using_alternate` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `gps_fusion_timout` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `gps_quality_poor` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `height_sensor_timeout` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `information_event_changes` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `invalid_accel_bias_cov_reset` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `reset_hgt_to_baro` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `reset_hgt_to_ev` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `reset_hgt_to_gps` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `reset_hgt_to_rng` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `reset_pos_to_gps` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_pos_to_last_known` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_pos_to_vision` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_vel_to_flow` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_vel_to_gps` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_vel_to_vision` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_vel_to_zero` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `starting_gps_fusion` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `starting_vision_pos_fusion` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `starting_vision_vel_fusion` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `starting_vision_yaw_fusion` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `stopping_mag_use` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `stopping_navigation` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vision_data_stopped` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `warning_event_changes` | `uint32_t` (F03, F04, F06) | F03, F04, F06 |
| `yaw_aligned_to_imu_gps` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `estimator_fusion_control`

Observed in: F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `agp_active[0]` | `bool` (F11) | F11 |
| `agp_active[1]` | `bool` (F11) | F11 |
| `agp_active[2]` | `bool` (F11) | F11 |
| `agp_active[3]` | `bool` (F11) | F11 |
| `agp_intended[0]` | `bool` (F11) | F11 |
| `agp_intended[1]` | `bool` (F11) | F11 |
| `agp_intended[2]` | `bool` (F11) | F11 |
| `agp_intended[3]` | `bool` (F11) | F11 |
| `aspd_active` | `bool` (F11) | F11 |
| `aspd_intended` | `bool` (F11) | F11 |
| `baro_active` | `bool` (F11) | F11 |
| `baro_intended` | `bool` (F11) | F11 |
| `ev_active` | `bool` (F11) | F11 |
| `ev_intended` | `bool` (F11) | F11 |
| `gps_active[0]` | `bool` (F11) | F11 |
| `gps_active[1]` | `bool` (F11) | F11 |
| `gps_intended[0]` | `bool` (F11) | F11 |
| `gps_intended[1]` | `bool` (F11) | F11 |
| `mag_active` | `bool` (F11) | F11 |
| `mag_intended` | `bool` (F11) | F11 |
| `of_active` | `bool` (F11) | F11 |
| `of_intended` | `bool` (F11) | F11 |
| `rng_active` | `bool` (F11) | F11 |
| `rng_intended` | `bool` (F11) | F11 |
| `rngbcn_active` | `bool` (F11) | F11 |
| `rngbcn_intended` | `bool` (F11) | F11 |
| `timestamp` | `uint64_t` (F11) | F11 |

## `estimator_global_position`

Observed in: F03, F04, F05, F06, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt` | `float` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `alt_ellipsoid` | `float` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `alt_reset_counter` | `uint8_t` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `alt_valid` | `bool` (F05, F08, F09) | F05, F08, F09 |
| `dead_reckoning` | `bool` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `delta_alt` | `float` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `delta_terrain` | `float` (F05, F08, F09) | F05, F08, F09 |
| `eph` | `float` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `epv` | `float` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `lat` | `double` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `lat_lon_reset_counter` | `uint8_t` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `lat_lon_valid` | `bool` (F05, F08, F09) | F05, F08, F09 |
| `lon` | `double` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `terrain_alt` | `float` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `terrain_alt_valid` | `bool` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `terrain_reset_counter` | `uint8_t` (F05, F08, F09) | F05, F08, F09 |
| `timestamp` | `uint64_t` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |
| `timestamp_sample` | `uint64_t` (F03, F04, F05, F06, F08, F09) | F03, F04, F05, F06, F08, F09 |

## `estimator_gnss_hgt_bias`

Observed in: F10.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `bias` | `float` (F10) | F10 |
| `bias_var` | `float` (F10) | F10 |
| `device_id` | `uint32_t` (F10) | F10 |
| `innov` | `float` (F10) | F10 |
| `innov_test_ratio` | `float` (F10) | F10 |
| `innov_var` | `float` (F10) | F10 |
| `timestamp` | `uint64_t` (F10) | F10 |
| `timestamp_sample` | `uint64_t` (F10) | F10 |

## `estimator_gps_status`

Observed in: F03, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `check_fail_gps_fix` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_horz_drift` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_horz_err` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_horz_spd_err` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_pdop` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_spd_err` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_vert_drift` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_vert_err` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_max_vert_spd_err` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_min_sat_count` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `check_fail_spoofed_gps` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `checks_passed` | `bool` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `filtered_horizontal_speed_m_s` | `float` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `position_drift_rate_horizontal_m_s` | `float` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `position_drift_rate_vertical_m_s` | `float` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |

## `estimator_innovation_test_ratios`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `airspeed` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_vvel` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `baro_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `beta` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `drag[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `drag[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hpos[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hpos[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_vvel` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fake_hpos[0]` | `float` (F02) | F02 |
| `fake_hpos[1]` | `float` (F02) | F02 |
| `fake_hvel[0]` | `float` (F02) | F02 |
| `fake_hvel[1]` | `float` (F02) | F02 |
| `fake_vpos` | `float` (F02) | F02 |
| `fake_vvel` | `float` (F02) | F02 |
| `flow[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flow[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hpos[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hpos[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_vvel` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `hagl` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hagl_rate` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `heading` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rng_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `terr_flow[0]` | `float` (F06) | F06 |
| `terr_flow[1]` | `float` (F06) | F06 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `estimator_innovation_variances`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `airspeed` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_vvel` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `baro_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `beta` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `drag[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `drag[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hpos[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hpos[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_vvel` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fake_hpos[0]` | `float` (F02) | F02 |
| `fake_hpos[1]` | `float` (F02) | F02 |
| `fake_hvel[0]` | `float` (F02) | F02 |
| `fake_hvel[1]` | `float` (F02) | F02 |
| `fake_vpos` | `float` (F02) | F02 |
| `fake_vvel` | `float` (F02) | F02 |
| `flow[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flow[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hpos[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hpos[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_vvel` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `hagl` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hagl_rate` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `heading` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rng_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `terr_flow[0]` | `float` (F06) | F06 |
| `terr_flow[1]` | `float` (F06) | F06 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `estimator_innovations`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `airspeed` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `aux_vvel` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `baro_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `beta` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `drag[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `drag[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hpos[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hpos[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ev_vvel` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fake_hpos[0]` | `float` (F02) | F02 |
| `fake_hpos[1]` | `float` (F02) | F02 |
| `fake_hvel[0]` | `float` (F02) | F02 |
| `fake_hvel[1]` | `float` (F02) | F02 |
| `fake_vpos` | `float` (F02) | F02 |
| `fake_vvel` | `float` (F02) | F02 |
| `flow[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flow[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hpos[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hpos[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hvel[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_hvel[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_vvel` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gravity[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `hagl` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hagl_rate` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `heading` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_field[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rng_vpos` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `terr_flow[0]` | `float` (F06) | F06 |
| `terr_flow[1]` | `float` (F06) | F06 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `estimator_local_position`

Observed in: F01, F03, F04, F05, F06, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `ax` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `ay` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `az` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `dead_reckoning` | `bool` (F01, F05, F06, F08, F09) | F01, F05, F06, F08, F09 |
| `delta_dist_bottom` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `delta_heading` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_vxy[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_vxy[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_vz` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_xy[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_xy[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `delta_z` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `dist_bottom` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `dist_bottom_reset_counter` | `uint8_t` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `dist_bottom_sensor_bitfield` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `dist_bottom_valid` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `dist_bottom_var` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `eph` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `epv` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `evh` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `evv` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `hagl_max` | `float` (F03, F04, F06) | F03, F04, F06 |
| `hagl_max_xy` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `hagl_max_z` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `hagl_min` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `heading` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `heading_good_for_control` | `bool` (F01, F03, F05, F06, F08, F09) | F01, F03, F05, F06, F08, F09 |
| `heading_reset_counter` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `heading_var` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `ref_alt` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `ref_lat` | `double` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `ref_lon` | `double` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `ref_timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `tilt_var` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `unaided_heading` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `v_xy_valid` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `v_z_valid` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `vx` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `vxy_max` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `vxy_reset_counter` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `vy` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `vz` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `vz_max` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `vz_reset_counter` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `x` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `xy_global` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `xy_reset_counter` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `xy_valid` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `y` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `z` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `z_deriv` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `z_global` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `z_reset_counter` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `z_valid` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |

## `estimator_odometry`

Observed in: F01, F05, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `angular_velocity[0]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `angular_velocity[1]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `angular_velocity[2]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `orientation_variance[0]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `orientation_variance[1]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `orientation_variance[2]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `pose_frame` | `uint8_t` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `position[0]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `position[1]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `position[2]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `position_variance[0]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `position_variance[1]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `position_variance[2]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `q[0]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `q[1]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `q[2]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `q[3]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `quality` | `int8_t` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `reset_counter` | `uint8_t` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `timestamp` | `uint64_t` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `timestamp_sample` | `uint64_t` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `velocity[0]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `velocity[1]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `velocity[2]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `velocity_frame` | `uint8_t` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `velocity_variance[0]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `velocity_variance[1]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |
| `velocity_variance[2]` | `float` (F01, F05, F08, F09) | F01, F05, F08, F09 |

## `estimator_optical_flow_vel`

Observed in: F03.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `flow_compensated_integral[0]` | `float` (F03) | F03 |
| `flow_compensated_integral[1]` | `float` (F03) | F03 |
| `flow_uncompensated_integral[0]` | `float` (F03) | F03 |
| `flow_uncompensated_integral[1]` | `float` (F03) | F03 |
| `gyro_rate_integral[0]` | `float` (F03) | F03 |
| `gyro_rate_integral[1]` | `float` (F03) | F03 |
| `gyro_rate_integral[2]` | `float` (F03) | F03 |
| `timestamp` | `uint64_t` (F03) | F03 |
| `timestamp_sample` | `uint64_t` (F03) | F03 |
| `vel_body[0]` | `float` (F03) | F03 |
| `vel_body[1]` | `float` (F03) | F03 |
| `vel_ne[0]` | `float` (F03) | F03 |
| `vel_ne[1]` | `float` (F03) | F03 |

## `estimator_selector_status`

Observed in: F01, F03, F04, F05, F06, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accel_fault_detected` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_accel_error[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_accel_error[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_accel_error[2]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_accel_error[3]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_gyro_error[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_gyro_error[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_gyro_error[2]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `accumulated_gyro_error[3]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `baro_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[2]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[3]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[4]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[5]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[6]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[7]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `combined_test_ratio[8]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `gyro_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `gyro_fault_detected` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[0]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[1]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[2]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[3]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[4]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[5]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[6]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[7]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `healthy[8]` | `bool` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `instance_changed_count` | `uint32_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `instances_available` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `last_instance_change` | `uint64_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `mag_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `primary_instance` | `uint8_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[0]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[1]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[2]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[3]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[4]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[5]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[6]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[7]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `relative_test_ratio[8]` | `float` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F08, F09) | F01, F03, F04, F05, F06, F08, F09 |

## `estimator_sensor_bias`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_bias[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias_limit` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias_stable` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias_valid` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias_variance[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias_variance[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_bias_variance[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias_limit` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias_stable` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias_valid` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias_variance[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias_variance[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_bias_variance[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias_limit` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias_stable` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias_valid` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias_variance[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias_variance[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_bias_variance[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `estimator_states`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `covariances[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[10]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[11]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[12]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[13]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[14]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[15]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[16]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[17]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[18]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[19]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[20]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[21]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[22]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[23]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[3]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[4]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[5]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[6]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[7]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[8]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[9]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `n_states` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[10]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[11]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[12]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[13]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[14]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[15]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[16]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[17]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[18]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[19]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[20]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[21]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[22]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[23]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[24]` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `states[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[3]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[4]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[5]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[6]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[7]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[8]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[9]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `estimator_status`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `baro_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `beta_test_ratio` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `control_mode_flags` | `uint32_t` (F02, F03, F04); `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `covariances[0]` | `float` (F02) | F02 |
| `covariances[10]` | `float` (F02) | F02 |
| `covariances[11]` | `float` (F02) | F02 |
| `covariances[12]` | `float` (F02) | F02 |
| `covariances[13]` | `float` (F02) | F02 |
| `covariances[14]` | `float` (F02) | F02 |
| `covariances[15]` | `float` (F02) | F02 |
| `covariances[16]` | `float` (F02) | F02 |
| `covariances[17]` | `float` (F02) | F02 |
| `covariances[18]` | `float` (F02) | F02 |
| `covariances[19]` | `float` (F02) | F02 |
| `covariances[1]` | `float` (F02) | F02 |
| `covariances[20]` | `float` (F02) | F02 |
| `covariances[21]` | `float` (F02) | F02 |
| `covariances[22]` | `float` (F02) | F02 |
| `covariances[23]` | `float` (F02) | F02 |
| `covariances[2]` | `float` (F02) | F02 |
| `covariances[3]` | `float` (F02) | F02 |
| `covariances[4]` | `float` (F02) | F02 |
| `covariances[5]` | `float` (F02) | F02 |
| `covariances[6]` | `float` (F02) | F02 |
| `covariances[7]` | `float` (F02) | F02 |
| `covariances[8]` | `float` (F02) | F02 |
| `covariances[9]` | `float` (F02) | F02 |
| `filter_fault_flags` | `uint16_t` (F02); `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gps_check_fail_flags` | `uint16_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hagl_test_ratio` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hdg_test_ratio` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `health_flags` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hgt_test_ratio` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innovation_check_flags` | `uint16_t` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `mag_device_id` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mag_inclination_deg` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `mag_inclination_ref_deg` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `mag_strength_gs` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `mag_strength_ref_gs` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `mag_test_ratio` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `n_states` | `uint8_t` (F02) | F02 |
| `output_tracking_error[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output_tracking_error[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `output_tracking_error[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pos_horiz_accuracy` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pos_test_ratio` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pos_vert_accuracy` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pre_flt_fail_innov_heading` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pre_flt_fail_innov_height` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pre_flt_fail_innov_pos_horiz` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `pre_flt_fail_innov_vel_horiz` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pre_flt_fail_innov_vel_vert` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pre_flt_fail_mag_field_disturbed` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_count_pod_d` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_count_pos_ne` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_count_quat` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_count_vel_d` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_count_vel_ne` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `solution_status_flags` | `uint16_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `states[0]` | `float` (F02) | F02 |
| `states[10]` | `float` (F02) | F02 |
| `states[11]` | `float` (F02) | F02 |
| `states[12]` | `float` (F02) | F02 |
| `states[13]` | `float` (F02) | F02 |
| `states[14]` | `float` (F02) | F02 |
| `states[15]` | `float` (F02) | F02 |
| `states[16]` | `float` (F02) | F02 |
| `states[17]` | `float` (F02) | F02 |
| `states[18]` | `float` (F02) | F02 |
| `states[19]` | `float` (F02) | F02 |
| `states[1]` | `float` (F02) | F02 |
| `states[20]` | `float` (F02) | F02 |
| `states[21]` | `float` (F02) | F02 |
| `states[22]` | `float` (F02) | F02 |
| `states[23]` | `float` (F02) | F02 |
| `states[2]` | `float` (F02) | F02 |
| `states[3]` | `float` (F02) | F02 |
| `states[4]` | `float` (F02) | F02 |
| `states[5]` | `float` (F02) | F02 |
| `states[6]` | `float` (F02) | F02 |
| `states[7]` | `float` (F02) | F02 |
| `states[8]` | `float` (F02) | F02 |
| `states[9]` | `float` (F02) | F02 |
| `tas_test_ratio` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `time_slip` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timeout_flags` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_test_ratio` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vibe[0]` | `float` (F02, F04) | F02, F04 |
| `vibe[1]` | `float` (F02, F04) | F02, F04 |
| `vibe[2]` | `float` (F02, F04) | F02, F04 |

## `estimator_status_flags`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `control_status_changes` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_aux_gpos` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_baro_fault` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_baro_hgt` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_constant_pos` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_ev_hgt` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_ev_pos` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_ev_vel` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_ev_yaw` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_ev_yaw_fault` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_fake_hgt` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `cs_fake_pos` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `cs_fixed_wing` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_fuse_aspd` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_fuse_beta` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_gnd_effect` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_gnss_fault` | `bool` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `cs_gnss_hgt_fault` | `bool` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `cs_gnss_pos` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_gnss_vel` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_gnss_yaw` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_gnss_yaw_fault` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_gps` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `cs_gps_hgt` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_gps_yaw` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `cs_gps_yaw_fault` | `bool` (F03, F06) | F03, F06 |
| `cs_gravity_vector` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `cs_heading_observable` | `bool` (F10, F11) | F10, F11 |
| `cs_in_air` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_in_transition` | `bool` (F10, F11) | F10, F11 |
| `cs_inertial_dead_reckoning` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `cs_mag` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_mag_3d` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_mag_aligned_in_flight` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_mag_dec` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_mag_fault` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_mag_field_disturbed` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_mag_hdg` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_mag_heading_consistent` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_opt_flow` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_opt_flow_terrain` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_rng_fault` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `cs_rng_hgt` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_rng_kin_consistent` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `cs_rng_stuck` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_rng_terrain` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_synthetic_mag_z` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_tilt_align` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_valid_fake_pos` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `cs_vehicle_at_rest` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_wind` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_wind_dead_reckoning` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `cs_yaw_align` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cs_yaw_manual` | `bool` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `fault_status_changes` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_acc_bias` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `fs_bad_acc_clipping` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_acc_vertical` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_airspeed` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_hdg` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_mag_decl` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_mag_x` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_mag_y` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_mag_z` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_optflow_x` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_optflow_y` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_pos_d` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `fs_bad_pos_e` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `fs_bad_pos_n` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `fs_bad_sideslip` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fs_bad_vel_d` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `fs_bad_vel_e` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `fs_bad_vel_n` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `innovation_fault_status_changes` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_airspeed` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_hagl` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_hor_pos` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_hor_vel` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_mag_x` | `bool` (F03, F04) | F03, F04 |
| `reject_mag_y` | `bool` (F03, F04) | F03, F04 |
| `reject_mag_z` | `bool` (F03, F04) | F03, F04 |
| `reject_optflow_x` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_optflow_y` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_sideslip` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_ver_pos` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_ver_vel` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `reject_yaw` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09) | F01, F03, F04, F05, F06, F07, F08, F09 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `event`

Observed in: F01, F03, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `arguments[0]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[10]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[11]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[12]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[13]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[14]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[15]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[16]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[17]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[18]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[19]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[1]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[20]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[21]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[22]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[23]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[24]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[2]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[3]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[4]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[5]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[6]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[7]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[8]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `arguments[9]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `event_sequence` | `uint16_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `id` | `uint32_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `log_levels` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |

## `failsafe_flags`

Observed in: F01, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `angular_velocity_invalid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `attitude_invalid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `auto_mission_missing` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `battery_low_remaining_time` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `battery_unhealthy` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `battery_warning` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `fd_alt_loss` | `bool` (F10, F11) | F10, F11 |
| `fd_critical_failure` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `fd_esc_arming_failure` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `fd_imbalanced_prop` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `fd_motor_failure` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `flight_time_limit_exceeded` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gcs_connection_lost` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `geofence_breached` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `global_position_invalid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `global_position_invalid_relaxed` | `bool` (F01, F07, F09, F10, F11) | F01, F07, F09, F10, F11 |
| `gnss_lost` | `bool` (F10, F11) | F10, F11 |
| `home_position_invalid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `local_altitude_invalid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `local_position_accuracy_low` | `bool` (F05, F06, F08) | F05, F06, F08 |
| `local_position_invalid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `local_position_invalid_relaxed` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `local_velocity_invalid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `manual_control_signal_lost` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mission_failure` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_angular_velocity` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_attitude` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_global_position` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_global_position_relaxed` | `uint32_t` (F01, F07, F09, F10, F11) | F01, F07, F09, F10, F11 |
| `mode_req_home_position` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_local_alt` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_local_position` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_local_position_relaxed` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_manual_control` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_mission` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_offboard_signal` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_other` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_prevent_arming` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `mode_req_wind_and_flight_time_compliance` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `navigator_failure` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `offboard_control_signal_lost` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `parachute_unhealthy` | `bool` (F10, F11) | F10, F11 |
| `position_accuracy_low` | `bool` (F01, F07, F09, F10, F11) | F01, F07, F09, F10, F11 |
| `primary_geofence_breached` | `bool` (F06) | F06 |
| `remote_id_unhealthy` | `bool` (F10, F11) | F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `vtol_fixed_wing_system_failure` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `wind_limit_exceeded` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |

## `failure_detector_status`

Observed in: F01, F03, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `fd_alt` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `fd_arm_escs` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `fd_battery` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `fd_ext` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `fd_high_wind` | `bool` (F03) | F03 |
| `fd_imbalanced_prop` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `fd_motor` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `fd_pitch` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `fd_roll` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `imbalanced_prop_metric` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `motor_failure_mask` | `uint16_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `motor_stop_mask` | `uint16_t` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |

## `fixed_wing_lateral_guidance_status`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `adapted_period` | `float` (F09) | F09 |
| `bearing_feas` | `float` (F09) | F09 |
| `bearing_feas_on_track` | `float` (F09) | F09 |
| `course_setpoint` | `float` (F09) | F09 |
| `lateral_acceleration_ff` | `float` (F09) | F09 |
| `signed_track_error` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |
| `track_error_bound` | `float` (F09) | F09 |
| `wind_est_valid` | `uint8_t` (F09) | F09 |

## `fixed_wing_lateral_setpoint`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `airspeed_direction` | `float` (F09) | F09 |
| `course` | `float` (F09) | F09 |
| `lateral_acceleration` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `fixed_wing_lateral_status`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `can_run_factor` | `float` (F09) | F09 |
| `lateral_acceleration_setpoint` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `fixed_wing_longitudinal_setpoint`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `altitude` | `float` (F09) | F09 |
| `equivalent_airspeed` | `float` (F09) | F09 |
| `height_rate` | `float` (F09) | F09 |
| `pitch_direct` | `float` (F09) | F09 |
| `throttle_direct` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `flaps_setpoint`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `normalized_setpoint` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `gps_dump`

Observed in: F07.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `data[0]` | `uint8_t` (F07) | F07 |
| `data[10]` | `uint8_t` (F07) | F07 |
| `data[11]` | `uint8_t` (F07) | F07 |
| `data[12]` | `uint8_t` (F07) | F07 |
| `data[13]` | `uint8_t` (F07) | F07 |
| `data[14]` | `uint8_t` (F07) | F07 |
| `data[15]` | `uint8_t` (F07) | F07 |
| `data[16]` | `uint8_t` (F07) | F07 |
| `data[17]` | `uint8_t` (F07) | F07 |
| `data[18]` | `uint8_t` (F07) | F07 |
| `data[19]` | `uint8_t` (F07) | F07 |
| `data[1]` | `uint8_t` (F07) | F07 |
| `data[20]` | `uint8_t` (F07) | F07 |
| `data[21]` | `uint8_t` (F07) | F07 |
| `data[22]` | `uint8_t` (F07) | F07 |
| `data[23]` | `uint8_t` (F07) | F07 |
| `data[24]` | `uint8_t` (F07) | F07 |
| `data[25]` | `uint8_t` (F07) | F07 |
| `data[26]` | `uint8_t` (F07) | F07 |
| `data[27]` | `uint8_t` (F07) | F07 |
| `data[28]` | `uint8_t` (F07) | F07 |
| `data[29]` | `uint8_t` (F07) | F07 |
| `data[2]` | `uint8_t` (F07) | F07 |
| `data[30]` | `uint8_t` (F07) | F07 |
| `data[31]` | `uint8_t` (F07) | F07 |
| `data[32]` | `uint8_t` (F07) | F07 |
| `data[33]` | `uint8_t` (F07) | F07 |
| `data[34]` | `uint8_t` (F07) | F07 |
| `data[35]` | `uint8_t` (F07) | F07 |
| `data[36]` | `uint8_t` (F07) | F07 |
| `data[37]` | `uint8_t` (F07) | F07 |
| `data[38]` | `uint8_t` (F07) | F07 |
| `data[39]` | `uint8_t` (F07) | F07 |
| `data[3]` | `uint8_t` (F07) | F07 |
| `data[40]` | `uint8_t` (F07) | F07 |
| `data[41]` | `uint8_t` (F07) | F07 |
| `data[42]` | `uint8_t` (F07) | F07 |
| `data[43]` | `uint8_t` (F07) | F07 |
| `data[44]` | `uint8_t` (F07) | F07 |
| `data[45]` | `uint8_t` (F07) | F07 |
| `data[46]` | `uint8_t` (F07) | F07 |
| `data[47]` | `uint8_t` (F07) | F07 |
| `data[48]` | `uint8_t` (F07) | F07 |
| `data[49]` | `uint8_t` (F07) | F07 |
| `data[4]` | `uint8_t` (F07) | F07 |
| `data[50]` | `uint8_t` (F07) | F07 |
| `data[51]` | `uint8_t` (F07) | F07 |
| `data[52]` | `uint8_t` (F07) | F07 |
| `data[53]` | `uint8_t` (F07) | F07 |
| `data[54]` | `uint8_t` (F07) | F07 |
| `data[55]` | `uint8_t` (F07) | F07 |
| `data[56]` | `uint8_t` (F07) | F07 |
| `data[57]` | `uint8_t` (F07) | F07 |
| `data[58]` | `uint8_t` (F07) | F07 |
| `data[59]` | `uint8_t` (F07) | F07 |
| `data[5]` | `uint8_t` (F07) | F07 |
| `data[60]` | `uint8_t` (F07) | F07 |
| `data[61]` | `uint8_t` (F07) | F07 |
| `data[62]` | `uint8_t` (F07) | F07 |
| `data[63]` | `uint8_t` (F07) | F07 |
| `data[64]` | `uint8_t` (F07) | F07 |
| `data[65]` | `uint8_t` (F07) | F07 |
| `data[66]` | `uint8_t` (F07) | F07 |
| `data[67]` | `uint8_t` (F07) | F07 |
| `data[68]` | `uint8_t` (F07) | F07 |
| `data[69]` | `uint8_t` (F07) | F07 |
| `data[6]` | `uint8_t` (F07) | F07 |
| `data[70]` | `uint8_t` (F07) | F07 |
| `data[71]` | `uint8_t` (F07) | F07 |
| `data[72]` | `uint8_t` (F07) | F07 |
| `data[73]` | `uint8_t` (F07) | F07 |
| `data[74]` | `uint8_t` (F07) | F07 |
| `data[75]` | `uint8_t` (F07) | F07 |
| `data[76]` | `uint8_t` (F07) | F07 |
| `data[77]` | `uint8_t` (F07) | F07 |
| `data[78]` | `uint8_t` (F07) | F07 |
| `data[7]` | `uint8_t` (F07) | F07 |
| `data[8]` | `uint8_t` (F07) | F07 |
| `data[9]` | `uint8_t` (F07) | F07 |
| `instance` | `uint8_t` (F07) | F07 |
| `len` | `uint8_t` (F07) | F07 |
| `timestamp` | `uint64_t` (F07) | F07 |

## `gripper`

Observed in: F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `command` | `int8_t` (F10, F11) | F10, F11 |
| `timestamp` | `uint64_t` (F10, F11) | F10, F11 |

## `home_position`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `lat` | `double` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `lon` | `double` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `manual_home` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pitch` | `float` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `roll` | `float` (F01, F07, F10, F11) | F01, F07, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `update_count` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `valid_alt` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `valid_hpos` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `valid_lpos` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `x` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `y` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `hover_thrust_estimate`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_innov` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `accel_innov_test_ratio` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `accel_innov_var` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `accel_noise_var` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `hover_thrust` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `hover_thrust_var` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `valid` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |

## `input_rc`

Observed in: F01, F02, F03, F05, F06, F07, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `channel_count` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `input_source` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `link_quality` | `int8_t` (F01, F05, F06, F07, F08, F09) | F01, F05, F06, F07, F08, F09 |
| `rc_failsafe` | `bool` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `rc_lost` | `bool` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `rc_lost_frame_count` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `rc_ppm_frame_length` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `rc_total_frame_count` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `rssi` | `int32_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `rssi_dbm` | `float` (F01, F05, F06, F07, F08, F09) | F01, F05, F06, F07, F08, F09 |
| `timestamp` | `uint64_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `timestamp_last_signal` | `uint64_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[0]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[10]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[11]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[12]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[13]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[14]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[15]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[16]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[17]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[1]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[2]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[3]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[4]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[5]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[6]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[7]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[8]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |
| `values[9]` | `uint16_t` (F01, F02, F03, F05, F06, F07, F08, F09) | F01, F02, F03, F05, F06, F07, F08, F09 |

## `landing_gear`

Observed in: F06, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `landing_gear` | `int8_t` (F06, F11) | F06, F11 |
| `timestamp` | `uint64_t` (F06, F11) | F06, F11 |

## `landing_gear_wheel`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `normalized_wheel_setpoint` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `lateral_control_configuration`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `lateral_accel_max` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `logger_status`

Observed in: F02, F04, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `backend` | `uint8_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `buffer_size_bytes` | `uint32_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `buffer_used_bytes` | `uint32_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `dropouts` | `uint32_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `is_logging` | `bool` (F10, F11) | F10, F11 |
| `message_gaps` | `uint32_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `num_messages` | `uint8_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `timestamp` | `uint64_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `total_written_kb` | `float` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `type` | `uint8_t` (F02, F04, F10, F11) | F02, F04, F10, F11 |
| `write_rate_kb_s` | `float` (F02, F04, F10, F11) | F02, F04, F10, F11 |

## `longitudinal_control_configuration`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `climb_rate_target` | `float` (F09) | F09 |
| `disable_underspeed_protection` | `bool` (F09) | F09 |
| `enforce_low_height_condition` | `bool` (F09) | F09 |
| `pitch_max` | `float` (F09) | F09 |
| `pitch_min` | `float` (F09) | F09 |
| `sink_rate_target` | `float` (F09) | F09 |
| `speed_weight` | `float` (F09) | F09 |
| `throttle_max` | `float` (F09) | F09 |
| `throttle_min` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `magnetometer_bias_estimate`

Observed in: F01, F03, F05, F06, F07, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `bias_x[0]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_x[1]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_x[2]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_x[3]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_y[0]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_y[1]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_y[2]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_y[3]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_z[0]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_z[1]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_z[2]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `bias_z[3]` | `float` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `stable[0]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `stable[1]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `stable[2]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `stable[3]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `timestamp` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `valid[0]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `valid[1]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `valid[2]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `valid[3]` | `bool` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |

## `manual_control_setpoint`

Observed in: F01, F02, F03, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `acro_switch` | `uint8_t` (F02) | F02 |
| `arm_switch` | `uint8_t` (F02) | F02 |
| `aux1` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `aux2` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `aux3` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `aux4` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `aux5` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `aux6` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `buttons` | `uint16_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `data_source` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `flaps` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gear_switch` | `uint8_t` (F02) | F02 |
| `kill_switch` | `uint8_t` (F02) | F02 |
| `loiter_switch` | `uint8_t` (F02) | F02 |
| `man_switch` | `uint8_t` (F02) | F02 |
| `mode_slot` | `uint8_t` (F02) | F02 |
| `mode_switch` | `uint8_t` (F02) | F02 |
| `offboard_switch` | `uint8_t` (F02) | F02 |
| `pitch` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `posctl_switch` | `uint8_t` (F02) | F02 |
| `r` | `float` (F02, F03) | F02, F03 |
| `rattitude_switch` | `uint8_t` (F02) | F02 |
| `return_switch` | `uint8_t` (F02) | F02 |
| `roll` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `stab_switch` | `uint8_t` (F02) | F02 |
| `sticks_moving` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `throttle` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `transition_switch` | `uint8_t` (F02) | F02 |
| `valid` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `x` | `float` (F02, F03) | F02, F03 |
| `y` | `float` (F02, F03) | F02, F03 |
| `yaw` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `z` | `float` (F02, F03) | F02, F03 |

## `manual_control_switches`

Observed in: F01, F03, F05, F06, F07, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `arm_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `engage_main_motor_switch` | `uint8_t` (F01, F05, F06, F07, F08, F09) | F01, F05, F06, F07, F08, F09 |
| `gear_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `kill_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `loiter_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `mode_slot` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `offboard_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `payload_power_switch` | `uint8_t` (F01, F05, F07, F08, F09) | F01, F05, F07, F08, F09 |
| `photo_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `return_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `switch_changes` | `uint32_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `termination_switch` | `uint8_t` (F01, F07) | F01, F07 |
| `timestamp` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `timestamp_sample` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `transition_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |
| `video_switch` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09) | F01, F03, F05, F06, F07, F08, F09 |

## `mission`

Observed in: F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `count` | `uint16_t` (F04) | F04 |
| `current_seq` | `int32_t` (F04) | F04 |
| `dataman_id` | `uint8_t` (F04) | F04 |
| `timestamp` | `uint64_t` (F04) | F04 |

## `mission_result`

Observed in: F03, F04, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `execution_mode` | `uint8_t` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `failure` | `bool` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `finished` | `bool` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `flight_termination` | `bool` (F03, F04) | F03, F04 |
| `geofence_id` | `uint32_t` (F07, F08, F09, F10, F11) | F07, F08, F09, F10, F11 |
| `home_position_counter` | `uint32_t` (F07, F08, F09, F10, F11) | F07, F08, F09, F10, F11 |
| `instance_count` | `uint32_t` (F03, F04, F06) | F03, F04, F06 |
| `item_changed_index` | `uint16_t` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `item_do_jump_changed` | `bool` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `item_do_jump_remaining` | `uint16_t` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `mission_id` | `uint32_t` (F07, F08, F09, F10, F11) | F07, F08, F09, F10, F11 |
| `seq_current` | `uint16_t` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `seq_reached` | `int32_t` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `seq_total` | `uint16_t` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `stay_in_failsafe` | `bool` (F03, F04) | F03, F04 |
| `timestamp` | `uint64_t` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `valid` | `bool` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |
| `warning` | `bool` (F03, F04, F06, F07, F08, F09, F10, F11) | F03, F04, F06, F07, F08, F09, F10, F11 |

## `multirotor_motor_limits`

Observed in: F02, F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `saturation_status` | `uint16_t` (F02, F04) | F02, F04 |
| `timestamp` | `uint64_t` (F02, F04) | F02, F04 |

## `navigator_mission_item`

Observed in: F04, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `acceptance_radius` | `float` (F04, F09) | F04, F09 |
| `altitude` | `float` (F04, F09) | F04, F09 |
| `altitude_is_relative` | `bool` (F04, F09) | F04, F09 |
| `autocontinue` | `bool` (F04, F09) | F04, F09 |
| `force_heading` | `bool` (F04, F09) | F04, F09 |
| `frame` | `uint8_t` (F04, F09) | F04, F09 |
| `instance_count` | `uint32_t` (F04) | F04 |
| `latitude` | `float` (F04, F09) | F04, F09 |
| `loiter_exit_xtrack` | `bool` (F04, F09) | F04, F09 |
| `loiter_radius` | `float` (F04, F09) | F04, F09 |
| `longitude` | `float` (F04, F09) | F04, F09 |
| `nav_cmd` | `uint16_t` (F04, F09) | F04, F09 |
| `origin` | `uint8_t` (F04, F09) | F04, F09 |
| `sequence_current` | `uint16_t` (F04, F09) | F04, F09 |
| `time_inside` | `float` (F04, F09) | F04, F09 |
| `timestamp` | `uint64_t` (F04, F09) | F04, F09 |
| `vtol_back_transition` | `bool` (F04, F09) | F04, F09 |
| `yaw` | `float` (F04, F09) | F04, F09 |

## `navigator_status`

Observed in: F01, F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `failure` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `nav_state` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |

## `offboard_control_mode`

Observed in: F01, F03, F04, F06.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `acceleration` | `bool` (F01, F03, F04, F06) | F01, F03, F04, F06 |
| `actuator` | `bool` (F03, F06) | F03, F06 |
| `attitude` | `bool` (F01, F03, F04, F06) | F01, F03, F04, F06 |
| `body_rate` | `bool` (F01, F03, F04, F06) | F01, F03, F04, F06 |
| `direct_actuator` | `bool` (F01) | F01 |
| `position` | `bool` (F01, F03, F04, F06) | F01, F03, F04, F06 |
| `thrust_and_torque` | `bool` (F01) | F01 |
| `timestamp` | `uint64_t` (F01, F03, F04, F06) | F01, F03, F04, F06 |
| `velocity` | `bool` (F01, F03, F04, F06) | F01, F03, F04, F06 |

## `optical_flow`

Observed in: F03.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `frame_count_since_last_readout` | `uint16_t` (F03) | F03 |
| `ground_distance_m` | `float` (F03) | F03 |
| `gyro_temperature` | `int16_t` (F03) | F03 |
| `gyro_x_rate_integral` | `float` (F03) | F03 |
| `gyro_y_rate_integral` | `float` (F03) | F03 |
| `gyro_z_rate_integral` | `float` (F03) | F03 |
| `integration_timespan` | `uint32_t` (F03) | F03 |
| `max_flow_rate` | `float` (F03) | F03 |
| `max_ground_distance` | `float` (F03) | F03 |
| `min_ground_distance` | `float` (F03) | F03 |
| `mode` | `uint8_t` (F03) | F03 |
| `pixel_flow_x_integral` | `float` (F03) | F03 |
| `pixel_flow_y_integral` | `float` (F03) | F03 |
| `quality` | `uint8_t` (F03) | F03 |
| `sensor_id` | `uint8_t` (F03) | F03 |
| `time_since_last_sonar_update` | `uint32_t` (F03) | F03 |
| `timestamp` | `uint64_t` (F03) | F03 |

## `parameter_update`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `active` | `uint16_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `changed` | `uint16_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `custom_default` | `uint16_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `export_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `find_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `get_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `instance` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `set_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `position_controller_status`

Observed in: F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `acceptance_radius` | `float` (F04) | F04 |
| `altitude_acceptance` | `float` (F04) | F04 |
| `nav_bearing` | `float` (F04) | F04 |
| `nav_pitch` | `float` (F04) | F04 |
| `nav_roll` | `float` (F04) | F04 |
| `target_bearing` | `float` (F04) | F04 |
| `timestamp` | `uint64_t` (F04) | F04 |
| `type` | `uint8_t` (F04) | F04 |
| `wp_dist` | `float` (F04) | F04 |
| `xtrack_error` | `float` (F04) | F04 |
| `yaw_acceptance` | `float` (F04) | F04 |

## `position_setpoint_triplet`

Observed in: F01, F02, F03, F04, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `current._padding0[0]` | `uint8_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current._padding0[1]` | `uint8_t` (F01, F02, F03, F04, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F07, F08, F09, F10, F11 |
| `current._padding0[2]` | `uint8_t` (F01, F02, F03, F04, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F07, F08, F09, F10, F11 |
| `current._padding0[3]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `current._padding0[4]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `current._padding0[5]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `current._padding0[6]` | `uint8_t` (F02, F10, F11) | F02, F10, F11 |
| `current.a_x` | `float` (F02) | F02 |
| `current.a_y` | `float` (F02) | F02 |
| `current.a_z` | `float` (F02) | F02 |
| `current.acceleration_is_force` | `bool` (F02) | F02 |
| `current.acceleration_valid` | `bool` (F02) | F02 |
| `current.acceptance_radius` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.alt` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.alt_acceptance_radius` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `current.alt_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `current.course` | `float` (F10, F11) | F10, F11 |
| `current.cruising_speed` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.cruising_throttle` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.disable_weather_vane` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `current.gliding_enabled` | `bool` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `current.landing_gear` | `int8_t` (F02, F03, F04) | F02, F03, F04 |
| `current.lat` | `double` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.loiter_direction` | `int8_t` (F02, F03, F04) | F02, F03, F04 |
| `current.loiter_direction_counter_clockwise` | `bool` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `current.loiter_minor_radius` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `current.loiter_orientation` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `current.loiter_pattern` | `uint8_t` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `current.loiter_radius` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.lon` | `double` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.pitch_min` | `float` (F02) | F02 |
| `current.position_valid` | `bool` (F02) | F02 |
| `current.timestamp` | `uint64_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.type` | `uint8_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.valid` | `bool` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.velocity_frame` | `uint8_t` (F02, F03, F04) | F02, F03, F04 |
| `current.velocity_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `current.vx` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.vy` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.vz` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.x` | `float` (F02) | F02 |
| `current.y` | `float` (F02) | F02 |
| `current.yaw` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `current.yaw_valid` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `current.yawspeed` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `current.yawspeed_valid` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `current.z` | `float` (F02) | F02 |
| `next._padding0[0]` | `uint8_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next._padding0[1]` | `uint8_t` (F01, F02, F03, F04, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F07, F08, F09, F10, F11 |
| `next._padding0[2]` | `uint8_t` (F01, F02, F03, F04, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F07, F08, F09, F10, F11 |
| `next._padding0[3]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `next._padding0[4]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `next._padding0[5]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `next._padding0[6]` | `uint8_t` (F02, F10, F11) | F02, F10, F11 |
| `next.a_x` | `float` (F02) | F02 |
| `next.a_y` | `float` (F02) | F02 |
| `next.a_z` | `float` (F02) | F02 |
| `next.acceleration_is_force` | `bool` (F02) | F02 |
| `next.acceleration_valid` | `bool` (F02) | F02 |
| `next.acceptance_radius` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.alt` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.alt_acceptance_radius` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `next.alt_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `next.course` | `float` (F10, F11) | F10, F11 |
| `next.cruising_speed` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.cruising_throttle` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.disable_weather_vane` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `next.gliding_enabled` | `bool` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `next.landing_gear` | `int8_t` (F02, F03, F04) | F02, F03, F04 |
| `next.lat` | `double` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.loiter_direction` | `int8_t` (F02, F03, F04) | F02, F03, F04 |
| `next.loiter_direction_counter_clockwise` | `bool` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `next.loiter_minor_radius` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `next.loiter_orientation` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `next.loiter_pattern` | `uint8_t` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `next.loiter_radius` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.lon` | `double` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.pitch_min` | `float` (F02) | F02 |
| `next.position_valid` | `bool` (F02) | F02 |
| `next.timestamp` | `uint64_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.type` | `uint8_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.valid` | `bool` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.velocity_frame` | `uint8_t` (F02, F03, F04) | F02, F03, F04 |
| `next.velocity_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `next.vx` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.vy` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.vz` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.x` | `float` (F02) | F02 |
| `next.y` | `float` (F02) | F02 |
| `next.yaw` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `next.yaw_valid` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `next.yawspeed` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `next.yawspeed_valid` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `next.z` | `float` (F02) | F02 |
| `previous._padding0[0]` | `uint8_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous._padding0[1]` | `uint8_t` (F01, F02, F03, F04, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F07, F08, F09, F10, F11 |
| `previous._padding0[2]` | `uint8_t` (F01, F02, F03, F04, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F07, F08, F09, F10, F11 |
| `previous._padding0[3]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `previous._padding0[4]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `previous._padding0[5]` | `uint8_t` (F02, F03, F04, F10, F11) | F02, F03, F04, F10, F11 |
| `previous._padding0[6]` | `uint8_t` (F02, F10, F11) | F02, F10, F11 |
| `previous.a_x` | `float` (F02) | F02 |
| `previous.a_y` | `float` (F02) | F02 |
| `previous.a_z` | `float` (F02) | F02 |
| `previous.acceleration_is_force` | `bool` (F02) | F02 |
| `previous.acceleration_valid` | `bool` (F02) | F02 |
| `previous.acceptance_radius` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.alt` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.alt_acceptance_radius` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `previous.alt_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `previous.course` | `float` (F10, F11) | F10, F11 |
| `previous.cruising_speed` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.cruising_throttle` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.disable_weather_vane` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `previous.gliding_enabled` | `bool` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `previous.landing_gear` | `int8_t` (F02, F03, F04) | F02, F03, F04 |
| `previous.lat` | `double` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.loiter_direction` | `int8_t` (F02, F03, F04) | F02, F03, F04 |
| `previous.loiter_direction_counter_clockwise` | `bool` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `previous.loiter_minor_radius` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `previous.loiter_orientation` | `float` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `previous.loiter_pattern` | `uint8_t` (F01, F07, F08, F09, F10, F11) | F01, F07, F08, F09, F10, F11 |
| `previous.loiter_radius` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.lon` | `double` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.pitch_min` | `float` (F02) | F02 |
| `previous.position_valid` | `bool` (F02) | F02 |
| `previous.timestamp` | `uint64_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.type` | `uint8_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.valid` | `bool` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.velocity_frame` | `uint8_t` (F02, F03, F04) | F02, F03, F04 |
| `previous.velocity_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `previous.vx` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.vy` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.vz` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.x` | `float` (F02) | F02 |
| `previous.y` | `float` (F02) | F02 |
| `previous.yaw` | `float` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `previous.yaw_valid` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `previous.yawspeed` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `previous.yawspeed_valid` | `bool` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `previous.z` | `float` (F02) | F02 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |

## `px4io_status`

Observed in: F01, F02, F07, F08, F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `actuators[0]` | `int16_t` (F02) | F02 |
| `actuators[1]` | `int16_t` (F02) | F02 |
| `actuators[2]` | `int16_t` (F02) | F02 |
| `actuators[3]` | `int16_t` (F02) | F02 |
| `actuators[4]` | `int16_t` (F02) | F02 |
| `actuators[5]` | `int16_t` (F02) | F02 |
| `actuators[6]` | `int16_t` (F02) | F02 |
| `actuators[7]` | `int16_t` (F02) | F02 |
| `alarm_acc_current` | `bool` (F02) | F02 |
| `alarm_fmu_lost` | `bool` (F02) | F02 |
| `alarm_pwm_error` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `alarm_rc_lost` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `alarm_servo_current` | `bool` (F02) | F02 |
| `alarm_temperature` | `bool` (F02) | F02 |
| `alarm_vbatt_low` | `bool` (F02) | F02 |
| `alarm_vservo_fault` | `bool` (F02) | F02 |
| `arming_always_pwm_enable` | `bool` (F02) | F02 |
| `arming_failsafe_custom` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `arming_fmu_armed` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `arming_fmu_prearmed` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `arming_force_failsafe` | `bool` (F02, F08, F09) | F02, F08, F09 |
| `arming_inair_restart_ok` | `bool` (F02) | F02 |
| `arming_io_arm_ok` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `arming_lockdown` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `arming_manual_override_ok` | `bool` (F02) | F02 |
| `arming_override_immediate` | `bool` (F02) | F02 |
| `arming_rc_handling_disabled` | `bool` (F02) | F02 |
| `arming_termination` | `bool` (F01, F07) | F01, F07 |
| `arming_termination_failsafe` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `free_memory_bytes` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `pwm[0]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm[1]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm[2]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm[3]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm[4]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm[5]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm[6]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm[7]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[0]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[1]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[2]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[3]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[4]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[5]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[6]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_disarmed[7]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[0]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[1]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[2]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[3]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[4]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[5]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[6]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_failsafe[7]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[0]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[1]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[2]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[3]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[4]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[5]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[6]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `pwm_rate_hz[7]` | `uint16_t` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `raw_inputs[0]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[10]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[11]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[12]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[13]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[14]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[15]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[16]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[17]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[1]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[2]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[3]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[4]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[5]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[6]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[7]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[8]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `raw_inputs[9]` | `uint16_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `rssi_v` | `float` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `servos[0]` | `uint16_t` (F02) | F02 |
| `servos[1]` | `uint16_t` (F02) | F02 |
| `servos[2]` | `uint16_t` (F02) | F02 |
| `servos[3]` | `uint16_t` (F02) | F02 |
| `servos[4]` | `uint16_t` (F02) | F02 |
| `servos[5]` | `uint16_t` (F02) | F02 |
| `servos[6]` | `uint16_t` (F02) | F02 |
| `servos[7]` | `uint16_t` (F02) | F02 |
| `status_arm_sync` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_failsafe` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_fmu_initialized` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_fmu_ok` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_init_ok` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_mixer_ok` | `bool` (F02) | F02 |
| `status_outputs_armed` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_override` | `bool` (F02) | F02 |
| `status_raw_pwm` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_rc_dsm` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_rc_ok` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_rc_ppm` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_rc_sbus` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_rc_st24` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_rc_sumd` | `bool` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `status_safety_button_event` | `bool` (F01, F07, F08, F09) | F01, F07, F08, F09 |
| `status_safety_off` | `bool` (F02) | F02 |
| `timestamp` | `uint64_t` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |
| `voltage_v` | `float` (F01, F02, F07, F08, F09) | F01, F02, F07, F08, F09 |

## `radio_status`

Observed in: F07, F08.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `fix` | `uint16_t` (F07, F08) | F07, F08 |
| `noise` | `uint8_t` (F07, F08) | F07, F08 |
| `remote_noise` | `uint8_t` (F07, F08) | F07, F08 |
| `remote_rssi` | `uint8_t` (F07, F08) | F07, F08 |
| `rssi` | `uint8_t` (F07, F08) | F07, F08 |
| `rxerrors` | `uint16_t` (F07, F08) | F07, F08 |
| `timestamp` | `uint64_t` (F07, F08) | F07, F08 |
| `txbuf` | `uint8_t` (F07, F08) | F07, F08 |

## `ranging_beacon`

Observed in: F10.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt` | `float` (F10) | F10 |
| `alt_type` | `uint8_t` (F10) | F10 |
| `beacon_id` | `uint8_t` (F10) | F10 |
| `carrier_freq` | `uint16_t` (F10) | F10 |
| `hacc` | `float` (F10) | F10 |
| `lat` | `double` (F10) | F10 |
| `lon` | `double` (F10) | F10 |
| `range` | `float` (F10) | F10 |
| `range_accuracy` | `float` (F10) | F10 |
| `sequence_nr` | `uint8_t` (F10) | F10 |
| `status` | `uint8_t` (F10) | F10 |
| `timestamp` | `uint64_t` (F10) | F10 |
| `timestamp_sample` | `uint64_t` (F10) | F10 |
| `vacc` | `float` (F10) | F10 |

## `rate_ctrl_status`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `additional_integ1` | `float` (F02, F03, F04) | F02, F03, F04 |
| `pitchspeed_integ` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rollspeed_integ` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `wheel_rate_integ` | `float` (F05, F06, F08) | F05, F06, F08 |
| `yawspeed_integ` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `rtl_flight_time`

Observed in: F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `rtl_limit_fraction` | `float` (F04) | F04 |
| `rtl_time_s` | `float` (F04) | F04 |
| `timestamp` | `uint64_t` (F04) | F04 |

## `rtl_status`

Observed in: F01, F05, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `has_vtol_approach` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `is_evaluation_pending` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `rtl_type` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `safe_point_index` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `safe_points_id` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |

## `rtl_time_estimate`

Observed in: F01, F03, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `safe_time_estimate` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `time_estimate` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `valid` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |

## `safety`

Observed in: F02, F03.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `override_available` | `bool` (F02) | F02 |
| `override_enabled` | `bool` (F02) | F02 |
| `safety_off` | `bool` (F02, F03) | F02, F03 |
| `safety_switch_available` | `bool` (F02, F03) | F02, F03 |
| `timestamp` | `uint64_t` (F02, F03) | F02, F03 |

## `sensor_accel`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `clip_counter[0]` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `clip_counter[1]` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `clip_counter[2]` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `error_count` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `samples` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `temperature` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `x` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `y` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `sensor_baro`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `error_count` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `pressure` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `temperature` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `sensor_combined`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_calibration_count` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `accelerometer_clipping` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accelerometer_integral_dt` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accelerometer_m_s2[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accelerometer_m_s2[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accelerometer_m_s2[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accelerometer_timestamp_relative` | `int32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_calibration_count` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_clipping` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_integral_dt` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_rad[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_rad[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_rad[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `sensor_gps`

Observed in: F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `alt_ellipsoid` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `altitude_ellipsoid_m` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `altitude_msl_m` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `antenna_offset_x` | `float` (F10, F11) | F10, F11 |
| `antenna_offset_y` | `float` (F10, F11) | F10, F11 |
| `antenna_offset_z` | `float` (F10, F11) | F10, F11 |
| `authentication_state` | `uint8_t` (F07, F10, F11) | F07, F10, F11 |
| `automatic_gain_control` | `uint16_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `c_variance_rad` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cog_rad` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `device_id` | `uint32_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `eph` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `epv` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fix_type` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hdop` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heading` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heading_accuracy` | `float` (F03, F05, F06, F07, F08, F09, F10, F11) | F03, F05, F06, F07, F08, F09, F10, F11 |
| `heading_offset` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `jamming_indicator` | `int32_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `jamming_state` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `lat` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `latitude_deg` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `lon` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `longitude_deg` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `noise_per_ms` | `int32_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rtcm_crc_failed` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `rtcm_injection_rate` | `float` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `rtcm_msg_used` | `uint8_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `s_variance_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `satellites_used` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `selected_rtcm_instance` | `uint8_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `spoofing_state` | `uint8_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `system_error` | `uint32_t` (F07, F10, F11) | F07, F10, F11 |
| `time_utc_usec` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_time_relative` | `int32_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vdop` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_d_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_e_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_n_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_ned_valid` | `bool` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `sensor_gyro`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `clip_counter[0]` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `clip_counter[1]` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `clip_counter[2]` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `error_count` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `samples` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `temperature` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `x` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `y` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `sensor_gyro_fft`

Observed in: F03, F10.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F03, F10) | F03, F10 |
| `peak_frequencies_x[0]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_x[1]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_x[2]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_y[0]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_y[1]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_y[2]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_z[0]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_z[1]` | `float` (F03, F10) | F03, F10 |
| `peak_frequencies_z[2]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_x[0]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_x[1]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_x[2]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_y[0]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_y[1]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_y[2]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_z[0]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_z[1]` | `float` (F03, F10) | F03, F10 |
| `peak_snr_z[2]` | `float` (F03, F10) | F03, F10 |
| `resolution_hz` | `float` (F03, F10) | F03, F10 |
| `sensor_sample_rate_hz` | `float` (F03, F10) | F03, F10 |
| `timestamp` | `uint64_t` (F03, F10) | F03, F10 |
| `timestamp_sample` | `uint64_t` (F03, F10) | F03, F10 |

## `sensor_mag`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `error_count` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `is_external` | `bool` (F02, F04) | F02, F04 |
| `temperature` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `x` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `y` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `sensor_preflight`

Observed in: F02.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_inconsistency_m_s_s` | `float` (F02) | F02 |
| `gyro_inconsistency_rad_s` | `float` (F02) | F02 |
| `mag_inconsistency_angle` | `float` (F02) | F02 |
| `timestamp` | `uint64_t` (F02) | F02 |

## `sensor_preflight_mag`

Observed in: F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `mag_inconsistency_angle` | `float` (F04) | F04 |
| `timestamp` | `uint64_t` (F04) | F04 |

## `sensor_selection`

Observed in: F01, F02, F03, F04, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_device_id` | `uint32_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `gyro_device_id` | `uint32_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |
| `mag_device_id` | `uint32_t` (F02) | F02 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F06, F07, F08, F09, F10, F11 |

## `sensors_status_imu`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_device_id_primary` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_device_ids[0]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_device_ids[1]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_device_ids[2]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_device_ids[3]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_healthy[0]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_healthy[1]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_healthy[2]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_healthy[3]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_inconsistency_m_s_s[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_inconsistency_m_s_s[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_inconsistency_m_s_s[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_inconsistency_m_s_s[3]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_priority[0]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `accel_priority[1]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `accel_priority[2]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `accel_priority[3]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_id_primary` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_ids[0]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_ids[1]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_ids[2]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_ids[3]` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_healthy[0]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_healthy[1]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_healthy[2]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_healthy[3]` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_inconsistency_rad_s[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_inconsistency_rad_s[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_inconsistency_rad_s[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_inconsistency_rad_s[3]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_priority[0]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_priority[1]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_priority[2]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_priority[3]` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `spoilers_setpoint`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `normalized_setpoint` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |

## `system_power`

Observed in: F01, F02, F03, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `brick_valid` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `can1_gps1_5v_valid` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `comp_5v_valid` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `hipower_5v_oc` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `payload_v_valid` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `periph_5v_oc` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `sensors3v3[0]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `sensors3v3[1]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `sensors3v3[2]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `sensors3v3[3]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `sensors3v3_valid` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `servo_valid` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `usb_connected` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `usb_valid` | `uint8_t` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `v3v3_valid` | `uint8_t` (F02) | F02 |
| `voltage3v3_v` | `float` (F02) | F02 |
| `voltage5v_v` | `float` (F01, F02, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F05, F06, F07, F08, F09, F10, F11 |
| `voltage_payload_v` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |

## `takeoff_status`

Observed in: F01, F03, F04, F05, F06, F07, F08, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `takeoff_state` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F10, F11 |
| `tilt_limit` | `float` (F01, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F10, F11 |

## `tecs_status`

Observed in: F09.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `altitude_reference` | `float` (F09) | F09 |
| `altitude_sp` | `float` (F09) | F09 |
| `altitude_time_constant` | `float` (F09) | F09 |
| `equivalent_airspeed_sp` | `float` (F09) | F09 |
| `fast_descend_ratio` | `float` (F09) | F09 |
| `height_rate` | `float` (F09) | F09 |
| `height_rate_direct` | `float` (F09) | F09 |
| `height_rate_reference` | `float` (F09) | F09 |
| `height_rate_setpoint` | `float` (F09) | F09 |
| `pitch_integ` | `float` (F09) | F09 |
| `pitch_sp_rad` | `float` (F09) | F09 |
| `throttle_integ` | `float` (F09) | F09 |
| `throttle_sp` | `float` (F09) | F09 |
| `throttle_trim` | `float` (F09) | F09 |
| `timestamp` | `uint64_t` (F09) | F09 |
| `total_energy_balance_rate` | `float` (F09) | F09 |
| `total_energy_balance_rate_sp` | `float` (F09) | F09 |
| `total_energy_rate` | `float` (F09) | F09 |
| `total_energy_rate_sp` | `float` (F09) | F09 |
| `true_airspeed_derivative` | `float` (F09) | F09 |
| `true_airspeed_derivative_raw` | `float` (F09) | F09 |
| `true_airspeed_derivative_sp` | `float` (F09) | F09 |
| `true_airspeed_filtered` | `float` (F09) | F09 |
| `true_airspeed_sp` | `float` (F09) | F09 |
| `underspeed_ratio` | `float` (F09) | F09 |

## `telemetry_status`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `avoidance_system_healthy` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `data_rate` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flow_control` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `forwarding` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ftp` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_component_log` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_component_obstacle_avoidance` | `bool` (F03, F04, F06) | F03, F04, F06 |
| `heartbeat_component_osd` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_component_pairing_manager` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_component_telemetry_radio` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_component_uart_bridge` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_component_udp_bridge` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_component_vio` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_adsb` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_antenna_tracker` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_camera` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_flarm` | `bool` (F10, F11) | F10, F11 |
| `heartbeat_type_gcs` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_gimbal` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_onboard_controller` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_open_drone_id` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeat_type_parachute` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `heartbeats[0]._padding0[0]` | `uint8_t` (F02) | F02 |
| `heartbeats[0]._padding0[1]` | `uint8_t` (F02) | F02 |
| `heartbeats[0]._padding0[2]` | `uint8_t` (F02) | F02 |
| `heartbeats[0]._padding0[3]` | `uint8_t` (F02) | F02 |
| `heartbeats[0].component_id` | `uint8_t` (F02) | F02 |
| `heartbeats[0].state` | `uint8_t` (F02) | F02 |
| `heartbeats[0].system_id` | `uint8_t` (F02) | F02 |
| `heartbeats[0].timestamp` | `uint64_t` (F02) | F02 |
| `heartbeats[0].type` | `uint8_t` (F02) | F02 |
| `heartbeats[1]._padding0[0]` | `uint8_t` (F02) | F02 |
| `heartbeats[1]._padding0[1]` | `uint8_t` (F02) | F02 |
| `heartbeats[1]._padding0[2]` | `uint8_t` (F02) | F02 |
| `heartbeats[1]._padding0[3]` | `uint8_t` (F02) | F02 |
| `heartbeats[1].component_id` | `uint8_t` (F02) | F02 |
| `heartbeats[1].state` | `uint8_t` (F02) | F02 |
| `heartbeats[1].system_id` | `uint8_t` (F02) | F02 |
| `heartbeats[1].timestamp` | `uint64_t` (F02) | F02 |
| `heartbeats[1].type` | `uint8_t` (F02) | F02 |
| `heartbeats[2]._padding0[0]` | `uint8_t` (F02) | F02 |
| `heartbeats[2]._padding0[1]` | `uint8_t` (F02) | F02 |
| `heartbeats[2]._padding0[2]` | `uint8_t` (F02) | F02 |
| `heartbeats[2]._padding0[3]` | `uint8_t` (F02) | F02 |
| `heartbeats[2].component_id` | `uint8_t` (F02) | F02 |
| `heartbeats[2].state` | `uint8_t` (F02) | F02 |
| `heartbeats[2].system_id` | `uint8_t` (F02) | F02 |
| `heartbeats[2].timestamp` | `uint64_t` (F02) | F02 |
| `heartbeats[2].type` | `uint8_t` (F02) | F02 |
| `heartbeats[3]._padding0[0]` | `uint8_t` (F02) | F02 |
| `heartbeats[3]._padding0[1]` | `uint8_t` (F02) | F02 |
| `heartbeats[3]._padding0[2]` | `uint8_t` (F02) | F02 |
| `heartbeats[3]._padding0[3]` | `uint8_t` (F02) | F02 |
| `heartbeats[3].component_id` | `uint8_t` (F02) | F02 |
| `heartbeats[3].state` | `uint8_t` (F02) | F02 |
| `heartbeats[3].system_id` | `uint8_t` (F02) | F02 |
| `heartbeats[3].timestamp` | `uint64_t` (F02) | F02 |
| `heartbeats[3].type` | `uint8_t` (F02) | F02 |
| `mavlink_v2` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mode` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `open_drone_id_system_healthy` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `parachute_system_healthy` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `rate_multiplier` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rate_rx` | `float` (F02) | F02 |
| `rate_tx` | `float` (F02) | F02 |
| `rate_txerr` | `float` (F02) | F02 |
| `rx_buffer_overruns` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rx_message_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rx_message_lost_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rx_message_lost_rate` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rx_packet_drop_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rx_parse_errors` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rx_rate_avg` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `streams` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `tx_buffer_overruns` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `tx_error_rate_avg` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `tx_message_count` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `tx_rate_avg` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `type` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `test_motor`

Observed in: F02, F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `action` | `uint8_t` (F02, F04) | F02, F04 |
| `driver_instance` | `uint8_t` (F02, F04) | F02, F04 |
| `motor_number` | `uint32_t` (F02, F04) | F02, F04 |
| `timeout_ms` | `uint32_t` (F02, F04) | F02, F04 |
| `timestamp` | `uint64_t` (F02, F04) | F02, F04 |
| `value` | `float` (F02, F04) | F02, F04 |

## `timesync_status`

Observed in: F01.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `estimated_offset` | `int64_t` (F01) | F01 |
| `observed_offset` | `int64_t` (F01) | F01 |
| `remote_timestamp` | `uint64_t` (F01) | F01 |
| `round_trip_time` | `uint32_t` (F01) | F01 |
| `source_protocol` | `uint8_t` (F01) | F01 |
| `timestamp` | `uint64_t` (F01) | F01 |

## `trajectory_setpoint`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `acceleration[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `acceleration[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `acceleration[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `jerk[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `jerk[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `jerk[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `position[0]` | `float` (F01, F05, F06, F07, F08, F10, F11) | F01, F05, F06, F07, F08, F10, F11 |
| `position[1]` | `float` (F01, F05, F06, F07, F08, F10, F11) | F01, F05, F06, F07, F08, F10, F11 |
| `position[2]` | `float` (F01, F05, F06, F07, F08, F10, F11) | F01, F05, F06, F07, F08, F10, F11 |
| `thrust[0]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `thrust[1]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `thrust[2]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `velocity[0]` | `float` (F01, F05, F06, F07, F08, F10, F11) | F01, F05, F06, F07, F08, F10, F11 |
| `velocity[1]` | `float` (F01, F05, F06, F07, F08, F10, F11) | F01, F05, F06, F07, F08, F10, F11 |
| `velocity[2]` | `float` (F01, F05, F06, F07, F08, F10, F11) | F01, F05, F06, F07, F08, F10, F11 |
| `vx` | `float` (F02, F03, F04) | F02, F03, F04 |
| `vy` | `float` (F02, F03, F04) | F02, F03, F04 |
| `vz` | `float` (F02, F03, F04) | F02, F03, F04 |
| `x` | `float` (F02, F03, F04) | F02, F03, F04 |
| `y` | `float` (F02, F03, F04) | F02, F03, F04 |
| `yaw` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `yawspeed` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F10, F11 |
| `z` | `float` (F02, F03, F04) | F02, F03, F04 |

## `transponder_report`

Observed in: F01, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `altitude` | `float` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `altitude_type` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[0]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[1]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[2]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[3]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[4]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[5]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[6]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[7]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `callsign[8]` | `char` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `emitter_type` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `flags` | `uint16_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `heading` | `float` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `hor_velocity` | `float` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `icao_address` | `uint32_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `lat` | `double` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `lon` | `double` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `squawk` | `uint16_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `tslc` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[0]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[10]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[11]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[12]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[13]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[14]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[15]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[16]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[17]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[1]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[2]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[3]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[4]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[5]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[6]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[7]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[8]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `uas_id[9]` | `uint8_t` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |
| `ver_velocity` | `float` (F01, F06, F07, F08, F09, F10, F11) | F01, F06, F07, F08, F09, F10, F11 |

## `vehicle_acceleration`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_air_data`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `ambient_temperature` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `baro_alt_meter` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `baro_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `baro_pressure_pa` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `baro_temp_celcius` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `calibration_count` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `rho` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `temperature_source` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_angular_acceleration`

Observed in: F03, F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F03, F04) | F03, F04 |
| `timestamp_sample` | `uint64_t` (F03, F04) | F03, F04 |
| `xyz[0]` | `float` (F03, F04) | F03, F04 |
| `xyz[1]` | `float` (F03, F04) | F03, F04 |
| `xyz[2]` | `float` (F03, F04) | F03, F04 |

## `vehicle_angular_velocity`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xyz_derivative[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz_derivative[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz_derivative[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_angular_velocity_groundtruth`

Observed in: F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F10, F11) | F10, F11 |
| `timestamp_sample` | `uint64_t` (F10, F11) | F10, F11 |
| `xyz[0]` | `float` (F10, F11) | F10, F11 |
| `xyz[1]` | `float` (F10, F11) | F10, F11 |
| `xyz[2]` | `float` (F10, F11) | F10, F11 |
| `xyz_derivative[0]` | `float` (F10, F11) | F10, F11 |
| `xyz_derivative[1]` | `float` (F10, F11) | F10, F11 |
| `xyz_derivative[2]` | `float` (F10, F11) | F10, F11 |

## `vehicle_attitude`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `delta_q_reset[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_q_reset[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_q_reset[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_q_reset[3]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `q[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `q[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `q[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `q[3]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `quat_reset_counter` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_attitude_groundtruth`

Observed in: F04, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `delta_q_reset[0]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_q_reset[1]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_q_reset[2]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_q_reset[3]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `q[0]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `q[1]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `q[2]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `q[3]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `quat_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `timestamp` | `uint64_t` (F04, F10, F11) | F04, F10, F11 |
| `timestamp_sample` | `uint64_t` (F04, F10, F11) | F04, F10, F11 |

## `vehicle_attitude_setpoint`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `apply_flaps` | `uint8_t` (F02, F03, F04) | F02, F03, F04 |
| `fw_control_yaw` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `fw_control_yaw_wheel` | `bool` (F05, F06, F08) | F05, F06, F08 |
| `pitch_body` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `pitch_reset_integral` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `q_d[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `q_d[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `q_d[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `q_d[3]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_integral` | `bool` (F05, F06, F08) | F05, F06, F08 |
| `roll_body` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `roll_reset_integral` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `thrust_body[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `thrust_body[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `thrust_body[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw_body` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `yaw_reset_integral` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `yaw_sp_move_rate` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_command`

Observed in: F01, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `command` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `confirmation` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `from_external` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `param1` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `param2` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `param3` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `param4` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `param5` | `double` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `param6` | `double` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `param7` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `source_component` | `uint16_t` (F01, F05, F07, F08, F09, F10, F11); `uint8_t` (F03, F04, F06) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `source_system` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `target_component` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `target_system` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_command_ack`

Observed in: F01, F05, F06, F07, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `command` | `uint32_t` (F01, F05, F06, F07, F10, F11) | F01, F05, F06, F07, F10, F11 |
| `from_external` | `bool` (F01, F05, F06, F07, F10, F11) | F01, F05, F06, F07, F10, F11 |
| `result` | `uint8_t` (F01, F05, F06, F07, F10, F11) | F01, F05, F06, F07, F10, F11 |
| `result_param1` | `uint8_t` (F01, F05, F06, F07, F10, F11) | F01, F05, F06, F07, F10, F11 |
| `result_param2` | `int32_t` (F01, F05, F06, F07, F10, F11) | F01, F05, F06, F07, F10, F11 |
| `target_component` | `uint16_t` (F01, F05, F07, F10, F11); `uint8_t` (F06) | F01, F05, F06, F07, F10, F11 |
| `target_system` | `uint8_t` (F01, F05, F06, F07, F10, F11) | F01, F05, F06, F07, F10, F11 |
| `timestamp` | `uint64_t` (F01, F05, F06, F07, F10, F11) | F01, F05, F06, F07, F10, F11 |

## `vehicle_constraints`

Observed in: F01, F03, F04, F05, F06, F07, F08, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `speed_down` | `float` (F01, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F10, F11 |
| `speed_up` | `float` (F01, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F10, F11 |
| `speed_xy` | `float` (F04) | F04 |
| `timestamp` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F10, F11 |
| `want_takeoff` | `bool` (F01, F03, F04, F05, F06, F07, F08, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F10, F11 |

## `vehicle_control_mode`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `flag_armed` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_acceleration_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09) | F01, F02, F03, F04, F05, F06, F07, F08, F09 |
| `flag_control_allocation_enabled` | `bool` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `flag_control_altitude_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_attitude_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_auto_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_climb_rate_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_fixed_hdg_enabled` | `bool` (F02) | F02 |
| `flag_control_force_enabled` | `bool` (F02) | F02 |
| `flag_control_manual_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_offboard_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_position_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_rates_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_rattitude_enabled` | `bool` (F02) | F02 |
| `flag_control_termination_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09) | F01, F02, F03, F04, F05, F06, F07, F08, F09 |
| `flag_control_velocity_enabled` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `flag_control_yawrate_override_enabled` | `bool` (F02) | F02 |
| `flag_external_manual_override_ok` | `bool` (F02, F04) | F02, F04 |
| `flag_multicopter_position_control_enabled` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `source_id` | `uint8_t` (F01, F05, F07, F08, F09) | F01, F05, F07, F08, F09 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_global_position`

Observed in: F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `alt_ellipsoid` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `alt_reset_counter` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `alt_valid` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `dead_reckoning` | `bool` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_alt` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_terrain` | `float` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `eph` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `epv` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `lat` | `double` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `lat_lon_reset_counter` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `lat_lon_valid` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `lon` | `double` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `terrain_alt` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `terrain_alt_valid` | `bool` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `terrain_reset_counter` | `uint8_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_global_position_groundtruth`

Observed in: F04, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt` | `float` (F04, F10, F11) | F04, F10, F11 |
| `alt_ellipsoid` | `float` (F04, F10, F11) | F04, F10, F11 |
| `alt_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `alt_valid` | `bool` (F10, F11) | F10, F11 |
| `dead_reckoning` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `delta_alt` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_terrain` | `float` (F10, F11) | F10, F11 |
| `eph` | `float` (F04, F10, F11) | F04, F10, F11 |
| `epv` | `float` (F04, F10, F11) | F04, F10, F11 |
| `lat` | `double` (F04, F10, F11) | F04, F10, F11 |
| `lat_lon_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `lat_lon_valid` | `bool` (F10, F11) | F10, F11 |
| `lon` | `double` (F04, F10, F11) | F04, F10, F11 |
| `terrain_alt` | `float` (F04, F10, F11) | F04, F10, F11 |
| `terrain_alt_valid` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `terrain_reset_counter` | `uint8_t` (F10, F11) | F10, F11 |
| `timestamp` | `uint64_t` (F04, F10, F11) | F04, F10, F11 |
| `timestamp_sample` | `uint64_t` (F04, F10, F11) | F04, F10, F11 |

## `vehicle_gps_position`

Observed in: F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `alt_ellipsoid` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `altitude_ellipsoid_m` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `altitude_msl_m` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `antenna_offset_x` | `float` (F10, F11) | F10, F11 |
| `antenna_offset_y` | `float` (F10, F11) | F10, F11 |
| `antenna_offset_z` | `float` (F10, F11) | F10, F11 |
| `authentication_state` | `uint8_t` (F07, F10, F11) | F07, F10, F11 |
| `automatic_gain_control` | `uint16_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `c_variance_rad` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `cog_rad` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `device_id` | `uint32_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `eph` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `epv` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `fix_type` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hdop` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heading` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heading_accuracy` | `float` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `heading_offset` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `jamming_indicator` | `int32_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `jamming_state` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `lat` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `latitude_deg` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `lon` | `int32_t` (F03, F04, F06) | F03, F04, F06 |
| `longitude_deg` | `double` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `noise_per_ms` | `int32_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rtcm_crc_failed` | `bool` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `rtcm_injection_rate` | `float` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `rtcm_msg_used` | `uint8_t` (F05, F07, F08, F09, F10, F11) | F05, F07, F08, F09, F10, F11 |
| `s_variance_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `satellites_used` | `uint8_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `selected` | `uint8_t` (F03, F04) | F03, F04 |
| `selected_rtcm_instance` | `uint8_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `spoofing_state` | `uint8_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `system_error` | `uint32_t` (F07, F10, F11) | F07, F10, F11 |
| `time_utc_usec` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_time_relative` | `int32_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vdop` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_d_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_e_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_n_m_s` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vel_ned_valid` | `bool` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_imu`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_calibration_count` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `accel_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `calibration_count` | `uint8_t` (F04) | F04 |
| `delta_angle[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_angle[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_angle[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_angle_clipping` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `delta_angle_dt` | `uint16_t` (F02, F03, F04, F06); `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_velocity[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_velocity[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_velocity[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_velocity_clipping` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_velocity_dt` | `uint16_t` (F02, F03, F04, F06); `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_calibration_count` | `uint8_t` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_imu_status`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accel_clipping[0]` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_clipping[1]` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_clipping[2]` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_error_count` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_rate_hz` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11); `uint16_t` (F02) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_raw_rate_hz` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `accel_vibration_metric` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_angle_coning_metric` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_clipping[0]` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_clipping[1]` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_clipping[2]` | `uint32_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_coning_vibration` | `float` (F02, F04) | F02, F04 |
| `gyro_device_id` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_error_count` | `uint32_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_rate_hz` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11); `uint16_t` (F02) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_raw_rate_hz` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `gyro_vibration_metric` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mean_accel[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mean_accel[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mean_accel[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mean_gyro[0]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mean_gyro[1]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mean_gyro[2]` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `temperature_accel` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `temperature_gyro` | `float` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `var_accel[0]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `var_accel[1]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `var_accel[2]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `var_gyro[0]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `var_gyro[1]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `var_gyro[2]` | `float` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_land_detected`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `alt_max` | `float` (F02, F04) | F02, F04 |
| `at_rest` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `close_to_ground_or_skipped_check` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `freefall` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ground_contact` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `has_low_throttle` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `horizontal_movement` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `in_descend` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `in_ground_effect` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `landed` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `maybe_landed` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `rotational_movement` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vertical_movement` | `bool` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_local_position`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `ax` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ay` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `az` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `dead_reckoning` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `delta_dist_bottom` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `delta_heading` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_vxy[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_vxy[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_vz` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_xy[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_xy[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `delta_z` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `dist_bottom` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `dist_bottom_reset_counter` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `dist_bottom_sensor_bitfield` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `dist_bottom_valid` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `dist_bottom_var` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `eph` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `epv` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `evh` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `evv` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hagl_max` | `float` (F02, F03, F04, F06) | F02, F03, F04, F06 |
| `hagl_max_xy` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `hagl_max_z` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `hagl_min` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heading` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heading_good_for_control` | `bool` (F01, F03, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F05, F06, F07, F08, F09, F10, F11 |
| `heading_reset_counter` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `heading_var` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `ref_alt` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ref_lat` | `double` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ref_lon` | `double` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `ref_timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `tilt_var` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `unaided_heading` | `float` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `v_xy_valid` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `v_z_valid` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vx` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vxy_max` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vxy_reset_counter` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vy` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vz` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vz_max` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vz_reset_counter` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `x` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xy_global` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xy_reset_counter` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `xy_valid` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `y` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z_deriv` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z_global` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z_reset_counter` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z_valid` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_local_position_groundtruth`

Observed in: F04, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `ax` | `float` (F04, F10, F11) | F04, F10, F11 |
| `ay` | `float` (F04, F10, F11) | F04, F10, F11 |
| `az` | `float` (F04, F10, F11) | F04, F10, F11 |
| `dead_reckoning` | `bool` (F10, F11) | F10, F11 |
| `delta_dist_bottom` | `float` (F10, F11) | F10, F11 |
| `delta_heading` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_vxy[0]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_vxy[1]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_vz` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_xy[0]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_xy[1]` | `float` (F04, F10, F11) | F04, F10, F11 |
| `delta_z` | `float` (F04, F10, F11) | F04, F10, F11 |
| `dist_bottom` | `float` (F04, F10, F11) | F04, F10, F11 |
| `dist_bottom_reset_counter` | `uint8_t` (F10, F11) | F10, F11 |
| `dist_bottom_sensor_bitfield` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `dist_bottom_valid` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `dist_bottom_var` | `float` (F10, F11) | F10, F11 |
| `eph` | `float` (F04, F10, F11) | F04, F10, F11 |
| `epv` | `float` (F04, F10, F11) | F04, F10, F11 |
| `evh` | `float` (F04, F10, F11) | F04, F10, F11 |
| `evv` | `float` (F04, F10, F11) | F04, F10, F11 |
| `hagl_max` | `float` (F04) | F04 |
| `hagl_max_xy` | `float` (F10, F11) | F10, F11 |
| `hagl_max_z` | `float` (F10, F11) | F10, F11 |
| `hagl_min` | `float` (F04, F10, F11) | F04, F10, F11 |
| `heading` | `float` (F04, F10, F11) | F04, F10, F11 |
| `heading_good_for_control` | `bool` (F10, F11) | F10, F11 |
| `heading_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `heading_var` | `float` (F10, F11) | F10, F11 |
| `ref_alt` | `float` (F04, F10, F11) | F04, F10, F11 |
| `ref_lat` | `double` (F04, F10, F11) | F04, F10, F11 |
| `ref_lon` | `double` (F04, F10, F11) | F04, F10, F11 |
| `ref_timestamp` | `uint64_t` (F04, F10, F11) | F04, F10, F11 |
| `tilt_var` | `float` (F10, F11) | F10, F11 |
| `timestamp` | `uint64_t` (F04, F10, F11) | F04, F10, F11 |
| `timestamp_sample` | `uint64_t` (F04, F10, F11) | F04, F10, F11 |
| `unaided_heading` | `float` (F10, F11) | F10, F11 |
| `v_xy_valid` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `v_z_valid` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `vx` | `float` (F04, F10, F11) | F04, F10, F11 |
| `vxy_max` | `float` (F04, F10, F11) | F04, F10, F11 |
| `vxy_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `vy` | `float` (F04, F10, F11) | F04, F10, F11 |
| `vz` | `float` (F04, F10, F11) | F04, F10, F11 |
| `vz_max` | `float` (F04, F10, F11) | F04, F10, F11 |
| `vz_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `x` | `float` (F04, F10, F11) | F04, F10, F11 |
| `xy_global` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `xy_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `xy_valid` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `y` | `float` (F04, F10, F11) | F04, F10, F11 |
| `z` | `float` (F04, F10, F11) | F04, F10, F11 |
| `z_deriv` | `float` (F04, F10, F11) | F04, F10, F11 |
| `z_global` | `bool` (F04, F10, F11) | F04, F10, F11 |
| `z_reset_counter` | `uint8_t` (F04, F10, F11) | F04, F10, F11 |
| `z_valid` | `bool` (F04, F10, F11) | F04, F10, F11 |

## `vehicle_local_position_setpoint`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `acceleration[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `acceleration[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `acceleration[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `jerk[0]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `jerk[1]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `jerk[2]` | `float` (F02, F03, F04) | F02, F03, F04 |
| `thrust[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `thrust[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `thrust[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vx` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vy` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vz` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `x` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `y` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yawspeed` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `z` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_magnetometer`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `calibration_count` | `uint8_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `device_id` | `uint32_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `magnetometer_ga[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `magnetometer_ga[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `magnetometer_ga[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_rates_setpoint`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `pitch` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `reset_integral` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `roll` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `thrust_body[0]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `thrust_body[1]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `thrust_body[2]` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw` | `float` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_status`

Observed in: F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `accepts_offboard_setpoints` | `bool` (F10, F11) | F10, F11 |
| `armed_time` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `arming_state` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `avoidance_system_required` | `bool` (F06) | F06 |
| `avoidance_system_valid` | `bool` (F06) | F06 |
| `calibration_enabled` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `can_set_nav_states_mask` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `component_id` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `data_link_lost` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `data_link_lost_counter` | `uint8_t` (F02, F03, F04) | F02, F03, F04 |
| `engine_failure` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `executor_in_charge` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `failsafe` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `failsafe_and_user_took_over` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `failsafe_defer_state` | `uint8_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `failsafe_timestamp` | `uint64_t` (F03, F04) | F03, F04 |
| `failure_detector_status` | `uint16_t` (F01, F05, F06, F07, F08, F09); `uint8_t` (F02, F03, F04) | F01, F02, F03, F04, F05, F06, F07, F08, F09 |
| `gcs_connection_lost` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `gcs_connection_lost_counter` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `geofence_violated` | `bool` (F03, F04) | F03, F04 |
| `high_latency_data_link_lost` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `hil_state` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `in_transition_mode` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `in_transition_to_fw` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `is_vtol` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `is_vtol_tailsitter` | `bool` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `latest_arming_reason` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `latest_disarming_reason` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `mission_failure` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `nav_state` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `nav_state_display` | `uint8_t` (F10, F11) | F10, F11 |
| `nav_state_timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `nav_state_user_intention` | `uint8_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `onboard_control_sensors_enabled` | `uint32_t` (F02, F04); `uint64_t` (F03) | F02, F03, F04 |
| `onboard_control_sensors_health` | `uint32_t` (F02, F04); `uint64_t` (F03) | F02, F03, F04 |
| `onboard_control_sensors_present` | `uint32_t` (F02, F04); `uint64_t` (F03) | F02, F03, F04 |
| `open_drone_id_system_healthy` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `open_drone_id_system_present` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `parachute_system_healthy` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `parachute_system_present` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `power_input_valid` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `pre_flight_checks_pass` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `rc_calibration_in_progress` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `rc_input_mode` | `uint8_t` (F02, F04) | F02, F04 |
| `rc_signal_lost` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `safety_button_available` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `safety_off` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `system_id` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `system_type` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `takeoff_time` | `uint64_t` (F01, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `traffic_avoidance_system_present` | `bool` (F10, F11) | F10, F11 |
| `usb_connected` | `bool` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `valid_nav_states_mask` | `uint32_t` (F01, F05, F07, F08, F09, F10, F11) | F01, F05, F07, F08, F09, F10, F11 |
| `vehicle_type` | `uint8_t` (F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `vtol_fw_permanent_stab` | `bool` (F02, F03, F04) | F02, F03, F04 |

## `vehicle_status_flags`

Observed in: F02, F03, F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `angular_velocity_valid` | `bool` (F03) | F03 |
| `attitude_valid` | `bool` (F03) | F03 |
| `auto_mission_available` | `bool` (F03) | F03 |
| `avoidance_system_required` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `avoidance_system_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `battery_healthy` | `bool` (F03) | F03 |
| `calibration_enabled` | `bool` (F03) | F03 |
| `circuit_breaker_engaged_airspd_check` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `circuit_breaker_engaged_enginefailure_check` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `circuit_breaker_engaged_posfailure_check` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `circuit_breaker_engaged_power_check` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `circuit_breaker_engaged_usb_check` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `circuit_breaker_flight_termination_disabled` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `circuit_breaker_vtol_fw_arming_check` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `condition_angular_velocity_valid` | `bool` (F04) | F04 |
| `condition_attitude_valid` | `bool` (F04) | F04 |
| `condition_auto_mission_available` | `bool` (F02, F04) | F02, F04 |
| `condition_battery_healthy` | `bool` (F02, F04) | F02, F04 |
| `condition_calibration_enabled` | `bool` (F02, F04) | F02, F04 |
| `condition_escs_error` | `bool` (F02, F04) | F02, F04 |
| `condition_escs_failure` | `bool` (F04) | F04 |
| `condition_global_position_valid` | `bool` (F02, F04) | F02, F04 |
| `condition_home_position_valid` | `bool` (F02, F04) | F02, F04 |
| `condition_local_altitude_valid` | `bool` (F02, F04) | F02, F04 |
| `condition_local_position_valid` | `bool` (F02, F04) | F02, F04 |
| `condition_local_velocity_valid` | `bool` (F02, F04) | F02, F04 |
| `condition_power_input_valid` | `bool` (F02, F04) | F02, F04 |
| `condition_system_hotplug_timeout` | `bool` (F02, F04) | F02, F04 |
| `condition_system_returned_to_home` | `bool` (F02, F04) | F02, F04 |
| `condition_system_sensors_initialized` | `bool` (F02, F04) | F02, F04 |
| `dead_reckoning` | `bool` (F03) | F03 |
| `escs_error` | `bool` (F03) | F03 |
| `escs_failure` | `bool` (F03) | F03 |
| `flight_terminated` | `bool` (F03) | F03 |
| `global_position_valid` | `bool` (F03) | F03 |
| `gps_position_valid` | `bool` (F03) | F03 |
| `home_position_valid` | `bool` (F03) | F03 |
| `local_altitude_valid` | `bool` (F03) | F03 |
| `local_position_valid` | `bool` (F03) | F03 |
| `local_velocity_valid` | `bool` (F03) | F03 |
| `offboard_control_set_by_command` | `bool` (F02) | F02 |
| `offboard_control_signal_found_once` | `bool` (F02, F04) | F02, F04 |
| `offboard_control_signal_lost` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `parachute_system_healthy` | `bool` (F03) | F03 |
| `parachute_system_present` | `bool` (F03) | F03 |
| `position_reliant_on_gps` | `bool` (F03) | F03 |
| `position_reliant_on_optical_flow` | `bool` (F03) | F03 |
| `position_reliant_on_vision_position` | `bool` (F03) | F03 |
| `power_input_valid` | `bool` (F03) | F03 |
| `rc_calibration_in_progress` | `bool` (F03) | F03 |
| `rc_calibration_valid` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `rc_input_blocked` | `bool` (F02, F04) | F02, F04 |
| `rc_signal_found_once` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `sd_card_detected_once` | `bool` (F03, F04) | F03, F04 |
| `system_hotplug_timeout` | `bool` (F03) | F03 |
| `system_sensors_initialized` | `bool` (F03) | F03 |
| `timestamp` | `uint64_t` (F02, F03, F04) | F02, F03, F04 |
| `usb_connected` | `bool` (F02, F03, F04) | F02, F03, F04 |
| `vtol_transition_failure` | `bool` (F02, F03, F04) | F02, F03, F04 |

## `vehicle_thrust_setpoint`

Observed in: F01, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_torque_setpoint`

Observed in: F01, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[0]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[1]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |
| `xyz[2]` | `float` (F01, F05, F06, F07, F08, F09, F10, F11) | F01, F05, F06, F07, F08, F09, F10, F11 |

## `vehicle_trajectory_waypoint`

Observed in: F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F04) | F04 |
| `type` | `uint8_t` (F04) | F04 |
| `waypoints[0]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[0]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[0].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[0].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[0].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[0].point_valid` | `bool` (F04) | F04 |
| `waypoints[0].position[0]` | `float` (F04) | F04 |
| `waypoints[0].position[1]` | `float` (F04) | F04 |
| `waypoints[0].position[2]` | `float` (F04) | F04 |
| `waypoints[0].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[0].type` | `uint8_t` (F04) | F04 |
| `waypoints[0].velocity[0]` | `float` (F04) | F04 |
| `waypoints[0].velocity[1]` | `float` (F04) | F04 |
| `waypoints[0].velocity[2]` | `float` (F04) | F04 |
| `waypoints[0].yaw` | `float` (F04) | F04 |
| `waypoints[0].yaw_speed` | `float` (F04) | F04 |
| `waypoints[1]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[1]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[1].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[1].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[1].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[1].point_valid` | `bool` (F04) | F04 |
| `waypoints[1].position[0]` | `float` (F04) | F04 |
| `waypoints[1].position[1]` | `float` (F04) | F04 |
| `waypoints[1].position[2]` | `float` (F04) | F04 |
| `waypoints[1].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[1].type` | `uint8_t` (F04) | F04 |
| `waypoints[1].velocity[0]` | `float` (F04) | F04 |
| `waypoints[1].velocity[1]` | `float` (F04) | F04 |
| `waypoints[1].velocity[2]` | `float` (F04) | F04 |
| `waypoints[1].yaw` | `float` (F04) | F04 |
| `waypoints[1].yaw_speed` | `float` (F04) | F04 |
| `waypoints[2]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[2]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[2].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[2].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[2].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[2].point_valid` | `bool` (F04) | F04 |
| `waypoints[2].position[0]` | `float` (F04) | F04 |
| `waypoints[2].position[1]` | `float` (F04) | F04 |
| `waypoints[2].position[2]` | `float` (F04) | F04 |
| `waypoints[2].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[2].type` | `uint8_t` (F04) | F04 |
| `waypoints[2].velocity[0]` | `float` (F04) | F04 |
| `waypoints[2].velocity[1]` | `float` (F04) | F04 |
| `waypoints[2].velocity[2]` | `float` (F04) | F04 |
| `waypoints[2].yaw` | `float` (F04) | F04 |
| `waypoints[2].yaw_speed` | `float` (F04) | F04 |
| `waypoints[3]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[3]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[3].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[3].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[3].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[3].point_valid` | `bool` (F04) | F04 |
| `waypoints[3].position[0]` | `float` (F04) | F04 |
| `waypoints[3].position[1]` | `float` (F04) | F04 |
| `waypoints[3].position[2]` | `float` (F04) | F04 |
| `waypoints[3].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[3].type` | `uint8_t` (F04) | F04 |
| `waypoints[3].velocity[0]` | `float` (F04) | F04 |
| `waypoints[3].velocity[1]` | `float` (F04) | F04 |
| `waypoints[3].velocity[2]` | `float` (F04) | F04 |
| `waypoints[3].yaw` | `float` (F04) | F04 |
| `waypoints[3].yaw_speed` | `float` (F04) | F04 |
| `waypoints[4]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[4]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[4].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[4].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[4].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[4].point_valid` | `bool` (F04) | F04 |
| `waypoints[4].position[0]` | `float` (F04) | F04 |
| `waypoints[4].position[1]` | `float` (F04) | F04 |
| `waypoints[4].position[2]` | `float` (F04) | F04 |
| `waypoints[4].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[4].type` | `uint8_t` (F04) | F04 |
| `waypoints[4].velocity[0]` | `float` (F04) | F04 |
| `waypoints[4].velocity[1]` | `float` (F04) | F04 |
| `waypoints[4].velocity[2]` | `float` (F04) | F04 |
| `waypoints[4].yaw` | `float` (F04) | F04 |
| `waypoints[4].yaw_speed` | `float` (F04) | F04 |

## `vehicle_trajectory_waypoint_desired`

Observed in: F04.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `timestamp` | `uint64_t` (F04) | F04 |
| `type` | `uint8_t` (F04) | F04 |
| `waypoints[0]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[0]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[0].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[0].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[0].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[0].point_valid` | `bool` (F04) | F04 |
| `waypoints[0].position[0]` | `float` (F04) | F04 |
| `waypoints[0].position[1]` | `float` (F04) | F04 |
| `waypoints[0].position[2]` | `float` (F04) | F04 |
| `waypoints[0].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[0].type` | `uint8_t` (F04) | F04 |
| `waypoints[0].velocity[0]` | `float` (F04) | F04 |
| `waypoints[0].velocity[1]` | `float` (F04) | F04 |
| `waypoints[0].velocity[2]` | `float` (F04) | F04 |
| `waypoints[0].yaw` | `float` (F04) | F04 |
| `waypoints[0].yaw_speed` | `float` (F04) | F04 |
| `waypoints[1]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[1]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[1].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[1].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[1].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[1].point_valid` | `bool` (F04) | F04 |
| `waypoints[1].position[0]` | `float` (F04) | F04 |
| `waypoints[1].position[1]` | `float` (F04) | F04 |
| `waypoints[1].position[2]` | `float` (F04) | F04 |
| `waypoints[1].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[1].type` | `uint8_t` (F04) | F04 |
| `waypoints[1].velocity[0]` | `float` (F04) | F04 |
| `waypoints[1].velocity[1]` | `float` (F04) | F04 |
| `waypoints[1].velocity[2]` | `float` (F04) | F04 |
| `waypoints[1].yaw` | `float` (F04) | F04 |
| `waypoints[1].yaw_speed` | `float` (F04) | F04 |
| `waypoints[2]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[2]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[2].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[2].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[2].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[2].point_valid` | `bool` (F04) | F04 |
| `waypoints[2].position[0]` | `float` (F04) | F04 |
| `waypoints[2].position[1]` | `float` (F04) | F04 |
| `waypoints[2].position[2]` | `float` (F04) | F04 |
| `waypoints[2].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[2].type` | `uint8_t` (F04) | F04 |
| `waypoints[2].velocity[0]` | `float` (F04) | F04 |
| `waypoints[2].velocity[1]` | `float` (F04) | F04 |
| `waypoints[2].velocity[2]` | `float` (F04) | F04 |
| `waypoints[2].yaw` | `float` (F04) | F04 |
| `waypoints[2].yaw_speed` | `float` (F04) | F04 |
| `waypoints[3]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[3]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[3].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[3].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[3].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[3].point_valid` | `bool` (F04) | F04 |
| `waypoints[3].position[0]` | `float` (F04) | F04 |
| `waypoints[3].position[1]` | `float` (F04) | F04 |
| `waypoints[3].position[2]` | `float` (F04) | F04 |
| `waypoints[3].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[3].type` | `uint8_t` (F04) | F04 |
| `waypoints[3].velocity[0]` | `float` (F04) | F04 |
| `waypoints[3].velocity[1]` | `float` (F04) | F04 |
| `waypoints[3].velocity[2]` | `float` (F04) | F04 |
| `waypoints[3].yaw` | `float` (F04) | F04 |
| `waypoints[3].yaw_speed` | `float` (F04) | F04 |
| `waypoints[4]._padding0[0]` | `uint8_t` (F04) | F04 |
| `waypoints[4]._padding0[1]` | `uint8_t` (F04) | F04 |
| `waypoints[4].acceleration[0]` | `float` (F04) | F04 |
| `waypoints[4].acceleration[1]` | `float` (F04) | F04 |
| `waypoints[4].acceleration[2]` | `float` (F04) | F04 |
| `waypoints[4].point_valid` | `bool` (F04) | F04 |
| `waypoints[4].position[0]` | `float` (F04) | F04 |
| `waypoints[4].position[1]` | `float` (F04) | F04 |
| `waypoints[4].position[2]` | `float` (F04) | F04 |
| `waypoints[4].timestamp` | `uint64_t` (F04) | F04 |
| `waypoints[4].type` | `uint8_t` (F04) | F04 |
| `waypoints[4].velocity[0]` | `float` (F04) | F04 |
| `waypoints[4].velocity[1]` | `float` (F04) | F04 |
| `waypoints[4].velocity[2]` | `float` (F04) | F04 |
| `waypoints[4].yaw` | `float` (F04) | F04 |
| `waypoints[4].yaw_speed` | `float` (F04) | F04 |

## `yaw_estimator_status`

Observed in: F03, F04, F05, F06, F07, F08, F09, F10, F11.

| Field | Observed type(s) | Files |
| --- | --- | --- |
| `innov_ve[0]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_ve[1]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_ve[2]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_ve[3]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_ve[4]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_vn[0]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_vn[1]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_vn[2]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_vn[3]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `innov_vn[4]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `timestamp_sample` | `uint64_t` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `weight[0]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `weight[1]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `weight[2]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `weight[3]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `weight[4]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw[0]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw[1]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw[2]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw[3]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw[4]` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw_composite` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
| `yaw_composite_valid` | `bool` (F05, F06, F07, F08, F09, F10, F11) | F05, F06, F07, F08, F09, F10, F11 |
| `yaw_variance` | `float` (F03, F04, F05, F06, F07, F08, F09, F10, F11) | F03, F04, F05, F06, F07, F08, F09, F10, F11 |
