#!/bin/bash
set -euo pipefail
# Reuse the pinned Flink 2.2.1 / JDK 17 runtime; no downloads or new dependencies.
runtime="${1:?Pass the existing m3-compatibility-002 runtime directory}"
target="${2:?Pass a new output directory}"
source_dir="$(cd "$(dirname "$0")" && pwd)/java"
test ! -e "$target"
mkdir -p "$target/classes"
"$runtime/jdk/jdk-17.0.20.1+1/bin/javac" --release 17 \
  -cp "$runtime/venv/lib/python3.12/site-packages/pyflink/lib/*" \
  -d "$target/classes" "$source_dir/PartitionTime.java"
"$runtime/jdk/jdk-17.0.20.1+1/bin/jar" --create \
  --date=2026-10-27T00:00:00Z --file "$target/partition-time.jar" \
  -C "$target/classes" .
"$runtime/venv/bin/python" - "$source_dir/PartitionTime.java" "$target" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

source, target = Path(sys.argv[1]), Path(sys.argv[2])
manifest = {
    "flink": "2.2.1", "java_release": 17,
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "jar_sha256": hashlib.sha256((target / "partition-time.jar").read_bytes()).hexdigest(),
}
(target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest))
PY
