from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis
from typing import Generator, AsyncGenerator
from app.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

# Debug: Print the database URL being used
print(f"DEBUG: Database URL being used: {settings.database_url}")

# Database setup
engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Redis setup
redis_client = redis.from_url(settings.redis_url, decode_responses=True)
aioredis_client = None


async def get_aioredis():
    """Get async Redis client"""
    global aioredis_client
    if aioredis_client is None:
        aioredis_client = redis.from_url(
            settings.redis_url, 
            decode_responses=True,
            max_connections=20
        )
    return aioredis_client


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[Session, None]:
    """Async dependency to get database session"""
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


# WebSocket Connection Manager
class WebSocketConnectionManager:
    """Manages WebSocket connections for real-time communication"""
    
    def __init__(self):
        self.active_connections: dict = {}  # session_id -> websocket
        self.game_sessions: dict = {}  # game_id -> set of session_ids
        self.session_info: dict = {}  # session_id -> session info
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket, session_id: str, game_id: str, client_info: dict = None):
        """Accept a WebSocket connection"""
        async with self._lock:
            await websocket.accept()
            
            self.active_connections[session_id] = websocket
            
            if game_id not in self.game_sessions:
                self.game_sessions[game_id] = set()
            self.game_sessions[game_id].add(session_id)
            
            self.session_info[session_id] = {
                'game_id': game_id,
                'client_info': client_info or {},
                'connected_at': asyncio.get_event_loop().time()
            }
            
            logger.info(f"WebSocket connected: {session_id} for game {game_id}")
    
    async def disconnect(self, session_id: str):
        """Disconnect a WebSocket"""
        async with self._lock:
            if session_id in self.active_connections:
                websocket = self.active_connections.pop(session_id)
                
                # Remove from game sessions
                session_info = self.session_info.get(session_id, {})
                game_id = session_info.get('game_id')
                if game_id and game_id in self.game_sessions:
                    self.game_sessions[game_id].discard(session_id)
                    if not self.game_sessions[game_id]:
                        del self.game_sessions[game_id]
                
                # Remove session info
                self.session_info.pop(session_id, None)
                
                logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_personal_message(self, message: dict, session_id: str):
        """Send a message to a specific session"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {str(e)}")
                await self.disconnect(session_id)
                return False
        return False
    
    async def broadcast_to_game(self, message: dict, game_id: str, exclude_session: str = None):
        """Broadcast a message to all sessions of a game"""
        if game_id not in self.game_sessions:
            return 0
        
        sent_count = 0
        sessions_to_remove = []
        
        for session_id in self.game_sessions[game_id].copy():
            if exclude_session and session_id == exclude_session:
                continue
                
            if await self.send_personal_message(message, session_id):
                sent_count += 1
            else:
                sessions_to_remove.append(session_id)
        
        # Clean up failed sessions
        for session_id in sessions_to_remove:
            await self.disconnect(session_id)
        
        return sent_count
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected sessions"""
        sent_count = 0
        sessions_to_remove = []
        
        for session_id in list(self.active_connections.keys()):
            if await self.send_personal_message(message, session_id):
                sent_count += 1
            else:
                sessions_to_remove.append(session_id)
        
        # Clean up failed sessions
        for session_id in sessions_to_remove:
            await self.disconnect(session_id)
        
        return sent_count
    
    def get_game_sessions(self, game_id: str) -> set:
        """Get all session IDs for a game"""
        return self.game_sessions.get(game_id, set()).copy()
    
    def get_session_info(self, session_id: str) -> dict:
        """Get session information"""
        return self.session_info.get(session_id, {})
    
    def get_active_sessions_count(self) -> int:
        """Get total number of active sessions"""
        return len(self.active_connections)
    
    def get_game_sessions_count(self, game_id: str) -> int:
        """Get number of active sessions for a game"""
        return len(self.game_sessions.get(game_id, set()))
    
    async def cleanup_inactive_sessions(self, timeout_seconds: int = 300):
        """Clean up inactive sessions"""
        current_time = asyncio.get_event_loop().time()
        sessions_to_remove = []
        
        for session_id, info in self.session_info.items():
            if current_time - info.get('connected_at', 0) > timeout_seconds:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            await self.disconnect(session_id)
        
        return len(sessions_to_remove)


# Global WebSocket manager instance
websocket_manager = WebSocketConnectionManager()


# Real-time cache for fast lookups
class RealtimeCache:
    """Redis-based cache for real-time data"""
    
    def __init__(self):
        self.redis = redis_client
        self.prefix = "adaptive_boss:"
    
    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}"
    
    async def set_session_data(self, session_id: str, data: dict, ttl: int = 3600):
        """Store session data"""
        redis = await get_aioredis()
        await redis.setex(
            self._key(f"session:{session_id}"),
            ttl,
            str(data)
        )
    
    async def get_session_data(self, session_id: str) -> dict:
        """Get session data"""
        redis = await get_aioredis()
        data = await redis.get(self._key(f"session:{session_id}"))
        return eval(data) if data else {}
    
    async def set_game_stats(self, game_id: str, stats: dict, ttl: int = 300):
        """Cache game statistics"""
        redis = await get_aioredis()
        await redis.setex(
            self._key(f"stats:{game_id}"),
            ttl,
            str(stats)
        )
    
    async def get_game_stats(self, game_id: str) -> dict:
        """Get cached game statistics"""
        redis = await get_aioredis()
        data = await redis.get(self._key(f"stats:{game_id}"))
        return eval(data) if data else {}
    
    async def increment_counter(self, key: str, ttl: int = 3600) -> int:
        """Increment a counter"""
        redis = await get_aioredis()
        pipe = redis.pipeline()
        pipe.incr(self._key(key))
        pipe.expire(self._key(key), ttl)
        results = await pipe.execute()
        return results[0]
    
    async def set_realtime_action(self, action_id: str, action_data: dict, ttl: int = 60):
        """Store real-time action data"""
        redis = await get_aioredis()
        await redis.setex(
            self._key(f"action:{action_id}"),
            ttl,
            str(action_data)
        )
    
    async def get_realtime_action(self, action_id: str) -> dict:
        """Get real-time action data"""
        redis = await get_aioredis()
        data = await redis.get(self._key(f"action:{action_id}"))
        return eval(data) if data else {}


# Global realtime cache instance
realtime_cache = RealtimeCache()