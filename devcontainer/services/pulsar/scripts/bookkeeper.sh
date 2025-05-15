#!/bin/bash
set -e

# Ensure bookkeeper.conf exists
if [ ! -f /pulsar/conf/bookkeeper.conf ]; then
    echo "Error: /pulsar/conf/bookkeeper.conf not found!"
    exit 1
fi

# Apply environment variables to bookkeeper.conf
echo "Applying environment variables to bookkeeper.conf..."
echo "Bookie: Starting with ADVERTISED_ADDRESS=${ADVERTISED_ADDRESS}, BOOKIEID=${BOOKIEID}, BOOKIE_MEM=${BOOKIE_MEM}"
bin/apply-config-from-env.py conf/bookkeeper.conf

# Start BookKeeper
echo "Starting BookKeeper..."
exec bin/pulsar bookie
