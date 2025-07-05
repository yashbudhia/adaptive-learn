from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
import json
import uuid
import asyncio
import logging
from typing import Optional

from app.database import get_db, websocket_manager
from app.models import (
    WebSocketMessage, WebSocketMessageType, WebSocketConnectData,
    WebSocketBossActionRequest, WebSocketActionOutcome
)
from app.services.realtime_service import realtime_service
from app.api.auth import get_websocket_user

logger = logging.getLogger(__name__)

# Create WebSocket router
websocket_router = APIRouter()


@websocket_router.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(..., description="JWT access token"),
    session_id: Optional[str] = Query(None, description="Optional session ID"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time adaptive boss behavior
    
    This endpoint provides real-time communication for:
    - Boss action requests and responses
    - Action outcome logging
    - Learning updates
    - Performance metrics
    """
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Authenticate user
    user = await get_websocket_user(websocket, token)
    if not user or user["game_id"] != game_id:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    logger.info(f"WebSocket connection attempt: {session_id} for game {game_id}")
    
    try:
        # Handle connection
        await realtime_service.handle_websocket_connection(
            websocket, session_id, game_id, token, 
            {"user_agent": websocket.headers.get("user-agent", "unknown")}
        )
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            _heartbeat_task(websocket, session_id)
        )
        
        # Message handling loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle message
                await realtime_service.handle_websocket_message(
                    websocket, session_id, message_data
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {session_id}")
                break
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received from {session_id}: {str(e)}")
                error_message = WebSocketMessage(
                    type=WebSocketMessageType.ERROR,
                    data={"error": "Invalid JSON format"},
                    session_id=session_id
                )
                await websocket.send_text(json.dumps(error_message.dict()))
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {session_id}: {str(e)}")
                error_message = WebSocketMessage(
                    type=WebSocketMessageType.ERROR,
                    data={"error": str(e)},
                    session_id=session_id
                )
                try:
                    await websocket.send_text(json.dumps(error_message.dict()))
                except:
                    break
    
    except Exception as e:
        logger.error(f"WebSocket connection error for {session_id}: {str(e)}")
        try:
            await websocket.close(code=4000, reason=f"Server error: {str(e)}")
        except:
            pass
    
    finally:
        # Cleanup
        heartbeat_task.cancel()
        await websocket_manager.disconnect(session_id)
        logger.info(f"WebSocket cleanup completed for {session_id}")


async def _heartbeat_task(websocket: WebSocket, session_id: str):
    """Background task to send periodic heartbeats"""
    try:
        while True:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            
            heartbeat_message = WebSocketMessage(
                type=WebSocketMessageType.HEARTBEAT,
                data={"status": "ping"},
                session_id=session_id
            )
            
            try:
                await websocket.send_text(json.dumps(heartbeat_message.dict()))
            except:
                # Connection closed
                break
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Heartbeat task error for {session_id}: {str(e)}")


# Additional WebSocket management endpoints
@websocket_router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = await realtime_service.get_realtime_stats()
        return {
            "active_connections": websocket_manager.get_active_sessions_count(),
            "realtime_stats": stats.dict()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {str(e)}")
        return {"error": str(e)}


@websocket_router.get("/ws/games/{game_id}/sessions")
async def get_game_websocket_sessions(game_id: str):
    """Get active WebSocket sessions for a game"""
    try:
        sessions = websocket_manager.get_game_sessions(game_id)
        session_info = []
        
        for session_id in sessions:
            info = websocket_manager.get_session_info(session_id)
            session_info.append({
                "session_id": session_id,
                "connected_at": info.get("connected_at", 0),
                "client_info": info.get("client_info", {})
            })
        
        return {
            "game_id": game_id,
            "active_sessions": len(sessions),
            "sessions": session_info
        }
    except Exception as e:
        logger.error(f"Error getting game WebSocket sessions: {str(e)}")
        return {"error": str(e)}


@websocket_router.post("/ws/games/{game_id}/broadcast")
async def broadcast_to_game(
    game_id: str,
    message: dict,
    exclude_session: Optional[str] = None
):
    """Broadcast a message to all WebSocket sessions of a game"""
    try:
        sent_count = await websocket_manager.broadcast_to_game(
            message, game_id, exclude_session
        )
        
        return {
            "success": True,
            "message": f"Broadcasted to {sent_count} sessions",
            "sent_count": sent_count
        }
    except Exception as e:
        logger.error(f"Error broadcasting to game {game_id}: {str(e)}")
        return {"error": str(e)}


# WebSocket message examples for documentation
websocket_message_examples = {
    "connect": {
        "type": "connect",
        "data": {
            "game_id": "my_game_001",
            "access_token": "jwt_token_here",
            "client_info": {
                "version": "1.0.0",
                "platform": "unity"
            }
        }
    },
    "boss_action_request": {
        "type": "boss_action_request",
        "data": {
            "player_context": {
                "frequent_actions": ["dodge", "attack"],
                "dodge_frequency": 0.7,
                "attack_patterns": ["combo_attack"],
                "movement_style": "aggressive",
                "reaction_time": 0.3,
                "health_percentage": 0.8,
                "difficulty_preference": "normal",
                "session_duration": 15.0,
                "recent_deaths": 1,
                "equipment_level": 5
            },
            "boss_health_percentage": 0.6,
            "battle_phase": "mid_battle",
            "environment_factors": {
                "environment": "arena",
                "lighting": "dim"
            },
            "request_id": "optional_request_id"
        }
    },
    "action_outcome": {
        "type": "action_outcome",
        "data": {
            "action_id": 123,
            "outcome": "success",
            "effectiveness_score": 0.85,
            "damage_dealt": 30.0,
            "player_hit": True,
            "execution_time": 1.5,
            "additional_metrics": {
                "player_reaction": "dodged_partially"
            }
        }
    },
    "heartbeat": {
        "type": "heartbeat",
        "data": {}
    }
}