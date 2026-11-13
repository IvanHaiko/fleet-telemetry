"""Verify the exact copied Linux runtime and actual native imports before use."""

import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import cast


def main() -> None:
    root = Path(os.environ["FLEET_RUNTIME"])
    manifest = cast(
        dict[str, dict[str, int | str]],
        json.loads(Path("/opt/m3/runtime-manifest.json").read_text()),
    )
    for name, expected in manifest.items():
        path = root / name
        if "symlink" in expected:
            if not path.is_symlink() or os.readlink(path) != expected["symlink"]:
                raise ValueError("runtime_symlink_changed")
        else:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            if (
                digest.hexdigest() != expected["sha256"]
                or path.stat().st_size != expected["bytes"]
                or path.stat().st_mode & 0o777 != expected["mode"]
            ):
                raise ValueError("runtime_file_changed")
    if platform.python_version() != "3.12.13":
        raise ValueError("wrong_runtime_python")
    if importlib.metadata.version("apache-flink") != "2.2.1":
        raise ValueError("wrong_runtime_flink")
    utility = cast(
        dict[str, str], json.loads(Path("/opt/m3/utility-pins.json").read_text())
    )
    if (
        hashlib.sha256(Path(utility["image_path"]).read_bytes()).hexdigest()
        != utility["sha256"]
    ):
        raise ValueError("runtime_utility_changed")
    for module in ("pyflink", "grpc", "numpy", "pyarrow", "apache_beam"):
        importlib.import_module(module)
    java = subprocess.run(
        [str(Path(os.environ["JAVA_HOME"]) / "bin/java"), "-version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if "17.0.20.1" not in java.stderr:
        raise ValueError("wrong_runtime_java")
    print(
        json.dumps(
            {
                "status": "copied_runtime_verified",
                "python": platform.python_version(),
                "flink": "2.2.1",
                "java": java.stderr,
                "files": len(manifest),
            }
        )
    )


if __name__ == "__main__":
    main()
