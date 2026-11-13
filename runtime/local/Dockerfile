FROM flink:2.2.1-scala_2.12-java17@sha256:15e8901a97a3703ad351f8212166798e36dd411c100b869e30c7c5e6b64351b0

USER root
RUN wget -q --timeout=30 --tries=3 \
      -O /opt/flink/lib/flink-sql-connector-kafka-5.0.0-2.2.jar \
      https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/5.0.0-2.2/flink-sql-connector-kafka-5.0.0-2.2.jar \
    && echo '5605c691d11a501382c383fecba37a7a552467da5ab7ba904ef5d6f3d62c5616  /opt/flink/lib/flink-sql-connector-kafka-5.0.0-2.2.jar' | sha256sum -c - \
    && mkdir -p /opt/flink/checkpoints \
    && chown flink:flink /opt/flink/checkpoints
COPY battery.sql /opt/flink/jobs/battery.sql
USER flink
