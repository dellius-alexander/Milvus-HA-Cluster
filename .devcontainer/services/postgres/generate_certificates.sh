#!/bin/bash
# generate_certificates.sh
#
# Automates the creation of SSL/TLS certificates for a Patroni PostgreSQL cluster.
# Generates a self-signed CA and signs server/client certificates for PostgreSQL
# and Patroni REST API. Stores certificates in .secrets/ with secure permissions.
#
# Usage:
#   chmod +x generate_certificates.sh
#   ./generate_certificates.sh
#
# Prerequisites:
#   - OpenSSL installed
#   - Run as a user with permissions to create .secrets/ and set ownership
#   - Docker installed (for user ID lookup)
#
# Output:
#   - Certificates in .secrets/:
#     - postgres_ca_cert.pem, patroni_ca_cert.pem
#     - postgres_client_cert.pem, postgres_client_key.pem
#     - postgres_server_cert.pem, postgres_server_key.pem
#     - patroni_api_cert.pem, patroni_api_key.pem
#   - Log file: certificate_generation.log
#
# Notes:
#   - Certificates are self-signed for simplicity; use a trusted CA in production.
#   - Adjust DAYS_VALID and subject details as needed.
#   - Run this script before starting the Docker Compose cluster.

set -e  # Exit on error

# Configuration
SECRETS_DIR=".secrets"
LOG_FILE="certificate_generation.log"
DAYS_VALID=365  # Certificate validity period
CA_SUBJECT="/C=US/ST=State/L=City/O=Organization/OU=IT/CN=PatroniCA"
SERVER_SUBJECT="/C=US/ST=State/L=City/O=Organization/OU=IT/CN=patroni-postgres"
CLIENT_SUBJECT="/C=US/ST=State/L=City/O=Organization/OU=IT/CN=patroni-client"
API_SUBJECT="/C=US/ST=State/L=City/O=Organization/OU=IT/CN=patroni-api"
SAN="DNS:localhost,DNS:patroni-replica0,DNS:patroni-replica1,DNS:patroni-replica2,DNS:patroni-replica3,IP:127.0.0.1,IP:10.1.0.0"

# File paths
CA_CERT="$SECRETS_DIR/postgres_ca_cert.pem"
CA_KEY="$SECRETS_DIR/postgres_ca_key.pem"
PATRONI_CA_CERT="$SECRETS_DIR/patroni_ca_cert.pem"  # Symlink to CA_CERT
POSTGRES_CLIENT_CERT="$SECRETS_DIR/postgres_client_cert.pem"
POSTGRES_CLIENT_KEY="$SECRETS_DIR/postgres_client_key.pem"
POSTGRES_SERVER_CERT="$SECRETS_DIR/postgres_server_cert.pem"
POSTGRES_SERVER_KEY="$SECRETS_DIR/postgres_server_key.pem"
PATRONI_API_CERT="$SECRETS_DIR/patroni_api_cert.pem"
PATRONI_API_KEY="$SECRETS_DIR/patroni_api_key.pem"
OPENSSL_CONF="$SECRETS_DIR/openssl.cnf"

# User IDs (match Docker container users)
POSTGRES_UID=999  # Default to 999 if postgres user not found

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if OpenSSL is installed
if ! command -v openssl &>/dev/null; then
    log "ERROR: OpenSSL is not installed. Please install it and try again."
    exit 1
fi

# Create secrets directory
if [ ! -d "$SECRETS_DIR" ]; then
    log "Creating secrets directory: $SECRETS_DIR"
    mkdir -p "$SECRETS_DIR" || {
      log "ERROR: Failed to create $SECRETS_DIR";
      exit 1;
      }
    chmod 700 "$SECRETS_DIR"
fi

# Check for existing certificates
for cert in "$CA_CERT" "$POSTGRES_CLIENT_CERT" "$POSTGRES_SERVER_CERT" "$PATRONI_API_CERT"; do
    if [ -f "$cert" ]; then
        log "WARNING: Certificate $cert already exists. Skipping generation."
        echo "To regenerate, remove existing certificates in $SECRETS_DIR and rerun."
        exit 0
    fi
done

# Create OpenSSL configuration file for SANs
log "Generating OpenSSL configuration file"
cat > "$OPENSSL_CONF" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = IT
CN = patroni-postgres

