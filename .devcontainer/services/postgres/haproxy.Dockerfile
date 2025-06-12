# haproxy.Dockerfile
# Builds an HAProxy image for load balancing a Patroni PostgreSQL cluster.
# Uses ssl_config.yml to configure SSL for Patroni REST API health checks.
# Toggles SSL with ENABLE_SSL environment variable.

FROM haproxy:2.8

USER root

# Add metadata to the image
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="HAProxy for Patroni PostgreSQL cluster"

# Install dependencies
RUN apt-get update && \
    apt-get install -y gettext-base && \
    rm -rf /var/lib/apt/lists/*

# Copy configuration files and secrets
COPY cfg/haproxy.cfg.tmpl /usr/local/etc/haproxy/haproxy.cfg.tmpl
COPY cfg/ssl_config.yml /tmp/ssl_config.yml
COPY .secrets/patroni_password.txt /run/secrets/patroni_password
COPY .secrets/haproxy_stats_password.txt /run/secrets/haproxy_stats_password
COPY .secrets/postgres_ca_cert.pem /tmp/secrets/postgres_ca_cert.pem

# Copy CA certificate if ENABLE_SSL is true
RUN if [ "$ENABLE_SSL" = "true" ]; then \
        cp /tmp/secrets/postgres_ca_cert.pem /run/secrets/postgres_ca_cert && \
        chown haproxy:haproxy /run/secrets/postgres_ca_cert && \
        chmod 600 /run/secrets/postgres_ca_cert; \
    fi

# Set permissions for secrets
RUN chown haproxy:haproxy \
    /run/secrets/patroni_password \
    /run/secrets/haproxy_stats_password && \
    chmod 600 /run/secrets/patroni_password \
    /run/secrets/haproxy_stats_password

# Generate haproxy.cfg with environment variable substitution
RUN envsubst < /usr/local/etc/haproxy/haproxy.cfg.tmpl > /usr/local/etc/haproxy/haproxy.cfg && \
    rm /usr/local/etc/haproxy/haproxy.cfg.tmpl /tmp/ssl_config.yml

USER haproxy

# Expose HAProxy ports
EXPOSE 5432 8080

# Run HAProxy
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]

# Notes:
# - SSL settings for health checks are sourced from ssl_config.yml.
# - CA certificate is copied only if ENABLE_SSL=true.
# - File permissions are set to 600 for sensitive files.