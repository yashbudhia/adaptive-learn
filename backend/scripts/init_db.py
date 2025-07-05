#!/usr/bin/env python3
"""
Database initialization script for the Adaptive Boss Behavior System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, engine
from app.models import Base
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {str(e)}")
        return False


def check_database_connection():
    """Check if database connection is working"""
    try:
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✅ Database connection successful!")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False


def main():
    """Main initialization function"""
    logger.info("🚀 Initializing Adaptive Boss Behavior System Database")
    logger.info("=" * 60)
    
    # Check configuration
    logger.info(f"Database URL: {settings.database_url}")
    
    # Test connection
    if not check_database_connection():
        logger.error("Cannot proceed without database connection")
        sys.exit(1)
    
    # Create tables
    if not create_tables():
        logger.error("Failed to create database tables")
        sys.exit(1)
    
    logger.info("✨ Database initialization completed successfully!")
    logger.info("You can now start the application with: python -m app.main")


if __name__ == "__main__":
    main()