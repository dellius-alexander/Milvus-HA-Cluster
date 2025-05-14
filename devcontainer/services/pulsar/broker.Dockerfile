FROM apachepulsar/pulsar:4.0.4
ARG SERVERID=""

# Metadata for the image
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="Custom Pulsar image for Milvus high-availability setup"

# Save user and change to root
RUN OLDUSER=$(id -u)
USER root

# Copy all config files
COPY cfg/broker.conf /pulsar/conf/broker.conf

# Copy entrypoint script
COPY scripts/broker.sh /pulsar/entrypoint.sh
RUN chmod +x /pulsar/entrypoint.sh && \
    chown -R ${OLDUSER}:${OLDUSER} /pulsar/conf/broker.conf

# Set working directory
WORKDIR /pulsar

# Expose BookKeeper ports
EXPOSE 6650 8080

# Change back to pulsar user
USER ${OLDUSER}

#Define entrypoint
ENTRYPOINT ["/pulsar/entrypoint.sh"]

