#!/bin/bash

# pg_repository.sh
set -e

# This script sets up the PostgreSQL APT repository for installing PostgreSQL client tools.
apt-get update -y && \
apt-get install -y --no-install-recommends \
curl ca-certificates

# Create the directory for PostgreSQL APT repository key
install -d /usr/share/postgresql-common/pgdg

# Download the PostgreSQL APT repository key and add it to the trusted keys
curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
. /etc/os-release

# Use the codename from /etc/os-release or fallback to lsb_release
VERSION_CODENAME=${VERSION_CODENAME:-$(lsb_release -cs)}
sh -c "echo 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main' > /etc/apt/sources.list.d/pgdg.list"

apt-get update -y && \
apt-get install -y postgresql-client-17
