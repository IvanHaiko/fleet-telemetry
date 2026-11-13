#!/usr/bin/env python3
"""Offline, pinned enumerator-only local backport; no dependency resolution."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import struct
import subprocess
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import TypedDict, cast

BASE = "org/apache/flink/connector/kafka/source/enumerator/KafkaSourceEnumerator"
HERE = Path(__file__).resolve().parent


class SourcePin(TypedDict):
    url: str
    sha256: str


class Pins(TypedDict):
    source: SourcePin
    inputs: dict[str, str]
    classpath: list[str]
    major: int
    jar: str
    javac: str
    javap: str
    java: str
    guard: str
    probe_sha256: str


class Arguments(argparse.Namespace):
    source: Path
    runtime: Path
    output: Path


def fresh_output(path: Path, source: Path, runtime: Path) -> Path:
    """Check an explicit destination without creating or deleting anything."""
    if not path.is_absolute():
        raise ValueError("output must be absolute")
    parent = path.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("output parent must be an existing directory")
    output = parent / path.name
    if output.exists() or output.is_symlink():
        raise ValueError("output must be absent")
    for protected in (runtime, source.parent, HERE):
        if output.is_relative_to(protected) or protected.is_relative_to(output):
            raise ValueError("output overlaps runtime, source inputs or proposed code")
    return output


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(args: list[str]) -> str:
    return subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
    ).stdout


def entries(path: Path) -> dict[str, zipfile.ZipInfo]:
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("archive too large")
    with zipfile.ZipFile(path) as jar:
        infos = jar.infolist()
        if len(infos) > 40000 or sum(i.file_size for i in infos) > 256 * 1024 * 1024:
            raise ValueError("archive expansion limit")
        names = [i.filename for i in infos]
        if len(set(names)) != len(names):
            raise ValueError("duplicate archive entries")
        for i in infos:
            p = PurePosixPath(i.filename)
            if (
                p.is_absolute()
                or ".." in p.parts
                or "\\" in i.filename
                or i.file_size > 32 * 1024 * 1024
            ):
                raise ValueError("unsafe archive entry")
            if i.flag_bits & 1 or (
                i.filename.upper().startswith("META-INF/")
                and (
                    i.filename.upper().endswith((".SF", ".RSA", ".DSA", ".EC"))
                    or PurePosixPath(i.filename).name.upper().startswith("SIG-")
                )
            ):
                raise ValueError("encrypted or signed archive")
        manifest = jar.read("META-INF/MANIFEST.MF").upper()
        if b"-DIGEST" in manifest or b"SIGNATURE-VERSION:" in manifest:
            raise ValueError("signing manifest surprise")
        return dict(zip(names, infos, strict=True))


def metadata(i: zipfile.ZipInfo) -> tuple[object, ...]:
    return (
        i.filename,
        i.date_time,
        i.compress_type,
        i.comment,
        i.extra,
        i.create_system,
        i.create_version,
        i.extract_version,
        i.reserved,
        i.flag_bits,
        i.volume,
        i.internal_attr,
        i.external_attr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help=(
            "absolute fresh directory with an existing parent "
            "outside runtime, source inputs and code"
        ),
    )
    args = parser.parse_args(namespace=Arguments())
    # Trusted repository configuration: type every consumed JSON field.
    pins = cast(Pins, json.loads((HERE / "connector-backport.json").read_text()))
    source, runtime = (
        args.source.resolve(strict=True),
        args.runtime.resolve(strict=True),
    )
    output = fresh_output(args.output, source, runtime)
    if source.stat().st_size > 100000 or digest(source) != pins["source"]["sha256"]:
        raise ValueError("released source hash mismatch")
    if (
        pins["classpath"] != sorted(set(pins["classpath"]))
        or len(pins["classpath"]) > 32
    ):
        raise ValueError("unbounded or unsorted classpath")
    paths = {name: runtime / name for name in pins["inputs"]}
    for name, path in paths.items():
        if (
            not path.resolve(strict=True).is_relative_to(runtime)
            or digest(path) != pins["inputs"][name]
        ):
            raise ValueError("installed input hash mismatch: " + name)
    jar = runtime / pins["jar"]
    original = entries(jar)
    allowed = sorted(
        n
        for n in original
        if n == BASE + ".class" or (n.startswith(BASE + "$") and n.endswith(".class"))
    )
    with zipfile.ZipFile(jar) as z:
        majors = {struct.unpack(">H", z.read(n)[6:8])[0] for n in allowed}
    if majors != {pins["major"]}:
        raise ValueError("class target mismatch")
    text = source.read_text()
    old = "        if (partitionChange.isEmpty()) {"
    if text.count(old) != 1:
        raise ValueError("guard mismatch")
    patched = text.replace(old, pins["guard"])
    output.mkdir()
    (output / "production.diff").write_text(
        "".join(
            difflib.unified_diff(
                text.splitlines(True),
                patched.splitlines(True),
                fromfile="v5.0.0/KafkaSourceEnumerator.java",
                tofile="backport/KafkaSourceEnumerator.java",
            )
        )
    )
    relocated = patched.replace(
        "import org.apache.kafka.",
        "import org.apache.flink.kafka.shaded.org.apache.kafka.",
    )
    (output / "relocation.diff").write_text(
        "".join(
            difflib.unified_diff(
                patched.splitlines(True),
                relocated.splitlines(True),
                fromfile="backport",
                tofile="sql-shaded",
            )
        )
    )
    javac = str(runtime / pins["javac"])
    javap = str(runtime / pins["javap"])
    cp = [str(runtime / p) for p in pins["classpath"]]
    records: dict[str, object] = {
        "compiler_version": run([javac, "-version"]),
        "inputs": pins["inputs"],
        "classpath": cp,
    }
    jars: list[Path] = []
    for build in ("build-a", "build-b"):
        work = output / build
        work.mkdir()
        src = work / "KafkaSourceEnumerator.java"
        src.write_text(relocated)
        classes = work / "classes"
        classes.mkdir()
        command = [
            javac,
            "-proc:none",
            "--release",
            str(pins["major"] - 44),
            "-classpath",
            os.pathsep.join(cp),
            "-d",
            str(classes),
            str(src),
        ]
        run(command)
        compiled = {
            p.relative_to(classes).as_posix(): p for p in classes.rglob("*.class")
        }
        if sorted(compiled) != allowed:
            raise ValueError("compiled class allowlist mismatch")
        for name, path in compiled.items():
            if struct.unpack(">H", path.read_bytes()[6:8])[0] != pins["major"]:
                raise ValueError("wrong compiled major")
            cls = name[:-6].replace("/", ".")
            before = run([javap, "-p", "-s", "-classpath", str(jar), cls])
            after = run([javap, "-p", "-s", "-classpath", str(classes), cls])
            if before != after:
                (work / "abi-failure.txt").write_text(before + "\nAFTER\n" + after)
                raise ValueError("ABI mismatch: " + cls)
        target = work / "connector-local-backport.jar"
        # Retain untouched local records and original central metadata.
        raw = jar.read_bytes()
        with zipfile.ZipFile(jar) as inp, target.open("wb") as out:
            infos = inp.infolist()
            central_pos = inp.start_dir
            central_records: list[bytes] = []
            for index, info in enumerate(infos):
                offset = out.tell()
                end = (
                    infos[index + 1].header_offset
                    if index + 1 < len(infos)
                    else inp.start_dir
                )
                local = raw[info.header_offset : end]
                crc, size, compressed_size = (
                    info.CRC,
                    info.file_size,
                    info.compress_size,
                )
                if info.filename in compiled:
                    content = compiled[info.filename].read_bytes()
                    if info.compress_type != zipfile.ZIP_DEFLATED:
                        raise ValueError("unexpected class compression")
                    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
                    compressed = compressor.compress(content) + compressor.flush()
                    crc, size, compressed_size = (
                        zlib.crc32(content),
                        len(content),
                        len(compressed),
                    )
                    name_len, extra_len = struct.unpack_from("<HH", local, 26)
                    header = bytearray(local[: 30 + name_len + extra_len])
                    if info.flag_bits & 8:
                        struct.pack_into("<III", header, 14, 0, 0, 0)
                        tail = struct.pack(
                            "<IIII", 0x08074B50, crc, compressed_size, size
                        )
                    else:
                        struct.pack_into("<III", header, 14, crc, compressed_size, size)
                        tail = b""
                    local = bytes(header) + compressed + tail
                out.write(local)
                n, e, c = struct.unpack_from("<HHH", raw, central_pos + 28)
                record = bytearray(raw[central_pos : central_pos + 46 + n + e + c])
                struct.pack_into("<III", record, 16, crc, compressed_size, size)
                struct.pack_into("<I", record, 42, offset)
                central_records.append(bytes(record))
                central_pos += len(record)
            start = out.tell()
            for central_record in central_records:
                out.write(central_record)
            length = out.tell() - start
            out.write(
                struct.pack(
                    "<IHHHHIIH",
                    0x06054B50,
                    0,
                    0,
                    len(infos),
                    len(infos),
                    length,
                    start,
                    len(inp.comment),
                )
                + inp.comment
            )
        rebuilt = entries(target)
        if list(original) != list(rebuilt):
            raise ValueError("archive inventory mismatch")
        changed: list[str] = []
        with zipfile.ZipFile(jar) as a, zipfile.ZipFile(target) as b:
            if a.comment != b.comment:
                raise ValueError("archive comment mismatch")
            for name in original:
                if metadata(original[name]) != metadata(rebuilt[name]):
                    raise ValueError("entry metadata mismatch: " + name)
                if a.read(name) != b.read(name):
                    changed.append(name)
        if set(changed) - set(allowed) or BASE + ".class" not in changed:
            raise ValueError("changed entry allowlist failure")
        records[build] = {
            "command": command,
            "changed_entries": changed,
            "class_sha256": {n: digest(p) for n, p in compiled.items()},
            "jar_sha256": digest(target),
            "abi": "all private/public descriptors equal",
        }
        jars.append(target)
    if digest(jars[0]) != digest(jars[1]):
        raise ValueError("nondeterministic output")
    # Recheck every installed input after compilation and archive verification.
    if any(digest(paths[n]) != h for n, h in pins["inputs"].items()):
        raise ValueError("original input changed")
    probe = HERE / "EnumeratorGuardProbe.java"
    if digest(probe) != pins["probe_sha256"]:
        raise ValueError("probe hash mismatch")
    probe_classes = output / "probe-classes"
    probe_classes.mkdir()
    run(
        [
            javac,
            "-proc:none",
            "--release",
            str(pins["major"] - 44),
            "-classpath",
            os.pathsep.join(cp),
            "-d",
            str(probe_classes),
            str(probe),
        ]
    )
    java = str(runtime / pins["java"])
    probe_results: dict[str, object] = {}
    for label, connector in [("stock", jar), ("patched", jars[0])]:
        probe_cp = [str(probe_classes), str(connector)] + [
            p for p in cp if p != str(jar)
        ]
        command = [
            java,
            "-classpath",
            os.pathsep.join(probe_cp),
            "EnumeratorGuardProbe",
        ]
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        probe_results[label] = {
            "command": command,
            "exit": result.returncode,
            "output": result.stdout,
        }
        (output / (label + "-probe.txt")).write_text(result.stdout)
        expected = (
            "restoredBounded=false emptyFreshBounded=false"
            if label == "stock"
            else "restoredBounded=true emptyFreshBounded=true"
        )
        if (
            expected not in result.stdout
            or (label == "patched" and result.returncode != 0)
            or (
                label == "stock"
                and (
                    result.returncode == 0
                    or "bounded empty-change completion missing" not in result.stdout
                )
            )
        ):
            raise ValueError("unexpected probe outcome: " + label)
    records["probes"] = probe_results
    records["deterministic"] = True
    (output / "build-record.json").write_text(json.dumps(records, indent=2) + "\n")
    print(str(output / "build-record.json"))


if __name__ == "__main__":
    main()
