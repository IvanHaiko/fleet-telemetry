#!/bin/bash
set -euo pipefail

for topic in telemetry.battery.input telemetry.battery.output; do
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 \
        --create --if-not-exists --topic "$topic" \
        --partitions 12 --replication-factor 1 \
        --config retention.ms=3600000 --config retention.bytes=8388608 \
        --config segment.bytes=1048576 --config segment.ms=60000
    description=$(/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 \
        --describe --topic "$topic")
    printf '%s\n' "$description"
    printf '%s\n' "$description" | grep -Eq 'PartitionCount:[[:space:]]+12([[:space:]]|$)'
    printf '%s\n' "$description" | grep -Eq 'ReplicationFactor:[[:space:]]+1([[:space:]]|$)'
done
