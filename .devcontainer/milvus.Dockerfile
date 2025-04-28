# Use official Milvus standalone base image
FROM milvusdb/milvus:v2.5.9

# Metadata for image
LABEL maintainer="Dellius Alexander <admin@hyfisolutions.com>"
LABEL description="Custom Milvus standalone image for high-availability setup"

# Install dependencies for health checks and monitoring
RUN apt-get update && apt-get install -y curl && apt-get clean

# Set working directory
WORKDIR /var/lib/milvus

# Copy custom configuration (optional, adjust as needed)
COPY .devcontainer/cfg/milvus.yaml /milvus/configs/milvus.yaml

# Expose Milvus ports
#EXPOSE 19530
#EXPOSE 9091

# Run Milvus standalone
ENTRYPOINT ["/milvus/bin/milvus"]
#CMD ["run", "standalone"]

# Purpose:
# - Uses Milvus v2.4.12, a stable release for production.
# - Installs curl for health checks to monitor service status.
# - Supports persistent volumes for data and logs to ensure durability.
# - Exposes gRPC (19530) and RESTful API (9091) ports for client access.
# - Allows custom configuration via milvus.yaml (commented out for default).
