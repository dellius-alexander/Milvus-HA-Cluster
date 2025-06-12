FROM apachepulsar/pulsar:4.0.4
ARG NODE_TYPE=""
ARG ADVERTISED_ADDRESS=""
ARG BOOKIEID=""

# Metadata for the image
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="Custom Pulsar image for Milvus high-availability setup"

# Save user and change to root
RUN OLDUSER=$(id -u)
USER root

# Copy all config files
COPY cfg/${NODE_TYPE}.conf /pulsar/conf/${NODE_TYPE}.conf

# Apply environment configuration to "bookkeeper.conf"
RUN if [ "${NODE_TYPE}" == "bookkeeper" ]; then \
    sed -i "s|\${BOOKIEID}|${BOOKIEID}|g" /pulsar/conf/${NODE_TYPE}.conf; \
    sed -i "s|\${ADVERTISED_ADDRESS}|${ADVERTISED_ADDRESS}|g" /pulsar/conf/${NODE_TYPE}.conf; \
    # Create node data directories and set ownership
    mkdir -p /pulsar/data/${NODE_TYPE} && \
    chown -R ${OLDUSER}:${OLDUSER} /pulsar/data/${NODE_TYPE}; \
    fi

# Apply environment configuration to "zookeeper" node
RUN if [ "${NODE_TYPE}" == "zookeeper" ]; then \
    mkdir -p "/pulsar/data/zookeeper/version-2"; \
        # Create node data directories and set ownership
    mkdir -p /pulsar/data/${NODE_TYPE} && \
    chown -R ${OLDUSER}:${OLDUSER} /pulsar/data/${NODE_TYPE}; \
    fi

# Apply environment configuration to "broker" node
RUN if [ "${NODE_TYPE}" == "broker" ]; then \
    sed -i "s|\${ADVERTISED_ADDRESS}|${ADVERTISED_ADDRESS}|g" /pulsar/conf/${NODE_TYPE}.conf; \
    fi

# Apply permissions to configuration file
RUN chown -R ${OLDUSER}:${OLDUSER} /pulsar/conf/${NODE_TYPE}.conf

# Set working directory
WORKDIR /pulsar

# Change back to pulsar user
USER ${OLDUSER}

#Purpose:
#
#- Uses Apache Pulsar 4.0.4 for a reliable BookKeeper instance.
#
#- Installs curl for health checks to monitor service status.
#
#- Pre-creates BookKeeper data directories (ledgers, journal, index) to prevent permission issues.
#
#- Sets ownership to UID 10000 (pulsar user) for compatibility with the Pulsar image.
#
#- Uses an entrypoint script for consistent BookKeeper startup.
#
#- Exposes port 3181 for BookKeeper client connections and 8000 for HTTP admin interface.
#
#- Ensures minimal dependencies and a clean image by removing apt cache.
#
#- The ENTRYPOINT script applies environment variables and starts the BookKeeper service.
#
#- The WORKDIR directive sets the working directory to /pulsar, where Pulsar binaries are located.
#
#- The LABEL directive adds metadata for maintainability and documentation.
#
#- The FROM directive specifies the base image as Apache Pulsar 4.0.4.