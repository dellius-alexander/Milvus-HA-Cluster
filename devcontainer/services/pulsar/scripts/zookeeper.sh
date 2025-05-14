#!/bin/bash
set -e

# Ensure zookeeper.conf exists
if [ ! -f /pulsar/conf/zookeeper.conf ]; then
    echo "Error: /pulsar/conf/zookeeper.conf not found!"
    exit 1
fi

# Creates the myid
echo "ZooKeeper: Starting with SERVERID=${SERVERID}"
test -w /pulsar/data/zookeeper || (echo "ZooKeeper: Directory not writable"; exit 1)
echo "${SERVERID}" > /pulsar/data/zookeeper/myid
chmod 644 /pulsar/data/zookeeper/myid

# Apply environment variables to zookeeper.conf
echo "Applying environment variables to zookeeper.conf..."
/pulsar/bin/apply-config-from-env.py /pulsar/conf/zookeeper.conf

# Generate ZooKeeper configuration
echo "Generating ZooKeeper configuration..."
/pulsar/bin/generate-zookeeper-config.sh /pulsar/conf/zookeeper.conf

# Start ZooKeeper
echo "Starting ZooKeeper..."
exec bin/pulsar zookeeper