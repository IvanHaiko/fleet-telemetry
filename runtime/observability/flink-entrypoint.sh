#!/bin/bash
set -euo pipefail
# Preserve the admitted image's generated JVM options and log configuration.
mkdir -p /tmp/flink-monitor-conf
cp /opt/m3/conf/* /tmp/flink-monitor-conf/
if [ -n "${FLEET_TASK_SLOTS:-}" ]; then
    [[ "$FLEET_TASK_SLOTS" =~ ^([1-9]|1[0-8])$ ]] || exit 2
    sed -i "s/^taskmanager.numberOfTaskSlots:.*/taskmanager.numberOfTaskSlots: $FLEET_TASK_SLOTS/" /tmp/flink-monitor-conf/config.yaml
fi
cat /opt/observability/flink-reporter.yaml >> /tmp/flink-monitor-conf/config.yaml
export FLINK_CONF_DIR=/tmp/flink-monitor-conf
exec /opt/m3/entrypoint.sh "$@"
