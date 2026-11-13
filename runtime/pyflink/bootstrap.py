"""Prepare pinned Linux runtimes and install only the separate frozen profile."""

import argparse
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import cast

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MARKER = "pyflink-compatibility-v1\n"


@dataclass(frozen=True)
class Artifact:
    filename: str
    url: str
    sha256: str


def obj(value: object) -> dict[str, object]:
    """Validate JSON object keys before reading runtime configuration."""
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ValueError("invalid_runtime_configuration")
    return cast(dict[str, object], value)


def text(value: object) -> str:
    """Require a nonempty configuration string."""
    if not isinstance(value, str) or not value:
        raise ValueError("invalid_runtime_configuration")
    return value


def sha256(path: Path) -> str:
    """Hash a complete file without loading an archive into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def owned_path(path: Path) -> Path:
    """Confine writes to project scratch or its dedicated native Linux runtime."""
    result = path.resolve()
    roots = (
        (ROOT / ".local-discovery").resolve(),
        (Path.home() / ".local/share/fleet-telemetry/pyflink").resolve(),
    )
    if not any(result != root and result.is_relative_to(root) for root in roots):
        raise ValueError("project_local_directory_required")
    return result


def artifacts() -> dict[str, Artifact]:
    """Read reviewed archive URLs and SHA-256 pins."""
    raw: object = json.loads((HERE / "artifacts.json").read_bytes())
    rows = obj(obj(raw)["artifacts"])
    if set(rows) != {"python", "jdk", "uv", "kafka_sql"}:
        raise ValueError("unexpected_artifact_set")
    result = {}
    for name, value in rows.items():
        row = obj(value)
        filename, url, digest = (text(row[k]) for k in ("filename", "url", "sha256"))
        if (
            Path(filename).name != filename
            or filename in {".", ".."}
            or not url.startswith("https://")
            or re.fullmatch("[0-9a-f]{64}", digest) is None
        ):
            raise ValueError("invalid_artifact_pin")
        result[name] = Artifact(filename, url, digest)
    return result


def cached_artifact(row: Artifact, cache: Path, offline: bool) -> Path:
    """Refuse corrupt cached bytes; never replace an existing archive."""
    path = cache / row.filename
    if not path.exists():
        if offline:
            raise ValueError("offline_archive_missing")
        with (
            urllib.request.urlopen(row.url, timeout=60) as response,
            path.open("xb") as out,
        ):
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 256 * 1024 * 1024:
                    raise ValueError("archive_size_limit")
                out.write(chunk)
    if sha256(path) != row.sha256:
        raise ValueError("archive_checksum_mismatch")
    return path


def paths(directory: Path) -> dict[str, Path]:
    """Resolve only the expected executables from the owned runtime tree."""
    if (directory / ".pyflink-owned").read_text() != MARKER:
        raise ValueError("owned_runtime_required")
    java = list((directory / "jdk").glob("*/bin/java"))
    if len(java) != 1:
        raise ValueError("unexpected_jdk_layout")
    result = {
        "python": directory / "python/python/bin/python3.12",
        "java_home": java[0].parents[1],
        "uv": directory / "uv/uv-x86_64-unknown-linux-gnu/uv",
        "venv": directory / "venv",
        "connector": directory / artifacts()["kafka_sql"].filename,
    }
    if any(not result[k].is_file() for k in ("python", "uv")):
        raise ValueError("runtime_executable_missing")
    return result


def environment(directory: Path) -> dict[str, str]:
    """Keep tool caches, interpreter selection and Java local to this process."""
    selected = paths(directory)
    for name in ("tmp", "cache"):
        (directory / name).mkdir(exist_ok=True)
    result = dict(
        os.environ,
        JAVA_HOME=str(selected["java_home"]),
        UV_PROJECT_ENVIRONMENT=str(selected["venv"]),
        UV_CACHE_DIR=str(directory / "cache"),
        UV_LINK_MODE="copy",
        UV_PYTHON_DOWNLOADS="never",
        UV_DEFAULT_INDEX="https://pypi.org/simple",
        TMPDIR=str(directory / "tmp"),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        PYTHONPATH=str(HERE),
    )
    for key in ("PYTHONHOME", "FLINK_HOME", "FLINK_CONF_DIR"):
        result.pop(key, None)
    return result


def command(
    args: list[str], env: dict[str, str], cwd: Path, timeout: int = 600
) -> dict[str, object]:
    """Retain exits and stop an owned Linux process group on timeout."""
    if sys.platform != "linux":
        raise ValueError("linux_execution_required")
    child = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=10)
    except KeyboardInterrupt:
        os.killpg(child.pid, signal.SIGKILL)
        child.communicate(timeout=10)
        raise
    try:
        os.killpg(child.pid, 0)
    except ProcessLookupError:
        ended = True
    else:
        os.killpg(child.pid, signal.SIGKILL)
        ended = False
    return {
        "command": args,
        "exit_code": child.returncode,
        "timed_out": timed_out,
        "owned_process_group_ended": ended,
        "stdout": stdout,
        "stderr": stderr,
    }


def prepare(directory: Path, cache: Path, offline: bool) -> None:
    """Create a fresh tree only after all pinned archives verify."""
    cache.mkdir(parents=True, exist_ok=True)
    rows = artifacts()
    sources = {k: cached_artifact(v, cache, offline) for k, v in rows.items()}
    directory.mkdir(parents=True, exist_ok=False)
    (directory / ".pyflink-owned").write_text(MARKER)
    for name in ("python", "jdk", "uv"):
        destination = directory / name
        destination.mkdir()
        with tarfile.open(sources[name]) as archive:
            archive.extractall(destination, filter="data")
    connector = directory / rows["kafka_sql"].filename
    with connector.open("xb") as out:
        out.write(sources["kafka_sql"].read_bytes())


def install(directory: Path, offline: bool) -> dict[str, object]:
    """Install a complete existing lock; never resolve or change its versions."""
    selected = paths(directory)
    env = environment(directory)
    lock = sha256(HERE / "uv.lock")
    args = [
        str(selected["uv"]),
        "sync",
        "--frozen",
        "--project",
        str(HERE),
        "--python",
        str(selected["python"]),
        "--no-python-downloads",
    ]
    if offline:
        args.append("--offline")
    validation = command(
        [
            str(selected["uv"]),
            "lock",
            "--check",
            "--offline",
            "--project",
            str(HERE),
            "--python",
            str(selected["python"]),
            "--no-python-downloads",
        ],
        env,
        HERE,
    )
    if (
        validation["exit_code"] != 0
        or validation["timed_out"]
        or not validation["owned_process_group_ended"]
    ):
        result = dict(validation, phase="lock_validation")
    else:
        result = command(args, env, HERE)
    result["lock_validation"] = validation
    attempt = len(list(directory.glob("install-*.json"))) + 1
    result["lock_unchanged"] = lock == sha256(HERE / "uv.lock")
    with (directory / f"install-{attempt}.json").open("x") as out:
        json.dump(result, out, indent=2)
    return result


def main() -> int:
    """Require explicit prepare or install; refuse unsupported host platforms."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "install"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--offline", action="store_true")
    options = parser.parse_args()
    if (
        sys.platform != "linux"
        or platform.machine() != "x86_64"
        or sys.version_info < (3, 12)
    ):
        parser.error("Bootstrap requires Linux x86-64 and Python 3.12 or newer.")
    try:
        directory = owned_path(options.directory)
        if options.phase == "prepare":
            if options.cache is None:
                parser.error("prepare requires --cache")
            prepare(directory, owned_path(options.cache), options.offline)
            print(json.dumps({"status": "runtime_archives_prepared"}))
            return 0
        result = install(directory, options.offline)
        print(json.dumps(result))
        return (
            0
            if (
                result["exit_code"] == 0
                and not result["timed_out"]
                and result["owned_process_group_ended"]
                and result["lock_unchanged"]
            )
            else 2
        )
    except (OSError, ValueError, tarfile.TarError):
        print(json.dumps({"status": "failed", "reason": "runtime_setup_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
