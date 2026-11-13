"""Parent-run Windows candidate recipe; no downloads or package installation."""

import argparse
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from wheel_tools import exports, members, read, sha, wheel

SOURCES = (
    "confluent_kafka.c",
    "Producer.c",
    "Consumer.c",
    "ShareConsumer.c",
    "Metadata.c",
    "AdminTypes.c",
    "Admin.c",
)
HERE = Path(__file__).resolve().parent


def apply_patch(source: str, patch: str) -> str:
    """Apply exact unified context; refuse fuzz, unrelated paths and trailing edits."""
    lines = patch.splitlines(keepends=True)
    if lines[:2] != [
        "--- a/src/confluent_kafka/src/confluent_kafka.c\n",
        "+++ b/src/confluent_kafka/src/confluent_kafka.c\n",
    ]:
        raise ValueError("patch_paths")
    original = source.splitlines(keepends=True)
    result: list[str] = []
    position = 0
    index = 2
    while index < len(lines):
        match = re.fullmatch(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*\n", lines[index])
        if match is None:
            raise ValueError("patch_hunk")
        start, removed, _, added = map(int, match.groups())
        start -= 1
        if start < position:
            raise ValueError("patch_order")
        result.extend(original[position:start])
        position = start
        index += 1
        old_count = new_count = 0
        while index < len(lines) and not lines[index].startswith("@@"):
            line = lines[index]
            if line[0] in " -":
                if position >= len(original) or original[position] != line[1:]:
                    raise ValueError("patch_context")
                position += 1
                old_count += 1
            if line[0] in " +":
                result.append(line[1:])
                new_count += 1
            if line[0] not in " +-":
                raise ValueError("patch_line")
            index += 1
        if (old_count, new_count) != (removed, added):
            raise ValueError("patch_counts")
    return "".join(result + original[position:])


def verify_tree(archive: Path, tree: Path) -> None:
    """Verify compiler executable AND library tree against the pinned archive."""
    expected: set[str] = set()
    total = 0
    with tarfile.open(archive, "r:*") as tar:
        for item in tar:
            path = PurePosixPath(item.name)
            if path.is_absolute() or ".." in path.parts or "\\" in item.name:
                raise ValueError("archive_path")
            if item.isdir():
                continue
            if not item.isfile() or item.size > 256 * 1024 * 1024:
                raise ValueError("archive_member")
            total += item.size
            if total > 1024 * 1024 * 1024:
                raise ValueError("archive_bound")
            stream = tar.extractfile(item)
            if stream is None:
                raise ValueError("archive_file")
            with stream:
                data = stream.read(item.size + 1)
            if len(data) != item.size or read(tree / item.name) != data:
                raise ValueError("compiler_tree_mismatch")
            expected.add(item.name)
    actual = {str(p.relative_to(tree)) for p in tree.rglob("*") if not p.is_dir()}
    if actual != expected:
        raise ValueError("compiler_tree_inventory")


def load_pins(path: Path) -> dict[str, str]:
    """Validate local recipe pin mappings before using them as paths."""
    value: object = json.loads(read(path))
    if not isinstance(value, dict) or not value:
        raise ValueError("pin_mapping")
    result: dict[str, str] = {}
    for name, digest in value.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ValueError("pin_type")
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError("pin_path")
        if re.fullmatch("[0-9a-f]{64}", digest) is None:
            raise ValueError("pin_digest")
        result[name] = digest
    return result


def build(inputs: Path, python: Path, output: Path) -> None:
    """Own a fresh output tree; retain commands, compiler failures and artifacts."""
    inputs = inputs.absolute()
    python = python.absolute()
    output = output.absolute()
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("output_symlink")
    if output.is_relative_to(inputs) or output.is_relative_to(python):
        raise ValueError("output_overlaps_inputs")
    pins = load_pins(HERE / "pins.json")
    for name, digest in pins.items():
        if sha(read(inputs / name)) != digest:
            raise ValueError("input_checksum: " + name)
    python_pins = load_pins(HERE / "python-pins.json")
    for name, digest in python_pins.items():
        if sha(read(python / name)) != digest:
            raise ValueError("python_checksum: " + name)
    actual_headers = {
        str(p.relative_to(python))
        for p in (python / "include").rglob("*")
        if not p.is_dir()
    }
    if actual_headers != {name for name in python_pins if name.startswith("include/")}:
        raise ValueError("python_header_inventory")
    verify_tree(inputs / "zig.tar.xz", inputs / "zig")
    original = members(inputs / "confluent_kafka-2.16.0-cp313-cp313-win_amd64.whl")
    output.mkdir(exist_ok=False)
    (output / "OWNER").write_text("windows-uuid-fix recipe output v1\n")
    for name in (
        "source",
        "include/librdkafka",
        "cache",
        "global-cache",
        "tmp",
        "build",
        "wheel",
    ):
        (output / name).mkdir(parents=True, exist_ok=False)
    source = output / "source"
    upstream = inputs / "sdk-source/confluent_kafka-2.16.0/src/confluent_kafka/src"
    for name in pins:
        if name.startswith("sdk-source/"):
            (source / Path(name).name).write_bytes(read(inputs / name))
    # Require extracted compilation inputs to match the exact upstream sdist too.
    with tarfile.open(inputs / "confluent_kafka-2.16.0.tar.gz", "r:gz") as archive:
        for path in source.iterdir():
            member = archive.getmember(
                "confluent_kafka-2.16.0/src/confluent_kafka/src/" + path.name
            )
            if not member.isfile() or member.size > 128 * 1024 * 1024:
                raise ValueError("source_archive_member")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("source_archive_missing")
            with stream:
                if stream.read(member.size + 1) != read(upstream / path.name):
                    raise ValueError("source_archive_mismatch")
    target = source / "confluent_kafka.c"
    patch = read(HERE / "sdk-uuid-int64.patch")
    target.write_text(apply_patch(target.read_text(), patch.decode()))
    (output / "include/librdkafka/rdkafka.h").write_bytes(
        read(inputs / "librdkafka/rdkafka.h")
    )
    dlls = [
        k
        for k in original
        if k.endswith(".dll") and Path(k).name.lower().startswith("librdkafka")
    ]
    if len(dlls) != 1:
        raise ValueError("rdkafka_dll_count")
    dll = dlls[0]
    definition = output / "build/librdkafka.def"
    definition.write_text(
        "LIBRARY "
        + Path(dll).name
        + "\nEXPORTS\n"
        + "\n".join(exports(original[dll]))
        + "\n"
    )
    zig = inputs / "zig/zig-x86_64-linux-0.17.0/zig"
    # Exclude ambient compiler search paths and preload hooks from the recipe.
    env = {
        key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ
    }
    env.update(
        {
            "ZIG_LOCAL_CACHE_DIR": str(output / "cache"),
            "ZIG_GLOBAL_CACHE_DIR": str(output / "global-cache"),
            "TMPDIR": str(output / "tmp"),
            "TMP": str(output / "tmp"),
            "TEMP": str(output / "tmp"),
            "ZIG_LIB_DIR": str(zig.parent / "lib"),
        }
    )
    commands: list[list[str]] = []
    manifest: dict[str, object] = {
        "status": "prepared",
        "inputs": pins,
        "python_inputs": python_pins,
        "patch_sha256": sha(patch),
        "commands": commands,
        "source_sha256": {p.name: sha(read(p)) for p in source.iterdir()},
        "native_dll_sha256": {
            k: sha(v) for k, v in original.items() if k.endswith(".dll")
        },
    }

    def record() -> None:
        (output / "build-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )

    def run(args: list[str]) -> None:
        commands.append(args)
        record()
        with (output / "build/compiler.log").open("ab") as log:
            subprocess.run(
                args,
                cwd=output,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )

    try:
        run(
            [
                str(zig),
                "dlltool",
                "-m",
                "i386:x86-64",
                "-d",
                str(definition),
                "-l",
                str(output / "build/librdkafka.a"),
            ]
        )
        extension = output / "build/cimpl.cp313-win_amd64.pyd"
        flags = [
            "-target",
            "x86_64-windows-gnu",
            "-shared",
            "-O2",
            "-s",
            "-DNDEBUG",
            "-DMS_WIN64",
            "-DMS_WINDOWS",
            "-DWIN32",
            "-D_WIN32",
            "-D_WIN64",
            "-I" + str(python / "include"),
            "-I" + str(output / "include"),
            "-I" + str(source),
        ]
        run(
            [
                str(zig),
                "cc",
                *flags,
                *[str(source / name) for name in SOURCES],
                str(python / "libs/python313.lib"),
                str(output / "build/librdkafka.a"),
                "-o",
                str(extension),
            ]
        )
        destination = (
            output
            / "wheel/confluent_kafka-2.16.0+fleet.uuid1-cp313-cp313-win_amd64.whl"
        )
        manifest["wheel"] = wheel(original, read(extension), destination)
        manifest["status"] = "built_unvalidated"
    except BaseException:
        manifest["status"] = "failed"
        raise
    finally:
        record()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--python-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.inputs, args.python_root, args.output)


if __name__ == "__main__":
    main()
