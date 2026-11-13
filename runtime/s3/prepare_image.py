"""Prepare an offline image context from exactly pinned upstream bytes."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path
from typing import cast


class PreparationError(ValueError):
    """Safe preparation refusal without partially accepting another release."""


def _digest(path: Path, expected_bytes: int, expected_hash: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise PreparationError("regular_input_required")
    if path.stat().st_size != expected_bytes:
        raise PreparationError("input_length_mismatch")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected_hash:
        raise PreparationError("input_checksum_mismatch")


def prepare_context(archive: Path, license_path: Path, output: Path) -> dict[str, str]:
    """Validate every input before creating a fresh, never overwritten context."""
    directory = Path(__file__).resolve().parent
    pins_object: object = json.loads((directory / "artifacts.json").read_bytes())
    if not isinstance(pins_object, dict):
        raise PreparationError("invalid_pins")
    pins = cast(dict[str, object], pins_object)
    for name in ("archive_bytes", "binary_bytes"):
        if type(pins.get(name)) is not int or cast(int, pins[name]) <= 0:
            raise PreparationError("invalid_pins")
    for name in ("archive_sha256", "binary_sha256", "source_license_sha256"):
        value = pins.get(name)
        if not isinstance(value, str) or len(value) != 64:
            raise PreparationError("invalid_pins")
        if any(char not in "0123456789abcdef" for char in value):
            raise PreparationError("invalid_pins")
    _digest(
        archive, cast(int, pins["archive_bytes"]), cast(str, pins["archive_sha256"])
    )
    if license_path.is_symlink() or not license_path.is_file():
        raise PreparationError("regular_input_required")
    if not 1 <= license_path.stat().st_size <= 64 * 1024:
        raise PreparationError("license_limit_exceeded")
    license_bytes = license_path.read_bytes()
    if hashlib.sha256(license_bytes).hexdigest() != pins["source_license_sha256"]:
        raise PreparationError("license_checksum_mismatch")
    with tarfile.open(archive, "r:gz") as bundle:
        entries = bundle.getmembers()
        if len(entries) != 1:
            raise PreparationError("unexpected_archive_entries")
        member = entries[0]
        if (
            member.name != "weed"
            or not member.isfile()
            or member.size != pins["binary_bytes"]
        ):
            raise PreparationError("unexpected_archive_member")
        stream = bundle.extractfile(member)
        if stream is None:
            raise PreparationError("missing_executable")
        with stream:
            binary = stream.read(cast(int, pins["binary_bytes"]) + 1)
    if len(binary) != pins["binary_bytes"]:
        raise PreparationError("binary_length_mismatch")
    if hashlib.sha256(binary).hexdigest() != pins["binary_sha256"]:
        raise PreparationError("binary_checksum_mismatch")
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise PreparationError("fresh_output_required")
    payload = {
        "weed": binary,
        "LICENSE": license_bytes,
        # The already tested Windows build context used CRLF. Preserve those
        # exact input bytes on every host rather than silently changing layers.
        "Dockerfile": (directory / "Dockerfile")
        .read_bytes()
        .replace(b"\r\n", b"\n")
        .replace(b"\n", b"\r\n"),
        "data/volume-owner": (
            b"Initial ownership seed for the isolated M4 storage volume.\r\n"
        ),
    }
    output.mkdir()
    (output / "data").mkdir()
    hashes: dict[str, str] = {}
    for name, data in payload.items():
        with (output / name).open("xb") as target:
            target.write(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    (output / "weed").chmod(0o755)
    # Failures retain a visibly incomplete context; no recursive cleanup occurs.
    with (output / "preparation.json").open("x", encoding="utf-8") as receipt:
        json.dump({"complete": True, "sha256": hashes}, receipt, indent=2)
        receipt.write("\n")
    return hashes


def main() -> int:
    """Print safe preparation outcome; never download, build or start services."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--license", dest="license_path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        hashes = prepare_context(args.archive, args.license_path, args.output)
    except (OSError, ValueError, tarfile.TarError):
        print(json.dumps({"complete": False, "reason": "preparation_refused"}))
        return 1
    print(json.dumps({"complete": True, "sha256": hashes}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
