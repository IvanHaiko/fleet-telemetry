"""Verify the untouched runtime and the explicitly pinned local connector repair."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast


def main() -> None:
    subprocess.run(
        [sys.executable, "-B", "/opt/m3/preflight-base.py"], check=True, timeout=120
    )
    pin = cast(
        dict[str, str], json.loads(Path("/opt/m3/connector-image-pin.json").read_text())
    )
    if pin.get("profile") != "m3-kafka-31006-backport-v1":
        raise ValueError("connector_backport_profile")
    filename = "flink-sql-connector-kafka-5.0.0-2.2.jar"
    original = Path(os.environ["FLEET_RUNTIME"]) / filename
    installed = Path(os.environ["FLINK_HOME"]) / "lib" / filename
    for path, key in ((original, "original_sha256"), (installed, "patched_sha256")):
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin[key]:
            raise ValueError("connector_backport_hash")
    print(json.dumps({"status": "connector_backport_verified", **pin}))


if __name__ == "__main__":
    main()
