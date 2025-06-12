# postgres.Dockerfile
# This file builds the PostgreSQL image for both master and replica nodes.
# Start with the official PostgreSQL 17.5 image
FROM postgres:17.5

# Pass in the HOSTNAME so we know if we're building the master or a replica
ARG HOSTNAME="postgres"
ARG PGDATA="/var/lib/postgresql/data"

# Set the HOSTNAME environment variable for use in the container
ENV HOSTNAME=${HOSTNAME}
ENV PGDATA=${PGDATA}

# Add metadata to the image (like labeling a box)
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="Custom PostgreSQL configuration for high-availability cluster"

# Install nano for editing files (just in case we need to debug)
RUN apt-get update && \
    apt-get install -y nano && \
    rm -rf /var/lib/apt/lists/*

# Copy configuration files to a temporary location
COPY cfg/postgresql.auto.conf /tmp/postgresql.auto.conf
COPY cfg/postgresql.base.conf /tmp/postgresql-base.conf
COPY cfg/postgresql.master.conf /tmp/postgresql-master.conf
COPY cfg/postgresql.replica.conf /tmp/postgresql-replica.conf
COPY cfg/pg_hba.conf /tmp/pg_hba.conf
COPY .secrets/postgres_password.txt /run/secrets/postgres_password
COPY .secrets/repl_password.txt /run/secrets/repl_password
COPY init-replica.sh /init-replica.sh
COPY initdb.d/00_init.sql /docker-entrypoint-initdb.d/00_init.sql


# Make the custom entrypoint script executable
RUN chmod +x /init-replica.sh

# Create the PostgreSQL data directory if it doesn't exist
RUN mkdir -p ${PGDATA} && \
    chown postgres:postgres ${PGDATA} && \
    chmod 644 ${PGDATA}

# Set up the configuration based on whether this is the master or a replica
RUN if [ "${HOSTNAME}" == "postgres-master" ]; then \
        # For the master, use the master-specific config and create an archive directory
        mv /tmp/postgresql-base.conf /etc/postgresql/postgresql.conf && \
        cat /tmp/postgresql-master.conf >> /etc/postgresql/postgresql.conf && \
        mkdir -p /var/lib/postgresql/archive && \
        chown postgres:postgres /var/lib/postgresql/archive && \
        chmod 644 /var/lib/postgresql/archive; \
    else \
        # For replicas, use the replica-specific config \
        mv /tmp/postgresql.auto.conf /etc/postgresql/postgresql.auto.conf && \
        mv /tmp/postgresql-base.conf /etc/postgresql/postgresql.conf && \
        cat /tmp/postgresql-replica.conf >> /etc/postgresql/postgresql.conf; \
    fi


# Expose the PostgreSQL port so other containers can connect
EXPOSE 5432

ENTRYPOINT["/init-replica.sh", "/usr/local/bin/docker-entrypoint.sh"]
# Use the default entrypoint from the PostgreSQL image
# The entrypoint script will handle starting PostgreSQL
# No need to specify CMD here, as the base image already has it set
# to start PostgreSQL with the correct parameters.
