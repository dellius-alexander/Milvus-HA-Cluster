# haproxy.Dockerfile
# This file builds the HAProxy image to balance traffic between our database servers.
# Start with the latest HAProxy long-term support image
FROM haproxy:lts

# Run as root to set up files and permissions
USER root

# Add metadata to the image
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="HAProxy load balancer for PostgreSQL cluster"

# Copy the HAProxy configuration file
COPY cfg/haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

# Set permissions for the configuration file
RUN groupadd -r haproxy 2>/dev/null || true && \
    useradd -r -g haproxy haproxy 2>/dev/null || true && \
    chown haproxy:haproxy /usr/local/etc/haproxy/haproxy.cfg && \
    chmod 644 /usr/local/etc/haproxy/haproxy.cfg

# Create and set permissions for the runtime directory
RUN mkdir -p /var/run && \
    chown haproxy:haproxy /var/run && \
    chmod 770 /var/run

# Expose ports for PostgreSQL traffic and stats page
EXPOSE 5432 5433 5434 5435 8080

# Switch to the haproxy user for security
USER haproxy

# Start HAProxy with our configuration file
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
