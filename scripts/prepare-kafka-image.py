"""Prepare only the pinned Kafka 4.4.0 local image build context."""

import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://downloads.apache.org/kafka/4.4.0/kafka_2.13-4.4.0.tgz"
SHA512 = (
    "f5ceba8a265ab6bb2d68362b1f6859a95e15d60ef92ba83b43fdf065b557dc18"
    "e98d6383c15b9977320e25b3a2c8b6f11decb17b0fa6c0f163423793a0eb95cb"
)
MAX_BYTES = 256 * 1024 * 1024


def checksum(path: Path) -> str:
    """Hash exact archive bytes without expanding them on the host."""
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha512").hexdigest()


def prepare() -> None:
    """Download once with bounded reads and refuse mismatching retained bytes."""
    context = ROOT / ".local-discovery/kafka-image"
    context.mkdir(parents=True, exist_ok=True)
    archive = context / "kafka.tgz"
    if not archive.exists():
        partial = context / "kafka.tgz.partial"
        deadline = time.monotonic() + 180
        size = 0
        with partial.open("xb") as destination:
            with urllib.request.urlopen(URL, timeout=20) as response:
                while chunk := response.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES or time.monotonic() > deadline:
                        raise ValueError("archive_download_bound_exceeded")
                    destination.write(chunk)
        if checksum(partial) != SHA512:
            raise ValueError("archive_checksum_mismatch")
        # rename refuses an existing destination on the supported Windows host.
        partial.rename(archive)
    if archive.stat().st_size > MAX_BYTES or checksum(archive) != SHA512:
        raise ValueError("retained_archive_checksum_mismatch")
    for name in ("Dockerfile", "kafka-probe.properties", "start-kafka.sh"):
        source = ROOT / "runtime/kafka" / name
        # Normalize authored text for execution by Linux tools.
        (context / name).write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
    shutil.copyfile(
        ROOT / "docs/adr/0013-local-kafka-release-image.md", context / "decision.md"
    )
    print(
        json.dumps(
            {
                "status": "prepared",
                "archive_url": URL,
                "bytes": archive.stat().st_size,
                "sha512": SHA512,
                "context": str(context),
                "signature_verified": False,
            }
        )
    )


if __name__ == "__main__":
    prepare()
