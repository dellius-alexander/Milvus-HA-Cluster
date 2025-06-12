# High-Availability PostgreSQL Cluster with Patroni and Docker Compose

This project sets up a high-availability (HA) PostgreSQL 17 cluster using Docker Compose, 
managed by Patroni, with one primary node for write operations and three replica nodes for 
read-only queries. HAProxy balances traffic, directing writes to the primary and reads to replicas. 
An Etcd cluster provides distributed consensus, and a client container tests the setup. This guide 
covers setup, configuration, testing, verification, and best practices for a robust Patroni PostgreSQL 
HA cluster.

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
   - [Directory Structure](#directory-structure)
   - [Mermaid Diagram](#mermaid-diagram)
3. [Prerequisites](#prerequisites)
4. [Setup Instructions](#setup-instructions)
5. [Configuration Details](#configuration-details)
   - [Docker Compose and Patroni](#docker-compose-and-patroni)
   - [PostgreSQL Configuration](#postgresql-configuration)
   - [HAProxy Configuration](#haproxy-configuration)
   - [Etcd Configuration](#etcd-configuration)
6. [Testing and Verification](#testing-and-verification)
   - [Using Docker](#using-docker)
   - [Using Docker and `patronictl`](#using-docker-and-patronictl)
   - [Testing with Python](#testing-with-python)
   - [Failover and Network Partition Testing](#failover-and-network-partition-testing)
7. [Interacting with the Cluster](#interacting-with-the-cluster)
   - [Using `psql`](#using-psql)
   - [Using GUI Tools](#using-gui-tools)
   - [Application Connectivity](#application-connectivity)
8. [Best Practices](#best-practices)
   - [Node Count and Topology](#node-count-and-topology)
   - [Security](#security)
   - [Monitoring and Alerting](#monitoring-and-alerting)
   - [Backup and Recovery](#backup-and-recovery)
   - [Resource Management](#resource-management)
   - [Regular Testing](#regular-testing)
9. [Troubleshooting](#troubleshooting)
10. [References](#references)

## Overview
This project creates a robust PostgreSQL HA cluster using:
- **Patroni**: Automates leader election, failover, replication, and cluster management.
- **PostgreSQL 17**: One primary node (`patroni-replica1`) for writes and three replicas (`patroni-replica0`, `patroni-replica2`, `patroni-replica3`) for reads.
- **HAProxy**: Load balancer directing write queries to the primary (port 5432) and read queries to replicas (port 5433).
- **Etcd**: Three-node cluster (`etcd0`, `etcd1`, `etcd2`) with a proxy (`etcd-proxy`) for distributed consensus.
- **Docker Compose**: Orchestrates services, networks, and volumes.
- **Client**: Tests connectivity, CRUD operations, and replication.

The cluster uses streaming replication for data consistency, persistent volumes for durability, and Patroni’s REST API for health checks and management. It’s designed for mission-critical applications requiring high availability, scalability, and automated failover.

## Architecture
The system comprises:
- **Patroni Nodes**: Four PostgreSQL instances (`patroni-replica0` to `patroni-replica3`), one acting as the primary and three as replicas.
- **HAProxy**: Routes traffic based on Patroni’s REST API health checks (`/leader` for primary, `/replica` for replicas).
- **Etcd Cluster**: Three nodes (`etcd0`, `etcd1`, `etcd2`) plus a proxy (`etcd-proxy`) for quorum and cluster state management.
- **Networks**: `patroni-network`, `etcd-network`, `etcd-proxy-network`, and `postgres-proxy-network` for isolated communication.
- **Volumes**: Persistent storage for PostgreSQL data (`replica0-data` to `replica3-data`) and Etcd data (`etcd0-data` to `etcd2-data`).
- **Secrets**: Secure storage for passwords (`postgres_password`, `repl_password`, `milvus_password`, `patroni_password`).

### Directory Structure
```text
.
├── ENVIRONMENT-Patroni.rst
├── ENVIRONMENT-PostgreSQL.md
├── README.md
├── cfg
│   ├── haproxy.cfg.tmpl
│   ├── patroni-conf.yml
│   ├── pg_hba.conf
│   ├── postgresql.auto.conf
│   ├── postgresql.base.conf
│   ├── postgresql.master.conf
│   ├── postgresql.orig.conf
│   ├── postgresql.replica.conf
├── client.Dockerfile
├── client.yaml
├── create_secrets.sh
├── haproxy.Dockerfile
├── init-replica.sh
├── initdb.d
│   ├── 00_init.sql
│   ├── init-user-db.sh
├── patroni.Dockerfile
├── patroni.mermaid
├── patroni.yml
├── pg_repository.sh
├── postgres.Dockerfile
├── postgres.http
├── postgres.yml
├── postgres_test.sh
├── secrets
│   ├── milvus_password.txt
│   ├── patroni_password.txt
│   ├── postgres_password.txt
│   ├── repl_password.txt
│   ├── secrets.json
```

### Mermaid Diagram
The following diagram, based on the `patroni.yml` service definition, illustrates the cluster architecture, highlighting service interactions, network isolation, and data flows.

```mermaid
graph TD
    subgraph ClientApp[Client Application]
        App[Client] -->|Write: 5432|HP[HAProxy: patroni-haproxy]
        App -->|Read: 5433|HP
        App -->|Stats: 8080|HP
    end

    subgraph PostgresProxyNetwork[postgres-proxy-network]
        HP
    end

    subgraph PatroniNetwork[patroni-network]
        HP -->|"Primary (PG Port): 5432"|PR1[patroni-replica1:5432<br>Primary]
        HP -->|"Replicas (PG Port): 5432"|PR0[patroni-replica0:5432<br>Replica]
        HP -->|"Replicas (PG Port): 5432"|PR2[patroni-replica2:5432<br>Replica]
        HP -->|"Replicas (PG Port): 5432"|PR3[patroni-replica3:5432<br>Replica]
        HP -->|Health Checks: 8008|PR0API[patroni-replica0:8008<br>Patroni API]
        HP -->|Health Checks: 8008|PR1API[patroni-replica1:8008<br>Patroni API]
        HP -->|Health Checks: 8008|PR2API[patroni-replica2:8008<br>Patroni API]
        HP -->|Health Checks: 8008|PR3API[patroni-replica3:8008<br>Patroni API]

        PR1 -->|Streaming Replication|PR0
        PR1 -->|Streaming Replication|PR2
        PR1 -->|Streaming Replication|PR3
        PR0 -->|pg_rewind|PR1
        PR2 -->|pg_rewind|PR1
        PR3 -->|pg_rewind|PR1
    end

    subgraph EtcdProxyNetwork[etcd-proxy-network]
        PR0 -->|Consensus|EP[etcd-proxy:2379]
        PR1 -->|Consensus|EP
        PR2 -->|Consensus|EP
        PR3 -->|Consensus|EP
    end

    subgraph EtcdNetwork[etcd-network]
        EP -->|Client Requests|E0[etcd0:2379]
        EP -->|Client Requests|E1[etcd1:2379]
        EP -->|Client Requests|E2[etcd2:2379]
        E0 -->|Peer Sync|E1
        E0 -->|Peer Sync|E2
        E1 -->|Peer Sync|E0
        E1 -->|Peer Sync|E2
        E2 -->|Peer Sync|E0
        E2 -->|Peer Sync|E1
    end

    subgraph PersistentStorage[Persistent Storage]
        PR0 -->|Data|RD0[replica0-data]
        PR1 -->|Data|RD1[replica1-data]
        PR2 -->|Data|RD2[replica2-data]
        PR3 -->|Data|RD3[replica3-data]
        E0 -->|Data|ED0[etcd0-data]
        E1 -->|Data|ED1[etcd1-data]
        E2 -->|Data|ED2[etcd2-data]
    end

    style HP fill:#bbf,stroke:#333,stroke-width:2px,color:#000
    style PR1 fill:#f9f,stroke:#333,stroke-width:2px,color:#000
    style PR0 fill:#ccf,stroke:#333,stroke-width:2px,color:#000
    style PR2 fill:#ccf,stroke:#333,stroke-width:2px,color:#000
    style PR3 fill:#ccf,stroke:#333,stroke-width:2px,color:#000
    style PR0API fill:#dfd,stroke:#333,stroke-width:1px,color:#000
    style PR1API fill:#dfd,stroke:#333,stroke-width:1px,color:#000
    style PR2API fill:#dfd,stroke:#333,stroke-width:1px,color:#000
    style PR3API fill:#dfd,stroke:#333,stroke-width:1px,color:#000
    style EP fill:#ffb,stroke:#333,stroke-width:2px,color:#000
    style E0 fill:#ffb,stroke:#333,stroke-width:1px,color:#000
    style E1 fill:#ffb,stroke:#333,stroke-width:1px,color:#000
    style E2 fill:#ffb,stroke:#333,stroke-width:1px,color:#000

    linkStyle 0,1 stroke:#000,stroke-width:2px
    linkStyle 2 stroke:#000,stroke-width:1px
    linkStyle 3,4,5,6 stroke:#000,stroke-width:2px
    linkStyle 7,8,9,10 stroke:#f60,stroke-width:1px,stroke-dasharray: 5 5
    linkStyle 11,12,13 stroke:#00f,stroke-width:2px
    linkStyle 14,15,16 stroke:#00f,stroke-width:1px,stroke-dasharray: 5 5
    linkStyle 17,18,19 stroke:#0f0,stroke-width:2px
    linkStyle 20,21,22,23,24,25 stroke:#0f0,stroke-width:1px
    linkStyle 26,27,28,29,30,31,32 stroke:#666,stroke-width:1px

```

## Prerequisites
- **Docker** and **Docker Compose** installed.
- Basic understanding of PostgreSQL, Patroni, and Docker.
- A text editor to create configuration and secret files.
- Minimum system resources: 8GB RAM, 4 CPU cores, 50GB disk space for testing.
- Network access for Docker images (e.g., `postgres:17.5`, `haproxy:lts`, `bitnami/etcd:latest`).

## Setup Instructions
1. **Clone the Repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Create Secret Files**:
   ```bash
   mkdir .secrets
   echo "securepassword123" > .secrets/postgres_password.txt
   echo "replpassword123" > .secrets/repl_password.txt
   echo "milvuspassword123" > .secrets/milvus_password.txt
   echo "patronipassword123" > .secrets/patroni_password.txt
   ```

3. **Create Configuration Directory**:
   ```bash
   mkdir cfg
   ```
   Copy or create `postgresql-base.conf`, `postgresql-master.conf`, `postgresql-replica.conf`, `pg_hba.conf`, and `haproxy.cfg.tmpl` in the `cfg` directory. Example `haproxy.cfg.tmpl` is provided in previous responses.

4. **Create `.env` File**:
   ```bash
   echo "PATRONI_SCOPE=pg_cluster
    PATRONI_NAMESPACE=/pg_cluster
    PATRONI_RESTAPI_LISTEN=0.0.0.0:8008
    PATRONI_RESTAPI_USERNAME=patroni
    PATRONI_RESTAPI_PASSWORD_FILE=/run/secrets/patroni_password
    PATRONI_ETCD3_HOSTS=etcd-proxy:2379
    PATRONI_ETCD3_PROTOCOL=http
    PATRONI_ETCD3_USE_PROXIES=true
    PATRONI_POSTGRESQL_LISTEN=0.0.0.0:5432
    PATRONI_POSTGRESQL_DATA_DIR=/var/lib/postgresql/data
    PATRONI_POSTGRESQL_USERNAME=admin
    POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
    PATRONI_POSTGRESQL_REPLICATION_USERNAME=repl
    PATRONI_POSTGRESQL_REPLICATION_PASSWORD_FILE=/run/secrets/repl_password
    PATRONI_LOG_LEVEL=DEBUG
    HAPROXY_STATS_USER=admin
    HAPROXY_STATS_PASSWORD=admin123
    PATRONI_RESTAPI_AUTH_HEADER=$(echo -n 'patroni:patronipassword123' | base64)
    PGDATA=/var/lib/postgresql/data" > .env
   ```

5. **Build and Run**:
   ```bash
   docker-compose -f patroni.yml up -d
   ```

6. **Verify Setup**:
   Check service logs:
   ```bash
   docker logs patroni-replica1
   docker logs patroni-haproxy
   ```
   Access HAProxy stats at `http://localhost:8080/stats` (username: `admin`, password: `admin123`).

## Configuration Details

### Docker Compose and Patroni
- **File**: `patroni.yml`
- Defines services: `etcd0`, `etcd1`, `etcd2`, `etcd-proxy`, `patroni-replica0` to `patroni-replica3`, and `patroni-haproxy`.
- Networks: `patroni-network` (PostgreSQL and HAProxy), `etcd-network` (Etcd nodes), `etcd-proxy-network` (Patroni to Etcd proxy), `postgres-proxy-network` (external access).
- Volumes: Persistent storage for data (`replica0-data` to `replica3-data`, `etcd0-data` to `etcd2-data`).
- Secrets: Passwords for PostgreSQL (`postgres_password`, `repl_password`, `milvus_password`) and Patroni (`patroni_password`).
- Patroni configuration is driven by environment variables (`.env`) and Docker build arguments.

### PostgreSQL Configuration
- **postgresql-base.conf**: Shared settings (e.g., `listen_addresses='*'`, `max_connections=100`, `huge_pages=off`).
- **postgresql-master.conf**: Primary-specific settings (e.g., `archive_mode=on`, `archive_command='mkdir -p ../archive && cp %p ../archive/%f'`).
- **postgresql-replica.conf**: Replica-specific settings (e.g., `hot_standby=on`, `default_transaction_read_only=on`).
- **pg_hba.conf**: Uses SCRAM-SHA-256 authentication:
  ```plaintext
  host all all 0.0.0.0/0 scram-sha-256
  host replication repl 0.0.0.0/0 scram-sha-256
  ```

### HAProxy Configuration
- **haproxy.cfg.tmpl**: Configured to:
  - Route writes to the primary via `/leader` health checks (port 5432).
  - Distribute reads to replicas via `/replica` health checks (port 5433).
  - Provide stats at port 8080.
  - Use `http-check` with `PATRONI_RESTAPI_AUTH_HEADER` for authenticated Patroni API access.
  - Example configuration provided in previous responses ensures dynamic `Host` headers and proper user settings.

### Etcd Configuration
- **etcd.yaml**: Defines three Etcd nodes and a proxy.
- Each node listens on `2379` (client) and `2380` (peer) with persistent volumes.
- Proxy (`etcd-proxy`) simplifies Patroni access to Etcd quorum.

## Testing and Verification

### Using Docker
Test cluster health and functionality directly with Docker commands:
1. **Check Service Status**:
   ```bash
   docker ps
   ```
   Verify all services (`patroni-replica0` to `patroni-replica3`, `patroni-haproxy`, `etcd0` to `etcd2`, `etcd-proxy`) are running.

2. **Inspect Logs**:
   ```bash
   docker logs patroni-replica1
   docker logs patroni-haproxy
   ```
   Look for errors or confirm replication (`streaming` state) and HAProxy routing.

3. **Test Connectivity**:
   Connect to the primary via HAProxy:
   ```bash
   docker run -it postgres:17.5 psql -h localhost -p 5432 -U admin -d postgres
   ```
   Run `SELECT * FROM pg_stat_replication;` to verify replica connections.

4. **Test Replication**:
   Create a test table on the primary:
   ```bash
   docker exec -it patroni-haproxy psql -h patroni-replica1 -p 5432 -U admin -d postgres -c "CREATE TABLE test_table (id SERIAL PRIMARY KEY, value TEXT); INSERT INTO test_table (value) VALUES ('Test');"
   ```
   Verify on a replica:
   ```bash
   docker run -it postgres:17.5 psql -h localhost -p 5433 -U admin -d postgres -c "SELECT * FROM test_table;"
   ```

5. **Simulate Failure**:
   Stop the primary:
   ```bash
   docker stop patroni-replica1
   ```
   Check HAProxy stats (`http://localhost:8080/stats`) to confirm a new primary is elected.

### Using Docker and `patronictl`
`patronictl` is Patroni’s CLI tool for cluster management. Use it within Docker containers to verify and interact with the cluster:
1. **Access `patronictl`**:
   ```bash
   docker exec -it patroni-replica0 bash
   patronictl -c /etc/patroni.yml list
   ```
   Expected output (based on provided logs):
   ```
   + Cluster: pg_cluster (7513374972804124694) ----+-----------+----+-----------+-----------------+
   | Member           | Host             | Role    | State     | TL | Lag in MB | Tags            |
   +------------------+------------------+---------+-----------+----+-----------+-----------------+
   | patroni-replica0 | patroni-replica0 | Replica | streaming |  9 |         0 | clonefrom: true |
   | patroni-replica1 | patroni-replica1 | Leader  | running   |  9 |           | clonefrom: true |
   | patroni-replica2 | patroni-replica2 | Replica | streaming |  9 |         0 | clonefrom: true |
   | patroni-replica3 | patroni-replica3 | Replica | streaming |  9 |         0 | clonefrom: true |
   +------------------+------------------+---------+-----------+----+-----------+-----------------+
   ```

2. **Check Configuration**:
   ```bash
   patronictl -c /etc/patroni.yml show-config
   ```
   Verify settings like `maximum_lag_on_failover` and `postgresql.parameters`.

3. **Initiate Switchover**:
   ```bash
   patronictl -c /etc/patroni.yml switchover --candidate patroni-replica0
   ```
   Confirm the new primary with `patronictl list`.

4. **Reinitialize Replica**:
   If a replica lags or fails:
   ```bash
   patronictl -c /etc/patroni.yml reinit patroni-replica2
   ```

5. **Verify Health**:
   Check Patroni REST API:
   ```bash
   docker exec patroni-replica0 curl -u patroni:securepassword123 http://localhost:8008/health
   ```
   Expect a 200 OK response.

### Testing with Python
Use Python scripts with `psycopg2` and `requests` to automate testing (from `README2.md`):
1. **Basic Connectivity Test**:
   ```python
   import psycopg2

   def connect_to_pg(host, port, dbname, user, password):
       try:
           conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
           print(f"Connected to {host}:{port}")
           return conn
       except psycopg2.OperationalError as e:
           print(f"Connection failed: {e}")
           return None

   conn = connect_to_pg("localhost", 5432, "postgres", "admin", "securepassword123")
   if conn:
       conn.close()
   ```

2. **Replication Test**:
   ```python
   import psycopg2
   import time

   def insert_data(conn, value):
       with conn.cursor() as cur:
           cur.execute("CREATE TABLE IF NOT EXISTS test_data (id SERIAL PRIMARY KEY, value TEXT);")
           cur.execute("INSERT INTO test_data (value) VALUES (%s);", (value,))
           conn.commit()

   def read_data(conn):
       with conn.cursor() as cur:
           cur.execute("SELECT value FROM test_data ORDER BY id DESC LIMIT 1;")
           return cur.fetchone()[0] if cur.fetchone() else None

   primary_conn = connect_to_pg("localhost", 5432, "postgres", "admin", "securepassword123")
   insert_data(primary_conn, "Test")
   primary_conn.close()

   time.sleep(2)
   replica_conn = connect_to_pg("localhost", 5433, "postgres", "admin", "securepassword123")
   assert read_data(replica_conn) == "Test", "Replication failed"
   replica_conn.close()
   ```

3. **Patroni API Test**:
   ```python
   import requests

   def get_cluster_status(url, user, password):
       response = requests.get(f"{url}/cluster", auth=(user, password))
       response.raise_for_status()
       return response.json()

   status = get_cluster_status("http://localhost:8008", "patroni", "patronipassword123")
   print(status)
   ```

### Failover and Network Partition Testing
1. **Failover Test**:
   - Stop the primary:
     ```bash
     docker stop patroni-replica1
     ```
   - Verify new leader with `patronictl list`.
   - Check application connectivity to port 5432.

2. **Network Partition Test**:
   - Simulate a partition by pausing an Etcd node:
     ```bash
     docker pause etcd0
     ```
   - Observe cluster behavior with `patronictl list`.
   - Resume the node:
     ```bash
     docker unpause etcd0
     ```

3. **Data Consistency Check**:
   - Insert data before failover:
     ```bash
     docker exec -it patroni-haproxy psql -h patroni-replica1 -p 5432 -U admin -d postgres -c "INSERT INTO test_data (value) VALUES ('Pre-failover');"
     ```
   - After failover, verify on new primary:
     ```bash
     docker run -it postgres:17.5 psql -h localhost -p 5432 -U admin -d postgres -c "SELECT * FROM test_data;"
     ```

## Interacting with the Cluster

### Using `psql`
Connect to the primary via HAProxy:
```bash
psql -h localhost -p 5432 -U admin -d postgres
```
Connect to a replica:
```bash
psql -h localhost -p 5433 -U admin -d postgres
```

### Using GUI Tools
Use tools like DBeaver or pgAdmin:
- Host: `localhost`
- Port: `5432` (primary) or `5433` (replicas)
- Username: `admin`
- Password: `securepassword123`
- Database: `postgres`

### Application Connectivity
Configure applications to connect via HAProxy:
```python
from sqlalchemy import create_engine
engine = create_engine("postgresql://admin:securepassword123@localhost:5432/postgres")
```

## Best Practices

### Node Count and Topology
- Use at least three PostgreSQL nodes (one primary, two replicas) and three Etcd nodes for quorum.
- Deploy Etcd and PostgreSQL on separate hosts in production to avoid resource contention.
- Distribute nodes across availability zones for disaster recovery.

### Security
- Use SCRAM-SHA-256 in `pg_hba.conf`.
- Enable SSL/TLS for PostgreSQL and Patroni API.
- Store passwords in secrets management (e.g., Docker secrets).
- Restrict network access with firewalls (ports 5432, 8008, 2379, 2380).

### Monitoring and Alerting
- Monitor with Prometheus and Grafana using Patroni’s `/metrics` endpoint.
- Set alerts for primary failure, high replication lag, Etcd quorum loss, and resource utilization.
- Centralize logs with Fluentd or Loki.

### Backup and Recovery
- Use `pgBackRest` for automated backups and PITR.
- Store WAL archives off-site (e.g., S3).
- Test restores regularly.

### Resource Management
- Provision SSDs for PostgreSQL and Etcd.
- Set `nofile` limits to 65535.
- Tune PostgreSQL parameters (`shared_buffers`, `work_mem`) based on workload.

### Regular Testing
- Conduct failover drills in staging.
- Simulate network partitions and resource exhaustion.
- Verify data consistency post-failover.

## Troubleshooting
- **HAProxy Socket Errors**:
  - Verify Patroni API accessibility:
    ```bash
    docker exec patroni-haproxy curl -u patroni:patronipassword123 http://patroni-replica0:8008/leader
    ```
  - Check network connectivity:
    ```bash
    docker exec patroni-haproxy ping patroni-replica0
    ```
  - Ensure `option httpchk` in `haproxy.cfg`.

- **Replication Issues**:
  - Check `pg_stat_replication`:
    ```bash
    docker exec -it patroni-replica1 psql -U admin -d postgres -c "SELECT * FROM pg_stat_replication;"
    ```
  - Review replica logs:
    ```bash
    docker logs patroni-replica0
    ```

- **Huge Pages Error**:
  - Ensure `huge_pages=off` in `postgresql-base.conf` or configure host huge pages:
    ```bash
    sudo sysctl -w vm.nr_hugepages=128
    ```

## References
- [Patroni Documentation](https://patroni.readthedocs.io/en/latest/)
- [PostgreSQL 17 Documentation](https://www.postgresql.org/docs/17/)
- [Etcd Documentation](https://etcd.io/docs/)
- [HAProxy Documentation](https://www.haproxy.com/documentation/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [pytest Documentation](https://docs.pytest.org/en/stable/)
