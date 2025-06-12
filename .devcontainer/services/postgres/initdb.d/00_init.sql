-- File: 00_init.sql
-- The file name must start with a number to ensure it runs first, because the
-- postgres container will run the initdb script during initial container startup.
-- This file is used to initialize the PostgreSQL database with a replication user.

-- Create replication user
CREATE ROLE repl WITH LOGIN PASSWORD :'REPL_PASSWORD' REPLICATION;

-- Create database if it doesn't exist
CREATE USER milvus WITH PASSWORD :'MILVUS_PASSWORD';
CREATE DATABASE milvus;
GRANT ALL PRIVILEGES ON DATABASE milvus TO milvus;

