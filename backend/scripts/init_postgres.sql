-- Initialize PostgreSQL database for Adaptive Boss Behavior System

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance (will be created by SQLAlchemy, but good to have)
-- These will be created after tables are created by the application

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE adaptive_boss_db TO adaptive_user;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Note: Triggers will be added after tables are created by SQLAlchemy