# client.Dockerfile
# This file builds a container to test our PostgreSQL cluster.
# Start with the latest Ubuntu image
FROM ubuntu:latest

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables for connecting to the database
ENV PG_HOST="postgres-haproxy"
ENV PG_PORT=5432
ENV PG_USER="admin"
ENV PG_DATABASE="milvus"
ENV HAPROXY_STATS_URL=http://${PG_HOST}:8080/stats
ENV HAPROXY_STATS_USER=admin
ENV HAPROXY_STATS_PASSWORD=admin123

# Install PostgreSQL client and other tools
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    curl ca-certificates lsb-release && \
    install -d /usr/share/postgresql-common/pgdg && \
    curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    . /etc/os-release && \
    VERSION_CODENAME=${VERSION_CODENAME:-$(lsb_release -cs)} && \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update -y && \
    apt-get install -y postgresql-client-17 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy the test script
COPY postgres_test.sh /usr/local/bin/postgres_test.sh
COPY .secrets/postgres_password.txt /run/secrets/postgres_password
COPY .secrets/repl_password.txt /run/secrets/repl_password

# Make the test script executable
RUN chmod +x /usr/local/bin/postgres_test.sh

# Create a non-root user for running tests
RUN useradd -m -s /bin/bash testuser

# Switch to the non-root user
USER testuser

# Set the working directory
WORKDIR /home/testuser

# Check if the database is ready before starting
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DATABASE" || exit 1

# Run the test script when the container starts
CMD ["/usr/local/bin/postgres_test.sh"]