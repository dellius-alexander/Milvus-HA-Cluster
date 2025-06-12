FROM prom/prometheus:v2.51.0

# Metadata for image
LABEL maintainer="Dellius Alexander <admin@hyfisolutions.com>"
LABEL description="Custom Prometheus image for Milvus high-availability setup"

# Copy configuration file
COPY cfg/prometheus.yml /etc/prometheus/prometheus.yml

# Configure ports
EXPOSE 9090

# Execute Prometheus with the custom configuration
CMD ["--config.file=/etc/prometheus/prometheus.yml", "--web.listen-address=:9090", "--storage.tsdb.path=/prometheus"]
