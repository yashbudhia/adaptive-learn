from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, get_aioredis
from app.api.endpoints import router
from app.api.websocket_endpoints import websocket_router
from app.models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Adaptive Boss Behavior System with Real-time WebSocket Support...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    # Initialize Redis connection
    try:
        redis = await get_aioredis()
        await redis.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise
    
    # Create data directories
    import os
    os.makedirs(settings.faiss_index_path, exist_ok=True)
    logger.info(f"FAISS index directory created: {settings.faiss_index_path}")
    
    logger.info("Application startup complete")
    logger.info(f"🎮 Real-time WebSocket endpoint: ws://localhost:{settings.api_port}/api/v1/ws/{{game_id}}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Adaptive Boss Behavior System...")
    
    # Close JigsawStack session
    try:
        from app.services.jigsawstack_service import JigsawStackService
        jigsawstack_service = JigsawStackService()
        await jigsawstack_service.close_session()
        logger.info("JigsawStack session closed")
    except Exception as e:
        logger.warning(f"Error closing JigsawStack session: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="Adaptive Boss Behavior System",
    description="""
    An adaptive boss behavior system with **real-time WebSocket support** that uses RAG pipeline 
    combining FAISS, OpenAI embeddings, and JigsawStack Prompt Engine. The system learns from 
    player interactions to provide increasingly effective boss behaviors tailored to each game 
    and player context.
    
    ## 🚀 Features
    
    * **Real-time WebSocket Communication**: Instant boss action generation and learning updates
    * **RAG Pipeline**: Combines FAISS vector search with OpenAI embeddings
    * **JigsawStack Integration**: Uses JigsawStack Prompt Engine for game-specific AI responses
    * **Adaptive Learning**: Learns from action outcomes to improve future responses
    * **Multi-Game Support**: Handles different games with unique vocabularies and mechanics
    * **Secure API**: JWT-based authentication with encrypted credential storage
    * **Real-time Analytics**: Live insights into system performance and learning progress
    
    ## 🔌 WebSocket Integration
    
    Connect to the WebSocket endpoint for real-time boss behavior:
    
    ```
    ws://localhost:8000/api/v1/ws/{game_id}?token={jwt_token}
    ```
    
    ### Message Types:
    - `boss_action_request`: Request adaptive boss action
    - `boss_action_response`: Receive generated boss action
    - `action_outcome`: Log action effectiveness
    - `learning_update`: Receive system learning updates
    - `heartbeat`: Connection health monitoring
    
    ## 🎯 Real-time Workflow
    
    1. **Connect**: Establish WebSocket connection with JWT token
    2. **Request**: Send player context for boss action generation
    3. **Receive**: Get adaptive boss action in real-time
    4. **Execute**: Perform boss action in your game
    5. **Feedback**: Send action outcome for system learning
    6. **Learn**: Receive learning updates and improvements
    
    ## 🔐 Authentication
    
    Most endpoints require authentication using JWT tokens. Register your game first to get an access token.
    WebSocket connections also require valid JWT tokens passed as query parameters.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "path": str(request.url)
        }
    )


# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Adaptive Boss System"])
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket Real-time"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    from app.database import websocket_manager
    
    return {
        "name": "Adaptive Boss Behavior System",
        "version": "1.0.0",
        "description": "RAG-powered adaptive boss AI with real-time WebSocket support",
        "docs": "/docs",
        "health": "/api/v1/health",
        "websocket_endpoint": f"ws://localhost:{settings.api_port}/api/v1/ws/{{game_id}}",
        "active_websocket_connections": websocket_manager.get_active_sessions_count(),
        "features": [
            "Real-time WebSocket communication",
            "Multi-game support",
            "RAG pipeline with FAISS",
            "OpenAI embeddings",
            "JigsawStack Prompt Engine",
            "Adaptive learning",
            "Real-time analytics",
            "Secure authentication"
        ],
        "endpoints": {
            "register_game": "POST /api/v1/games/register",
            "generate_action": "POST /api/v1/boss/action",
            "websocket": "WS /api/v1/ws/{game_id}",
            "get_token": "GET /api/v1/games/{game_id}/token",
            "health_check": "GET /api/v1/health"
        }
    }


# WebSocket connection info endpoint
@app.get("/websocket-info")
async def websocket_info():
    """Information about WebSocket connections and usage"""
    from app.database import websocket_manager
    
    return {
        "websocket_url": f"ws://localhost:{settings.api_port}/api/v1/ws/{{game_id}}",
        "connection_params": {
            "token": "JWT access token (required)",
            "session_id": "Optional session identifier"
        },
        "message_types": [
            "connect", "disconnect", "heartbeat",
            "boss_action_request", "boss_action_response", 
            "action_outcome", "learning_update", "error", "status"
        ],
        "current_stats": {
            "active_connections": websocket_manager.get_active_sessions_count(),
            "games_with_connections": len(websocket_manager.game_sessions),
            "max_connections": settings.max_websocket_connections
        },
        "example_usage": {
            "javascript": "const ws = new WebSocket('ws://localhost:8000/api/v1/ws/my_game?token=jwt_token');",
            "unity": "Use WebSocket libraries like NativeWebSocket or WebSocketSharp",
            "python": "Use websockets library: websockets.connect('ws://localhost:8000/api/v1/ws/my_game?token=jwt_token')"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        ws_ping_interval=30,
        ws_ping_timeout=10
    )