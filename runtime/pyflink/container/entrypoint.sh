#!/bin/bash
set -euo pipefail
case "${1:-}" in
  preflight)
    exec "$FLEET_RUNTIME/venv/bin/python" -B /opt/m3/preflight.py
    ;;
  jobmanager|taskmanager)
    role="$1"
    export FLINK_LOG_DIR="/state/logs/$role"
    export FLINK_PID_DIR=/tmp
    mkdir -p "$FLINK_LOG_DIR"
    exec "$FLINK_HOME/bin/$role.sh" start-foreground
    ;;
  submit)
    shift
    export FLINK_LOG_DIR=/state/logs/client
    mkdir -p "$FLINK_LOG_DIR"
    exec "$FLINK_HOME/bin/flink" run -m jobmanager:8081 \
      -pyclientexec "$FLEET_RUNTIME/venv/bin/python" \
      -pyexec "$FLEET_RUNTIME/venv/bin/python" "$@"
    ;;
  *)
    echo 'Expected preflight, jobmanager, taskmanager or submit.' >&2
    exit 2
    ;;
esac
