# Patroni PostgreSQL Cluster Setup Instructions

## Overview
This configuration sets up a high-availability PostgreSQL cluster using Patroni, HAProxy, and etcd, with support for SSL in production and non-SSL in development environments. Secrets and certificates are managed by HashiCorp Vault, and configurations are templated for flexibility.

## Prerequisites
- Docker and Docker Compose installed.
- HashiCorp Vault server running (or use the included Vault service).
- Valid SSL certificates for production (generated or provided).
- Access to a Git repository for CI/CD.

## Setup Steps

1. **Set Environment Variables**
   - Create a `.env` file with:
     ```
     ENVIRONMENT=prod  # or dev
     VAULT_TOKEN=<your-vault-token>
     PATRONI_SCOPE=pg_cluster
     PATRONI_NAMESPACE=/service
     PATRONI_RESTAPI_USERNAME=patroni
     PATRONI_POSTGRESQL_USERNAME=postgres
     PATRONI_POSTGRESQL_REPLICATION_USERNAME=repl
     MILVUS_USER=milvus
     HAPROXY_STATS_USER=admin
     ```
   - Ensure `VAULT_TOKEN` is a valid Vault token for accessing secrets.

2. **Configure HashiCorp Vault**
   - Initialize Vault and enable the `secret/` engine.
   - Store secrets at `secret/data/postgres` with keys:
     - `postgres_password`
     - `repl_password`
     - `milvus_password`
     - `patroni_password`
     - `haproxy_stats_password`
     - `postgres_ca_cert`
     - `patroni_api_cert`
     - `patroni_api_key`
     - `patroni_ca_cert`
     - `postgres_server_cert`
     - `postgres_server_key`
   - Example Vault command:
     ```bash
     vault kv put secret/postgres postgres_password=<password> repl_password=<password> ...
     ```

3. **Generate SSL Certificates (Production Only)**
   - Use OpenSSL or a certificate authority to generate:
     - `postgres_ca_cert.pem`
     - `patroni_api_cert.pem`
     - `patroni_api_key.pem`
     - `patroni_ca_cert.pem`
     - `postgres_server_cert.pem`
     - `postgres_server_key.pem`
   - Store in Vault or provide manually if not using Vault.

4. **Build and Run**
   - Run `docker-compose up --build` to build and start the services.
   - The `fetch_secrets.sh` script retrieves secrets from Vault and places them in `/run/secrets`.
   - The `apply_ssl_config.sh` script configures SSL based on `ENVIRONMENT`.

5. **Monitoring**
   - Use Prometheus and Grafana to monitor cluster health:
     - Configure Prometheus to scrape Patroni REST API (`/metrics`) and HAProxy stats (`/stats`).
     - Set up Grafana dashboards for PostgreSQL metrics (e.g., connections, replication lag).
   - Check logs at `/var/log/patroni` for configuration changes and errors.

6. **CI/CD Pipeline**
   - Use GitHub Actions for automated deployment:
     ```yaml
     name: Deploy Patroni Cluster
     on:
       push:
         branches:
           - main
     jobs:
       deploy:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v3
           - name: Set up Docker Buildx
             uses: docker/setup-buildx-action@v2
           - name: Log in to Docker Hub
             uses: docker/login-action@v2
             with:
               username: ${{ secrets.DOCKER_USERNAME }}
               password: ${{ secrets.DOCKER_PASSWORD }}
           - name: Build and push images
             run: |
               docker-compose build
               docker-compose push
           - name: Deploy to server
             run: |
               ssh user@server 'docker-compose pull && docker-compose up -d'
     ```
   - Store Docker credentials in GitHub Secrets.

## Best Practices
- **Secrets Management**: Use HashiCorp Vault for secure storage and rotation of passwords and certificates.
- **Logging**: Structured JSON logging (`python-json-logger`) enables integration with monitoring systems like ELK or Loki.
- **Monitoring**: Set up alerts in Grafana for replication lag, connection spikes, or node failures.
- **Security**: Restrict network access with `PATRONI_RESTAPI_ALLOWLIST` and use `hostssl` in production.
- **High Availability**: Deploy multiple HAProxy instances with a VIP (e.g., Keepalived).
- **Backups**: Configure `archive_command` for PITR (Point-in-Time Recovery).
- **Updates**: Regularly update `postgres`, `patroni`, and `haproxy` images to the latest versions.
- **Testing**: Test failover scenarios with `patronictl` in a staging environment.

## Troubleshooting
- Check `/var/log/patroni/secrets.log` and `ssl_config.log` for issues.
- Use `patronictl -c /etc/patroni.yml list` to verify cluster status.
- Access HAProxy stats at `http://<haproxy>:8080/stats` (use credentials from Vault).
- Ensure Vault is accessible and the token is valid.

## Notes
- In development (`ENVIRONMENT=dev`), SSL is disabled for simplicity.
- In production (`ENVIRONMENT=prod`), SSL is required for PostgreSQL and REST API.
- Regularly rotate secrets in Vault for security.
- Use a configuration management tool like Ansible for large-scale deployments.