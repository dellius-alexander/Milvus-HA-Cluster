# patroni.Dockerfile
# Builds a Patroni-managed PostgreSQL image for a high-availability cluster.
# Supports SSL in production (ENVIRONMENT=prod) and non-SSL in development (ENVIRONMENT=dev).
# Uses HashiCorp Vault sidecar for secrets and certificates.

FROM postgres:17.5

# Define build arguments
ARG PATRONI_SCOPE
ARG PATRONI_NAMESPACE
ARG PATRONI_NAME
ARG PATRONI_RESTAPI_LISTEN
ARG PATRONI_RESTAPI_CONNECT_ADDRESS
ARG PATRONI_RESTAPI_USERNAME
ARG PATRONI_ETCD3_HOSTS
ARG PATRONI_ETCD3_PROTOCOL
ARG PATRONI_ETCD3_USE_PROXIES
ARG PATRONI_POSTGRESQL_LISTEN
ARG PATRONI_POSTGRESQL_CONNECT_ADDRESS
ARG PATRONI_POSTGRESQL_DATA_DIR
ARG PATRONI_POSTGRESQL_USERNAME
ARG PATRONI_POSTGRESQL_REPLICATION_USERNAME
ARG PATRONI_LOG_TYPE
ARG PATRONI_LOG_FORMAT
ARG PATRONI_LOG_STATIC_FIELDS
ARG PATRONI_LOG_LEVEL
ARG PATRONI_LOG_FILE_NUM
ARG PATRONI_LOG_FILE_SIZE
ARG PATRONI_LOG_DATEFORMAT
ARG PATRONI_LOG_HANDLERS

# Set environment variables
ENV PGDATA=${PGDATA:-/var/lib/postgresql/data} \
    PATRONI_SCOPE=${PATRONI_SCOPE} \
    PATRONI_NAMESPACE=${PATRONI_NAMESPACE} \
    PATRONI_NAME=${PATRONI_NAME} \
    PATRONI_RESTAPI_LISTEN=${PATRONI_RESTAPI_LISTEN} \
    PATRONI_RESTAPI_CONNECT_ADDRESS=${PATRONI_RESTAPI_CONNECT_ADDRESS} \
    PATRONI_RESTAPI_USERNAME=${PATRONI_RESTAPI_USERNAME} \
    PATRONI_ETCD3_HOSTS=${PATRONI_ETCD3_HOSTS} \
    PATRONI_ETCD3_PROTOCOL=${PATRONI_ETCD3_PROTOCOL} \
    PATRONI_ETCD3_USE_PROXIES=${PATRONI_ETCD3_USE_PROXIES} \
    PATRONI_POSTGRESQL_LISTEN=${PATRONI_POSTGRESQL_LISTEN} \
    PATRONI_POSTGRESQL_CONNECT_ADDRESS=${PATRONI_POSTGRESQL_CONNECT_ADDRESS} \
    PATRONI_POSTGRESQL_DATA_DIR=${PATRONI_POSTGRESQL_DATA_DIR} \
    PATRONI_POSTGRESQL_USERNAME=${PATRONI_POSTGRESQL_USERNAME} \
    PATRONI_POSTGRESQL_REPLICATION_USERNAME=${PATRONI_POSTGRESQL_REPLICATION_USERNAME} \
    PATRONI_LOG_TYPE=${PATRONI_LOG_TYPE} \
    PATRONI_LOG_FORMAT=${PATRONI_LOG_FORMAT} \
    PATRONI_LOG_STATIC_FIELDS=${PATRONI_LOG_STATIC_FIELDS} \
    PATRONI_LOG_LEVEL=${PATRONI_LOG_LEVEL} \
    PATRONI_LOG_FILE_NUMコンピンプレート
    PATRONI_LOG_FILE_NUM=${PATRONI_LOG_FILE_NUM} \
    PATRONI_LOG_FILE_SIZE=${PATRONI_LOG_FILE_SIZE} \
    PATRONI_LOG_DATEFORMAT=${PATRONI_LOG_DATEFORMAT} \
    PATRONI_LOG_HANDLERS=${PATRONI_LOG_HANDLERS} \
    ENVIRONMENT=${ENVIRONMENT:-dev} \
    PATH="/opt/patroni/bin/:${PATH}"

USER root

# Add metadata
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="Patroni-managed PostgreSQL for high-availability cluster"

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl python3-dev python3-venv libpq-dev python3-psycopg2 gettext yq && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment for Patroni
RUN python3 -m venv /opt/patroni-venv && \
    . /opt/patroni-venv/bin/activate && \
    pip install --upgrade pip setuptools && \
    pip install patroni[psycopg3,etcd3] python-etcd psycopg>=3.0.0 python-json-logger

# Copy configuration files
COPY cfg/patroni-conf.yml /tmp/patroni.yml
COPY cfg/pg_hba.conf /etc/postgresql/pg_hba.conf
COPY scripts/apply_ssl_config.sh /tmp/apply_ssl_config.sh
COPY scripts/fetch_secrets.sh /tmp/fetch_secrets.sh
COPY initdb.d/00_init.sql /docker-entrypoint-initdb.d/00_init.sql

# Run fetch_secrets.sh to retrieve secrets from Vault
RUN bash /tmp/fetch_secrets.sh && \
    rm /tmp/fetch_secrets.sh

# Apply SSL configuration based on ENVIRONMENT
RUN bash /tmp/apply_ssl_config.sh && \
    rm /tmp/apply_ssl_config.sh

# Generate .pgpass file
RUN echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${PATRONI_POSTGRESQL_USERNAME}:${PATRONI_POSTGRESQL_PASSWORD}" > /var/lib/postgresql/.pgpass && \
    echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${PATRONI_POSTGRESQL_REPLICATION_USERNAME}:${PATRONI_POSTGRESQL_REPLICATION_PASSWORD}" >> /var/lib/postgresql/.pgpass && \
    echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${MILVUS_USER}:${MILVUS_PASSWORD}" >> /var/lib/postgresql/.pgpass && \
    chown postgres:postgres /var/lib/postgresql/.pgpass && \
    chmod 600 /var/lib/postgresql/.pgpass

# Substitute environment variables in the Patroni configuration
RUN envsubst < /tmp/patroni.yml > /etc/patroni.yml && \
    mkdir -p /var/lib/postgresql/.config/patroni && \
    envsubst < /tmp/patroni.yml > /var/lib/postgresql/.config/patroni/patronictl.yaml && \
    rm /tmp/patroni.yml

# Set permissions
RUN mkdir -p /var/log/patroni && \
    chown postgres:postgres /var/log/patroni && \
    chmod 750 /var/log/patroni && \
    chown postgres:postgres ${PGDATA} && \
    chmod 700 ${PGDATA} && \
    chown postgres:postgres /etc/patroni.yml /etc/postgresql/pg_hba.conf && \
    chmod 600 /etc/patroni.yml /etc/postgresql/pg_hba.conf

# Expose ports
EXPOSE 5432 8008

USER postgres

# Run Patroni
ENTRYPOINT ["patroni", "/etc/patroni.yml"]

# Notes:
# - Set ENVIRONMENT=prod for SSL; ENVIRONMENT=dev for non-SSL.
# - Secrets are fetched from HashiCorp Vault via fetch_secrets.sh.
# - Structured logging is enabled with python-json-logger.
# - Monitor with Prometheus/Grafana (configured separately).