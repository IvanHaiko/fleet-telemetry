"""Linux bubblewrap profile and fresh source-only production closure."""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from runtime.archive_runtime.config import Config, directory, regular
from telemetry.archive_codec import _fail

ROOT = Path(__file__).resolve().parents[2]


def prerequisite() -> None:
    if (
        sys.platform != "linux"
        or sys.version_info[:2] != (3, 13)
        or platform.python_implementation() != "CPython"
        or platform.machine().lower() != "x86_64"
    ):
        _fail("unsupported_profile", "worker")
    try:
        result = subprocess.run(
            ["/usr/bin/bwrap", "--version"],
            capture_output=True,
            timeout=2,
            env={},
        )
    except (OSError, subprocess.TimeoutExpired):
        _fail("unsupported_profile", "worker")
    if result.returncode != 0 or result.stdout.strip() != b"bubblewrap 0.11.1":
        _fail("unsupported_profile", "worker")


def admit_space(parent: Path, estimate: int = 512 * 1024 * 1024) -> None:
    if shutil.disk_usage(directory(parent)).free - estimate < 1024**3:
        _fail("limit_exceeded", "storage")


def hidden_mounts(config: Config, code: Path, protected: Path) -> None:
    mounts = (
        code,
        config.python_root,
        *config.sdk_paths,
        *(
            Path(name).resolve()
            for name in ("/usr/lib", "/usr/lib64", "/lib", "/lib64")
        ),
    )
    if any(protected.is_relative_to(mount) for mount in mounts):
        _fail("unsupported_profile", "path")


def closure(parent: Path) -> Path:
    directory(parent)
    files = list(ROOT.glob("*.py"))
    for relative in (
        "telemetry",
        "runtime/s3",
        "runtime/kafka_archive",
        "runtime/archive_runtime",
    ):
        files.extend((ROOT / relative).glob("*.py"))
    estimate = sum(regular(path).stat().st_size for path in files)
    # Include graph, export, IPC, restored observations and filesystem overhead.
    admit_space(parent, estimate * 2 + 512 * 1024 * 1024)
    stage = Path(tempfile.mkdtemp(prefix="archive-runtime-", dir=parent))
    code = stage / "code"
    code.mkdir()
    for source in files:
        target = code / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o444)
    return code


def command(
    config: Config,
    code: Path,
    *,
    offline: bool = False,
    stage: Path | None = None,
    output_parent: Path | None = None,
) -> list[str]:
    args = [
        "/usr/bin/bwrap",
        # Worker PID 1 owns namespace lifetime without an extra namespace init helper.
        "--as-pid-1",
        "--die-with-parent",
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--disable-userns",
        "--cap-drop",
        "ALL",
        "--clearenv",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--size",
        str(16 * 1024 * 1024),
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        str(code),
        "/code",
        "--chdir",
        "/code",
    ]
    if offline:
        args.append("--unshare-net")
    sdks = () if offline else config.sdk_paths
    mounts = (config.python_root, *sdks)
    for mount in mounts:
        directory(mount)
        # No operator capability may expose the checkout or its parent.
        if ROOT.is_relative_to(mount) or mount.is_relative_to(ROOT):
            _fail("unsupported_profile", "path")
        args.extend(["--ro-bind", str(mount), str(mount)])
    for name in ("/usr/lib", "/usr/lib64", "/lib", "/lib64"):
        path = Path(name)
        if path.is_symlink():
            args.extend(["--symlink", os.readlink(path), name])
        elif path.is_dir():
            args.extend(["--ro-bind", name, name])
    if stage is not None:
        args.extend(["--ro-bind" if offline else "--bind", str(stage), "/stage"])
    if output_parent is not None:
        directory(output_parent)
        if ROOT.is_relative_to(output_parent) or code.is_relative_to(output_parent):
            _fail("unsupported_profile", "path")
        args.extend(["--bind", str(output_parent), "/output"])
    args.extend(["--remount-ro", "/"])
    pythonpath = ":".join(["/code", *(str(path) for path in sdks)])
    args.extend(
        [
            "--setenv",
            "PYTHONPATH",
            pythonpath,
            "--setenv",
            "MALLOC_ARENA_MAX",
            "2",
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
            "--setenv",
            "TMPDIR",
            "/tmp",
            "--",
            str(config.python_root / "bin/python3.13"),
            "-B",
            "-m",
            "runtime.archive_runtime.worker",
        ]
    )
    return args
