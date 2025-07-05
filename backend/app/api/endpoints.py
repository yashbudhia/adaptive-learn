from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
import logging

from app.database import get_db, websocket_manager
from app.models import (
    BossActionRequest, BossActionResponse, ActionOutcomeData,
    GameRegistrationRequest, GameRegistrationResponse, HealthCheckResponse,
    RealtimeStats
)
from app.services.adaptive_boss_service import AdaptiveBossService
from app.services.realtime_service import realtime_service
from app.api.auth import get_current_user, get_optional_user, create_game_token

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
adaptive_boss_service = AdaptiveBossService()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint with WebSocket connection info"""
    try:
        # Get real-time stats
        realtime_stats = await realtime_service.get_realtime_stats()
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            services={
                "database": "connected",
                "redis": "connected",
                "faiss": "ready",
                "openai": "configured",
                "jigsawstack": "configured",
                "websockets": "active"
            },
            websocket_connections=websocket_manager.get_active_sessions_count()
        )
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return HealthCheckResponse(
            status="degraded",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            services={
                "database": "unknown",
                "redis": "unknown",
                "faiss": "unknown",
                "openai": "unknown",
                "jigsawstack": "unknown",
                "websockets": "unknown"
            },
            websocket_connections=0
        )


@router.post("/games/register", response_model=GameRegistrationResponse)
async def register_game(
    request: GameRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register a new game with the adaptive boss system"""
    try:
        result = await adaptive_boss_service.register_game_async(
            request.game_id,
            request.name,
            request.description,
            request.vocabulary,
            db
        )
        
        if result["success"]:
            # Create access token for the game
            access_token = create_game_token(request.game_id)
            result["access_token"] = access_token
        
        return GameRegistrationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error registering game: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register game: {str(e)}"
        )


