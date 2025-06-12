FROM haproxy:lts
USER root

# Metadata for image
LABEL maintainer="Dellius Alexander <admin@hyfisolutions.com>"
LABEL description="Custom HAProxy image for Minio high-availability setup"

# Copy configuration file
COPY cfg/haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

# Set permissions for configuration file
RUN groupadd -r haproxy 2>/dev/null || true && useradd -r -g haproxy haproxy 2>/dev/null || true
RUN chown haproxy:haproxy /usr/local/etc/haproxy/haproxy.cfg
RUN chmod 644 /usr/local/etc/haproxy/haproxy.cfg

# Ensure /var/run exists and has correct permissions
RUN mkdir -p /var/run && chown haproxy:haproxy /var/run && chmod 770 /var/run

# Expose necessary ports: etcd (2379)
EXPOSE 9000 9001

# Run HAProxy as the haproxy user
USER haproxy
#ENTRYPOINT ["/usr/local/sbin/haproxy"]
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]