[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = $SAN
EOF

# Generate CA
log "Generating CA certificate and key"
openssl genrsa -out "$CA_KEY" 4096
openssl req -x509 -new -nodes -key "$CA_KEY" -sha256 -days "$DAYS_VALID" \
    -out "$CA_CERT" -subj "$CA_SUBJECT"
chmod 600 "$CA_KEY" "$CA_CERT"
chown "$POSTGRES_UID:$POSTGRES_UID" "$CA_KEY" "$CA_CERT" 2>/dev/null || true
log "Created $CA_CERT and $CA_KEY"

# Symlink patroni_ca_cert.pem to postgres_ca_cert.pem
log "Creating symlink for patroni_ca_cert.pem"
ln -sf "$CA_CERT" "$PATRONI_CA_CERT"
chown -h "$POSTGRES_UID:$POSTGRES_UID" "$PATRONI_CA_CERT" 2>/dev/null || true

# Generate PostgreSQL server certificate
log "Generating PostgreSQL server certificate and key"
openssl genrsa -out "$POSTGRES_SERVER_KEY" 2048
openssl req -new -key "$POSTGRES_SERVER_KEY" -out "$SECRETS_DIR/server.csr" \
    -subj "$SERVER_SUBJECT" -config "$OPENSSL_CONF"
openssl x509 -req -in "$SECRETS_DIR/server.csr" -CA "$CA_CERT" -CAkey "$CA_KEY" \
    -CAcreateserial -out "$POSTGRES_SERVER_CERT" -days "$DAYS_VALID" -sha256 \
    -extensions v3_req -extfile "$OPENSSL_CONF"
chmod 600 "$POSTGRES_SERVER_KEY" "$POSTGRES_SERVER_CERT"  2>/dev/null
chown "$POSTGRES_UID:$POSTGRES_UID" "$POSTGRES_SERVER_KEY" "$POSTGRES_SERVER_CERT"  2>/dev/null || true
rm "$SECRETS_DIR/server.csr"
log "Created $POSTGRES_SERVER_CERT and $POSTGRES_SERVER_KEY"

# Generate PostgreSQL client certificate
log "Generating PostgreSQL client certificate and key"
openssl genrsa -out "$POSTGRES_CLIENT_KEY" 2048
openssl req -new -key "$POSTGRES_CLIENT_KEY" -out "$SECRETS_DIR/client.csr" \
    -subj "$CLIENT_SUBJECT" -config "$OPENSSL_CONF"
openssl x509 -req -in "$SECRETS_DIR/client.csr" -CA "$CA_CERT" -CAkey "$CA_KEY" \
    -CAcreateserial -out "$POSTGRES_CLIENT_CERT" -days "$DAYS_VALID" -sha256 \
    -extensions v3_req -extfile "$OPENSSL_CONF"
chmod 600 "$POSTGRES_CLIENT_KEY" "$POSTGRES_CLIENT_CERT"
chown "$POSTGRES_UID:$POSTGRES_UID" "$POSTGRES_CLIENT_KEY" "$POSTGRES_CLIENT_CERT" 2>/dev/null || true
rm "$SECRETS_DIR/client.csr"
log "Created $POSTGRES_CLIENT_CERT and $POSTGRES_CLIENT_KEY"

# Generate Patroni REST API certificate
log "Generating Patroni REST API certificate and key"
openssl genrsa -out "$PATRONI_API_KEY" 2048
openssl req -new -key "$PATRONI_API_KEY" -out "$SECRETS_DIR/api.csr" \
    -subj "$API_SUBJECT" -config "$OPENSSL_CONF"
openssl x509 -req -in "$SECRETS_DIR/api.csr" -CA "$CA_CERT" -CAkey "$CA_KEY" \
    -CAcreateserial -out "$PATRONI_API_CERT" -days "$DAYS_VALID" -sha256 \
    -extensions v3_req -extfile "$OPENSSL_CONF"
chmod 600 "$PATRONI_API_KEY" "$PATRONI_API_CERT"
chown "$POSTGRES_UID:$POSTGRES_UID" "$PATRONI_API_KEY" "$PATRONI_API_CERT" 2>/dev/null || true
rm "$SECRETS_DIR/api.csr"
log "Created $PATRONI_API_CERT and $PATRONI_API_KEY"

# Clean up OpenSSL config
rm "$OPENSSL_CONF"
log "Cleaned up temporary OpenSSL configuration"

# Verify certificates
log "Verifying generated certificates"
for cert in "$CA_CERT" "$POSTGRES_CLIENT_CERT" "$POSTGRES_SERVER_CERT" "$PATRONI_API_CERT"; do
    if openssl x509 -in "$cert" -text -noout >/dev/null 2>&1; then
        log "Verified: $cert"
    else
        log "ERROR: Invalid certificate: $cert"
        exit 1
    fi
done

# Output instructions
log "Certificate generation complete"
echo
echo "Certificates generated in $SECRETS_DIR:"
echo "- $CA_CERT"
echo "- $PATRONI_CA_CERT (symlink)"
echo "- $POSTGRES_CLIENT_CERT"
echo "- $POSTGRES_CLIENT_KEY"
echo "- $POSTGRES_SERVER_CERT"
echo "- $POSTGRES_SERVER_KEY"
echo "- $PATRONI_API_CERT"
echo "- $PATRONI_API_KEY"
echo
echo "Next steps:"
echo "1. Ensure .secrets/ contains password files (e.g., postgres_password.txt)."
echo "2. Run 'docker-compose -f patroni.yml up -d --build' to start the cluster."
echo "3. In production, replace self-signed certificates with trusted CA certificates."
echo
echo "Log file: $LOG_FILE"

exit 0