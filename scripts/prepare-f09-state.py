"""Prepare a fresh restricted state delivery from the registered F09 ULog."""

import argparse
import json
from pathlib import Path

from runtime.flight_analytics.state import prepare


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = prepare(args.source, args.output)
    print(json.dumps({"status": "prepared", "records": manifest["records"]}))


if __name__ == "__main__":
    main()
