-- Setup script for Adaptive Boss Database
-- This script creates the user, database, and necessary permissions

-- Create the user
CREATE USER adaptive_user WITH PASSWORD 'adaptive_password';

-- Create the database
CREATE DATABASE adaptive_boss_db OWNER adaptive_user;

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON DATABASE adaptive_boss_db TO adaptive_user;

-- Connect to the new database and create extensions
\c adaptive_boss_db;

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO adaptive_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO adaptive_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO adaptive_user;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Show successful creation
SELECT 'Database setup completed successfully!' as status;
