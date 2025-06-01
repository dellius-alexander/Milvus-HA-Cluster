-- File: 00_init.sql
-- The file name must start with a number to ensure it runs first, because the
-- postgres container will run the initdb script during initial container startup.
-- This file is used to initialize the PostgreSQL database with a replication user.


-- 1. Create a replication user on the PostgreSQL server "postgres-master"
-- 1.2 Verify we are on the correct host first
SELECT inet_server_addr() AS server_address, inet_server_port() AS server_port;
