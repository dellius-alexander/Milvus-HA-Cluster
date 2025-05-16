FROM grafana/grafana:10.4.0

# Metadata for the image
LABEL maintainer="Dellius Alexander <admin@hyfisolutions.com>"
LABEL description="Custom Grafana image for Milvus high-availability setup"

# Copy dashboards and provisioning configuration
COPY cfg/dashboards/ /var/lib/grafana/dashboards/
COPY cfg/provisioning/ /etc/grafana/provisioning/
