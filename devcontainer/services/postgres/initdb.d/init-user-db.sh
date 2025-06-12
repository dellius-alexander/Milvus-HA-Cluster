#!/usr/bin/env bash
set -e

# Define the custom password for the 'milvus' user
MILVUS_PASSWORD="your_custom_password"

psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" <<-EOSQL
  CREATE USER milvus WITH PASSWORD '${MILVUS_PASSWORD}';
  CREATE DATABASE milvus;
  GRANT ALL PRIVILEGES ON DATABASE milvus TO milvus;
EOSQL