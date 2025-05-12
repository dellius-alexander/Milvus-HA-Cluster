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

# Purpose:
# - Uses Apache Pulsar 4.0.4 for a reliable messaging system.
# - Installs curl for health checks to monitor service status.
# - Sets up a standalone Pulsar instance for local development.
# - Exposes Pulsar ports (6650 for client connections, 8080 for REST API).
# - Allows custom configuration via environment variables.
# - Uses apply-config-from-env.py to apply environment variables to the configuration file.
# - Runs Pulsar in standalone mode with no functions worker and no stream storage.
# - The ENTRYPOINT command ensures that the Pulsar server starts with the correct configuration.
# - The --no-functions-worker and --no-stream-storage flags are used to disable the functions worker and stream storage, respectively.
# - This is useful for local development and testing purposes, where you may not need these features.
# - The ENTRYPOINT command also uses /bin/bash -c to allow for the execution of multiple commands in a single line.
# - This is useful for applying the configuration and starting the Pulsar server in one step.
# - The WORKDIR directive sets the working directory for the container to /pulsar, which is where the Pulsar binaries are located.
# - The EXPOSE directive exposes the Pulsar ports (6650 and 8080) for client connections and REST API access, respectively.
# - The RUN directive installs curl for health checks and debugging purposes.
# - The apt-get update command updates the package list, and the apt-get install command installs curl.
# - The apt-get clean command removes unnecessary files to reduce the image size.
# - The LABEL directive adds metadata to the image, including the maintainer and description.
# - The FROM directive specifies the base image for the container, which is Apache Pulsar 4.0.4 in this case.
# - The FROM directive also specifies the version of Pulsar to use, which is 4.0.4 in this case.



