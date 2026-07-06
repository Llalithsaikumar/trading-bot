-- PostgreSQL initialization script
-- Runs once when the container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "vector";


-- Create test database (for CI/CD)
-- CREATE DATABASE crypto_trader_test WITH OWNER trader;
