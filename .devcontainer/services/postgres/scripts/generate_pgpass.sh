#!/bin/bash
# generate_pgpass.sh
# Generates .pgpass file for PostgreSQL authentication.

set -e

LOG_FILE=/var/log/patroni/setup.log
echo "{\"message\": \"Generating .pgpass file\", \"level\": \"INFO\", \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S,%f')\"}" >> $LOG_FILE

# Generate .pgpass
echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${PATRONI_POSTGRESQL_USERNAME}:$(cat /run/secrets/postgres_password)" > /var/lib/postgresql/.pgpass
echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${PATRONI_POSTGRESQL_REPLICATION_USERNAME}:$(cat /run/secrets/repl_password)" >> /var/lib/postgresql/.pgpass
echo "${PATRONI_POSTGRESQL_LISTEN:-0.0.0.0:5432}:*:${MILVUS_USER}:$(cat /run/secrets/milvus_password)" >> /var/lib/postgresql/.pgpass

# Set permissions
chown postgres:postgres /var/lib/postgresql/.pgpass
chmod 600 /var/lib/postgresql/.pgpass

echo "{\"message\": \".pgpass file generated\", \"level\": \"INFO\", \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S,%f')\"}" >> $LOG_FILE