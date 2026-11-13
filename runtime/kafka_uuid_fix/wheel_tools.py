"""Bounded PE exports and wheel rewriting; standard library only."""

import base64
import csv
import hashlib
import io
import struct
import zipfile
from pathlib import Path, PurePosixPath

LIMIT = 256 * 1024 * 1024


def read(path: Path) -> bytes:
    """Read one bounded regular file, refusing symlinks in its ancestry."""
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError("regular_file_required")
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("file_bound")
    return data


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def members(path: Path) -> dict[str, bytes]:
    """Reject duplicate, escaping, oversized and symlink archive members."""
    result: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(read(path))) as archive:
        total = 0
        for item in archive.infolist():
            name = PurePosixPath(item.filename)
            total += item.file_size
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in item.filename
                or item.filename in result
                or total > LIMIT
                or (item.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("unsafe_wheel")
            if not item.is_dir():
                result[item.filename] = archive.read(item)
    return result


def exports(data: bytes) -> list[str]:
    """Read named exports from an x86-64 PE32+ DLL without executing it."""

    def u32(offset: int) -> int:
        return int(struct.unpack_from("<I", data, offset)[0])

    pe = u32(0x3C)
    if data[:2] != b"MZ" or data[pe : pe + 6] != b"PE\0\0d\x86":
        raise ValueError("pe_machine")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x20B:
        raise ValueError("pe_format")
    sections = opt + struct.unpack_from("<H", data, pe + 20)[0]

    def offset(rva: int) -> int:
        for index in range(count):
            section = sections + 40 * index
            size, address, rawsize, raw = struct.unpack_from("<IIII", data, section + 8)
            if address <= rva < address + max(size, rawsize):
                result = raw + rva - address
                if rva - address >= rawsize or result >= len(data):
                    break
                return int(result)
        raise ValueError("pe_rva")

    directory = offset(u32(opt + 112))
    names = u32(directory + 24)
    if not 0 < names < 100000:
        raise ValueError("pe_export_bound")
    table = offset(u32(directory + 32))
    result: list[str] = []
    for index in range(names):
        start = offset(u32(table + 4 * index))
        end = data.find(b"\0", start, start + 512)
        if end < 0:
            raise ValueError("pe_export_name")
        name = data[start:end].decode("ascii")
        if not name or any(
            c not in "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            for c in name
        ):
            raise ValueError("pe_export_name")
        result.append(name)
    return sorted(result)


def wheel(
    original: dict[str, bytes], extension: bytes, output: Path
) -> dict[str, object]:
    """Keep original package and DLL bytes, replacing only declared members."""
    old = "confluent_kafka-2.16.0.dist-info/"
    new = "confluent_kafka-2.16.0+fleet.uuid1.dist-info/"
    result = {k.replace(old, new): v for k, v in original.items()}
    candidates = [
        k
        for k in result
        if k.startswith("confluent_kafka/cimpl.") and k.endswith(".pyd")
    ]
    if len(candidates) != 1:
        raise ValueError("extension_count")
    result[candidates[0]] = extension
    metadata = result[new + "METADATA"]
    version_lines = [
        line
        for line in metadata.splitlines(keepends=True)
        if line.startswith(b"Version:")
    ]
    if (
        len(version_lines) != 1
        or version_lines[0].rstrip(b"\r\n") != b"Version: 2.16.0"
    ):
        raise ValueError("metadata_version")
    result[new + "METADATA"] = metadata.replace(
        version_lines[0], version_lines[0].replace(b"2.16.0", b"2.16.0+fleet.uuid1"), 1
    )
    tags = [
        line
        for line in result[new + "WHEEL"].decode().splitlines()
        if line.startswith("Tag:")
    ]
    if tags != ["Tag: cp313-cp313-win_amd64"]:
        raise ValueError("wheel_tag")
    record = new + "RECORD"
    result.pop(record)
    rows = [
        [
            k,
            "sha256="
            + base64.urlsafe_b64encode(hashlib.sha256(v).digest()).decode().rstrip("="),
            str(len(v)),
        ]
        for k, v in sorted(result.items())
    ]
    rows.append([record, "", ""])
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    result[record] = buffer.getvalue().encode()
    with (
        output.open("xb") as stream,
        zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive,
    ):
        for key, value in sorted(result.items()):
            info = zipfile.ZipInfo(key, (2026, 10, 24, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, value)
    return {
        "changed_members": [
            k
            for k in sorted(set(original) | set(result))
            if original.get(k) != result.get(k)
        ],
        "members": {k: sha(v) for k, v in sorted(result.items())},
        "sha256": sha(read(output)),
    }
