FROM apachepulsar/pulsar:4.0.4

# Metadata for the image
LABEL maintainer="Dellius Alexander admin@hyfisolutions.com"
LABEL description="Custom Pulsar image for Milvus high-availability setup"

## Install necessary tools for health checks and debugging
#RUN apt-get update && \
#    apt-get install -y curl && \
#    apt-get clean

# Set the working directory
WORKDIR /pulsar

# Expose Pulsar ports
EXPOSE 6650
EXPOSE 8080

# Run Pulsar standalone with custom configuration
ENTRYPOINT ["/bin/bash", "-c", "bin/apply-config-from-env.py conf/standalone.conf && exec bin/pulsar standalone --no-functions-worker --no-stream-storage"]
