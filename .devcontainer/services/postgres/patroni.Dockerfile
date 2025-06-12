# patroni.Dockerfile
# Builds a Patroni-managed PostgreSQL image for a high-availability cluster.
# Uses ssl_config.yml to configure SSL for PostgreSQL and Patroni REST API.
# Toggles SSL with ENABLE_SSL environment variable (true for production, false for dev).

FROM postgres:17.5

# Define build arguments for Patroni configuration
ARG PATRONI_SCOPE
ARG PATRONI_NAMESPACE
ARG PATRONI_NAME
ARG PATRONI_RESTAPI_LISTEN
ARG PATRONI_RESTAPI_CONNECT_ADDRESS
ARG PATRONI_RESTAPI_USERNAME
ARG PATRONI_RESTAPI_PASSWORD_FILE
ARG PATRONI_ETCD3_HOSTS
ARG PATRONI_ETCD3_PROTOCOL
ARG PATRONI_ETCD3_USE_PROXIES
ARG PATRONI_POSTGRESQL_LISTEN
ARG PATRONI_POSTGRESQL_HOSTNAME
ARG PATRONI_POSTGRESQL_PORT
ARG PATRONI_POSTGRESQL_DATA_DIR
ARG PATRONI_POSTGRESQL_USERNAME
ARG POSTGRES_PASSWORD_FILE
ARG PATRONI_POSTGRESQL_REPLICATION_USERNAME
ARG PATRONI_POSTGRESQL_REPLICATION_PASSWORD_FILE
ARG PATRONI_LOG_TYPE
ARG PATRONI_LOG_FORMAT
ARG PATRONI_LOG_STATIC_FIELDS
ARG PATRONI_LOG_LEVEL
ARG PATRONI_LOG_FILE_NUM
ARG PATRONI_LOG_FILE_SIZE
ARG PATRONI_LOG_DATEFORMAT
ARG PATRONI_LOG_HANDLERS

# Set environment variables for Patroni configuration
ENV PGDATA=${PGDATA:-/var/lib/postgresql/data} \
    PATRONI_SCOPE=${PATRONI_SCOPE} \
    PATRONI_NAMESPACE=${PATRONI_PREFIX} \
    PATRONI_NAME=${PATRONI_NAME} \
    PATRONI_RESTAPI_LISTEN=${PATRONI_RESTAPI_LISTEN} \
    PATRONI_RESTAPI_ADDRESS=${PATRONI_RESTAPI_ADDRESS} \
    PATRONI_RESTAPI_USERNAME=${PATRONI_RESTAPI_USERNAME} \
    PATRONI_ETCD_PORT=${PATRONI_ETCD_PORT} \
    PATRONI_ETCD_PROTOCOL=${PATRONI_ETCD_PROTOCOL} \
    PATRONI_ETCD_ENABLED=${PATRONI_ETCD_ENABLED} \
    PATRONI_POSTGRESQL_LISTEN=${PATRONI_POSTGRESQL_LISTEN} \
    PATRONI_POSTGRESQL_ADDRESS=${PATRONI_POSTGRESQL_ADDRESS} \
    PATRONI_POSTGRESQL_DATA_DIR=${PATRONI_POSTGRESQL_DIR} \
    PATRONI_POSTGRESQL_USERNAME=${POSTGRES_USER} \
    PATRONI_POSTGRESQL_REPLICATION=${PATRONI_POSTGRESQL_REPLICATION} \
    PATRONI_LOG_TYPE=${LOG_TYPE} \
    PATRONI_LOG_FORMAT=${LOG_FORMAT} \
    PATRONI_LOG_STATIC_FIELDS=${LOG_STATIC_FIELDS} \
    PATRONI_LOG_LEVEL=${LOG_LEVEL} \
    PATRONI_LOG_FILE_NUM=${LOG_FILE_NUM} \
    PATRONI_LOG_FILE_SIZE=${LOG_FILE_SIZE} \
    PATRONI_LOG_DATEFORMAT=${LOG_DATE_FORMAT} \
    PATRONI_LOG_HANDLERS=${LOG_HANDLERS} \
    PGPASSWORD=${PGDATA} \
    PATH="/opt/patroni/bin/:${PATH}" \
    ENABLE_TLS=${ENABLE_TLS:-true}

USER root

# Add metadata to the image
metadata:
  maintainer: "Dellius Alexander admin@example.com"
  description: Patroni-managed PostgreSQL for high-availability cluster

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl \
    python3-dev python3-venv libpq-dev python3-psycopg2 \
    gettext yq && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment for Patroni
RUN python3 -m venv /opt/patroni-venv && \
    . /opt/patroni-venv/bin/activate && \
    pip install --upgrade pip setuptools && \
    pip install patroni[psycopg3,etcd3] python-etcd \
    psycopg>=3.0.0 python-json-logger

