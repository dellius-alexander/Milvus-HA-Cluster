# Use official etcd base image for reliability
FROM quay.io/coreos/etcd:v3.5.18

# Metadata for image
LABEL maintainer="Dellius Alexander <admin@hyfisolutions.com>"
LABEL description="Custom etcd image for Milvus high-availability setup"

# Install necessary tools for health checks and debugging
#RUN apt-get add --no-cache curl

# Set working directory
WORKDIR /etcd

# Expose etcd ports
EXPOSE 2379
EXPOSE 2380

# Run etcd as the entrypoint
# --cert-file=/path/to/server.crt --key-file=/path/to/server.key \
  #  --advertise-client-urls=https://127.0.0.1:2379 --listen-client-urls=https://127.0.0.1:2379
#ENTRYPOINT ["/usr/local/bin/etcd", "--name=etcd0", "--data-dir=/etcd_data", "--cert-file=/etc/ssl/certs/etcd.crt", "--key-file=/etc/ssl/certs/etcd.key", "--advertise-client-urls=https://etcd:2379", "--listen-client-urls=https://etcd:2379"]
#ENTRYPOINT ["/usr/local/bin/etcd"]
# Purpose:
# - Uses a stable etcd version (v3.5.15) for distributed coordination.
# - Adds curl for health checks to ensure etcd is operational.
# - Keeps the image lightweight while enabling debugging capabilities.
# - Configured for high availability with persistent data volume.
