import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.database import websocket_manager, realtime_cache, get_async_db
from app.config import settings
from app.models import (
    WebSocketMessage, WebSocketMessageType, BossActionRequest, BossActionResponse,
    WebSocketBossActionRequest, WebSocketActionOutcome, LearningUpdateData,
    RealtimeStats, WebSocketSession, Game
)
from app.services.adaptive_boss_service import AdaptiveBossService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RealtimeAdaptiveBossService:
    """Real-time WebSocket service for adaptive boss behavior"""
    
    def __init__(self):
        self.adaptive_service = AdaptiveBossService()
        self.active_requests: Dict[str, Dict[str, Any]] = {}  # request_id -> request_data
        self.performance_metrics = {
            'actions_per_minute': 0,
            'avg_response_time': 0.0,
            'total_requests': 0,
            'successful_requests': 0,
            'start_time': time.time()
        }
        
        # Start background tasks
        asyncio.create_task(self._cleanup_task())
        asyncio.create_task(self._metrics_update_task())
    
    async def handle_websocket_connection(self, websocket, session_id: str, game_id: str, 
                                        access_token: str, client_info: Dict[str, Any]):
        """Handle a new WebSocket connection"""
        try:
            # Verify access token and game
            # (You'd implement proper JWT verification here)
            
            # Connect to WebSocket manager
            await websocket_manager.connect(websocket, session_id, game_id, client_info)
            
            # Store session in database
            async for db in get_async_db():
                game = db.query(Game).filter(Game.game_id == game_id).first()
                if game:
                    ws_session = WebSocketSession(
                        session_id=session_id,
                        game_id=game.id,
                        client_info=client_info,
                        is_active=True
                    )
                    db.add(ws_session)
                    db.commit()
                break
            
            # Send welcome message
            welcome_message = WebSocketMessage(
                type=WebSocketMessageType.CONNECT,
                data={
                    'status': 'connected',
                    'session_id': session_id,
                    'game_id': game_id,
                    'features': [
                        'realtime_boss_actions',
                        'learning_updates',
                        'performance_metrics'
                    ]
                },
                session_id=session_id,
                game_id=game_id
            )
            
            await websocket_manager.send_personal_message(
                welcome_message.dict(), session_id
            )
            
            logger.info(f"WebSocket session established: {session_id} for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {str(e)}")
            await websocket_manager.disconnect(session_id)
    
    async def handle_websocket_message(self, websocket, session_id: str, message_data: dict):
        """Handle incoming WebSocket message"""
        try:
            message = WebSocketMessage(**message_data)
            
            if message.type == WebSocketMessageType.HEARTBEAT:
                await self._handle_heartbeat(session_id)
            
            elif message.type == WebSocketMessageType.BOSS_ACTION_REQUEST:
                await self._handle_boss_action_request(session_id, message.data)
            
            elif message.type == WebSocketMessageType.ACTION_OUTCOME:
                await self._handle_action_outcome(session_id, message.data)
            
            else:
                logger.warning(f"Unknown message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
            error_message = WebSocketMessage(
                type=WebSocketMessageType.ERROR,
                data={'error': str(e)},
                session_id=session_id
            )
            await websocket_manager.send_personal_message(
                error_message.dict(), session_id
            )
    
    async def _handle_heartbeat(self, session_id: str):
        """Handle heartbeat message"""
        # Update last heartbeat in database
        async for db in get_async_db():
            ws_session = db.query(WebSocketSession).filter(
                WebSocketSession.session_id == session_id
            ).first()
            if ws_session:
                ws_session.last_heartbeat = datetime.utcnow()
                db.commit()
            break
        
        # Send heartbeat response
        response = WebSocketMessage(
            type=WebSocketMessageType.HEARTBEAT,
            data={'status': 'alive'},
            session_id=session_id
        )
        await websocket_manager.send_personal_message(response.dict(), session_id)
    
    async def _handle_boss_action_request(self, session_id: str, request_data: dict):
        """Handle real-time boss action request"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Parse request
            ws_request = WebSocketBossActionRequest(**request_data)
            
            # Get session info
            session_info = websocket_manager.get_session_info(session_id)
            game_id = session_info.get('game_id')
            
            if not game_id:
                raise ValueError("No game_id found for session")
            
            # Store active request
            self.active_requests[request_id] = {
                'session_id': session_id,
                'game_id': game_id,
                'start_time': start_time,
                'request_data': ws_request.dict()
            }
            
            # Create boss action request
            boss_request = BossActionRequest(
                game_id=game_id,
                player_context=ws_request.player_context,
                boss_health_percentage=ws_request.boss_health_percentage,
                battle_phase=ws_request.battle_phase,
                environment_factors=ws_request.environment_factors,
                realtime=True,
                session_id=session_id
            )
            
            # Generate boss action asynchronously
            asyncio.create_task(self._generate_boss_action_async(
                request_id, boss_request, session_id
            ))
            
            # Send immediate acknowledgment
            ack_message = WebSocketMessage(
                type=WebSocketMessageType.STATUS,
                data={
                    'status': 'processing',
                    'request_id': request_id,
                    'estimated_time': 2.0  # seconds
                },
                session_id=session_id
            )
            await websocket_manager.send_personal_message(ack_message.dict(), session_id)
            
        except Exception as e:
            logger.error(f"Error handling boss action request: {str(e)}")
            error_message = WebSocketMessage(
                type=WebSocketMessageType.ERROR,
                data={
                    'error': str(e),
                    'request_id': request_id
                },
                session_id=session_id
            )
            await websocket_manager.send_personal_message(error_message.dict(), session_id)
    
    async def _generate_boss_action_async(self, request_id: str, boss_request: BossActionRequest, 
                                        session_id: str):
        """Generate boss action asynchronously"""
        try:
            # Get database session
            async for db in get_async_db():
                # Generate boss action
                boss_action = self.adaptive_service.generate_boss_action(boss_request, db)
                
                # Calculate response time
                request_info = self.active_requests.get(request_id, {})
                start_time = request_info.get('start_time', time.time())
                response_time = time.time() - start_time
                
                # Update performance metrics
                self._update_metrics(response_time, True)
                
                # Add response time to boss action
                boss_action.response_time = response_time
                
                # Send response
                response_message = WebSocketMessage(
                    type=WebSocketMessageType.BOSS_ACTION_RESPONSE,
                    data={
                        'request_id': request_id,
                        'boss_action': boss_action.dict()
                    },
                    session_id=session_id
                )
                
                await websocket_manager.send_personal_message(
                    response_message.dict(), session_id
                )
                
                # Store in real-time cache
                await realtime_cache.set_realtime_action(
                    request_id, boss_action.dict(), ttl=300
                )
                
                logger.info(f"Boss action generated for request {request_id} in {response_time:.3f}s")
                break
                
        except Exception as e:
            logger.error(f"Error generating boss action: {str(e)}")
            self._update_metrics(0, False)
            
            error_message = WebSocketMessage(
                type=WebSocketMessageType.ERROR,
                data={
                    'error': str(e),
                    'request_id': request_id
                },
                session_id=session_id
            )
            await websocket_manager.send_personal_message(error_message.dict(), session_id)
        
        finally:
            # Clean up active request
            self.active_requests.pop(request_id, None)
    
    async def _handle_action_outcome(self, session_id: str, outcome_data: dict):
        """Handle action outcome from client"""
        try:
            ws_outcome = WebSocketActionOutcome(**outcome_data)
            
            # Get session info
            session_info = websocket_manager.get_session_info(session_id)
            game_id = session_info.get('game_id')
            
            # Log outcome to database
            async for db in get_async_db():
                from app.models import ActionOutcomeData
                outcome = ActionOutcomeData(
                    action_id=ws_outcome.action_id,
                    outcome=ws_outcome.outcome,
                    effectiveness_score=ws_outcome.effectiveness_score,
                    damage_dealt=ws_outcome.damage_dealt,
                    player_hit=ws_outcome.player_hit,
                    execution_time=ws_outcome.execution_time,
                    additional_metrics=ws_outcome.additional_metrics
                )
                
                self.adaptive_service.log_action_outcome(outcome, db)
                break
            
            # Send learning update to all sessions of this game
            await self._broadcast_learning_update(game_id, ws_outcome.effectiveness_score)
            
            logger.info(f"Action outcome logged for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling action outcome: {str(e)}")
    
    async def _broadcast_learning_update(self, game_id: str, effectiveness_score: float):
        """Broadcast learning update to all game sessions"""
        try:
            # Get game statistics
            async for db in get_async_db():
                stats = self.adaptive_service.get_game_stats(game_id, db)
                break
            
            # Create learning update
            learning_update = LearningUpdateData(
                contexts_learned=stats.get('faiss_stats', {}).get('total_contexts', 0),
                avg_effectiveness=stats.get('avg_effectiveness', 0.0),
                recent_improvements=[
                    f"Action effectiveness: {effectiveness_score:.1%}",
                    f"Learning rate: {stats.get('learning_progress', {}).get('improvement_trend', 0):.1%}"
                ],
                performance_trend="improving" if effectiveness_score > 0.7 else "stable"
            )
            
            # Broadcast to all sessions of this game
            update_message = WebSocketMessage(
                type=WebSocketMessageType.LEARNING_UPDATE,
                data=learning_update.dict(),
                game_id=game_id
            )
            
            await websocket_manager.broadcast_to_game(
                update_message.dict(), game_id
            )
            
        except Exception as e:
            logger.error(f"Error broadcasting learning update: {str(e)}")
    
    def _update_metrics(self, response_time: float, success: bool):
        """Update performance metrics"""
        self.performance_metrics['total_requests'] += 1
        if success:
            self.performance_metrics['successful_requests'] += 1
        
        # Update average response time
        if response_time > 0:
            current_avg = self.performance_metrics['avg_response_time']
            total_requests = self.performance_metrics['total_requests']
            self.performance_metrics['avg_response_time'] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
        
        # Update actions per minute
        elapsed_time = time.time() - self.performance_metrics['start_time']
        if elapsed_time > 0:
            self.performance_metrics['actions_per_minute'] = (
                self.performance_metrics['total_requests'] / (elapsed_time / 60)
            )
    
    async def get_realtime_stats(self) -> RealtimeStats:
        """Get real-time system statistics"""
        return RealtimeStats(
            active_sessions=websocket_manager.get_active_sessions_count(),
            actions_per_minute=self.performance_metrics['actions_per_minute'],
            avg_response_time=self.performance_metrics['avg_response_time'],
            learning_rate=self.performance_metrics['successful_requests'] / max(1, self.performance_metrics['total_requests']),
            cache_hit_rate=0.85  # This would be calculated from actual cache metrics
        )
    
    async def _cleanup_task(self):
        """Background task to clean up inactive sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Clean up inactive WebSocket sessions
                cleaned = await websocket_manager.cleanup_inactive_sessions(
                    timeout_seconds=settings.websocket_timeout
                )
                
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} inactive WebSocket sessions")
                
                # Clean up old active requests
                current_time = time.time()
                expired_requests = [
                    req_id for req_id, req_data in self.active_requests.items()
                    if current_time - req_data.get('start_time', 0) > settings.realtime_action_timeout
                ]
                
                for req_id in expired_requests:
                    self.active_requests.pop(req_id, None)
                
                if expired_requests:
                    logger.info(f"Cleaned up {len(expired_requests)} expired requests")
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
    
    async def _metrics_update_task(self):
        """Background task to update metrics"""
        while True:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                # Update real-time stats in cache
                stats = await self.get_realtime_stats()
                await realtime_cache.set_game_stats("_global", stats.dict(), ttl=60)
                
            except Exception as e:
                logger.error(f"Error in metrics update task: {str(e)}")


# Global real-time service instance
realtime_service = RealtimeAdaptiveBossService()