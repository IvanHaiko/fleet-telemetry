#!/bin/bash
set -euo pipefail
: "${KAFKA_CLUSTER_ID:?An explicit cluster ID is required}"
: "${KAFKA_NODE_ID:?An explicit node ID is required}"
config=/run/kafka/node.properties
data=/var/lib/kafka/data
if [[ -f "$data/meta.properties" ]]; then
    grep -Fxq "cluster.id=$KAFKA_CLUSTER_ID" "$data/meta.properties"
    grep -Fxq "node.id=$KAFKA_NODE_ID" "$data/meta.properties"
else
    if [[ -n "$(find "$data" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
        echo 'Refusing nonempty unformatted storage.' >&2
        exit 2
    fi
    if [[ "$KAFKA_NODE_ID" -le 3 ]]; then
        bin/kafka-storage.sh format --cluster-id "$KAFKA_CLUSTER_ID" \
            --initial-controllers "$KAFKA_INITIAL_CONTROLLERS" --config "$config"
    else
        bin/kafka-storage.sh format --cluster-id "$KAFKA_CLUSTER_ID" \
            --no-initial-controllers --config "$config"
    fi
fi
exec bin/kafka-server-start.sh "$config"
