#!/bin/bash

set -e

case "$1" in
  "init")
    echo "Initializing Docker..."
    # Add your Docker initialization commands here
    ;;
  "start")
    echo "Starting Docker..."
    # Add your Docker start commands here
     docker compose -f \
     milvus-cluster.docker-compose.yml up \
     --always-recreate-deps \
     --renew-anon-volumes \
     --remove-orphans \
     --force-recreate \
     -d \
     --build "${2:-}"
    ;;
  "stop")
    echo "Stopping Docker..."
    # Add your Docker stop commands here
    docker compose \
    -f milvus-cluster.docker-compose.yml down \
    --volumes \
    --remove-orphans \
    --rmi local
    ;;
  *)
    echo "Usage: $0 {init|start|stop}"
    exit 1
    ;;
esac