from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.api.endpoints import router
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
    logger.info("Starting Adaptive Boss Behavior System...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    # Create data directories
    import os
    os.makedirs(settings.faiss_index_path, exist_ok=True)
    logger.info(f"FAISS index directory created: {settings.faiss_index_path}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Adaptive Boss Behavior System...")


# Create FastAPI application
app = FastAPI(
    title="Adaptive Boss Behavior System",
    description="""
    An adaptive boss behavior system that uses RAG pipeline combining FAISS, OpenAI embeddings, 
    and JigsawStack Prompt Engine. The system learns from player interactions to provide 
    increasingly effective boss behaviors tailored to each game and player context.
    
    ## Features
    
    * **RAG Pipeline**: Combines FAISS vector search with OpenAI embeddings
    * **JigsawStack Integration**: Uses JigsawStack Prompt Engine for game-specific AI responses
    * **Adaptive Learning**: Learns from action outcomes to improve future responses
    * **Multi-Game Support**: Handles different games with unique vocabularies and mechanics
    * **Secure API**: JWT-based authentication with encrypted credential storage
    * **Real-time Analytics**: Provides insights into system performance and learning progress
    
    ## Authentication
    
    Most endpoints require authentication using JWT tokens. Register your game first to get an access token.
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


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "name": "Adaptive Boss Behavior System",
        "version": "1.0.0",
        "description": "RAG-powered adaptive boss AI using FAISS, OpenAI, and JigsawStack",
        "docs": "/docs",
        "health": "/api/v1/health",
        "features": [
            "Multi-game support",
            "RAG pipeline with FAISS",
            "OpenAI embeddings",
            "JigsawStack Prompt Engine",
            "Adaptive learning",
            "Real-time analytics",
            "Secure authentication"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )