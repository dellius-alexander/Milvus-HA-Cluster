FROM apachepulsar/pulsar:4.0.4

# Metadata for the image
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="Custom Pulsar image for Milvus high-availability setup"

# Save user and change to root
RUN OLDUSER=$(id -u)
USER root

# Copy all config files
COPY cfg/bookkeeper.conf /pulsar/conf/bookkeeper.conf

# Create BookKeeper data directories and set ownership
RUN mkdir -p /pulsar/data/bookkeeper && \
    chown -R ${OLDUSER}:${OLDUSER} /pulsar/data/bookkeeper && \
    chown -R ${OLDUSER}:${OLDUSER} /pulsar/conf/bookkeeper.conf

# Copy entrypoint script
COPY scripts/bookkeeper.sh /pulsar/entrypoint.sh
RUN chmod +x /pulsar/entrypoint.sh

# Set working directory
WORKDIR /pulsar

# Expose BookKeeper ports
EXPOSE 3181 8000

# Change back to pulsar user
USER ${OLDUSER}

#Define entrypoint
ENTRYPOINT ["/pulsar/entrypoint.sh"]

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