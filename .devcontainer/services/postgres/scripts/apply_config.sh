#!/bin/bash
# apply_config.sh
# Applies templated configuration using environment variables.

set -e

LOG_FILE=/var/log/patroni/setup.log
echo "{\"message\": \"Applying configuration for ENVIRONMENT=$ENVIRONMENT\", \"level\": \"INFO\", \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S,%f')\"}" >> $LOG_FILE

# Substitute environment variables
envsubst < /tmp/patroni.yml.tmpl > /etc/patroni.yml
mkdir -p /var/lib/postgresql/.config/patroni
envsubst < /tmp/patroni.yml.tmpl > /var/lib/postgresql/.config/patroni/patronictl.yaml

echo "{\"message\": \"Configuration applied\", \"level\": \"INFO\", \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S,%f')\"}" >> $LOG_FILE