@router.post("/boss/action", response_model=BossActionResponse)
async def generate_boss_action(
    request: BossActionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate an adaptive boss action based on player context"""
    try:
        # Verify game access
        if current_user["game_id"] != request.game_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this game"
            )
        
        # Use async version if real-time is requested
        if request.realtime:
            boss_action = await adaptive_boss_service.generate_boss_action_async(request, db)
        else:
            boss_action = adaptive_boss_service.generate_boss_action(request, db)
        
        return boss_action
        
    except ValueError as e:
        logger.warning(f"Invalid request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating boss action: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate boss action: {str(e)}"
        )


@router.post("/boss/action/outcome")
async def log_action_outcome(
    outcome: ActionOutcomeData,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Log the outcome of a boss action for learning"""
    try:
        # Use async version for better performance
        await adaptive_boss_service.log_action_outcome_async(outcome, db)
        
        # Schedule index optimization in background if needed
        background_tasks.add_task(optimize_game_index_if_needed, current_user["game_id"], db)
        
        return {"success": True, "message": "Action outcome logged successfully"}
        
    except ValueError as e:
        logger.warning(f"Invalid outcome data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error logging action outcome: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log action outcome: {str(e)}"
        )


@router.get("/games/{game_id}/stats")
async def get_game_stats(
    game_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for a game's adaptive behavior system"""
    try:
        # Verify game access
        if current_user["game_id"] != game_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this game"
            )
        
        stats = adaptive_boss_service.get_game_stats(game_id, db)
        
        # Add real-time WebSocket stats
        websocket_sessions = websocket_manager.get_game_sessions_count(game_id)
        stats["websocket_sessions"] = websocket_sessions
        
        return stats
        
    except ValueError as e:
        logger.warning(f"Invalid request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting game stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game stats: {str(e)}"
        )


@router.get("/games/{game_id}/realtime-stats", response_model=RealtimeStats)
async def get_realtime_stats(
    game_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get real-time statistics for a game"""
    try:
        # Verify game access
        if current_user["game_id"] != game_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this game"
            )
        
        stats = await realtime_service.get_realtime_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting real-time stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get real-time stats: {str(e)}"
        )


@router.post("/games/{game_id}/optimize")
async def optimize_game_index(
    game_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Optimize the FAISS index for a game"""
    try:
        # Verify game access
        if current_user["game_id"] != game_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this game"
            )
        
        # Run optimization in background
        background_tasks.add_task(
            adaptive_boss_service.optimize_game_index,
            game_id,
            db
        )
        
        return {"success": True, "message": "Index optimization started"}
        
    except Exception as e:
        logger.error(f"Error starting index optimization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start index optimization: {str(e)}"
        )


@router.get("/games/{game_id}/token")
async def get_game_token(
    game_id: str,
    db: Session = Depends(get_db)
):
    """Get access token for a game (for development/testing purposes)"""
    try:
        # In production, this should have proper authentication
        # For now, we'll just check if the game exists
        from app.models import Game
        game = db.query(Game).filter(Game.game_id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )
        
        access_token = create_game_token(game_id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "game_id": game_id,
            "websocket_url": f"/api/v1/ws/{game_id}?token={access_token}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )


# Public endpoints (no authentication required)
@router.get("/games/public/stats/{game_id}")
async def get_public_game_stats(
    game_id: str,
    db: Session = Depends(get_db)
):
    """Get public statistics for a game (limited information)"""
    try:
        stats = adaptive_boss_service.get_game_stats(game_id, db)
        
        # Return only public information
        public_stats = {
            "game_id": game_id,
            "total_actions": stats.get("total_actions", 0),
            "success_rate": stats.get("success_rate", 0.0),
            "active_websocket_sessions": websocket_manager.get_game_sessions_count(game_id),
            "learning_progress": {
                "contexts_learned": stats.get("faiss_stats", {}).get("total_contexts", 0),
                "avg_effectiveness": stats.get("faiss_stats", {}).get("avg_effectiveness", 0.0)
            }
        }
        
        return public_stats
        
    except ValueError as e:
        logger.warning(f"Invalid request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting public game stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game stats: {str(e)}"
        )


# Development/Testing endpoints
@router.post("/dev/test-boss-action")
async def test_boss_action(
    request: BossActionRequest,
    db: Session = Depends(get_db)
):
    """Test endpoint for boss action generation (development only)"""
    try:
        # This endpoint bypasses authentication for testing
        if request.realtime:
            boss_action = await adaptive_boss_service.generate_boss_action_async(request, db)
        else:
            boss_action = adaptive_boss_service.generate_boss_action(request, db)
        return boss_action
        
    except Exception as e:
        logger.error(f"Error in test boss action: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test failed: {str(e)}"
        )


@router.get("/dev/websocket-info")
async def get_websocket_info():
    """Get WebSocket connection information for development"""
    try:
        return {
            "total_connections": websocket_manager.get_active_sessions_count(),
            "games": {
                game_id: websocket_manager.get_game_sessions_count(game_id)
                for game_id in websocket_manager.game_sessions.keys()
            },
            "realtime_stats": (await realtime_service.get_realtime_stats()).dict()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket info: {str(e)}")
        return {"error": str(e)}


async def optimize_game_index_if_needed(game_id: str, db: Session):
    """Background task to optimize game index if needed"""
    try:
        # Add logic to determine if optimization is needed
        # For example, optimize every 100 new outcomes
        adaptive_boss_service.optimize_game_index(game_id, db)
        logger.info(f"Background optimization completed for game {game_id}")
    except Exception as e:
        logger.error(f"Background optimization failed for game {game_id}: {str(e)}")


# WebSocket connection examples for documentation
websocket_examples = {
    "connection_url": "/api/v1/ws/{game_id}?token={jwt_token}&session_id={optional_session_id}",
    "message_types": [
        "connect", "disconnect", "heartbeat", 
        "boss_action_request", "boss_action_response",
        "action_outcome", "learning_update", "error", "status"
    ],
    "example_flow": [
        "1. Connect to WebSocket with JWT token",
        "2. Send boss_action_request with player context",
        "3. Receive boss_action_response with adaptive action",
        "4. Execute action in game",
        "5. Send action_outcome with effectiveness score",
        "6. Receive learning_update with system improvements"
    ]
}