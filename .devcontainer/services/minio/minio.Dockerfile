# Use official MinIO base image for object storage
FROM minio/minio:RELEASE.2025-04-08T15-41-24Z

# Metadata for image
LABEL maintainer="Dellius Alexander <admin@hyfisolutions.com>"
LABEL description="Custom MinIO image for Milvus high-availability setup"

## Install curl for health checks
#RUN microdnf install curl && microdnf clean all

# Set MinIO data directory
VOLUME /data

# Expose MinIO ports
EXPOSE 9000 9001

# Run MinIO with server command
ENTRYPOINT ["/usr/bin/minio"]
#CMD ["server", "/data", "--console-address", ":9001"]

# Purpose:
# - Uses a recent MinIO release for scalable, S3-compatible storage.
# - Enables erasure coding via environment variable for data redundancy.
# - Adds curl for health checks to verify MinIO status.
# - Configures persistent storage to prevent data loss.
# - Exposes API (9000) and console (9001) ports for management.