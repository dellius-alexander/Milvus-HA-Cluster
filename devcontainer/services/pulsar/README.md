# Apache Pulsar Cluster

> **Purpose**: To complete the Apache Pulsar cluster setup with 3 brokers, 
> 3 bookies, 3 ZooKeepers, and an HAProxy load balancer using Docker 
> Compose, we need to create configuration files (`broker.conf`, `zookeeper.conf`, 
> and `bookkeeper.conf`) that reflect the implementation and incorporate 
> best practices. These files will be mounted into the respective containers to 
> override the default configurations, ensuring consistency, performance, and 
> fault tolerance.

### Approach
- **Why Custom Config Files?**: While the previous `docker-compose.yml` uses environment variables and `apply-config-from-env.py` to configure services, mounting explicit configuration files provides better control, readability, and maintainability, especially for production-like setups. This approach avoids reliance on environment variable parsing and ensures all settings are documented in one place.
- **Best Practices**:
  - **ZooKeeper**: Configure a 3-node ensemble with optimized memory settings, tick time, and snapshot policies for reliability and performance.
  - **BookKeeper**: Set up bookies with proper journal and ledger directories, optimized write/read caches, and fault-tolerant replication settings.
  - **Brokers**: Configure brokers to use HAProxy as the advertised address, enable load balancing, and tune performance parameters like message batching and managed ledger settings.
  - **Consistency**: Align configurations with the `docker-compose.yml` (e.g., cluster name `cluster-a`, ZooKeeper quorum `zookeeper1:2181,zookeeper2:2181,zookeeper3:2181`, HAProxy endpoints `haproxy:6650` and `haproxy:8080`).
  - **Performance**: Use conservative memory settings for testing but include comments for production tuning.
  - **Persistence**: Leverage the mounted volumes (`./data/zookeeper{1,2,3}`, `./data/bookkeeper{1,2,3}`) for data durability.
- **Implementation**: Each service (ZooKeeper, BookKeeper, broker) will have a tailored configuration file mounted via Docker Compose volumes. The `docker-compose.yml` will be updated to mount these files and remove redundant environment variables where possible.

Below, I’ll provide the configuration files (`zookeeper.conf`, `bookkeeper.conf`, `broker.conf`), an updated `docker-compose.yml` to incorporate them, and explanations of key settings.

---

### Configuration Files

1. **zookeeper.conf** (for ZooKeeper nodes)
   Create a file named `zookeeper.conf` in the same directory as `docker-compose.yml`. This file configures the ZooKeeper ensemble for all three nodes (`zookeeper1`, `zookeeper2`, `zookeeper3`).

   ```conf
   # ZooKeeper configuration for Apache Pulsar cluster
   tickTime=2000
   initLimit=10
   syncLimit=5
   dataDir=/pulsar/data/zookeeper
   clientPort=2181
   maxClientCnxns=60
   autopurge.snapRetainCount=3
   autopurge.purgeInterval=1
   server.1=zookeeper1:2888:3888
   server.2=zookeeper2:2888:3888
   server.3=zookeeper3:2888:3888
   4lw.commands.whitelist=*

   # JVM options for memory and GC
   jvm.memory=-Xms256m -Xmx256m -XX:MaxDirectMemorySize=256m
   jvm.gcOptions=-XX:+UseG1GC -XX:MaxGCPauseMillis=200
   ```

   **Key Settings**:
   - `tickTime=2000`: Basic time unit (ms) for heartbeats and timeouts.
   - `initLimit=10`, `syncLimit=5`: Allow 10 ticks (20s) for initial sync and 5 ticks (10s) for follower sync, suitable for a small ensemble.
   - `dataDir=/pulsar/data/zookeeper`: Maps to the mounted volume for persistent storage.
   - `clientPort=2181`: Standard ZooKeeper client port.
   - `maxClientCnxns=60`: Limits connections to prevent overload in a small cluster.
   - `autopurge.snapRetainCount=3`, `autopurge.purgeInterval=1`: Purges old snapshots hourly, keeping the last 3 to manage disk space.
   - `server.1`, `server.2`, `server.3`: Defines the 3-node ensemble with leader election ports (2888) and quorum ports (3888).
   - `4lw.commands.whitelist=*`: Allows all 4-letter commands (e.g., `ruok`) for monitoring.
   - `jvm.memory`: Conservative heap (256MB) for testing; increase to 1-2GB for production.
   - `jvm.gcOptions`: Uses G1GC for low-latency garbage collection.

