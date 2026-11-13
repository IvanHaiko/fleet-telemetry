FROM eclipse-temurin:25-jre@sha256:171ffcf2a9ca207dfbc77b825cd3aaf8ab08d6113c086ee11514b965269fde28

RUN --mount=type=bind,source=kafka.tgz,target=/tmp/kafka.tgz,readonly \
    echo 'f5ceba8a265ab6bb2d68362b1f6859a95e15d60ef92ba83b43fdf065b557dc18e98d6383c15b9977320e25b3a2c8b6f11decb17b0fa6c0f163423793a0eb95cb  /tmp/kafka.tgz' | sha512sum -c - \
    && mkdir -p /opt/kafka /var/lib/kafka/data \
    && tar -xzf /tmp/kafka.tgz -C /opt/kafka --strip-components=1 \
    && chown -R 10001:10001 /var/lib/kafka

COPY kafka-probe.properties /opt/kafka/config/probe.properties
COPY start-kafka.sh /opt/kafka/bin/probe-start.sh
USER 10001:10001
WORKDIR /opt/kafka
ENV KAFKA_HEAP_OPTS="-Xms256m -Xmx512m" LOG_DIR="/tmp/kafka-logs"
ENTRYPOINT ["/bin/bash", "/opt/kafka/bin/probe-start.sh"]
