-- Database initialization script for TimescaleDB
-- This script runs automatically when the PostgreSQL container starts

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create custom types
DO $$ BEGIN
    CREATE TYPE order_status AS ENUM (
        'CREATED', 'SENT', 'ACK', 'PARTIAL', 
        'FILLED', 'CANCELLED', 'REJECTED', 'EXITED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE type position_side AS ENUM ('LONG', 'SHORT');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE regime_type AS ENUM (
        'BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'EVENT_MODE'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO astra;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO astra;

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;
