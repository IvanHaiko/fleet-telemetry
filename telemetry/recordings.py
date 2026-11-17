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

import re
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

# Topics a mapping profile selects, and the capability each one serves.
SELECTED_TOPICS = (
    "vehicle_gps_position",
    "battery_status",
    "vehicle_land_detected",
    "vehicle_status",
)
# Limits for a file admitted under a mapping profile: those of the largest
# reviewed original (F09, ADR-0041), never larger.
ADMITTED_MAX_INPUT_BYTES = F09.max_input_bytes
ADMITTED_MAX_RECORDS = F09.max_records
# Per-file counts a validator did not measure itself (see ``resolve``).
UNMEASURED = -1


@dataclass(frozen=True)
class MappingProfile:
    """Reviewed meanings for a set of embedded layouts on reviewed firmware.

    A file whose selected topics have exactly these layout digests (each
    topic's definition with every definition it references) and whose reported
    firmware is listed here is admitted without a registry entry (ADR-0058).
    The meanings were reviewed once, for ``reference``; widening ``firmware``
    needs evidence for units, sentinels, enumerations and clocks.
    """

    key: str
    reference: Recording
    firmware: tuple[str, ...]

    @property
    def layouts(self) -> dict[str, str]:
        reference = self.reference
        return {
            "vehicle_gps_position": reference.gps_definition,
            "battery_status": reference.battery_definition.removeprefix("sha256:"),
            **reference.state_definition_map,
        }

    def admit(
        self,
        source_id: str,
        *,
        firmware: str,
        source_bytes: int,
        gps_records: int,
        battery_records: int,
        state_records: tuple[tuple[str, int], ...],
        dropout_markers: int,
    ) -> Recording:
        """One admitted original: shared reviewed names, its own identity."""
        if _SOURCE_ID.fullmatch(source_id) is None:
            raise ValueError("admission_source_id")
        if firmware and firmware not in self.firmware:
            raise ValueError("admission_firmware")
        digest = source_id.removeprefix("sha256:")
        reference = self.reference
        return Recording(
            key=self.key,
            label="ULog " + digest[:8],
            source_id=source_id,
            source_bytes=source_bytes,
            firmware=firmware,
            # A pseudonym of the file, not of a vehicle: a firmware mapping
            # carries no evidence of physical vehicle identity.
            vehicle_id=f"ulog-{digest[:16]}",
            battery_definition=reference.battery_definition,
            gps_definition=reference.gps_definition,
            state_definitions=reference.state_definitions,
            gps_records=gps_records,
            battery_records=battery_records,
            state_records=state_records,
            gps_layout=reference.gps_layout,
            dropout_markers=dropout_markers,
            max_input_bytes=ADMITTED_MAX_INPUT_BYTES,
            max_records=ADMITTED_MAX_RECORDS,
        )


# Firmware revisions reviewed for a profile beyond its reference recording's
# own (ADR-0058): at each listed commit the upstream BatteryStatus, SensorGps
# and VehicleLandDetected definitions equal the reference's byte for byte, and
# VehicleStatus differs only in VEHICLE_TYPE constants, a field no mapping reads.
REVIEWED_FIRMWARE = {
    "f09": (
        "54f0455ffcd755534539a7cf33a09a20bf71d29d",
        "94cb2012792b2ae89f0b147cfee53ee31ae550be",
    ),
}
MAPPING_PROFILES: tuple[MappingProfile, ...] = tuple(
    MappingProfile(
        f"px4-{item.key}-v1",
        item,
        (item.firmware, *REVIEWED_FIRMWARE.get(item.key, ())),
    )
    for item in (F09, F07, F03)
)
_SOURCE_ID = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)
# Admitted originals known to this process: measured ones (from the file) and
# identity-only ones resolved from a versioned name (UNMEASURED counts).
_ADMITTED: dict[str, Recording] = {}


def register_admitted(item: Recording) -> Recording:
    """Make a measured admission resolvable by checksum in this process."""
    if item.source_id in RECORDINGS or item.key not in _MAPPING_KEYS:
        raise ValueError("admission_conflict")
    known = _ADMITTED.get(item.source_id)
    if known is not None and known.source_bytes != UNMEASURED and known != item:
        raise ValueError("admission_conflict")
    _ADMITTED[item.source_id] = item
    return item


_MAPPING_KEYS = {item.key: item for item in MAPPING_PROFILES}


def withdraw_admitted(source_id: str) -> None:
    """Forget an admission whose later checks failed in this process."""
    _ADMITTED.pop(source_id, None)


def lookup(source_id: object) -> Recording | None:
    """A registered recording, else an admission known to this process."""
    if not isinstance(source_id, str):
        return None
    return RECORDINGS.get(source_id) or _ADMITTED.get(source_id)


def recording(source_id: object) -> Recording:
    """Return the registered or admitted recording for a checksum, or refuse."""
    found = lookup(source_id)
    if found is None:
        raise ValueError("unregistered_recording")
    return found


def resolve(source_id: object, profile: object, suffix: str) -> Recording:
    """Resolve an envelope's source from its checksum and versioned name.

    A registered checksum keeps its legacy recipe. Otherwise a name under a
    mapping profile (``px4-f09-v1-<suffix>``) yields that profile's meanings
    for this checksum. Admission was decided where the original was read;
    a downstream validator that never sees the original gets the identity
    only, with per-file counts UNMEASURED and no firmware, so a count or
    firmware check fails closed.
    """
    found = lookup(source_id)
    if found is not None:
        return found
    if isinstance(source_id, str) and isinstance(profile, str):
        for item in MAPPING_PROFILES:
            if profile == f"{item.key}-{suffix}":
                resolved = item.admit(
                    source_id,
                    firmware="",
                    source_bytes=UNMEASURED,
                    gps_records=UNMEASURED,
                    battery_records=UNMEASURED,
                    state_records=(),
                    dropout_markers=UNMEASURED,
                )
                _ADMITTED.setdefault(source_id, resolved)
                return _ADMITTED[source_id]
    raise ValueError("unregistered_recording")


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


def by_battery_normalization(version: object) -> tuple[Recording | None, bool]:
    """(registered recording, is a mapping-profile name) for a version string."""
    if isinstance(version, str):
        for item in RECORDINGS.values():
            if version == item.battery_normalization:
                return item, False
        for profile in MAPPING_PROFILES:
            if version == f"ulog-battery-{profile.key}-research-v1":
                return None, True
    return None, False
