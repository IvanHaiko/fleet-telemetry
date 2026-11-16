"""Sample container CPU/memory and volume sizes of the recording profile.

Read-only observation through the Docker CLI: it starts, stops and changes
nothing. Each line of the output JSONL is one timestamped sample. Container
stats are taken every interval; volume sizes once per minute because
`docker system df -v` is comparatively expensive. Stop with Ctrl+C.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

PROJECT = "fleet-recording-local"


def docker(*args: str) -> str:
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True, timeout=60
    ).stdout


def containers() -> list[str]:
    output = docker(
        "ps", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"
    )
    return output.split()


def stats() -> list[dict[str, object]]:
    ids = containers()
    if not ids:
        return []
    lines = docker("stats", "--no-stream", "--format", "{{json .}}", *ids)
    return [json.loads(line) for line in lines.splitlines() if line.strip()]


def volumes() -> list[dict[str, object]]:
    report = json.loads(docker("system", "df", "-v", "--format", "{{json .}}"))
    return [
        {"name": volume.get("Name"), "size": volume.get("Size")}
        for volume in report.get("Volumes") or []
        if str(volume.get("Name", "")).startswith(PROJECT + "_")
    ]


def sample(output: Path, interval: float, duration: float) -> int:
    started = time.monotonic()
    last_volumes = -60.0
    count = 0
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        while time.monotonic() - started < duration:
            now = time.monotonic()
            row: dict[str, object] = {"written_ms": time.time_ns() // 1_000_000}
            try:
                row["containers"] = stats()
                if now - last_volumes >= 60:
                    row["volumes"] = volumes()
                    last_volumes = now
            except (subprocess.SubprocessError, OSError, ValueError) as error:
                # A missed sample stays visible as an explicit gap.
                row["error"] = type(error).__name__
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            count += 1
            time.sleep(max(0.0, interval - (time.monotonic() - now)))
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--duration", type=float, default=4 * 3600.0)
    args = parser.parse_args(argv)
    if not 1 <= args.interval <= 300 or not 1 <= args.duration <= 24 * 3600:
        print(json.dumps({"status": "failed", "category": "sample_bounds"}))
        return 2
    try:
        count = sample(args.output, args.interval, args.duration)
    except KeyboardInterrupt:
        print(json.dumps({"status": "stopped"}))
        return 0
    print(json.dumps({"status": "finished", "samples": count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
