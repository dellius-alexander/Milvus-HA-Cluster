FROM apachepulsar/pulsar:4.0.4
ARG PULSAR_MEM=""

ENV PULSAR_MEM=${PULSAR_MEM}

LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="Custom Pulsar Proxy image for Milvus high-availability setup"

RUN OLDUSER=$(id -u)
USER root

# Copy and substiture environment variables
COPY cfg/pulsar-proxy.conf /pulsar/conf/proxy.conf
COPY scripts/proxy.sh /pulsar/entrypoint.sh

RUN chmod +x /pulsar/entrypoint.sh && \
    chown -R ${OLDUSER}:${OLDUSER} /pulsar/conf/proxy.conf

WORKDIR /pulsar

EXPOSE 6650 8080

USER ${OLDUSER}

ENTRYPOINT ["/pulsar/entrypoint.sh"]