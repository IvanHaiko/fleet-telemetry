#!/bin/bash
set -euo pipefail

: "${KAFKA_CLUSTER_ID:?An explicit experiment cluster ID is required}"
data=/var/lib/kafka/data
if [[ -f "$data/meta.properties" ]]; then
    grep -Fxq "cluster.id=$KAFKA_CLUSTER_ID" "$data/meta.properties" || {
        echo 'Existing Kafka cluster ID differs from the experiment configuration.' >&2
        exit 2
    }
else
    if [[ -n "$(find "$data" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
        echo 'Refusing to format nonempty unformatted Kafka storage.' >&2
        exit 2
    fi
    bin/kafka-storage.sh format --standalone --cluster-id "$KAFKA_CLUSTER_ID" \
        --config config/probe.properties
fi
exec bin/kafka-server-start.sh config/probe.properties
