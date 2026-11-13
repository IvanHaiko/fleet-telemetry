FROM fleet-telemetry/kafka-probe:4.4.0@sha256:676a930ab90762c2c32ef79642ad2293c18e5cea96381fc72af54e51fb3cd1c3

USER 0:0
ARG RUNTIME_PREFIX
ADD runtime-payload.tar ${RUNTIME_PREFIX}/
COPY runtime-payload-manifest.json /opt/m3/runtime-manifest.json
COPY config.yaml /opt/m3/conf/config.yaml
COPY entrypoint.sh preflight.py /opt/m3/
COPY utility-pins.json /opt/m3/utility-pins.json
COPY rev /usr/local/bin/rev
COPY rev-copyright GPL-2 /usr/share/doc/m3-rev/

ENV FLEET_RUNTIME=${RUNTIME_PREFIX} \
    JAVA_HOME=${RUNTIME_PREFIX}/jdk/jdk-17.0.20.1+1 \
    FLINK_HOME=${RUNTIME_PREFIX}/venv/lib/python3.12/site-packages/pyflink \
    FLINK_CONF_DIR=/opt/m3/conf \
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
    PYTHONPATH=/workspace:/workspace/runtime/pyflink
ENV PATH="${JAVA_HOME}/bin:${FLEET_RUNTIME}/venv/bin:${PATH}"

RUN mkdir -p /state/checkpoints /state/logs /state/inputs /state/tmp \
    && chown -R 10001:10001 /state \
    && cp "${FLEET_RUNTIME}/flink-sql-connector-kafka-5.0.0-2.2.jar" "${FLINK_HOME}/lib/" \
    && cp "${FLINK_HOME}/conf/"*log* /opt/m3/conf/ \
    && chmod 755 /opt/m3/entrypoint.sh /usr/local/bin/rev

USER 10001:10001
WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "/opt/m3/entrypoint.sh"]