2. **bookkeeper.conf** (for Bookie nodes)
   Create a file named `bookkeeper.conf`. This file will be used by all three bookies (`bookie1`, `bookie2`, `bookie3`), with `advertisedAddress` set dynamically via environment variables to avoid duplication.

   ```conf
   # BookKeeper configuration for Apache Pulsar cluster
   bookiePort=3181
   advertisedAddress=${ADVERTISED_ADDRESS}
   zkServers=zookeeper1:2181,zookeeper2:2181,zookeeper3:2181
   zkLedgersRootPath=/ledgers
   journalDirectory=/pulsar/data/bookkeeper/journal
   ledgerDirectories=/pulsar/data/bookkeeper/ledgers
   indexDirectories=/pulsar/data/bookkeeper/ledgers
   dbStorage_writeCacheMaxSizeMb=64
   dbStorage_readAheadCacheMaxSizeMb=16
   dbStorage_readAheadCacheBatchSize=100
   minUsableSizeForIndexFileCreation=10
   diskUsageThreshold=0.95
   diskUsageLwmThreshold=0.90
   autoRecoveryDaemonEnabled=true
   allowMultipleDirsUnderSameDiskPartition=true
   numAddWorkerThreads=2
   numReadWorkerThreads=4
   numHighPriorityWorkerThreads=2
   entryLogSizeLimit=2097152
   entryLogFilePreallocationEnabled=true

   # JVM options for memory and GC
   JVMOptions=-Xms512m -Xmx512m -XX:MaxDirectMemorySize=256m -XX:+UseG1GC -XX:MaxGCPauseMillis=200
   ```

   **Key Settings**:
   - `bookiePort=3181`: Default BookKeeper port.
   - `advertisedAddress=${ADVERTISED_ADDRESS}`: Set via environment variable (`bookie1`, `bookie2`, `bookie3`) to ensure unique identities.
   - `zkServers`: Connects to the ZooKeeper ensemble for metadata.
   - `journalDirectory`, `ledgerDirectories`, `indexDirectories`: Use the mounted volume (`/pulsar/data/bookkeeper`) for persistence.
   - `dbStorage_writeCacheMaxSizeMb=64`, `dbStorage_readAheadCacheMaxSizeMb=16`: Balances memory usage for write/read performance; increase for production (e.g., 256MB).
   - `diskUsageThreshold=0.95`, `diskUsageLwmThreshold=0.90`: Prevents writes if disk usage exceeds 95%, resumes at 90%.
   - `autoRecoveryDaemonEnabled=true`: Ensures bookies recover ledgers automatically.
   - `numAddWorkerThreads=2`, `numReadWorkerThreads=4`: Optimizes for read-heavy workloads; adjust based on workload.
   - `entryLogSizeLimit=2097152`: Limits entry log size to 2MB for faster compaction.
   - `entryLogFilePreallocationEnabled=true`: Improves write performance.
   - `JVMOptions`: 512MB heap for testing; increase to 2-4GB for production with SSDs.

