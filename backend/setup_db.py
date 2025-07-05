#!/usr/bin/env python3
"""
Database setup script for the adaptive learning system.
This script creates the required database if it doesn't exist.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the database if it doesn't exist."""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="vaibhav"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'adaptive_boss_db'")
        if cursor.fetchone():
            print("Database 'adaptive_boss_db' already exists.")
        else:
            # Create database
            cursor.execute("CREATE DATABASE adaptive_boss_db")
            print("Database 'adaptive_boss_db' created successfully.")
        
        cursor.close()
        conn.close()
        
        # Test connection to the new database
        test_conn = psycopg2.connect(
            host="localhost",
            database="adaptive_boss_db",
            user="postgres",
            password="vaibhav"
        )
        test_conn.close()
        print("Successfully connected to 'adaptive_boss_db'.")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = create_database()
    if success:
        print("Database setup completed successfully!")
    else:
        print("Database setup failed!")
