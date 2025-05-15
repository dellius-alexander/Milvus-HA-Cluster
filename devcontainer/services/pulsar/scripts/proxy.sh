#!/bin/bash
echo "Proxy: Starting with PULSAR_MEM=${PULSAR_MEM}"
bin/apply-config-from-env.py /pulsar/conf/proxy.conf
exec bin/pulsar proxy