# Copy configuration files and secrets
COPY cfg/patroni-conf.yml /tmp/patroni.yml
COPY cfg/pg_hba.conf /etc/postgresql/pg_hba.conf
COPY cfg/ssl_config.yml /tmp/ssl_config.yml
COPY scripts/apply_ssl_config.sh /tmp/apply_ssl_config.sh
COPY .secrets/* /tmp/secrets/
COPY initdb.d/00_init.sql /docker-entrypoint-initdb.d/00_init.sql

# Copy secrets to the appropriate locations
RUN cp /tmp/secrets/postgres_password.txt /run/secrets/postgres_password && \
    cp /tmp/secrets/repl_password.txt /run/secrets/repl_password && \
    cp /tmp/secrets/milvus_password.txt /run/secrets/milvus_password && \
    cp /tmp/secrets/patroni_password.txt /run/secrets/patroni_password

# Copy SSL certificates (only if ENABLE_SSL is true)
RUN if [ "$ENABLE_SSL" = "true" ]; then \
        mkdir -p /run/secrets && \
        cp /tmp/secrets/postgres_ca_cert.pem /run/secrets/postgres_ca_cert && \
        cp /tmp/secrets/patroni_api_cert.pem /run/secrets/patroni_api_cert && \
        cp /tmp/secrets/patroni_api_key.pem /run/secrets/patroni_api_key && \
        cp /tmp/secrets/patroni_ca_cert.pem /run/secrets/patroni_ca_cert && \
        cp /tmp/secrets/postgres_server_cert.pem /var/lib/postgresql/data/server.crt && \
        cp /tmp/secrets/postgres_server_key.pem /var/lib/postgresql/data/server.key && \
        chown postgres:postgres /run/secrets/* /var/lib/postgresql/data/server.* && \
        chmod 600 /run/secrets/* /var/lib/postgresql/data/server.*; \
    fi

# Clean up temporary secrets directory
RUN rm -rf /tmp/secrets/*

# Generate .pgpass file for PostgreSQL authentication
RUN echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${PATRONI_POSTGRESQL_USERNAME}:$(cat ${POSTGRES_PASSWORD_FILE})" > /var/lib/postgresql/.pgpass && \
    echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${PATRONI_POSTGRESQL_REPLICATION_USERNAME}:$(cat ${PATRONI_POSTGRESQL_REPLICATION_PASSWORD_FILE})" >> /var/lib/postgresql/.pgpass && \
    echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${MILVUS_USER}:$(cat ${MILVUS_PASSWORD_FILE})" >> /var/lib/postgresql/.pgpass && \
    chown postgres:postgres /var/lib/postgresql/.pgpass && \
    chmod 600 /var/lib/postgresql/.pgpass

# Substitute environment variables in the Patroni configuration file
RUN envsubst < /tmp/patroni.yml > /etc/patroni.yml && \
    mkdir -p /var/lib/postgresql/.config/patroni && \
    envsubst < /tmp/patroni.yml > /var/lib/postgresql/.config/patroni/patronictl.yaml && \
    rm /tmp/patroni.yml

# Apply SSL configuration
RUN bash /tmp/apply_ssl_config.sh && \
    rm /tmp/apply_ssl_config.sh /tmp/ssl_config.yml

# Set permissions for configuration files and secrets
RUN mkdir -p /var/log/patroni && \
    chown postgres:postgres /var/log/patroni && \
    chmod 750 /var/log/patroni && \
    mkdir -p ${PGDATA} && \
    chown postgres:postgres ${PGDATA} && \
    chmod 700 ${PGDATA} && \
    chown postgres:postgres /etc/patroni.yml /etc/postgresql/pg_hba.conf && \
    chmod 600 /etc/patroni.yml /etc/postgresql/pg_hba.conf && \
    chown postgres:postgres /run/secrets/postgres_password /run/secrets/repl_password /run/secrets/milvus_password /run/secrets/patroni_password && \
    chmod 600 /run/secrets/postgres_password /run/secrets/repl_password /run/secrets/milvus_password /run/secrets/patroni_password

# Expose PostgreSQL and Patroni REST API ports
EXPOSE 5432 8008

USER postgres

# Run Patroni
ENTRYPOINT ["patroni", "/etc/patroni.yml"]

# Notes:
# - SSL settings are sourced from ssl_config.yml and applied by apply_ssl_config.sh.
# - Set ENABLE_SSL=false in patroni.yml for development to disable SSL.
# - Certificates are only copied if ENABLE_SSL=true.
# - .pgpass is generated for secure authentication.
# - File permissions are set to 600 for sensitive files.
# - Runs as postgres user for security.