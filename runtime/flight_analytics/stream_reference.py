"""Write bounded offline F09 reference facts from a verified stream bundle."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import NoReturn

from runtime.flight_analytics.stream_prepare import load_bundle
from telemetry.conversion_contract import json_line
from telemetry.local_io import destination, publish_run, read_bounded, run_path
from telemetry.recording_processing import MAX_AGE_US, process_events
from ulog_integrity import F09_SOURCE_ID

PROFILE = "f09-recording-reference-v1"
MAX_BYTES = 64 * 1024 * 1024


class _Arguments(argparse.Namespace):
    bundle: Path
    output: Path
    max_age_us: int


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, "reference_arguments_invalid\n")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-age-us", type=int, default=1_000_000)
    args = parser.parse_args(argv, namespace=_Arguments())
    try:
        # Reserve a fresh destination before reading any bundle evidence.
        target = destination(args.output, args.output.name)
        if not 0 <= args.max_age_us <= MAX_AGE_US:
            raise ValueError("reference_age_limit")
        target.mkdir()
        manifest_path = run_path(args.bundle / "manifest.json", "manifest.json")
        input_manifest = read_bounded(manifest_path, MAX_BYTES)
        events, context, _ = load_bundle(args.bundle)
        if read_bounded(manifest_path, MAX_BYTES) != input_manifest:
            raise ValueError("reference_bundle_changed")
        facts = process_events(events, context, max_age_us=args.max_age_us)
        digest = hashlib.sha256()
        size = 0
        with (target / "facts.jsonl").open("xb") as handle:
            for fact in facts:
                line = json_line(fact)
                size += len(line)
                if size > MAX_BYTES:
                    raise ValueError("reference_byte_limit")
                handle.write(line)
                digest.update(line)
        manifest: dict[str, object] = {
            "profile": PROFILE,
            "source_id": F09_SOURCE_ID,
            "run_id": context["run_id"],
            "facts": len(facts),
            "max_age_us": args.max_age_us,
            "files": {"facts.jsonl": {"bytes": size, "sha256": digest.hexdigest()}},
            "input_bundle_manifest_sha256": hashlib.sha256(input_manifest).hexdigest(),
            "limitations": [
                "offline ordered file replay; no Kafka/Flink/archive/SQL integration",
                "exact F09 research source; physical producer unverified",
                "common native boot clock assumed; no synchronization proof",
                "GPS receiver UTC is display time; battery UTC anchor is synthetic",
                "gap masks do not establish source completeness or lost duration",
                "no physical phases, distance or current aircraft freshness inferred",
                "completion manifest written last; no crash durability guarantee",
            ],
        }
        pending = target / ".manifest.pending"
        with pending.open("xb") as handle:
            handle.write(json_line(manifest))
        publish_run(pending, target / "manifest.json")
    except (ValueError, OSError, KeyError, TypeError, OverflowError):
        # Fixed text also protects paths or payloads embedded in upstream errors.
        print(
            json.dumps({"status": "failed", "reason": "reference_failed"}),
            file=sys.stderr,
        )
        return 2
    print(json.dumps({"status": "completed", "facts": len(facts)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
