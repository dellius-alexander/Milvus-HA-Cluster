#!/usr/bin/env bash
set -e
# Run init-replica.sh first
if [ -f /docker-entrypoint-initdb.d/init-replica.sh ]; then
    echo "Running init-replica.sh"
    /docker-entrypoint-initdb.d/init-replica.sh
fi
# Run the default PostgreSQL entrypoint
exec /usr/local/bin/docker-entrypoint.sh "$@"