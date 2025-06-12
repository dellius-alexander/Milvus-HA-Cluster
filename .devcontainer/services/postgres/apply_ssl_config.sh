#!/bin/bash
# apply_ssl_config.sh
#
# Applies SSL configuration from ssl_config.yml during Patroni image build.
# Configures PostgreSQL and Patroni REST API SSL settings based on ENABLE_SSL.
# Validates certificates and sets permissions.
#
# Usage:
#   Executed automatically in patroni.Dockerfile.
#
# Prerequisites:
#   - ssl_config.yml at /tmp/ssl_config.yml
#   - Certificates in /run/secrets/ or /var/lib/postgresql/data/
#
# Environment Variables:
#   - ENABLE_SSL: Set to 'true' for production, 'false' for development
#
# Output:
#   - Log file: /var/log/patroni/ssl_config.log
#   - Updated /etc/patroni.yml

set -e

# Configuration
LOG_FILE="/var/log/patroni/ssl_config.log"
SSL_CONFIG="/tmp/ssl_config.yml"
PATRONI_CONFIG="/etc/patroni.yml"
PGPASS_FILE="/var/lib/postgresql/.pgpass"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"
chown postgres:postgres "$(dirname "$LOG_FILE")"
chmod 750 "$(dirname "$LOG_FILE")"

# Check if ssl_config.yml exists
if [ ! -f "$SSL_CONFIG" ]; then
    log "ERROR: SSL configuration file $SSL_CONFIG not found"
    exit 1
fi

# Extract values from ssl_config.yml using yq (install yq if needed)
if ! command -v yq >/dev/null 2>&1; then
    log "Installing yq for YAML parsing"
    apt-get update && apt-get install -y yq
fi

# Validate certificates if SSL is enabled
if [ "$ENABLE_SSL" = "true" ]; then
    log "ENABLE_SSL is true, validating certificates"
    CERT_FILES=(
        "$(yq e '.certificates.postgres_ca_cert' "$SSL_CONFIG")"
        "$(yq e '.certificates.patroni_api_cert' "$SSL_CONFIG")"
        "$(yq e '.certificates.patroni_api_key' "$SSL_CONFIG")"
        "$(yq e '.certificates.patroni_ca_cert' "$SSL_CONFIG")"
        "$(yq e '.certificates.postgres_server_cert' "$SSL_CONFIG")"
        "$(yq e '.certificates.postgres_server_key' "$SSL_CONFIG")"
    )
    for cert in "${CERT_FILES[@]}"; do
        if [ ! -f "$cert" ]; then
            log "ERROR: Certificate file $cert not found"
            exit 1
        fi
        if [[ "$cert" == *.crt || "$cert" == *.cert ]]; then
            if ! openssl x509 -in "$cert" -text -noout >/dev/null 2>&1; then
                log "ERROR: Invalid certificate: $cert"
                exit 1
            fi
        elif [[ "$cert" == *.key ]]; then
            if ! openssl rsa -in "$cert" -check >/dev/null 2>&1; then
                log "ERROR: Invalid key: $cert"
                exit 1
            fi
        fi
        log "Validated: $cert"
    done
    # Set certificate permissions
    chmod 600 "${CERT_FILES[@]}"
    chown postgres:postgres "${CERT_FILES[@]}"
else
    log "ENABLE_SSL is false, skipping certificate validation"
fi

# Update Patroni configuration
log "Updating $PATRONI_CONFIG based on ENABLE_SSL"
if [ "$ENABLE_SSL" = "true" ]; then
    # Apply SSL settings
    yq e -i '.postgresql.parameters.ssl = true' "$PATRONI_CONFIG"
    yq e -i ".postgresql.parameters.ssl_cert_file = \"$(yq e '.postgresql.cert_file' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.parameters.ssl_key_file = \"$(yq e '.postgresql.key_file' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.parameters.ssl_ca_file = \"$(yq e '.postgresql.ca_file' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.parameters.sslmode = \"$(yq e '.postgresql.sslmode' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.replication.sslcert = \"$(yq e '.postgresql.replication.sslcert' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.replication.sslkey = \"$(yq e '.postgresql.replication.sslkey' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.replication.sslca = \"$(yq e '.postgresql.replication.sslca' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.superuser.sslcert = \"$(yq e '.postgresql.superuser.sslcert' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.superuser.sslkey = \"$(yq e '.postgresql.superuser.sslkey' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".postgresql.superuser.sslca = \"$(yq e '.postgresql.superuser.sslca' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".restapi.certfile = \"$(yq e '.restapi.certfile' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".restapi.keyfile = \"$(yq e '.restapi.keyfile' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".restapi.cafile = \"$(yq e '.restapi.cafile' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
    yq e -i ".restapi.verify_client = \"$(yq e '.restapi.verify_client' "$SSL_CONFIG")\"" "$PATRONI_CONFIG"
else
    # Disable SSL settings
    yq e -i 'del(.postgresql.parameters.ssl)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.parameters.ssl_cert_file)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.parameters.ssl_key_file)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.parameters.ssl_ca_file)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.parameters.sslmode)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.replication.sslcert)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.replication.sslkey)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.replication.sslca)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.superuser.sslcert)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.superuser.sslkey)' "$PATRONI_CONFIG"
    yq e -i 'del(.postgresql.superuser.sslca)' "$PATRONI_CONFIG"
    yq e -i 'del(.restapi.certfile)' "$PATRONI_CONFIG"
    yq e -i 'del(.restapi.keyfile)' "$PATRONI_CONFIG"
    yq e -i 'del(.restapi.cafile)' "$PATRONI_CONFIG"
    yq e -i 'del(.restapi.verify_client)' "$PATRONI_CONFIG"
fi

# Validate .pgpass
if [ -f "$PGPASS_FILE" ]; then
    log "Validating .pgpass file"
    chmod 600 "$PGPASS_FILE"
    chown postgres:postgres "$PGPASS_FILE"
else
    log "ERROR: .pgpass file not found at $PGPASS_FILE"
    exit 1
fi

log "SSL configuration applied successfully"
exit 0