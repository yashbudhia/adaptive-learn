from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import redis
from typing import Generator
from app.config import settings

# Database setup
engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Redis setup
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> redis.Redis:
    """Get Redis client"""
    return redis_client


def init_db():
    """Initialize database tables"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)