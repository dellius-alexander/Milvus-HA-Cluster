#!/bin/bash
# apply_ssl_config.sh
# Applies SSL configuration based on ENVIRONMENT variable (prod/dev).

set -e

# Log initialization
echo "{\"timestamp\":\"$(date -u '+%Y-%m-%d %H:%M:%S,%f')\",\"message\":\"Applying SSL configuration\",\"environment\":\"${ENVIRONMENT:-dev}\"}" >> /var/log/patroni/ssl_config.log

if [ "${ENVIRONMENT:-dev}" = "prod" ]; then
    echo "{\"timestamp\":\"$(date -u '+%Y-%m-%d %H:%M:%S,%f')\",\"message\":\"Configuring SSL for production\"}" >> /var/log/patroni/ssl_config.log
    # Ensure SSL certificates are in place
    for file in /run/secrets/postgres_ca_cert /run/secrets/patroni_api_cert /run/secrets/patroni_api_key /run/secrets/patroni_ca_cert /var/lib/postgresql/data/server.crt /var/lib/postgresql/data/server.key; do
        if [ ! -f "$file" ]; then
            echo "{\"timestamp\":\"$(date -u '+%Y-%m-%d %H:%M:%S,%f')\",\"message\":\"Error: Missing SSL file $file\",\"level\":\"ERROR\"}" >> /var/log/patroni/ssl_config.log
            exit 1
        fi
    done
    chown postgres:postgres /var/lib/postgresql/data/server.* /run/secrets/*
    chmod 600 /var/lib/postgresql/data/server.* /run/secrets/*
else
    echo "{\"timestamp\":\"$(date -u '+%Y-%m-%d %H:%M:%S,%f')\",\"message\":\"Skipping SSL configuration for development\"}" >> /var/log/patroni/ssl_config.log
fi

echo "{\"timestamp\":\"$(date -u '+%Y-%m-%d %H:%M:%S,%f')\",\"message\":\"SSL configuration completed\",\"environment\":\"${ENVIRONMENT:-dev}\"}" >> /var/log/patroni/ssl_config.log