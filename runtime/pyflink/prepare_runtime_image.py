"""Stage only the existing pinned Linux runtime for an offline local image build."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from bootstrap import paths


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def stage(runtime: Path, output: Path) -> dict[str, object]:
    """Refuse existing destinations and links escaping the owned runtime."""
    runtime = runtime.resolve(strict=True)
    selected = paths(runtime)
    if (
        os.name != "posix"
        or not runtime.is_relative_to(
            Path.home() / ".local/share/fleet-telemetry/pyflink"
        )
        or output.exists()
        or not output.is_absolute()
        or output.is_relative_to(runtime)
    ):
        raise ValueError("invalid_runtime_image_scope")
    names = ["python", "jdk", "venv", selected["connector"].name]
    manifest: dict[str, dict[str, str | int]] = {}
    for name in names:
        source = runtime / name
        for path in [source] if source.is_file() else source.rglob("*"):
            relative = path.relative_to(runtime).as_posix()
            mode = path.lstat().st_mode & 0o777
            if path.is_symlink():
                target = path.resolve(strict=True)
                if not any(
                    target == runtime / name or target.is_relative_to(runtime / name)
                    for name in names
                ):
                    raise ValueError("runtime_link_escapes_scope")
                manifest[relative] = {"symlink": os.readlink(path), "mode": mode}
            elif path.is_file():
                manifest[relative] = {
                    "sha256": digest(path),
                    "bytes": path.stat().st_size,
                    "mode": mode,
                }
    needed = sum(int(item.get("bytes", 0)) for item in manifest.values()) + 1024**3
    if shutil.disk_usage(output.parent).free < needed:
        raise ValueError("runtime_image_disk_budget")
    output.mkdir()
    payload = output / "runtime-payload.tar"
    with tarfile.open(payload, "x") as archive:
        for name in names:
            archive.add(runtime / name, arcname=name)
    (output / "runtime-payload-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    container = Path(__file__).with_name("container")
    for name in ("Dockerfile", "entrypoint.sh", "preflight.py"):
        shutil.copyfile(container / name, output / name)
    utility = json.loads((container / "utility-pins.json").read_text())
    if (
        digest(Path("/usr/bin/rev")) != utility["sha256"]
        or subprocess.check_output(
            ["dpkg-query", "-W", "-f", "${Version}", "bsdextrautils"], text=True
        )
        != utility["version"]
    ):
        raise ValueError("runtime_utility_pin_mismatch")
    for source, destination in (
        (Path("/usr/bin/rev"), "rev"),
        (Path("/usr/share/doc/bsdextrautils/copyright"), "rev-copyright"),
        (Path("/usr/share/common-licenses/GPL-2"), "GPL-2"),
        (container / "utility-pins.json", "utility-pins.json"),
    ):
        shutil.copyfile(source, output / destination)
    original = (
        selected["venv"] / "lib/python3.12/site-packages/pyflink/conf/config.yaml"
    )
    options = [
        line.partition("all: ")[2]
        for line in original.read_text().splitlines()
        if line.startswith("      all: ")
    ]
    if len(options) != 1 or "--add-opens=java.base/java.lang" not in options[0]:
        raise ValueError("jdk_options_not_recognized")
    (output / "config.yaml").write_text(
        (container / "config.yaml").read_text()
        + "env.java.opts.all: "
        + json.dumps(options[0])
        + "\n"
    )
    receipt: dict[str, object] = {
        "profile": "m3-offline-runtime-image-v1",
        "runtime_prefix": str(runtime),
        "runtime_payload_sha256": digest(payload),
        "context_sha256": {
            p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()
        },
        "source_locks": {
            name: digest(Path(__file__).with_name(name))
            for name in ("artifacts.json", "uv.lock", "pyproject.toml")
        },
        "base_image_id": (
            "sha256:676a930ab90762c2c32ef79642ad2293c18e5cea96381fc72af54e51fb3cd1c3"
        ),
    }
    (output / "build-inputs.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.runtime, args.output)), flush=True)


if __name__ == "__main__":
    main()
