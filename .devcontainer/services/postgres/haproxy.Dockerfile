# haproxy.Dockerfile
# Builds an HAProxy image for load balancing a Patroni PostgreSQL cluster.
# Supports SSL in production (ENVIRONMENT=prod) and non-SSL in development (ENVIRONMENT=dev).
# Uses HashiCorp Vault for secrets.

FROM haproxy:2.8

USER root

# Add metadata
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="HAProxy for Patroni PostgreSQL cluster"

# Install dependencies
RUN apt-get update && \
    apt-get install -y gettext-base curl && \
    rm -rf /var/lib/apt/lists/*

# Copy configuration files and scripts
COPY cfg/haproxy.cfg.tmpl /tmp/haproxy.cfg.tmpl
COPY scripts/fetch_secrets.sh /tmp/fetch_secrets.sh

# Run fetch_secrets.sh to retrieve secrets from Vault
RUN bash /tmp/fetch_secrets.sh && \
    rm /tmp/fetch_secrets.sh

# Generate haproxy.cfg with environment variable substitution
RUN envsubst < /tmp/haproxy.cfg.tmpl > /usr/local/etc/haproxy/haproxy.cfg && \
    rm /tmp/haproxy.cfg.tmpl

USER haproxy

# Expose HAProxy ports
EXPOSE 5432 5433 8080

# Run HAProxy
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]

# Notes:
# - Secrets are fetched from HashiCorp Vault via fetch_secrets.sh.
# - Set ENVIRONMENT=prod for SSL-enabled health checks; ENVIRONMENT=dev for non-SSL.
# - Monitor HAProxy stats dashboard at port 8080.