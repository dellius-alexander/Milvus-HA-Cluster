#!/bin/bash
# init-replica.sh
# This script sets up replicas to copy data from the master database.
# It's like setting up a backup copy machine that syncs with the main one.

# Stop the script if anything goes wrong
set -e

# Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create the replication user on the master
if [ "$HOSTNAME" = "postgres-master" ]; then
    log "Creating replication user 'repl' on master"
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE ROLE repl WITH REPLICATION LOGIN ENCRYPTED PASSWORD '$REPL_PASSWORD';" || {
        log "Warning: Replication user 'repl' may already exist"
    }
    log "Configuring pg_hba.conf for replication on master"
    echo "host replication repl 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"
else
    log "This is a replica node ($HOSTNAME), starting initialization"

    # Check if PGDATA is set
    if [ -z "$PGDATA" ]; then
        log "Error: PGDATA environment variable is not set"
        exit 1
    fi

    # Clear existing data
    log "Clearing existing data in $PGDATA"
    rm -rf "$PGDATA"/*

    # Copy data from the master
    log "Running pg_basebackup to copy data from postgres-master"
    pg_basebackup \
        --host=postgres-master \
        --pgdata="$PGDATA" \
        --username="$REPL_USER" \
        --progress \
        --verbose \
        --write-recovery-conf \
        --wal-method=stream || {
        log "Error: pg_basebackup failed"
        exit 1
    }

    # Create standby.signal to make this a replica
    log "Creating standby.signal for replica mode"
    touch "$PGDATA/standby.signal"

    # Configure recovery settings
    log "Configuring recovery settings"
    cat >> "$PGDATA/postgresql.auto.conf" <<EOF
primary_conninfo = 'user=$REPL_USER password=$REPL_PASSWORD host=postgres-master port=5432 sslmode=prefer'
restore_command = 'cp /var/lib/postgresql/archiveopsin/restore/%f %p'
EOF

    # Disable WAL archiving
    log "Disabling WAL archiving on replica"
    echo "archive_mode = off" >> "$PGDATA/postgresql.auto.conf"

    # Set ownership and permissions
    log "Setting ownership and permissions for $PGDATA"
    chown -R postgres:postgres "$PGDATA"
    chmod -R 700 "$PGDATA"

    log "Replica initialization completed for $HOSTNAME"
fi