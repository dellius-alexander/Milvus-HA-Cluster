#!/usr/bin/env bash
# init-replica.sh
# This script sets up replicas to copy data from the master database.
# It's like setting up a backup copy machine that syncs with the main one.

# Stop the script if anything goes wrong
set -e

# Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Running as user: $(whoami) on ${HOSTNAME}"

REPL_PASSWORD=$(cat ${REPL_PASSWORD_FILE})

# Verify that PGDATA is set before running the command by adding a check
if [ -z "${PGDATA}" ]; then
    log "Error: PGDATA is not set"
    exit 1
fi

# Check if the replication user password is set
if [ -z "$REPL_PASSWORD" ]; then
    log "Error: REPL_PASSWORD is not set. Please set the REPL_PASSWORD environment variable."
    exit 1
fi

# Create the replication user on the master
if [ "${HOSTNAME}" == "postgres-master" ]; then

  # Clear existing data
    log "Clearing existing data in ${PGDATA}"
    if ! rm -rf "${PGDATA:?}"/*; then
        log "Error: Failed to clear ${PGDATA}"
        exit 1
    fi

    # Move pg_hba.conf to PGDATA
    log "Moving pg_hba.conf to ${PGDATA}"
    mv /tmp/pg_hba.conf "${PGDATA}/pg_hba.conf"

    log "Creating replication user ${REPL_USER} on master"
    psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -c "CREATE ROLE ${REPL_USER} WITH REPLICATION LOGIN ENCRYPTED PASSWORD ${REPL_PASSWORD};" || {
        log "Warning: Replication user 'repl' may already exist"
    }
else
    log "This is a replica node (${HOSTNAME}), starting initialization"

    # Adding a delay in init-replica.sh for replicas to ensure the master is ready
    if [ "${HOSTNAME}" != "postgres-master" ]; then
        log "Waiting for master to be ready..."
        until pg_isready -h postgres-master -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"; do
            sleep 2
            log "Master not ready, retrying..."
        done
    fi

    # Check if PGDATA is set
    if [ -z "${PGDATA}" ]; then
        log "Error: PGDATA environment variable is not set"
        exit 1
    fi

    # Clear existing data
    log "Clearing existing data in ${PGDATA}"
    rm -rf "${PGDATA:?}"/*

    log "Postgresql data directory: ${PGDATA}"
    log "Creating PGDATA directory if it doesn't exist"
    mkdir -p "${PGDATA}"
    chown postgres:postgres "${PGDATA}"
    chmod 644 "${PGDATA}"
    # Create a PG_VERSION file to prevent initdb
    echo "17" > "${PGDATA}/PG_VERSION"

    # Move pg_hba.conf to PGDATA
    log "Moving pg_hba.conf to ${PGDATA}"
    mv /tmp/pg_hba.conf "${PGDATA}/pg_hba.conf"



    # Read replication password from secret
    if [ -f /run/secrets/repl_password ]; then
        export PGPASSWORD=${REPL_PASSWORD}
    else
        log "Error: repl_password secret file missing"
        exit 1
    fi

    # Check if PGDATA is empty before running pg_basebackup or initdb
    if [ "$(ls -A ${PGDATA})" ]; then
        log "Error: ${PGDATA} is not empty"
        exit 1
    fi

    # Perform a base backup from the master node to initialize the replica
    # -h | --host: Master hostname (postgres-master)
    # -D | --pgdata: Data directory ($PGDATA)
    # -U | --username: Replication user (admin, as set in postgres.yaml)
    # -P | --progress: Show progress
    # -v: Verbose output
    # -R | --write-recovery-conf: Create recovery configuration for streaming replication
    # --wal-method=stream: Stream write-ahead logs for replication
    log "Running pg_basebackup to copy data from postgres-master"
    pg_basebackup \
    -h postgres-master \
    -D "$PGDATA" \
    -U "${POSTGRES_USER}" \
    -P -v -R \
    --wal-method=stream \
    --force-overwrite || {
        log "Error: pg_basebackup failed"
        exit 1
    }

    # Create standby.signal to make this a replica
    log "Creating standby.signal for replica mode"
    touch "${PGDATA}/standby.signal"

    # Configure recovery settings
    log "Configuring recovery settings"
    cat "${PGDATA}/postgresql.auto.conf"


    # Disable WAL archiving
    log "Disabling WAL archiving on replica"
    echo "archive_mode = off" >> "${PGDATA}/postgresql.auto.conf"

    # Set ownership and permissions
    log "Setting ownership and permissions for ${PGDATA}"
    chown -R ${POSTGRES_USER}:${POSTGRES_USER} "${PGDATA}"
    chmod -R 644 "${PGDATA}"

    log "Replica initialization completed for ${HOSTNAME}"
fi

