#!/usr/bin/env python3
"""
Startup script for the Adaptive Boss Behavior System
"""

import sys
import os
import subprocess
import time
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import init_db, engine
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if all required dependencies are available"""
    logger.info("🔍 Checking dependencies...")
    
    # Check OpenAI API key
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        logger.error("❌ OpenAI API key not configured. Please set OPENAI_API_KEY in .env")
        return False
    
    # Check JigsawStack API key
    if not settings.jigsawstack_api_key or settings.jigsawstack_api_key == "your_jigsawstack_api_key_here":
        logger.error("❌ JigsawStack API key not configured. Please set JIGSAWSTACK_API_KEY in .env")
        return False
    
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        logger.error("Please ensure PostgreSQL is running and DATABASE_URL is correct")
        return False
    
    # Check Redis connection
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        logger.info("✅ Redis connection successful")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        logger.error("Please ensure Redis is running and REDIS_URL is correct")
        return False
    
    logger.info("✅ All dependencies check passed")
    return True


def initialize_database():
    """Initialize the database"""
    logger.info("🗄️ Initializing database...")
    
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        return False


def create_directories():
    """Create necessary directories"""
    logger.info("📁 Creating directories...")
    
    directories = [
        settings.faiss_index_path,
        "logs",
        "data"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✅ Created directory: {directory}")


def start_application():
    """Start the FastAPI application"""
    logger.info("🚀 Starting Adaptive Boss Behavior System...")
    
    try:
        # Import and run the application
        from app.main import app
        import uvicorn
        
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info" if not settings.debug else "debug",
            reload=settings.debug
        )
    except KeyboardInterrupt:
        logger.info("👋 Application stopped by user")
    except Exception as e:
        logger.error(f"❌ Application failed to start: {str(e)}")
        sys.exit(1)


def main():
    """Main startup function"""
    print("🎮 Adaptive Boss Behavior System")
    print("=" * 50)
    print("RAG-powered adaptive boss AI using FAISS, OpenAI, and JigsawStack")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        logger.warning("⚠️  .env file not found. Please copy .env.example to .env and configure it.")
        logger.info("You can continue with environment variables if they are set.")
        time.sleep(2)
    
    # Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        logger.error("❌ Database initialization failed.")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Start the application
    logger.info("🎯 All checks passed. Starting the application...")
    logger.info(f"📡 API will be available at: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"📚 Documentation will be available at: http://{settings.api_host}:{settings.api_port}/docs")
    
    time.sleep(1)
    start_application()


if __name__ == "__main__":
    main()