#!/usr/bin/env bash
set -e

for name in postgres-master postgres-replica1 postgres-replica2; do
  echo "Starting PostgreSQL container: ${name}"
  docker run -d \
	--name ${name} \
	-e POSTGRES_PASSWORD=securepassword123 \
	-e PGDATA=/var/lib/postgresql/data/pgdata \
	postgres:17.5 && wait $! || {
    echo "Error: Failed to start container ${name}"
    exit 1
  }
  if [ $(docker ps -q -f name=${name}) 2>&1 ]; then
    echo "Container ${name} is running"
    echo "Container ${name} started successfully"
  else
    echo "Error: Container ${name} failed to start"
    exit 1
  fi
  
done



