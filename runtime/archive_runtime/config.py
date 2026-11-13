"""Pure strict configuration and local path admission; no client construction."""

import json
import math
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from runtime.s3.boto_transport import _bucket, _endpoint, _refuse_ambient_aws
from telemetry.archive_codec import _fail
from telemetry.archive_documents import mapping
from telemetry.local_io import read_bounded


@dataclass(frozen=True)
class Credentials:
    access_key: str
    secret_key: str


@dataclass(frozen=True)
class Config:
    python_root: Path
    sdk_paths: tuple[Path, ...]
    endpoint: str
    region: str
    bucket: str
    reader: Credentials
    writer: Credentials | None


def directory(path: Path) -> Path:
    if ".." in path.parts:
        _fail("invalid_format", "path")
    absolute = Path(os.path.abspath(path))
    for item in (absolute, *absolute.parents):
        if item.is_symlink() or item.is_junction() or not item.is_dir():
            _fail("invalid_format", "path")
    return absolute


def regular(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    directory(absolute.parent)
    if (
        ".." in path.parts
        or absolute.is_symlink()
        or not stat.S_ISREG(absolute.stat().st_mode)
    ):
        _fail("invalid_format", "path")
    return absolute


def duration(value: float) -> float:
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0 < value <= 120
    ):
        _fail("invalid_format", "timeout")
    return float(value)


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            _fail("invalid_format", "json")
        result[key] = value
    return result


def _constant(value: str) -> object:
    _fail("invalid_format", "json")


def strict_json(body: bytes, maximum: int) -> dict[str, object]:
    if type(body) is not bytes or not 0 < len(body) <= maximum:
        _fail("limit_exceeded", "json")
    try:
        value: object = json.loads(
            body, object_pairs_hook=_pairs, parse_constant=_constant
        )
    except (ValueError, UnicodeError, RecursionError):
        _fail("invalid_format", "json")
    if not isinstance(value, dict):
        _fail("invalid_format", "json")
    pending: list[object] = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(cast(dict[str, object], item).values())
        elif isinstance(item, list):
            pending.extend(cast(list[object], item))
        elif isinstance(item, float) and not math.isfinite(item):
            _fail("invalid_format", "json")
    return cast(dict[str, object], value)


def token(value: object) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= 512
        or any(ord(char) < 33 or ord(char) > 126 for char in value)
    ):
        _fail("invalid_format", "config")
    return value


def _credentials(value: object) -> Credentials:
    spec = mapping(value, {"access_key", "secret_key"})
    return Credentials(token(spec["access_key"]), token(spec["secret_key"]))


def load_config(path: Path, *, publish: bool) -> Config:
    _refuse_ambient_aws()
    spec = mapping(
        strict_json(read_bounded(regular(path), 65536), 65536),
        {
            "runtime_version",
            "python_root",
            "sdk_paths",
            "storage",
        },
    )
    if spec["runtime_version"] != "local-archive-runtime-v1":
        _fail("unsupported_profile", "config")
    root = Path(token(spec["python_root"]))
    if not root.is_absolute():
        _fail("invalid_format", "path")
    directory(root)
    regular(root / "bin/python3.13")
    paths = spec["sdk_paths"]
    if type(paths) is not list or not 1 <= len(paths) <= 8:
        _fail("invalid_format", "config")
    sdks: list[Path] = []
    for raw in cast(list[object], paths):
        sdk = Path(token(raw))
        if not sdk.is_absolute() or sdk in sdks:
            _fail("invalid_format", "path")
        sdks.append(directory(sdk))
    fields = {"endpoint", "region", "bucket", "reader"}
    storage = mapping(spec["storage"], fields | ({"writer"} if publish else set()))
    endpoint, region, bucket = (
        token(storage[key]) for key in ("endpoint", "region", "bucket")
    )
    _endpoint(endpoint)
    _bucket(bucket)
    reader = _credentials(storage["reader"])
    writer = _credentials(storage["writer"]) if publish else None
    if writer is not None and (
        writer.access_key == reader.access_key or writer.secret_key == reader.secret_key
    ):
        _fail("unsupported_profile", "credentials")
    return Config(root, tuple(sdks), endpoint, region, bucket, reader, writer)
