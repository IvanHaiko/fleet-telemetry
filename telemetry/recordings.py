"""Registered exact-file recordings admitted to the integrated recording path.

Each entry is a reviewed, exact original: its checksum, firmware, embedded field
definitions, selected stream counts, vehicle pseudonym and versioned names. A
file that is not registered here is refused before any parser runs. Adding an
entry requires the source, rights, field-meaning and time review recorded in
ADR-0057; the F09 entry reproduces the names that ADR-0041 and ADR-0049 fixed,
so its identities and bytes do not change.

This module imports nothing from the project, so the low-level integrity
checker and every adapter can depend on it without cycles.
"""

from dataclasses import dataclass
from typing import Literal

STATE_STREAMS = ("vehicle_land_detected", "vehicle_status")

# Default bounded-reader limits; F09 alone has the larger ADR-0041 limits.
DEFAULT_MAX_INPUT_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_RECORDS = 100_000


@dataclass(frozen=True)
class Recording:
    """One reviewed original; every derived name keeps the registered key."""

    key: str
    label: str
    source_id: str
    source_bytes: int
    firmware: str
    vehicle_id: str
    battery_definition: str
    gps_definition: str
    state_definitions: tuple[tuple[str, str], ...]
    gps_records: int
    battery_records: int
    state_records: tuple[tuple[str, int], ...]
    # "degrees": float64 latitude_deg/longitude_deg/altitude_msl_m with
    # timestamp_sample. "scaled_integer": int32 lat/lon in 1e-7 degrees and
    # alt in millimetres, without timestamp_sample (older SensorGps layout).
    gps_layout: Literal["degrees", "scaled_integer"]
    dropout_markers: int
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES
    max_records: int = DEFAULT_MAX_RECORDS

    def name(self, suffix: str) -> str:
        """Versioned profile or format name under this recording's key."""
        return f"{self.key}-{suffix}"

    @property
    def gps_profile(self) -> str:
        return self.name("gps-research-v1")

    @property
    def state_profile(self) -> str:
        return self.name("state-research-v1")

    @property
    def battery_normalization(self) -> str:
        return f"ulog-battery-{self.key}-research-v1"

    @property
    def battery_native_format(self) -> str:
        return f"px4-battery-status-{self.firmware[:8]}-v1"

    @property
    def battery_producer_profile(self) -> str:
        return f"px4-{self.key}-producer-unverified-v1"

    @property
    def battery_pipeline(self) -> str:
        return f"bounded-converter-{self.key}-research-v1"

    @property
    def battery_manifest_id(self) -> str:
        return self.name("restricted-research-v1")

    @property
    def state_counts(self) -> dict[str, int]:
        return dict(self.state_records)

    @property
    def state_definition_map(self) -> dict[str, str]:
        return dict(self.state_definitions)


_F09_STATE = (
    (
        "vehicle_land_detected",
        "27a0f6bb53a636b60bd86e021e3db416a7cc6505701a6285f2bc793fc76cb687",
    ),
    (
        "vehicle_status",
        "1831131423c63fe4eb3fc837cc6f4cf5aed73a01f475c6e4034aaec6044d26dd",
    ),
)

F09 = Recording(
    key="f09",
    label="F09",
    source_id="sha256:30f1d0f89f6eed0853cdf78a04eced1c5f56afd047541594158a76df74b1a1a0",
    source_bytes=122_463_132,
    firmware="9a2a8d4d3cf3bc74956337d8da8d506073684be0",
    vehicle_id="f09-research-vehicle",
    battery_definition=(
        "sha256:249dc314d1c3efb0a47293f5cd70f535e55ccd59aa14260ab4777ec43cce5dcb"
    ),
    gps_definition="e01e4b9dfff5a5b7332eca486e78460ddacf9bb36363a8cb450c176eda18675e",
    state_definitions=_F09_STATE,
    gps_records=21_054,
    battery_records=11_730,
    state_records=(("vehicle_land_detected", 2337), ("vehicle_status", 4644)),
    gps_layout="degrees",
    dropout_markers=15,
    max_input_bytes=128 * 1024 * 1024,
    max_records=2_500_000,
)

F07 = Recording(
    key="f07",
    label="F07",
    source_id="sha256:c426c6e8a5bfd00d2e48946493c4e44c32d2d02ae7cc637973dcb117ec3cceff",
    source_bytes=8_079_735,
    firmware="d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
    vehicle_id="f07-research-vehicle",
    battery_definition=(
        "sha256:7a97e9bcf63f8679be61a15f0a3089c6d212a76579ab129bff7b781f22139d8d"
    ),
    gps_definition="dc4f3afc4d21a4fd3a2dbfe1e258793ba3401e0118990e44a11620a30e9dace9",
    # Same embedded state layouts as F09 and F01 (ADR-0044).
    state_definitions=_F09_STATE,
    gps_records=182,
    battery_records=932,
    state_records=(("vehicle_land_detected", 199), ("vehicle_status", 379)),
    gps_layout="degrees",
    dropout_markers=0,
    # 159,459 frames in total; the default 100,000-frame bound is too small.
    max_records=200_000,
)

F03 = Recording(
    key="f03",
    label="F03",
    source_id="sha256:d8a1f18026a781eeb7ac33e20a9105611f27fb94f4b85e1b62ef1bf31ae0e841",
    source_bytes=12_386_279,
    firmware="46a12a09bf11c8cbafc5ad905996645b4fe1a9df",
    vehicle_id="f03-research-vehicle",
    battery_definition=(
        "sha256:c59bce8aa512ae86e731a010d475e38664fd1027dca38f360132fff4a98966a3"
    ),
    gps_definition="fc0cfd95889b1e16653a014fcbbb392a612494b08fefab4ef16c8f84d442c112",
    state_definitions=(
        (
            "vehicle_land_detected",
            "e987309e73577d7d589030c204caef77887057c06e25c9af84917afd69758b29",
        ),
        (
            "vehicle_status",
            "7a69930e30ea0a27ea79382480306f6f60cf31fa00099464cf0b3685cb3fbf91",
        ),
    ),
    gps_records=259,
    battery_records=649,
    state_records=(("vehicle_land_detected", 139), ("vehicle_status", 258)),
    gps_layout="scaled_integer",
    dropout_markers=0,
    # 250,072 frames in total.
    max_records=300_000,
)

RECORDINGS: dict[str, Recording] = {item.source_id: item for item in (F09, F07, F03)}
BY_KEY: dict[str, Recording] = {item.key: item for item in RECORDINGS.values()}


def recording(source_id: object) -> Recording:
    """Return the registered recording for an exact checksum, or refuse."""
    if not isinstance(source_id, str) or source_id not in RECORDINGS:
        raise ValueError("unregistered_recording")
    return RECORDINGS[source_id]


def recording_by_key(key: object) -> Recording:
    if not isinstance(key, str) or key not in BY_KEY:
        raise ValueError("unregistered_recording")
    return BY_KEY[key]


def by_profile(profile: object, suffix: str) -> Recording:
    """Resolve a versioned name such as ``f07-recording-event-v1``."""
    if isinstance(profile, str):
        for item in RECORDINGS.values():
            if profile == item.name(suffix):
                return item
    raise ValueError("unregistered_recording_profile")
