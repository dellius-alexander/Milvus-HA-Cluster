#!/bin/bash
# fetch_secrets.sh
# Fetches secrets and certificates from HashiCorp Vault and places them in /run/secrets.
# Controlled by ENVIRONMENT variable (prod/dev).

set -e

# Vault configuration
VAULT_ADDR=${VAULT_ADDR:-http://vault:8200}
VAULT_TOKEN=${VAULT_TOKEN:-$(cat /run/secrets/vault_token)}
SECRETS_PATH="secret/data/postgres"

# Create secrets directory
mkdir -p /run/secrets
chmod 700 /run/secrets

# Function to fetch secret from Vault
fetch_vault_secret() {
    local key=$1
    local file=$2
    local value=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        ${VAULT_ADDR}/v1/${SECRETS_PATH} | jq -r ".data.data.$key")
    echo "$value" > "$file"
    chown postgres:postgres "$file" || chown haproxy:haproxy "$file"
    chmod 600 "$file"
    echo "Fetched $key to $file" >> /var/log/patroni/secrets.log
}

# Log initialization
echo "{\"timestamp\":\"$(date -u '+%Y-%m-%d %H:%M:%S,%f')\",\"message\":\"Starting secrets fetch\",\"environment\":\"${ENVIRONMENT:-dev}\"}" >> /var/log/patroni/secrets.log

# Fetch passwords
fetch_vault_secret "postgres_password" "/run/secrets/postgres_password"
fetch_vault_secret "repl_password" "/run/secrets/repl_password"
fetch_vault_secret "milvus_password" "/run/secrets/milvus_password"
fetch_vault_secret "patroni_password" "/run/secrets/patroni_password"
fetch_vault_secret "haproxy_stats_password" "/run/secrets/haproxy_stats_password"

# Fetch SSL certificates (production only)
if [ "${ENVIRONMENT:-dev}" = "prod" ]; then
    fetch_vault_secret "postgres_ca_cert" "/run/secrets/postgres_ca_cert"
    fetch_vault_secret "patroni_api_cert" "/run/secrets/patroni_api_cert"
    fetch_vault_secret "patroni_api_key" "/run/secrets/patroni_api_key"
    fetch_vault_secret "patroni_ca_cert" "/run/secrets/patroni_ca_cert"
    fetch_vault_secret "postgres_server_cert" "/var/lib/postgresql/data/server.crt"
    fetch_vault_secret "postgres_server_key" "/var/lib/postgresql/data/server.key"
fi

echo "{\"timestamp\":\"$(date -u '+%Y-%m-%d %H:%M:%S,%f')\",\"message\":\"Secrets fetch completed\",\"environment\":\"${ENVIRONMENT:-dev}\"}" >> /var/log/patroni/secrets.log