3. **broker.conf** (for Broker nodes)
   Create a file named `broker.conf`. This file will be used by all three brokers (`broker1`, `broker2`, `broker3`), with `advertisedAddress` set dynamically.

   ```conf
   # Pulsar Broker configuration for Apache Pulsar cluster
   zookeeperServers=zookeeper1:2181,zookeeper2:2181,zookeeper3:2181
   configurationStoreServers=zookeeper1:2181,zookeeper2:2181,zookeeper3:2181
   clusterName=cluster-a
   brokerServicePort=6650
   webServicePort=8080
   advertisedAddress=${ADVERTISED_ADDRESS}
   brokerServiceUrl=pulsar://haproxy:6650
   webServiceUrl=http://haproxy:8080
   managedLedgerDefaultEnsembleSize=2
   managedLedgerDefaultWriteQuorum=2
   managedLedgerDefaultAckQuorum=2
   managedLedgerMaxEntriesPerLedger=50000
   managedLedgerMinLedgerRolloverTimeMinutes=10
   managedLedgerMaxSizePerLedgerMbytes=2048
   defaultNumberOfNamespaceBundles=4
   maxUnackedMessagesPerConsumer=50000
   maxUnackedMessagesPerSubscription=200000
   backlogQuotaDefaultLimitGB=10
   ttlDurationDefaultInSeconds=0
   maxMessageSize=5242880
   brokerDeleteInactiveTopicsEnabled=true
   brokerDeleteInactiveTopicsFrequencySeconds=60
   loadBalancerEnabled=true
   loadBalancerReportUpdateThresholdPercentage=10
   loadBalancerSheddingEnabled=true
   loadBalancerSheddingIntervalMinutes=1

   # JVM options for memory and GC
   PULSAR_MEM=-Xms512m -Xmx512m -XX:MaxDirectMemorySize=256m -XX:+UseG1GC -XX:MaxGCPauseMillis=200
   ```

   **Key Settings**:
   - `zookeeperServers`, `configurationStoreServers`: Connects to the ZooKeeper ensemble.
   - `clusterName=cluster-a`: Matches the `pulsar-init` configuration.
   - `brokerServicePort=6650`, `webServicePort=8080`: Default Pulsar ports.
   - `advertisedAddress=${ADVERTISED_ADDRESS}`: Set to `broker1`, `broker2`, or `broker3` via environment variables.
   - `brokerServiceUrl`, `webServiceUrl`: Points to HAProxy (`haproxy:6650`, `haproxy:8080`) for client connections.
   - `managedLedgerDefaultEnsembleSize=2`, `managedLedgerDefaultWriteQuorum=2`, `managedLedgerDefaultAckQuorum=2`: Ensures replication across two bookies for fault tolerance.
   - `managedLedgerMaxEntriesPerLedger=50000`, `managedLedgerMinLedgerRolloverTimeMinutes=10`: Balances ledger size and rollover frequency.
   - `defaultNumberOfNamespaceBundles=4`: Improves load distribution across brokers.
   - `maxUnackedMessagesPerConsumer`, `maxUnackedMessagesPerSubscription`: Prevents memory overload for consumers.
   - `backlogQuotaDefaultLimitGB=10`: Limits backlog to 10GB per topic.
   - `brokerDeleteInactiveTopicsEnabled=true`: Cleans up inactive topics hourly.
   - `loadBalancerEnabled=true`, `loadBalancerSheddingEnabled=true`: Enables dynamic load balancing and shedding for even distribution.
   - `PULSAR_MEM`: 512MB heap for testing; increase to 2-4GB for production.

---

### Updated `docker-compose.yml`
The updated `docker-compose.yml` mounts the configuration files and adjusts environment variables to set `ADVERTISED_ADDRESS` for each service. It removes redundant environment variables (e.g., `metadataStoreUrl`, `PULSAR_MEM`) since these are now defined in the config files. The HAProxy service and other components remain unchanged from the previous version.

