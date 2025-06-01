#!/bin/bash
# postgres_test.sh
# This script tests the PostgreSQL cluster by checking connectivity, CRUD operations,
# and replication. It ensures writes go to the master and reads go to replicas.

# Stop the script if anything goes wrong
set -e

# Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Environment variables with defaults
PG_HOST="${PG_HOST:-postgres-haproxy}"
PG_WRITE_PORT="${PG_WRITE_PORT:-5432}" # Master port for writes
PG_READ_PORTS=(5433) # Replica ports for reads
PG_USER="${PG_USER:-admin}"
PG_DATABASE="${PG_DATABASE:-milvus}"
HAPROXY_STATS_URL="${HAPROXY_STATS_URL:-http://postgres-haproxy:8080/stats}"
HAPROXY_STATS_USER="${HAPROXY_STATS_USER:-admin}"
HAPROXY_STATS_PASSWORD="${HAPROXY_STATS_PASSWORD:-admin123}"

# Export password from secret file
export PGPASSWORD=$(cat /run/secrets/postgres_password)

# Test 1: Check connectivity to master
log "Test 1: Checking connectivity to master"
psql -h "$PG_HOST" -p "$PG_WRITE_PORT" -U "$PG_USER" -d "$PG_DATABASE" -c "SELECT 1 AS test;" || {
    log "Error: Failed to connect to master"
    exit 1
}

# Test 2: Create a test table on master
log "Test 2: Creating test table on master"
psql -h "$PG_HOST" -p "$PG_WRITE_PORT" -U "$PG_USER" -d "$PG_DATABASE" \
    -c "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, name TEXT);" || {
    log "Error: Failed to create test table"
    exit 1
}

# Test 3: Insert data on master
log "Test 3: Inserting data on master"
psql -h "$PG_HOST" -p "$PG_WRITE_PORT" -U "$PG_USER" -d "$PG_DATABASE" \
    -c "INSERT INTO test_table (name) VALUES ('Test Data 1'), ('Test Data 2'); COMMIT;" || {
    log "Error: Failed to insert data"
    exit 1
}

# Test 4: Verify data on replicas
log "Test 4: Verifying data replication on replicas"
for port in "${PG_READ_PORTS[@]}"; do
    log "Checking replica at port $port"
    timeout 30s bash -c "until psql -h $PG_HOST -p $port -U $PG_USER -d $PG_DATABASE -c 'SELECT EXISTS (SELECT FROM test_table WHERE name = ''Test Data 1'');' | grep -q 't'; do sleep 1; done" || {
        log "Error: Data not found on replica at port $port"
        exit 1
    }
    psql -h "$PG_HOST" -p "$port" -U "$PG_USER" -d "$PG_DATABASE" -c "SELECT * FROM test_table;" || {
        log "Error: Failed to read data on replica at port $port"
        exit 1
    }
done

# Test 5: Test read-only enforcement on replicas
log "Test 5: Testing read-only enforcement on replicas"
for port in "${PG_READ_PORTS[@]}"; do
    log "Attempting write on replica at port $port"
    psql -h "$PG_HOST" -p "$port" -U "$PG_USER" -d "$PG_DATABASE" -c "INSERT INTO test_table (name) VALUES ('Should Fail');" 2>/dev/null && {
        log "Error: Write succeeded on replica at port $port"
        exit 1
    } || log "Write correctly failed on replica at port $port"
done

# Test 6: Check HAProxy stats
log "Test 6: Checking HAProxy stats page"
curl -u "$HAPROXY_STATS_USER:$HAPROXY_STATS_PASSWORD" "$HAPROXY_STATS_URL" || {
    log "Error: Failed to access HAProxy stats page"
    exit 1
}

# Clean up
log "Cleaning up test table"
psql -h "$PG_HOST" -p "$PG_WRITE_PORT" -U "$PG_USER" -d "$PG_DATABASE" -c "DROP TABLE IF EXISTS test_table;" || {
    log "Warning: Failed to drop test table"
}

log "All tests completed successfully"