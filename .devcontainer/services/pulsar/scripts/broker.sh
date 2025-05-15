#!/bin/bash
set -e

# Ensure broker.conf exists
if [ ! -f /pulsar/conf/broker.conf ]; then
    echo "Error: /pulsar/conf/broker.conf not found!"
    exit 1
fi

# Apply environment variables to broker.conf
echo "Applying environment variables to broker.conf..."
echo "Broker: Starting with ADVERTISED_ADDRESS=${ADVERTISED_ADDRESS}"
/pulsar/bin/apply-config-from-env.py /pulsar/conf/broker.conf

# Start BookKeeper
echo "Starting Broker..."
echo "Broker: Starting with ADVERTISED_ADDRESS=${ADVERTISED_ADDRESS}, PULSAR_MEM=${PULSAR_MEM}"
exec bin/pulsar broker