```yaml
version: '3'
networks:
  pulsar:
    driver: bridge

services:
  # ZooKeeper Ensemble (3 nodes)
  zookeeper1:
    image: apachepulsar/pulsar:latest
    container_name: zookeeper1
    hostname: zookeeper1
    restart: on-failure
    networks:
      - pulsar
    volumes:
      - ./data/zookeeper1:/pulsar/data/zookeeper
      - ./zookeeper.conf:/pulsar/conf/zookeeper.conf
    environment:
      - serverId=1
    command: >
      bash -c "bin/generate-zookeeper-config.sh conf/zookeeper.conf &&
               exec bin/pulsar zookeeper"
    healthcheck:
      test: ["CMD", "bin/pulsar-zookeeper-ruok.sh"]
      interval: 10s
      timeout: 5s
      retries: 30

  zookeeper2:
    image: apachepulsar/pulsar:latest
    container_name: zookeeper2
    hostname: zookeeper2
    restart: on-failure
    networks:
      - pulsar
    volumes:
      - ./data/zookeeper2:/pulsar/data/zookeeper
      - ./zookeeper.conf:/pulsar/conf/zookeeper.conf
    environment:
      - serverId=2
    command: >
      bash -c "bin/generate-zookeeper-config.sh conf/zookeeper.conf &&
               exec bin/pulsar zookeeper"
    healthcheck:
      test: ["CMD", "bin/pulsar-zookeeper-ruok.sh"]
      interval: 10s
      timeout: 5s
      retries: 30

  zookeeper3:
    image: apachepulsar/pulsar:latest
    container_name: zookeeper3
    hostname: zookeeper3
    restart: on-failure
    networks:
      - pulsar
    volumes:
      - ./data/zookeeper3:/pulsar/data/zookeeper
      - ./zookeeper.conf:/pulsar/conf/zookeeper.conf
    environment:
      - serverId=3
    command: >
      bash -c "bin/generate-zookeeper-config.sh conf/zookeeper.conf &&
               exec bin/pulsar zookeeper"
    healthcheck:
      test: ["CMD", "bin/pulsar-zookeeper-ruok.sh"]
      interval: 10s
      timeout: 5s
      retries: 30

  # Initialize Cluster Metadata
  pulsar-init:
    container_name: pulsar-init
    hostname: pulsar-init
    image: apachepulsar/pulsar:latest
    networks:
      - pulsar
    command: >
      bin/pulsar initialize-cluster-metadata \
      --cluster cluster-a \
      --zookeeper zookeeper1:2181,zookeeper2:2181,zookeeper3:2181 \
      --configuration-store zookeeper1:2181,zookeeper2:2181,zookeeper3:2181 \
      --web-service-url http://haproxy:8080 \
      --broker-service-url pulsar://haproxy:6650
    depends_on:
      zookeeper1:
        condition: service_healthy
      zookeeper2:
        condition: service_healthy
      zookeeper3:
        condition: service_healthy

  # Bookies (3 nodes)
  bookie1:
    image: apachepulsar/pulsar:latest
    container_name: bookie1
    hostname: bookie1
    restart: on-failure
    networks:
      - pulsar
    environment:
      - ADVERTISED_ADDRESS=bookie1
    depends_on:
      zookeeper1:
        condition: service_healthy
      zookeeper2:
        condition: service_healthy
      zookeeper3:
        condition: service_healthy
      pulsar-init:
        condition: service_completed_successfully
    volumes:
      - ./data/bookkeeper1:/pulsar/data/bookkeeper
      - ./bookkeeper.conf:/pulsar/conf/bookkeeper.conf
    command: >
      bash -c "bin/apply-config-from-env.py conf/bookkeeper.conf && exec bin/pulsar bookie"

  bookie2:
    image: apachepulsar/pulsar:latest
    container_name: bookie2
    hostname: bookie2
    restart: on-failure
    networks:
      - pulsar
    environment:
      - ADVERTISED_ADDRESS=bookie2
    depends_on:
      zookeeper1:
        condition: service_healthy
      zookeeper2:
        condition: service_healthy
      zookeeper3:
        condition: service_healthy
      pulsar-init:
        condition: service_completed_successfully
    volumes:
      - ./data/bookkeeper2:/pulsar/data/bookkeeper
      - ./bookkeeper.conf:/pulsar/conf/bookkeeper.conf
    command: >
      bash -c "bin/apply-config-from-env.py conf/bookkeeper.conf && exec bin/pulsar bookie"

  bookie3:
    image: apachepulsar/pulsar:latest
    container_name: bookie3
    hostname: bookie3
    restart: on-failure
    networks:
      - pulsar
    environment:
      - ADVERTISED_ADDRESS=bookie3
    depends_on:
      zookeeper1:
        condition: service_healthy
      zookeeper2:
        condition: service_healthy
      zookeeper3:
        condition: service_healthy
      pulsar-init:
        condition: service_completed_successfully
    volumes:
      - ./data/bookkeeper3:/pulsar/data/bookkeeper
      - ./bookkeeper.conf:/pulsar/conf/bookkeeper.conf
    command: >
      bash -c "bin/apply-config-from-env.py conf/bookkeeper.conf && exec bin/pulsar bookie"

  # Brokers (3 nodes)
  broker1:
    image: apachepulsar/pulsar:latest
    container_name: broker1
    hostname: broker1
    restart: on-failure
    networks:
      - pulsar
    environment:
      - ADVERTISED_ADDRESS=broker1
    depends_on:
      zookeeper1:
        condition: service_healthy
      zookeeper2:
        condition: service_healthy
      zookeeper3:
        condition: service_healthy
      bookie1:
        condition: service_started
      bookie2:
        condition: service_started
      bookie3:
        condition: service_started
    volumes:
      - ./broker.conf:/pulsar/conf/broker.conf
    command: >
      bash -c "bin/apply-config-from-env.py conf/broker.conf && exec bin/pulsar broker"

  broker2:
    image: apachepulsar/pulsar:latest
    container_name: broker2
    hostname: broker2
    restart: on-failure
    networks:
      - pulsar
    environment:
      - ADVERTISED_ADDRESS=broker2
    depends_on:
      zookeeper1:
        condition: service_healthy
      zookeeper2:
        condition: service_healthy
      zookeeper3:
        condition: service_healthy
      bookie1:
        condition: service_started
      bookie2:
        condition: service_started
      bookie3:
        condition: service_started
    volumes:
      - ./broker.conf:/pulsar/conf/broker.conf
    command: >
      bash -c "bin/apply-config-from-env.py conf/broker.conf && exec bin/pulsar broker"

  broker3:
    image: apachepulsar/pulsar:latest
    container_name: broker3
    hostname: broker3
    restart: on-failure
    networks:
      - pulsar
    environment:
      - ADVERTISED_ADDRESS=broker3
    depends_on:
      zookeeper1:
        condition: service_healthy
      zookeeper2:
        condition: service_healthy
      zookeeper3:
        condition: service_healthy
      bookie1:
        condition: service_started
      bookie2:
        condition: service_started
      bookie3:
        condition: service_started
    volumes:
      - ./broker.conf:/pulsar/conf/broker.conf
    command: >
      bash -c "bin/apply-config-from-env.py conf/broker.conf && exec bin/pulsar broker"

  # HAProxy Load Balancer
  haproxy:
    image: haproxy:latest
    container_name: haproxy
    hostname: haproxy
    restart: on-failure
    networks:
      - pulsar
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    ports:
      - "6650:6650"
      - "8080:8080"
    depends_on:
      broker1:
        condition: service_started
      broker2:
        condition: service_started
      broker3:
        condition: service_started
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://broker1:8080/admin/v2/brokers/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

**Key Changes**:
- **ZooKeeper**:
  - Mounts `zookeeper.conf` to `/pulsar/conf/zookeeper.conf`.
  - Adds `serverId` environment variable (1, 2, 3) to distinguish nodes in the ensemble.
  - Removes `metadataStoreUrl` and `PULSAR_MEM` environment variables, as they’re defined in `zookeeper.conf`.
- **Bookies**:
  - Mounts `bookkeeper.conf` to `/pulsar/conf/bookkeeper.conf`.
  - Sets `ADVERTISED_ADDRESS` to `bookie1`, `bookie2`, or `bookie3` for unique identities.
  - Removes `clusterName`, `zkServers`, `metadataServiceUri`, `BOOKIE_MEM` environment variables, as they’re in `bookkeeper.conf`.
  - Retains `apply-config-from-env.py` to apply `ADVERTISED_ADDRESS`.
- **Brokers**:
  - Mounts `broker.conf` to `/pulsar/conf/broker.conf`.
  - Sets `ADVERTISED_ADDRESS` to `broker1`, `broker2`, or `broker3`.
  - Removes `metadataStoreUrl`, `zookeeperServers`, `clusterName`, `managedLedger*`, `PULSAR_MEM`, `advertisedListeners` environment variables, as they’re in `broker.conf`.
- **HAProxy and `pulsar-init`**: Unchanged, as they don’t require configuration file adjustments.

---

### Deployment Steps

1. **Create Configuration Files**:
   Create the following files in the same directory as `docker-compose.yml`:
   - `zookeeper.conf`: Copy the ZooKeeper configuration.
   - `bookkeeper.conf`: Copy the BookKeeper configuration.
   - `broker.conf`: Copy the broker configuration.
   - `haproxy.cfg`: Ensure it exists from the previous setup (unchanged).

2. **Set Up Directories**:
   ```bash
   mkdir -p ./data/zookeeper{1,2,3} ./data/bookkeeper{1,2,3}
   sudo chown -R 10000 ./data
   touch zookeeper.conf bookkeeper.conf broker.conf
   ```

3. **Deploy the Cluster**:
   Save the updated `docker-compose.yml` and run:
   ```bash
   docker-compose up -d
   ```

4. **Verify the Setup**:
   - Check container status:
     ```bash
     docker-compose ps
     ```
   - Verify ZooKeeper:
     ```bash
     docker exec zookeeper1 bin/pulsar-zookeeper-ruok.sh
     ```
     Repeat for `zookeeper2`, `zookeeper3`. Should return `imok`.

   - Verify Bookies:
     ```bash
     docker exec bookie1 bin/bookkeeper shell listbookies -rw
     ```
     Should list `bookie1:3181`, `bookie2:3181`, `bookie3:3181`.

   - Confirm brokers are UP (e.g., Server pulsar_backend/broker1 is UP).
     ```bash
      docker exec pulsar-proxy nc -zv broker1 6650
      docker exec pulsar-proxy curl -f http://broker1:8080/admin/v2/brokers/health
     ```

  - Verify Brokers:
    ```bash
    docker exec broker1 bin/pulsar-admin brokers list cluster-a -b http://haproxy:8080
    ```
    Should list all three brokers.

  - Test Messaging:
    ```bash
    docker exec broker1 bin/pulsar-client produce my-topic --messages "Hello Pulsar" -n 1 -r pulsar://haproxy:6650
    docker exec broker1 bin/pulsar-client consume my-topic -s "test-sub" -n 1 -r pulsar://haproxy:6650
    ```

5. **Clean Up** (Optional):
   ```bash
   docker-compose down
   rm -rf ./data zookeeper.conf bookkeeper.conf broker.conf haproxy.cfg
   ```

---

### Best Practices and Notes
- **Configuration Management**:
  - Explicit config files improve transparency and reduce errors compared to environment variables.
  - Single `bookkeeper.conf` and `broker.conf` files are reused across nodes, with `ADVERTISED_ADDRESS` dynamically set to minimize duplication.
  - `zookeeper.conf` is identical for all nodes, with `serverId` distinguishing them.
- **Performance Tuning**:
  - Memory settings (256MB for ZooKeeper, 512MB for bookies/brokers) are suitable for testing. For production:
    - ZooKeeper: 1-2GB heap, SSDs for `dataDir`.
    - Bookies: 2-4GB heap, separate SSDs for `journalDirectory` and `ledgerDirectories`.
    - Brokers: 2-4GB heap, tune `maxUnackedMessages*` based on consumer patterns.
  - BookKeeper’s `dbStorage_*` settings are conservative; increase caches for high-throughput workloads.
- **Fault Tolerance**:
  - ZooKeeper’s 3-node ensemble tolerates one failure.
  - BookKeeper’s `managedLedgerDefaultEnsembleSize=2` ensures data replication across two bookies.
  - HAProxy’s health checks ensure traffic goes to healthy brokers.
- **Production Considerations**:
  - Add SSL/TLS to `broker.conf` (`brokerServicePortTls`, `webServicePortTls`) and HAProxy for secure communication.
  - Use external storage (e.g., EBS, NFS) for `./data` volumes in production.
  - Monitor with tools like Prometheus (enable metrics in `broker.conf` via `exposePublisherStats=true`).
  - Consider Pulsar Proxy for advanced features like authentication offloading.
- **Source**: Configurations are based on Apache Pulsar’s default templates (`conf/zookeeper.conf`, `conf/bookkeeper.conf`, `conf/broker.conf` in the Pulsar Docker image), optimized for a 3-node cluster with HAProxy, and aligned with best practices from Pulsar and BookKeeper documentation.

---

This setup provides a fully configured Pulsar cluster with explicit configuration files, HAProxy load balancing, and best practices for reliability and performance. Let me know if you need additional features, such as TLS or monitoring, or further clarification!